"""initial agent schema

Revision ID: 001_initial_agent_schema
Revises:
Create Date: 2026-09-19 17:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_agent_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. pgvector extension & agent schema 보장
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE SCHEMA IF NOT EXISTS agent;")

    # 2. agent.scrap_vector 테이블 및 인덱스 생성
    op.execute("""
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
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS scrap_vector_member_id_idx
        ON agent.scrap_vector (member_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS scrap_vector_embedding_hnsw_idx
        ON agent.scrap_vector USING hnsw (embedding vector_cosine_ops);
    """)

    # 3. agent.match_scraps RPC 함수 생성
    op.execute("""
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
    """)

    # 4. agent.chat_sessions 테이블 생성
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent.chat_sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            member_id UUID,
            persona_id VARCHAR(50) NOT NULL,
            librarian_name VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    # 5. agent.debate_insights 테이블 및 인덱스 생성
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent.debate_insights (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            member_id UUID NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            book_title TEXT NOT NULL,
            persona_id VARCHAR(50) NOT NULL,
            summary TEXT NOT NULL,
            topic TEXT,
            embedding vector(768),
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS debate_insights_member_id_idx
        ON agent.debate_insights (member_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS debate_insights_embedding_hnsw_idx
        ON agent.debate_insights USING hnsw (embedding vector_cosine_ops);
    """)

    # 6. agent.match_debate_insights RPC 함수 생성
    op.execute("""
        CREATE OR REPLACE FUNCTION agent.match_debate_insights(
            p_member_id UUID,
            query_embedding vector(768),
            match_threshold float DEFAULT 0.3,
            match_count int DEFAULT 5
        )
        RETURNS TABLE (
            id UUID,
            member_id UUID,
            session_id VARCHAR,
            book_title TEXT,
            persona_id VARCHAR,
            summary TEXT,
            topic TEXT,
            similarity float,
            created_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                d.id,
                d.member_id,
                d.session_id,
                d.book_title,
                d.persona_id,
                d.summary,
                d.topic,
                (1 - (d.embedding <=> query_embedding))::float AS similarity,
                d.created_at
            FROM agent.debate_insights d
            WHERE d.member_id = p_member_id
              AND (1 - (d.embedding <=> query_embedding)) > match_threshold
            ORDER BY d.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS agent.match_debate_insights(UUID, vector, float, int);")
    op.execute("DROP TABLE IF EXISTS agent.debate_insights CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent.chat_sessions CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS agent.match_scraps(UUID, vector, float, int);")
    op.execute("DROP TABLE IF EXISTS agent.scrap_vector CASCADE;")
