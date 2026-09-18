"""Unit and concurrency tests for Guest Mode and Dual Circuit Breaker.

Verifies:
1. Guest JWT claims extraction (sub, role, lack of name/email fallback)
2. Session partitioning (guest-uuid:persona)
3. Individual guest message limits (default 10) with graceful 200 OK fallbacks
4. Dual Circuit Breaker (RPM & RPD) with role separation (guest vs member)
5. Guest write lock (403 Forbidden on memory vectorization & skipping debate finale DB tasks)
6. Concurrency scenarios:
   - Atomic counter increments under high concurrency (asyncio.gather)
   - Circuit breaker boundary race-condition defense
"""

import asyncio
from typing import Any, Dict, List

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.router import (
    CIRCUIT_BREAKER_FALLBACK_MSG,
    GUEST_LIMIT_EXCEEDED_MSG,
    extract_auth_info_from_auth,
)
from app.core.config import settings
from app.infrastructure.redis_session import RedisSessionManager
from app.main import app


def create_mock_jwt(sub: str, role: str) -> str:
    """Helper to create test JWT tokens."""
    payload = {
        "sub": sub,
        "role": role,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def parse_sse_events(raw_text: str) -> List[Dict[str, Any]]:
    """Parse SSE text into events."""
    import json
    events = []
    blocks = [b.strip() for b in raw_text.strip().split("\n\n") if b.strip()]
    for block in blocks:
        lines = block.split("\n")
        event_name = None
        data = None
        for line in lines:
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                except Exception:
                    data = data_str
        if event_name:
            events.append({"event": event_name, "data": data})
    return events


# 1. Claims extraction & null-safety
def test_extract_auth_info_guest():
    token = create_mock_jwt("guest-test-1234", "guest")
    auth_header = f"Bearer {token}"
    sub, raw_token, role = extract_auth_info_from_auth(auth_header)
    assert sub == "guest-test-1234"
    assert role == "guest"
    assert raw_token == token


def test_extract_auth_info_member():
    token = create_mock_jwt("member-real-5678", "user")
    auth_header = f"Bearer {token}"
    sub, raw_token, role = extract_auth_info_from_auth(auth_header)
    assert sub == "member-real-5678"
    assert role == "member"


# 2. Redis Session Manager Unit Tests (INCR + EXPIRE NX, Guest Limit, Circuit Breaker)
@pytest.mark.asyncio
async def test_redis_session_manager_guest_usage():
    mgr = RedisSessionManager(redis_url=None)
    guest_id = "guest-uuid-1"

    # Initial usage should be 0
    usage = await mgr.get_guest_usage(guest_id)
    assert usage == 0

    # Increment
    new_usage = await mgr.incr_guest_usage(guest_id)
    assert new_usage == 1

    usage_after = await mgr.get_guest_usage(guest_id)
    assert usage_after == 1


@pytest.mark.asyncio
async def test_redis_session_circuit_breaker_dual_rpm_rpd(monkeypatch):
    mgr = RedisSessionManager(redis_url=None)
    monkeypatch.setattr(settings, "circuit_guest_rpm_limit", 3)
    monkeypatch.setattr(settings, "circuit_guest_rpd_limit", 5)
    monkeypatch.setattr(settings, "circuit_member_rpm_limit", 10)
    monkeypatch.setattr(settings, "circuit_member_rpd_limit", 20)

    # 1st call for guest
    tripped, reason = await mgr.check_and_incr_circuit_breaker(role="guest")
    assert tripped is False
    assert reason is None

    # 2nd call for guest
    tripped, reason = await mgr.check_and_incr_circuit_breaker(role="guest")
    assert tripped is False

    # 3rd call for guest (RPM limit reached: 3)
    tripped, reason = await mgr.check_and_incr_circuit_breaker(role="guest")
    assert tripped is False

    # 4th call for guest (RPM exceeded!)
    tripped, reason = await mgr.check_and_incr_circuit_breaker(role="guest")
    assert tripped is True
    assert reason == "rpm"

    # Verify Member traffic is unaffected! (Role isolation)
    member_tripped, _ = await mgr.check_and_incr_circuit_breaker(role="member")
    assert member_tripped is False


# 3. Concurrency Tests
@pytest.mark.asyncio
async def test_guest_usage_concurrency_atomic():
    """Verify concurrent increments on the same guest_id are strictly atomic."""
    mgr = RedisSessionManager(redis_url=None)
    guest_id = "guest-concurrent-test"

    # Run 50 concurrent increments
    tasks = [mgr.incr_guest_usage(guest_id) for _ in range(50)]
    results = await asyncio.gather(*tasks)

    # Results should contain 1..50
    assert len(results) == 50
    assert max(results) == 50
    assert len(set(results)) == 50

    final_usage = await mgr.get_guest_usage(guest_id)
    assert final_usage == 50


@pytest.mark.asyncio
async def test_circuit_breaker_race_condition_defense(monkeypatch):
    """Verify circuit breaker cleanly handles concurrent requests at threshold boundary."""
    mgr = RedisSessionManager(redis_url=None)
    monkeypatch.setattr(settings, "circuit_guest_rpm_limit", 10)

    # Launch 20 concurrent requests for guest
    tasks = [mgr.check_and_incr_circuit_breaker(role="guest") for _ in range(20)]
    results = await asyncio.gather(*tasks)

    passed = [r for r in results if not r[0]]
    tripped = [r for r in results if r[0]]

    # Exactly 10 should pass, exactly 10 should be tripped
    assert len(passed) == 10
    assert len(tripped) == 10
    for t in tripped:
        assert t[1] == "rpm"


# 4. Guest Write Lock Tests (403 Forbidden)
@pytest.mark.asyncio
async def test_guest_write_lock_scraps():
    transport = ASGITransport(app=app)
    guest_token = create_mock_jwt("guest-1234", "guest")

    payload = {
        "member_id": "guest-1234",
        "book_id": "b-1",
        "book_title": "테스트책",
        "content": "테스트 내용",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Bearer guest token
        res1 = await client.post(
            "/api/v1/memory/scraps",
            json=payload,
            headers={"Authorization": f"Bearer {guest_token}"},
        )
        assert res1.status_code == 403
        assert "게스트 체험 모드" in res1.json()["detail"]

        # 2. Member_id starting with guest- without token
        res2 = await client.post(
            "/api/v1/memory/scraps",
            json=payload,
        )
        assert res2.status_code == 403


@pytest.mark.asyncio
async def test_guest_write_lock_records():
    transport = ASGITransport(app=app)
    guest_token = create_mock_jwt("guest-5678", "guest")

    payload = {
        "record_id": 1,
        "member_id": "guest-5678",
        "title": "테스트",
        "content": "내용",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/vectors/records",
            json=payload,
            headers={"Authorization": f"Bearer {guest_token}"},
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_guest_write_lock_debate_insights():
    transport = ASGITransport(app=app)
    guest_token = create_mock_jwt("guest-9999", "guest")

    payload = {
        "session_id": "test-session-1",
        "member_id": "guest-9999",
        "book_title": "소크라테스의 변명",
        "persona_id": "DEBATE_CRITIC",
        "summary": "토론 요약",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/memory/debate-insights",
            json=payload,
            headers={"Authorization": f"Bearer {guest_token}"},
        )
        assert res.status_code == 403


# 5. Endpoint Graceful 200 OK Fallback Tests (/chat and /chat/stream)
@pytest.mark.asyncio
async def test_guest_chat_limit_fallback_non_streaming(monkeypatch):
    """When guest hits limit, /chat returns 200 OK with graceful message."""
    transport = ASGITransport(app=app)
    guest_token = create_mock_jwt("guest-exceeded-1", "guest")

    # Set guest limit to 2
    monkeypatch.setattr(settings, "guest_chat_limit", 2)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {guest_token}"}
        payload = {
            "message": "안녕",
            "mode": "LIBRARIAN",
            "persona": "CAT",
        }

        # 1st request
        r1 = await client.post("/api/v1/chat", json=payload, headers=headers)
        assert r1.status_code == 200

        # 2nd request
        r2 = await client.post("/api/v1/chat", json=payload, headers=headers)
        assert r2.status_code == 200

        # 3rd request -> Limit exceeded!
        r3 = await client.post("/api/v1/chat", json=payload, headers=headers)
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["reply"] == GUEST_LIMIT_EXCEEDED_MSG
        assert data3["session_id"].startswith("guest-exceeded-1:")


@pytest.mark.asyncio
async def test_guest_circuit_breaker_fallback_streaming(monkeypatch):
    """When circuit breaker trips, /chat/stream returns 200 OK with SSE fallback tokens."""
    transport = ASGITransport(app=app)
    guest_token = create_mock_jwt("guest-cb-stream", "guest")

    # Set RPM limit to 1
    monkeypatch.setattr(settings, "circuit_guest_rpm_limit", 1)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {guest_token}"}
        payload = {
            "message": "스트리밍 질문",
            "mode": "LIBRARIAN",
            "persona": "CAT",
        }

        # 1st request
        r1 = await client.post("/api/v1/chat/stream", json=payload, headers=headers)
        assert r1.status_code == 200

        # 2nd request -> Trips Circuit Breaker!
        r2 = await client.post("/api/v1/chat/stream", json=payload, headers=headers)
        assert r2.status_code == 200
        assert "text/event-stream" in r2.headers.get("content-type", "")

        events = parse_sse_events(r2.text)
        assert len(events) >= 2
        # Metadata -> Token -> Done
        assert events[0]["event"] == "metadata"
        assert events[1]["event"] == "token"
        assert events[1]["data"]["delta"] == CIRCUIT_BREAKER_FALLBACK_MSG
        assert events[2]["event"] == "done"
        assert events[2]["data"]["reply"] == CIRCUIT_BREAKER_FALLBACK_MSG
