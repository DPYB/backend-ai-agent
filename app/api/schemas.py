"""Pydantic request and response schemas for FastAPI endpoints."""

from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User request payload for conversational AI librarian or debate partner."""

    member_id: str = Field(
        ...,
        description="Member UUID to strictly partition personalized scrap memory and bookshelf",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User message text",
        examples=["내 서재에 있는 책 중에 지금 읽기 좋은 책 추천해 줘"],
    )
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Conversation session ID for Redis history tracking",
    )
    mode: Optional[Literal["LIBRARIAN", "DEBATE"]] = Field(
        default="LIBRARIAN",
        description="Interaction mode: LIBRARIAN (사서) or DEBATE (토론)",
    )
    persona: Optional[str] = Field(
        default="CAT",
        description="Target persona ID (CAT, SHOEBILL, SEA_SLUG, GECKO, DEBATE_CRITIC, etc.)",
    )
    librarian_name: Optional[str] = Field(
        default=None,
        description="User-defined custom librarian name (사용자가 개명한 사서 애칭)",
        examples=["내 고양이", "누디", "초록이"],
    )


class SwitchSuggestionResponse(BaseModel):
    """Frontend-ready button suggestion to switch librarian or debate partner persona."""

    suggested_persona: str = Field(..., description="Persona ID to switch to")
    display_name: str = Field(..., description="Korean character display name")
    reason: str = Field(..., description="Contextual reason for suggestion")


class ChatResponse(BaseModel):
    """Response payload returned by AI librarian or debate partner."""

    session_id: str = Field(..., description="Session identifier")
    reply: str = Field(..., description="AI response message")
    active_persona: str = Field(..., description="Active persona ID")
    display_name: str = Field(
        ...,
        description="Character display name (블루, 슈빌, 바다달팽이, 게코 or custom librarian_name)",
    )
    mode: Optional[str] = Field(default="LIBRARIAN", description="Current operating mode")
    switch_suggestion: Optional[SwitchSuggestionResponse] = Field(
        default=None,
        description="Button action metadata when handoff is recommended",
    )


class PersonaInfo(BaseModel):
    """Metadata for available librarian and debate personas."""

    persona_id: str
    display_name: str
    mode: str
    description: str
    tone: str


class HealthResponse(BaseModel):
    """System health status response."""

    status: str
    environment: str
    version: str
    redis_connected: bool
    supabase_connected: bool


class ScrapVectorizeRequest(BaseModel):
    """Request payload for vectorizing a reading scrap/memo."""

    member_id: str = Field(..., description="Unique member UUID", min_length=1)
    book_id: str = Field(..., description="Target book UUID/ID", min_length=1)
    book_title: str = Field(..., description="Title of the book", min_length=1)
    content: str = Field(..., description="Scrapped book quote/sentence", min_length=1)
    memo: Optional[str] = Field(default="", description="User reflection/thought on the quote")


class ScrapVectorizeResponse(BaseModel):
    """Response payload after scrap vectorization and Supabase pgvector insertion."""

    success: bool = Field(..., description="Whether vectorization and insertion succeeded")
    scrap_id: Optional[str] = Field(default=None, description="Created or mock scrap record ID")
    message: str = Field(..., description="Result summary message")
