"""Node implementations for LangGraph: 8 Personas and Summarizer node."""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.domain.graph.state import AgentState
from app.domain.graph.tools import GENERIC_TOOLS
from app.domain.personas import (
    CAT_ID,
    DEBATE_COUNSELOR_ID,
    DEBATE_CRITIC_ID,
    DEBATE_OBSERVER_ID,
    DEBATE_STORYTELLER_ID,
    GECKO_ID,
    PERSONA_REGISTRY,
    SEA_SLUG_ID,
    SHOEBILL_ID,
    normalize_persona,
)

logger = logging.getLogger(__name__)


def extract_message_text(content: Any) -> str:
    """Extract plain text even if content is returned as a list of blocks/dicts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "".join(parts)
    return str(content)


class ResilientLLM:
    """Wrapper that tries candidates in sequence (Gemini Primary -> Gemini Secondary -> Light -> Gemma -> OpenAI -> Mock)."""

    def __init__(
        self,
        candidate_llms: Optional[List[Any]] = None,
        bound_tools: Optional[List[Any]] = None,
        # Backward compatibility arguments
        primary_llm: Optional[Any] = None,
        secondary_llm: Optional[Any] = None,
    ):
        if candidate_llms is not None:
            self.candidate_llms = candidate_llms
        else:
            self.candidate_llms = [llm for llm in (primary_llm, secondary_llm) if llm is not None]
        self.bound_tools = bound_tools or []

    @property
    def primary_llm(self) -> Optional[Any]:
        return self.candidate_llms[0] if self.candidate_llms else None

    @property
    def secondary_llm(self) -> Optional[Any]:
        return self.candidate_llms[1] if len(self.candidate_llms) > 1 else None

    def bind_tools(self, tools: List[Any]) -> "ResilientLLM":
        new_candidates = []
        for llm in self.candidate_llms:
            try:
                new_candidates.append(llm.bind_tools(tools))
            except Exception:
                new_candidates.append(llm)
        return ResilientLLM(
            candidate_llms=new_candidates,
            bound_tools=tools,
        )

    async def ainvoke(
        self,
        messages: List[BaseMessage],
        config: Optional[RunnableConfig] = None,
    ) -> AIMessage:
        # Fast deterministic mock in test environment to avoid slow network rate-limits
        if getattr(settings, "app_env", "") == "test":
            return self._generate_mock_response(messages)

        for idx, candidate in enumerate(self.candidate_llms):
            try:
                res = await candidate.ainvoke(messages, config=config)
                if hasattr(res, "content"):
                    res.content = extract_message_text(res.content)
                return res
            except Exception as e:
                logger.warning("LLM Candidate #%d failed (%s). Trying next candidate.", idx + 1, e)

        return self._generate_mock_response(messages)

    def _generate_mock_response(self, messages: List[BaseMessage]) -> AIMessage:
        last_msg = str(messages[-1].content) if messages else ""
        system_text = "".join(str(m.content) for m in messages if isinstance(m, SystemMessage))

        # Check if bound tools contain routing tools and books are not yet curated in system_prompt
        has_curated_books = "검증한 국립중앙도서관 실존 도서 목록" in system_text
        bound_tool_names = [getattr(t, "name", "") for t in self.bound_tools]

        # 1. Natural debate conclude trigger via tool call
        if (
            "trigger_debate_conclude" in bound_tool_names
            and not has_curated_books
            and any(
                w in last_msg for w in ["마무리", "종료", "끝", "여기까지", "수고하셨", "그만할래"]
            )
        ):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "trigger_debate_conclude",
                        "args": {"reason": "사용자가 토론 마무리 의사를 표현함"},
                        "id": "mock_call_conclude_1",
                    }
                ],
            )

        # 2. Book curation request trigger via tool call
        if (
            "request_book_curation" in bound_tool_names
            and not has_curated_books
            and any(
                w in last_msg
                for w in [
                    "추천",
                    "골라줘",
                    "권해줘",
                    "어떤 책",
                    "읽을만한",
                    "책 찾아",
                    "뭘 읽",
                    "무슨 책",
                    "등록",
                    "결과",
                    "보여줘",
                    "신간",
                ]
            )
        ):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_book_curation",
                        "args": {"query": last_msg},
                        "id": "mock_call_curation_1",
                    }
                ],
            )

        if "서재" in last_msg or "책장" in last_msg:
            return AIMessage(
                content="독자님의 서재를 확인해보니 흥미로운 책들이 가득하네요. 어떤 책에 대해 이야기해볼까요?"
            )
        if "스크랩" in last_msg or "기억" in last_msg:
            return AIMessage(
                content="서재에 남겨두신 스크랩 구절들을 살펴보았습니다. 삶의 고요한 순간을 기록해두셨군요."
            )
        if "추천" in last_msg:
            return AIMessage(content="요청하신 취향에 어울리는 책들을 서재에서 엄선해보았습니다.")
        if "토론" in last_msg or "어떻게 생각해" in last_msg:
            return AIMessage(
                content="그 쟁점은 매우 흥미롭습니다. 텍스트 이면에 숨겨진 다양한 층위를 함께 짚어봅시다."
            )
        return AIMessage(
            content="책과 함께하는 시간은 언제나 마음에 잔잔한 파동을 남깁니다. 어떤 이야기를 나누고 싶으신가요?"
        )


def _sanitize_persona_output(text: str, curated_books: Optional[List[Dict[str, Any]]]) -> str:
    """Sanitize persona output at code level to strictly prevent fake card fabrication.

    1. If curated_books is empty/absent:
       - Strip all fake card markers ('📖', '등록 ➔', '### 📖', '💡 추천 이유', etc.)
         so frontend will NEVER falsely render a book registration card.
    2. If curated_books exists:
       - Ensure only verified book titles in curated_books appear under '### 📖' headings.
    """
    if not text:
        return text

    if not curated_books:
        # Strip standalone fake card lines and markers
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Strip lines that try to mimic card components
            if stripped.startswith("### 📖"):
                continue
            if stripped == "📖":
                continue
            if "등록 ➔" in stripped or "등록➔" in stripped:
                continue
            if (
                stripped.startswith("💡 추천 이유")
                or stripped.startswith("🏷️ 장르")
                or stripped.startswith("👤 저자")
                or stripped.startswith("사유:")
            ):
                continue
            cleaned_lines.append(line)
        cleaned_text = "\n".join(cleaned_lines)
        # Remove leftover isolated book emojis
        cleaned_text = re.sub(r"(?<![A-Za-z0-9가-힣])📖(?![A-Za-z0-9가-힣])", "", cleaned_text)
        return cleaned_text.strip()

    # When curated_books exist, clean up any fabricated book headings not in curated_books
    valid_titles = {
        re.sub(r"[\s《》〈〉「」『』\"']", "", str(b.get("title", ""))) for b in curated_books
    }
    lines = text.split("\n")
    curated_lines = []
    for line in lines:
        match = re.match(r"^###\s*📖\s*(.+)$", line.strip())
        if match:
            heading_title = re.sub(r"[\s《》〈〉「」『』\"']", "", match.group(1))
            # Keep heading only if it matches one of the curated books
            if any(vt in heading_title or heading_title in vt for vt in valid_titles if vt):
                curated_lines.append(line)
            else:
                logger.warning("Sanitizer removed fabricated book heading: %s", match.group(1))
                continue
        else:
            curated_lines.append(line)

    return "\n".join(curated_lines).strip()


def _is_delayed_curation_promise(text: str) -> bool:
    """Check if the assistant's response ends with an empty promise to curate later."""
    if not text:
        return False
    promise_markers = [
        "골라올게",
        "골라올마",
        "골라오겠",
        "찾아올게",
        "찾아오겠",
        "부탁해 볼게",
        "부탁해볼게",
        "잠시만 기다려",
        "잠시 기다려",
        "잠깐만 기다려",
    ]
    return any(marker in text for marker in promise_markers)


def _get_llm(tools: Optional[List[Any]] = None) -> ResilientLLM:
    """Obtain LLM instance bound with tools (Gemini 3.5 Primary -> Gemini 3.5 Secondary Key -> Gemini 3.1 Light -> Gemma Emergency -> OpenAI -> Mock)."""
    candidates: List[Any] = []
    gemini_key = settings.gemini_api_key.strip()
    gemini_fallback_key = getattr(settings, "gemini_fallback_api_key", "").strip()
    openai_key = settings.openai_api_key.strip()

    # 1. Primary: Google Gemini 3.5 Flash Lite with Primary Key (max_retries=0: 즉시 다음 후보로 토스)
    if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm1: Any = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=gemini_key,
                max_retries=0,
            )
            if tools:
                llm1 = llm1.bind_tools(tools)
            candidates.append(llm1)
        except Exception as e:
            logger.warning("Failed to initialize primary Gemini LLM (%s).", e)

    # 2. Secondary: Google Gemini 3.5 Flash Lite with Fallback Key (팀원 키로 3.5 재시도)
    if (
        gemini_fallback_key
        and not gemini_fallback_key.startswith("your_")
        and len(gemini_fallback_key) > 10
    ):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm2: Any = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=gemini_fallback_key,
                max_retries=0,
            )
            if tools:
                llm2 = llm2.bind_tools(tools)
            candidates.append(llm2)
        except Exception as e:
            logger.warning("Failed to initialize fallback Gemini LLM (%s).", e)

    # 3. Tertiary: Google Gemini 3.1 Flash Lite with Primary Key (안정적인 경량 모델)
    light_model = getattr(settings, "gemini_light_model", "gemini-3.1-flash-lite")
    if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm3: Any = ChatGoogleGenerativeAI(
                model=light_model,
                google_api_key=gemini_key,
                max_retries=0,
            )
            if tools:
                llm3 = llm3.bind_tools(tools)
            candidates.append(llm3)
        except Exception as e:
            logger.warning("Failed to initialize primary light Gemini LLM (%s).", e)

    # 4. Quaternary: Google Gemini 3.1 Flash Lite with Fallback Key (팀원 키로 3.1)
    if (
        gemini_fallback_key
        and not gemini_fallback_key.startswith("your_")
        and len(gemini_fallback_key) > 10
    ):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm4: Any = ChatGoogleGenerativeAI(
                model=light_model,
                google_api_key=gemini_fallback_key,
                max_retries=0,
            )
            if tools:
                llm4 = llm4.bind_tools(tools)
            candidates.append(llm4)
        except Exception as e:
            logger.warning("Failed to initialize fallback light Gemini LLM (%s).", e)

    # 5. Emergency: Gemma 4 31B (안전망)
    emergency_model = getattr(settings, "gemma_emergency_model", "gemma-4-31b-it")
    emergency_key = gemini_key or gemini_fallback_key
    if emergency_key and not emergency_key.startswith("your_") and len(emergency_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm5: Any = ChatGoogleGenerativeAI(
                model=emergency_model,
                google_api_key=emergency_key,
                temperature=0.7,
                max_retries=0,
            )
            if tools:
                llm5 = llm5.bind_tools(tools)
            candidates.append(llm5)
        except Exception as e:
            logger.warning("Failed to initialize emergency Gemma LLM (%s).", e)

    # 5. Fallback: OpenAI gpt-4o-mini
    if openai_key and not openai_key.startswith("your_") and len(openai_key) > 10:
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            openai_llm: Any = ChatOpenAI(
                model=settings.openai_model,
                api_key=SecretStr(openai_key),
                temperature=0.7,
            )
            if tools:
                openai_llm = openai_llm.bind_tools(tools)
            candidates.append(openai_llm)
        except Exception as e:
            logger.warning("Failed to initialize OpenAI LLM (%s).", e)

    return ResilientLLM(candidate_llms=candidates, bound_tools=tools)


def _extract_debate_topic(messages: List[BaseMessage]) -> str:
    """Extract debate topic or mentioned book titles from conversation history."""
    book_candidates: List[str] = []
    for msg in reversed(messages):
        text = str(getattr(msg, "content", ""))
        matches = re.findall(r"[《<「『](.*?)[》>」』]", text)
        for m in matches:
            cleaned = m.strip()
            if cleaned and cleaned not in book_candidates:
                book_candidates.append(cleaned)

    if book_candidates:
        return f"도서 '{book_candidates[0]}'와 관련된 심화 사유 및 토론 확장"

    recent_user_texts: List[str] = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            txt = str(msg.content).strip()
            if txt and txt not in ["토론 마무리", "마무리", "종료", "끝", "토론 끝"]:
                recent_user_texts.append(txt)
            if len(recent_user_texts) >= 2:
                break

    if recent_user_texts:
        return f"독서 토론 주제: {' / '.join(reversed(recent_user_texts))}"

    return "독서 토론의 화두를 확장해 줄 깊이 있는 인문/문학 도서"


def extract_debate_book_title(messages: List[BaseMessage]) -> str:
    """Extract the primary book title discussed in the conversation history."""
    for msg in reversed(messages):
        text = str(getattr(msg, "content", ""))
        matches = re.findall(r"[《<「『](.*?)[》>」』]", text)
        for m in matches:
            cleaned = m.strip()
            if cleaned:
                return cleaned
    return "독서 토론"


def _extract_debate_summary(ai_content: str) -> Optional[str]:
    """Extract a concise debate summary from the concluding response text."""
    if not ai_content:
        return None

    summary_markers = [
        r"(?:\[토론 요약\]|【토론 요약】|오늘의 토론 요약|토론 요약:?)(.*?)(?=(?:\[|【|■|★|🏛️|🌱|🔍|추천 도서|다음 책|\Z))",
        r"(?:■ 한 줄 총평|한 줄 총평:?)(.*?)(?=(?:■|★|◆|🏛️|🌱|🔍|\Z))",
    ]
    for pattern in summary_markers:
        match = re.search(pattern, ai_content, flags=re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 10:
                return extracted

    paragraphs = [p.strip() for p in ai_content.split("\n\n") if p.strip()]
    if paragraphs:
        first_p = re.sub(r"^#+\s*", "", paragraphs[0]).strip()
        return first_p[:300]

    return ai_content[:200]


async def _run_persona_node(
    state: AgentState,
    persona_id: str,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """Universal runner for any of the 8 persona nodes with custom librarian name support."""
    canonical_persona_id = normalize_persona(persona_id)
    logger.info("Executing persona node: %s (canonical: %s)", persona_id, canonical_persona_id)
    persona_meta = PERSONA_REGISTRY.get(canonical_persona_id, PERSONA_REGISTRY[CAT_ID])

    # Determine if this is a debate persona
    is_debate = canonical_persona_id.startswith("DEBATE_")

    # For debate personas: dynamically choose opening vs turn prompt based on human message count
    if is_debate:
        all_messages = state.get("messages", [])
        human_msg_count = sum(1 for m in all_messages if isinstance(m, HumanMessage))
        if human_msg_count <= 1:
            # First user message → use opening prompt with fixed format
            system_prompt = persona_meta.get("opening_system_prompt", persona_meta["system_prompt"])
        else:
            # Subsequent turns → use turn prompt (no fixed format, mirroring + open question)
            system_prompt = persona_meta.get("turn_system_prompt", persona_meta["system_prompt"])
        logger.info(
            "Debate persona %s: human_msg_count=%d, using %s prompt",
            persona_id,
            human_msg_count,
            "opening" if human_msg_count <= 1 else "turn",
        )
    else:
        system_prompt = persona_meta["system_prompt"]

    # Inject user-defined custom librarian name if provided (ONLY for librarian mode, NEVER for debate mode)
    custom_name = state.get("librarian_name")
    if custom_name and not is_debate:
        system_prompt += (
            f"\n\n[호출 명칭]: 사용자가 당신에게 붙여준 고유 이름은 '{custom_name}'입니다. "
            "본인을 지칭하거나 인사할 때 기본 이름 대신 이 이름을 친근하게 사용하십시오."
        )

    # Inject context summary from previous persona if handoff occurred
    context_summary = state.get("context_summary")
    if context_summary:
        system_prompt += f"\n\n[이전 대화 핵심 팩트 요약 (어조 제외)]\n{context_summary}"

    # Inject real-time weather context if available — ONLY for librarian mode, NOT debate mode
    weather_context = state.get("weather_context")
    if weather_context and not is_debate:
        system_prompt += (
            f"\n\n[날씨 및 위치 환경 정보]\n{weather_context}\n"
            "지침:\n"
            "- '[위치 권한 허용됨]' 상태인 경우: 사용자가 위치 권한을 승인하여 실제 현재 위치의 날씨가 전달되었습니다. "
            "절대로 '위치 권한이 없다'고 말하지 마시고, 위 실시간 날씨(기온, 날씨 상태)를 사실 그대로 따뜻하고 자연스럽게 대화에 녹여내세요.\n"
            "- '[위치 권한 미허용 상태]'인 경우: 날씨를 아는 체 지어내지 마시고, '위치 권한이 없어 정확한 동네 날씨는 알 수 없지만, 서울 기준으로...' "
            "또는 '계절의 문맥'으로 정직하고 자연스럽게 언급해야 합니다."
        )

    # Inject debate target book factual grounding if in debate mode
    debate_book = state.get("debate_book_info")
    topic = state.get("topic")

    if is_debate and debate_book:
        b_title = debate_book.get("title", "")
        b_author = debate_book.get("author", "")
        b_publisher = debate_book.get("publisher", "")
        b_desc = debate_book.get("description", "")
        system_prompt += (
            f"\n\n[📖 토론 대상 도서 팩트 정보 (환각 및 내용 날조 엄격 금지)]\n"
            f"- 도서명: 《{b_title}》\n"
            f"- 저자: {b_author}\n"
            f"- 출판사: {b_publisher}\n"
            f"- 도서 개요/줄거리: {b_desc}\n\n"
            "지침: 당신은 위 도서의 실제 내용과 서지 정보에 엄격히 입각하여 깊이 있는 토론과 비평을 나누어야 합니다. "
            "위의 실제 줄거리와 설정을 벗어나 책에 나오지 않는 가짜 인물이나 사건을 자의적으로 날조(환각)하지 마십시오. "
            "모르는 세부 내용은 독자에게 책의 해당 구절을 물어보며 겸손하고 지적인 태도로 사유를 심화하십시오."
        )
    if is_debate and topic:
        system_prompt += f"\n\n[💡 오늘의 토론 화두/논제]: {topic}"

    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            last_user_msg = str(msg.content)
            break

    # 1. Conclude Intent Check (UI explicit action='conclude', natural concluding phrases, or already concluded)
    action = state.get("action") or "chat"
    is_conclude_requested = action == "conclude"
    is_already_concluded = bool(state.get("is_concluded"))

    # Natural conclude phrases in debate mode
    is_natural_conclude = False
    if is_debate and not state.get("curated_books"):
        conclude_keywords = [
            "토론 마무리",
            "토론 종료",
            "토론 끝",
            "여기까지 하고 토론",
            "토론 그만",
            "대화 마무리",
        ]
        is_natural_conclude = any(kw in last_user_msg for kw in conclude_keywords)

    # If conclude is explicitly or naturally requested and books are not yet curated, delegate to curator_node
    if (is_conclude_requested or is_natural_conclude or is_already_concluded) and not state.get(
        "curated_books"
    ):
        logger.info(
            "Conclude action detected for persona %s (explicit=%s, natural=%s). Delegating to curator_node for wrap-up books.",
            persona_id,
            is_conclude_requested,
            is_natural_conclude,
        )
        debate_topic = _extract_debate_topic(state.get("messages", []))
        return {
            "active_persona": persona_id,
            "curator_request": f"토론 마무리 연계 추천: {debate_topic}",
            "is_concluded": True,
        }

    # 1-1. Book Curation Pre-Delegation (Librarian mode: explicit recommendation/registration request)
    # If user asks for book recommendation, registration, or result display and curated_books are not yet loaded,
    # immediately delegate to curator_node to guarantee 100% verified National Library metadata.
    if not is_debate and not state.get("curated_books"):
        recommend_keywords = [
            "추천",
            "골라줘",
            "권해줘",
            "어떤 책",
            "읽을만한",
            "책 찾아",
            "뭘 읽",
            "무슨 책",
            "등록",
            "결과로 보여",
            "결과 보여",
            "신간",
            "최신 도서",
            # 독서 욕구 표현 (읽고 싶다 계열)
            "읽고싶",
            "읽고 싶",
            "읽어보고싶",
            "읽어보고 싶",
            "읽어보려",
            "읽어볼",
            "읽어봐야",
            "읽어봤으면",
            "읽고파",
            # 탐색/추천 요청
            "책 좀",
            "책 알려",
            "뭐 읽",
            "뭐 읽지",
            "뭐 읽을",
            "재밌는 책",
            "좋은 책",
            "재밌는거",
            "흥미로운 책",
            "괜찮은 책",
        ]
        has_recommend_intent = any(k in last_user_msg for k in recommend_keywords)
        # Also check if user mentions specific book in brackets (e.g. 《프로젝트 헤일메리》 추천해줘)
        has_bracket_book = bool(re.search(r"[《〈「『](.*?)[》〉」』]", last_user_msg))
        if has_recommend_intent or has_bracket_book:
            logger.info(
                "Recommendation intent detected in user message for persona %s. Delegating to curator_node.",
                persona_id,
            )
            return {
                "active_persona": persona_id,
                "curator_request": last_user_msg,
                "target_unresolved": None,
            }

    # Inject verified curated books if returned from curator_node
    curated_books = state.get("curated_books")
    if curated_books:
        books_desc = "\n".join(
            [
                f"- 《{b['title']}》 ({b.get('author', '저자')}, {b.get('publisher', '출판사')}) / ISBN: {b.get('isbn', '')}\n"
                f"  큐레이션 핵심 사유: {b.get('reason') or b.get('description', '')}"
                for b in curated_books
            ]
        )
        system_prompt += (
            "\n\n[도서 큐레이터가 엄선 및 검증한 국립중앙도서관 실존 도서 목록]\n"
            f"{books_desc}\n\n"
            "지침: 위의 검증된 실존 도서를 당신 고유의 어조와 캐릭터 감성으로 독자에게 다정하게 소개해 주십시오.\n"
            "- [도서 추천 시 필수 출력 순서 및 구성 원칙 - 포맷 하이재킹 및 자판기식 출력 엄격 금지]:\n"
            "  * 절대로 인사나 공감 없이 책 제목이나 헤딩(`### 📖`)부터 성급하게 먼저 던지지 마십시오. 반드시 아래의 순서를 엄격히 지키십시오.\n"
            "  * 1단계: (상황 공감 및 캐릭터 고유 사색 / 2~3문장)\n"
            "    - 사용자의 현재 감정, 고민, 상황(예: 시험/연수 탈락, 번아웃, 우울, 새로운 시작 등)에 깊이 공감하고, 캐릭터 고유의 시선(예: 블루의 경우 철학적이고 차분한 사색)으로 따뜻한 위로와 사유의 말을 건넵니다. 섹션 헤딩 없이 부드러운 평문으로 시작하십시오.\n"
            "  * 2단계: (도서 추천 및 구체적 처방 사유 / 책 당 1~2문장)\n"
            "    - 추천하는 책이 왜 지금 사용자의 상황과 감정에 도움이 되는지, 책의 핵심 메시지와 철학적/감정적 처방 사유를 대화체로 풀어서 설명하십시오.\n"
            "  * 3단계: (마크다운 헤딩 규격 및 카드 트리거)\n"
            "    - 답변의 하단부에 각 도서별로 반드시 `### 📖 도서명`(`### 📖 {도서명}`) 형식의 마크다운 3단계 헤딩만 별도의 줄에 명시하십시오. (화면에는 이 헤딩 아래에 시스템 추천 도서 카드가 자동으로 예쁘게 렌더링됩니다.)\n"
            "    - 헤딩 아래에는 해당 책에 대한 1문장의 짧은 감상이나 격려를 덧붙일 수 있습니다.\n"
            "  * 4단계: (마무리 응원/작별 멘트 / 1문장)\n"
            "    - 독자의 마음을 보듬는 캐릭터 고유의 따뜻한 마무리 멘트로 마침표를 찍으십시오.\n"
            "- [답변 출력 형식 주의사항]:\n"
            "  * [헤딩 이모지 절대 금지]: 서두 섹션 타이틀(예: `### 📚 누디가 건네는 책`, `### 📚 블루의 서재` 등)이나 추천 도서 헤딩에 `📚` 이모지를 절대로 사용하지 마십시오. `📚`는 사용자의 '내 서재 보유 도서' 전용 이모지이므로, 추천 본문에 사용하면 프론트엔드가 이를 보유 도서로 오인합니다.\n"
            "  * [추천 도서 헤딩 규격]: 추천 도서 헤딩은 오직 `### 📖 {도서명}` 형식만 사용하십시오. (헤딩에 다른 이모지나 부연 수식어를 붙이지 마십시오.)\n"
            "  * 본문에는 `저자: ...`, `사유: ...` 와 같은 딱딱한 메타데이터 목록이나 `---` 구분선, `등록 ➔` 버튼 텍스트를 직접 적지 마십시오. (화면 카드 컴포넌트와 중복되어 시인성을 해칩니다.)\n"
            "- [절대 준수]: 도서의 제목과 저자명(작가)은 위 목록에 적힌 그대로 정확하게 일치시켜 언급해야 합니다. 작가 이름을 임의로 다른 작가(예: 김애란 등)로 바꾸거나 날조하지 마십시오.\n"
            "- [중복 호출 금지]: 도서 검색/추천 도구를 다시 호출하지 마십시오. 이미 큐레이터가 최적의 책을 엄선했으므로, 위 목록의 책들을 독자에게 소개하는 데 집중하십시오.\n"
            "- 존재하지 않는 가짜 책을 임의로 지어내지 마십시오."
        )

    # Inform user if explicitly requested target book could not be verified in library DB
    target_unresolved = state.get("target_unresolved")
    if target_unresolved:
        system_prompt += (
            f"\n\n[⚠️ 지목 도서 미확인 안내]: 사용자가 직접 요청/등록을 원하신 《{target_unresolved}》 도서를 "
            "국립중앙도서관 정식 서지 DB에서 정확히 확인하지 못했습니다. "
            f"답변 서두에 '말씀해주신 《{target_unresolved}》의 정식 서지 정보를 아쉽게도 찾지 못했어요'라는 취지의 다정한 안내를 전한 뒤, "
            "대신 엄선해 드린 위의 추천 도서를 소개하십시오."
        )

    # 2. Inject finale & debate wrap-up instructions if concluding
    is_conclude_active = is_conclude_requested or is_already_concluded
    if is_conclude_active:
        system_prompt += (
            "\n\n[🏁 독서 토론 피날레 및 마무리 총평 지침]\n"
            "사용자가 이번 토론의 마무리를 요청했습니다. 당신은 다음 세 가지 구성을 반드시 포함하여 토론의 대미를 장식해야 합니다:\n"
            "1. [토론 요약]: 오늘 사용자와 깊이 있게 나눈 논제, 쟁점, 그리고 도출된 핵심 통찰을 2~3문장 또는 개조식으로 명확하고 품격 있게 요약하십시오.\n"
            "2. [작별 및 피날레 총평]: 당신 고유의 오마주 캐릭터 어조(평론가의 별점/한줄평, 이야기꾼의 역사적 교훈, 상담사의 마음 돌봄, 관찰가의 행동 시그널 등)를 살려 독자에게 진심 어린 찬사와 마지막 총평을 전하십시오.\n"
            "3. [연계 도서 제안]: 큐레이터가 엄선한 위의 실존 추천 도서를 소개하며, 오늘 나눈 토론의 사유를 이어갈 다음 책으로 자연스럽게 권유하십시오.\n"
            "- [절대 준수]: 이번 발화로 토론이 완전히 마무리되므로, 사용자에게 새로운 질문이나 다음 화두를 던져 대화를 연장하지 말고 감사의 작별 인사로 마침표를 찍으십시오."
        )

    system_prompt += f"\n\n[현재 사용자 식별자: member_id={state.get('member_id')}]"

    # Sanitize messages to avoid dangling tool_calls without tool response messages
    sanitized_messages: List[BaseMessage] = []
    raw_messages = list(state.get("messages", []))
    for i, msg in enumerate(raw_messages):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            # Check if immediately followed by ToolMessage
            has_tool_reply = i + 1 < len(raw_messages) and getattr(
                raw_messages[i + 1], "tool_call_id", None
            )
            if not has_tool_reply:
                # Strip dangling tool_calls to satisfy OpenAI API requirement
                sanitized_messages.append(AIMessage(content=msg.content or ""))
                continue
        sanitized_messages.append(msg)

    prompt_messages = [SystemMessage(content=system_prompt)] + sanitized_messages

    # If books have already been curated, exclude recommendation tools to prevent duplicate LLM/API calls
    active_tools = GENERIC_TOOLS
    if curated_books:
        active_tools = [
            t
            for t in GENERIC_TOOLS
            if getattr(t, "name", "") not in ("search_recent_books", "request_book_curation")
        ]

    llm = _get_llm(tools=active_tools)
    t_llm_start = time.perf_counter()
    response = await llm.ainvoke(prompt_messages, config=config)
    t_llm_ms = (time.perf_counter() - t_llm_start) * 1000
    logger.info(
        "[PROFILE] [Persona Node LLM] %s ainvoke completed in %.2f ms", persona_id, t_llm_ms
    )

    # Check for Agent Tool Calls (trigger_debate_conclude or request_book_curation)
    tool_calls = getattr(response, "tool_calls", None) or []
    for call in tool_calls:
        call_name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
        call_args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
        if not isinstance(call_args, dict):
            call_args = {}

        if call_name == "trigger_debate_conclude":
            logger.info("LLM invoked trigger_debate_conclude. Delegating to curator_node.")
            debate_topic = _extract_debate_topic(state.get("messages", []))
            return {
                "active_persona": persona_id,
                "curator_request": f"토론 마무리 연계 추천: {debate_topic}",
                "is_concluded": True,
            }

        if call_name == "request_book_curation" and not curated_books:
            curation_query = call_args.get("query") or last_user_msg
            logger.info(
                "LLM invoked request_book_curation with query '%s'. Delegating to curator_node.",
                curation_query,
            )
            return {
                "active_persona": persona_id,
                "curator_request": curation_query,
                "target_unresolved": None,
            }

    # Safety Net: If the LLM response contains an empty delay promise without curated books,
    # immediately delegate to curator_node so the user receives verified book cards in turn 1.
    response_text = str(response.content) if response.content else ""
    if not is_debate and not curated_books and _is_delayed_curation_promise(response_text):
        logger.info(
            "Delayed curation promise detected in LLM response for persona %s. Intercepting and delegating to curator_node.",
            persona_id,
        )
        return {
            "active_persona": persona_id,
            "curator_request": last_user_msg,
            "target_unresolved": None,
        }

    # Sanitize persona output to strictly prevent unverified book card UI fabrication
    sanitized_content = _sanitize_persona_output(response_text, curated_books)
    if sanitized_content != response_text:
        response = AIMessage(
            content=sanitized_content, additional_kwargs=getattr(response, "additional_kwargs", {})
        )

    debate_summary: Optional[str] = None
    if is_conclude_active:
        debate_summary = _extract_debate_summary(str(response.content))

    result: Dict[str, Any] = {
        "messages": [response],
        "active_persona": persona_id,
        "switch_suggestion": None,
        "handoff_target": None,
        "is_concluded": is_conclude_active,
        "debate_summary": debate_summary,
        "target_unresolved": None,  # Reset so it doesn't linger into the next turn
    }
    if curated_books:
        result["curated_books"] = curated_books
    if state.get("recommended_history"):
        result["recommended_history"] = state.get("recommended_history")

    return result


# ==============================================================================
# 📚 Librarian Persona Nodes (4: CAT, SHOEBILL, SEA_SLUG, GECKO)
# ==============================================================================
async def cat_node(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Execute Cat persona node (고양이 사서 '블루')."""
    return await _run_persona_node(state, CAT_ID, config=config)


async def shoebill_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Shoebill persona node (넓적부리황새 사서 '슈빌')."""
    return await _run_persona_node(state, SHOEBILL_ID, config=config)


async def sea_slug_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Sea Slug persona node (바다달팽이 사서)."""
    return await _run_persona_node(state, SEA_SLUG_ID, config=config)


async def gecko_node(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Execute Gecko persona node (게코 도마뱀 사서)."""
    return await _run_persona_node(state, GECKO_ID, config=config)


# Aliases for backward compatibility
blue_node = cat_node
russian_blue_node = cat_node
librarian_3_node = sea_slug_node
librarian_4_node = gecko_node


# ==============================================================================
# 🎙️ Debate Persona Nodes (4)
# ==============================================================================
async def debate_critic_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Debate Critic persona node (평론가)."""
    return await _run_persona_node(state, DEBATE_CRITIC_ID, config=config)


async def debate_storyteller_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Debate Storyteller persona node (이야기꾼)."""
    return await _run_persona_node(state, DEBATE_STORYTELLER_ID, config=config)


async def debate_counselor_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Debate Counselor persona node (상담사)."""
    return await _run_persona_node(state, DEBATE_COUNSELOR_ID, config=config)


async def debate_observer_node(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Execute Debate Observer persona node (관찰가)."""
    return await _run_persona_node(state, DEBATE_OBSERVER_ID, config=config)


# ==============================================================================
# 🔄 Summarizer Node & Fact Sanitizer (Persona Contamination Prevention)
# ==============================================================================
async def summarize_conversation_facts(messages: List[BaseMessage]) -> str:
    """Strip persona-specific tone and extract pure factual context from conversation messages.

    Prevents persona and tone contamination across all 8 personas.
    """
    conversation_text = ""
    for msg in messages[-6:]:
        role = "사용자" if isinstance(msg, HumanMessage) else "사서/토론자"
        conversation_text += f"{role}: {msg.content}\n"

    summarizer_prompt = (
        "다음 사서/토론자와 사용자의 대화 기록에서 발화자의 캐릭터 어조(평론가, 강사, 힐링, "
        "심리상담, 행동관찰 등의 말투나 캐릭터 뉘앙스)를 완전히 제거하고, "
        "오직 사용자의 독서 취향, 언급된 책 제목, 스크랩 내용, 논의된 핵심 팩트만 2~3줄의 "
        "객관적인 개조식 문장으로 요약하십시오.\n\n"
        f"대화 내용:\n{conversation_text}"
    )

    llm = _get_llm()
    try:
        summary_response = await llm.ainvoke([HumanMessage(content=summarizer_prompt)])
        fact_summary = str(summary_response.content).strip()
    except Exception as e:
        logger.warning("Summarizer LLM call failed (%s), using structured fallback.", e)
        fact_summary = (
            "- 사용자와 책에 대한 대화를 진행 중이었음.\n- 특정 취향과 질문에 대한 관심 표명."
        )

    return fact_summary


async def summarizer_node(state: AgentState) -> Dict[str, Any]:
    """Strip persona-specific tone and extract pure factual context during handoff.

    Prevents persona contamination across all 8 personas.
    """
    target_persona = state.get("handoff_target") or CAT_ID
    logger.info("Executing summarizer_node: handing off to %s", target_persona)

    fact_summary = await summarize_conversation_facts(state.get("messages", []))
    logger.info("Sanitized fact summary: %s", fact_summary)

    return {
        "active_persona": target_persona,
        "handoff_target": None,
        "context_summary": fact_summary,
    }
