"""Node implementations for LangGraph: 8 Personas and Summarizer node."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.domain.graph.state import AgentState, SwitchSuggestion
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
)

logger = logging.getLogger(__name__)


class ResilientLLM:
    """Wraps LLM execution with automatic fallback to mock responses on API failure."""

    def __init__(self, primary_llm=None, bound_tools=None):
        self.primary_llm = primary_llm
        self.bound_tools = bound_tools or []

    def bind_tools(self, tools):
        new_primary = self.primary_llm.bind_tools(tools) if self.primary_llm else None
        return ResilientLLM(primary_llm=new_primary, bound_tools=tools)

    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        if self.primary_llm:
            try:
                return await self.primary_llm.ainvoke(messages)
            except Exception as e:
                logger.warning(
                    "Primary Gemini LLM call failed (%s). Falling back to mock response.", e
                )

        last_msg = str(messages[-1].content) if messages else ""
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


def _get_llm(tools: Optional[List[Any]] = None) -> ResilientLLM:
    """Obtain LLM instance bound with tools or mock fallback."""
    key = settings.gemini_api_key.strip()
    primary: Any = None

    if key and not key.startswith("your_") and len(key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            primary = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=key,
                temperature=0.7,
            )
            if tools:
                primary = primary.bind_tools(tools)
        except Exception as e:
            logger.warning("Failed to initialize Gemini LLM (%s), using mock fallback.", e)

    return ResilientLLM(primary_llm=primary, bound_tools=tools)


def _detect_switch_intent(
    last_user_message: str,
    ai_content: str,
    current_persona: str,
) -> Tuple[Optional[SwitchSuggestion], Optional[str]]:
    """Detect if handoff suggestion or immediate handoff should be triggered among 8 personas."""
    text = (last_user_message + " " + ai_content).lower()

    # Keyword to Persona mapping for intentional switching
    switch_map = {
        "슈빌": SHOEBILL_ID,
        "1타": SHOEBILL_ID,
        "블루": CAT_ID,
        "고양이": CAT_ID,
        "달팽이": SEA_SLUG_ID,
        "바다달팽이": SEA_SLUG_ID,
        "심해": SEA_SLUG_ID,
        "게코": GECKO_ID,
        "도마뱀": GECKO_ID,
        "평론가": DEBATE_CRITIC_ID,
        "이동진": DEBATE_CRITIC_ID,
        "이야기꾼": DEBATE_STORYTELLER_ID,
        "설민석": DEBATE_STORYTELLER_ID,
        "상담사": DEBATE_COUNSELOR_ID,
        "오은영": DEBATE_COUNSELOR_ID,
        "관찰가": DEBATE_OBSERVER_ID,
        "강형욱": DEBATE_OBSERVER_ID,
    }

    explicit_change = "바꿔" in text or "변경" in text or "전환" in text

    for keyword, target_persona_id in switch_map.items():
        if target_persona_id != current_persona and keyword in text:
            target_meta = PERSONA_REGISTRY.get(target_persona_id, {})
            display_name = target_meta.get("display_name", target_persona_id)
            suggestion: SwitchSuggestion = {
                "suggested_persona": target_persona_id,
                "display_name": display_name,
                "reason": f"새로운 시선으로 대화를 이어갈 수 있도록 '{display_name}' 파트너로의 전환을 제안합니다.",
            }
            target = target_persona_id if explicit_change else None
            return suggestion, target

    return None, None


async def _run_persona_node(state: AgentState, persona_id: str) -> Dict[str, Any]:
    """Universal runner for any of the 8 persona nodes with custom librarian name support."""
    logger.info("Executing persona node: %s", persona_id)
    persona_meta = PERSONA_REGISTRY.get(persona_id, PERSONA_REGISTRY[CAT_ID])
    system_prompt = persona_meta["system_prompt"]

    # Inject user-defined custom librarian name if provided
    custom_name = state.get("librarian_name")
    if custom_name:
        system_prompt += (
            f"\n\n[호출 명칭]: 사용자가 당신에게 붙여준 고유 이름은 '{custom_name}'입니다. "
            "본인을 지칭하거나 인사할 때 기본 이름 대신 이 이름을 친근하게 사용하십시오."
        )

    # Inject context summary from previous persona if handoff occurred
    context_summary = state.get("context_summary")
    if context_summary:
        system_prompt += f"\n\n[이전 대화 핵심 팩트 요약 (어조 제외)]\n{context_summary}"

    # Inject real-time weather context if available
    weather_context = state.get("weather_context")
    if weather_context:
        system_prompt += (
            f"\n\n[날씨 및 위치 환경 정보]\n{weather_context}\n"
            "지침: 사용자의 위치 권한이 미허용된 상태라면 날씨를 아는 체 지어내지 마십시오. "
            "날씨를 언급해야 할 때는 '위치 권한이 없어 정확한 동네 날씨는 알 수 없지만, 서울 기준으로...' "
            "또는 '계절의 문맥'으로 정직하고 자연스럽게 언급해야 합니다."
        )

    # Inject verified curated books if returned from curator_node
    curated_books = state.get("curated_books")
    if curated_books:
        books_desc = "\n".join(
            [
                f"- 《{b['title']}》 ({b.get('author', '저자')}, {b.get('publisher', '출판사')}) / ISBN: {b.get('isbn', '')}\n"
                f"  사유: {b.get('reason') or b.get('description', '')}"
                for b in curated_books
            ]
        )
        system_prompt += (
            "\n\n[도서 큐레이터가 엄선 및 검증한 실존 추천 도서 목록]\n"
            f"{books_desc}\n\n"
            "지침: 위의 검증된 도서들을 당신 고유의 어조와 캐릭터 감성으로 독자에게 다정하게 소개해 주십시오. "
            "존재하지 않는 가짜 책을 임의로 지어내지 마십시오."
        )

    system_prompt += f"\n\n[현재 사용자 식별자: member_id={state.get('member_id')}]"

    prompt_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

    llm = _get_llm(tools=GENERIC_TOOLS)
    response = await llm.ainvoke(prompt_messages)

    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_msg = str(msg.content)
            break

    # Check if recommendation/curation intent is present and not yet curated
    curator_request = None
    if not state.get("curated_books"):
        recom_keywords = ["추천", "골라줘", "권해줘", "어떤 책", "읽을만한", "책 찾아"]
        if any(kw in last_user_msg for kw in recom_keywords):
            curator_request = last_user_msg

    suggestion, target = _detect_switch_intent(
        last_user_msg,
        str(response.content),
        persona_id,
    )

    result_payload: Dict[str, Any] = {
        "messages": [response],
        "active_persona": persona_id,
        "switch_suggestion": suggestion,
        "handoff_target": target,
    }
    if curator_request:
        result_payload["curator_request"] = curator_request

    return result_payload


# ==============================================================================
# 📚 Librarian Persona Nodes (4: CAT, SHOEBILL, SEA_SLUG, GECKO)
# ==============================================================================
async def cat_node(state: AgentState) -> Dict[str, Any]:
    """Execute Cat persona node (고양이 사서 '블루')."""
    return await _run_persona_node(state, CAT_ID)


async def shoebill_node(state: AgentState) -> Dict[str, Any]:
    """Execute Shoebill persona node (넓적부리황새 사서 '슈빌')."""
    return await _run_persona_node(state, SHOEBILL_ID)


async def sea_slug_node(state: AgentState) -> Dict[str, Any]:
    """Execute Sea Slug persona node (바다달팽이 사서)."""
    return await _run_persona_node(state, SEA_SLUG_ID)


async def gecko_node(state: AgentState) -> Dict[str, Any]:
    """Execute Gecko persona node (게코 도마뱀 사서)."""
    return await _run_persona_node(state, GECKO_ID)


# Aliases for backward compatibility
blue_node = cat_node
russian_blue_node = cat_node
librarian_3_node = sea_slug_node
librarian_4_node = gecko_node


# ==============================================================================
# 🎙️ Debate Persona Nodes (4)
# ==============================================================================
async def debate_critic_node(state: AgentState) -> Dict[str, Any]:
    """Execute Debate Critic persona node (평론가)."""
    return await _run_persona_node(state, DEBATE_CRITIC_ID)


async def debate_storyteller_node(state: AgentState) -> Dict[str, Any]:
    """Execute Debate Storyteller persona node (이야기꾼)."""
    return await _run_persona_node(state, DEBATE_STORYTELLER_ID)


async def debate_counselor_node(state: AgentState) -> Dict[str, Any]:
    """Execute Debate Counselor persona node (상담사)."""
    return await _run_persona_node(state, DEBATE_COUNSELOR_ID)


async def debate_observer_node(state: AgentState) -> Dict[str, Any]:
    """Execute Debate Observer persona node (관찰가)."""
    return await _run_persona_node(state, DEBATE_OBSERVER_ID)


# ==============================================================================
# 🔄 Summarizer Node (Persona Contamination Prevention)
# ==============================================================================
async def summarizer_node(state: AgentState) -> Dict[str, Any]:
    """Strip persona-specific tone and extract pure factual context during handoff.

    Prevents persona contamination across all 8 personas.
    """
    target_persona = state.get("handoff_target") or CAT_ID
    logger.info("Executing summarizer_node: handing off to %s", target_persona)

    conversation_text = ""
    for msg in state["messages"][-6:]:
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

    logger.info("Sanitized fact summary: %s", fact_summary)

    return {
        "active_persona": target_persona,
        "handoff_target": None,
        "context_summary": fact_summary,
    }
