"""Unit tests for book recommendation metadata, KDC parsing, and Kyobo CDN zero-latency fallback."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.national_library_client import (
    NationalLibraryClient,
    get_verified_cover_url,
    map_kdc_to_genre,
    parse_page_count,
)
from app.main import app


def test_parse_page_count():
    """Test integer page count extraction from various Korean and English bibliography formats."""
    assert parse_page_count("328 p.") == 328
    assert parse_page_count("450쪽") == 450
    assert parse_page_count("192면") == 192
    assert parse_page_count("v, 280 p.") == 280
    assert parse_page_count("280p") == 280
    assert parse_page_count("") is None
    assert parse_page_count("페이지 없음") is None


def test_map_kdc_to_genre():
    """Test KDC classification and subject keyword genre mapping."""
    assert map_kdc_to_genre("843.6") == "문학"
    assert map_kdc_to_genre("813.7") == "문학"
    assert map_kdc_to_genre("189.2") == "인문/철학"
    assert map_kdc_to_genre("320.1") == "사회과학"
    assert map_kdc_to_genre("400") == "자연과학"
    assert map_kdc_to_genre("600") == "예술"
    # Subject keyword fallback
    assert map_kdc_to_genre("", "따뜻한 위로의 힐링 소설") == "문학/소설"
    assert map_kdc_to_genre("", "감성 산문과 에세이 모음") == "에세이"
    assert map_kdc_to_genre("", "") == "일반도서"


def test_get_verified_cover_url_kyobo_fallback():
    """Test 0ms latency Kyobo CDN cover fallback when National Library cover is missing."""
    # When official cover exists
    official_url = "https://www.nl.go.kr/image/demian.jpg"
    assert get_verified_cover_url(official_url, "9788937460449") == official_url

    # When official cover is empty, fallback to Kyobo CDN
    kyobo_url = get_verified_cover_url("", "9788937460449")
    assert kyobo_url == "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg"

    # When ISBN contains hyphens
    kyobo_hyphen_url = get_verified_cover_url("", "978-89-374-6044-9")
    assert (
        kyobo_hyphen_url
        == "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg"
    )

    # When neither cover nor valid ISBN exists
    placeholder_url = get_verified_cover_url("", "")
    assert "placeholder" in placeholder_url


@pytest.mark.asyncio
async def test_national_library_fallback_sample_catalog_metadata():
    """Test that sample fallback catalog includes enriched page_count, genre, and cover_url."""
    client = NationalLibraryClient(cert_key="")
    biblio = await client.search_book("데미안", "헤르만 헤세")

    assert biblio is not None
    assert biblio["title"] == "데미안"
    assert biblio["author"] == "헤르만 헤세"
    assert biblio["isbn"] == "9788937460449"
    assert biblio["page_count"] == 240
    assert biblio["genre"] == "문학/소설"
    assert "kyobobook.co.kr" in biblio["cover_url"]


@pytest.mark.asyncio
async def test_chat_response_includes_recommended_books(monkeypatch):
    """Test that POST /api/v1/chat includes structured recommended_books for one-click frontend registration."""
    from langchain_core.messages import AIMessage

    from app.api import router

    mock_curated_books = [
        {
            "title": "데미안",
            "author": "헤르만 헤세",
            "publisher": "민음사",
            "isbn": "9788937460449",
            "cover_url": "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg",
            "page_count": 240,
            "genre": "문학",
            "reason": "마음이 쓸쓸할 때 내면의 용기를 주는 책",
            "description": "성장의 아픔과 용기",
        }
    ]

    async def mock_ainvoke(state):
        return {
            **state,
            "messages": [AIMessage(content="데미안을 추천해 드려요냥!")],
            "active_persona": "CAT",
            "curated_books": mock_curated_books,
        }

    monkeypatch.setattr(router._graph, "ainvoke", mock_ainvoke)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "message": "비도 오고 마음이 쓸쓸한데 따뜻한 책 추천해줘",
            "member_id": "test-member-uuid",
            "persona_id": "CAT",
        }
        response = await ac.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "recommended_books" in data
        assert len(data["recommended_books"]) == 1
        book = data["recommended_books"][0]
        assert book["title"] == "데미안"
        assert book["author"] == "헤르만 헤세"
        assert book["isbn"] == "9788937460449"
        assert book["publisher"] == "민음사"
        assert book["page_count"] == 240
        assert book["genre"] == "문학"
        assert book["cover_url"].startswith("https://contents.kyobobook.co.kr")


@pytest.mark.asyncio
async def test_chat_stream_includes_recommended_books_in_done_event(monkeypatch):
    """Test that POST /api/v1/chat/stream includes recommended_books in done event."""
    import json

    from langchain_core.messages import AIMessage

    from app.api import router

    mock_curated_books = [
        {
            "title": "불편한 편의점",
            "author": "김호연",
            "publisher": "나무옆의자",
            "isbn": "9791161571188",
            "cover_url": "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9791161571188.jpg",
            "page_count": 268,
            "genre": "문학/소설",
            "reason": "따뜻한 이웃들의 온정",
            "description": "청파동 골목 모퉁이 편의점 이야기",
        }
    ]

    async def mock_astream_events(state, version="v2"):
        yield {
            "event": "on_chain_end",
            "name": "book_curator_node",
            "data": {"output": {"curated_books": mock_curated_books}},
        }
        yield {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "cat_node"},
            "data": {"chunk": AIMessage(content="불편한 편의점을 추천합니다!")},
        }
        yield {
            "event": "on_chain_end",
            "name": "cat_node",
            "data": {
                "output": {
                    "messages": [AIMessage(content="불편한 편의점을 추천합니다!")],
                    "active_persona": "CAT",
                    "curated_books": mock_curated_books,
                }
            },
        }

    monkeypatch.setattr(router._graph, "astream_events", mock_astream_events)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "message": "힐링 소설 한 권 추천해줘",
            "member_id": "test-member-uuid",
            "persona_id": "CAT",
        }
        response = await ac.post("/api/v1/chat/stream", json=payload)
        assert response.status_code == 200

        text = response.text
        assert "event: books" in text
        assert "event: done" in text

        # Parse done event data
        done_payload = None
        for line in text.splitlines():
            if line.startswith("data: ") and "recommended_books" in line:
                done_payload = json.loads(line.replace("data: ", "", 1))
                break

        assert done_payload is not None
        assert "recommended_books" in done_payload
        assert len(done_payload["recommended_books"]) == 1
        book = done_payload["recommended_books"][0]
        assert book["title"] == "불편한 편의점"
        assert book["author"] == "김호연"
        assert book["isbn"] == "9791161571188"
        assert book["page_count"] == 268
        assert book["genre"] == "문학/소설"
        assert book["cover_url"].startswith("https://contents.kyobobook.co.kr")
