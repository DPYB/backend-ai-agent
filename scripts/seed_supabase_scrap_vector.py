"""Supabase pgvector scrap_vector seeding and schema setup script.

Run this script to inspect the Supabase SQL schema or seed dummy personalized scrap data:
    uv run python scripts/seed_supabase_scrap_vector.py
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List

from app.domain.memory.rag_tool import generate_query_embedding
from app.infrastructure.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed-scrap-vector")

# Supabase DDL SQL for scrap_vector and RPC match function
SUPABASE_SCHEMA_SQL = """
-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create scrap_vector table for personalized memory (Phase 1)
CREATE TABLE IF NOT EXISTS scrap_vector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL,
    book_id VARCHAR(255) NOT NULL,
    book_title TEXT NOT NULL,
    content TEXT NOT NULL,
    memo TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Create index for high-speed cosine distance similarity search
CREATE INDEX IF NOT EXISTS scrap_vector_embedding_idx
ON scrap_vector USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create RPC function to strictly query member scraps
CREATE OR REPLACE FUNCTION match_scraps(
    p_member_id UUID,
    query_embedding vector(768),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id UUID,
    member_id UUID,
    book_id VARCHAR,
    book_title TEXT,
    content TEXT,
    memo TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.member_id,
        s.book_id,
        s.book_title,
        s.content,
        s.memo,
        1 - (s.embedding <=> query_embedding) AS similarity
    FROM scrap_vector s
    WHERE s.member_id = p_member_id
      AND 1 - (s.embedding <=> query_embedding) > match_threshold
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

DUMMY_SCRAPS: List[Dict[str, Any]] = [
    {
        "book_id": "book-sf-001",
        "book_title": "프로젝트 헤일메리",
        "content": "인간은 생존을 위해서라면 상상할 수 없을 만큼 지혜로워질 수 있다.",
        "memo": "우주 속 고립감 속에서도 꺾이지 않는 인간의 연대와 유머 감각이 너무 뭉클했다.",
    },
    {
        "book_id": "book-sf-002",
        "book_title": "듄 (Dune)",
        "content": "두려움은 마음을 죽이는 자다. 두려움은 완전한 소멸을 가져오는 작은 죽음이다.",
        "memo": "불안할 때마다 이 구절을 소리 내어 읽으면 차분해지는 기분이 든다.",
    },
    {
        "book_id": "book-lit-003",
        "book_title": "데미안",
        "content": "새는 알에서 나오려고 투쟁한다. 알은 세계다. 태어나려는 자는 하나의 세계를 깨뜨려야 한다.",
        "memo": "이직을 앞두고 내 세계를 확장하고 싶을 때 적어둔 문장.",
    },
    {
        "book_id": "book-essay-004",
        "book_title": "어린 왕자",
        "content": "가장 중요한 것은 눈에 보이지 않아. 마음으로 보아야 분명하게 보여.",
        "memo": "밤마다 복잡한 생각을 정리할 때 떠올리는 가장 순수한 문장.",
    },
]


async def seed_scraps(sample_member_id: str = "550e8400-e29b-41d4-a716-446655440000"):
    """Seed dummy scraps for a specific member."""
    print("=" * 70)
    print("DPYB Supabase pgvector Setup SQL (Copy & run in Supabase SQL Editor):")
    print("=" * 70)
    print(SUPABASE_SCHEMA_SQL)
    print("=" * 70)

    client = get_supabase_client()
    print(f"\n[Seeding] Starting seed for sample member_id={sample_member_id}...")

    for item in DUMMY_SCRAPS:
        text_to_embed = f"{item['book_title']} {item['content']} {item['memo']}"
        embedding = generate_query_embedding(text_to_embed)
        inserted = await client.insert_scrap_vector(
            member_id=sample_member_id,
            book_id=item["book_id"],
            book_title=item["book_title"],
            content=item["content"],
            memo=item["memo"],
            embedding=embedding,
        )
        print(f" -> Inserted scrap: <{inserted.get('book_title')}> (id: {inserted.get('id')})")

    print("\n[Verification] Performing search for '우주와 고립'...")
    search_emb = generate_query_embedding("우주와 고립 두려움")
    results = await client.search_member_scraps(sample_member_id, search_emb, match_threshold=0.2)
    print(f"Found {len(results)} matching scraps:")
    for r in results:
        print(f' - <{r.get("book_title")}>: "{r.get("content")}"')
    print("\nSeed completed successfully!")


if __name__ == "__main__":
    test_uuid = str(uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))
    asyncio.run(seed_scraps(test_uuid))
