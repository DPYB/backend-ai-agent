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

    # Current authenticated member UUID (strictly isolates personal scrap vectors & library)
    member_id: str

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
