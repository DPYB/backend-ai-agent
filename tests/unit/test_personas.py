"""Unit tests for 8 Librarian and Debate Personas aligned with core-api."""

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


def test_persona_registry_total_count():
    """Verify registry contains exactly 8 personas (4 Librarians + 4 Debaters)."""
    assert len(PERSONA_REGISTRY) == 8


def test_librarian_personas_aligned_with_core_db_enum():
    """Verify 4 librarian personas match core-api DB ENUM ('CAT', 'SHOEBILL', 'SEA_SLUG', 'GECKO')."""
    librarians = [p for p in PERSONA_REGISTRY.values() if p["mode"] == "LIBRARIAN"]
    assert len(librarians) == 4

    lib_ids = [p["persona_id"] for p in librarians]
    assert CAT_ID in lib_ids
    assert SHOEBILL_ID in lib_ids
    assert SEA_SLUG_ID in lib_ids
    assert GECKO_ID in lib_ids


def test_debate_personas_count_and_keys():
    """Verify 4 debate personas exist with correct mode and metadata."""
    debaters = [p for p in PERSONA_REGISTRY.values() if p["mode"] == "DEBATE"]
    assert len(debaters) == 4

    debate_ids = [p["persona_id"] for p in debaters]
    assert DEBATE_CRITIC_ID in debate_ids
    assert DEBATE_STORYTELLER_ID in debate_ids
    assert DEBATE_COUNSELOR_ID in debate_ids
    assert DEBATE_OBSERVER_ID in debate_ids


def test_persona_prompt_integrity():
    """Verify each persona has non-empty prompts, display names, and unique IDs."""
    ids = set()
    display_names = set()

    for pid, meta in PERSONA_REGISTRY.items():
        assert pid == meta["persona_id"]
        assert len(meta["display_name"]) > 0
        assert len(meta["system_prompt"]) > 50
        assert len(meta["tone"]) > 0
        assert meta["mode"] in ("LIBRARIAN", "DEBATE")

        ids.add(meta["persona_id"])
        display_names.add(meta["display_name"])

    assert len(ids) == 8
    assert len(display_names) == 8


def test_debate_personas_homage_display_names():
    """Verify all 4 debate personas use the standardized '(오마주)' display name format."""
    critic = PERSONA_REGISTRY[DEBATE_CRITIC_ID]
    storyteller = PERSONA_REGISTRY[DEBATE_STORYTELLER_ID]
    counselor = PERSONA_REGISTRY[DEBATE_COUNSELOR_ID]
    observer = PERSONA_REGISTRY[DEBATE_OBSERVER_ID]

    assert critic["display_name"] == "평론가(이동진 오마주)"
    assert storyteller["display_name"] == "이야기꾼(설민석 오마주)"
    assert counselor["display_name"] == "상담사(오은영 오마주)"
    assert observer["display_name"] == "관찰가(강형욱 오마주)"


def test_debate_personas_required_format_and_recommendation_guidelines():
    """Verify each debate persona prompt enforces required answer formats and book recommendation link."""
    # Critic: Star rating, one-line review, discourse question
    critic_prompt = PERSONA_REGISTRY[DEBATE_CRITIC_ID]["system_prompt"]
    assert "★ 별점:" in critic_prompt
    assert "■ 한 줄 총평:" in critic_prompt
    assert "◆ 오늘의 화두:" in critic_prompt
    assert "토론 마무리 및 도서 추천 연계" in critic_prompt

    # Storyteller: Historical lesson, existential question, high-tension call
    storyteller_prompt = PERSONA_REGISTRY[DEBATE_STORYTELLER_ID]["system_prompt"]
    assert "🏛️ 역사가 주는 교훈:" in storyteller_prompt
    assert "🔥 함께 던지는 질문:" in storyteller_prompt
    assert "독자님!" in storyteller_prompt
    assert "토론 마무리 및 도서 추천 연계" in storyteller_prompt

    # Counselor: Mind care question, 109 crisis hotline, no medical diagnosis
    counselor_prompt = PERSONA_REGISTRY[DEBATE_COUNSELOR_ID]["system_prompt"]
    assert "🌱 마음 돌봄 질문:" in counselor_prompt
    assert "109" in counselor_prompt
    assert "진단명" in counselor_prompt
    assert "토론 마무리 및 도서 추천 연계" in counselor_prompt

    # Observer: Behavioral signal review, reality observation question
    observer_prompt = PERSONA_REGISTRY[DEBATE_OBSERVER_ID]["system_prompt"]
    assert "🔍 행동 시그널 총평:" in observer_prompt
    assert "⚡ 현실 관찰 질문:" in observer_prompt
    assert "행동 시그널" in observer_prompt
    assert "토론 마무리 및 도서 추천 연계" in observer_prompt
