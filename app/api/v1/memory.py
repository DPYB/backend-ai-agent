"""Memory API endpoints for scrap vectorization and Supabase pgvector storage."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import ScrapVectorizeRequest, ScrapVectorizeResponse
from app.domain.memory.rag_tool import generate_query_embedding
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["Memory"])


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
