"""Unit tests for Personalization RAG tool (scrap_vector)."""

import pytest

from app.domain.memory.rag_tool import generate_query_embedding, search_scrap_memory
from app.infrastructure.supabase_client import get_supabase_client


def test_generate_query_embedding_dimension():
    """Verify embedding vector generation produces unit-normalized 768-dim vector."""
    emb = generate_query_embedding("SF 소설과 우주 여행")
    assert isinstance(emb, list)
    assert len(emb) == 768
    # Norm check (approximately 1.0)
    norm = sum(x * x for x in emb) ** 0.5
    assert abs(norm - 1.0) < 1e-3


@pytest.mark.asyncio
async def test_scrap_vector_member_isolation():
    """Verify scrap_vector search strictly isolates results by member_id."""
    client = get_supabase_client()
    member_a = "11111111-1111-1111-1111-111111111111"
    member_b = "22222222-2222-2222-2222-222222222222"

    emb_a = generate_query_embedding("듄 모래언덕")
    emb_b = generate_query_embedding("어린왕자 여우")

    # Insert scrap for member A
    await client.insert_scrap_vector(
        member_id=member_a,
        book_id="book-1",
        book_title="듄",
        content="두려움은 마음을 죽인다.",
        memo="명문장",
        embedding=emb_a,
    )

    # Insert scrap for member B
    await client.insert_scrap_vector(
        member_id=member_b,
        book_id="book-2",
        book_title="어린 왕자",
        content="마음으로 보아야 보인다.",
        memo="감동적",
        embedding=emb_b,
    )

    # Query for member A
    results_a = await client.search_member_scraps(member_a, emb_a)
    assert len(results_a) >= 1
    for item in results_a:
        assert item["member_id"] == member_a
        assert "듄" in item["book_title"]

    # Member B should NOT see Member A's scrap
    results_b = await client.search_member_scraps(member_b, emb_a)
    for item in results_b:
        assert item["member_id"] == member_b


@pytest.mark.asyncio
async def test_search_scrap_memory_tool():
    """Verify LangChain search_scrap_memory tool returns formatted text."""
    member_id = "test-member-uuid"
    client = get_supabase_client()
    emb = generate_query_embedding("프로젝트 헤일메리")

    await client.insert_scrap_vector(
        member_id=member_id,
        book_id="book-phm",
        book_title="프로젝트 헤일메리",
        content="지혜는 생존의 열쇠다.",
        memo="로키와의 우정이 돋보임",
        embedding=emb,
    )

    tool_output = await search_scrap_memory.ainvoke(
        {"member_id": member_id, "query": "프로젝트 헤일메리"}
    )
    assert "프로젝트 헤일메리" in tool_output
    assert "지혜는 생존의 열쇠다" in tool_output
    assert "로키와의 우정" in tool_output
