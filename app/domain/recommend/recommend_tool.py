"""Book recommendation tool using Tavily web search, National Library 4-stage validation chain, and Redis caching.

Dual-Track Hybrid Architecture:
  - 1-Track (Exploration): Tavily lightweight REST search for trending/viral books (Free Tier: 1,000/mo)
  - 2-Track (Verification): National Library of Korea 4-stage monograph validation chain (Public Open API)
  - 3-Track (Presentation): Kyobo CDN verified high-res cover binding (0ms server latency)
  - 4-Track (Caching): Redis TTL caching (1 hour) to defend against duplicate API calls
  - Graceful Fallback: 100% functional even when Tavily is offline/unconfigured
"""

import hashlib
import json
import logging
from typing import Any, Dict, List

from langchain_core.tools import tool

from app.core.config import settings
from app.infrastructure.national_library_client import get_national_library_client
from app.infrastructure.redis_session import get_redis_session_manager

logger = logging.getLogger(__name__)


async def _search_web_book_candidates(query: str, count: int) -> List[Dict[str, str]]:
    """Search for book title candidates using Tavily Web Search (on-demand, graceful degradation)."""
    from app.domain.recommend.search_books_tool import _extract_book_candidates_from_results
    from app.infrastructure.tavily_search_client import get_tavily_search_client

    tavily_client = get_tavily_search_client()
    if not tavily_client.is_configured or settings.is_testing:
        return []

    enriched_query = f"{query} 신간 도서 추천 베스트셀러"
    results = await tavily_client.search(query=enriched_query, count=count * 2)
    return _extract_book_candidates_from_results(results, max_candidates=count)


@tool("recommend_books")
async def recommend_books(query: str, count: int = 2) -> str:
    """사용자의 취향, 장르, 감정, 현재 고민에 어울리는 새로운 책을 추천합니다.

    실시간 웹 트렌드 탐색(Tavily) + 국립중앙도서관 4단계 실전 검증 체인 + 교보문고 표지 연동 + Redis 캐싱을 결합합니다.
    (개인 스크랩 기억 조회는 search_scrap_memory를 사용하며 이 도구와 혼용하지 않습니다.)

    Args:
        query: 추천을 원하는 키워드, 장르, 주제 또는 독서 동기
               (예: '위로가 되는 SF 소설', '생각을 비우는 에세이')
        count: 추천받을 권수 (기본 2권)

    Returns:
        추천 도서 제목, 저자, 출판사, 추천 사유가 담긴 설명 텍스트
    """
    logger.info("Recommending books for query='%s', count=%d", query, count)
    redis_mgr = get_redis_session_manager()
    cache_key = hashlib.md5(f"recommend:{query}:{count}".encode("utf-8")).hexdigest()

    # 1. Check Redis cache to defend against duplicate API calls
    cached = await redis_mgr.get_cached_recommendation(cache_key)
    if cached:
        logger.info("Cache hit for recommendation query: %s", query)
        return json.dumps(cached, ensure_ascii=False, indent=2)

    nl_client = get_national_library_client()
    recommendations: List[Dict[str, Any]] = []

    # 2. Try real-time web search via Tavily for trending titles (if configured)
    web_candidates = await _search_web_book_candidates(query, count)

    if web_candidates:
        for candidate in web_candidates[:count]:
            title = candidate["candidate_title"]
            biblio = await nl_client.search_book(title)
            if biblio and biblio.get("isbn"):
                recommendations.append(
                    {
                        "title": biblio.get("title", title),
                        "author": biblio.get("author", "저자 미상"),
                        "publisher": biblio.get("publisher", "출판사"),
                        "isbn": biblio.get("isbn", ""),
                        "cover_url": biblio.get("cover_url", ""),
                        "page_count": biblio.get("page_count"),
                        "genre": biblio.get("genre"),
                        "curation_reason": candidate.get(
                            "snippet", "독자님의 요청에 맞춰 실시간 웹에서 엄선한 도서입니다."
                        ),
                        "source": biblio.get("source", "NATIONAL_LIBRARY"),
                    }
                )

    # 3. Fallback: use embedded hybrid catalog if web search returned insufficient verified titles
    if not recommendations:
        fallback_titles = _get_fallback_titles_for_query(query, count)
        for title_info in fallback_titles:
            biblio = await nl_client.search_book(
                title=title_info["title"],
                author=title_info.get("author", ""),
            )
            if biblio:
                recommendations.append(
                    {
                        "title": biblio.get("title", title_info["title"]),
                        "author": biblio.get("author", title_info.get("author", "저자 미상")),
                        "publisher": biblio.get("publisher", "출판사"),
                        "isbn": biblio.get("isbn", ""),
                        "cover_url": biblio.get("cover_url", ""),
                        "page_count": biblio.get("page_count"),
                        "genre": biblio.get("genre"),
                        "curation_reason": title_info.get(
                            "reason", "독자님의 요청에 맞춰 엄선한 도서입니다."
                        ),
                        "source": biblio.get("source", "NATIONAL_LIBRARY_FALLBACK_CATALOG"),
                    }
                )

    # 4. Save to Redis cache
    if recommendations:
        await redis_mgr.set_cached_recommendation(cache_key, recommendations)

    # 5. Format human-readable response for the Persona Head Agent
    if not recommendations:
        return f"'{query}' 주제의 추천 도서를 찾지 못했습니다. 다른 키워드로 시도해보세요."

    formatted_items = []
    for i, rec in enumerate(recommendations, 1):
        item = (
            f"[{i}] 《{rec['title']}》\n"
            f"- 저자/출판사: {rec['author']} | {rec['publisher']}\n"
            f"- ISBN: {rec['isbn']}\n"
            f"- 추천 이유: {rec['curation_reason']}"
        )
        formatted_items.append(item)

    return "\n\n".join(formatted_items)


def _get_fallback_titles_for_query(query: str, count: int) -> List[Dict[str, str]]:
    """Return keyword-matched title candidates from embedded hybrid catalog (recent + classic)."""
    # Keyword → (recent title, classic title) pairs
    keyword_map: List[tuple[List[str], Dict[str, str], Dict[str, str]]] = [
        (
            ["우울", "울적", "힘들", "슬프", "지친", "피곤"],
            {
                "title": "죽고 싶지만 떡볶이는 먹고 싶어",
                "author": "백세희",
                "reason": "가벼운 우울과 일상의 온기를 함께 담은 진솔한 기록",
            },
            {
                "title": "바람이 분다 당신이 좋다",
                "author": "이병률",
                "reason": "쓸쓸한 감성에 울림을 주는 감성 산문의 고전",
            },
        ),
        (
            ["성장", "용기", "도전", "자아", "나", "인생"],
            {
                "title": "아몬드",
                "author": "손원평",
                "reason": "감정을 찾아가는 특별한 성장 이야기",
            },
            {
                "title": "데미안",
                "author": "헤르만 헤세",
                "reason": "내면의 알을 깨고 진정한 자신을 마주하는 불멸의 고전",
            },
        ),
        (
            ["철학", "인문", "사유", "삶", "의미", "생각"],
            {
                "title": "소크라테스 익스프레스",
                "author": "에릭 와이너",
                "reason": "14명의 철학자와 함께하는 유쾌한 삶의 여정",
            },
            {
                "title": "이방인",
                "author": "알베르 카뮈",
                "reason": "부조리한 세상과 정직하게 맞선 인간의 실존적 초상",
            },
        ),
        (
            ["역사", "사회", "세계", "문명", "정치"],
            {
                "title": "사피엔스",
                "author": "유발 하라리",
                "reason": "인류 문명의 거대한 흐름을 파헤친 기념비적 저작",
            },
            {
                "title": "총, 균, 쇠",
                "author": "재레드 다이아몬드",
                "reason": "지리 환경과 문명 불평등의 비밀을 규명한 역작",
            },
        ),
        (
            ["과학", "우주", "자연", "기술", "물리"],
            {
                "title": "물고기는 존재하지 않는다",
                "author": "룰루 밀러",
                "reason": "과학과 삶의 의미를 함께 탐구하는 매혹적인 논픽션",
            },
            {
                "title": "코스모스",
                "author": "칼 세이건",
                "reason": "광대한 우주 속 인류의 숭고한 탐구 여정",
            },
        ),
    ]

    selected: List[Dict[str, str]] = []
    for keywords, recent, classic in keyword_map:
        if any(kw in query for kw in keywords):
            selected = [recent, classic]
            break

    if not selected:
        selected = [
            {
                "title": "달러구트 꿈 백화점",
                "author": "이미예",
                "reason": "몽환적이고 따스한 판타지로 일상을 환기시키는 화제작",
            },
            {
                "title": "어린 왕자",
                "author": "앙투안 드 생텍쥐페리",
                "reason": "마음의 눈으로 본질을 바라보게 해주는 영혼의 쉼표",
            },
        ]

    return selected[:count]
