"""Unit tests for book recommendation metadata, KDC parsing, and Kyobo CDN zero-latency fallback."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.national_library_client import (
    NationalLibraryClient,
    genre_to_korean,
    get_verified_cover_url,
    map_kdc_to_genre,
    normalize_genre,
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
    """Test KDC classification and subject keyword genre mapping into standard uppercase Enum."""
    assert map_kdc_to_genre("843.6") == "LITERATURE"
    assert map_kdc_to_genre("813.7") == "LITERATURE"
    assert map_kdc_to_genre("189.2") == "PHILOSOPHY"
    assert map_kdc_to_genre("320.1") == "SOCIAL_SCIENCE"
    assert map_kdc_to_genre("400") == "NATURAL_SCIENCE"
    assert map_kdc_to_genre("600") == "ARTS"
    # Subject keyword fallback
    assert map_kdc_to_genre("", "따뜻한 위로의 힐링 소설") == "LITERATURE"
    assert map_kdc_to_genre("", "감성 산문과 에세이 모음") == "LITERATURE"
    assert map_kdc_to_genre("", "") == "GENERAL"

    # KDC 000 series splitting (004/005 -> TECHNOLOGY, 020s -> PHILOSOPHY, others -> GENERAL)
    assert map_kdc_to_genre("004") == "TECHNOLOGY"
    assert map_kdc_to_genre("004.7") == "TECHNOLOGY"
    assert map_kdc_to_genre("005.133") == "TECHNOLOGY"
    assert map_kdc_to_genre("020") == "PHILOSOPHY"
    assert map_kdc_to_genre("029.1") == "PHILOSOPHY"
    assert map_kdc_to_genre("030") == "GENERAL"
    assert map_kdc_to_genre("050") == "GENERAL"
    assert map_kdc_to_genre("001") == "GENERAL"

    # Bidirectional Korean / English interoperability
    assert genre_to_korean("LITERATURE") == "문학"
    assert genre_to_korean("PHILOSOPHY") == "철학"
    assert normalize_genre("문학") == "LITERATURE"
    assert normalize_genre("문학/소설") == "LITERATURE"
    assert normalize_genre("에세이") == "LITERATURE"
    assert normalize_genre("LITERATURE") == "LITERATURE"


def test_extract_publish_year():
    """Test 4-digit publication year extraction from irregular dates (e.g. 20230000)."""
    from app.infrastructure.national_library_client import _extract_publish_year

    assert _extract_publish_year({"PUBLISH_PREDATE": "20230000"}) == 2023
    assert _extract_publish_year({"PUBLISH_YEAR": "1998"}) == 1998
    assert _extract_publish_year({"INPUT_DATE": "2024-05-12"}) == 2024
    assert _extract_publish_year({"REAL_PUBLISH_DATE": "2025.01"}) == 2025
    assert _extract_publish_year({}) == 0


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
    assert biblio["genre"] == "LITERATURE"
    assert genre_to_korean(biblio["genre"]) == "문학"
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

    async def mock_ainvoke(state, *args, **kwargs):
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

    async def mock_astream_events(state, version="v2", *args, **kwargs):
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


def test_genre_normalization_general_to_gyoyang():
    """Test that GENERAL maps to 교양 in UI representations."""
    from app.infrastructure.national_library_client import genre_to_korean, normalize_genre

    assert genre_to_korean("GENERAL") == "교양"
    assert normalize_genre("교양") == "GENERAL"
    assert normalize_genre("총류") == "GENERAL"


def test_short_title_subtitle_ranking():
    """Test that short titles (e.g. '모순') match subtitles correctly without dropping."""
    from app.infrastructure.national_library_client import NationalLibraryClient

    client = NationalLibraryClient()
    docs = [
        {
            "TITLE": "모순 : 양귀자 소설",
            "AUTHOR": "양귀자",
            "EA_ISBN": "9788998441012",
            "PAGE": "300",
            "PUBLISH_PREDATE": "20230101",
        },
        {
            "TITLE": "모순의 인간 히틀러를 보며",
            "AUTHOR": "홍길동",
            "EA_ISBN": "9788998441999",
            "PAGE": "250",
            "PUBLISH_PREDATE": "20200101",
        },
    ]
    ranked = client._filter_and_rank_monographs(docs, target_title="모순", target_author="양귀자")
    assert len(ranked) >= 1
    assert ranked[0]["TITLE"] == "모순 : 양귀자 소설"
    # Unrelated long title should be dropped
    titles = [item["TITLE"] for item in ranked]
    assert "모순의 인간 히틀러를 보며" not in titles


@pytest.mark.asyncio
async def test_check_cover_alive_robustness(monkeypatch):
    """Test cover check handles 34,150B placeholder and content-length presence safely."""
    from app.infrastructure import national_library_client
    from app.infrastructure.national_library_client import check_cover_alive

    # Ensure app_env is not test for this test to hit logic
    monkeypatch.setattr(national_library_client.settings, "app_env", "development")

    class MockResponse:
        def __init__(self, status_code: int, headers: dict):
            self.status_code = status_code
            self.headers = headers

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def head(self, url: str):
            if "empty_cover" in url:
                return MockResponse(200, {"content-length": "34150"})
            elif "good_cover" in url:
                return MockResponse(200, {"content-length": "45000"})
            elif "no_cl_cover" in url:
                return MockResponse(200, {})
            return MockResponse(404, {})

    monkeypatch.setattr(national_library_client.httpx, "AsyncClient", MockClient)

    assert await check_cover_alive("https://contents.kyobobook.co.kr/empty_cover.jpg") is False
    assert await check_cover_alive("https://contents.kyobobook.co.kr/good_cover.jpg") is True
    assert await check_cover_alive("https://contents.kyobobook.co.kr/no_cl_cover.jpg") is True


def test_clean_book_title_removes_noise_brackets():
    """Verify clean_book_title strips noisy brackets and extra subtitles."""
    from app.infrastructure.national_library_client import clean_book_title

    assert (
        clean_book_title("세네카, 오늘을 빼앗기고 있는 당신에게 (큰글자책)")
        == "세네카, 오늘을 빼앗기고 있는 당신에게"
    )
    assert clean_book_title("브람스를 좋아하세요(오디오북)") == "브람스를 좋아하세요"
    assert clean_book_title("[양장] 싯다르타 <개정판>") == "싯다르타"
    assert clean_book_title("《모순》 (리커버)") == "모순"
    assert clean_book_title("(진중문고납품)브람스를 좋아하세요") == "브람스를 좋아하세요"
    assert clean_book_title("모순 - 양귀자 소설") == "모순"
    assert (
        clean_book_title("교사를 지키는 단단한 생활지도 : 상황별 실전 사례 100")
        == "교사를 지키는 단단한 생활지도"
    )
