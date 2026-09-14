-- ==============================================================================
-- DPYB backend-ai-agent: Supabase 'agent' Schema Initialization DDL
-- Single Supabase Instance Shared ($0 Zero-cost Policy)
-- Pure schema isolation: 'agent' schema is owned exclusively by backend-ai-agent.
-- ==============================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create isolated schema for AI agent
CREATE SCHEMA IF NOT EXISTS agent;

-- 3. Create scrap_vector table in 'agent' schema
CREATE TABLE IF NOT EXISTS agent.scrap_vector (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL,
    book_id VARCHAR(255) NOT NULL,
    book_title TEXT NOT NULL,
    content TEXT NOT NULL,
    memo TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Create member_id index for strict multi-tenant isolation
CREATE INDEX IF NOT EXISTS scrap_vector_member_id_idx
ON agent.scrap_vector (member_id);

-- 5. Create HNSW vector cosine similarity index
CREATE INDEX IF NOT EXISTS scrap_vector_embedding_hnsw_idx
ON agent.scrap_vector USING hnsw (embedding vector_cosine_ops);

-- 6. Create RPC match function inside 'agent' schema
CREATE OR REPLACE FUNCTION agent.match_scraps(
    p_member_id UUID,
    query_embedding vector(768),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5
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
        (1 - (s.embedding <=> query_embedding))::float AS similarity
    FROM agent.scrap_vector s
    WHERE s.member_id = p_member_id
      AND (1 - (s.embedding <=> query_embedding)) > match_threshold
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 7. Optional chat sessions table in 'agent' schema
CREATE TABLE IF NOT EXISTS agent.chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    member_id UUID,
    persona_id VARCHAR(50) NOT NULL,
    librarian_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
