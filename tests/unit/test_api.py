"""Unit tests for FastAPI endpoints with 8 Personas and custom librarian name."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_swagger_docs_endpoint():
    """Verify Swagger UI docs are accessible at /docs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify health check endpoint returns 200 healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_health_check_endpoint():
    """Verify root /health endpoint for Central Keep-Alive returns 200 healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_all_personas_endpoint():
    """Verify list personas endpoint returns all 8 personas aligned with core ENUM."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/personas")
        assert response.status_code == 200
        personas = response.json()
        assert len(personas) == 8
        ids = [p["persona_id"] for p in personas]
        assert "CAT" in ids
        assert "SHOEBILL" in ids
        assert "SEA_SLUG" in ids
        assert "GECKO" in ids


@pytest.mark.asyncio
async def test_list_personas_by_mode():
    """Verify list personas endpoint correctly filters by mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Librarian mode (4 동물 사서)
        res_lib = await client.get("/api/v1/personas?mode=LIBRARIAN")
        assert res_lib.status_code == 200
        libs = res_lib.json()
        assert len(libs) == 4
        for p in libs:
            assert p["mode"] == "LIBRARIAN"

        # Debate mode (4 토론 파트너)
        res_deb = await client.get("/api/v1/personas?mode=DEBATE")
        assert res_deb.status_code == 200
        debs = res_deb.json()
        assert len(debs) == 4
        for p in debs:
            assert p["mode"] == "DEBATE"


@pytest.mark.asyncio
async def test_chat_endpoint_librarian_mode():
    """Verify POST /api/v1/chat works in LIBRARIAN mode with Cat persona."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "안녕 블루, 내 서재에 있는 책 좀 확인해줘",
            "mode": "LIBRARIAN",
            "persona": "CAT",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert data["active_persona"] == "CAT"
        assert data["display_name"] == "블루"
        assert data["mode"] == "LIBRARIAN"


@pytest.mark.asyncio
async def test_chat_endpoint_with_custom_librarian_name():
    """Verify POST /api/v1/chat displays user's custom librarian name."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "안녕 내 고양이야!",
            "mode": "LIBRARIAN",
            "persona": "CAT",
            "librarian_name": "우리냥이",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "우리냥이"


@pytest.mark.asyncio
async def test_chat_endpoint_debate_mode():
    """Verify POST /api/v1/chat works in DEBATE mode with Critic persona."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "member_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "이 책의 주인공이 내린 선택에 대해 토론해보고 싶습니다.",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert data["active_persona"] == "DEBATE_CRITIC"
        assert data["display_name"] == "평론가"
        assert data["mode"] == "DEBATE"
