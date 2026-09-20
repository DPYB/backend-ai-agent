"""Unit tests for LangGraph 8-Persona Handoff, Custom Name, and Summarizer Node."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.domain.graph.nodes import (
    cat_node,
    debate_critic_node,
    gecko_node,
    sea_slug_node,
    shoebill_node,
    summarizer_node,
)
from app.domain.graph.workflow import create_agent_graph
from app.domain.personas import (
    CAT_ID,
    DEBATE_CRITIC_ID,
    DEBATE_STORYTELLER_ID,
    GECKO_ID,
    SEA_SLUG_ID,
    SHOEBILL_ID,
)


@pytest.mark.asyncio
async def test_cat_node_generates_response():
    """Verify Cat node produces an AI response message (non-recommendation intent)."""
    # 추천 의도가 없는 순수 인사 메시지 → LLM 응답이 messages에 담겨야 함
    state = {
        "messages": [HumanMessage(content="안녕하세요 고양이 사서님!")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    result = await cat_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["active_persona"] == CAT_ID


@pytest.mark.asyncio
async def test_cat_node_delegates_read_intent_to_curator():
    """'읽고 싶어' 발화 시 curator_node로 선위임되어야 한다 (추천 카드 보장)."""
    state = {
        "messages": [HumanMessage(content="안녕하세요 고양이 사서님, 책 한 권 읽고 싶네요.")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
    }
    result = await cat_node(state)
    # '읽고 싶' 키워드 → curator_node 선위임이 올바른 동작
    assert "curator_request" in result, "읽고싶어 발화는 curator_node로 위임되어야 합니다"
    assert result["curator_request"] is not None


@pytest.mark.asyncio
async def test_cat_node_with_custom_librarian_name():
    """Verify Cat node accepts and uses user-defined custom librarian name."""
    state = {
        "messages": [HumanMessage(content="안녕 파랭아!")],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": "파랭이",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    result = await cat_node(state)
    assert result["active_persona"] == CAT_ID


@pytest.mark.asyncio
async def test_shoebill_node_generates_response():
    """Verify Shoebill node produces an AI response message."""
    state = {
        "messages": [HumanMessage(content="빠르게 핵심만 알려주세요!")],
        "member_id": "test-uuid",
        "active_persona": SHOEBILL_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    result = await shoebill_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["active_persona"] == SHOEBILL_ID


@pytest.mark.asyncio
async def test_sea_slug_and_gecko_nodes():
    """Verify Sea Slug and Gecko nodes produce AI responses."""
    state_slug = {
        "messages": [HumanMessage(content="마음이 차분해지는 시집을 보고 싶어요.")],
        "member_id": "test-uuid",
        "active_persona": SEA_SLUG_ID,
        "librarian_name": "누디",
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    res_slug = await sea_slug_node(state_slug)
    assert res_slug["active_persona"] == SEA_SLUG_ID

    state_gecko = {
        "messages": [HumanMessage(content="구석에 숨은 신선한 책 찾아줘!")],
        "member_id": "test-uuid",
        "active_persona": GECKO_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    res_gecko = await gecko_node(state_gecko)
    assert res_gecko["active_persona"] == GECKO_ID


@pytest.mark.asyncio
async def test_debate_critic_node_generates_response():
    """Verify Debate Critic node produces an AI response message."""
    state = {
        "messages": [HumanMessage(content="이 책의 결말에 대해 어떻게 생각하시나요?")],
        "member_id": "test-uuid",
        "active_persona": DEBATE_CRITIC_ID,
        "librarian_name": None,
        "mode": "DEBATE",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }
    result = await debate_critic_node(state)
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["active_persona"] == DEBATE_CRITIC_ID


@pytest.mark.asyncio
async def test_handoff_trigger_and_summarizer():
    """Verify session isolation and summarizer_node stripping tone to retain facts upon explicit handoff."""
    state = {
        "messages": [
            HumanMessage(content="1타 강사 슈빌로 바꿔주세요!"),
        ],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }

    # With rule-based _detect_switch_intent removed, node keeps its session isolated and relies on frontend tab switching
    rb_res = await cat_node(state)
    assert rb_res["active_persona"] == CAT_ID
    assert rb_res.get("handoff_target") is None
    assert rb_res.get("switch_suggestion") is None

    # When handoff_target is explicitly passed to summarizer_node (e.g. via tab switch / state transfer),
    # verify summarizer extracts factual context and sets active_persona
    state_for_summary = {
        "messages": state["messages"] + rb_res["messages"],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": SHOEBILL_ID,
    }

    summary_res = await summarizer_node(state_for_summary)
    assert summary_res["active_persona"] == SHOEBILL_ID
    assert summary_res["handoff_target"] is None
    assert summary_res["context_summary"] is not None


@pytest.mark.asyncio
async def test_graph_end_to_end_invocation():
    """Verify LangGraph compiled workflow invokes cleanly with 8-node configuration."""
    graph = create_agent_graph()
    initial_state = {
        "messages": [HumanMessage(content="반가워요, 서재에 어떤 책들이 있나요?")],
        "member_id": "test-uuid-1234",
        "active_persona": DEBATE_STORYTELLER_ID,
        "librarian_name": None,
        "mode": "DEBATE",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }

    final_state = await graph.ainvoke(initial_state)
    assert "messages" in final_state
    assert len(final_state["messages"]) >= 2
    last_msg = final_state["messages"][-1]
    assert isinstance(last_msg, AIMessage)


@pytest.mark.asyncio
async def test_no_switch_intent_on_casual_mention_without_explicit_switch():
    """Verify that merely mentioning a colleague or creature without '바꿔/변경' does NOT trigger switch_suggestion."""
    state = {
        "messages": [
            HumanMessage(content="도마뱀이나 황새가 나오는 동물 동화책 추천해줘!"),
        ],
        "member_id": "test-uuid",
        "active_persona": CAT_ID,
        "librarian_name": None,
        "mode": "LIBRARIAN",
        "switch_suggestion": None,
        "context_summary": None,
        "handoff_target": None,
    }

    res = await cat_node(state)
    # Should NOT trigger switch or handoff because user didn't ask to switch librarian
    assert res.get("handoff_target") is None
    assert res.get("switch_suggestion") is None


def test_sanitize_persona_output_strips_fake_cards_when_curated_absent():
    """Verify that fake card UI markers and arbitrary headings are stripped when curated_books is None."""
    from app.domain.graph.nodes import _sanitize_persona_output

    raw_ai_text = (
        "마음이 많이 복잡하셨겠어요. 따뜻한 책을 추천해 드릴게요.\n\n"
        "### 📖 아무 책이나 지어내기\n"
        "💡 추천 이유: 마음이 따뜻해집니다.\n"
        "👤 저자: 아무개 작가\n"
        "등록 ➔ 지금 등록하기\n"
        "📖\n"
        "이 책을 천천히 읽어보세요."
    )
    cleaned = _sanitize_persona_output(raw_ai_text, curated_books=None)

    assert "### 📖 아무 책이나 지어내기" not in cleaned
    assert "💡 추천 이유" not in cleaned
    assert "👤 저자" not in cleaned
    assert "등록 ➔" not in cleaned
    assert "마음이 많이 복잡하셨겠어요" in cleaned
    assert "이 책을 천천히 읽어보세요" in cleaned


def test_sanitize_persona_output_preserves_verified_headings_when_curated_present():
    """Verify that only verified book titles are preserved under '### 📖' headings."""
    from app.domain.graph.nodes import _sanitize_persona_output

    curated_books = [
        {"title": "달러구트 꿈 백화점", "author": "이미예", "isbn": "9791165341909"},
    ]
    raw_ai_text = (
        "엄선해 드린 책입니다.\n\n"
        "### 📖 달러구트 꿈 백화점\n"
        "잠든 동안에만 찾아갈 수 있는 꿈의 상점 이야기예요.\n\n"
        "### 📖 가짜로 꾸며낸 책 제목\n"
        "이 책은 가짜입니다."
    )
    cleaned = _sanitize_persona_output(raw_ai_text, curated_books=curated_books)

    assert "### 📖 달러구트 꿈 백화점" in cleaned
    assert "잠든 동안에만 찾아갈 수 있는 꿈의 상점 이야기예요" in cleaned
    assert "### 📖 가짜로 꾸며낸 책 제목" not in cleaned


def test_is_delayed_curation_promise():
    """Verify detection of delayed curation promise markers."""
    from app.domain.graph.nodes import _is_delayed_curation_promise

    assert _is_delayed_curation_promise("내가 멋진 책을 골라올게! 잠시만 기다려줘.") is True
    assert _is_delayed_curation_promise("전문 큐레이터에게 부탁해 볼게.") is True
    assert _is_delayed_curation_promise("시간 있으면 이야기하자.") is False
    assert _is_delayed_curation_promise("이 책은 정말 감동적인 이야기란다.") is False
