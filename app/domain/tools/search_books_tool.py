"""On-demand recent and trending book search tool using lightweight Tavily REST search.

Curator sub-agent or persona agents call this when they need fresh trending titles
from the web (e.g. viral books on SNS, 2025 literary awards, breaking new releases).
"""

import logging
import re
from typing import Any, Dict, List

from langchain_core.tools import tool

from app.infrastructure.tavily_search_client import get_tavily_search_client

logger = logging.getLogger(__name__)

# Noise patterns to clean from web result titles
_TITLE_NOISE_PATTERN = re.compile(
    r"(?:베스트셀러|도서|책|서평|읽기|독서|추천|알라딘|yes24|교보|인터파크|리뷰|줄거리|요약|목차|저자|작가)",
    re.IGNORECASE,
)


def _extract_book_candidates_from_results(
    results: List[Dict[str, Any]],
    max_candidates: int = 5,
) -> List[Dict[str, str]]:
    """Parse web search results into structured book candidate dicts."""
    candidates: List[Dict[str, str]] = []
    seen_titles: set[str] = set()

    for result in results:
        raw_title = result.get("title", "").strip()
        snippet = result.get("content", "").strip()

        # Strip common noise words from web result titles
        clean = _TITLE_NOISE_PATTERN.sub("", raw_title).strip(" -|·:[]()")

        # Try to extract book title enclosed in brackets/quotes: 《...》, <...>, 「...」, '...'
        bracket_match = re.search(r"[《〈「『\'\"](.*?)[》〉」』\'\"]", clean)
        if bracket_match:
            candidate_title = bracket_match.group(1).strip()
        else:
            candidate_title = clean

        # Filter out very short or duplicate titles
        normalized = re.sub(r"\s+", "", candidate_title).lower()
        if len(normalized) < 2 or normalized in seen_titles:
            continue

        seen_titles.add(normalized)
        candidates.append(
            {
                "candidate_title": candidate_title,
                "snippet": snippet[:200],
                "url": result.get("url", ""),
            }
        )

        if len(candidates) >= max_candidates:
            break

    return candidates


@tool("search_recent_books")
async def search_recent_books(query: str, count: int = 3) -> str:
    """최근 출간된 화제의 신간이나 웹에서 유행하는 트렌드 도서를 실시간 웹 검색으로 탐색합니다.

    사서/토론 에이전트가 최신 유행 도서, SNS 화제작, 문학상 수상작 등 실시간 정보가 필요할 때 호출합니다.

    Args:
        query: 검색할 도서 주제, 장르, 키워드 (예: '2025 화제 소설 신간', 'SNS 역주행 감성 에세이')
        count: 검색할 후보 수 (기본 3, 최대 5)

    Returns:
        신간 도서 후보 제목 및 설명 목록 (텍스트 형식)
    """
    logger.info("search_recent_books called: query='%s', count=%d", query, count)

    tavily_client = get_tavily_search_client()
    if not tavily_client.is_configured:
        return "웹 검색 API가 설정되지 않아 실시간 웹 탐색을 건너뜁니다."

    enriched_query = f"{query} 신간 도서 추천 책"
    results = await tavily_client.search(query=enriched_query, count=min(count * 2, 8))

    candidates = _extract_book_candidates_from_results(results, max_candidates=count)
    if not candidates:
        return f"'{query}' 관련 도서 후보를 추출하지 못했습니다."

    # Verify candidates against National Library 4-stage validation chain
    from app.infrastructure.national_library_client import (
        genre_to_korean,
        get_national_library_client,
    )

    nl_client = get_national_library_client()
    verified_entries: List[str] = []

    for i, c in enumerate(candidates, 1):
        cand_title = c["candidate_title"]
        snippet = c["snippet"][:100] + "..." if len(c["snippet"]) > 100 else c["snippet"]

        biblio = await nl_client.search_book(title=cand_title)
        if biblio and biblio.get("isbn"):
            real_title = biblio.get("title", cand_title)
            real_author = biblio.get("author", "저자 미상")
            real_publisher = biblio.get("publisher", "")
            real_isbn = biblio.get("isbn", "")
            real_pages = biblio.get("page_count")
            genre_name = genre_to_korean(biblio.get("genre", ""))

            meta_parts = [f"저자: {real_author}"]
            if real_publisher:
                meta_parts.append(f"출판사: {real_publisher}")
            if real_isbn:
                meta_parts.append(f"ISBN: {real_isbn}")
            if real_pages:
                meta_parts.append(f"쪽수: {real_pages}쪽")
            if genre_name:
                meta_parts.append(f"장르: {genre_name}")

            meta_str = " | ".join(meta_parts)
            verified_entries.append(
                f"{i}. 《{real_title}》 (국립도서관 정식 서지 검증 완료)\n"
                f"   - 서지 정보: {meta_str}\n"
                f"   - 웹 맥락: {snippet}"
            )
        else:
            verified_entries.append(f"{i}. {cand_title}\n   └ {snippet}")

    lines = [f"[실시간 웹 신간 탐색 및 서지 검증 결과: '{query}']"] + verified_entries
    return "\n".join(lines)
