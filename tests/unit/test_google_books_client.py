"""Unit tests for Google Books API client and supplementary enrichment chain."""

from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.google_books_client import GoogleBooksClient, get_google_books_client


@pytest.mark.asyncio
async def test_google_books_client_singleton():
    """Verify singleton returns instance."""
    client1 = get_google_books_client()
    client2 = get_google_books_client()
    assert client1 is client2
    assert isinstance(client1, GoogleBooksClient)


@pytest.mark.asyncio
async def test_google_books_search_volume_by_isbn_mock():
    """Test searching volume by ISBN returns expected structure."""
    client = GoogleBooksClient(api_key="test_key")
    result = await client.search_volume(isbn="9791168473690")
    assert result is not None
    assert "page_count" in result
    assert result["page_count"] == 320
    assert "cover_url" in result


@pytest.mark.asyncio
async def test_google_books_enrich_missing_metadata_skips_when_already_present():
    """If both page_count and cover_url are present, should skip API lookup."""
    client = GoogleBooksClient()
    existing_page = 280
    existing_cover = "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9791168473690.jpg"

    with patch.object(client, "search_volume", new_callable=AsyncMock) as mock_search:
        page, cover = await client.enrich_missing_metadata(
            isbn="9791168473690",
            title="불편한 편의점",
            existing_page_count=existing_page,
            existing_cover_url=existing_cover,
        )
        mock_search.assert_not_called()
        assert page == 280
        assert cover == existing_cover


@pytest.mark.asyncio
async def test_google_books_enrich_missing_metadata_fills_missing():
    """Fills missing page count or cover url when absent."""
    client = GoogleBooksClient()

    with patch.object(
        client,
        "search_volume",
        new_callable=AsyncMock,
        return_value={
            "title": "테스트 도서",
            "author": "작가",
            "page_count": 350,
            "cover_url": "https://books.google.com/test_cover.jpg",
        },
    ):
        # 1. Missing page_count
        page, cover = await client.enrich_missing_metadata(
            isbn="9791168473690",
            title="테스트 도서",
            existing_page_count=None,
            existing_cover_url="https://existing.cover.jpg",
        )
        assert page == 350
        assert cover == "https://existing.cover.jpg"

        # 2. Missing cover_url
        page, cover = await client.enrich_missing_metadata(
            isbn="9791168473690",
            title="테스트 도서",
            existing_page_count=210,
            existing_cover_url=None,
        )
        assert page == 210
        assert cover == "https://books.google.com/test_cover.jpg"


def test_google_books_parse_volume_info():
    """Verify parsing volumeInfo correctly upgrades http to https and extracts clean pages."""
    client = GoogleBooksClient()
    sample_volume_info = {
        "title": "클린 코드",
        "authors": ["로버트 C. 마틴"],
        "publisher": "인사이트",
        "pageCount": 584,
        "imageLinks": {
            "smallThumbnail": "http://books.google.com/books/content?id=1&zoom=5",
            "thumbnail": "http://books.google.com/books/content?id=1&zoom=1",
            "medium": "http://books.google.com/books/content?id=1&zoom=2",
        },
        "description": "애자일 소프트웨어 장인 정신",
    }
    parsed = client._parse_volume_info(sample_volume_info)
    assert parsed["title"] == "클린 코드"
    assert parsed["author"] == "로버트 C. 마틴"
    assert parsed["page_count"] == 584
    assert parsed["cover_url"] == "https://books.google.com/books/content?id=1&zoom=2"
    assert parsed["publisher"] == "인사이트"
