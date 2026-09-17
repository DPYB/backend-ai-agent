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


def test_librarian_personas_default_display_names():
    """Verify all 4 librarian personas use the standardized default display names (블루, 슈빌, 누디, 게코)."""
    cat = PERSONA_REGISTRY[CAT_ID]
    shoebill = PERSONA_REGISTRY[SHOEBILL_ID]
    sea_slug = PERSONA_REGISTRY[SEA_SLUG_ID]
    gecko = PERSONA_REGISTRY[GECKO_ID]

    assert cat["display_name"] == "블루"
    assert shoebill["display_name"] == "슈빌"
    assert sea_slug["display_name"] == "누디"
    assert gecko["display_name"] == "게코"


def test_librarian_personas_mbti_genre_and_endings():
    """Verify all 4 librarian personas enforce their respective MBTI, genres, and ending rules (~냥, ~두둥, ~누누, ~크크)."""
    # 1. Cat: INTJ, 총류/철학/종교, ~냥
    cat_prompt = PERSONA_REGISTRY[CAT_ID]["system_prompt"]
    assert "러시안 블루" in cat_prompt
    assert "INTJ" in cat_prompt
    assert "철학" in cat_prompt
    assert "~냥" in cat_prompt
    assert "사색가" in cat_prompt
    assert "[호출 명칭]" in cat_prompt

    # 2. Shoebill: ISTP, 자연과학/기술과학, ~두둥
    shoebill_prompt = PERSONA_REGISTRY[SHOEBILL_ID]["system_prompt"]
    assert "넙적부리황새" in shoebill_prompt
    assert "ISTP" in shoebill_prompt
    assert "자연과학" in shoebill_prompt
    assert "~두둥" in shoebill_prompt
    assert "실용적인 탐구자" in shoebill_prompt
    assert "[호출 명칭]" in shoebill_prompt

    # 3. Sea Slug: INFP, 예술/문학, ~누누
    sea_slug_prompt = PERSONA_REGISTRY[SEA_SLUG_ID]["system_prompt"]
    assert "갯민숭달팽이" in sea_slug_prompt
    assert "INFP" in sea_slug_prompt
    assert "문학" in sea_slug_prompt
    assert "~누누" in sea_slug_prompt
    assert "감성가" in sea_slug_prompt
    assert "[호출 명칭]" in sea_slug_prompt

    # 4. Gecko: ENFJ, 사회과학/언어/역사, ~크크
    gecko_prompt = PERSONA_REGISTRY[GECKO_ID]["system_prompt"]
    assert "게코 도마뱀" in gecko_prompt
    assert "ENFJ" in gecko_prompt
    assert "역사" in gecko_prompt
    assert "~크크" in gecko_prompt
    assert "공감형 탐구자" in gecko_prompt
    assert "[호출 명칭]" in gecko_prompt


def test_debate_personas_opening_turn_prompt_split():
    """Verify all 4 debate personas have separate opening and turn system prompts registered."""
    debate_ids = [
        DEBATE_CRITIC_ID,
        DEBATE_STORYTELLER_ID,
        DEBATE_COUNSELOR_ID,
        DEBATE_OBSERVER_ID,
    ]
    for persona_id in debate_ids:
        meta = PERSONA_REGISTRY[persona_id]
        assert "opening_system_prompt" in meta, f"{persona_id} is missing opening_system_prompt"
        assert "turn_system_prompt" in meta, f"{persona_id} is missing turn_system_prompt"
        # Opening prompt should contain fixed format markers
        opening = meta["opening_system_prompt"]
        turn = meta["turn_system_prompt"]
        # They must be different
        assert opening != turn, f"{persona_id} opening and turn prompts must differ"
        # Turn prompt must forbid fixed format (contains the strict rule)
        assert "고정 포맷" in turn and "금지" in turn, (
            f"{persona_id} turn_prompt must contain fixed-format prohibition"
        )


def test_debate_personas_opening_prompt_contains_fixed_formats():
    """Verify each debate persona opening prompt still enforces its required fixed answer format."""
    # Critic opening: star rating + one-line review + discourse question
    critic_opening = PERSONA_REGISTRY[DEBATE_CRITIC_ID]["opening_system_prompt"]
    assert "★ 별점:" in critic_opening
    assert "■ 한 줄 총평:" in critic_opening
    assert "◆ 오늘의 화두:" in critic_opening

    # Storyteller opening: historical lesson + existential question
    storyteller_opening = PERSONA_REGISTRY[DEBATE_STORYTELLER_ID]["opening_system_prompt"]
    assert "🏛️ 역사가 주는 교훈:" in storyteller_opening
    assert "🔥 함께 던지는 질문:" in storyteller_opening

    # Counselor opening: mind care question with 109 hotline
    counselor_opening = PERSONA_REGISTRY[DEBATE_COUNSELOR_ID]["opening_system_prompt"]
    assert "🌱 마음 돌봄 질문:" in counselor_opening
    assert "109" in counselor_opening

    # Observer opening: behavioral signal review + reality observation question
    observer_opening = PERSONA_REGISTRY[DEBATE_OBSERVER_ID]["opening_system_prompt"]
    assert "🔍 행동 시그널 총평:" in observer_opening
    assert "⚡ 현실 관찰 질문:" in observer_opening


def test_debate_personas_turn_prompt_enforces_mirroring_and_open_questions():
    """Verify each debate persona turn prompt enforces mirroring and open-ended questions."""
    for persona_id in [
        DEBATE_CRITIC_ID,
        DEBATE_STORYTELLER_ID,
        DEBATE_COUNSELOR_ID,
        DEBATE_OBSERVER_ID,
    ]:
        turn = PERSONA_REGISTRY[persona_id]["turn_system_prompt"]
        # Must contain mirroring instruction
        assert "미러링" in turn or "Mirroring" in turn, (
            f"{persona_id} turn prompt missing mirroring rule"
        )
        # Must contain open question / ending question guidance
        assert "질문" in turn, f"{persona_id} turn prompt missing question guidance"
