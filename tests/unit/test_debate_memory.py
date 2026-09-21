"""Unit tests for dedicated debate memory (agent.debate_insights) and recall tool."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.memory.debate_memory_tool import search_debate_memory
from app.infrastructure.db.models import DebateInsight
from app.infrastructure.db.repository import AgentVectorRepository, get_agent_vector_repository
from app.main import app


def test_debate_insight_model_schema():
    """Verify DebateInsight ORM model belongs strictly to schema 'agent'."""
    assert DebateInsight.__table_args__ == {"schema": "agent"}
    assert DebateInsight.__tablename__ == "debate_insights"

    insight = DebateInsight(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        session_id="test-session-001",
        book_title="데미안",
        persona_id="DEBATE_CRITIC",
        summary="알을 깨고 나오는 싱클레어의 내면 투쟁과 아프락사스를 향한 자기 구원",
        topic="선과 악의 이분법 극복",
    )
    data = insight.to_dict()
    assert data["book_title"] == "데미안"
    assert data["persona_id"] == "DEBATE_CRITIC"
    assert data["topic"] == "선과 악의 이분법 극복"
    assert "자기 구원" in data["summary"]


@pytest.mark.asyncio
async def test_agent_vector_repository_debate_insights_isolation():
    """Verify AgentVectorRepository debate insight storage and member_id partitioning."""
    repo = AgentVectorRepository()

    member_1 = str(uuid.uuid4())
    member_2 = str(uuid.uuid4())

    dummy_embedding = [0.1] * 768

    # Insert insight for member 1
    await repo.insert_debate_insight(
        member_id=member_1,
        session_id="session-1",
        book_title="데미안",
        persona_id="DEBATE_CRITIC",
        summary="자아 성장의 투쟁과 아프락사스에 관한 토론 요약",
        topic="내면의 성장",
        embedding=dummy_embedding,
    )

    # Insert insight for member 2
    await repo.insert_debate_insight(
        member_id=member_2,
        session_id="session-2",
        book_title="코스모스",
        persona_id="DEBATE_STORYTELLER",
        summary="우주와 인류의 역사적 교훈에 관한 토론 요약",
        topic="우주 속 인류",
        embedding=dummy_embedding,
    )

    # Search for member 1
    results_1 = await repo.search_member_debate_insights(
        member_id=member_1,
        query_embedding=dummy_embedding,
        match_threshold=0.0,
    )
    assert len(results_1) == 1
    assert results_1[0]["book_title"] == "데미안"
    assert results_1[0]["member_id"] == member_1

    # Search for member 2
    results_2 = await repo.search_member_debate_insights(
        member_id=member_2,
        query_embedding=dummy_embedding,
        match_threshold=0.0,
    )
    assert len(results_2) == 1
    assert results_2[0]["book_title"] == "코스모스"
    assert results_2[0]["member_id"] == member_2


@pytest.mark.asyncio
async def test_search_debate_memory_tool_guest_bypass():
    """Verify guest users get an immediate bypass response with zero DB queries."""
    for guest_id in [None, "guest", "None", "guest-1234"]:
        res = await search_debate_memory.ainvoke(
            {"member_id": guest_id or "", "query": "데미안 토론 내용"}
        )
        assert "게스트" in res
        assert "기억이 없습니다" in res


@pytest.mark.asyncio
async def test_search_debate_memory_tool_success_and_formatting():
    """Verify tool returns nicely formatted markdown text when insights match."""
    member_id = str(uuid.uuid4())
    repo = get_agent_vector_repository()

    await repo.insert_debate_insight(
        member_id=member_id,
        session_id="session-demian",
        book_title="데미안",
        persona_id="DEBATE_CRITIC",
        summary="두 세계의 충돌과 진정한 자아를 찾는 용기",
        topic="자아 탐색",
        embedding=[0.05] * 768,
    )

    res = await search_debate_memory.ainvoke({"member_id": member_id, "query": "데미안"})
    assert "도서: <데미안>" in res
    assert "토론 파트너: DEBATE_CRITIC" in res
    assert "핵심 논제: 자아 탐색" in res
    assert "두 세계의 충돌" in res


@pytest.mark.asyncio
async def test_search_debate_memory_tool_not_found():
    """Verify helpful not-found message when no past insights exist for the user."""
    member_id = str(uuid.uuid4())
    res = await search_debate_memory.ainvoke({"member_id": member_id, "query": "존재하지않는책"})
    assert f"사용자({member_id})의 과거 토론 기록" in res
    assert "찾지 못했습니다" in res


@pytest.mark.asyncio
async def test_vectorize_debate_insight_api_endpoint():
    """Verify POST /api/v1/memory/debate-insights vectorizes and returns 201 Created."""
    transport = ASGITransport(app=app)
    payload = {
        "member_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "session-test-endpoint",
        "book_title": "멋진 신세계",
        "persona_id": "DEBATE_CRITIC",
        "summary": "쾌락과 통제가 지배하는 디스토피아에서 진정한 인간 존엄성의 가치를 고찰함.",
        "topic": "디스토피아와 자유의지",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/memory/debate-insights", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["insight_id"] is not None
        assert "성공적으로 벡터화" in data["message"]


@pytest.mark.asyncio
async def test_chat_conclude_auto_saves_debate_insight_in_background():
    """Verify concluding a debate automatically vectors and saves insight in background."""
    transport = ASGITransport(app=app)
    member_id = "550e8400-e29b-41d4-a716-446655440000"
    repo = get_agent_vector_repository()

    # Clear prior mock insights for this test
    repo._mock_debate_insights.clear()

    payload = {
        "message": "오늘 토론은 여기까지 하고 마무리하자.",
        "mode": "DEBATE",
        "persona": "DEBATE_CRITIC",
        "action": "conclude",
        "member_id": member_id,
        "session_id": "conclude-auto-save-session",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_concluded"] is True
        assert data["debate_summary"] is not None

    # Verify that background task inserted the insight into repository
    matching = [d for d in repo._mock_debate_insights if str(d.get("member_id")) == member_id]
    assert len(matching) >= 1
    saved = matching[-1]
    assert saved["persona_id"] == "DEBATE_CRITIC"
    assert saved["summary"] == data["debate_summary"]
    assert saved["session_id"] == data["session_id"]
    assert saved["session_id"] == f"{member_id}:conclude-auto-save-session:DEBATE_CRITIC"
