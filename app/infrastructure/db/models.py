"""SQLAlchemy ORM models strictly confined to the 'agent' PostgreSQL schema.

Follows the DPYB zero-cost architecture: single Supabase PostgreSQL instance,
strict schema-level isolation (backend-ai-agent exclusively owns schema 'agent').
"""

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative Base class for SQLAlchemy ORM models."""

    pass


class ScrapVector(Base):
    """Personalized scrap memory vectors strictly isolated by member_id.

    Table: agent.scrap_vector
    """

    __tablename__ = "scrap_vector"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    book_id: Mapped[str] = mapped_column(String(255), nullable=False)
    book_title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        """Convert model instance to dictionary representation."""
        return {
            "id": str(self.id),
            "member_id": str(self.member_id),
            "book_id": self.book_id,
            "book_title": self.book_title,
            "content": self.content,
            "memo": self.memo or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChatSession(Base):
    """Chat session metadata table in schema 'agent'."""

    __tablename__ = "chat_sessions"
    __table_args__ = {"schema": "agent"}

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    member_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    persona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    librarian_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class DebateInsight(Base):
    """Personalized debate insights and takeaways strictly isolated by member_id.

    Table: agent.debate_insights
    Preserves the pure quote/scrap nature of scrap_vector by housing user-AI philosophical
    and literary discussion conclusions separately.
    """

    __tablename__ = "debate_insights"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    book_title: Mapped[str] = mapped_column(Text, nullable=False)
    persona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        """Convert model instance to dictionary representation."""
        return {
            "id": str(self.id),
            "member_id": str(self.member_id),
            "session_id": self.session_id,
            "book_title": self.book_title,
            "persona_id": self.persona_id,
            "summary": self.summary,
            "topic": self.topic or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
