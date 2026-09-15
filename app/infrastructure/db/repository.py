"""Vector repository for personalized scrap memories in the 'agent' schema."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text

from app.core.config import settings
from app.infrastructure.db.models import DebateInsight, ScrapVector
from app.infrastructure.db.session import get_session_factory

logger = logging.getLogger(__name__)


class AgentVectorRepository:
    """Manages scrap vector similarity search and storage in schema 'agent'.

    Strictly partitions queries by member_id for personalized reading memory.
    Provides automatic fallback to in-memory storage when DB is unconfigured.
    """

    def __init__(self) -> None:
        self._mock_scraps: List[Dict[str, Any]] = []
        self._mock_debate_insights: List[Dict[str, Any]] = []

    @property
    def is_connected(self) -> bool:
        """Check if database connection factory is available."""
        return settings.is_db_configured and get_session_factory() is not None

    async def ping_db(self) -> bool:
        """Execute a lightweight SELECT 1 query to prevent 7-day Supabase inactivity pause."""
        factory = get_session_factory()
        if not factory:
            return False
        try:
            async with factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.warning("Supabase DB ping failed: %s", e)
            return False

    async def search_member_scraps(
        self,
        member_id: str,
        query_embedding: List[float],
        match_threshold: float = 0.3,
        match_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search scrap vectors strictly filtered by member_id in schema 'agent'.

        Calculates cosine similarity: 1 - cosine_distance.
        """
        factory = get_session_factory()
        if factory:
            try:
                member_uuid = uuid.UUID(member_id)
                async with factory() as session:
                    # pgvector cosine distance operator: <=>
                    # cosine similarity = 1 - cosine_distance
                    similarity_expr = (
                        1 - ScrapVector.embedding.cosine_distance(query_embedding)
                    ).label("similarity")
                    stmt = (
                        select(
                            ScrapVector.id,
                            ScrapVector.member_id,
                            ScrapVector.book_id,
                            ScrapVector.book_title,
                            ScrapVector.content,
                            ScrapVector.memo,
                            similarity_expr,
                        )
                        .where(ScrapVector.member_id == member_uuid)
                        .where(similarity_expr > match_threshold)
                        .order_by(ScrapVector.embedding.cosine_distance(query_embedding))
                        .limit(match_count)
                    )
                    result = await session.execute(stmt)
                    rows = result.all()
                    return [
                        {
                            "id": str(row.id),
                            "member_id": str(row.member_id),
                            "book_id": row.book_id,
                            "book_title": row.book_title,
                            "content": row.content,
                            "memo": row.memo or "",
                            "similarity": float(row.similarity),
                        }
                        for row in rows
                    ]
            except Exception as e:
                logger.error(
                    "Database search_member_scraps failed: %s. Falling back to in-memory.", e
                )

        # Fallback / mock search for local development or testing
        matching = [
            scrap for scrap in self._mock_scraps if str(scrap.get("member_id")) == str(member_id)
        ]
        return matching[:match_count]

    async def insert_scrap_vector(
        self,
        member_id: str,
        book_id: str,
        book_title: str,
        content: str,
        memo: str,
        embedding: List[float],
    ) -> Dict[str, Any]:
        """Insert scrap embedding vector into agent.scrap_vector."""
        record_id = uuid.uuid4()
        factory = get_session_factory()

        if factory:
            try:
                member_uuid = uuid.UUID(member_id)
                async with factory() as session:
                    scrap = ScrapVector(
                        id=record_id,
                        member_id=member_uuid,
                        book_id=book_id,
                        book_title=book_title,
                        content=content,
                        memo=memo,
                        embedding=embedding,
                    )
                    session.add(scrap)
                    await session.commit()
                    logger.info(
                        "Inserted scrap vector for member %s into agent.scrap_vector", member_id
                    )
                    return scrap.to_dict()
            except Exception as e:
                logger.error(
                    "Failed to insert scrap_vector into DB: %s. Using in-memory fallback.", e
                )

        # In-memory storage for mock/local testing
        mock_record = {
            "id": str(record_id),
            "member_id": member_id,
            "book_id": book_id,
            "book_title": book_title,
            "content": content,
            "memo": memo,
            "embedding": embedding,
        }
        self._mock_scraps.append(mock_record)
        return mock_record

    async def search_member_debate_insights(
        self,
        member_id: str,
        query_embedding: List[float],
        match_threshold: float = 0.3,
        match_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search debate insights strictly filtered by member_id in schema 'agent'.

        Calculates cosine similarity: 1 - cosine_distance.
        """
        factory = get_session_factory()
        if factory:
            try:
                member_uuid = uuid.UUID(member_id)
                async with factory() as session:
                    similarity_expr = (
                        1 - DebateInsight.embedding.cosine_distance(query_embedding)
                    ).label("similarity")
                    stmt = (
                        select(
                            DebateInsight.id,
                            DebateInsight.member_id,
                            DebateInsight.session_id,
                            DebateInsight.book_title,
                            DebateInsight.persona_id,
                            DebateInsight.summary,
                            DebateInsight.topic,
                            DebateInsight.created_at,
                            similarity_expr,
                        )
                        .where(DebateInsight.member_id == member_uuid)
                        .where(similarity_expr > match_threshold)
                        .order_by(DebateInsight.embedding.cosine_distance(query_embedding))
                        .limit(match_count)
                    )
                    result = await session.execute(stmt)
                    rows = result.all()
                    return [
                        {
                            "id": str(row.id),
                            "member_id": str(row.member_id),
                            "session_id": row.session_id,
                            "book_title": row.book_title,
                            "persona_id": row.persona_id,
                            "summary": row.summary,
                            "topic": row.topic or "",
                            "similarity": float(row.similarity),
                            "created_at": (row.created_at.isoformat() if row.created_at else None),
                        }
                        for row in rows
                    ]
            except Exception as e:
                logger.error(
                    "Database search_member_debate_insights failed: %s. Falling back to in-memory.",
                    e,
                )

        # Fallback / mock search for local development or testing
        matching = [
            debate
            for debate in self._mock_debate_insights
            if str(debate.get("member_id")) == str(member_id)
        ]
        return matching[:match_count]

    async def insert_debate_insight(
        self,
        member_id: str,
        session_id: str,
        book_title: str,
        persona_id: str,
        summary: str,
        topic: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Insert debate insight vector into agent.debate_insights."""
        record_id = uuid.uuid4()
        factory = get_session_factory()

        if factory:
            try:
                member_uuid = uuid.UUID(member_id)
                async with factory() as session:
                    insight = DebateInsight(
                        id=record_id,
                        member_id=member_uuid,
                        session_id=session_id,
                        book_title=book_title,
                        persona_id=persona_id,
                        summary=summary,
                        topic=topic,
                        embedding=embedding,
                    )
                    session.add(insight)
                    await session.commit()
                    logger.info(
                        "Inserted debate insight for member %s (book: %s) into agent.debate_insights",
                        member_id,
                        book_title,
                    )
                    return insight.to_dict()
            except Exception as e:
                logger.error(
                    "Failed to insert debate_insight into DB: %s. Using in-memory fallback.",
                    e,
                )

        # In-memory storage for mock/local testing
        mock_record = {
            "id": str(record_id),
            "member_id": member_id,
            "session_id": session_id,
            "book_title": book_title,
            "persona_id": persona_id,
            "summary": summary,
            "topic": topic or "",
            "embedding": embedding,
        }
        self._mock_debate_insights.append(mock_record)
        return mock_record

    async def get_member_monthly_debate_insights(
        self,
        member_id: str,
        year: int,
        month: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve debate insights for a member in a specific year/month."""
        factory = get_session_factory()
        if factory:
            try:
                member_uuid = uuid.UUID(member_id)
                async with factory() as session:
                    stmt = (
                        select(
                            DebateInsight.id,
                            DebateInsight.member_id,
                            DebateInsight.session_id,
                            DebateInsight.book_title,
                            DebateInsight.persona_id,
                            DebateInsight.summary,
                            DebateInsight.topic,
                            DebateInsight.created_at,
                        )
                        .where(DebateInsight.member_id == member_uuid)
                        .order_by(DebateInsight.created_at.desc())
                        .limit(limit)
                    )
                    result = await session.execute(stmt)
                    rows = result.all()
                    # Filter by year and month if created_at is present
                    insights = []
                    for row in rows:
                        if row.created_at:
                            if row.created_at.year == year and row.created_at.month == month:
                                insights.append(
                                    {
                                        "id": str(row.id),
                                        "book_title": row.book_title,
                                        "topic": row.topic or "",
                                        "summary": row.summary,
                                        "created_at": row.created_at.isoformat(),
                                    }
                                )
                        else:
                            insights.append(
                                {
                                    "id": str(row.id),
                                    "book_title": row.book_title,
                                    "topic": row.topic or "",
                                    "summary": row.summary,
                                }
                            )
                    return insights
            except Exception as e:
                logger.warning("DB query get_member_monthly_debate_insights failed (%s).", e)

        # In-memory mock filter
        results = []
        for d in self._mock_debate_insights:
            if str(d.get("member_id")) == str(member_id):
                results.append(
                    {
                        "id": str(d.get("id")),
                        "book_title": d.get("book_title", ""),
                        "topic": d.get("topic", ""),
                        "summary": d.get("summary", ""),
                    }
                )
        return results[:limit]


_agent_repository: Optional[AgentVectorRepository] = None


def get_agent_vector_repository() -> AgentVectorRepository:
    """Return singleton instance of AgentVectorRepository."""
    global _agent_repository
    if _agent_repository is None:
        _agent_repository = AgentVectorRepository()
    return _agent_repository
