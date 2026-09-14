"""Unit tests for FastAPI real-time SSE streaming chat endpoint (/api/v1/chat/stream)."""

import json
from typing import Any, Dict, List

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def parse_sse_events(raw_text: str) -> List[Dict[str, Any]]:
    """Parse raw SSE text stream into list of event dictionaries."""
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


@pytest.mark.asyncio
async def test_chat_stream_endpoint_librarian_mode():
    """Verify POST /api/v1/chat/stream returns text/event-stream with metadata, token, and done."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "안녕 블루, 책 읽기 좋은 날이네",
            "mode": "LIBRARIAN",
            "persona": "CAT",
        }
        response = await client.post("/api/v1/chat/stream", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = parse_sse_events(response.text)
        assert len(events) >= 2

        # 1. First event must be metadata
        meta_event = events[0]
        assert meta_event["event"] == "metadata"
        assert meta_event["data"]["active_persona"] == "CAT"
        assert meta_event["data"]["mode"] == "LIBRARIAN"
        assert meta_event["data"]["display_name"] == "블루"

        # 2. Last event must be done
        done_event = events[-1]
        assert done_event["event"] == "done"
        assert done_event["data"]["active_persona"] == "CAT"
        assert len(done_event["data"]["reply"]) > 0

        # 3. Intermediate events should include token
        event_types = [e["event"] for e in events]
        assert "token" in event_types


@pytest.mark.asyncio
async def test_chat_stream_custom_librarian_name():
    """Verify POST /api/v1/chat/stream properly displays custom librarian name in metadata and done."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "안녕 파랭이야 반가워!",
            "mode": "LIBRARIAN",
            "persona": "CAT",
            "librarian_name": "파랭이",
        }
        response = await client.post("/api/v1/chat/stream", json=payload)
        assert response.status_code == 200

        events = parse_sse_events(response.text)
        meta_event = events[0]
        assert meta_event["data"]["display_name"] == "파랭이"

        done_event = events[-1]
        assert done_event["data"]["display_name"] == "파랭이"


@pytest.mark.asyncio
async def test_chat_stream_debate_mode():
    """Verify POST /api/v1/chat/stream works seamlessly for debate partner personas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "인간의 본성에 대한 고전 문학 작품 토론을 원합니다.",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
        }
        response = await client.post("/api/v1/chat/stream", json=payload)
        assert response.status_code == 200

        events = parse_sse_events(response.text)
        meta_event = events[0]
        assert meta_event["data"]["mode"] == "DEBATE"
        assert meta_event["data"]["active_persona"] == "DEBATE_CRITIC"

        done_event = events[-1]
        assert done_event["event"] == "done"
        assert done_event["data"]["active_persona"] == "DEBATE_CRITIC"
