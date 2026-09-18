"""Unit tests for Debate Persona tone isolation, anti-animal-leakage, and session partitioning."""

from typing import Any, Dict

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.guardrails.shared_rules import DEBATE_GUARDRAILS
from app.domain.personas import (
    DEBATE_COUNSELOR_ID,
    DEBATE_CRITIC_ID,
    DEBATE_OBSERVER_ID,
    DEBATE_STORYTELLER_ID,
    PERSONA_REGISTRY,
)
from app.main import app


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
