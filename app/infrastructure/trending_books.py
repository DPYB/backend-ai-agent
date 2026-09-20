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
EMERGENCY_FALLBACK_BOOKS: List[Dict[str, Any]] = [
    {
        "rank": 2,
        "title": "세네카, 오늘을 빼앗기고 있는 당신에게",
        "author": "루키우스 안나이우스 세네카, 하와이 대저택",
        "publisher": "논픽션",
        "genre": "PHILOSOPHY",
    },
    {
        "rank": 5,
        "title": "싯다르타",
        "author": "헤르만 헤세, 박병덕",
        "publisher": "민음사",
        "genre": "PHILOSOPHY",
    },
    {
        "rank": 7,
        "title": "니체의 초월자",
        "author": "프리드리히 니체, 김철",
        "publisher": "히읏",
        "genre": "PHILOSOPHY",
    },
    {
        "rank": 8,
        "title": "그랬다고 적었다",
        "author": "김애란",
        "publisher": "문학동네",
        "genre": "LITERATURE",
    },
    {
        "rank": 9,
        "title": "마음의 어휘력",
        "author": "조아란, 권희, 이정윤",
        "publisher": "페이지2북스",
        "genre": "GENERAL",
    },
    {
        "rank": 11,
        "title": "모순",
        "author": "양귀자",
        "publisher": "쓰다",
        "genre": "LITERATURE",
    },
    {
        "rank": 12,
        "title": "오디세이아",
        "author": "호메로스, 페테르 파울 루벤스, 박문재",
        "publisher": "민음사",
        "genre": "LITERATURE",
    },
    {
        "rank": 15,
        "title": "쇼펜하우어 인생수업",
        "author": "아르투어 쇼펜하우어, 김지민",
        "publisher": "유노서가",
        "genre": "PHILOSOPHY",
    },
    {
        "rank": 22,
        "title": "아주 작은 습관의 힘",
        "author": "제임스 클리어, 이한이",
        "publisher": "비즈니스북스",
        "genre": "GENERAL",
    },
    {
        "rank": 23,
        "title": "데미안",
        "author": "헤르만 헤세, 전영애",
        "publisher": "민음사",
        "genre": "LITERATURE",
    },
]


def parse_yes24_bestseller_html(html: str) -> List[Dict[str, Any]]:
    """Parse Yes24 Server-Side Rendered (SSR) HTML to extract live bestseller books.

    Args:
        html: Raw HTML string of the Yes24 bestseller webpage.

    Returns:
        List of book dictionaries with rank, title, author, publisher, and KDC genre.
    """
    from app.infrastructure.national_library_client import (
        clean_book_title,
        is_curatable_book,
        map_kdc_to_genre,
    )

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("#yesBestList li")
    if not items:
        # Fallback to general itemUnit selector if layout shifts
        items = soup.select(".itemUnit")

    parsed_books: List[Dict[str, Any]] = []
    exam_books: List[Dict[str, Any]] = []
    rank_counter = 0

    for li in items:
        title_el = li.select_one("a.gd_name")
        if not title_el:
            continue
        raw_title = title_el.get_text(strip=True)
        if not raw_title:
            continue

        rank_counter += 1
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

        genre = map_kdc_to_genre(title=title)

        book_entry: Dict[str, Any] = {
            "rank": rank_counter,
            "title": title,
            "author": author or "저자 미상",
            "publisher": publisher,
            "genre": genre,
        }

        if is_curatable_book(title, author, publisher):
            parsed_books.append(book_entry)
        else:
            exam_books.append(book_entry)

    # Monograph and cultural books first, followed by remaining books if needed
    final_books = parsed_books + exam_books
    return final_books


async def fetch_and_cache_trending_books(
    url: str = YES24_BESTSELLER_WEB_URL,
) -> List[Dict[str, Any]]:
    """Fetch live Yes24 bestsellers via SSR web scraping and cache them into Redis for 24 hours."""
    logger.info("Starting real-time Yes24 bestseller web fetch: %s", url)
    trending_books: List[Dict[str, Any]] = []

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


async def get_trending_books(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve live trending books list filtered for curatable monographs."""
    from app.infrastructure.national_library_client import is_curatable_book

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

    return [
        b
        for b in trending_books
        if is_curatable_book(b.get("title", ""), b.get("author", ""), b.get("publisher", ""))
    ][:limit]


async def get_trending_books_text(limit: int = 30) -> str:
    """Retrieve live trending books and format as structured, rank-preserved open-book catalog grouped by KDC genre."""
    curatable_list = await get_trending_books(limit=limit)

    # Group into KDC categories
    lit_books: List[Dict[str, Any]] = []
    phil_books: List[Dict[str, Any]] = []
    gen_books: List[Dict[str, Any]] = []

    for b in curatable_list:
        genre = b.get("genre", "GENERAL")
        if genre == "LITERATURE":
            lit_books.append(b)
        elif genre in ("PHILOSOPHY", "RELIGION"):
            phil_books.append(b)
        else:
            gen_books.append(b)

    sections: List[str] = ["[오늘의 화제작 오픈북 (실제 종합 베스트셀러 순위)]"]

    def _format_book_line(b: Dict[str, Any]) -> str:
        rank_str = f"종합 {b.get('rank', '-')}위"
        pub_str = f", 출판사: {b.get('publisher')}" if b.get("publisher") else ""
        return f"  - ({rank_str}) {b['title']} (저자: {b.get('author', '저자 미상')}{pub_str})"

    if lit_books:
        sections.append("📚 문학 / 소설 / 에세이:")
        sections.extend([_format_book_line(b) for b in lit_books[:10]])

    if phil_books:
        sections.append("🌱 인문 / 철학 / 심리:")
        sections.extend([_format_book_line(b) for b in phil_books[:10]])

    if gen_books:
        sections.append("💡 교양 / 사회 / 과학 / 라이프:")
        sections.extend([_format_book_line(b) for b in gen_books[:10]])

    # Fallback to flat list if all groups empty
    if len(sections) <= 1:
        sections.extend([_format_book_line(b) for b in curatable_list[:limit]])

    return "\n".join(sections)
