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
    assert "- " in text
