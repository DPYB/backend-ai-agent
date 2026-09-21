"""Pydantic request and response schemas for FastAPI endpoints."""

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

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
    book_id: Optional[str] = Field(
        default=None,
        description="Target book ID in user's bookshelf for debate mode",
        examples=["book-123", "550e8400-e29b-41d4-a716-446655440000"],
    )
    topic: Optional[str] = Field(
        default=None,
        description="Debate topic or specific discussion agenda",
        examples=["상실의 아픔과 성장의 의미"],
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

        # 2. Normalize persona and map librarian_id securely
        from app.domain.personas import normalize_persona

        # Check if persona is explicitly a debate partner
        persona_normalized = (
            normalize_persona(self.persona, default_mode="LIBRARIAN") if self.persona else None
        )
        is_debate_persona = bool(persona_normalized and persona_normalized.startswith("DEBATE_"))

        if self.mode == "DEBATE" or is_debate_persona:
            self.mode = "DEBATE"
            effective_raw = self.persona or self.librarian_id
        else:
            effective_raw = self.librarian_id or self.persona
        self.persona = normalize_persona(effective_raw, default_mode=self.mode or "LIBRARIAN")

        # 3. Assemble location from flat coordinates if not already present
        if not self.location and self.latitude is not None and self.longitude is not None:
            self.location = LocationPayload(latitude=self.latitude, longitude=self.longitude)

        # 4. Generate or validate session_id
        if not self.session_id:
            self.session_id = str(uuid4())
        else:
            try:
                UUID(str(self.session_id))
            except (ValueError, TypeError, AttributeError) as err:
                from app.core.config import settings

                if getattr(settings, "app_env", "").lower() in ("test", "development"):
                    pass
                else:
                    raise ValueError("session_id는 올바른 UUID 형식이어야 합니다.") from err

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


class LibraryBook(BaseModel):
    """User's personal bookshelf book details."""

    title: str = Field(..., description="Book title (도서명)")
    author: Optional[str] = Field(default="미상", description="Author name (저자명)")
    status: Optional[str] = Field(
        default="보유 중", description="Reading status ('READING', 'COMPLETED', 'WISH')"
    )


class WeatherSignal(BaseModel):
    """Weather signal details for frontend WeatherMoodBadge."""

    condition: Optional[str] = Field(
        default=None,
        description="Standard weather condition ('clear', 'cloudy', 'rainy', 'snowy', 'stormy', 'foggy')",
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Temperature in Celsius (온도)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable weather description summary",
    )
    location_source: str = Field(
        default="none",
        description="Location origin: 'user', 'default_seoul', 'text_stated', or 'none'",
    )


class SignalsResponse(BaseModel):
    """Contextual conversation signals for frontend mood and weather chips."""

    weather: Optional[WeatherSignal] = Field(
        default=None,
        description="Weather context signal",
    )
    time_of_day: Optional[str] = Field(
        default=None,
        description="Time of day ('dawn', 'day', 'evening', 'night')",
    )
    mood: Optional[str] = Field(
        default=None,
        description="Conversation mood ('cozy', 'adventurous', 'reflective', 'dreamy', 'thrilling', 'calm')",
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
        description="Character display name (블루, 슈빌, 누디, 게코 or custom librarian_name)",
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
    library_books: List[LibraryBook] = Field(
        default_factory=list,
        description="Structured personal bookshelf books (내 서재 보유 도서 목록)",
    )
    signals: Optional[SignalsResponse] = Field(
        default=None,
        description="Weather, time of day, and emotional mood context signals for badge display",
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


class ClassifyGenreRequest(BaseModel):
    """Request payload for book genre classification."""

    title: str = Field(..., description="도서 제목", min_length=1)
    author: Optional[str] = Field(default="", description="저자명")
    isbn: Optional[str] = Field(default="", description="ISBN")
    raw_category: Optional[str] = Field(default="", description="원본 카테고리/주제")


class ClassifyGenreResponse(BaseModel):
    """Response payload for book genre classification."""

    genre: str = Field(..., description="표준 KDC 장르 코드 (LITERATURE, PHILOSOPHY 등)")
    confidence: float = Field(default=1.0, description="분류 신뢰도 (0.0 ~ 1.0)")
