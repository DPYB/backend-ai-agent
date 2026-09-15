"""Personalized debate memory tool for recalling past debate insights (agent.debate_insights)."""

import logging
from typing import Any, Dict, List

from langchain_core.tools import tool

from app.domain.memory.rag_tool import generate_query_embedding
from app.infrastructure.db.repository import get_agent_vector_repository

logger = logging.getLogger(__name__)


@tool("search_debate_memory")
async def search_debate_memory(member_id: str, query: str) -> str:
    """사용자가 과거에 AI 토론 파트너(평론가, 이야기꾼, 상담사, 관찰가)와 나누었던 토론 기록과 통찰 요약을 검색합니다.

    이 도구는 오직 '과거 독서 토론 기억 회상' 전용입니다.
    사용자가 과거에 읽고 토론했던 책의 주제, 나누었던 생각, 철학적/심리적 화두, 총평을 대화에 반영할 때 호출합니다.

    Args:
        member_id: 사용자의 고유 식별자 (UUID)
        query: 검색할 주제, 책 제목, 화두, 질문 또는 키워드

    Returns:
        사용자의 과거 토론 도서, 토론 파트너, 핵심 논제, 나눈 생각 및 총평 요약 텍스트
    """
    logger.info("Searching debate memory for member_id=%s, query='%s'", member_id, query)

    # Bypass for unauthenticated guest users
    if (
        not member_id
        or member_id in ("None", "guest", "undefined")
        or member_id.startswith("guest-")
    ):
        logger.info("Skipping search_debate_memory: Unauthenticated guest user.")
        return "현재 로그인하지 않은 게스트 상태이므로 과거 독서 토론 통찰 기억이 없습니다."

    try:
        embedding = generate_query_embedding(query)
        repo = get_agent_vector_repository()
        insights: List[Dict[str, Any]] = await repo.search_member_debate_insights(
            member_id=member_id,
            query_embedding=embedding,
            match_threshold=0.3,
            match_count=3,
        )

        if not insights:
            return f"사용자({member_id})의 과거 토론 기록에서 '{query}'와 관련된 통찰이나 요약을 찾지 못했습니다."

        results = []
        for i, item in enumerate(insights, 1):
            book_title = item.get("book_title", "제목 미상")
            persona_id = item.get("persona_id", "토론 파트너")
            topic = item.get("topic", "").strip()
            summary = item.get("summary", "").strip()

            entry = f"[{i}] 도서: <{book_title}> (토론 파트너: {persona_id})"
            if topic:
                entry += f"\n- 핵심 논제: {topic}"
            if summary:
                entry += f"\n- 나눈 생각 및 요약: {summary}"
            results.append(entry)

        return "\n\n".join(results)

    except Exception as e:
        logger.error("Error in search_debate_memory: %s", e)
        return f"과거 토론 기억 조회 중 오류가 발생했습니다: {str(e)}"
