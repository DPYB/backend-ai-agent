"""Initialize Supabase 'agent' schema and pgvector tables.

Usage:
    uv run python scripts/init_agent_schema.py
    uv run python scripts/init_agent_schema.py --seed
"""

import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path

import asyncpg

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init-agent-schema")

DDL_FILE_PATH = Path(__file__).parent / "init_agent_schema.sql"


async def run_init_schema(seed: bool = False) -> None:
    """Run DDL SQL on Supabase using asyncpg."""
    if not settings.is_db_configured:
        logger.error(
            "Database connection is not configured in .env! "
            "Please configure DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME in .env."
        )
        sys.exit(1)

    logger.info(
        "Connecting to Supabase Transaction Pooler at %s:%s (db=%s, user=%s)...",
        settings.db_host,
        settings.db_port,
        settings.db_name,
        settings.db_user,
    )

    if not DDL_FILE_PATH.exists():
        logger.error("DDL file not found at %s", DDL_FILE_PATH)
        sys.exit(1)

    ddl_sql = DDL_FILE_PATH.read_text(encoding="utf-8")

    try:
        # Note: statement_cache_size=0 is required for Supabase Transaction Pooler (port 6543)
        conn = await asyncpg.connect(
            user=settings.db_user,
            password=settings.db_password,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            statement_cache_size=0,
        )
    except Exception as e:
        logger.error("Failed to connect to Supabase: %s", e)
        sys.exit(1)

    try:
        logger.info("Executing DDL statements from %s...", DDL_FILE_PATH.name)
        await conn.execute(ddl_sql)
        logger.info("Schema 'agent' and tables successfully initialized!")

        # Verify agent.scrap_vector existence
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'agent' AND table_name = 'scrap_vector'
            );
            """
        )
        logger.info("Verification: table agent.scrap_vector exists = %s", table_exists)

        # Verify agent.debate_insights existence
        debate_table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'agent' AND table_name = 'debate_insights'
            );
            """
        )
        logger.info("Verification: table agent.debate_insights exists = %s", debate_table_exists)

        if seed:
            logger.info("Seeding dummy scrap data into agent.scrap_vector...")
            sample_member_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
            from app.domain.memory.rag_tool import generate_query_embedding

            sample_scraps = [
                (
                    sample_member_id,
                    "book-sf-001",
                    "프로젝트 헤일메리",
                    "인간은 생존을 위해서라면 상상할 수 없을 만큼 지혜로워질 수 있다.",
                    "우주 속 고립감 속에서도 꺾이지 않는 인간의 연대와 유머 감각.",
                ),
                (
                    sample_member_id,
                    "book-lit-003",
                    "데미안",
                    "새는 알에서 나오려고 투쟁한다. 알은 세계다. 태어나려는 자는 하나의 세계를 깨뜨려야 한다.",
                    "새로운 도전을 앞두고 내 세계를 확장하고 싶을 때 적어둔 문장.",
                ),
            ]

            for s_member, s_book_id, s_title, s_content, s_memo in sample_scraps:
                emb = generate_query_embedding(f"{s_title} {s_content} {s_memo}")
                emb_str = f"[{','.join(map(str, emb))}]"
                await conn.execute(
                    """
                    INSERT INTO agent.scrap_vector (member_id, book_id, book_title, content, memo, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6::vector)
                    """,
                    s_member,
                    s_book_id,
                    s_title,
                    s_content,
                    s_memo,
                    emb_str,
                )
                logger.info(" -> Seeded scrap: <%s>", s_title)

            logger.info("Seeding dummy debate insights into agent.debate_insights...")
            sample_debates = [
                (
                    sample_member_id,
                    "session-sample-001",
                    "데미안",
                    "debate_critic",
                    "알을 깨고 나오는 싱클레어의 내면 투쟁과 아프락사스를 향한 자기 구원의 여정을 미학적으로 탐구함. 선과 악의 이분법을 넘어 온전한 자아를 마주하는 용기에 대해 깊은 토론을 나눔.",
                    "선과 악의 이분법 극복과 진정한 자아 발견",
                ),
                (
                    sample_member_id,
                    "session-sample-002",
                    "불편한 편의점",
                    "debate_counselor",
                    "각자의 상처와 외로움을 안고 살아가는 현대인들에게 야간 편의점이 건네는 무조건적인 온기와 경청의 힘을 조명함. 작은 환대와 배려가 인간을 치유하는 과정에 공감함.",
                    "단절된 관계의 회복과 따뜻한 연대의 가치",
                ),
            ]

            for d_member, d_session, d_title, d_persona, d_summary, d_topic in sample_debates:
                emb = generate_query_embedding(f"{d_title} {d_topic} {d_summary}")
                emb_str = f"[{','.join(map(str, emb))}]"
                await conn.execute(
                    """
                    INSERT INTO agent.debate_insights (member_id, session_id, book_title, persona_id, summary, topic, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::vector)
                    """,
                    d_member,
                    d_session,
                    d_title,
                    d_persona,
                    d_summary,
                    d_topic,
                    emb_str,
                )
                logger.info(" -> Seeded debate insight: <%s> (%s)", d_title, d_persona)

            logger.info("Seeding completed successfully.")

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Supabase agent schema and tables")
    parser.add_argument("--seed", action="store_true", help="Seed sample scraps after schema init")
    args = parser.parse_args()

    asyncio.run(run_init_schema(seed=args.seed))


if __name__ == "__main__":
    main()
