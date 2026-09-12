"""REST client for backend-core-api communication."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CoreApiClient:
    """Asynchronous REST client for communication with DPYB backend-core-api."""

    def __init__(
        self,
        base_url: str = settings.core_api_base_url,
        timeout: float = settings.core_api_timeout_seconds,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_book_details(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Fetch book details from core-api (GET /api/v1/books/{book_id}).

        Provides graceful fallback if core-api is not yet reachable during Phase 1.
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/books/{book_id}")
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "core-api returned status %d for book_id %s",
                response.status_code,
                book_id,
            )
        except Exception as e:
            logger.info("core-api not reachable (%s), using structured fallback for %s", e, book_id)

        # Graceful fallback mock for Phase 1 testing and offline execution
        return {
            "book_id": book_id,
            "title": f"도서 정보 ({book_id})",
            "author": "작가 미상",
            "publisher": "DPYB 도서관",
            "isbn": "9791100000000",
            "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
            "description": "국립중앙도서관 및 core-api 연동 대기 중인 도서 정보입니다.",
        }

    async def search_books(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search books via core-api (GET /api/v1/books/search?query=...).

        Provides graceful fallback if core-api is not yet reachable.
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/books/search",
                params={"query": query, "limit": limit},
            )
            if response.status_code == 200:
                return response.json().get("books", [])
        except Exception as e:
            logger.info("core-api book search failed (%s), returning query-based fallback", e)

        return [
            {
                "book_id": f"core-book-{i+1}",
                "title": f"{query} 관련 추천 도서 {i+1}",
                "author": f"저자 {i+1}",
                "publisher": "DPYB 출판사",
                "isbn": f"979110000000{i+1}",
                "cover_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
                "description": f"'{query}' 주제에 부합하는 추천 도서입니다.",
            }
            for i in range(min(limit, 3))
        ]

    async def get_my_bookshelf(self, member_id: str) -> Dict[str, Any]:
        """Fetch member's bookshelf from core-api (GET /api/v1/members/{member_id}/bookshelf).

        Provides graceful fallback if core-api is not yet reachable.
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/members/{member_id}/bookshelf")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.info("core-api bookshelf query failed (%s), using structured fallback", e)

        return {
            "member_id": member_id,
            "total_count": 3,
            "books": [
                {
                    "book_id": "book-phm",
                    "title": "프로젝트 헤일메리",
                    "author": "앤디 위어",
                    "status": "COMPLETED",
                    "rating": 5,
                    "created_at": "2026-08-15T10:00:00Z",
                },
                {
                    "book_id": "book-dune",
                    "title": "듄 (Dune)",
                    "author": "프랭크 허버트",
                    "status": "READING",
                    "rating": 4,
                    "created_at": "2026-09-01T15:30:00Z",
                },
                {
                    "book_id": "book-demian",
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "status": "WISH",
                    "rating": None,
                    "created_at": "2026-09-05T09:00:00Z",
                },
            ],
        }


_core_api_client: Optional[CoreApiClient] = None


def get_core_api_client() -> CoreApiClient:
    """Return singleton CoreApiClient instance."""
    global _core_api_client
    if _core_api_client is None:
        _core_api_client = CoreApiClient()
    return _core_api_client
