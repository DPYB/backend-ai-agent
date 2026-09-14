"""FastAPI API routes for AI Agent services with 8 Personas and 2 Modes."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    PersonaInfo,
    RecommendedBook,
    SwitchSuggestionResponse,
)
from app.core.config import settings
from app.domain.graph.nodes import extract_message_text
from app.domain.graph.workflow import ALL_PERSONA_NODES, create_agent_graph
from app.domain.personas import (
    CAT_ID,
    DEBATE_CRITIC_ID,
    PERSONA_REGISTRY,
)
from app.infrastructure.redis_session import (
    RedisSessionManager,
    get_redis_session_manager,
)
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


def extract_member_id_from_auth(auth_header: Optional[str]) -> Optional[str]:
    """Extract authenticated member UUID from JWT Authorization header if present."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.replace("Bearer ", "", 1).strip()
    try:
        import jwt

        # Safely extract sub/member_id from JWT token payload
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub") or payload.get("member_id")
        return str(sub).strip() if sub else None
    except Exception:
        return None


async def _prepare_chat_context(
    request: ChatRequest,
    authorization: Optional[str] = None,
) -> Tuple[str, str, str, Dict[str, Any], Optional[str], RedisSessionManager]:
    """Prepare initial conversation context, weather info, and session state."""
    session_mgr = get_redis_session_manager()
    session_id = request.session_id or "default"

    # Resolve member_id: 1) JWT Bearer token sub, 2) request body, 3) generated guest UUID
    authenticated_member_id = extract_member_id_from_auth(authorization)
    effective_member_id = authenticated_member_id or request.member_id or str(uuid4())

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

    # 2. Fetch live weather context (user location or Seoul default fallback)
    from app.infrastructure.weather_client import get_weather_client

    weather_client = get_weather_client()
    location_coords = None

    if request.location:
        location_coords = {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
        }
        weather_context = await weather_client.get_current_weather(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
        )
    else:
        # Fallback to Seoul standard weather (37.5665, 126.9780)
        seoul_weather = await weather_client.get_current_weather(37.5665, 126.9780)
        if seoul_weather:
            weather_context = f"[위치 권한 미허용 상태] 현재 서울 기준 날씨: {seoul_weather}"
        else:
            weather_context = "[위치 권한 미허용 상태]"

    initial_state = {
        "messages": history_messages,
        "member_id": effective_member_id,
        "active_persona": active_persona,
        "librarian_name": request.librarian_name,
        "mode": requested_mode,
        "switch_suggestion": None,
        "context_summary": context_summary,
        "handoff_target": None,
        "curator_request": None,
        "curated_books": None,
        "location_coords": location_coords,
        "weather_context": weather_context,
    }

    return (
        session_id,
        active_persona,
        requested_mode,
        initial_state,
        weather_context,
        session_mgr,
    )


@api_router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_persona(
    request: ChatRequest,
    authorization: Optional[str] = Header(default=None),
) -> ChatResponse:
    """Chat with the persona-driven AI librarian or debate partner.

    Supports custom user-defined librarian names, memory RAG, bookshelf search,
    and persona handoff across the 8 personas.
    """
    (
        session_id,
        active_persona,
        requested_mode,
        initial_state,
        weather_context,
        session_mgr,
    ) = await _prepare_chat_context(request, authorization=authorization)

    try:
        result_state = await _graph.ainvoke(initial_state)

        final_messages = result_state.get("messages", [])
        last_ai_msg = ""
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                last_ai_msg = extract_message_text(msg.content)
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

        # Save session state to Redis (sliding window of last 10 messages)
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

        curated_books_data = result_state.get("curated_books") or []
        recommended_books = []
        for b in curated_books_data:
            if isinstance(b, dict):
                recommended_books.append(
                    RecommendedBook(
                        title=str(b.get("title", "")),
                        author=str(b.get("author", "")),
                        isbn=str(b.get("isbn", "")),
                        publisher=b.get("publisher"),
                        page_count=b.get("page_count"),
                        genre=b.get("genre"),
                        cover_url=b.get("cover_url"),
                        reason=b.get("reason"),
                        description=b.get("description"),
                    )
                )

        return ChatResponse(
            session_id=session_id,
            reply=last_ai_msg or "답변을 정리하고 있습니다.",
            active_persona=current_active_persona,
            display_name=display_name,
            mode=persona_mode,
            switch_suggestion=switch_suggestion,
            recommended_books=recommended_books,
        )

    except Exception as e:
        logger.exception("Error processing chat request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 처리 중 오류가 발생했습니다: {str(e)}",
        ) from e


def _format_sse(event_type: str, data: Any) -> str:
    """Format Server-Sent Event (SSE) message frame."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@api_router.post("/chat/stream", tags=["Chat"])
async def chat_stream_with_persona(
    request: ChatRequest,
    authorization: Optional[str] = Header(default=None),
) -> StreamingResponse:
    """Stream real-time chat responses chunk by chunk using Server-Sent Events (SSE).

    Emits structured events:
      - metadata: Initial session and active persona information
      - token: Real-time text token deltas from the master persona
      - switch_suggestion: Persona handoff recommendation (if triggered)
      - done: Stream completion with full accumulated response and session persistence
      - error: Error notification if an exception occurs
    """
    (
        session_id,
        active_persona,
        requested_mode,
        initial_state,
        weather_context,
        session_mgr,
    ) = await _prepare_chat_context(request, authorization=authorization)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Emit metadata event
            persona_meta = PERSONA_REGISTRY.get(active_persona, PERSONA_REGISTRY[CAT_ID])
            display_name = (
                request.librarian_name
                if (request.librarian_name and persona_meta.get("mode") == "LIBRARIAN")
                else persona_meta.get("display_name", active_persona)
            )
            yield _format_sse(
                "metadata",
                {
                    "session_id": session_id,
                    "active_persona": active_persona,
                    "display_name": display_name,
                    "mode": persona_meta.get("mode", requested_mode),
                    "weather_context": weather_context,
                },
            )

            # 2. Iterate through LangGraph events
            accumulated_text = ""
            tokens_emitted = 0
            last_active_persona = active_persona
            switch_suggestion_data = None
            curated_books_data: List[Dict[str, Any]] = []
            final_messages: List[BaseMessage] = list(initial_state["messages"])
            context_summary = initial_state.get("context_summary")

            async for event in _graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")
                node = event.get("metadata", {}).get("langgraph_node")

                # Real-time token streaming for active master persona nodes only
                if kind == "on_chat_model_stream" and node in ALL_PERSONA_NODES:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        text_delta = ""
                        if hasattr(chunk, "content"):
                            text_delta = extract_message_text(chunk.content)
                        if text_delta:
                            accumulated_text += text_delta
                            tokens_emitted += 1
                            yield _format_sse("token", {"delta": text_delta})

                elif kind == "on_chain_end":
                    node_name = event.get("name")
                    output = event.get("data", {}).get("output")
                    if node_name in ALL_PERSONA_NODES and isinstance(output, dict):
                        if output.get("active_persona"):
                            last_active_persona = output["active_persona"]
                        if output.get("switch_suggestion"):
                            switch_suggestion_data = output["switch_suggestion"]
                        if output.get("curated_books"):
                            curated_books_data = output["curated_books"]
                        if output.get("messages"):
                            for m in output["messages"]:
                                final_messages.append(m)
                            if tokens_emitted == 0:
                                ai_m = output["messages"][-1]
                                accumulated_text = extract_message_text(
                                    getattr(ai_m, "content", "")
                                )
                    elif node_name == "book_curator_node" and isinstance(output, dict):
                        if output.get("curated_books"):
                            curated_books_data = output["curated_books"]
                            yield _format_sse("books", {"books": curated_books_data})
                    elif node_name == "summarizer_node" and isinstance(output, dict):
                        if output.get("active_persona"):
                            last_active_persona = output["active_persona"]
                        if output.get("context_summary"):
                            context_summary = output["context_summary"]

            # Fallback for mock responses or non-streamed outputs
            if tokens_emitted == 0 and accumulated_text:
                yield _format_sse("token", {"delta": accumulated_text})

            # Emit switch suggestion if triggered
            if switch_suggestion_data:
                yield _format_sse("switch_suggestion", switch_suggestion_data)

            # 3. Finalize and persist session to Redis
            final_meta = PERSONA_REGISTRY.get(last_active_persona, PERSONA_REGISTRY[CAT_ID])
            final_display_name = (
                request.librarian_name
                if (request.librarian_name and final_meta.get("mode") == "LIBRARIAN")
                else final_meta.get("display_name", last_active_persona)
            )
            final_mode = final_meta.get("mode", requested_mode)

            # Ensure final_messages contains the assistant reply
            if not any(
                isinstance(m, AIMessage) for m in final_messages[len(initial_state["messages"]) :]
            ):
                final_messages.append(AIMessage(content=accumulated_text))

            serializable_history = []
            for msg in final_messages[-10:]:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                serializable_history.append({"role": role, "content": str(msg.content)})

            await session_mgr.save_session(
                session_id=session_id,
                data={
                    "member_id": request.member_id,
                    "active_persona": last_active_persona,
                    "librarian_name": request.librarian_name,
                    "mode": final_mode,
                    "context_summary": context_summary,
                    "messages": serializable_history,
                },
            )

            formatted_books = []
            for b in curated_books_data:
                if isinstance(b, dict):
                    formatted_books.append(
                        {
                            "title": str(b.get("title", "")),
                            "author": str(b.get("author", "")),
                            "isbn": str(b.get("isbn", "")),
                            "publisher": b.get("publisher"),
                            "page_count": b.get("page_count"),
                            "genre": b.get("genre"),
                            "cover_url": b.get("cover_url"),
                            "reason": b.get("reason"),
                            "description": b.get("description"),
                        }
                    )

            # 4. Emit done event
            yield _format_sse(
                "done",
                {
                    "session_id": session_id,
                    "reply": accumulated_text or "답변을 정리하고 있습니다.",
                    "active_persona": last_active_persona,
                    "display_name": final_display_name,
                    "mode": final_mode,
                    "switch_suggestion": switch_suggestion_data,
                    "recommended_books": formatted_books,
                },
            )

        except Exception as e:
            logger.exception("Error in chat streaming: %s", e)
            yield _format_sse(
                "error",
                {"detail": f"AI 스트리밍 처리 중 오류가 발생했습니다: {str(e)}"},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )
