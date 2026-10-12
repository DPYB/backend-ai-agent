"""Unit tests for Debate Persona tone isolation, anti-animal-leakage, and session partitioning."""

from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.api import router
from app.domain.guardrails.shared_rules import DEBATE_GUARDRAILS
from app.domain.personas import (
    DEBATE_COUNSELOR_ID,
    DEBATE_CRITIC_ID,
    DEBATE_OBSERVER_ID,
    DEBATE_STORYTELLER_ID,
    PERSONA_REGISTRY,
)
from app.main import app


@pytest.fixture(autouse=True)
def mock_graph_for_debate(monkeypatch: pytest.MonkeyPatch):
    """Narrow mock on LangGraph execution to isolate debate persona routing tests from external LLM I/O."""

    async def _mock_ainvoke(initial_state, config=None):
        persona = initial_state.get("active_persona", "DEBATE_CRITIC")
        meta = PERSONA_REGISTRY.get(persona, {})
        return {
            **initial_state,
            "messages": [
                *initial_state.get("messages", []),
                AIMessage(content="토론 격리 테스트용 모킹 응답입니다."),
            ],
            "active_persona": persona,
            "display_name": meta.get("display_name", persona),
            "switch_suggestion": None,
            "curated_books": None,
            "signals": initial_state.get("signals"),
            "is_concluded": False,
            "debate_summary": None,
        }

    mock = AsyncMock(side_effect=_mock_ainvoke)
    monkeypatch.setattr(router._graph, "ainvoke", mock)
    return mock


def test_debate_personas_have_anti_animal_guardrails():
    """Verify that all 4 debate personas include DEBATE_GUARDRAILS in their prompts."""
    debate_ids = [
        DEBATE_CRITIC_ID,
        DEBATE_STORYTELLER_ID,
        DEBATE_COUNSELOR_ID,
        DEBATE_OBSERVER_ID,
    ]

    for p_id in debate_ids:
        meta = PERSONA_REGISTRY[p_id]
        sys_prompt = meta["system_prompt"]
        opening_prompt = meta["opening_system_prompt"]
        turn_prompt = meta["turn_system_prompt"]

        for prompt_text in (sys_prompt, opening_prompt, turn_prompt):
            assert DEBATE_GUARDRAILS in prompt_text, f"{p_id} missing DEBATE_GUARDRAILS"
            assert "동물 사서 말투 오염 엄격 금지" in prompt_text
            assert "~냥" in prompt_text
            assert "~누누" in prompt_text
            assert "~두둥" in prompt_text
            assert "~크크" in prompt_text


def test_debate_output_sanitizer_removes_accidental_animal_endings():
    """Verify that _sanitize_persona_output strips librarian animal endings while strictly preserving legitimate words.

    Must preserve:
    - Currency/quantifiers: '열 냥', '백 냥', '열 냥이'
    - Adverbs: '누누이', '그냥'
    - Common nouns: '크레파스'
    """
    from app.domain.graph.nodes import _sanitize_persona_output, _strip_debate_animal_endings

    # 1. Animal endings stripped at predicate endings
    raw_critic_leak = "이 작품의 결말은 정말 비극적이었다냥! 독자님 생각은 어떠신가요두둥?"
    cleaned = _sanitize_persona_output(
        raw_critic_leak, curated_books=None, persona_id=DEBATE_CRITIC_ID
    )
    assert "냥" not in cleaned
    assert "두둥" not in cleaned
    assert cleaned == "이 작품의 결말은 정말 비극적이었다! 독자님 생각은 어떠신가요?"

    raw_slug_leak = "그렇게 생각할 수도 있어요누누. 그 심정이 참 애틋하네요크크~"
    cleaned_slug = _sanitize_persona_output(
        raw_slug_leak, curated_books=None, persona_id=DEBATE_COUNSELOR_ID
    )
    assert "누누" not in cleaned_slug
    assert "크크" not in cleaned_slug
    assert cleaned_slug == "그렇게 생각할 수도 있어요. 그 심정이 참 애틋하네요~"

    # 2. Strict False Positive Prevention:
    # '열 냥', '백 냥', '열 냥이', '누누이', '그냥', '크레파스' must NEVER be stripped!
    currency_text = (
        "당시 책 한 권의 가격은 열 냥, 혹은 백 냥에 달했습니다. 열 냥이 결코 적은 돈이 아니었죠."
    )
    cleaned_currency = _strip_debate_animal_endings(currency_text)
    assert cleaned_currency == currency_text
    assert "열 냥" in cleaned_currency
    assert "백 냥" in cleaned_currency
    assert "열 냥이" in cleaned_currency

    adverb_noun_text = (
        "제가 누누이 강조했듯, 그냥 책을 읽은 게 아니라 크레파스로 표지를 칠하듯 깊이 사유하셨군요."
    )
    cleaned_adverb_noun = _strip_debate_animal_endings(adverb_noun_text)
    assert cleaned_adverb_noun == adverb_noun_text
    assert "누누이" in cleaned_adverb_noun
    assert "그냥" in cleaned_adverb_noun
    assert "크레파스" in cleaned_adverb_noun


@pytest.mark.asyncio
async def test_session_partitioning_for_debate_mode():
    """Verify that session_id is automatically partitioned with persona ID for DEBATE mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Send chat in DEBATE mode with plain session_id
        payload: Dict[str, Any] = {
            "message": "인간실격의 요조에 대해 어떻게 생각하시나요?",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
            "session_id": "test-session-1234",
            "librarian_name": "내고양이",  # custom librarian name should NOT leak to debate persona
        }
        res = await client.post("/api/v1/chat", json=payload)
        assert res.status_code == 200
        data = res.json()

        # Session ID must be partitioned with :DEBATE_CRITIC
        assert data["session_id"] == "test-session-1234:DEBATE_CRITIC"
        assert data["active_persona"] == "DEBATE_CRITIC"
        # Display name must remain the debate homage name, NOT the custom librarian name
        assert data["display_name"] == "평론가(이동진 오마주)"
        assert "내고양이" not in data["display_name"]


@pytest.mark.asyncio
async def test_cross_session_isolation_between_sea_slug_and_debate():
    """Verify that conversation with Sea Slug (누디) does not bleed into Debate session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        base_session = "shared-session-test"

        # 1. First chat with Sea Slug (누디)
        sea_slug_payload = {
            "message": "바다를 보며 기차 여행을 떠나고 싶어",
            "mode": "LIBRARIAN",
            "persona": "SEA_SLUG",
            "session_id": base_session,
        }
        res_slug = await client.post("/api/v1/chat", json=sea_slug_payload)
        assert res_slug.status_code == 200
        slug_data = res_slug.json()
        assert slug_data["session_id"] == f"{base_session}:SEA_SLUG"

        # 2. Chat with Debate Critic using the same base session
        debate_payload = {
            "message": "오늘 토론을 시작해봅시다.",
            "mode": "DEBATE",
            "persona": "DEBATE_CRITIC",
            "session_id": base_session,
        }
        res_debate = await client.post("/api/v1/chat", json=debate_payload)
        assert res_debate.status_code == 200
        debate_data = res_debate.json()
        # Partitioned separately, preventing message history bleed
        assert debate_data["session_id"] == f"{base_session}:DEBATE_CRITIC"
        assert debate_data["active_persona"] == "DEBATE_CRITIC"


@pytest.mark.asyncio
async def test_frontend_lingering_librarian_id_does_not_override_debate_persona():
    """Verify that if frontend sends a lingering librarian_id (e.g. 'nudi') along with persona='관찰가'

    or mode='DEBATE', the debate observer persona is strictly chosen and not sea slug.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Case 1: persona='DEBATE_OBSERVER', but librarian_id='nudi' lingers from previous tab
        payload_1 = {
            "message": "동물들 생각을 읽고 싶어",
            "persona": "DEBATE_OBSERVER",
            "librarian_id": "nudi",  # Lingering frontend state
            "mode": "DEBATE",
        }
        res_1 = await client.post("/api/v1/chat", json=payload_1)
        assert res_1.status_code == 200
        data_1 = res_1.json()
        assert data_1["active_persona"] == "DEBATE_OBSERVER"
        assert data_1["display_name"] == "관찰가(강형욱 오마주)"
        assert data_1["mode"] == "DEBATE"

        # Case 2: persona='관찰가' (Korean alias), librarian_id='sea_slug', mode not set or LIBRARIAN
        payload_2 = {
            "message": "동물들 생각을 읽고 싶어",
            "persona": "관찰가",
            "librarian_id": "sea_slug",  # Lingering frontend state
        }
        res_2 = await client.post("/api/v1/chat", json=payload_2)
        assert res_2.status_code == 200
        data_2 = res_2.json()
        assert data_2["active_persona"] == "DEBATE_OBSERVER"
        assert data_2["display_name"] == "관찰가(강형욱 오마주)"
        assert data_2["mode"] == "DEBATE"
