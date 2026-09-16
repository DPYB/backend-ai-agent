"""Unit tests for Phase 17 (Milestone 3.5): Tavily web search + National Library 4-stage validation hybrid curation pipeline."""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.tavily_search_client import TavilySearchClient

# ---------------------------------------------------------------------------
# 1. TavilySearchClient (Lightweight httpx REST client)
# ---------------------------------------------------------------------------


class TestTavilySearchClient:
    """Tests for the lightweight async Tavily Web Search client."""

    def test_is_configured_false_when_no_key(self) -> None:
        client = TavilySearchClient(api_key="")
        assert not client.is_configured

    def test_is_configured_false_when_placeholder(self) -> None:
        client = TavilySearchClient(api_key="tvly-your_tavily_api_key_here")
        assert not client.is_configured

    def test_is_configured_true_with_valid_key(self) -> None:
        client = TavilySearchClient(api_key="tvly-live-abc123xyz")
        assert client.is_configured

    @pytest.mark.asyncio
    async def test_search_returns_empty_in_test_env(self) -> None:
        """In test env (is_testing guard) the client must return [] without HTTP requests."""
        client = TavilySearchClient(api_key="tvly-live-abc123xyz")
        results = await client.search("2025 소설 추천")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_unconfigured(self) -> None:
        client = TavilySearchClient(api_key="")
        results = await client.search("책 추천")
        assert results == []

    def test_client_attributes(self) -> None:
        client = TavilySearchClient(
            api_key="tvly-test-key",
            api_url="https://api.tavily.com/search",
            timeout=5.0,
        )
        assert client.api_key == "tvly-test-key"
        assert "tavily.com" in client.api_url
        assert client.timeout == 5.0


# ---------------------------------------------------------------------------
# 2. search_recent_books tool (On-demand web search)
# ---------------------------------------------------------------------------


class TestSearchRecentBooksTool:
    """Tests for the on-demand search_recent_books tool."""

    @pytest.mark.asyncio
    async def test_returns_message_when_unconfigured_or_test_env(self) -> None:
        from app.domain.recommend.search_books_tool import search_recent_books

        result = await search_recent_books.ainvoke({"query": "2025 소설 신간", "count": 3})
        assert isinstance(result, str)
        # Returns graceful message when unconfigured or in test env
        assert "웹 검색" in result or "결과가 없습니다" in result or "후보" in result

    @pytest.mark.asyncio
    async def test_tool_name_is_correct(self) -> None:
        from app.domain.recommend.search_books_tool import search_recent_books

        assert search_recent_books.name == "search_recent_books"

    def test_extract_candidates_from_results(self) -> None:
        from app.domain.recommend.search_books_tool import _extract_book_candidates_from_results

        fake_results = [
            {
                "title": "《아무튼, 여름》 감성 에세이 추천",
                "content": "여름의 감성을 담은 산뜻한 에세이",
                "url": "https://example.com/1",
            },
            {
                "title": "2025년 화제 소설 '밝은 밤'",
                "content": "최은영 장편소설",
                "url": "https://example.com/2",
            },
            {
                "title": "",  # Empty title should be skipped
                "content": "no title",
                "url": "https://example.com/3",
            },
        ]
        candidates = _extract_book_candidates_from_results(fake_results, max_candidates=5)
        assert len(candidates) >= 1
        titles = [c["candidate_title"] for c in candidates]
        assert any("아무튼" in t for t in titles)

    def test_no_duplicate_candidates(self) -> None:
        from app.domain.recommend.search_books_tool import _extract_book_candidates_from_results

        fake_results = [
            {
                "title": "《데미안》 추천 도서",
                "content": "헤르만 헤세 소설",
                "url": "https://a.com/1",
            },
            {
                "title": "《데미안》 서평",
                "content": "헤르만 헤세 고전",
                "url": "https://a.com/2",
            },
        ]
        candidates = _extract_book_candidates_from_results(fake_results, max_candidates=5)
        titles = [c["candidate_title"] for c in candidates]
        normalized = [t.replace(" ", "").lower() for t in titles]
        assert normalized.count("데미안") <= 1


# ---------------------------------------------------------------------------
# 3. National Library 4-stage monograph validation chain
# ---------------------------------------------------------------------------


class TestNationalLibraryFilterAndRank:
    """Tests for the 4-stage monograph filtration chain (Format, Text match, Recency)."""

    def _make_doc(self, **kwargs: Any) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {
            "EA_ISBN": "9788937460449",
            "TITLE": "데미안",
            "AUTHOR": "헤르만 헤세",
            "PUBLISHER": "민음사",
            "PAGE": "240 p.",
            "FORM": "",
            "KDC": "853",
            "SUBJECT": "소설",
            "TITLE_URL": "",
            "PUBLISH_PREDATE": "20230101",
        }
        defaults.update(kwargs)
        return defaults

    def test_filters_out_invalid_isbn(self) -> None:
        from app.infrastructure.national_library_client import NationalLibraryClient

        client = NationalLibraryClient(cert_key="fake")
        doc = self._make_doc(EA_ISBN="")
        result = client._filter_and_rank_monographs([doc], "데미안")
        assert result == []

    def test_filters_out_pamphlets_under_50_pages(self) -> None:
        from app.infrastructure.national_library_client import NationalLibraryClient

        client = NationalLibraryClient(cert_key="fake")
        doc = self._make_doc(PAGE="30 p.")
        result = client._filter_and_rank_monographs([doc], "데미안")
        assert result == []

    def test_filters_out_derivative_noise(self) -> None:
        from app.infrastructure.national_library_client import NationalLibraryClient

        client = NationalLibraryClient(cert_key="fake")
        doc = self._make_doc(TITLE="데미안 해설집")
        result = client._filter_and_rank_monographs([doc], "데미안")
        assert result == []

    def test_valid_doc_passes_all_stages(self) -> None:
        from app.infrastructure.national_library_client import NationalLibraryClient

        client = NationalLibraryClient(cert_key="fake")
        doc = self._make_doc()
        result = client._filter_and_rank_monographs([doc], "데미안")
        assert len(result) == 1

    def test_recency_score_applied(self) -> None:
        """More recent publication year should rank higher when titles match equally."""
        from app.infrastructure.national_library_client import NationalLibraryClient

        client = NationalLibraryClient(cert_key="fake")
        old_doc = self._make_doc(PUBLISH_PREDATE="20000101", TITLE="데미안")
        new_doc = self._make_doc(PUBLISH_PREDATE="20240601", TITLE="데미안")
        result = client._filter_and_rank_monographs([old_doc, new_doc], "데미안")
        assert result[0]["PUBLISH_PREDATE"] == "20240601"


class TestNationalLibraryCoverAlive:
    """Tests for 4th stage: Kyobo CDN cover image survival check."""

    @pytest.mark.asyncio
    async def test_check_cover_alive_in_test_env(self) -> None:
        from app.infrastructure.national_library_client import check_cover_alive

        alive = await check_cover_alive(
            "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg"
        )
        assert alive is True

    @pytest.mark.asyncio
    async def test_check_cover_alive_empty_url(self) -> None:
        from app.infrastructure.national_library_client import check_cover_alive

        assert await check_cover_alive("") is False
        assert await check_cover_alive("invalid-url") is False


# ---------------------------------------------------------------------------
# 4. Curator node — hybrid curation (New + Classic)
# ---------------------------------------------------------------------------


class TestCuratorNodeHybrid:
    """Tests for the hybrid new+classic book curation in book_curator_node."""

    @pytest.mark.asyncio
    async def test_curator_returns_verified_books_in_test_env(self) -> None:
        import typing

        from app.domain.graph.curator_node import book_curator_node
        from app.domain.graph.state import AgentState

        state = typing.cast(
            AgentState,
            {
                "member_id": "test-member",
                "curator_request": "울적한 날 위로가 되는 책",
                "messages": [],
                "weather_context": "흐림, 18°C",
                "curated_books": [],
                "location_coords": None,
            },
        )
        result = await book_curator_node(state)
        assert "curated_books" in result
        assert result["curator_request"] is None
        books: List[Dict[str, Any]] = result["curated_books"]
        assert isinstance(books, list)
        assert len(books) >= 1
        for book in books:
            assert "title" in book
            assert "author" in book
            assert "isbn" in book

    @pytest.mark.asyncio
    async def test_curator_hybrid_fallback_has_era_field(self) -> None:
        """Fallback candidates must carry era field (recent/classic)."""
        import typing

        from app.domain.graph.curator_node import book_curator_node
        from app.domain.graph.state import AgentState

        state = typing.cast(
            AgentState,
            {
                "member_id": None,
                "curator_request": "성장에 관한 책",
                "messages": [],
                "weather_context": None,
                "curated_books": [],
                "location_coords": None,
            },
        )
        result = await book_curator_node(state)
        books = result.get("curated_books", [])
        for book in books:
            assert "era" in book, f"Book {book.get('title')} missing 'era' field"

    @pytest.mark.asyncio
    async def test_curator_clears_curator_request(self) -> None:
        import typing

        from app.domain.graph.curator_node import book_curator_node
        from app.domain.graph.state import AgentState

        state = typing.cast(
            AgentState,
            {
                "member_id": "user-1",
                "curator_request": "과학 도서",
                "messages": [],
                "weather_context": None,
                "curated_books": [],
                "location_coords": None,
            },
        )
        result = await book_curator_node(state)
        assert result["curator_request"] is None


# ---------------------------------------------------------------------------
# 5. recommend_books tool — Tavily exploration + National Library verification
# ---------------------------------------------------------------------------


class TestRecommendBooksToolRefactored:
    """Tests for the dual-track recommend_books tool."""

    @pytest.mark.asyncio
    async def test_recommend_books_returns_string(self) -> None:
        from app.domain.recommend.recommend_tool import recommend_books

        result = await recommend_books.ainvoke({"query": "철학 에세이", "count": 2})
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_recommend_books_fallback_catalog_returns_books(self) -> None:
        from app.domain.recommend.recommend_tool import recommend_books

        result = await recommend_books.ainvoke({"query": "우울한 날 읽을 책", "count": 2})
        assert isinstance(result, str)
        assert "《" in result or "[1]" in result

    @pytest.mark.asyncio
    async def test_get_fallback_titles_keyword_matching(self) -> None:
        from app.domain.recommend.recommend_tool import _get_fallback_titles_for_query

        titles = _get_fallback_titles_for_query("우울 힐링", 2)
        assert len(titles) == 2
        assert any(
            "백세희" in t.get("author", "") or "이병률" in t.get("author", "") for t in titles
        )

    @pytest.mark.asyncio
    async def test_recommend_books_with_redis_cache_hit(self) -> None:
        """When Redis returns a cache hit, no API call should be made."""
        cached_data = [
            {
                "title": "캐시된 도서",
                "author": "저자",
                "publisher": "출판사",
                "isbn": "9788900000000",
                "cover_url": "",
                "page_count": 200,
                "genre": "문학",
                "curation_reason": "캐시에서 반환된 추천",
                "source": "CACHE",
            }
        ]
        mock_redis = AsyncMock()
        mock_redis.get_cached_recommendation = AsyncMock(return_value=cached_data)
        mock_redis.set_cached_recommendation = AsyncMock()

        with patch(
            "app.domain.recommend.recommend_tool.get_redis_session_manager",
            return_value=mock_redis,
        ):
            from app.domain.recommend.recommend_tool import recommend_books

            result = await recommend_books.ainvoke({"query": "캐시 테스트", "count": 1})
        assert "캐시된 도서" in result


# ---------------------------------------------------------------------------
# 6. tools.py registry integrity
# ---------------------------------------------------------------------------


def test_generic_tools_integrity() -> None:
    """GENERIC_TOOLS should contain standard tools including search_recent_books."""
    from app.domain.graph.tools import GENERIC_TOOLS

    tool_names = [t.name for t in GENERIC_TOOLS]
    assert "recommend_books" in tool_names
    assert "search_recent_books" in tool_names
    assert "search_scrap_memory" in tool_names
    assert "search_debate_memory" in tool_names
    assert "search_my_library" in tool_names
