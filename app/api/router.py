"""FastAPI API routes for AI Agent services with 8 Personas and 2 Modes."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    PersonaInfo,
    SwitchSuggestionResponse,
)
from app.core.config import settings
from app.domain.graph.workflow import create_agent_graph
from app.domain.personas import (
    CAT_ID,
    DEBATE_CRITIC_ID,
    PERSONA_REGISTRY,
)
from app.infrastructure.redis_session import get_redis_session_manager
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")
_graph = create_agent_graph()


@api_router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Service health and connection status endpoint."""
    redis_mgr = get_redis_session_manager()
    supabase_client = get_supabase_client()
    if supabase_client.is_connected:
        await supabase_client.ping_db()

    return HealthResponse(
        status="healthy",
        environment=settings.app_env,
        version="0.1.0",
        redis_connected=redis_mgr._is_redis_available,
        supabase_connected=supabase_client.is_connected,
    )


@api_router.get("/personas", response_model=List[PersonaInfo], tags=["Personas"])
async def list_personas(
    mode: Optional[str] = Query(
        default=None,
        description="Filter personas by mode: LIBRARIAN (사서) or DEBATE (토론)",
    ),
) -> List[PersonaInfo]:
    """Retrieve list of supported DPYB AI personas (4 Librarians: CAT, SHOEBILL, SEA_SLUG, GECKO + 4 Debaters)."""
    results = []
    for p in PERSONA_REGISTRY.values():
        if mode and p["mode"].upper() != mode.upper():
            continue
        results.append(
            PersonaInfo(
                persona_id=p["persona_id"],
                display_name=p["display_name"],
                mode=p["mode"],
                description=p["description"],
                tone=p["tone"],
            )
        )
    return results


@api_router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_persona(request: ChatRequest) -> ChatResponse:
    """Chat with the persona-driven AI librarian or debate partner.

    Supports custom user-defined librarian names, memory RAG, bookshelf search,
    and persona handoff across the 8 personas.
    """
    session_mgr = get_redis_session_manager()
    session_id = request.session_id or "default"

    # Default persona selection based on mode
    requested_mode = request.mode or "LIBRARIAN"
    if request.persona:
        target_persona = request.persona
    else:
        target_persona = CAT_ID if requested_mode == "LIBRARIAN" else DEBATE_CRITIC_ID

    # Normalize backward compatibility aliases
    alias_map = {
        "BLUE": "CAT",
        "RUSSIAN_BLUE": "CAT",
        "LIBRARIAN_3": "SEA_SLUG",
        "LIBRARIAN_4": "GECKO",
    }
    target_persona = alias_map.get(target_persona, target_persona)

    try:
        # 1. Retrieve session history from Redis if exists
        saved_session = await session_mgr.get_session(session_id)
        history_messages: List[BaseMessage] = []
        active_persona = target_persona
        context_summary = None

        if saved_session:
            active_persona = request.persona or saved_session.get("active_persona", active_persona)
            active_persona = alias_map.get(active_persona, active_persona)
            context_summary = saved_session.get("context_summary")
            for msg_data in saved_session.get("messages", []):
                role = msg_data.get("role")
                content = msg_data.get("content", "")
                if role == "user":
                    history_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    history_messages.append(AIMessage(content=content))

        # Add current user message
        history_messages.append(HumanMessage(content=request.message))

        # 2. Invoke LangGraph workflow
        initial_state = {
            "messages": history_messages,
            "member_id": request.member_id,
            "active_persona": active_persona,
            "librarian_name": request.librarian_name,
            "mode": requested_mode,
            "switch_suggestion": None,
            "context_summary": context_summary,
            "handoff_target": None,
        }

        result_state = await _graph.ainvoke(initial_state)

        # 3. Extract final reply and active persona
        final_messages = result_state.get("messages", [])
        last_ai_msg = ""
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                last_ai_msg = str(msg.content)
                break

        current_active_persona = result_state.get("active_persona", active_persona)
        persona_meta = PERSONA_REGISTRY.get(current_active_persona, PERSONA_REGISTRY[CAT_ID])

        # If user assigned a custom librarian name and current persona is a librarian, use it
        if request.librarian_name and persona_meta.get("mode") == "LIBRARIAN":
            display_name = request.librarian_name
        else:
            display_name = persona_meta.get("display_name", current_active_persona)

        persona_mode = persona_meta.get("mode", requested_mode)

        suggestion_data = result_state.get("switch_suggestion")
        switch_suggestion = None
        if suggestion_data:
            switch_suggestion = SwitchSuggestionResponse(
                suggested_persona=suggestion_data["suggested_persona"],
                display_name=suggestion_data["display_name"],
                reason=suggestion_data["reason"],
            )

        # 4. Save session state to Redis (sliding window of last 10 messages)
        serializable_history = []
        for msg in final_messages[-10:]:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            serializable_history.append({"role": role, "content": str(msg.content)})

        await session_mgr.save_session(
            session_id=session_id,
            data={
                "member_id": request.member_id,
                "active_persona": current_active_persona,
                "librarian_name": request.librarian_name,
                "mode": persona_mode,
                "context_summary": result_state.get("context_summary"),
                "messages": serializable_history,
            },
        )

        return ChatResponse(
            session_id=session_id,
            reply=last_ai_msg or "답변을 정리하고 있습니다.",
            active_persona=current_active_persona,
            display_name=display_name,
            mode=persona_mode,
            switch_suggestion=switch_suggestion,
        )

    except Exception as e:
        logger.exception("Error processing chat request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 처리 중 오류가 발생했습니다: {str(e)}",
        ) from e
