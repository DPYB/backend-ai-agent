"""Unit tests for session security, UUID validation, and member-level namespace partitioning.

Verifies:
1. Two different authenticated members sending the exact same UUID session_id receive isolated sessions:
   - Member A: {member_a}:{uuid}:{persona}
   - Member B: {member_b}:{uuid}:{persona}
   - Redis session histories are completely isolated, preventing room eavesdropping.
2. In production mode (APP_ENV != 'test'/'development'), non-UUID session_id is rejected with HTTP 422.
3. Conclude background task saves debate insight under the partitioned session_id.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.api import router
from app.core.config import settings
from app.infrastructure.db.repository import get_agent_vector_repository
from app.infrastructure.redis_session import get_redis_session_manager
from app.main import app


@pytest.fixture(autouse=True)
def mock_graph_ainvoke(monkeypatch: pytest.MonkeyPatch):
    """Narrow mock on LangGraph execution to isolate session security & schema tests from external LLM I/O."""

    async def _mock_ainvoke(initial_state, config=None):
        action = initial_state.get("action")
        is_conclude = action == "conclude"
        return {
            **initial_state,
            "messages": [
                *initial_state.get("messages", []),
                AIMessage(content="세션 격리 테스트를 위한 모킹 응답입니다."),
            ],
            "active_persona": initial_state.get("active_persona", "CAT"),
            "switch_suggestion": None,
            "curated_books": None,
            "signals": initial_state.get("signals"),
            "is_concluded": is_conclude,
            "debate_summary": "요약된 토론 내용입니다." if is_conclude else None,
        }

    mock = AsyncMock(side_effect=_mock_ainvoke)
    monkeypatch.setattr(router._graph, "ainvoke", mock)
    return mock


@pytest.mark.asyncio
async def test_cross_member_same_uuid_session_isolation(mock_graph_ainvoke: AsyncMock):
    """Verify two different members sending the same session UUID are partitioned by member namespace."""
    transport = ASGITransport(app=app)
    session_mgr = get_redis_session_manager()

    member_a = "11111111-1111-4111-a111-111111111111"
    member_b = "22222222-2222-4222-a222-222222222222"
    shared_uuid = str(uuid4())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Member A chats with CAT persona
        payload_a: Dict[str, Any] = {
            "session_id": shared_uuid,
            "member_id": member_a,
            "mode": "LIBRARIAN",
            "persona": "CAT",
            "message": "회원 A의 비밀 독서 기록입니다.",
        }
        res_a = await client.post("/api/v1/chat", json=payload_a)
        assert res_a.status_code == 200
        data_a = res_a.json()

        # Session ID must be prefixed with Member A's ID
        expected_session_a = f"{member_a}:{shared_uuid}:CAT"
        assert data_a["session_id"] == expected_session_a

        # 2. Member B chats with CAT persona using the EXACT same UUID
        payload_b: Dict[str, Any] = {
            "session_id": shared_uuid,
            "member_id": member_b,
            "mode": "LIBRARIAN",
            "persona": "CAT",
            "message": "회원 B의 독립된 독서 기록입니다.",
        }
        res_b = await client.post("/api/v1/chat", json=payload_b)
        assert res_b.status_code == 200
        data_b = res_b.json()

        # Session ID must be prefixed with Member B's ID
        expected_session_b = f"{member_b}:{shared_uuid}:CAT"
        assert data_b["session_id"] == expected_session_b
        assert data_b["session_id"] != data_a["session_id"]

        # 3. Verify Redis stored state for Member A and Member B are isolated
        redis_session_a = await session_mgr.get_session(expected_session_a)
        redis_session_b = await session_mgr.get_session(expected_session_b)

        assert redis_session_a is not None
        assert redis_session_b is not None

        # Inspect messages in Member A's session
        msgs_a = redis_session_a.get("messages", [])
        msgs_b = redis_session_b.get("messages", [])

        # Ensure Member A's secret does not appear in Member B's session
        assert any("회원 A의 비밀 독서 기록입니다." in m.get("content", "") for m in msgs_a)
        assert not any("회원 A의 비밀 독서 기록입니다." in m.get("content", "") for m in msgs_b)

        # Ensure Member B's secret does not appear in Member A's session
        assert any("회원 B의 독립된 독서 기록입니다." in m.get("content", "") for m in msgs_b)
        assert not any("회원 B의 독립된 독서 기록입니다." in m.get("content", "") for m in msgs_a)

        # 4. Verify LangGraph received the correctly partitioned session IDs in thread_id config
        assert mock_graph_ainvoke.call_count == 2
        call_config_a = mock_graph_ainvoke.call_args_list[0].kwargs.get("config", {})
        call_config_b = mock_graph_ainvoke.call_args_list[1].kwargs.get("config", {})
        assert call_config_a.get("configurable", {}).get("thread_id") == expected_session_a
        assert call_config_b.get("configurable", {}).get("thread_id") == expected_session_b


@pytest.mark.asyncio
async def test_uuid_validation_in_production(monkeypatch: pytest.MonkeyPatch):
    """Verify that non-UUID session_id is rejected with 422 in production environment."""
    monkeypatch.setattr(settings, "app_env", "production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid UUID should succeed
        valid_uuid = str(uuid4())
        res_valid = await client.post(
            "/api/v1/chat",
            json={
                "session_id": valid_uuid,
                "message": "안녕",
                "mode": "LIBRARIAN",
                "persona": "CAT",
            },
        )
        assert res_valid.status_code == 200

        # Non-UUID string should be rejected with 422
        res_invalid = await client.post(
            "/api/v1/chat",
            json={
                "session_id": "malicious-injection-key-1234",
                "message": "안녕",
                "mode": "LIBRARIAN",
                "persona": "CAT",
            },
        )
        assert res_invalid.status_code == 422
        err_detail = res_invalid.json().get("detail", [])
        assert any("UUID 형식" in str(e) for e in err_detail)


@pytest.mark.asyncio
async def test_conclude_debate_insight_uses_partitioned_session():
    """Verify conclude debate saves insight with the full member-partitioned session ID."""
    transport = ASGITransport(app=app)
    member_id = "33333333-3333-4333-a333-333333333333"
    session_uuid = str(uuid4())
    repo = get_agent_vector_repository()

    # Clear prior mock insights
    repo._mock_debate_insights.clear()

    payload = {
        "message": "오늘 토론은 여기서 정리하자.",
        "mode": "DEBATE",
        "persona": "DEBATE_CRITIC",
        "action": "conclude",
        "member_id": member_id,
        "session_id": session_uuid,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_concluded"] is True

        expected_session = f"{member_id}:{session_uuid}:DEBATE_CRITIC"
    # Verify background repository save
    matching = [d for d in repo._mock_debate_insights if str(d.get("member_id")) == member_id]
    assert len(matching) >= 1
    saved = matching[-1]
    assert saved["session_id"] == expected_session
    assert saved["persona_id"] == "DEBATE_CRITIC"


@pytest.mark.asyncio
async def test_composite_session_id_backward_compatibility(monkeypatch: pytest.MonkeyPatch):
    """Verify that clients sending composite session_ids (e.g. from previous responses) succeed and normalize to UUID."""
    monkeypatch.setattr(settings, "app_env", "production")

    transport = ASGITransport(app=app)
    member_id = "44444444-4444-4444-a444-444444444444"
    session_uuid = str(uuid4())
    composite_sid = f"{member_id}:{session_uuid}:CAT"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sending composite session_id should NOT throw 422 in production
        res = await client.post(
            "/api/v1/chat",
            json={
                "session_id": composite_sid,
                "member_id": member_id,
                "message": "안녕하세요 블루 사서님",
                "mode": "LIBRARIAN",
                "persona": "CAT",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == f"{member_id}:{session_uuid}:CAT"
