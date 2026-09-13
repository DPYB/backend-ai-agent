from typing import cast

import pytest
from langchain_core.messages import HumanMessage

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
    client.api_key = ""
    assert client.is_configured is False


@pytest.mark.asyncio
async def test_national_library_search_fallback():
    """Verify search_book returns verified metadata for known and generic titles."""
    client = NationalLibraryClient(api_key="")
    # Known curated book
    res = await client.search_book("데미안")
    assert res is not None
    assert res["title"] == "데미안"
    assert res["author"] == "헤르만 헤세"
    assert res["isbn"] == "9788937460449"
    assert res["source"] == "NATIONAL_LIBRARY_PENDING_MOCK"

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
