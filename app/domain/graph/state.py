"""Agent graph state definitions for LangGraph with 8 Personas and custom librarian name."""

from typing import Annotated, List, Literal, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

PersonaType = Literal[
    "CAT",
    "SHOEBILL",
    "SEA_SLUG",
    "GECKO",
    "BLUE",
    "DEBATE_CRITIC",
    "DEBATE_STORYTELLER",
    "DEBATE_COUNSELOR",
    "DEBATE_OBSERVER",
]

ModeType = Literal["LIBRARIAN", "DEBATE"]


class SwitchSuggestion(TypedDict, total=False):
    """Schema for librarian or debate partner switch suggestions sent to frontend."""

    suggested_persona: str
    display_name: str
    reason: str


class AgentState(TypedDict):
    """State definition for 8-Persona LangGraph workflow."""

    # Chat history with standard LangGraph message reducer
    messages: Annotated[List[BaseMessage], add_messages]

    # Current authenticated member UUID (strictly isolates personal scrap vectors & library, None for guest)
    member_id: Optional[str]

    # Raw Bearer token for Token Relay to backend-core-api
    auth_token: Optional[str]

    # Currently active persona in control (Head Agent)
    active_persona: str

    # User-defined custom librarian name (회원이 직접 지어준 사서 애칭)
    librarian_name: Optional[str]

    # Operating mode: LIBRARIAN (사서) or DEBATE (토론)
    mode: Optional[ModeType]

    # Frontend button trigger suggestion metadata
    switch_suggestion: Optional[SwitchSuggestion]

    # Factual context summary sanitized by summarizer_node to prevent persona contamination
    context_summary: Optional[str]

    # Internal routing target when a handoff is actively executed
    handoff_target: Optional[str]

    # Curation request metadata passed from Master Persona to Curator Agent
    curator_request: Optional[str]

    # Verified book list returned from Curator Agent back to Master Persona
    curated_books: Optional[List[dict]]

    # Geolocation coordinates (lat, lon) for live weather determination
    location_coords: Optional[dict]

    # Live weather summary (e.g. '보통 비, 기온 18.5°C')
    weather_context: Optional[str]

    # Action intent: 'chat' or 'conclude' (from ChatRequest.action)
    action: Optional[str]

    # Target book ID for debate mode
    book_id: Optional[str]

    # Debate topic or agenda
    topic: Optional[str]

    # Factual book information (title, author, publisher, description) to ground debate personas against hallucination
    debate_book_info: Optional[dict]

    # Whether the debate session has concluded with wrap-up curation
    is_concluded: Optional[bool]

    # Structured wrap-up summary of the debate discussion
    debate_summary: Optional[str]

    # Sliding window history of previously recommended book titles (to prevent repeating recommendations)
    recommended_history: Optional[List[str]]
