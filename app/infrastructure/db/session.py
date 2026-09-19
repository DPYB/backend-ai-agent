"""SQLAlchemy asyncpg database session and engine management.

Configured specifically for Supabase Transaction Pooler (Port 6543).
Statement caching is disabled to prevent pooler prepared statement collisions:
connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
"""

import logging
from typing import AsyncGenerator, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine() -> Optional[AsyncEngine]:
    """Return or initialize singleton AsyncEngine with Supabase pooler compatibility."""
    global _engine
    if _engine is None and settings.is_db_configured:
        try:
            _engine = create_async_engine(
                settings.async_database_url,
                echo=False,
                poolclass=NullPool,
                connect_args={
                    "statement_cache_size": 0,
                    "prepared_statement_cache_size": 0,
                    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
                },
            )
            logger.info("SQLAlchemy asyncpg engine initialized successfully with NullPool.")
        except Exception as e:
            logger.warning("Failed to initialize asyncpg engine (%s). Fallback mode enabled.", e)
            _engine = None
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Return or initialize async_sessionmaker."""
    global _session_factory
    if _session_factory is None:
        engine = get_async_engine()
        if engine:
            _session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
    return _session_factory


async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Dependency / generator yielding an AsyncSession."""
    factory = get_session_factory()
    if not factory:
        yield None
        return
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
