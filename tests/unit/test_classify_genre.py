"""Unit tests for book genre classification endpoint (POST /api/v1/classify-genre).

Verifies:
1. Normal LLM classification: 《그림의 힘》 -> genre="PHILOSOPHY", source="LLM", confidence >= 0.9.
2. Gemini 429 Rate Limit error: 200 OK graceful fallback with source="KDC_FALLBACK", reason containing 429.
3. Timeout (> 2.0s): 200 OK graceful fallback with source="KDC_FALLBACK", reason containing TIMEOUT.
4. Schema violation / JSON parse error: 200 OK graceful fallback with source="KDC_FALLBACK".
5. KDC / EA_ADD_CODE 5-digit fallback integration (Phase 60):
   - KDC empty, EA_ADD_CODE="03320" -> KDC "320" -> genre="SOCIAL_SCIENCE".
   - 513.8 KDC promotion to PHILOSOPHY.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_classify_genre_success_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 1: Normal LLM response correctly classifies 《그림의 힘》 to PHILOSOPHY."""
    monkeypatch.setattr(settings, "gemini_api_key", "mock-test-gemini-api-key-12345678")

    mock_llm_response = AIMessage(
        content='{"genre": "PHILOSOPHY", "subject": "미술치료/심리", "confidence": 0.95, "reason": "마음치유 목적의 미술 심리 에세이"}'
    )

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock
    ) as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/classify-genre",
                json={
                    "title": "그림의 힘",
                    "author": "김선현",
                    "description": "지친 몸과 마음을 치유하는 명화 테라피와 심리 치유의 감성 에세이",
                    "kdc": "513.8",
                    "isbn": "9788950958985",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "PHILOSOPHY"
    assert data["subject"] == "미술치료/심리"
    assert data["confidence"] == 0.95
    assert data["source"] == "LLM"
    assert data["reason"] == "마음치유 목적의 미술 심리 에세이"


@pytest.mark.asyncio
async def test_classify_genre_gemini_429_rate_limit_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario 2: Gemini 429 Rate Limit error triggers KDC fallback with 200 OK (no 500)."""
    monkeypatch.setattr(settings, "gemini_api_key", "mock-test-gemini-api-key-12345678")

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock
    ) as mock_invoke:
        mock_invoke.side_effect = Exception("429 Resource has been exhausted (e.g. check quota).")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/classify-genre",
                json={
                    "title": "이기적 유전자",
                    "author": "리처드 도킨스",
                    "description": "진화론의 새로운 패러다임과 유전자 중심의 생물학",
                    "kdc": "472",
                    "isbn": "9788932473901",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "NATURAL_SCIENCE"
    assert data["source"] == "KDC_FALLBACK"
    assert "FALLBACK_RATE_LIMIT" in data["reason"]
    assert "429" in data["reason"]
    assert data["subject"] == "자연과학"


@pytest.mark.asyncio
async def test_classify_genre_timeout_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 3: When LLM call takes > 2.0s, asyncio.TimeoutError is caught and fallback is returned."""
    monkeypatch.setattr(settings, "gemini_api_key", "mock-test-gemini-api-key-12345678")

    async def _delayed_invoke(*args, **kwargs):
        await asyncio.sleep(2.5)
        return AIMessage(content='{"genre": "LITERATURE", "subject": "소설"}')

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", side_effect=_delayed_invoke
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/classify-genre",
                json={
                    "title": "불편한 편의점",
                    "author": "김호연",
                    "description": "청파동 골목 모퉁이에 자리 잡은 작은 편의점을 무대로 펼쳐지는 이야기",
                    "kdc": "813.7",
                    "isbn": "9791161571188",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "LITERATURE"
    assert data["source"] == "KDC_FALLBACK"
    assert "FALLBACK_TIMEOUT" in data["reason"]
    assert data["subject"] == "문학"


@pytest.mark.asyncio
async def test_classify_genre_parse_error_or_invalid_schema_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario 4: When LLM outputs malformed JSON or illegal genre, fallback is returned gracefully."""
    monkeypatch.setattr(settings, "gemini_api_key", "mock-test-gemini-api-key-12345678")

    # Case 4-1: Malformed non-JSON string
    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock
    ) as mock_invoke:
        mock_invoke.return_value = AIMessage(content="이 책은 장르가 소설인 것 같습니다.")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/classify-genre",
                json={
                    "title": "어린 왕자",
                    "kdc": "863",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "LITERATURE"
    assert data["source"] == "KDC_FALLBACK"
    assert "FALLBACK_PARSE_ERROR" in data["reason"]

    # Case 4-2: Invalid genre literal returned
    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock
    ) as mock_invoke:
        mock_invoke.return_value = AIMessage(
            content='{"genre": "COMICS", "subject": "만화", "confidence": 0.9}'
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/classify-genre",
                json={
                    "title": "미술 산책",
                    "kdc": "650",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "ARTS"
    assert data["source"] == "KDC_FALLBACK"
    assert "FALLBACK_INVALID_GENRE" in data["reason"]


@pytest.mark.asyncio
async def test_classify_genre_kdc_513_8_and_add_code_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario 5 (Phase 60 integration): 513.8 promotion and 5-digit add code fallback in KDC mapping."""
    # When API key is not configured, fallback executes immediately
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_fallback_api_key", "")

    # 1. KDC 513.8 -> PHILOSOPHY promotion
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/classify-genre",
            json={
                "title": "임상미술치료의 이해",
                "kdc": "513.8",
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "PHILOSOPHY"
    assert data["source"] == "KDC_FALLBACK"
    assert data["subject"] == "철학"

    # 2. 5-digit EA_ADD_CODE in kdc parameter (e.g. "03320" -> "320" -> SOCIAL_SCIENCE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/classify-genre",
            json={
                "title": "화폐금융론 개론",
                "kdc": "03320",
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["genre"] == "SOCIAL_SCIENCE"
    assert data["source"] == "KDC_FALLBACK"
    assert data["subject"] == "사회과학"
