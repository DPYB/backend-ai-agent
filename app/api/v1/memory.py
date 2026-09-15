"""Memory API endpoints for scrap vectorization and Supabase pgvector storage."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import (
    DebateInsightVectorizeRequest,
    DebateInsightVectorizeResponse,
    RecordVectorizeRequest,
    RecordVectorizeResponse,
    ScrapVectorizeRequest,
    ScrapVectorizeResponse,
)
from app.domain.memory.rag_tool import generate_query_embedding
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["Memory"])
vectors_router = APIRouter(prefix="/api/v1/vectors", tags=["Vectors"])


@router.post("/scraps", response_model=ScrapVectorizeResponse, status_code=status.HTTP_201_CREATED)
async def vectorize_scrap(request: ScrapVectorizeRequest) -> ScrapVectorizeResponse:
    """Vectorize a book scrap/quote with user memo and insert into Supabase pgvector.

    - Combines content (quote) and memo for rich semantic representation
    - Generates 768-dim embedding (via Google Gemini or fallback)
    - Saves into Supabase scrap_vector partitioned by member_id
    """
    try:
        # Build embedding text combining quote and user reflection
        embedding_text = f"도서: {request.book_title}\n문장: {request.content}"
        if request.memo and request.memo.strip():
            embedding_text += f"\n메모: {request.memo.strip()}"

        embedding = generate_query_embedding(embedding_text)

        client = get_supabase_client()
        record = await client.insert_scrap_vector(
            member_id=request.member_id,
            book_id=request.book_id,
            book_title=request.book_title,
            content=request.content,
            memo=request.memo or "",
            embedding=embedding,
        )

        scrap_id = str(record.get("id", "")) if record else None

        return ScrapVectorizeResponse(
            success=True,
            scrap_id=scrap_id,
            message="스크랩 문장 및 메모가 성공적으로 벡터화되어 개인 독서 기억에 적재되었습니다.",
        )
    except Exception as e:
        logger.exception("Failed to vectorize and save scrap: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스크랩 벡터화 처리 중 오류가 발생했습니다: {str(e)}",
        ) from e


@vectors_router.post(
    "/records", response_model=RecordVectorizeResponse, status_code=status.HTTP_201_CREATED
)
async def vectorize_reading_record(request: RecordVectorizeRequest) -> RecordVectorizeResponse:
    """Vectorize a reading record/review from backend-core-api and store in Supabase pgvector.

    - Combines title and content (user review/thoughts)
    - Generates 768-dim embedding (via Google Gemini or fallback)
    - Stores into Supabase agent.scrap_vector partitioned by member_id
    """
    try:
        embedding_text = f"도서: {request.title}\n독서 기록: {request.content}"
        embedding = generate_query_embedding(embedding_text)

        client = get_supabase_client()
        record = await client.insert_scrap_vector(
            member_id=request.member_id,
            book_id=f"record-{request.record_id}",
            book_title=request.title,
            content=request.content,
            memo=f"독서 기록 #{request.record_id}",
            embedding=embedding,
        )

        scrap_id = str(record.get("id", "")) if record else None

        return RecordVectorizeResponse(
            success=True,
            record_id=request.record_id,
            scrap_id=scrap_id,
            message="독서 기록이 성공적으로 벡터화되어 개인 독서 기억에 적재되었습니다.",
        )
    except Exception as e:
        logger.exception("Failed to vectorize reading record: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"독서 기록 벡터화 처리 중 오류가 발생했습니다: {str(e)}",
        ) from e


@router.post(
    "/debate-insights",
    response_model=DebateInsightVectorizeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def vectorize_debate_insight(
    request: DebateInsightVectorizeRequest,
) -> DebateInsightVectorizeResponse:
    """Vectorize a debate insight and insert into agent.debate_insights.

    - Combines book title, topic, and debate summary
    - Generates 768-dim embedding (via Google Gemini or fallback)
    - Saves into agent.debate_insights partitioned by member_id
    """
    try:
        embedding_text = f"도서: {request.book_title}\n논제: {request.topic or ''}\n토론 요약: {request.summary}".strip()
        embedding = generate_query_embedding(embedding_text)

        from app.infrastructure.db.repository import get_agent_vector_repository

        repo = get_agent_vector_repository()
        record = await repo.insert_debate_insight(
            member_id=request.member_id,
            session_id=request.session_id,
            book_title=request.book_title,
            persona_id=request.persona_id,
            summary=request.summary,
            topic=request.topic,
            embedding=embedding,
        )

        insight_id = str(record.get("id", "")) if record else None

        return DebateInsightVectorizeResponse(
            success=True,
            insight_id=insight_id,
            message="토론 통찰 요약이 성공적으로 벡터화되어 토론 기억에 적재되었습니다.",
        )
    except Exception as e:
        logger.exception("Failed to vectorize debate insight: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"토론 통찰 벡터화 처리 중 오류가 발생했습니다: {str(e)}",
        ) from e
