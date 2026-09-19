import asyncio
from logging.config import fileConfig

import sqlalchemy as sa
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.infrastructure.db.migration_guard import check_remote_migration_safety
from app.infrastructure.db.models import Base  # noqa: F401 (모든 모델 등록)

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target metadata
target_metadata = Base.metadata

# 환경변수의 DATABASE_URL 설정 반영 (configparser 보간 에러 방지를 위해 % -> %% 이스케이프)
db_url = (
    settings.async_database_url or "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
)
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """오프라인 마이그레이션 실행"""
    check_remote_migration_safety()
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="agent",
        version_num_length=64,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # alembic_version 테이블이 agent 스키마에 생성되므로 vector 익스텐션 및 agent 스키마 선행 보장
    with connection.begin():
        connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS agent;"))
        connection.execute(
            sa.text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'agent' AND table_name = 'alembic_version' AND column_name = 'version_num'
                ) THEN
                    ALTER TABLE agent.alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);
                END IF;
            END $$;
            """)
        )

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="agent",
        version_num_length=64,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """온라인 비동기 마이그레이션 실행"""
    configuration = config.get_section(config.config_ini_section, {})
    connect_args = {}
    if "asyncpg" in db_url:
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    check_remote_migration_safety()
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
