"""Unit tests for My Library tool."""

import pytest

from app.domain.memory.my_library_tool import search_my_library
from app.infrastructure.core_api_client import get_core_api_client


@pytest.mark.asyncio
async def test_core_api_bookshelf_fallback():
    """Verify get_my_bookshelf returns structured bookshelf dictionary."""
    client = get_core_api_client()
    bookshelf = await client.get_my_bookshelf("test-member-123")
    assert "books" in bookshelf
    assert len(bookshelf["books"]) >= 1

    first = bookshelf["books"][0]
    assert "title" in first
    assert "status" in first


@pytest.mark.asyncio
async def test_search_my_library_tool_all():
    """Verify search_my_library tool returns formatted book list."""
    res = await search_my_library.ainvoke({"member_id": "test-member-123"})
    assert "서재 도서 목록" in res
    assert "프로젝트 헤일메리" in res
    assert "완독함" in res


@pytest.mark.asyncio
async def test_search_my_library_tool_filtered():
    """Verify search_my_library tool filters by status."""
    res = await search_my_library.ainvoke(
        {"member_id": "test-member-123", "status_filter": "READING"}
    )
    assert "읽는 중" in res
    assert "듄" in res
