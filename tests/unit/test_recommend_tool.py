"""Unit tests for Book Recommendation tool and core-api client."""

import pytest

from app.domain.recommend.recommend_tool import recommend_books
from app.infrastructure.core_api_client import get_core_api_client
from app.infrastructure.redis_session import get_redis_session_manager


@pytest.mark.asyncio
async def test_core_api_client_contract():
    """Verify core-api client provides structured book data even with fallback."""
    client = get_core_api_client()

    details = await client.get_book_details("test-isbn-123")
    assert details is not None
    assert "title" in details
    assert "author" in details
    assert "isbn" in details

    search_res = await client.search_books("철학", limit=2)
    assert isinstance(search_res, list)
    assert len(search_res) <= 2
    if search_res:
        assert "title" in search_res[0]


@pytest.mark.asyncio
async def test_recommend_books_tool_and_cache():
    """Verify recommend_books tool formats output and caches results."""
    query = "마음을 치유하는 에세이"

    # First call (generates recommendation & caches)
    result_1 = await recommend_books.ainvoke({"query": query, "count": 2})
    assert result_1 is not None
    assert len(result_1) > 0

    # Second call (cache hit check)
    redis_mgr = get_redis_session_manager()
    import hashlib

    cache_key = hashlib.md5(f"{query}:2".encode("utf-8")).hexdigest()
    cached = await redis_mgr.get_cached_recommendation(cache_key)
    assert cached is not None
    assert len(cached) > 0
    assert "title" in cached[0]
