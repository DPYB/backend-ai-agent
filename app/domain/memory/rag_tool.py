"""Personalization RAG tool for querying member's scrap memory (scrap_vector)."""

import hashlib
import logging
from typing import List

from langchain_core.tools import tool

from app.core.config import settings
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def generate_query_embedding(query: str, dimension: int = 768) -> List[float]:
    """Generate embedding vector using Google Gemini or deterministic fallback."""
    if settings.gemini_api_key:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            embeddings = GoogleGenerativeAIEmbeddings(  # type: ignore[call-arg]
                model=settings.gemini_embedding_model,
                google_api_key=settings.gemini_api_key,
            )
            return embeddings.embed_query(query)
        except Exception as e:
            logger.warning("Gemini embedding generation failed (%s), using fallback.", e)

    # Deterministic pseudo-embedding for testing or offline environment
    seed = int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16)
    vector = [((seed + i * 37) % 1000) / 1000.0 for i in range(dimension)]
    norm = sum(x * x for x in vector) ** 0.5 or 1.0
    return [x / norm for x in vector]


@tool("search_scrap_memory")
async def search_scrap_memory(member_id: str, query: str) -> str:
    """사용자 본인이 과거에 책을 읽고 남긴 스크랩(인상 깊은 문장, 개인 메모) 기록을 검색합니다.

    이 도구는 오직 '개인화 독서 기억' 전용이며, 새로운 도서 추천에는 사용되지 않습니다.
    사용자의 독서 취향, 과거 느꼈던 감정, 인용 문장을 대화에 자연스럽게 녹여낼 때 호출합니다.

    Args:
        member_id: 사용자의 고유 식별자 (UUID)
        query: 검색할 키워드, 감정, 문맥 또는 주제

    Returns:
        사용자의 스크랩 인용문과 개인 메모가 포함된 텍스트 결과
    """
    logger.info("Searching scrap memory for member_id=%s, query='%s'", member_id, query)
    # Bypass for unauthenticated guest users
    if (
        not member_id
        or member_id in ("None", "guest", "undefined")
        or member_id.startswith("guest-")
    ):
        logger.info("Skipping search_scrap_memory: Unauthenticated guest user.")
        return "현재 로그인하지 않은 게스트 상태이므로 저장된 개인 독서 스크랩 및 메모 기억이 없습니다."

    try:
        embedding = generate_query_embedding(query)
        client = get_supabase_client()
        scraps = await client.search_member_scraps(
            member_id=member_id,
            query_embedding=embedding,
            match_threshold=0.3,
            match_count=3,
        )

        if not scraps:
            return f"사용자({member_id})의 스크랩 기록에서 '{query}'와 관련된 문장이나 메모를 찾지 못했습니다."

        results = []
        for i, scrap in enumerate(scraps, 1):
            book_title = scrap.get("book_title", "제목 미상")
            content = scrap.get("content", "").strip()
            memo = scrap.get("memo", "").strip()
            item_str = f'[{i}] 책: <{book_title}>\n- 남긴 문장: "{content}"'
            if memo:
                item_str += f"\n- 독자 메모: {memo}"
            results.append(item_str)

        return "\n\n".join(results)

    except Exception as e:
        logger.error("Error in search_scrap_memory: %s", e)
        return f"스크랩 기억 조회 중 오류가 발생했습니다: {str(e)}"
