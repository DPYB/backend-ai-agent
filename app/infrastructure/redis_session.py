"""Redis session and caching infrastructure with fallback support."""

import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Manages chat sessions, state, and recommendation caching using Redis.

    Includes in-memory fallback for local development or testing without Redis.
    """

    def __init__(self, redis_url: str = settings.redis_url):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._in_memory_store: Dict[str, str] = {}
        self._is_redis_available: bool = False

    async def connect(self) -> None:
        """Establish Redis connection or fall back to in-memory store."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0,
            )
            await self._client.ping()
            self._is_redis_available = True
            logger.info("Connected to Redis at %s", self.redis_url)
        except Exception as e:
            self._is_redis_available = False
            logger.warning(
                "Redis connection failed (%s). Falling back to in-memory session store.",
                e,
            )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client and self._is_redis_available:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.error("Error closing Redis connection: %s", e)
        self._is_redis_available = False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data by session_id."""
        key = f"session:{session_id}"
        try:
            if self._is_redis_available and self._client:
                data = await self._client.get(key)
            else:
                data = self._in_memory_store.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error("Failed to get session %s: %s", session_id, e)
            return None

    async def save_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> None:
        """Save session data with TTL (default 24h)."""
        key = f"session:{session_id}"
        serialized = json.dumps(data, ensure_ascii=False)
        try:
            if self._is_redis_available and self._client:
                await self._client.setex(key, ttl_seconds, serialized)
            else:
                self._in_memory_store[key] = serialized
        except Exception as e:
            logger.error("Failed to save session %s: %s", session_id, e)
            self._in_memory_store[key] = serialized

    async def get_cached_recommendation(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached book recommendations."""
        key = f"recommend_cache:{cache_key}"
        try:
            if self._is_redis_available and self._client:
                data = await self._client.get(key)
            else:
                data = self._in_memory_store.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error("Failed to get recommendation cache for %s: %s", cache_key, e)
            return None

    async def set_cached_recommendation(
        self,
        cache_key: str,
        recommendations: List[Dict[str, Any]],
        ttl_seconds: int = settings.redis_cache_ttl_seconds,
    ) -> None:
        """Cache book recommendations to prevent redundant external API calls."""
        key = f"recommend_cache:{cache_key}"
        serialized = json.dumps(recommendations, ensure_ascii=False)
        try:
            if self._is_redis_available and self._client:
                await self._client.setex(key, ttl_seconds, serialized)
            else:
                self._in_memory_store[key] = serialized
        except Exception as e:
            logger.error("Failed to set recommendation cache for %s: %s", cache_key, e)

    async def get(self, key: str) -> Optional[str]:
        """Generic get method with fallback to in-memory store."""
        try:
            if self._is_redis_available and self._client:
                val = await self._client.get(key)
                if isinstance(val, bytes):
                    return val.decode("utf-8")
                return val
            return self._in_memory_store.get(key)
        except Exception as e:
            logger.error("Failed to get key %s: %s", key, e)
            return self._in_memory_store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        """Generic set method with optional TTL (ex seconds) and in-memory fallback."""
        try:
            if self._is_redis_available and self._client:
                if ex is not None:
                    await self._client.setex(key, ex, value)
                else:
                    await self._client.set(key, value)
            else:
                self._in_memory_store[key] = value
        except Exception as e:
            logger.error("Failed to set key %s: %s", key, e)
            self._in_memory_store[key] = value


_session_manager: Optional[RedisSessionManager] = None


def get_redis_session_manager() -> RedisSessionManager:
    """Return singleton RedisSessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = RedisSessionManager()
    return _session_manager
