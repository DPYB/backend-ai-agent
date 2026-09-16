"""Tavily Web Search API client — lightweight async REST client.

Uses pure httpx without heavy SDK dependencies.
Free Tier: 1,000 monthly requests, $0 Zero-cost.
Docs: https://docs.tavily.com/
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TavilySearchClient:
    """Lightweight async Tavily Web Search REST client for on-demand book discovery."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 4.0,
    ) -> None:
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = (settings.tavily_api_key or "").strip()
        self.api_url = (api_url or settings.tavily_api_url).strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Return True if a valid Tavily Search API key is configured."""
        return bool(self.api_key) and not self.api_key.startswith("tvly-your_")

    async def search(
        self,
        query: str,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search the web for book candidates using Tavily REST API.

        Args:
            query: Search query string (Korean keywords).
            count: Number of results to return (max 10).

        Returns:
            List of search result dicts with keys: title, content, url.
        """
        if not self.is_configured:
            logger.debug("Tavily Search API key not configured, returning empty results.")
            return []

        if settings.is_testing:
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": min(count, 10),
            "include_answer": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_results = data.get("results", [])
                return [
                    {
                        "title": r.get("title", ""),
                        "content": r.get("content", ""),
                        "url": r.get("url", ""),
                    }
                    for r in raw_results
                ]
        except Exception as e:
            logger.warning("Tavily Search API call failed (%s). Graceful fallback.", e)
            return []


_tavily_search_client: Optional[TavilySearchClient] = None


def get_tavily_search_client() -> TavilySearchClient:
    """Return singleton TavilySearchClient instance."""
    global _tavily_search_client
    if _tavily_search_client is None:
        _tavily_search_client = TavilySearchClient()
    return _tavily_search_client
