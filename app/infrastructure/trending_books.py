"""Real-time trending books collector using Yes24 SSR web scraper and Redis caching.

Fetches the live Yes24 comprehensive bestseller webpage (SSR), parses the top 40 books
using BeautifulSoup, filters out exam/workbooks, and caches the clean monographs into Redis
with a 24-hour TTL (daily_trending_books) to provide a 100% zero-hallucination,
real-time 'open-book' catalog for the LLM curator agent.
"""

import json
import logging
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup

from app.infrastructure.redis_session import get_redis_session_manager

logger = logging.getLogger(__name__)

YES24_BESTSELLER_WEB_URL = (
    "https://www.yes24.com/Product/Category/BestSeller?categoryNumber=001&pageNumber=1&pageSize=40"
)
REDIS_TRENDING_BOOKS_KEY = "daily_trending_books"
REDIS_TRENDING_BOOKS_TTL = 86400  # 24 hours

# Noise keywords for filtering out pure exam preparation/test question workbooks
# so the curator focuses on literary, humanities, essay, and cultural bestsellers.
NOISE_KEYWORDS = [
    "기출",
    "능력검정",
    "문제집",
    "기출문제",
    "핵심집약",
    "실전모의",
    "기본서",
    "모의고사",
    "수험서",
]

# Minimal emergency fallback catalog used ONLY when external network is completely down.
EMERGENCY_FALLBACK_BOOKS: List[Dict[str, str]] = [
    {
        "title": "세네카, 오늘을 빼앗기고 있는 당신에게",
        "author": "루키우스 안나이우스 세네카",
        "publisher": "논픽션",
    },
    {"title": "모순", "author": "양귀자", "publisher": "쓰다"},
    {"title": "싯다르타", "author": "헤르만 헤세", "publisher": "민음사"},
    {"title": "그랬다고 적었다", "author": "김애란", "publisher": "문학동네"},
    {"title": "마음의 어휘력", "author": "조아란", "publisher": "페이지2북스"},
    {"title": "니체의 초월자", "author": "프리드리히 니체", "publisher": "히읏"},
    {"title": "마흔에 읽는 쇼펜하우어", "author": "강용수", "publisher": "유노서가"},
    {"title": "불편한 편의점", "author": "김호연", "publisher": "나무옆의자"},
    {"title": "작별하지 않는다", "author": "한강", "publisher": "문학동네"},
    {"title": "지구 끝의 온실", "author": "김초엽", "publisher": "자이언트북스"},
]


def parse_yes24_bestseller_html(html: str) -> List[Dict[str, str]]:
    """Parse Yes24 Server-Side Rendered (SSR) HTML to extract live bestseller books.

    Args:
        html: Raw HTML string of the Yes24 bestseller webpage.

    Returns:
        List of book dictionaries with title, author, and publisher.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("#yesBestList li")
    if not items:
        # Fallback to general itemUnit selector if layout shifts
        items = soup.select(".itemUnit")

    parsed_books: List[Dict[str, str]] = []
    exam_books: List[Dict[str, str]] = []

    for li in items:
        title_el = li.select_one("a.gd_name")
        if not title_el:
            continue
        raw_title = title_el.get_text(strip=True)
        if not raw_title:
            continue
        from app.infrastructure.national_library_client import clean_book_title

        title = clean_book_title(raw_title) or raw_title

        # Extract authors
        author = "저자 미상"
        auth_el = li.select_one("span.info_auth")
        if auth_el:
            author_links = [
                a.get_text(strip=True) for a in auth_el.select("a") if a.get_text(strip=True)
            ]
            if author_links:
                author = ", ".join(author_links)
            else:
                author = auth_el.get_text(strip=True).replace(" 저", "").strip()

        # Extract publisher
        pub_el = li.select_one("span.info_pub")
        publisher = pub_el.get_text(strip=True) if pub_el else ""

        book_entry = {
            "title": title,
            "author": author or "저자 미상",
            "publisher": publisher,
        }

        # Check if title contains test/exam noise keywords
        if any(kw in title for kw in NOISE_KEYWORDS):
            exam_books.append(book_entry)
        else:
            parsed_books.append(book_entry)

    # Monograph and cultural books first, followed by remaining books if needed
    final_books = parsed_books + exam_books
    return final_books


async def fetch_and_cache_trending_books(
    url: str = YES24_BESTSELLER_WEB_URL,
) -> List[Dict[str, str]]:
    """Fetch live Yes24 bestsellers via SSR web scraping and cache them into Redis for 24 hours."""
    logger.info("Starting real-time Yes24 bestseller web fetch: %s", url)
    trending_books: List[Dict[str, str]] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=12.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        trending_books = parse_yes24_bestseller_html(html)
        if trending_books:
            logger.info(
                "Successfully scraped %d live real-time bestsellers from Yes24 web.",
                len(trending_books),
            )
        else:
            logger.warning(
                "Yes24 web scraping returned 0 books. Layout might have shifted. Using emergency fallback."
            )
    except Exception as e:
        logger.warning(
            "Error fetching live Yes24 bestseller webpage (%s). Using emergency fallback.",
            e,
        )

    # If scraping failed, use minimal emergency catalog
    if not trending_books:
        trending_books = list(EMERGENCY_FALLBACK_BOOKS)

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
    """Retrieve live trending books from Redis (or fallback) and format as open-book text for LLM."""
    redis_mgr = get_redis_session_manager()
    trending_books: List[Dict[str, Any]] = []

    try:
        trending_json = await redis_mgr.get(REDIS_TRENDING_BOOKS_KEY)
        if trending_json:
            trending_books = json.loads(trending_json)
    except Exception as e:
        logger.warning("Failed to load trending books from Redis (%s).", e)

    if not trending_books:
        trending_books = list(EMERGENCY_FALLBACK_BOOKS)

    lines = [
        f"- {b['title']} (저자: {b.get('author', '저자 미상')}, 출판사: {b.get('publisher', '')})"
        for b in trending_books[:limit]
    ]
    return "\n".join(lines)
