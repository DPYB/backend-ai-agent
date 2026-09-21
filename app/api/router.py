"""FastAPI API routes for AI Agent services with 8 Personas and 2 Modes."""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ClassifyGenreRequest,
    ClassifyGenreResponse,
    HealthResponse,
    LibraryBook,
    PersonaInfo,
    RecommendedBook,
    SignalsResponse,
    SwitchSuggestionResponse,
    WeatherSignal,
)
from app.core.config import settings
from app.core.context import current_auth_token
from app.domain.graph.nodes import (
    extract_debate_book_title,
    extract_message_text,
)
from app.domain.graph.workflow import ALL_PERSONA_NODES, create_agent_graph
from app.domain.guardrails import evaluate_guardrails
from app.domain.personas import (
    CAT_ID,
    PERSONA_REGISTRY,
)
from app.infrastructure.redis_session import (
    RedisSessionManager,
    get_redis_session_manager,
)
from app.infrastructure.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _extract_library_books_from_text(text: str) -> List[Dict[str, str]]:
    """Extract library books formatted as '### 📚 {title}' from AI response text.

    Filters out single emojis or non-title headers.
    """
    if not text or "### 📚" not in text:
        return []

    books: List[Dict[str, str]] = []
    seen: set = set()
    # Match blocks starting with ### 📚 {title}
    pattern = re.compile(
        r"^###\s*📚\s*([^\n]+?)\s*\n([\s\S]*?)(?=^###\s|$(?![\r\n]))", re.MULTILINE
    )
    for m in pattern.finditer(text):
        raw_title = m.group(1).strip()
        body = m.group(2) or ""
        clean_title = re.sub(r"^[『《\"'‘`<>\s]+|[』》\"'’`<>\s]+$", "", raw_title).strip()
        if clean_title and 1 <= len(clean_title) <= 50 and clean_title not in seen:
            seen.add(clean_title)
            author_match = re.search(r"\*\*저자\*\*\s*[:：]\s*([^\n]+)", body)
            status_match = re.search(r"\*\*독서\s*상태\*\*\s*[:：]\s*([^\n]+)", body)
            author = author_match.group(1).strip() if author_match else "미상"
            status = status_match.group(1).strip() if status_match else "보유 중"
            books.append({"title": clean_title, "author": author, "status": status})
    return books


api_router = APIRouter(prefix="/api/v1")
_graph = create_agent_graph()


async def save_debate_insight_task(
    member_id: str,
    session_id: str,
    book_title: str,
    persona_id: str,
    summary: str,
    topic: Optional[str] = None,
) -> None:
    """Background task to vectorize and store debate insight in agent.debate_insights."""
    try:
        from app.domain.memory.rag_tool import generate_query_embedding
        from app.infrastructure.db.repository import get_agent_vector_repository

        content_to_embed = f"도서: {book_title}\n논제: {topic or ''}\n토론 요약: {summary}".strip()
        embedding = generate_query_embedding(content_to_embed)
        repo = get_agent_vector_repository()
        await repo.insert_debate_insight(
            member_id=member_id,
            session_id=session_id,
            book_title=book_title,
            persona_id=persona_id,
            summary=summary,
            topic=topic,
            embedding=embedding,
        )
        logger.info(
            "Background debate insight vectorized and saved for member %s (book: %s)",
            member_id,
            book_title,
        )
    except Exception as e:
        logger.error("Failed to vectorize debate insight in background: %s", e)


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


def extract_auth_info_from_auth(
    auth_header: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract authenticated member UUID / sub, raw token, and role from JWT Authorization header.

    Validates signature and expiration using shared JWT_SECRET_KEY.

    Returns:
        Tuple of (sub, raw_token, role) if authenticated, or (None, None, None) if no header.
        - role: "guest" or "member" (default "member" if not specified)
        - sub: e.g. "guest-123e4567-..." or member UUID

    Raises:
        HTTPException(401): If token is expired, invalid, forged, or malformed.
    """
    if not auth_header or not auth_header.strip():
        return None, None, None

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 헤더는 'Bearer <token>' 형식이어야 합니다.",
        )

    token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 누락되었습니다.",
        )

    # 1. CI / Test mock token support matching backend-core-api (Safe guard for non-production)
    is_testing_env = getattr(settings, "app_env", "").lower() in ("test", "development")
    if is_testing_env and token.startswith("mock-token-"):
        mock_id = token.replace("mock-token-", "")
        role = "guest" if mock_id.startswith("guest-") else "member"
        return mock_id, token, role
    if is_testing_env and token == "test-token":
        return "00000000-0000-0000-0000-000000000001", token, "member"

    # 2. Standard JWT signature and expiration verification
    try:
        import jwt

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
        sub = payload.get("sub") or payload.get("member_id")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 사용자 식별자(sub)가 존재하지 않습니다.",
            )
        raw_role = payload.get("role")
        sub_str = str(sub).strip()
        if raw_role == "guest" or sub_str.startswith("guest-"):
            role = "guest"
        else:
            role = "member"

        return sub_str, token, role
    except jwt.ExpiredSignatureError as e:
        logger.warning("Expired JWT token received: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="만료된 인증 토큰입니다. 다시 로그인해 주세요.",
        ) from e
    except jwt.PyJWTError as e:
        logger.warning("Invalid JWT signature or format: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
        ) from e
    except Exception as e:
        logger.error("Unexpected error decoding JWT: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰 처리 중 오류가 발생했습니다.",
        ) from e


def extract_member_id_from_auth(
    auth_header: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Backward compatibility wrapper returning (member_id, raw_token)."""
    sub, token, _ = extract_auth_info_from_auth(auth_header)
    return sub, token


def _build_signals(
    weather_summary: Optional[str],
    location_source: str,
    message: str,
) -> SignalsResponse:
    """Construct structured weather, time-of-day, and mood signals for frontend badge display."""
    cond: Optional[str] = None
    temp: Optional[float] = None
    if weather_summary:
        text_lower = weather_summary.lower()
        if "비" in text_lower or "소나기" in text_lower:
            cond = "rainy"
        elif "눈" in text_lower:
            cond = "snowy"
        elif "흐림" in text_lower or "구름" in text_lower:
            cond = "cloudy"
        elif "안개" in text_lower:
            cond = "foggy"
        elif "뇌우" in text_lower:
            cond = "stormy"
        else:
            cond = "clear"

        temp_match = re.search(r"기온\s*([-\d.]+)\s*°?C?", weather_summary)
        if temp_match:
            try:
                temp = float(temp_match.group(1))
            except ValueError:
                pass

    weather_sig = WeatherSignal(
        condition=cond,
        temperature=temp,
        description=weather_summary or "날씨 정보 없음",
        location_source=location_source,
    )

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    hour = now_kst.hour

    if 5 <= hour < 8:
        time_of_day = "dawn"
    elif 8 <= hour < 17:
        time_of_day = "day"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    msg = message.lower()
    if any(w in msg for w in ["신나", "모험", "짜릿", "도전"]):
        mood = "adventurous"
    elif any(w in msg for w in ["우울", "슬퍼", "눈물", "외로", "힘들"]):
        mood = "calm"
    elif any(w in msg for w in ["생각", "고민", "철학", "의미", "사색", "토론"]):
        mood = "reflective"
    elif any(w in msg for w in ["꿈", "환상", "신비", "판타지"]):
        mood = "dreamy"
    elif any(w in msg for w in ["긴장", "스릴", "추리", "미스터리"]):
        mood = "thrilling"
    else:
        mood = "cozy"

    return SignalsResponse(
        weather=weather_sig if location_source != "none" else None,
        time_of_day=time_of_day,
        mood=mood,
    )


async def _prepare_chat_context(
    request: ChatRequest,
    authorization: Optional[str] = None,
) -> Tuple[str, str, str, Dict[str, Any], Optional[str], RedisSessionManager, str, Optional[str]]:
    """Prepare initial conversation context, weather info, and session state.

    Returns:
        Tuple of:
          - session_id
          - active_persona
          - requested_mode
          - initial_state
          - weather_context
          - session_mgr
          - user_role ("guest" or "member")
          - guest_id (sub string if guest, else None)
    """
    session_mgr = get_redis_session_manager()

    # Resolve member_id and role:
    # 1) Verified JWT Bearer token sub and role
    # 2) Explicit request.member_id (internal or testing)
    # 3) None (Guest mode: unauthenticated user without random UUID generation)
    authenticated_member_id, raw_token, token_role = extract_auth_info_from_auth(authorization)
    effective_member_id = authenticated_member_id or request.member_id or None

    user_role = token_role or (
        "guest" if (effective_member_id and effective_member_id.startswith("guest-")) else "member"
    )
    if not effective_member_id and not authorization:
        user_role = "guest"

    guest_id = effective_member_id if user_role == "guest" else None

    # Set request-scoped token for downstream tool Token Relay
    current_auth_token.set(raw_token)

    # Normalize persona using comprehensive matcher
    from app.domain.personas import normalize_persona

    requested_mode = request.mode or "LIBRARIAN"
    # Check if request.persona is explicitly a debate partner
    norm_persona = (
        normalize_persona(request.persona, default_mode="LIBRARIAN") if request.persona else None
    )
    if requested_mode == "DEBATE" or (norm_persona and norm_persona.startswith("DEBATE_")):
        requested_mode = "DEBATE"
        raw_persona = request.persona or request.librarian_id
    else:
        raw_persona = request.librarian_id or request.persona

    target_persona = normalize_persona(raw_persona, default_mode=requested_mode)

    # 1. Automatic Session Partitioning by Member and Persona ({effective_member_id}:{validated_uuid}:{persona})
    # Partition session_id at the DB level for all 8 personas.
    # For guest users, strictly anchor the session to {guest_id}:{persona} so conversations are isolated per guest.
    # For registered members, enforce namespace prefixing f"{effective_member_id}:{validated_uuid}" to prevent cross-account eavesdropping.
    if user_role == "guest" and guest_id:
        raw_session_id = guest_id
    elif effective_member_id and user_role != "guest":
        base_sid = request.session_id or "default"
        if base_sid.startswith(f"{effective_member_id}:"):
            raw_session_id = base_sid
        else:
            raw_session_id = f"{effective_member_id}:{base_sid}"
    else:
        raw_session_id = request.session_id or "default"

    if not raw_session_id.endswith(f":{target_persona}"):
        partitioned_session_id = f"{raw_session_id}:{target_persona}"
    else:
        partitioned_session_id = raw_session_id

    session_id = partitioned_session_id
    logger.info(
        "Chat context resolved: role=%s, raw_persona=%s -> target_persona=%s, raw_session=%s -> session_id=%s (thread_id)",
        user_role,
        raw_persona,
        target_persona,
        raw_session_id,
        session_id,
    )
    # Retrieve session history from Redis if exists for this partitioned session
    saved_session = await session_mgr.get_session(session_id)
    history_messages: List[BaseMessage] = []
    active_persona = target_persona
    context_summary = None
    saved_rec_history: List[str] = []

    if saved_session:
        saved_persona = saved_session.get("active_persona")
        saved_persona = (
            normalize_persona(saved_persona, default_mode=requested_mode) if saved_persona else None
        )
        active_persona = normalize_persona(
            request.persona or saved_persona or target_persona, default_mode=requested_mode
        )
        context_summary = saved_session.get("context_summary")
        saved_rec_history = saved_session.get("recommended_history") or []

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
    location_source = "none"
    weather_summary_for_signals: Optional[str] = None

    if request.location:
        location_coords = {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude,
        }
        weather_context = await weather_client.get_current_weather(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
        )
        if weather_context:
            location_source = "user"
            weather_summary_for_signals = weather_context
            weather_context = (
                f"[위치 권한 허용됨 - 사용자 실제 위치의 실시간 날씨]: {weather_context}"
            )
        else:
            weather_context = "[위치 권한 허용 상태이나 실시간 날씨 조회 실패]"
            location_source = "none"
    else:
        # Fallback to Seoul standard weather (37.5665, 126.9780)
        seoul_weather = await weather_client.get_current_weather(37.5665, 126.9780)
        if seoul_weather:
            weather_context = f"[위치 권한 미허용 상태] 현재 서울 기준 날씨: {seoul_weather}"
            location_source = "default_seoul"
            weather_summary_for_signals = seoul_weather
        else:
            weather_context = "[위치 권한 미허용 상태]"
            location_source = "none"

    signals = _build_signals(weather_summary_for_signals, location_source, request.message)

    # 3. Ground debate target book factual details to eliminate hallucinations
    debate_book_info: Optional[Dict[str, Any]] = None
    if requested_mode == "DEBATE" or target_persona.startswith("DEBATE_"):
        from app.infrastructure.core_api_client import get_core_api_client
        from app.infrastructure.national_library_client import get_national_library_client

        core_client = get_core_api_client()
        nl_client = get_national_library_client()

        if request.book_id:
            try:
                b_details = await core_client.get_book_details(request.book_id)
                if b_details and b_details.get("title"):
                    debate_book_info = b_details
            except Exception as e:
                logger.warning("Failed to fetch book_id=%s from core-api: %s", request.book_id, e)

        if not debate_book_info:
            from app.domain.graph.nodes import extract_debate_book_title

            extracted_title = extract_debate_book_title(history_messages)
            if (
                extracted_title
                and extracted_title not in ("문학 일반", "독서 토론", "토론")
                and len(extracted_title) <= 50
            ):
                try:
                    nl_biblio = await nl_client.search_book(extracted_title)
                    if nl_biblio:
                        debate_book_info = nl_biblio
                except Exception as e:
                    logger.warning("Failed to search debate book from national library: %s", e)

    initial_state = {
        "messages": history_messages,
        "member_id": effective_member_id,
        "auth_token": raw_token,
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
        "action": request.action or "chat",
        "book_id": request.book_id,
        "topic": request.topic,
        "debate_book_info": debate_book_info,
        "signals": signals,
        "is_concluded": False,
        "debate_summary": None,
        "recommended_history": saved_rec_history,
    }

    return (
        session_id,
        active_persona,
        requested_mode,
        initial_state,
        weather_context,
        session_mgr,
        user_role,
        guest_id,
    )


# Standard fallback messages
CIRCUIT_BREAKER_FALLBACK_MSG = (
    "앗, 지금 서재에 방문객이 너무 많아 사서들이 바빠요. 잠시 후 다시 시도해 주세요!"
)
GUEST_LIMIT_EXCEEDED_MSG = (
    "이번 체험에서 대화 가능 횟수를 모두 사용하셨습니다. 정식 로그인 후 다시 만나요!"
)


@api_router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_persona(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
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
        user_role,
        guest_id,
    ) = await _prepare_chat_context(request, authorization=authorization)

    persona_meta = PERSONA_REGISTRY.get(active_persona, PERSONA_REGISTRY[CAT_ID])
    if request.librarian_name and persona_meta.get("mode") == "LIBRARIAN":
        display_name = request.librarian_name
    else:
        display_name = persona_meta.get("display_name", active_persona)
    persona_mode = persona_meta.get("mode", requested_mode)

    # 1. Individual Guest Usage Limit Check
    if user_role == "guest" and guest_id:
        current_usage = await session_mgr.get_guest_usage(guest_id)
        if current_usage >= settings.guest_chat_limit:
            logger.info(
                "Guest %s exceeded chat limit (%d >= %d)",
                guest_id,
                current_usage,
                settings.guest_chat_limit,
            )
            return ChatResponse(
                session_id=session_id,
                reply=GUEST_LIMIT_EXCEEDED_MSG,
                active_persona=active_persona,
                display_name=display_name,
                mode=persona_mode,
                switch_suggestion=None,
                recommended_books=[],
                signals=initial_state.get("signals"),
                is_concluded=False,
                debate_summary=None,
            )

    # 2. Global Circuit Breaker Check (Role-based RPM / RPD)
    is_tripped, trip_type = await session_mgr.check_and_incr_circuit_breaker(user_role)
    if is_tripped:
        logger.warning(
            "Circuit breaker tripped (%s) for role %s. Returning fallback.", trip_type, user_role
        )
        return ChatResponse(
            session_id=session_id,
            reply=CIRCUIT_BREAKER_FALLBACK_MSG,
            active_persona=active_persona,
            display_name=display_name,
            mode=persona_mode,
            switch_suggestion=None,
            recommended_books=[],
            signals=initial_state.get("signals"),
            is_concluded=False,
            debate_summary=None,
        )

    # 1st-3rd: Pre-LLM Guardrails evaluation (Safety -> Input -> Security)
    guardrail_reply = evaluate_guardrails(
        message=request.message,
        persona_id=active_persona,
        librarian_name=request.librarian_name,
    )
    if guardrail_reply:
        logger.info(
            "Pre-LLM guardrail triggered for session %s (persona: %s)",
            session_id,
            active_persona,
        )

        # Save guardrail interaction to Redis session
        serializable_history = []
        if initial_state.get("messages"):
            for msg in initial_state["messages"][-9:]:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                serializable_history.append({"role": role, "content": str(msg.content)})
        serializable_history.append({"role": "assistant", "content": guardrail_reply})

        await session_mgr.save_session(
            session_id=session_id,
            data={
                "member_id": initial_state.get("member_id"),
                "active_persona": active_persona,
                "librarian_name": request.librarian_name,
                "mode": persona_mode,
                "context_summary": initial_state.get("context_summary"),
                "messages": serializable_history,
            },
        )

        return ChatResponse(
            session_id=session_id,
            reply=guardrail_reply,
            active_persona=active_persona,
            display_name=display_name,
            mode=persona_mode,
            switch_suggestion=None,
            recommended_books=[],
            signals=initial_state.get("signals"),
            is_concluded=False,
            debate_summary=None,
        )

    try:
        run_config = {"configurable": {"thread_id": session_id}}
        result_state = await _graph.ainvoke(initial_state, config=run_config)

        # Increment guest usage only on successful normal LLM turn
        if user_role == "guest" and guest_id:
            await session_mgr.incr_guest_usage(guest_id)

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
                "member_id": initial_state.get("member_id"),
                "active_persona": current_active_persona,
                "librarian_name": request.librarian_name,
                "mode": persona_mode,
                "context_summary": result_state.get("context_summary"),
                "messages": serializable_history,
                "recommended_history": result_state.get("recommended_history")
                or initial_state.get("recommended_history", []),
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

        is_concluded = bool(result_state.get("is_concluded", False))
        debate_summary = result_state.get("debate_summary")

        # Auto-persist debate insight to agent.debate_insights in background if concluded
        # NOTE: Skip background DB write if user is guest (guest write lock)
        effective_mid = initial_state.get("member_id")
        if (
            is_concluded
            and debate_summary
            and effective_mid
            and user_role != "guest"
            and not str(effective_mid).startswith("guest-")
        ):
            book_title = extract_debate_book_title(final_messages)
            background_tasks.add_task(
                save_debate_insight_task,
                member_id=str(effective_mid),
                session_id=session_id,
                book_title=book_title,
                persona_id=current_active_persona,
                summary=debate_summary,
                topic=None,
            )

        # Extract library books from text if present (e.g. from search_my_library)
        extracted_lib_books = _extract_library_books_from_text(last_ai_msg)
        library_books_objs = [
            LibraryBook(
                title=b["title"],
                author=b.get("author", "미상"),
                status=b.get("status", "보유 중"),
            )
            for b in extracted_lib_books
        ]

        return ChatResponse(
            session_id=session_id,
            reply=last_ai_msg or "답변을 정리하고 있습니다.",
            active_persona=current_active_persona,
            display_name=display_name,
            mode=persona_mode,
            switch_suggestion=switch_suggestion,
            recommended_books=recommended_books,
            library_books=library_books_objs,
            signals=initial_state.get("signals"),
            is_concluded=is_concluded,
            debate_summary=debate_summary,
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
    background_tasks: BackgroundTasks,
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
        user_role,
        guest_id,
    ) = await _prepare_chat_context(request, authorization=authorization)

    # 1st-3rd: Pre-LLM Guardrails evaluation (Safety -> Input -> Security)
    guardrail_reply = evaluate_guardrails(
        message=request.message,
        persona_id=active_persona,
        librarian_name=request.librarian_name,
    )

    persona_meta = PERSONA_REGISTRY.get(active_persona, PERSONA_REGISTRY[CAT_ID])
    display_name = (
        request.librarian_name
        if (request.librarian_name and persona_meta.get("mode") == "LIBRARIAN")
        else persona_meta.get("display_name", active_persona)
    )
    signals_obj = initial_state.get("signals")
    signals_payload = signals_obj.model_dump() if signals_obj else None

    # Check 1: Individual guest limit check before streaming
    guest_limit_tripped = False
    if user_role == "guest" and guest_id:
        current_usage = await session_mgr.get_guest_usage(guest_id)
        if current_usage >= settings.guest_chat_limit:
            guest_limit_tripped = True

    # Check 2: Global circuit breaker check before streaming
    circuit_tripped = False
    if not guest_limit_tripped:
        is_tripped, _ = await session_mgr.check_and_incr_circuit_breaker(user_role)
        if is_tripped:
            circuit_tripped = True

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 1. Emit metadata event
            yield _format_sse(
                "metadata",
                {
                    "session_id": session_id,
                    "active_persona": active_persona,
                    "display_name": display_name,
                    "mode": persona_meta.get("mode", requested_mode),
                    "weather_context": weather_context,
                    "signals": signals_payload,
                },
            )

            # 1.2 If guest limit tripped, stream graceful fallback and complete
            if guest_limit_tripped:
                yield _format_sse("token", {"delta": GUEST_LIMIT_EXCEEDED_MSG})
                yield _format_sse(
                    "done",
                    {
                        "session_id": session_id,
                        "reply": GUEST_LIMIT_EXCEEDED_MSG,
                        "active_persona": active_persona,
                        "display_name": display_name,
                        "mode": persona_meta.get("mode", requested_mode),
                        "switch_suggestion": None,
                        "recommended_books": [],
                        "library_books": [],
                        "signals": signals_payload,
                        "is_concluded": False,
                        "debate_summary": None,
                    },
                )
                return

            # 1.3 If circuit breaker tripped, stream busy fallback and complete
            if circuit_tripped:
                yield _format_sse("token", {"delta": CIRCUIT_BREAKER_FALLBACK_MSG})
                yield _format_sse(
                    "done",
                    {
                        "session_id": session_id,
                        "reply": CIRCUIT_BREAKER_FALLBACK_MSG,
                        "active_persona": active_persona,
                        "display_name": display_name,
                        "mode": persona_meta.get("mode", requested_mode),
                        "switch_suggestion": None,
                        "recommended_books": [],
                        "library_books": [],
                        "signals": signals_payload,
                        "is_concluded": False,
                        "debate_summary": None,
                    },
                )
                return

            # 1.5 If guardrail triggered, stream guidance token and complete without LLM
            if guardrail_reply:
                logger.info(
                    "Streaming guardrail triggered for session %s (persona: %s)",
                    session_id,
                    active_persona,
                )
                yield _format_sse("token", {"delta": guardrail_reply})

                # Persist to Redis session
                serializable_history = []
                if initial_state.get("messages"):
                    for msg in initial_state["messages"][-9:]:
                        role = "user" if isinstance(msg, HumanMessage) else "assistant"
                        serializable_history.append({"role": role, "content": str(msg.content)})
                serializable_history.append({"role": "assistant", "content": guardrail_reply})

                await session_mgr.save_session(
                    session_id=session_id,
                    data={
                        "member_id": request.member_id,
                        "active_persona": active_persona,
                        "librarian_name": request.librarian_name,
                        "mode": persona_meta.get("mode", requested_mode),
                        "context_summary": initial_state.get("context_summary"),
                        "messages": serializable_history,
                    },
                )

                yield _format_sse(
                    "done",
                    {
                        "session_id": session_id,
                        "reply": guardrail_reply,
                        "active_persona": active_persona,
                        "display_name": display_name,
                        "mode": persona_meta.get("mode", requested_mode),
                        "switch_suggestion": None,
                        "recommended_books": [],
                        "library_books": [],
                        "signals": signals_payload,
                        "is_concluded": False,
                        "debate_summary": None,
                    },
                )
                return

            # 2. Iterate through LangGraph events
            accumulated_text = ""
            tokens_emitted = 0
            last_active_persona = active_persona
            switch_suggestion_data = None
            curated_books_data: List[Dict[str, Any]] = []
            final_messages: List[BaseMessage] = list(initial_state["messages"])
            context_summary = initial_state.get("context_summary")
            is_concluded = bool(initial_state.get("is_concluded", False))
            debate_summary = initial_state.get("debate_summary")
            latest_recommended_history: List[str] = list(
                initial_state.get("recommended_history") or []
            )

            run_config = {"configurable": {"thread_id": session_id}}
            async for event in _graph.astream_events(
                initial_state, version="v2", config=run_config
            ):
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
                        if output.get("recommended_history"):
                            latest_recommended_history = output["recommended_history"]
                        if "is_concluded" in output:
                            is_concluded = bool(output["is_concluded"])
                        if "debate_summary" in output:
                            debate_summary = output["debate_summary"]
                        if output.get("messages"):
                            for m in output["messages"]:
                                final_messages.append(m)
                            if tokens_emitted == 0:
                                ai_m = output["messages"][-1]
                                accumulated_text = extract_message_text(
                                    getattr(ai_m, "content", "")
                                )
                    elif node_name in ("curator_node", "book_curator_node") and isinstance(
                        output, dict
                    ):
                        if output.get("curated_books"):
                            curated_books_data = output["curated_books"]
                            yield _format_sse("books", {"books": curated_books_data})
                        if output.get("recommended_history"):
                            latest_recommended_history = output["recommended_history"]
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
                    "member_id": initial_state.get("member_id"),
                    "active_persona": last_active_persona,
                    "librarian_name": request.librarian_name,
                    "mode": final_mode,
                    "context_summary": context_summary,
                    "messages": serializable_history,
                    "recommended_history": latest_recommended_history,
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

            # Increment guest usage only on successful normal LLM stream turn
            if user_role == "guest" and guest_id:
                await session_mgr.incr_guest_usage(guest_id)

            # Auto-persist debate insight to agent.debate_insights in background if concluded
            # NOTE: Skip background DB write if user is guest (guest write lock)
            effective_mid = initial_state.get("member_id")
            if (
                is_concluded
                and debate_summary
                and effective_mid
                and user_role != "guest"
                and not str(effective_mid).startswith("guest-")
            ):
                book_title = extract_debate_book_title(final_messages)
                background_tasks.add_task(
                    save_debate_insight_task,
                    member_id=str(effective_mid),
                    session_id=session_id,
                    book_title=book_title,
                    persona_id=last_active_persona,
                    summary=debate_summary,
                    topic=None,
                )

            # Extract library books from accumulated response text if present
            extracted_stream_lib_books = _extract_library_books_from_text(accumulated_text)

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
                    "library_books": extracted_stream_lib_books,
                    "signals": signals_payload,
                    "is_concluded": is_concluded,
                    "debate_summary": debate_summary,
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


@api_router.post("/classify-genre", response_model=ClassifyGenreResponse)
async def classify_genre(req: ClassifyGenreRequest) -> ClassifyGenreResponse:
    """Classify book genre into standard KDC 10-genre enum code."""
    from app.infrastructure.national_library_client import (
        get_national_library_client,
        map_kdc_to_genre,
    )

    client = get_national_library_client()

    # 1. If ISBN is given, try fast search via National Library
    if req.isbn and req.isbn.strip():
        book_info = await client.search_by_isbn(req.isbn.strip())
        if book_info and book_info.get("genre") and book_info["genre"] != "GENERAL":
            return ClassifyGenreResponse(genre=book_info["genre"], confidence=1.0)

    # 2. Map via KDC rules using subject, title, raw_category
    genre = map_kdc_to_genre(
        kdc="",
        subject=req.raw_category or "",
        title=req.title,
    )
    if genre and genre != "GENERAL":
        return ClassifyGenreResponse(genre=genre, confidence=0.95)

    # 3. Fallback search via title
    if req.title:
        book_info = await client.search_book(req.title, req.author or "")
        if book_info and book_info.get("genre"):
            return ClassifyGenreResponse(genre=book_info["genre"], confidence=0.9)

    return ClassifyGenreResponse(
        genre="LITERATURE" if "소설" in req.title or "시집" in req.title else "GENERAL",
        confidence=0.8,
    )
