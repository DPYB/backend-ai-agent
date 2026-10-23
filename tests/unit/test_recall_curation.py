"""Unit tests for recall query routing and honest recommendation history grounding (Phase 71 Step 1).

Verifies:
1. is_recall_query intent classifier:
   - Pure recall queries ('이전에 추천한 도서 알려줘', '아까 추천해준 책 뭐였지') -> True
   - Hybrid queries ('전에 추천한 책 말고 다른 책 추천해줘') -> False (delegates to new curation)
   - Pure recommendation requests ('비 오는 날 소설 추천해줘') -> False
   - General conversations ('안녕하세요') -> False
2. Routing behavior in librarian node:
   - Recall query does NOT delegate to curator_node (curator_request is None)
   - Hybrid query DOES delegate to curator_node (curator_request is set)
   - New recommendation query DOES delegate to curator_node
3. Recommendation history grounding in prompt & response:
   - When recommended_history is empty, prompt instructs honest '기록을 확인할 수 없어요' response
   - When recommended_history has books, prompt grounds strictly to those books
   - No arbitrary books (like '모순') are hallucinated when not in history
   - When '모순' is genuinely in history, it can be legitimately recalled
"""

from typing import List, Optional, cast

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.domain.graph.nodes import (
    cat_node,
    is_recall_query,
)
from app.domain.graph.state import AgentState
from app.main import app


def _make_agent_state(
    messages: List[BaseMessage],
    recommended_history: Optional[List[str]] = None,
    curator_request: Optional[str] = None,
    curated_books: Optional[List[dict]] = None,
    curator_attempted: bool = False,
) -> AgentState:
    """Helper to construct a fully-populated AgentState TypedDict for unit tests."""
    return {
        "messages": messages,
        "member_id": "test-user-uuid",
        "auth_token": None,
        "active_persona": "CAT",
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": curator_request,
        "curator_attempted": curator_attempted,
        "curated_books": curated_books,
        "location_coords": None,
        "weather_context": None,
        "action": "chat",
        "book_id": None,
        "topic": None,
        "debate_book_info": None,
        "is_concluded": None,
        "debate_summary": None,
        "recommended_history": recommended_history or [],
        "target_unresolved": None,
    }


# ==============================================================================
# 1. is_recall_query Classification Tests
# ==============================================================================
class TestIsRecallQuery:
    """Test intent classifier distinguishing pure recall from hybrid/new recommendation queries."""

    @pytest.mark.parametrize(
        "query",
        [
            "이전에 추천한 도서 알려줘",
            "아까 추천해준 책 뭐였지?",
            "전에 추천했던 책 이름이 뭐야?",
            "지난번 추천 책 다시 알려줘",
            "저번에 추천해준 책 뭐였더라",
            "전에 추천한 책 기억나?",
            "아까 그 책 제목이 뭐였지",
            "추천해준 책 다시 알려줘",
            "추천했던 책 목록 보여줘",
            "아까 말한 책이 뭐였지",
            "이전에 추천받은 책 이름",
            "추천한 거 뭐였어?",
        ],
    )
    def test_pure_recall_queries_return_true(self, query: str):
        assert is_recall_query(query) is True

    @pytest.mark.parametrize(
        "query",
        [
            "전에 추천한 책 말고 다른 책 추천해줘",
            "아까 추천해준 거 말고 새로운 책 골라줘",
            "이전에 추천한 책과 비슷한 소설 추천해줘",
            "전에 추천해준 책 말고 다른 거 읽고 싶어",
            "아까 추천한 거 외에 다른 책 알려줘",
            "저번에 추천한 책 말고 또 추천해줘",
            "전에 추천받은 책 대신 다른 책 골라줘",
            "전에 추천한 책이 뭐였지? 그리고 비슷한 책도 추천해 줘",
        ],
    )
    def test_hybrid_queries_return_false_for_new_curation(self, query: str):
        # Hybrid queries contain recall words but their primary intent is a NEW book recommendation
        assert is_recall_query(query) is False

    @pytest.mark.parametrize(
        "query",
        [
            "비 오는 날 읽기 좋은 소설 추천해줘",
            "마음이 따뜻해지는 에세이 골라줘",
            "어떤 책을 읽으면 좋을까?",
            "《데미안》 등록해줘",
            "신간 소설 추천해줘",
            "책 찾아줘",
            "재밌는 책 추천해줘",
        ],
    )
    def test_new_recommendation_queries_return_false(self, query: str):
        assert is_recall_query(query) is False

    @pytest.mark.parametrize(
        "query",
        [
            "안녕하세요",
            "오늘 날씨 어때요?",
            "너는 누구니?",
            "고양이야 안녕",
            "오늘 기분이 좀 그래",
        ],
    )
    def test_general_chat_queries_return_false(self, query: str):
        assert is_recall_query(query) is False

    def test_empty_or_none_query(self):
        assert is_recall_query("") is False
        assert is_recall_query("   ") is False


# ==============================================================================
# 2. Routing Priority in Librarian Persona Nodes
# ==============================================================================
class TestLibrarianRoutingWithRecall:
    """Verify librarian node routing: pure recall bypasses curator, hybrid/new delegates."""

    @pytest.mark.asyncio
    async def test_pure_recall_query_bypasses_curator(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="이전에 추천한 도서 알려줘")],
            recommended_history=[],
        )
        res = await cat_node(state)

        # Pure recall must NOT delegate to curator_node!
        assert "curator_request" not in res or res.get("curator_request") is None
        # It must produce an actual AIMessage response
        assert len(res["messages"]) == 1
        assert isinstance(res["messages"][0], AIMessage)

    @pytest.mark.asyncio
    async def test_hybrid_query_delegates_to_curator(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="전에 추천한 책 말고 다른 책 추천해줘")],
            recommended_history=["데미안"],
        )
        res = await cat_node(state)

        # Hybrid query must delegate to curator_node!
        assert res.get("curator_request") == "전에 추천한 책 말고 다른 책 추천해줘"

    @pytest.mark.asyncio
    async def test_pure_recommendation_delegates_to_curator(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="비 오는 날 읽을 소설 추천해줘")],
            recommended_history=[],
        )
        res = await cat_node(state)

        assert res.get("curator_request") == "비 오는 날 읽을 소설 추천해줘"


# ==============================================================================
# 3. Grounding & Honest Response Behavior
# ==============================================================================
class TestRecallGroundingBehavior:
    """Verify responses when recommended_history is empty vs when books exist."""

    @pytest.mark.asyncio
    async def test_empty_history_honest_response_no_hallucination(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="아까 추천해준 책 뭐였지?")],
            recommended_history=[],  # Empty history (e.g. new session)
        )
        res = await cat_node(state)
        ai_msg = str(res["messages"][0].content)

        # Must state honestly that history cannot be confirmed in this conversation
        assert "확인할 수 없" in ai_msg or "기록" in ai_msg
        # Must NEVER fabricate '모순' or classic books when history is empty!
        assert "모순" not in ai_msg
        assert "### 📖" not in ai_msg  # No recommendation card trigger

    @pytest.mark.asyncio
    async def test_with_history_recalls_only_recorded_books(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="이전에 추천한 도서 알려줘")],
            recommended_history=["코스모스", "어린 왕자"],
        )
        res = await cat_node(state)
        ai_msg = str(res["messages"][0].content)

        # Must recall recorded books
        assert "코스모스" in ai_msg
        assert "어린 왕자" in ai_msg
        # Must NOT hallucinate '모순'
        assert "모순" not in ai_msg

    @pytest.mark.asyncio
    async def test_recalls_mosun_only_when_genuinely_in_history(self):
        state = _make_agent_state(
            messages=[HumanMessage(content="이전에 추천한 도서 다시 알려줘")],
            recommended_history=["모순"],  # Genuinely recommended previously in this session
        )
        res = await cat_node(state)
        ai_msg = str(res["messages"][0].content)

        # In this legitimate case, '모순' must be recalled
        assert "모순" in ai_msg


# ==============================================================================
# 4. Chat & Stream Endpoints Recall Consistency Tests
# ==============================================================================
class TestRecallEndpointsConsistency:
    """Verify endpoint-level routing and streaming consistency for recall queries."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_history_returns_honest_reply_and_empty_books(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "message": "이전에 추천한 도서 알려줘",
                "member_id": "test-member-uuid-1",
                "persona": "CAT",
                "session_id": "new-empty-session-1",
            }
            res = await ac.post("/api/v1/chat", json=payload)
            assert res.status_code == 200
            data = res.json()

            # Must NOT produce any recommended_books
            assert data["recommended_books"] == []
            # Reply must state honestly that history cannot be confirmed in this conversation
            assert "확인할 수 없" in data["reply"] or "기록" in data["reply"]
            assert "모순" not in data["reply"]

    @pytest.mark.asyncio
    async def test_chat_stream_endpoint_empty_history_emits_no_books_event(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "message": "아까 추천해준 책 뭐였지?",
                "member_id": "test-member-uuid-2",
                "persona": "CAT",
                "session_id": "new-empty-session-2",
            }
            res = await ac.post("/api/v1/chat/stream", json=payload)
            assert res.status_code == 200

            stream_text = res.text
            # 'books' event must NEVER be emitted for recall queries!
            assert "event: books" not in stream_text
            # 'done' event must be present
            assert "event: done" in stream_text
            assert "모순" not in stream_text


# ==============================================================================
# 5. Hybrid Query (Recall + New Recommendation) Grounding Tests
# ==============================================================================
class TestHybridRecallAndRecommendation:
    """Verify hybrid queries: recall past book AND introduce verified new recommendation."""

    @pytest.mark.asyncio
    async def test_hybrid_query_with_past_history_distinguishes_past_from_new(self):
        # 1. State with curated_books (newly fetched by curator) AND recommended_history (past book)
        state = {
            "messages": [HumanMessage(content="전에 추천한 책이 뭐였지? 그리고 비슷한 책도 추천해 줘")],
            "member_id": "test-user-uuid",
            "active_persona": "CAT",
            "librarian_name": None,
            "mode": "LIBRARIAN",
            "action": "chat",
            "curator_request": None,
            "curated_books": [
                {
                    "title": "어린 왕자",
                    "author": "앙투안 드 생텍쥐페리",
                    "publisher": "열린책들",
                    "isbn": "9788932917245",
                    "reason": "순수한 감각을 되살려주는 책",
                }
            ],
            "curator_attempted": True,
            "recommended_history": ["코스모스"],  # Genuine past book
            "target_unresolved": None,
        }
        res = await cat_node(cast(AgentState, state))
        ai_msg = str(res["messages"][0].content)

        # Must mention the past book as previously recommended
        assert "코스모스" in ai_msg
        # Must introduce the newly curated book with recommendation trigger
        assert "어린 왕자" in ai_msg
        assert "### 📖 어린 왕자" in ai_msg
        # Must NOT hallucinate '모순'
        assert "모순" not in ai_msg

    @pytest.mark.asyncio
    async def test_hybrid_query_without_past_history_honestly_states_unconfirmed(self):
        # 2. State where user asks to recall and recommend, but past history is empty
        state = {
            "messages": [HumanMessage(content="전에 추천한 책이 뭐였지? 그리고 비슷한 책도 추천해 줘")],
            "member_id": "test-user-uuid",
            "active_persona": "CAT",
            "librarian_name": None,
            "mode": "LIBRARIAN",
            "action": "chat",
            "curator_request": None,
            "curated_books": [
                {
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "publisher": "민음사",
                    "isbn": "9788937460449",
                    "reason": "참된 자아를 마주하는 책",
                }
            ],
            "curator_attempted": True,
            "recommended_history": [],  # Empty past history
            "target_unresolved": None,
        }
        res = await cat_node(cast(AgentState, state))
        ai_msg = str(res["messages"][0].content)

        # Must state honestly that past history cannot be confirmed
        assert "확인할 수 없" in ai_msg or "기록" in ai_msg
        # Must introduce the newly curated book
        assert "데미안" in ai_msg
        assert "### 📖 데미안" in ai_msg
        # Must NOT hallucinate '모순' as past book
        assert "모순" not in ai_msg

