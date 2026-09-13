"""Unit tests for memory scrap vectorization endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_vectorize_scrap_success():
    """Verify that valid scrap payload is successfully vectorized and stored."""
    transport = ASGITransport(app=app)
    payload = {
        "member_id": "test-member-123",
        "book_id": "book-uuid-456",
        "book_title": "데미안",
        "content": "새는 알에서 나오려고 투쟁한다. 알은 세계이다.",
        "memo": "스스로의 세계를 깨뜨리는 성장의 고통과 필연성에 대한 깊은 공감.",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/memory/scraps", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["scrap_id"] is not None
        assert "성공적" in data["message"]


@pytest.mark.asyncio
async def test_vectorize_scrap_validation_error():
    """Verify that missing required fields returns 422 Unprocessable Entity."""
    transport = ASGITransport(app=app)
    invalid_payload = {
        "member_id": "test-member-123",
        # book_id, book_title missing
        "content": "",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/memory/scraps", json=invalid_payload)
        assert response.status_code == 422
