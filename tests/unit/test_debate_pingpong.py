"""Unit tests for Debate Persona 1:1 ping-pong interaction, fact-grounded counter-arguments, and isolation (Phase 66)."""

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.domain.graph.nodes import _run_persona_node
from app.domain.personas import (
    DEBATE_COUNSELOR_ID,
    DEBATE_CRITIC_ID,
    DEBATE_OBSERVER_ID,
    DEBATE_STORYTELLER_ID,
    PERSONA_REGISTRY,
)
from app.domain.personas.debate_common import FINALE_MARKER

DEBATE_PERSONA_IDS = [
    DEBATE_CRITIC_ID,
    DEBATE_STORYTELLER_ID,
    DEBATE_COUNSELOR_ID,
    DEBATE_OBSERVER_ID,
]


def test_common_debate_turn_rules_in_all_debate_personas():
    """Verify that all 4 debate personas include COMMON_DEBATE_TURN_RULES with 1:1 focus and fact grounding."""
    for p_id in DEBATE_PERSONA_IDS:
        meta = PERSONA_REGISTRY[p_id]
        turn_prompt = meta["turn_system_prompt"]

        # 1. Constructive counter-argument and mutual respect
        assert "논리의 대립과 건설적 반론" in turn_prompt, (
            f"{p_id} missing counter-argument in turn prompt"
        )
        assert "단순한 동조나 무조건적 찬사" in turn_prompt, (
            f"{p_id} missing praise discouragement in turn prompt"
        )
        assert "무조건 반대만 하는 것도 토론이 아니다" in turn_prompt, (
            f"{p_id} missing fair debate rule"
        )
        assert "타당한 근거가 있다면 이를 명확히 인정" in turn_prompt, (
            f"{p_id} missing ground acceptance rule"
        )

        # 2. Starting sentence variety (Anti-parrot)
        assert "시작 문구 다양성" in turn_prompt, f"{p_id} missing starting variety rule"
        assert "연속 두 턴에서 같은 어휘나 같은 형태의 시작 문장을 쓰지 않는다" in turn_prompt, (
            f"{p_id} missing anti-repetition start rule"
        )

        # 3. Strict factual grounding & Information limitation acknowledgement
        assert "도서 정보 한계와 팩트 그라운딩 엄수" in turn_prompt, (
            f"{p_id} missing fact grounding rule"
        )
        assert "텍스트에 없는 허위 장면" in turn_prompt, f"{p_id} missing no-hallucination rule"
        assert "책의 구체적인 장면이나 세부 맥락은 단정하기 어렵다" in turn_prompt, (
            f"{p_id} missing info limitation rule"
        )

        # 4. Independent 1:1 focus (No third-party partner fabrication or baton touch)
        assert "독립적 1:1 토론 몰입" in turn_prompt, f"{p_id} missing 1:1 focus rule"
        assert (
            "존재하지 않는 다른 파트너나 가상의 제3자를 지어내어 언급하지 않는다" in turn_prompt
        ), f"{p_id} missing anti-partner-leak rule"
        assert "바통 터치" not in turn_prompt, f"{p_id} should not contain baton touch"

        # 5. Ping-pong question interaction & conclude turn suppression
        assert "꼬리물기 질문" in turn_prompt, f"{p_id} missing ping-pong question rule"
        assert "마무리 턴 예외 엄격 준수" in turn_prompt, (
            f"{p_id} missing conclude turn question suppression"
        )


def test_each_debate_persona_turn_specific_pingpong_instructions():
    """Verify each debate persona has distinct tone-specific counter-argument and fact-grounded instructions."""
    # Critic (이동진 오마주)
    critic_turn = PERSONA_REGISTRY[DEBATE_CRITIC_ID]["turn_system_prompt"]
    assert "미학적 결" in critic_turn
    assert "건설적 반론과 쟁점 좁히기" in critic_turn
    assert "없는 허위 장면이나 거짓 설정을 지어내어 반론하지 않는다" in critic_turn
    assert "바통 터치" not in critic_turn

    # Storyteller (설민석 오마주)
    storyteller_turn = PERSONA_REGISTRY[DEBATE_STORYTELLER_ID]["turn_system_prompt"]
    assert "시대적 딜레마" in storyteller_turn
    assert "역사의 아이러니" in storyteller_turn
    assert "가짜 사건이나 거짓 역사를 날조하지 않는다" in storyteller_turn
    assert "바통 터치" not in storyteller_turn

    # Counselor (오은영 오마주)
    counselor_turn = PERSONA_REGISTRY[DEBATE_COUNSELOR_ID]["turn_system_prompt"]
    assert "심리적 이면 탐색" in counselor_turn
    assert "취약성과 방어기제" in counselor_turn
    assert "가공의 사연이나 날조된 인물 설정을 지어내지 않는다" in counselor_turn
    assert "바통 터치" not in counselor_turn

    # Observer (강형욱 오마주)
    observer_turn = PERSONA_REGISTRY[DEBATE_OBSERVER_ID]["turn_system_prompt"]
    assert "환경적 본능 직시" in observer_turn
    assert "생존 본능" in observer_turn
    assert "거짓 환경이나 가짜 설정을 날조하지 않는다" in observer_turn
    assert "바통 터치" not in observer_turn


@pytest.mark.asyncio
async def test_debate_mode_librarian_recommendation_and_genre_isolation():
    """Verify that in DEBATE mode, recommendation intent keywords and brackets do NOT trigger curator pre-delegation."""
    mock_llm_response = AIMessage(
        content="토론을 이어갑니다. 그 장면에 대한 독자님의 생각은 어떠신가요?"
    )

    with patch("app.domain.graph.nodes._get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_llm_response
        mock_get_llm.return_value = mock_llm

        state: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="《인간실격》 관련해서 책 추천해줘. 읽을만한 다른 책 골라줘."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "curated_books": None,
            "curator_attempted": False,
        }

        # Run persona node
        result = await _run_persona_node(state, DEBATE_CRITIC_ID)

        # In DEBATE mode, must NOT pre-delegate to curator_request
        assert "curator_request" not in result or result.get("curator_request") is None
        # It must proceed to LLM invocation directly
        assert mock_llm.ainvoke.called


@pytest.mark.asyncio
async def test_debate_mode_librarian_name_and_weather_isolation():
    """Verify that librarian custom name and weather context are strictly isolated from DEBATE prompts."""
    captured_prompts = []

    def mock_get_llm(**kwargs):
        mock_llm = AsyncMock()

        async def _ainvoke(prompt_messages, config=None):
            captured_prompts.extend(prompt_messages)
            return AIMessage(content="토론 답변입니다.")

        mock_llm.ainvoke = _ainvoke
        return mock_llm

    with patch("app.domain.graph.nodes._get_llm", side_effect=mock_get_llm):
        state: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="안녕하세요, 토론을 시작해 볼까요?"),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "librarian_name": "내소중한사서냥이",
            "weather_context": "현재 기온은 18도이며 비가 내리고 있습니다.",
            "context_summary": "이전 사서와의 대화 요약입니다.",
        }

        await _run_persona_node(state, DEBATE_CRITIC_ID)

        system_msg = next((m.content for m in captured_prompts if getattr(m, "content", "")), "")

        # Strict isolation: custom librarian name, weather, and context summary must NEVER enter debate prompt
        assert "내소중한사서냥이" not in system_msg
        assert "[호출 명칭]" not in system_msg
        assert "현재 기온은 18도이며" not in system_msg
        assert "[날씨 및 위치 환경 정보]" not in system_msg
        assert "이전 사서와의 대화 요약입니다." not in system_msg
        assert "[이전 대화 핵심 팩트 요약 (어조 제외)]" not in system_msg


@pytest.mark.asyncio
async def test_debate_opening_vs_turn_prompt_switching():
    """Verify that opening prompt is used for first human message and turn prompt is used for subsequent turns."""
    captured_prompts = []

    def mock_get_llm(**kwargs):
        mock_llm = AsyncMock()

        async def _ainvoke(prompt_messages, config=None):
            captured_prompts.append(prompt_messages[0].content)
            return AIMessage(content="토론 테스트 응답")

        mock_llm.ainvoke = _ainvoke
        return mock_llm

    with patch("app.domain.graph.nodes._get_llm", side_effect=mock_get_llm):
        # 1. First turn: 1 HumanMessage -> opening_system_prompt
        state_first: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="토론을 시작합니다."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
        }
        await _run_persona_node(state_first, DEBATE_CRITIC_ID)
        assert len(captured_prompts) == 1
        # Opening prompt contains '◆ 오늘의 화두:'
        assert "◆ 오늘의 화두:" in captured_prompts[0]
        assert "역할 (첫 턴)" in captured_prompts[0]

        # 2. Subsequent turn: 2 HumanMessages -> turn_system_prompt
        state_second: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="첫 번째 메시지"),
                AIMessage(content="첫 번째 응답"),
                HumanMessage(content="두 번째 메시지"),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
        }
        await _run_persona_node(state_second, DEBATE_CRITIC_ID)
        assert len(captured_prompts) == 2
        # Turn prompt contains COMMON_DEBATE_TURN_RULES and '역할 (실시간 대화, 티키타카)'
        assert "역할 (실시간 대화, 티키타카)" in captured_prompts[1]
        assert "논리의 대립과 건설적 반론" in captured_prompts[1]
        assert "◆ 오늘의 화두:" not in captured_prompts[1]


@pytest.mark.asyncio
async def test_debate_conclude_turn_suppresses_open_questions():
    """Verify that in concluding/finale turns, system prompt strictly prohibits open-ended questions."""
    captured_prompts = []

    def mock_get_llm(**kwargs):
        mock_llm = AsyncMock()

        async def _ainvoke(prompt_messages, config=None):
            captured_prompts.extend(prompt_messages)
            return AIMessage(content="피날레 마무리 응답입니다.")

        mock_llm.ainvoke = _ainvoke
        return mock_llm

    with patch("app.domain.graph.nodes._get_llm", side_effect=mock_get_llm):
        state_conclude: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="오늘 토론 정말 감사했습니다. 마무리해 주세요."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "action": "conclude",
            "curated_books": [
                {
                    "title": "이방인",
                    "author": "알베르 카뮈",
                    "publisher": "민음사",
                    "isbn": "9788937460000",
                }
            ],
            "is_concluded": True,
        }

        await _run_persona_node(state_conclude, DEBATE_CRITIC_ID)

        system_msg = next((m.content for m in captured_prompts if getattr(m, "content", "")), "")

        # Verify finale marker and strict prohibition on ending with open questions
        assert FINALE_MARKER in system_msg
        assert "사용자에게 새로운 질문이나 다음 화두를 던져 대화를 연장하지 말고" in system_msg


@pytest.mark.asyncio
async def test_debate_conclude_not_triggered_on_negative_or_summary_phrases():
    """Verify that phrases containing conclude keywords with negatives or summary requests do NOT trigger early conclude."""
    mock_llm_response = AIMessage(
        content="계속해서 토론을 이어갑니다. 그 장면에 대해 더 이야기해 볼까요?"
    )

    with patch("app.domain.graph.nodes._get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_llm_response
        mock_get_llm.return_value = mock_llm

        # Test case 1: "토론 그만둘 생각은 없고 더 깊이 파고들고 싶어" (Contains '토론 그만' but has '없고')
        state_neg1: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="토론 그만둘 생각은 없고 더 깊이 파고들고 싶어."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "curated_books": None,
        }
        res_neg1 = await _run_persona_node(state_neg1, DEBATE_CRITIC_ID)
        assert "curator_request" not in res_neg1 or res_neg1.get("curator_request") is None
        assert not res_neg1.get("is_concluded")

        # Test case 2: "토론 마무리 단계는 아직 일러요. 더 나눠요." (Contains '토론 마무리' but has '일러')
        state_neg2: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="토론 마무리 단계는 아직 일러요. 더 나눠요."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "curated_books": None,
        }
        res_neg2 = await _run_persona_node(state_neg2, DEBATE_CRITIC_ID)
        assert "curator_request" not in res_neg2 or res_neg2.get("curator_request") is None
        assert not res_neg2.get("is_concluded")

        # Test case 3: "줄거리 깔끔하게 정리해줘" (Contains '정리' but not concluding)
        state_summary: Dict[str, Any] = {
            "messages": [
                HumanMessage(content="방금 논의한 줄거리 내용 깔끔하게 정리해줘."),
            ],
            "mode": "DEBATE",
            "active_persona": DEBATE_CRITIC_ID,
            "curated_books": None,
        }
        res_summary = await _run_persona_node(state_summary, DEBATE_CRITIC_ID)
        assert "curator_request" not in res_summary or res_summary.get("curator_request") is None
        assert not res_summary.get("is_concluded")
