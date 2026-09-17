"""Trending books collector and Redis caching worker.

Fetches the Yes24 comprehensive bestseller RSS feed, parses the top 50 books,
and caches them in Redis with a 24-hour TTL (daily_trending_books)
to provide an 'open-book' catalog for the LLM curator agent.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import feedparser

from app.infrastructure.redis_session import get_redis_session_manager

logger = logging.getLogger(__name__)

YES24_BESTSELLER_RSS_URL = "https://www.yes24.com/rss/bestseller?categoryNumber=001"
REDIS_TRENDING_BOOKS_KEY = "daily_trending_books"
REDIS_TRENDING_BOOKS_TTL = 86400  # 24 hours

# Robust default trending books pool (2024~2026 notable steady-sellers and recent bestsellers)
# Used as offline/fallback open-book data if RSS feed is unreachable.
DEFAULT_TRENDING_BOOKS: List[Dict[str, str]] = [
    {
        "title": "마흔에 읽는 쇼펜하우어",
        "author": "강용수",
        "description": "삶의 고통을 덜어주는 철학",
    },
    {"title": "불편한 편의점", "author": "김호연", "description": "따스한 골목길 위로의 이야기"},
    {"title": "모순", "author": "양귀자", "description": "인생의 모순과 사랑에 대한 성찰"},
    {
        "title": "시대예보: 핵개인의 시대",
        "author": "송길영",
        "description": "미래 사회 변화와 개인의 생존 전략",
    },
    {
        "title": "아주 작은 습관의 힘",
        "author": "제임스 클리어",
        "description": "매일 1%씩 달라지는 삶의 변화",
    },
    {"title": "세이노의 가르침", "author": "세이노", "description": "치열한 현실을 살아가는 지혜"},
    {
        "title": "도둑맞은 집중력",
        "author": "요한 하리",
        "description": "집중력 위기의 현대 사회 탐구",
    },
    {
        "title": "도시와 그 불확실한 벽",
        "author": "무라카미 하루키",
        "description": "기억과 영혼의 미로를 걷는 소설",
    },
    {"title": "밝은 밤", "author": "최은영", "description": "백 년에 걸친 여성들의 연대와 치유"},
    {"title": "눈부신 안부", "author": "백수린", "description": "상실의 상처를 보듬는 다정한 문학"},
    {
        "title": "물고기는 존재하지 않는다",
        "author": "룰루 밀러",
        "description": "과학과 상실의 아름다운 조우",
    },
    {"title": "단 한 사람", "author": "최진영", "description": "소멸과 구원의 경계에 선 서사"},
    {
        "title": "죽고 싶지만 떡볶이는 먹고 싶어",
        "author": "백세희",
        "description": "일상의 가벼운 우울을 보듬는 에세이",
    },
    {
        "title": "어서 오세요, 휴남동 서점입니다",
        "author": "황보름",
        "description": "책과 사람의 온기가 머무는 곳",
    },
    {
        "title": "이처럼 사소한 것들",
        "author": "클레어 키건",
        "description": "용기와 침묵을 깨는 짧고 깊은 감동",
    },
]


async def fetch_and_cache_trending_books(
    rss_url: str = YES24_BESTSELLER_RSS_URL,
) -> List[Dict[str, str]]:
    """Fetch top trending books from RSS feed and cache them in Redis for 24 hours."""
    logger.info("Starting trending books fetch from RSS: %s", rss_url)
    trending_books: List[Dict[str, str]] = []

    try:
        # Parse RSS asynchronously to prevent blocking the event loop
        feed: Any = await asyncio.to_thread(feedparser.parse, rss_url)

        entries = getattr(feed, "entries", [])
        for entry in entries[:50]:
            title = str(getattr(entry, "title", "")).strip()
            author = str(getattr(entry, "author", "저자 미상")).strip()
            description = str(getattr(entry, "description", "")).strip()

            if title:
                trending_books.append(
                    {
                        "title": title,
                        "author": author or "저자 미상",
                        "description": description[:200],
                    }
                )

        logger.info("Parsed %d books from Yes24 RSS feed.", len(trending_books))
    except Exception as e:
        logger.warning("Error fetching/parsing Yes24 RSS feed (%s). Using fallback pool.", e)

    # If RSS was empty or failed, use robust default pool
    if not trending_books:
        trending_books = list(DEFAULT_TRENDING_BOOKS)

    # Cache into Redis
    try:
        redis_mgr = get_redis_session_manager()
        cache_data = json.dumps(trending_books, ensure_ascii=False)
        await redis_mgr.set(REDIS_TRENDING_BOOKS_KEY, cache_data, ex=REDIS_TRENDING_BOOKS_TTL)
        logger.info("Successfully cached %d trending books to Redis.", len(trending_books))
    except Exception as e:
        logger.error("Failed to cache trending books into Redis: %s", e)

    return trending_books


async def get_trending_books_text(limit: int = 30) -> str:
    """Retrieve trending books from Redis (or fallback) and format as open-book text for LLM."""
    redis_mgr = get_redis_session_manager()
    trending_books: Optional[List[Dict[str, str]]] = None

    try:
        trending_json = await redis_mgr.get(REDIS_TRENDING_BOOKS_KEY)
        if trending_json:
            trending_books = json.loads(trending_json)
    except Exception as e:
        logger.warning("Failed to load trending books from Redis (%s).", e)

    if not trending_books:
        trending_books = DEFAULT_TRENDING_BOOKS

    lines = [
        f"- {b['title']} (저자: {b.get('author', '저자 미상')})" for b in trending_books[:limit]
    ]
    return "\n".join(lines)
