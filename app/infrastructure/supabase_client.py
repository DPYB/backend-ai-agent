"""Supabase pgvector client for member personalized scrap vectors."""

import logging
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseVectorClient:
    """Manages Supabase client for scrap_vector similarity search partitioned by member_id."""

    def __init__(
        self,
        url: str = settings.supabase_url,
        key: str = settings.supabase_key,
    ):
        self.url = url
        self.key = key
        self._client: Optional[Client] = None
        self._mock_scraps: List[Dict[str, Any]] = []

        if self.url and self.key:
            try:
                self._client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.warning(
                    "Failed to initialize Supabase client (%s). In-memory mock enabled.",
                    e,
                )
        else:
            logger.info("Supabase credentials not configured. In-memory mock enabled.")

    @property
    def is_connected(self) -> bool:
        """Check if Supabase client is connected."""
        return self._client is not None

    async def ping_db(self) -> bool:
        """Execute a lightweight query on Supabase to prevent 7-day inactivity pause."""
        if not self._client:
            return False
        try:
            self._client.table("scrap_vector").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.info("Supabase ping attempt executed: %s", e)
            return True

    async def search_member_scraps(
        self,
        member_id: str,
        query_embedding: List[float],
        match_threshold: float = 0.5,
        match_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search scrap vectors strictly filtered by member_id (personalization only).

        Calls the Supabase RPC function `match_scraps`.
        """
        if self._client:
            try:
                response = self._client.rpc(
                    "match_scraps",
                    {
                        "p_member_id": member_id,
                        "query_embedding": query_embedding,
                        "match_threshold": match_threshold,
                        "match_count": match_count,
                    },
                ).execute()
                return response.data or []
            except Exception as e:
                logger.error("Supabase RPC match_scraps failed: %s", e)

        # Fallback / mock search
        return [scrap for scrap in self._mock_scraps if scrap.get("member_id") == member_id][
            :match_count
        ]

    async def insert_scrap_vector(
        self,
        member_id: str,
        book_id: str,
        book_title: str,
        content: str,
        memo: str,
        embedding: List[float],
    ) -> Dict[str, Any]:
        """Insert a scrap embedding record into Supabase pgvector scrap_vector table."""
        record = {
            "member_id": member_id,
            "book_id": book_id,
            "book_title": book_title,
            "content": content,
            "memo": memo,
            "embedding": embedding,
        }

        if self._client:
            try:
                response = self._client.table("scrap_vector").insert(record).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error("Failed to insert scrap_vector into Supabase: %s", e)

        # In-memory storage for mock/local testing
        mock_record = {"id": f"mock-{len(self._mock_scraps) + 1}", **record}
        self._mock_scraps.append(mock_record)
        return mock_record


_supabase_client: Optional[SupabaseVectorClient] = None


def get_supabase_client() -> SupabaseVectorClient:
    """Return singleton SupabaseVectorClient instance."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseVectorClient()
    return _supabase_client
