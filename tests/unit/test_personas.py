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
