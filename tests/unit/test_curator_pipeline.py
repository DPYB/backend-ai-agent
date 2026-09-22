from typing import cast

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.domain.graph.curator_node import book_curator_node
from app.domain.graph.state import AgentState
from app.domain.graph.workflow import create_agent_graph
from app.infrastructure.national_library_client import (
    NationalLibraryClient,
    get_national_library_client,
)


def test_national_library_client_fallback_mode():
    """Verify NationalLibraryClient returns deterministic verified books during pending approval."""
    client = get_national_library_client()
    # When unconfigured or pending approval
    client.cert_key = ""
    assert client.is_configured is False


@pytest.mark.asyncio
async def test_national_library_search_fallback():
    """Verify search_book returns verified metadata for known and generic titles."""
    client = NationalLibraryClient(cert_key="")
    # Known curated book
    res = await client.search_book("데미안")
    assert res is not None
    assert res["title"] == "데미안"
    assert res["author"] == "헤르만 헤세"
    assert res["isbn"] == "9788937460449"
    assert res["source"] == "NATIONAL_LIBRARY_FALLBACK_CATALOG"

    # Generic book
    res_generic = await client.search_book("임의의 소설")
    assert res_generic is not None
    assert "임의의 소설" in res_generic["title"]
    assert res_generic["isbn"] != ""


@pytest.mark.asyncio
async def test_book_curator_node_execution():
    """Verify book_curator_node extracts candidates and verifies them via bibliography client."""
    state = {
        "messages": [HumanMessage(content="비 오는 날 가볍게 읽기 좋은 에세이 추천해줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "비 오는 날 가볍게 읽기 좋은 에세이 추천해줘",
        "curated_books": None,
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    curated = result["curated_books"]
    assert len(curated) >= 1
    for book in curated:
        assert "title" in book
        assert "author" in book
        assert "isbn" in book
        assert book["verified"] is True
    assert result["curator_request"] is None


@pytest.mark.asyncio
async def test_full_graph_recommendation_handoff():
    """Verify graph end-to-end execution when user requests book recommendation."""
    graph = create_agent_graph()
    state = {
        "messages": [HumanMessage(content="기분이 울적한데 위로가 되는 책 한 권만 추천해줄래?")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
    }

    final_state = await graph.ainvoke(state)
    assert "messages" in final_state
    last_msg = str(final_state["messages"][-1].content)
    assert len(last_msg) > 0
    # Final reply delivered through active persona
    assert final_state["active_persona"] == "CAT"


@pytest.mark.asyncio
async def test_weather_client_fallback():
    """Verify WeatherClient gracefully returns None or formatted string without crashing."""
    from app.infrastructure.weather_client import get_weather_client

    client = get_weather_client()
    # Test valid coordinates (Seoul City Hall)
    weather = await client.get_current_weather(37.5665, 126.9780)
    # Open-Meteo is free and accessible; weather is string if online, or None if timeout/offline
    assert weather is None or isinstance(weather, str)


@pytest.mark.asyncio
async def test_recommendation_intent_delegation_keywords():
    """Verify various recommendation queries like '뭘 읽으면 좋을까' delegate directly to curator_node."""
    from app.domain.graph.nodes import cat_node

    queries = [
        "뭘 읽으면 좋을까",
        "오늘 같은 날 무슨 책이 좋을까?",
        "따뜻한 위로가 되는 책 좀 추천해줘",
        "도서 추천 부탁해",
        "가볍게 볼 만한 책 하나 골라줘",
        # 읽고 싶다 계열 (사용자 보고 버그 회귀 방지)
        "읽고싶어",
        "요즘 읽고 싶어서",
        "이 책 읽어보고 싶어",
        "읽어볼 만한 거 알려줘",
        "재밌는 책 있어?",
        "좋은 책 없어?",
        "뭐 읽지?",
    ]

    for q in queries:
        state = {
            "messages": [HumanMessage(content=q)],
            "member_id": "test-member",
            "active_persona": "CAT",
            "librarian_name": "블루",
            "mode": "LIBRARIAN",
            "switch_suggestion": None,
            "context_summary": None,
            "handoff_target": None,
            "curator_request": None,
            "curated_books": None,
        }
        res = await cat_node(cast(AgentState, state))
        assert "curator_request" in res, f"Query '{q}' should delegate to curator_node"
        assert res["curator_request"] == q


@pytest.mark.asyncio
async def test_curated_books_markdown_heading_instruction(monkeypatch):
    """Verify system prompt contains ### 📖 title markdown heading instruction when curated_books exist."""
    from app.domain.graph.nodes import cat_node

    captured_prompt = None

    class DummyLLM:
        async def ainvoke(self, messages, config=None):
            nonlocal captured_prompt
            captured_prompt = messages[0].content
            return AIMessage(content="### 📖 불편한 편의점\n이 책을 추천합니다냥.")

    monkeypatch.setattr("app.domain.graph.nodes._get_llm", lambda tools=None: DummyLLM())

    state = {
        "messages": [HumanMessage(content="뭘 읽으면 좋을까")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": [
            {
                "title": "불편한 편의점",
                "author": "김호연",
                "publisher": "나무옆의자",
                "isbn": "9791161571188",
                "reason": "마음이 따뜻해지는 소설입니다.",
            }
        ],
    }

    res = await cat_node(cast(AgentState, state))
    assert "messages" in res
    assert captured_prompt is not None
    assert "### 📖 도서명" in captured_prompt
    assert "### 📖 불편한 편의점" in res["messages"][0].content


def test_curator_structured_output_schema():
    """Verify BookCandidate and CuratorResponse Pydantic validation."""
    from app.domain.graph.curator_node import BookCandidate, CuratorResponse

    candidate = BookCandidate(
        title="소년이 온다",
        author="한강",
        reason="역사의 아픔을 위무하는 깊은 문장",
        era="recent",
    )
    assert candidate.title == "소년이 온다"
    assert candidate.era == "recent"

    response = CuratorResponse(
        recommendations=[
            candidate,
            BookCandidate(
                title="데미안",
                author="헤르만 헤세",
                reason="불멸의 고전",
                era="classic",
            ),
        ]
    )
    assert len(response.recommendations) == 2
    dumped = response.model_dump()
    assert "recommendations" in dumped
    assert len(dumped["recommendations"]) == 2


@pytest.mark.asyncio
async def test_curator_random_elegant_fallback():
    """Verify _get_random_elegant_fallback returns 2 masterpieces with honest fallback reasons."""
    from app.domain.graph.curator_node import _get_random_elegant_fallback

    fallback = _get_random_elegant_fallback()
    assert len(fallback) == 2
    for b in fallback:
        assert "title" in b
        assert "author" in b
        assert "reason" in b
        assert "era" in b
        assert "시스템 지연으로" in b["reason"] or "화제작" in b["reason"] or "명작" in b["reason"]


@pytest.mark.asyncio
async def test_trending_books_scraper_and_caching():
    """Verify parse_yes24_bestseller_html and fetch_and_cache_trending_books."""
    from app.infrastructure.redis_session import get_redis_session_manager
    from app.infrastructure.trending_books import (
        REDIS_TRENDING_BOOKS_KEY,
        fetch_and_cache_trending_books,
        get_trending_books_text,
        parse_yes24_bestseller_html,
    )

    # 1. Test HTML parsing with realistic Yes24 SSR snippet
    sample_html = """
    <ul id="yesBestList">
      <li>
        <div class="goods_info">
          <a class="gd_name">세네카, 오늘을 빼앗기고 있는 당신에게</a>
          <span class="info_auth">
            <a>세네카</a> 저 / <a>하와이 대저택</a> 편역
          </span>
          <span class="info_pub">논픽션</span>
        </div>
      </li>
      <li>
        <div class="goods_info">
          <a class="gd_name">2026 한국사능력검정시험 기출문제집</a>
          <span class="info_auth"><a>최태성</a></span>
          <span class="info_pub">이투스북</span>
        </div>
      </li>
    </ul>
    """
    parsed = parse_yes24_bestseller_html(sample_html)
    assert len(parsed) == 2
    assert parsed[0]["title"] == "세네카, 오늘을 빼앗기고 있는 당신에게"
    assert "세네카" in parsed[0]["author"]
    assert parsed[0]["publisher"] == "논픽션"
    # Exam book is moved after general books
    assert parsed[1]["title"] == "2026 한국사능력검정시험 기출문제집"

    # 2. Test live or emergency fallback fetch & cache
    books = await fetch_and_cache_trending_books()
    assert len(books) > 0

    redis_mgr = get_redis_session_manager()
    cached = await redis_mgr.get(REDIS_TRENDING_BOOKS_KEY)
    assert cached is not None

    text = await get_trending_books_text(limit=10)
    assert len(text) > 0
    assert "- (" in text or "- " in text


def test_is_curatable_book_filter():
    """Verify is_curatable_book correctly filters out exam/job manual/comics noise."""
    from app.infrastructure.national_library_client import is_curatable_book

    # Negative cases (should be filtered out)
    assert not is_curatable_book("교사를 지키는 단단한 생활지도 : 실전 사례 100", "", "테크빌교육")
    assert not is_curatable_book("2026 한국사능력검정시험 기출문제집", "최태성", "이투스북")
    assert not is_curatable_book("2027 황철곤 행정학 패스프레소", "황철곤", "")
    assert not is_curatable_book("ETS 토익 정기시험 기출문제집 1000", "ETS", "YBM")
    assert not is_curatable_book("흔한남매 23", "흔한남매", "흔한컴퍼니")
    assert not is_curatable_book("에그박사 19", "에그박사", "")
    assert not is_curatable_book("멜로우TV 팀 나빠 추리 탐정단 1", "멜로우 TV", "")
    assert not is_curatable_book("포스트카드북 합본판", "", "")

    # Positive cases (should pass)
    assert is_curatable_book("세네카, 오늘을 빼앗기고 있는 당신에게", "세네카", "논픽션")
    assert is_curatable_book("모순", "양귀자", "쓰다")
    assert is_curatable_book("그랬다고 적었다", "김애란", "문학동네")
    assert is_curatable_book("마음의 어휘력", "조아란", "페이지2북스")
    assert is_curatable_book("데미안", "헤르만 헤세", "민음사")


@pytest.mark.asyncio
async def test_trending_books_text_grouped_by_kdc_and_rank():
    """Verify get_trending_books_text preserves ranks and groups books into KDC categories."""
    from app.infrastructure.trending_books import get_trending_books_text

    text = await get_trending_books_text(limit=20)
    assert "[오늘의 화제작 오픈북 (실제 종합 베스트셀러 순위)]" in text
    assert "종합 " in text
    assert "위)" in text
    # Checks that at least one KDC category heading exists
    assert any(
        h in text
        for h in [
            "📚 문학 / 소설 / 에세이:",
            "🌱 인문 / 철학 / 심리:",
            "💡 교양 / 사회 / 과학 / 라이프:",
        ]
    )


@pytest.mark.asyncio
async def test_curator_node_anti_repeat_history_and_sliding_window():
    """Verify book_curator_node collects history, enforces sliding window cap, and updates state."""
    from app.domain.graph.curator_node import MAX_RECOMMENDED_HISTORY, book_curator_node

    # 1. State with existing recommended_history and assistant message containing book headings
    state = {
        "messages": [
            HumanMessage(content="책 하나 추천해줘"),
            AIMessage(content="첫 번째 책입니다.\n### 📖 과거추천도서A\n좋은 책입니다."),
        ],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "책 추천해줘",
        "curated_books": None,
        "recommended_history": [f"이전책_{i}" for i in range(12)],  # Exceeds cap of 10
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "recommended_history" in result
    rec_history = result["recommended_history"]

    # History must be capped at MAX_RECOMMENDED_HISTORY
    assert len(rec_history) <= MAX_RECOMMENDED_HISTORY
    # Newly curated books must be added to history
    curated = result["curated_books"]
    for b in curated:
        assert b["title"] in rec_history


@pytest.mark.asyncio
async def test_two_turn_continuous_chat_persists_recommended_history_across_turns():
    """Verify that in a 2-turn conversation with the same session_id:
    Turn 1: Recommended books are persisted to Redis session's recommended_history.
    Turn 2: The next request retrieves Turn 1 books from Redis, passes them to curator,
            and preserves them in the session history.
    """
    from httpx import ASGITransport, AsyncClient

    from app.infrastructure.redis_session import get_redis_session_manager
    from app.main import app

    session_mgr = get_redis_session_manager()
    session_id = "test-two-turn-integration-session"
    partitioned_key = f"test-member:{session_id}:CAT"

    # Clean up before testing
    await session_mgr.delete_session(partitioned_key)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Turn 1: First recommendation
        resp1 = await ac.post(
            "/api/v1/chat",
            json={
                "message": "책 추천해줘",
                "session_id": session_id,
                "persona": "CAT",
                "member_id": "test-member",
            },
            headers={"Authorization": "Bearer mock-token-test-member"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1.get("recommended_books", [])) > 0
        turn1_titles = [b["title"] for b in data1["recommended_books"]]

        # Check Redis persistence after Turn 1
        saved1 = await session_mgr.get_session(partitioned_key)
        assert saved1 is not None
        assert "recommended_history" in saved1
        assert len(saved1["recommended_history"]) > 0
        for t in turn1_titles:
            assert t in saved1["recommended_history"]

        # Turn 2: Second recommendation with the SAME session_id
        resp2 = await ac.post(
            "/api/v1/chat",
            json={
                "message": "다른 책도 추천해줘",
                "session_id": session_id,
                "persona": "CAT",
                "member_id": "test-member",
            },
            headers={"Authorization": "Bearer mock-token-test-member"},
        )
        assert resp2.status_code == 200

        # Check Redis persistence after Turn 2: Turn 1 titles must still be preserved
        saved2 = await session_mgr.get_session(partitioned_key)
        assert saved2 is not None
        assert "recommended_history" in saved2
        for t in turn1_titles:
            assert t in saved2["recommended_history"]


@pytest.mark.asyncio
async def test_curator_node_negative_constraint_prompt_content():
    """Verify that book_curator_node constructs the negative constraint section with previous turn books."""
    from app.domain.graph.curator_node import book_curator_node

    turn1_books = ["세네카, 오늘을 빼앗기고 있는 당신에게", "데미안"]
    state = {
        "messages": [
            HumanMessage(content="책 추천해줘"),
            AIMessage(
                content="추천합니다냥!\n### 📖 세네카, 오늘을 빼앗기고 있는 당신에게\n### 📖 데미안"
            ),
            HumanMessage(content="다른 책도 추천해줘"),
        ],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "다른 책도 추천해줘",
        "curated_books": None,
        "recommended_history": turn1_books,
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "recommended_history" in result
    # Turn 1 books must be preserved in result's recommended_history
    for t in turn1_books:
        assert t in result["recommended_history"]


@pytest.mark.asyncio
async def test_targeted_book_curation_metadata_completion():
    """Verify that when a user requests a specific book (e.g. '프로젝트 헤일메리 추천해줘'),

    the curator_node directly verifies it with the National Library and returns
    full metadata (ISBN, page_count, genre, cover_url) as the #1 priority recommendation.
    """
    from app.domain.graph.curator_node import book_curator_node

    state = {
        "messages": [
            HumanMessage(content="프로젝트 헤일메리 추천해줘"),
        ],
        "member_id": "test-member-hailmary",
        "active_persona": "SHOEBILL",
        "librarian_name": "슈빌",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "프로젝트 헤일메리 추천해줘",
        "curated_books": None,
        "recommended_history": [],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    curated = result["curated_books"]
    assert len(curated) >= 1

    # #1 priority book must be the targeted book
    target = curated[0]
    assert "프로젝트 헤일메리" in target["title"]
    assert "앤디 위어" in target["author"] or "Andy Weir" in target["author"]
    assert len(target.get("isbn", "")) == 13
    assert target.get("isbn", "").startswith("97889")
    assert target.get("page_count") is not None and target.get("page_count") > 500
    assert target.get("genre") == "LITERATURE"
    assert target.get("isbn") in target.get("cover_url", "")
    assert target.get("verified") is True


@pytest.mark.asyncio
async def test_meta_recommendation_query_not_converted_to_fake_book():
    """Verify that queries like '이전에 추천받은 도서랑 비슷한 도서 추천해달라고 하면'
    are not parsed as book titles and never produce fake book cards.
    """
    from app.domain.graph.curator_node import book_curator_node

    state = {
        "messages": [
            HumanMessage(content="이전에 추천받은 도서랑 비슷한 도서 추천해달라고 하면"),
        ],
        "member_id": "test-member-meta",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "이전에 추천받은 도서랑 비슷한 도서 추천해달라고 하면",
        "curated_books": None,
        "recommended_history": ["데미안"],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    curated = result["curated_books"]
    assert len(curated) >= 1

    # None of the curated books should have sentences/garbage as title
    for book in curated:
        title = book["title"]
        assert "이전에" not in title
        assert "비슷한" not in title
        assert "추천" not in title
        assert "해달라고" not in title
        assert book["isbn"] != "9791100000000"
        if not book.get("fallback"):
            assert book["verified"] is True
        else:
            # Enriched fallback books now have 100% real biblio metadata (ISBN, verified: True)
            assert book["verified"] is True
            assert len(book["isbn"]) == 13
            assert book["cover_url"].startswith("http")


@pytest.mark.parametrize(
    "query,expected_target,must_not_contain",
    [
        ("다른 책 추천해줘", None, ["다른 책"]),
        ("비 오는 날 읽을 책", None, ["비 오는 날 읽을"]),
        ("이전에 추천받은 책이랑 비슷한 도서 추천해줘", None, ["이전에 추천받은"]),
        ("《데미안》 등록해줘", "데미안", []),
        ("프로젝트 헤일메리 추천해줘", "프로젝트 헤일메리", []),
    ],
)
@pytest.mark.asyncio
async def test_curator_query_case_matrix(query, expected_target, must_not_contain):
    """Case Matrix test: verify various user intents produce exact 2 books,
    identify target_title only when explicitly targeted, and never leak query sentences as book titles.
    """
    from app.domain.graph.curator_node import book_curator_node

    state = {
        "messages": [HumanMessage(content=query)],
        "member_id": "test-case-matrix",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": query,
        "curated_books": None,
        "recommended_history": ["코스모스"],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    books = result["curated_books"]
    assert len(books) == 2, f"Query '{query}' must yield exactly 2 books"

    # If target is expected, #1 priority must match
    if expected_target:
        assert expected_target in books[0]["title"]
        assert books[0]["verified"] is True
        assert len(books[0]["isbn"]) == 13

    # Ensure no garbage sentence text is treated as book title
    for b in books:
        for forbidden in must_not_contain:
            assert forbidden not in b["title"]


@pytest.mark.asyncio
async def test_assemble_curated_books_guarantees_exact_two_books_and_enriched_fallback():
    """Verify assemble_curated_books guarantees exactly 2 books and enriches fallback books with full metadata."""
    from app.domain.graph.curator_node import assemble_curated_books

    # Case A: 0 verified books -> 2 fallback books enriched with 100% real metadata (ISBN, cover, page)
    assembled_a = await assemble_curated_books(targeted=None, verified=[], recommended_history=[])
    assert len(assembled_a) == 2
    for b in assembled_a:
        assert b["verified"] is True
        assert len(b["isbn"]) == 13
        assert b["cover_url"].startswith("http")
        assert b["page_count"] is not None and b["page_count"] > 0
        assert b["publisher"] != ""
        assert b["genre"] is not None
        assert b.get("fallback") is True

    # Case B: 1 targeted book + 0 verified -> fills 1 fallback book with full metadata (total 2)
    targeted = {
        "title": "프로젝트 헤일메리",
        "author": "앤디 위어",
        "isbn": "9788925588735",
        "verified": True,
        "era": "targeted",
    }
    assembled_b = await assemble_curated_books(
        targeted=targeted, verified=[], recommended_history=[]
    )
    assert len(assembled_b) == 2
    assert assembled_b[0]["title"] == "프로젝트 헤일메리"
    assert assembled_b[0]["verified"] is True
    assert assembled_b[1]["verified"] is True
    assert len(assembled_b[1]["isbn"]) == 13
    assert assembled_b[1]["cover_url"].startswith("http")
    assert assembled_b[1].get("fallback") is True


def test_is_similar_title():
    """Verify _is_similar_title correctly matches titles with subtitle or formatting differences."""
    from app.domain.graph.curator_node import _is_similar_title

    # 1. Exact match
    assert _is_similar_title("프로젝트 헤일메리", "프로젝트 헤일메리") is True
    # 2. Bracket edition / publisher tags
    assert _is_similar_title("데미안", "데미안 (민음사)") is True
    assert _is_similar_title("데미안", "데미안 [개정판]") is True
    # 3. Subtitle variations (colon / dash)
    assert _is_similar_title("데미안", "데미안 : 에밀 싱클레어의 청춘 이야기") is True
    assert (
        _is_similar_title(
            "세네카, 오늘을 빼앗기고 있는 당신에게", "세네카 오늘을 빼앗기고 있는 당신에게"
        )
        is True
    )
    # 4. Series prefix / suffix containment
    assert _is_similar_title("해리 포터와 마법사의 돌", "해리 포터 1 : 마법사의 돌") is True
    # 5. Negative cases
    assert _is_similar_title("완전 다른 책 제목", "전혀 무관한 소설") is False
    assert _is_similar_title("", "데미안") is False


@pytest.mark.asyncio
async def test_target_unresolved_returned_when_targeted_book_fails_verification(monkeypatch):
    """Verify that when target_title is identified but National Library verification fails,
    book_curator_node returns target_unresolved in the state.
    """
    from app.domain.graph.curator_node import book_curator_node

    # Mock resolve_targeted to return None for nonexistent book
    async def mock_resolve_targeted(target_title):
        return None

    monkeypatch.setattr("app.domain.graph.curator_node.resolve_targeted", mock_resolve_targeted)

    async def mock_generate_candidates(ctx, text):
        return "세상에없는가공의책12345", []

    monkeypatch.setattr(
        "app.domain.graph.curator_node.generate_candidates",
        mock_generate_candidates,
    )

    state = {
        "messages": [HumanMessage(content="세상에없는가공의책12345 등록해줘")],
        "member_id": "test-unresolved",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": "세상에없는가공의책12345 등록해줘",
        "curated_books": None,
        "recommended_history": [],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert result.get("target_unresolved") == "세상에없는가공의책12345"
    assert len(result["curated_books"]) == 2


@pytest.mark.asyncio
async def test_assemble_curated_books_deduplicates_against_recommended_history():
    """Verify assemble_curated_books filters out verified books that match recommended_history."""
    from app.domain.graph.curator_node import assemble_curated_books

    verified = [
        {
            "title": "데미안",
            "author": "헤르만 헤세",
            "isbn": "9788937460449",
            "verified": True,
        },
        {
            "title": "코스모스",
            "author": "칼 세이건",
            "isbn": "9788983711892",
            "verified": True,
        },
    ]
    # If "데미안" was recently recommended, it should be filtered out from verified list
    recommended_history = ["데미안"]
    assembled = await assemble_curated_books(
        targeted=None,
        verified=verified,
        recommended_history=recommended_history,
    )
    assert len(assembled) == 2
    # "데미안" must NOT be in assembled books
    assembled_titles = [b["title"] for b in assembled]
    assert "데미안" not in assembled_titles
    assert "코스모스" in assembled_titles


@pytest.mark.asyncio
async def test_persona_node_clears_target_unresolved_on_subsequent_turn(monkeypatch):
    """Verify that _run_persona_node clears target_unresolved in its return dict to prevent stale warnings."""
    from app.domain.graph.nodes import cat_node

    class DummyLLM:
        async def ainvoke(self, messages, config=None):
            return AIMessage(content="일반 대화 응답입니다냥.")

    monkeypatch.setattr("app.domain.graph.nodes._get_llm", lambda tools=None: DummyLLM())

    state = {
        "messages": [HumanMessage(content="오늘 날씨 어때?")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "target_unresolved": "이전턴에실패했던책",
    }

    result = await cat_node(cast(AgentState, state))
    assert result.get("target_unresolved") is None
