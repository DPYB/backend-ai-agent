"""Unit tests for Step 2 hierarchical book verification (Core API -> National Library fallback).

Validates:
1. ISBN-10 / ISBN-13 checksum verification and ISBN-10 to ISBN-13 recalculation.
2. Conservative author matching (Western name inversion, primary author vs translator separation, strict anti-set false positive protection).
3. Edition intent extraction, deterministic cache key isolation, and cache bypass for ambiguous queries.
4. Hierarchical verification chain: Tier 1 Core API (YES24) -> Tier 2 National Library fallback.
5. Track A (valid ISBN) vs Track B (strict 3-field requirement for missing ISBN).
"""

import asyncio

import pytest

from app.domain.graph.curator_node import (
    _extract_primary_author,
    _is_matching_author,
    _verify_single_candidate,
    calculate_isbn13_check_digit,
    convert_isbn10_to_isbn13,
    extract_edition_intent,
    get_biblio_cache_key,
    get_cached_biblio,
    normalize_and_validate_isbn,
    resolve_targeted,
    set_cached_biblio,
    validate_isbn10,
    validate_isbn13,
    verify_candidates,
)
from app.infrastructure.redis_session import get_redis_session_manager


@pytest.fixture(autouse=True)
def clear_biblio_cache():
    """Ensure in-memory cache is clear before each test."""
    redis_mgr = get_redis_session_manager()
    redis_mgr._in_memory_store.clear()
    yield
    redis_mgr._in_memory_store.clear()


# ---------------------------------------------------------------------------
# 1. ISBN Validation & Conversion Tests
# ---------------------------------------------------------------------------


def test_validate_isbn10_valid():
    """Valid ISBN-10 strings (numeric and 'X' check digit, with or without hyphens)."""
    assert validate_isbn10("0471958697") is True
    assert validate_isbn10("0-471-95869-7") is True
    # 'X' check digit (10)
    assert validate_isbn10("012000030X") is True
    assert validate_isbn10("0-120-00030-x") is True


def test_validate_isbn10_invalid():
    """Invalid ISBN-10 strings: wrong checksum, bad length, non-numeric."""
    assert validate_isbn10("0471958698") is False  # checksum failure
    assert validate_isbn10("123456789") is False  # 9 digits
    assert validate_isbn10("12345678901") is False  # 11 digits
    assert validate_isbn10("04719A8697") is False  # char in body
    assert validate_isbn10("") is False


def test_calculate_isbn13_check_digit():
    """EAN-13 check digit calculation with alternating 1, 3 weights."""
    # 978-0-471-95869 -> check digit 7
    assert calculate_isbn13_check_digit("978047195869") == "7"
    # 978-8-937-46001 -> check digit 2
    assert calculate_isbn13_check_digit("978893746001") == "2"

    with pytest.raises(ValueError):
        calculate_isbn13_check_digit("12345")  # not 12 digits


def test_validate_isbn13_valid():
    """Valid ISBN-13 strings with correct checksum."""
    assert validate_isbn13("9780471958697") is True
    assert validate_isbn13("978-0-471-95869-7") is True
    assert validate_isbn13("9788937460012") is True


def test_validate_isbn13_invalid():
    """Invalid ISBN-13 strings with wrong checksum or malformed length."""
    assert validate_isbn13("9780471958698") is False  # wrong check digit
    assert validate_isbn13("97804719586") is False  # 11 digits
    assert validate_isbn13("97804719586970") is False  # 14 digits
    assert validate_isbn13("978047195869X") is False  # 'X' not allowed in ISBN-13
    assert validate_isbn13("") is False


def test_convert_isbn10_to_isbn13():
    """Convert valid ISBN-10 to ISBN-13 with newly recalculated check digit."""
    # ISBN-10 '0471958697' (check digit 7) -> '978' + '047195869' + check digit '7' -> '9780471958697'
    conv = convert_isbn10_to_isbn13("0471958697")
    assert conv == "9780471958697"

    # ISBN-10 with check digit 'X': '012000030X'
    # 978 + 012000030 -> 978012000030
    # S = 9*1 + 7*3 + 8*1 + 0*3 + 1*1 + 2*3 + 0 + 0 + 0 + 0 + 3*1 + 0*3 = 9+21+8+1+6+3 = 48
    # check = (10 - (48 % 10)) % 10 = (10 - 8) % 10 = 2
    conv_x = convert_isbn10_to_isbn13("012000030X")
    assert conv_x == "9780120000302"

    # Additional real-world ISBN-10 with 'X': '080442957X' -> '9780804429573'
    conv_x2 = convert_isbn10_to_isbn13("080442957X")
    assert conv_x2 == "9780804429573"

    # Invalid ISBN-10 returns None
    assert convert_isbn10_to_isbn13("0471958699") is None
    assert convert_isbn10_to_isbn13("invalid") is None


def test_normalize_and_validate_isbn_categories():
    """Distinguish VALID_13, CONVERTED_10, INVALID, and MISSING status."""
    # VALID_13
    isbn, status = normalize_and_validate_isbn("978-0-471-95869-7")
    assert status == "VALID_13"
    assert isbn == "9780471958697"

    # CONVERTED_10
    isbn, status = normalize_and_validate_isbn("0471958697")
    assert status == "CONVERTED_10"
    assert isbn == "9780471958697"

    # MISSING
    assert normalize_and_validate_isbn(None) == (None, "MISSING")
    assert normalize_and_validate_isbn("") == (None, "MISSING")
    assert normalize_and_validate_isbn("   ") == (None, "MISSING")

    # INVALID
    assert normalize_and_validate_isbn("9780471958698") == (None, "INVALID")
    assert normalize_and_validate_isbn("12345") == (None, "INVALID")
    assert normalize_and_validate_isbn("bad-isbn-string") == (None, "INVALID")


# ---------------------------------------------------------------------------
# 2. Author Normalization & Conservative Matching Tests
# ---------------------------------------------------------------------------


def test_extract_primary_author():
    """Extract primary author and strip translator / illustrator annotations."""
    assert _extract_primary_author("조지 오웰 지음, 박경희 옮김") == "조지 오웰"
    assert _extract_primary_author("헤르만 헤세 저 / 정현규 역") == "헤르만 헤세"
    assert _extract_primary_author("미하엘 엔데 글, 베른하르트 그림") == "미하엘 엔데"
    assert _extract_primary_author("김호연 지음") == "김호연"
    assert _extract_primary_author("유발 하라리 저") == "유발 하라리"
    assert _extract_primary_author("Orwell, George") == "Orwell, George"


def test_is_matching_author_western_inversion():
    """Support Western name inversion ('George Orwell' <-> 'Orwell, George')."""
    assert _is_matching_author("George Orwell", "Orwell, George") is True
    assert _is_matching_author("Orwell, George", "George Orwell") is True
    assert _is_matching_author("헤르만 헤세", "헤르만 헤세 지음") is True
    assert _is_matching_author("조지 오웰", "조지 오웰 지음, 박경희 옮김") is True


def test_is_matching_author_reject_set_false_positive():
    """Conservative matching rejects character set anagram false positives."""
    # Anagram false positive: '김영하' vs '김하영'
    assert _is_matching_author("김영하", "김하영") is False
    assert _is_matching_author("이민진", "진민이") is False
    assert _is_matching_author("박완서", "서완박") is False


def test_is_matching_author_translator_vs_author():
    """Candidate where only translator matches must be rejected."""
    # When candidate specifies '박경희 지음' but expected author is '조지 오웰'
    assert _is_matching_author("조지 오웰", "박경희 지음") is False


def test_is_matching_author_empty_expected():
    """Empty expected author permits title-only lookup."""
    assert _is_matching_author("", "헤르만 헤세") is True
    assert _is_matching_author("   ", "조지 오웰") is True


# ---------------------------------------------------------------------------
# 3. Edition Intent & Cache Isolation Tests
# ---------------------------------------------------------------------------


def test_extract_edition_intent():
    """Identify comics, children, original, publisher, general, and ambiguous intents."""
    assert extract_edition_intent("마음을 달래줄 좋은 소설 추천해줘") == "GENERAL"
    assert extract_edition_intent("만화로 된 삼국지 있어?") == "COMICS"
    assert extract_edition_intent("웹툰 단행본 추천") == "COMICS"
    assert extract_edition_intent("초등학생 아이가 읽을 동화책 추천해줘") == "CHILDREN"
    assert extract_edition_intent("영문판 원서로 읽기 좋은 책") == "ORIGINAL"
    assert extract_edition_intent("민음사 세계문학 전집 중에서 추천해줘") == "PUB:민음사"

    # Conflicting / ambiguous intent bypasses cache (returns None)
    assert extract_edition_intent("만화로 된 아동용 원서 추천") is None


@pytest.mark.asyncio
async def test_biblio_cache_isolation_and_pollution_prevention():
    """Ensure different edition intents generate distinct cache keys preventing cache pollution."""
    key_general = get_biblio_cache_key("데미안", "헤르만 헤세", "GENERAL")
    key_comics = get_biblio_cache_key("데미안", "헤르만 헤세", "COMICS")
    key_pub = get_biblio_cache_key("데미안", "헤르만 헤세", "PUB:민음사")

    assert key_general != key_comics
    assert key_general != key_pub
    assert key_comics != key_pub

    # Save general edition to cache
    general_data = {
        "title": "데미안",
        "author": "헤르만 헤세",
        "isbn": "9788937460012",
        "description": "일반 소설 판본",
        "verified": True,
    }
    await set_cached_biblio(key_general, general_data, ttl_seconds=60)

    # General hit
    cached_general = await get_cached_biblio(key_general)
    assert cached_general is not None
    assert cached_general["description"] == "일반 소설 판본"

    # Comics must miss and NOT reuse general edition cache
    cached_comics = await get_cached_biblio(key_comics)
    assert cached_comics is None


@pytest.mark.asyncio
async def test_biblio_cache_language_and_publisher_isolation():
    """Verify Korean translation (GENERAL) and English original (ORIGINAL) do NOT share cache."""
    key_korean = get_biblio_cache_key("1984", "조지 오웰", "GENERAL")
    key_english = get_biblio_cache_key("1984", "조지 오웰", "ORIGINAL")
    key_pub = get_biblio_cache_key("1984", "조지 오웰", "PUB:민음사")

    # 1. Assert cache keys are physically distinct
    assert key_korean != key_english
    assert key_korean != key_pub
    assert key_english != key_pub

    # 2. Cache Korean translation
    korean_biblio = {
        "title": "1984",
        "author": "조지 오웰",
        "publisher": "민음사",
        "isbn": "9788937460777",
        "description": "한국어 정식 번역본",
        "verified": True,
    }
    await set_cached_biblio(key_korean, korean_biblio, ttl_seconds=60)

    # 3. Requesting original or publisher-specific must NOT hit Korean general cache
    assert await get_cached_biblio(key_korean) is not None
    assert await get_cached_biblio(key_english) is None
    assert await get_cached_biblio(key_pub) is None


# ---------------------------------------------------------------------------
# 4. Hierarchical Verification Chain Tests (Core API -> National Library)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_candidate_core_api_primary_hit(monkeypatch):
    """Tier 1: Core API returns valid book with ISBN -> immediately verified without National Library."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    nl_called = False

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "데미안",
                "author": "헤르만 헤세",
                "publisher": "민음사",
                "isbn": "9788937460012",
                "cover_url": "https://images.example.com/demian.jpg",
                "page_count": 240,
                "description": "정식 YES24 서지",
            }
        ]

    async def mock_nl_search(title, author=None):
        nonlocal nl_called
        nl_called = True
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "데미안", "author": "헤르만 헤세", "reason": "성장 소설"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is not None
    assert result["source"] == "CORE_API"
    assert result["isbn"] == "9788937460012"
    assert result["verified"] is True
    # National Library must NOT be called on Core API hit
    assert nl_called is False


@pytest.mark.asyncio
async def test_verify_candidate_core_api_timeout_fallback_to_national_library(monkeypatch):
    """Tier 2: Core API timeout / error triggers graceful fallback to National Library."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_timeout(query, limit=5):
        # Simulate network timeout
        await asyncio.sleep(0.01)
        raise asyncio.TimeoutError()

    async def mock_nl_search(title, author=None):
        return {
            "title": "데미안",
            "author": "헤르만 헤세",
            "publisher": "민음사",
            "isbn": "9788937460012",
            "cover_url": "https://images.nl.go.kr/demian.jpg",
            "page_count": 240,
            "description": "국립중앙도서관 정식 서지",
            "source": "NATIONAL_LIBRARY",
        }

    monkeypatch.setattr(core_client, "search_books", mock_core_timeout)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "데미안", "author": "헤르만 헤세", "reason": "성장 소설"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is not None
    assert result["source"] == "NATIONAL_LIBRARY"
    assert result["isbn"] == "9788937460012"
    assert result["verified"] is True


@pytest.mark.asyncio
async def test_verify_candidate_track_b_missing_isbn(monkeypatch):
    """Track B: Real book with MISSING ISBN is accepted if publisher, cover, and page_count are present."""
    from app.infrastructure.core_api_client import get_core_api_client

    core_client = get_core_api_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "어느 고서점의 일기",
                "author": "숀 바이텔",
                "publisher": "문학동네",
                "isbn": None,  # MISSING ISBN
                "cover_url": "https://images.example.com/cover.jpg",
                "page_count": 380,
                "description": "실존 도서",
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search)

    cand = {"title": "어느 고서점의 일기", "author": "숀 바이텔", "reason": "서점 이야기"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is not None
    assert result["verified"] is True
    assert result["source"] == "CORE_API"
    assert result["isbn"] == ""


@pytest.mark.asyncio
async def test_verify_candidate_track_b_reject_missing_fields(monkeypatch):
    """Track B: Candidate with MISSING ISBN is rejected if required fields (publisher, cover, page_count) are absent."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "불완전한 도서",
                "author": "작가 미상",
                "publisher": "",  # Missing publisher
                "isbn": None,
                "cover_url": "",  # Missing cover
                "page_count": 0,  # Missing page_count
            }
        ]

    async def mock_nl_search(title, author=None):
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "불완전한 도서", "author": "작가 미상", "reason": "테스트"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is None  # Completely rejected


@pytest.mark.asyncio
async def test_verify_candidate_invalid_isbn_reject(monkeypatch):
    """Candidate with malformed/INVALID checksum ISBN is immediately rejected."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "위조 바코드 도서",
                "author": "가짜 저자",
                "publisher": "가짜 출판사",
                "isbn": "9780471958698",  # Invalid checksum!
                "cover_url": "https://images.example.com/fake.jpg",
                "page_count": 200,
            }
        ]

    async def mock_nl_search(title, author=None):
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "위조 바코드 도서", "author": "가짜 저자", "reason": "테스트"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is None


@pytest.mark.asyncio
async def test_verify_candidate_author_mismatch_reject(monkeypatch):
    """Homonymous book title with completely different author must be rejected."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "코스모스",
                "author": "김철수",  # Expected: 칼 세이건
                "publisher": "다른 출판사",
                "isbn": "9788937460012",
                "cover_url": "https://images.example.com/other.jpg",
                "page_count": 300,
            }
        ]

    async def mock_nl_search(title, author=None):
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "코스모스", "author": "칼 세이건", "reason": "우주 과학"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is None


@pytest.mark.asyncio
async def test_resolve_targeted_hierarchical(monkeypatch):
    """resolve_targeted executes hierarchical verification for directly targeted titles."""
    from app.infrastructure.core_api_client import get_core_api_client

    core_client = get_core_api_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "프로젝트 헤일메리",
                "author": "앤디 위어",
                "publisher": "알에이치코리아",
                "isbn": "9788925588735",
                "cover_url": "https://images.example.com/phm.jpg",
                "page_count": 692,
                "description": "SF 명작",
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search)

    target_result = await resolve_targeted("《프로젝트 헤일메리》", edition_intent="GENERAL")
    assert target_result is not None
    assert target_result["title"] == "프로젝트 헤일메리"
    assert target_result["author"] == "앤디 위어"
    assert target_result["isbn"] == "9788925588735"
    assert target_result["era"] == "targeted"
    assert target_result["source"] == "CORE_API"


@pytest.mark.asyncio
async def test_verify_candidates_parallel_hierarchical(monkeypatch):
    """Parallel verification of 3 candidates: 1 Core API hit, 1 NL fallback hit, 1 rejection."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_search(query, limit=5):
        if "데미안" in query:
            return [
                {
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "publisher": "민음사",
                    "isbn": "9788937460012",
                    "cover_url": "https://images.example.com/demian.jpg",
                    "page_count": 240,
                }
            ]
        # For other queries, Core API has no results
        return []

    async def mock_nl_search(title, author=None):
        if "불편한 편의점" in title:
            return {
                "title": "불편한 편의점",
                "author": "김호연",
                "publisher": "나무옆의자",
                "isbn": "9791161571188",
                "cover_url": "https://images.nl.go.kr/store.jpg",
                "page_count": 268,
                "source": "NATIONAL_LIBRARY",
            }
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    candidates = [
        {"title": "데미안", "author": "헤르만 헤세", "reason": "이유 1"},
        {"title": "불편한 편의점", "author": "김호연", "reason": "이유 2"},
        {"title": "환상의 유령도서", "author": "가짜 저자", "reason": "이유 3"},
    ]

    verified = await verify_candidates(candidates, edition_intent=None)

    assert len(verified) == 2
    sources = {v["title"]: v["source"] for v in verified}
    assert sources["데미안"] == "CORE_API"
    assert sources["불편한 편의점"] == "NATIONAL_LIBRARY"


@pytest.mark.asyncio
async def test_verify_candidate_core_api_invalid_isbn_continues_to_next_candidate(monkeypatch):
    """Core API candidate with invalid ISBN is rejected without aborting search for subsequent valid candidates."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    nl_called = False

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "코스모스",
                "author": "칼 세이건",
                "publisher": "사이언스북스",
                "isbn": "9780471958698",  # Invalid checksum
                "cover_url": "https://images.example.com/bad.jpg",
                "page_count": 700,
            },
            {
                "title": "코스모스",
                "author": "칼 세이건",
                "publisher": "사이언스북스",
                "isbn": "9788983711892",  # Valid checksum (8983711892)
                "cover_url": "https://images.example.com/good.jpg",
                "page_count": 712,
            },
        ]

    async def mock_nl_search(title, author=None):
        nonlocal nl_called
        nl_called = True
        return None

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "코스모스", "author": "칼 세이건", "reason": "우주 교양"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is not None
    assert result["source"] == "CORE_API"
    assert result["isbn"] == "9788983711892"
    assert nl_called is False  # Second Core API candidate succeeded, NL fallback not needed


@pytest.mark.asyncio
async def test_verify_candidate_core_api_all_invalid_falls_back_to_national_library(monkeypatch):
    """When all Core API candidates have invalid ISBNs, search does not fail; it falls back to National Library."""
    from app.infrastructure.core_api_client import get_core_api_client
    from app.infrastructure.national_library_client import get_national_library_client

    core_client = get_core_api_client()
    nl_client = get_national_library_client()

    async def mock_core_search(query, limit=5):
        return [
            {
                "title": "코스모스",
                "author": "칼 세이건",
                "publisher": "가짜",
                "isbn": "9780000000001",  # Invalid checksum
                "cover_url": "https://images.example.com/bad.jpg",
                "page_count": 700,
            }
        ]

    async def mock_nl_search(title, author=None):
        return {
            "title": "코스모스",
            "author": "칼 세이건",
            "publisher": "사이언스북스",
            "isbn": "9788983711892",  # Valid ISBN in National Library
            "cover_url": "https://images.nl.go.kr/cosmos.jpg",
            "page_count": 712,
            "source": "NATIONAL_LIBRARY",
        }

    monkeypatch.setattr(core_client, "search_books", mock_core_search)
    monkeypatch.setattr(nl_client, "search_book", mock_nl_search)

    cand = {"title": "코스모스", "author": "칼 세이건", "reason": "우주 교양"}
    result = await _verify_single_candidate(cand, edition_intent=None)

    assert result is not None
    assert result["source"] == "NATIONAL_LIBRARY"
    assert result["isbn"] == "9788983711892"


# ---------------------------------------------------------------------------
# 6. Core API Verification Genre Preservation Tests (Phase 70-3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_candidate_core_api_genre_preserved(monkeypatch):
    """Verify standard genre Enum is preserved and normalized when Core API provides genre."""
    from app.infrastructure.core_api_client import get_core_api_client

    core_client = get_core_api_client()

    # Case 1: Standard uppercase Enum from Core API
    async def mock_core_search_lit(query, limit=5):
        return [
            {
                "title": "데미안",
                "author": "헤르만 헤세",
                "publisher": "민음사",
                "isbn": "9788937460012",
                "cover_url": "https://images.example.com/demian.jpg",
                "page_count": 240,
                "genre": "LITERATURE",
                "kdc": "853",
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search_lit)
    cand = {"title": "데미안", "author": "헤르만 헤세", "reason": "성장 소설"}
    result = await _verify_single_candidate(cand, edition_intent=None)
    assert result is not None
    assert result["source"] == "CORE_API"
    assert result["genre"] == "LITERATURE"

    # Case 2: Lowercase / alias normalization (e.g. 'art' -> 'ARTS')
    async def mock_core_search_art(query, limit=5):
        return [
            {
                "title": "서양미술사",
                "author": "에른스트 곰브리치",
                "publisher": "열화당",
                "isbn": "9788930101882",
                "cover_url": "https://images.example.com/art.jpg",
                "page_count": 688,
                "genre": "art",
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search_art)
    cand_art = {"title": "서양미술사", "author": "에른스트 곰브리치", "reason": "미술 고전"}
    result_art = await _verify_single_candidate(cand_art, edition_intent=None)
    assert result_art is not None
    assert result_art["genre"] == "ARTS"


@pytest.mark.asyncio
async def test_verify_candidate_core_api_kdc_fallback_when_genre_none(monkeypatch):
    """Verify KDC mapping fallback works when Core API returns genre='NONE' or None."""
    from app.infrastructure.core_api_client import get_core_api_client

    core_client = get_core_api_client()

    # Core API genre='NONE', but kdc='190' (철학)
    async def mock_core_search_kdc(query, limit=5):
        return [
            {
                "title": "정의란 무엇인가",
                "author": "마이클 샌델",
                "publisher": "김영사",
                "isbn": "9788934939603",
                "cover_url": "https://images.example.com/justice.jpg",
                "page_count": 400,
                "genre": "NONE",
                "kdc": "190",
                "subject": "서양철학",
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search_kdc)
    cand = {"title": "정의란 무엇인가", "author": "마이클 샌델", "reason": "정의와 윤리"}
    result = await _verify_single_candidate(cand, edition_intent=None)
    assert result is not None
    assert result["source"] == "CORE_API"
    assert result["genre"] == "PHILOSOPHY"


@pytest.mark.asyncio
async def test_verify_candidate_core_api_genre_none_when_no_genre_info(monkeypatch):
    """Verify genre remains None when neither Core API genre nor KDC is available."""
    from app.infrastructure.core_api_client import get_core_api_client

    core_client = get_core_api_client()

    async def mock_core_search_no_genre(query, limit=5):
        return [
            {
                "title": "미지의 책",
                "author": "알 수 없음",
                "publisher": "독립출판",
                "isbn": "9788937460012",  # Valid ISBN
                "cover_url": "https://images.example.com/unknown.jpg",
                "page_count": 100,
                "genre": None,
                "kdc": None,
            }
        ]

    monkeypatch.setattr(core_client, "search_books", mock_core_search_no_genre)
    cand = {"title": "미지의 책", "author": "알 수 없음", "reason": "새로운 시도"}
    result = await _verify_single_candidate(cand, edition_intent=None)
    assert result is not None
    assert result["source"] == "CORE_API"
    assert result["genre"] is None


@pytest.mark.asyncio
async def test_core_api_client_search_books_preserves_genre_and_kdc(monkeypatch):
    """Verify CoreApiClient.search_books preserves genre, kdc, and subject fields from Core API response."""
    from unittest.mock import AsyncMock, MagicMock

    from app.infrastructure.core_api_client import CoreApiClient

    client = CoreApiClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "bookId": "book-123",
                "title": "데미안",
                "author": "헤르만 헤세",
                "publisher": "민음사",
                "isbn": "9788937460012",
                "coverUrl": "https://images.example.com/cover.jpg",
                "totalPages": 240,
                "genre": "LITERATURE",
                "kdc": "853",
                "subject": "소설",
            }
        ]
    }

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    async def mock_get_client():
        return mock_http_client

    monkeypatch.setattr(client, "_get_client", mock_get_client)

    results = await client.search_books("데미안")
    assert len(results) == 1
    item = results[0]
    assert item["genre"] == "LITERATURE"
    assert item["kdc"] == "853"
    assert item["subject"] == "소설"
    assert item["page_count"] == 240
    assert item["cover_url"] == "https://images.example.com/cover.jpg"
