"""Redis session and caching infrastructure with fallback support."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

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

    async def delete_session(self, session_id: str) -> None:
        """Delete session data by session_id."""
        key = f"session:{session_id}"
        try:
            if self._is_redis_available and self._client:
                await self._client.delete(key)
            self._in_memory_store.pop(key, None)
        except Exception as e:
            logger.error("Failed to delete session %s: %s", session_id, e)
            self._in_memory_store.pop(key, None)

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

    async def incr(self, key: str, ex: Optional[int] = None, nx_expire: bool = False) -> int:
        """Atomically increment a key with optional TTL.

        If nx_expire is True, sets TTL only if the key has no existing TTL or on first creation.
        Uses in-memory fallback with asyncio lock if Redis is unavailable.
        """
        if not hasattr(self, "_memory_lock"):
            import asyncio

            self._memory_lock = asyncio.Lock()

        try:
            if self._is_redis_available and self._client:
                val = await self._client.incr(key)
                if ex is not None:
                    if nx_expire:
                        # Set expiration only if key has no expire set (NX)
                        # redis-py supports expire(key, ex, nx=True)
                        try:
                            await self._client.expire(key, ex, nx=True)
                        except Exception:
                            # Fallback if redis server < 7.0 doesn't support NX
                            ttl = await self._client.ttl(key)
                            if ttl < 0:
                                await self._client.expire(key, ex)
                    else:
                        await self._client.expire(key, ex)
                return int(val)
            else:
                async with self._memory_lock:
                    current_str = self._in_memory_store.get(key, "0")
                    try:
                        current = int(current_str)
                    except ValueError:
                        current = 0
                    current += 1
                    self._in_memory_store[key] = str(current)
                    return current
        except Exception as e:
            logger.error("Failed to incr key %s: %s", key, e)
            async with self._memory_lock:
                current_str = self._in_memory_store.get(key, "0")
                try:
                    current = int(current_str)
                except ValueError:
                    current = 0
                current += 1
                self._in_memory_store[key] = str(current)
                return current

    async def get_int(self, key: str) -> int:
        """Get integer value of a key, returning 0 if missing or invalid."""
        raw = await self.get(key)
        if raw is None:
            return 0
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    async def incr_guest_usage(self, guest_id: str, ttl_seconds: int = 86400 * 14) -> int:
        """Increment guest chat usage count permanently bound to guest_id (sub).

        TTL is set to 14 days by default to cover the full hackathon evaluation period.
        """
        key = f"guest_usage:{guest_id}"
        # Set expire only on creation to maintain permanent count without resetting
        return await self.incr(key, ex=ttl_seconds, nx_expire=True)

    async def get_guest_usage(self, guest_id: str) -> int:
        """Retrieve current guest chat usage count."""
        key = f"guest_usage:{guest_id}"
        return await self.get_int(key)

    async def check_and_incr_circuit_breaker(
        self,
        role: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check and increment dual RPM / RPD circuit breakers with role isolation.

        Returns:
            Tuple of (is_tripped, tripped_type)
            is_tripped: True if either RPM or RPD limit is exceeded
            tripped_type: "rpm" or "rpd" if tripped, else None
        """
        import time
        from datetime import datetime, timedelta, timezone

        norm_role = "guest" if role == "guest" else "member"
        if norm_role == "guest":
            rpm_limit = settings.circuit_guest_rpm_limit
            rpd_limit = settings.circuit_guest_rpd_limit
        else:
            rpm_limit = settings.circuit_member_rpm_limit
            rpd_limit = settings.circuit_member_rpd_limit

        # 1. Minute Counter (unix timestamp // 60) with 90-second TTL (NX expire)
        minute_bucket = int(time.time() // 60)
        rpm_key = f"circuit:rpm:{norm_role}:{minute_bucket}"

        # 2. Daily Counter (KST date string) with 48-hour TTL
        kst = timezone(timedelta(hours=9))
        date_bucket = datetime.now(kst).strftime("%Y%m%d")
        rpd_key = f"circuit:rpd:{norm_role}:{date_bucket}"

        if not hasattr(self, "_circuit_lock"):
            import asyncio

            self._circuit_lock = asyncio.Lock()

        async with self._circuit_lock:
            # Check existing values first before incrementing to avoid burning counter on tripped circuit
            current_rpm = await self.get_int(rpm_key)
            if current_rpm >= rpm_limit:
                logger.warning(
                    "Circuit breaker TRIPPED [RPM] for role %s: %d >= limit %d",
                    norm_role,
                    current_rpm,
                    rpm_limit,
                )
                return True, "rpm"

            current_rpd = await self.get_int(rpd_key)
            if current_rpd >= rpd_limit:
                logger.warning(
                    "Circuit breaker TRIPPED [RPD] for role %s: %d >= limit %d",
                    norm_role,
                    current_rpd,
                    rpd_limit,
                )
                return True, "rpd"

            # Atomically increment RPM and RPD
            new_rpm = await self.incr(rpm_key, ex=90, nx_expire=True)
            new_rpd = await self.incr(rpd_key, ex=172800, nx_expire=True)

            if new_rpm > rpm_limit:
                logger.warning(
                    "Circuit breaker TRIPPED [RPM race] for role %s: %d > limit %d",
                    norm_role,
                    new_rpm,
                    rpm_limit,
                )
                return True, "rpm"

            if new_rpd > rpd_limit:
                logger.warning(
                    "Circuit breaker TRIPPED [RPD race] for role %s: %d > limit %d",
                    norm_role,
                    new_rpd,
                    rpd_limit,
                )
                return True, "rpd"

            return False, None


_session_manager: Optional[RedisSessionManager] = None


def get_redis_session_manager() -> RedisSessionManager:
    """Return singleton RedisSessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = RedisSessionManager()
    return _session_manager
