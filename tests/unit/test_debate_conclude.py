"""Unit tests for Debate Persona Conclude & Finale Book Curation Pipeline."""

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
async def test_debate_conclude_via_ui_action():
    """Verify conclude via explicit UI button action='conclude'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "오늘 토론 여기서 마무리하겠습니다.",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
            "action": "conclude",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        # 1. Flag and summary assertions
        assert data["is_concluded"] is True
        assert data["debate_summary"] is not None
        assert len(data["debate_summary"]) > 0

        # 2. Curated books assertions
        assert "recommended_books" in data
        assert len(data["recommended_books"]) >= 1
        first_book = data["recommended_books"][0]
        assert "title" in first_book and len(first_book["title"]) > 0
        assert "isbn" in first_book
        assert "cover_url" in first_book
        assert "author" in first_book


@pytest.mark.asyncio
async def test_debate_conclude_empty_message_auto_fill():
    """Verify that action='conclude' with empty message auto-fills and succeeds."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "",
            "mode": "DEBATE",
            "persona": "DEBATE_STORYTELLER",
            "action": "conclude",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_concluded"] is True
        assert len(data["recommended_books"]) >= 1


@pytest.mark.asyncio
async def test_debate_conclude_via_natural_keywords():
    """Verify conclude via natural phrasing in conversation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "오늘 이야기 잘 들었습니다. 여기까지 하고 토론 마무리할게요.",
            "mode": "DEBATE",
            "persona": "DEBATE_COUNSELOR",
            "action": "chat",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_concluded"] is True
        assert len(data["recommended_books"]) >= 1


@pytest.mark.asyncio
async def test_debate_normal_turn_keeps_running():
    """Verify that a normal debate turn does NOT conclude and keeps running."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "한강 작가의 《소년이 온다》에서 동호의 내면 심리는 어떻게 해석할 수 있을까요?",
            "mode": "DEBATE",
            "persona": "DEBATE_OBSERVER",
            "action": "chat",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["is_concluded"] is False
        assert data["debate_summary"] is None


@pytest.mark.asyncio
async def test_debate_conclude_via_sse_streaming():
    """Verify debate conclude in SSE streaming (/api/v1/chat/stream)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "토론 마무리",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
            "action": "conclude",
        }
        response = await client.post("/api/v1/chat/stream", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = parse_sse_events(response.text)
        event_types = [e["event"] for e in events]
        assert "metadata" in event_types
        assert "done" in event_types

        done_event = [e for e in events if e["event"] == "done"][-1]
        assert done_event["data"]["is_concluded"] is True
        assert done_event["data"]["debate_summary"] is not None
        assert len(done_event["data"]["recommended_books"]) >= 1
