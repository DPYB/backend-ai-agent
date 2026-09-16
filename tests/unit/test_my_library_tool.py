"""Unit tests for My Library tool."""

import pytest

from app.domain.memory.my_library_tool import search_my_library
from app.infrastructure.core_api_client import get_core_api_client


@pytest.mark.asyncio
async def test_core_api_bookshelf_fallback():
    """Verify get_my_bookshelf returns honest empty bookshelf dictionary when core-api is unavailable."""
    client = get_core_api_client()
    bookshelf = await client.get_my_bookshelf("test-member-123")
    assert "books" in bookshelf
    assert bookshelf["books"] == []
    assert bookshelf["total_count"] == 0


@pytest.mark.asyncio
async def test_search_my_library_tool_empty():
    """Verify search_my_library tool returns honest empty message without hallucinating books."""
    res = await search_my_library.ainvoke({"member_id": "test-member-123"})
    assert "등록된 도서가 없습니다" in res


@pytest.mark.asyncio
async def test_search_my_library_tool_empty_filtered():
    """Verify search_my_library tool returns honest message when filtered by status on empty shelf."""
    res = await search_my_library.ainvoke(
        {"member_id": "test-member-123", "status_filter": "READING"}
    )
    assert "READING" in res
    assert "등록된 도서가 없습니다" in res


@pytest.mark.asyncio
async def test_search_my_library_tool_with_books(monkeypatch):
    """Verify search_my_library tool formats active bookshelf entries correctly."""
    client = get_core_api_client()

    async def mock_get_my_bookshelf(member_id: str, token: str | None = None):
        return {
            "total_count": 2,
            "books": [
                {
                    "book_id": "b-1",
                    "title": "클린 아키텍처",
                    "author": "로버트 C. 마틴",
                    "status": "COMPLETED",
                    "rating": 5.0,
                    "review": "필독서입니다.",
                },
                {
                    "book_id": "b-2",
                    "title": "리팩터링 2판",
                    "author": "마틴 파울러",
                    "status": "READING",
                    "rating": 4.5,
                    "review": "개선 중",
                },
            ],
        }

    monkeypatch.setattr(client, "get_my_bookshelf", mock_get_my_bookshelf)

    # Test all books
    res_all = await search_my_library.ainvoke({"member_id": "test-member-123"})
    assert "서재 도서 목록" in res_all
    assert "클린 아키텍처" in res_all
    assert "완독함" in res_all
    assert "리팩터링 2판" in res_all
    assert "읽는 중" in res_all

    # Test status filter
    res_filtered = await search_my_library.ainvoke(
        {"member_id": "test-member-123", "status_filter": "READING"}
    )
    assert "리팩터링 2판" in res_filtered
    assert "클린 아키텍처" not in res_filtered


@pytest.mark.asyncio
async def test_search_my_library_tool_guest_bypass():
    """Verify search_my_library tool gracefully bypasses for guest users."""
    res = await search_my_library.ainvoke({"member_id": "None"})
    assert "게스트" in res
    assert "서재" in res
