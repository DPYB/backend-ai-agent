"""Unit tests for Supabase 'agent' multi-schema and Transaction Pooler DB infrastructure."""

import uuid

import pytest

from app.core.config import Settings
from app.infrastructure.db.models import ChatSession, ScrapVector
from app.infrastructure.db.repository import AgentVectorRepository
from app.infrastructure.supabase_client import SupabaseVectorClient


def test_settings_database_url_encoding():
    """Verify Settings properly encodes special characters in DB_PASSWORD for asyncpg."""
    custom_settings = Settings(
        DB_USER="postgres.myuser",
        DB_PASSWORD="p@ss#word%123!",
        DB_HOST="aws-0-ap-northeast-2.pooler.supabase.com",
        DB_PORT=6543,
        DB_NAME="postgres",
        DB_SCHEMA="agent",
    )
    url = custom_settings.async_database_url

    assert url.startswith("postgresql+asyncpg://")
    assert "postgres.myuser:" in url
    assert "p%40ss%23word%25123%21" in url  # URL-encoded special characters
    assert "@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres" in url
    assert custom_settings.is_db_configured is True


def test_settings_empty_database_url():
    """Verify is_db_configured is False when credentials are not supplied."""
    empty_settings = Settings(
        DB_USER="",
        DB_PASSWORD="",
        DB_HOST="",
        DATABASE_URL="",
    )
    assert empty_settings.async_database_url == ""
    assert empty_settings.is_db_configured is False


def test_models_schema_isolation():
    """Verify ORM models strictly belong to schema 'agent'."""
    assert ScrapVector.__table_args__ == {"schema": "agent"}
    assert ScrapVector.__tablename__ == "scrap_vector"

    assert ChatSession.__table_args__ == {"schema": "agent"}
    assert ChatSession.__tablename__ == "chat_sessions"


@pytest.mark.asyncio
async def test_agent_vector_repository_fallback_and_isolation():
    """Verify AgentVectorRepository in-memory fallback and member_id partitioning."""
    repo = AgentVectorRepository()

    member_1 = str(uuid.uuid4())
    member_2 = str(uuid.uuid4())

    # Insert scrap for member 1
    scrap_1 = await repo.insert_scrap_vector(
        member_id=member_1,
        book_id="book-001",
        book_title="데미안",
        content="새는 알에서 나오려고 투쟁한다.",
        memo="성장에 대한 고뇌",
        embedding=[0.1] * 768,
    )
    assert scrap_1["member_id"] == member_1
    assert scrap_1["book_title"] == "데미안"

    # Insert scrap for member 2
    scrap_2 = await repo.insert_scrap_vector(
        member_id=member_2,
        book_id="book-002",
        book_title="어린 왕자",
        content="가장 중요한 것은 눈에 보이지 않아.",
        memo="순수함에 대하여",
        embedding=[0.2] * 768,
    )
    assert scrap_2["member_id"] == member_2

    # Query for member 1: must only return member 1's scrap
    results_m1 = await repo.search_member_scraps(
        member_id=member_1,
        query_embedding=[0.1] * 768,
        match_threshold=0.0,
        match_count=5,
    )
    assert len(results_m1) == 1
    assert results_m1[0]["book_title"] == "데미안"
    assert results_m1[0]["member_id"] == member_1

    # Query for member 2: must only return member 2's scrap
    results_m2 = await repo.search_member_scraps(
        member_id=member_2,
        query_embedding=[0.2] * 768,
        match_threshold=0.0,
        match_count=5,
    )
    assert len(results_m2) == 1
    assert results_m2[0]["book_title"] == "어린 왕자"
    assert results_m2[0]["member_id"] == member_2


@pytest.mark.asyncio
async def test_supabase_vector_client_adapter_priority():
    """Verify SupabaseVectorClient delegates seamlessly to AgentVectorRepository."""
    mock_repo = AgentVectorRepository()
    client = SupabaseVectorClient(repo=mock_repo)

    member_id = str(uuid.uuid4())
    inserted = await client.insert_scrap_vector(
        member_id=member_id,
        book_id="book-adapter-01",
        book_title="프로젝트 헤일메리",
        content="생존을 위해서라면 인간은 지혜로워진다.",
        memo="과학적 상상력",
        embedding=[0.05] * 768,
    )
    assert inserted["book_title"] == "프로젝트 헤일메리"

    searched = await client.search_member_scraps(
        member_id=member_id,
        query_embedding=[0.05] * 768,
        match_threshold=0.0,
    )
    assert len(searched) == 1
    assert searched[0]["content"] == "생존을 위해서라면 인간은 지혜로워진다."
