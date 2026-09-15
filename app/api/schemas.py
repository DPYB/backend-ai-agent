"""Pydantic request and response schemas for FastAPI endpoints."""

from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class LocationPayload(BaseModel):
    """Geolocation coordinates sent from frontend for weather-informed curation."""

    latitude: float = Field(..., description="Latitude", examples=[37.5665])
    longitude: float = Field(..., description="Longitude", examples=[126.9780])


class ChatRequest(BaseModel):
    """User request payload for conversational AI librarian or debate partner."""

    member_id: Optional[str] = Field(
        default=None,
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
        default=None,
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
    librarian_id: Optional[str] = Field(
        default=None,
        description="Frontend alias for persona (cat, stork, shoebill, etc.)",
    )
    librarian_name: Optional[str] = Field(
        default=None,
        description="User-defined custom librarian name (사용자가 개명한 사서 애칭)",
        examples=["내 고양이", "누디", "초록이"],
    )
    latitude: Optional[float] = Field(default=None, description="Flat coordinate latitude")
    longitude: Optional[float] = Field(default=None, description="Flat coordinate longitude")
    location: Optional[LocationPayload] = Field(
        default=None,
        description="Current user coordinates (위경도) for real-time weather curation",
    )
    stream: Optional[bool] = Field(default=False, description="Streaming response flag")
    action: Optional[Literal["chat", "conclude"]] = Field(
        default="chat",
        description="Action intent: 'chat' (normal conversation) or 'conclude' (UI button instant wrap-up & curation)",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_conclude_action(cls, data: Any) -> Any:
        if isinstance(data, dict):
            action = data.get("action", "chat")
            msg = data.get("message")
            if action == "conclude" and (not msg or not str(msg).strip()):
                data["message"] = "토론 마무리"
        return data

    @model_validator(mode="after")
    def populate_defaults_and_aliases(self) -> "ChatRequest":
        # 1. Do not auto-generate member_id; keep None for guest users

        # 2. Map librarian_id to persona if provided
        if self.librarian_id:
            lib_id = self.librarian_id.strip().upper()
            mapping = {
                "CAT": "CAT",
                "STORK": "SHOEBILL",
                "SHOEBILL": "SHOEBILL",
                "SEA_SLUG": "SEA_SLUG",
                "GECKO": "GECKO",
            }
            if lib_id in mapping:
                self.persona = mapping[lib_id]

        # 3. Assemble location from flat coordinates if not already present
        if not self.location and self.latitude is not None and self.longitude is not None:
            self.location = LocationPayload(latitude=self.latitude, longitude=self.longitude)

        # 4. Generate session_id if not present
        if not self.session_id:
            self.session_id = str(uuid4())

        return self


class SwitchSuggestionResponse(BaseModel):
    """Frontend-ready button suggestion to switch librarian or debate partner persona."""

    suggested_persona: str = Field(..., description="Persona ID to switch to")
    display_name: str = Field(..., description="Korean character display name")
    reason: str = Field(..., description="Contextual reason for suggestion")


class RecommendedBook(BaseModel):
    """Detailed book recommendation metadata verified by National Library of Korea."""

    title: str = Field(..., description="Book title (도서명)")
    author: str = Field(
        default="", description="Author name without extraneous notes (순수 저자명)"
    )
    isbn: str = Field(default="", description="13-digit standard ISBN (13자리 정식 ISBN)")
    publisher: Optional[str] = Field(default=None, description="Publisher name (출판사)")
    page_count: Optional[int] = Field(
        default=None, description="Total page count as integer (총 쪽수)"
    )
    genre: Optional[str] = Field(
        default=None, description="Book genre or KDC main category (도서 장르/대분류)"
    )
    cover_url: Optional[str] = Field(
        default=None, description="High-resolution book cover image URL (고화질 표지 URL)"
    )
    reason: Optional[str] = Field(
        default=None, description="AI recommendation context or rationale (추천 사유)"
    )
    description: Optional[str] = Field(
        default=None, description="Book summary or description (도서 소개/줄거리)"
    )


class ChatResponse(BaseModel):
    """Response payload returned by AI librarian or debate partner."""

    session_id: str = Field(..., description="Session identifier")
    reply: str = Field(..., description="AI response message")
    message: Optional[str] = Field(
        default=None,
        description="Deprecated frontend alias for reply",
    )
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
    switch_to: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Deprecated frontend alias for switch_suggestion",
    )
    recommended_books: List[RecommendedBook] = Field(
        default_factory=list,
        description="Structured verified book recommendations for one-click bookshelf registration",
    )
    is_concluded: Optional[bool] = Field(
        default=False,
        description="Whether this debate session has concluded with wrap-up curation",
    )
    debate_summary: Optional[str] = Field(
        default=None,
        description="Structured wrap-up summary of the debate discussion",
    )

    @model_validator(mode="after")
    def sync_frontend_aliases(self) -> "ChatResponse":
        if not self.message:
            self.message = self.reply
        if not self.switch_to and self.switch_suggestion:
            self.switch_to = {
                "librarian_id": self.switch_suggestion.suggested_persona.lower(),
                "persona": self.switch_suggestion.suggested_persona,
                "display_name": self.switch_suggestion.display_name,
                "reason": self.switch_suggestion.reason,
            }
        return self


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


class RecordVectorizeRequest(BaseModel):
    """Request payload from backend-core-api for vectorizing a reading record/review."""

    record_id: int = Field(..., description="backend-core-api record ID")
    member_id: str = Field(..., description="Member UUID", min_length=1)
    title: str = Field(..., description="Book title or record title", min_length=1)
    content: str = Field(..., description="Reading record review/thoughts", min_length=1)


class RecordVectorizeResponse(BaseModel):
    """Response payload after reading record vectorization."""

    success: bool = Field(..., description="Whether vectorization succeeded")
    record_id: int = Field(..., description="The processed record ID")
    scrap_id: Optional[str] = Field(default=None, description="Created scrap vector record ID")
    message: str = Field(..., description="Result summary message")


class DebateInsightVectorizeRequest(BaseModel):
    """Request payload for vectorizing a debate insight/takeaway."""

    member_id: str = Field(..., description="Unique member UUID", min_length=1)
    session_id: str = Field(..., description="Debate conversation session ID", min_length=1)
    book_title: str = Field(..., description="Title of the book discussed", min_length=1)
    persona_id: str = Field(..., description="Debate partner persona ID", min_length=1)
    summary: str = Field(..., description="Debate takeaway and summary text", min_length=1)
    topic: Optional[str] = Field(default="", description="Core discussion topic/issue")


class DebateInsightVectorizeResponse(BaseModel):
    """Response payload after debate insight vectorization."""

    success: bool = Field(..., description="Whether vectorization and insertion succeeded")
    insight_id: Optional[str] = Field(default=None, description="Created debate insight record ID")
    message: str = Field(..., description="Result summary message")
