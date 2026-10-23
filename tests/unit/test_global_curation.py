"""Unit tests for Phase 70-6: Global book curation, Google Books support, and author matching."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.graph.curator_node import (
    _is_matching_author,
    _verify_single_candidate,
)
from app.infrastructure.core_api_client import CoreApiClient
from app.infrastructure.national_library_client import map_english_category_to_genre


@pytest.fixture(autouse=True)
def disable_biblio_cache():
    """Disable biblio Redis cache for unit tests to avoid cross-test pollution."""
    with (
        patch(
            "app.domain.graph.curator_node.get_cached_biblio",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.domain.graph.curator_node.set_cached_biblio",
            new_callable=AsyncMock,
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# 1. Core API search_books data_source preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_core_api_search_books_preserves_data_source():
    """Verify search_books extracts dataSource or data_source, falling back to YES24."""
    client = CoreApiClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "bookId": "101",
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "isbn": "9780132350884",
                "dataSource": "GOOGLE",
            },
            {
                "book_id": "102",
                "title": "데미안",
                "author": "헤르만 헤세",
                "isbn": "9788937460449",
                "data_source": "YES24",
            },
            {
                "book_id": "103",
                "title": "미상 도서",
                "author": "미상",
                "isbn": "9788900000000",
                # dataSource and data_source both omitted
            },
        ]
    }

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch.object(client, "_get_client", new_callable=AsyncMock, return_value=mock_http_client):
        results = await client.search_books("test query")

    assert len(results) == 3
    assert results[0]["data_source"] == "GOOGLE"
    assert results[1]["data_source"] == "YES24"
    assert results[2]["data_source"] == "YES24"


# ---------------------------------------------------------------------------
# 2. English Category to Genre Mapping
# ---------------------------------------------------------------------------


def test_map_english_category_to_genre():
    """Verify English category strings or keywords map to the 10 standard Genre Enums."""
    # Direct Category Mappings
    assert map_english_category_to_genre(category="Computers") == "TECHNOLOGY"
    assert map_english_category_to_genre(category="Technology & Engineering") == "TECHNOLOGY"
    assert map_english_category_to_genre(category="Fiction") == "LITERATURE"
    assert map_english_category_to_genre(category="Juvenile Fiction") == "LITERATURE"
    assert map_english_category_to_genre(category="Poetry") == "LITERATURE"
    assert map_english_category_to_genre(category="Philosophy") == "PHILOSOPHY"
    assert map_english_category_to_genre(category="Psychology") == "PHILOSOPHY"
    assert map_english_category_to_genre(category="Business & Economics") == "SOCIAL_SCIENCE"
    assert map_english_category_to_genre(category="Science") == "NATURAL_SCIENCE"
    assert map_english_category_to_genre(category="Mathematics") == "NATURAL_SCIENCE"
    assert map_english_category_to_genre(category="Art") == "ARTS"
    assert map_english_category_to_genre(category="Music") == "ARTS"
    assert map_english_category_to_genre(category="Foreign Language Study") == "LANGUAGE"
    assert map_english_category_to_genre(category="History") == "HISTORY"
    assert map_english_category_to_genre(category="Biography & Autobiography") == "HISTORY"
    assert map_english_category_to_genre(category="Religion") == "RELIGION"

    # Fallback via Title / Description Keywords
    assert (
        map_english_category_to_genre(
            category="",
            title="Clean Architecture",
            desc="A Craftsman's Guide to Software Structure and Design",
        )
        == "TECHNOLOGY"
    )
    assert (
        map_english_category_to_genre(
            category="",
            title="The Great Gatsby",
            desc="A classic novel depicting the Jazz Age in America",
        )
        == "LITERATURE"
    )

    # General Fallback
    assert (
        map_english_category_to_genre(
            category="Miscellaneous",
            title="Unknown Topic",
            desc="Random notes without domain words",
        )
        == "GENERAL"
    )


# ---------------------------------------------------------------------------
# 3. Western Author Matching with Initials / Middle Names
# ---------------------------------------------------------------------------


def test_author_matching_western_names_with_initials():
    """Verify Western author matching supports initials, middle names, and inversions."""
    # Middle initial abbreviation
    assert _is_matching_author("Robert C. Martin", "Robert Cecil Martin") is True
    assert _is_matching_author("Robert Cecil Martin", "Robert C. Martin") is True

    # Inverted name order with initial
    assert _is_matching_author("Martin, Robert C.", "Robert C. Martin") is True
    assert _is_matching_author("Martin, Robert Cecil", "Robert C. Martin") is True

    # Multiple initials
    assert _is_matching_author("J. K. Rowling", "Joanne Kathleen Rowling") is True
    assert _is_matching_author("Rowling, J. K.", "Joanne Kathleen Rowling") is True

    # Two-token inversion
    assert _is_matching_author("George Orwell", "Orwell, George") is True

    # Middle name omission
    assert _is_matching_author("Robert Martin", "Robert Cecil Martin") is True


def test_author_matching_rejects_single_surname_and_mismatched_names():
    """Verify conservative matching rejects single surname and differing given names."""
    # Single surname match MUST be rejected (False Positive guard)
    assert _is_matching_author("Martin", "Robert C. Martin") is False
    assert _is_matching_author("Smith", "John Smith") is False

    # Different given names with same surname MUST be rejected
    assert _is_matching_author("John Martin", "Robert Martin") is False
    assert _is_matching_author("Stephen King", "Martin King") is False


def test_author_matching_asian_names_strictness():
    """Verify Asian short names retain strict exact match without set confusion."""
    # Exact match
    assert _is_matching_author("김영하", "김영하") is True

    # Anagram / character rearrangement MUST be rejected
    assert _is_matching_author("김영하", "김하영") is False

    # Substring match without delimiter MUST be rejected
    assert _is_matching_author("이민호", "이민") is False

    # Role suffix stripping
    assert _is_matching_author("한강", "한강 지음") is True
    assert _is_matching_author("헤르만 헤세 저", "헤르만 헤세") is True


# ---------------------------------------------------------------------------
# 4. Google Books Candidate Verification (Track A & Track B)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_candidate_google_books_track_a_valid_isbn():
    """Verify Google Books candidate with valid ISBN-13 succeeds via Track A."""
    cand: Dict[str, Any] = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "reason": "애자일 소프트웨어 장인 정신을 일깨우는 명저",
        "era": "classic",
    }

    mock_core_items = [
        {
            "book_id": "google_101",
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "publisher": "Prentice Hall",
            "isbn": "9780132350884",  # Valid ISBN-13
            "genre": None,
            "kdc": None,
            "subject": "Computers",
            "cover_url": "https://books.google.com/covers/cleancode.jpg",
            "page_count": 464,
            "description": "Even bad code can function. But if code isn't clean, it can bring a development organization to its knees.",
            "data_source": "GOOGLE",
        }
    ]

    mock_core_client = AsyncMock()
    mock_core_client.search_books.return_value = mock_core_items

    with (
        patch(
            "app.domain.graph.curator_node.get_core_api_client",
            return_value=mock_core_client,
        ),
        patch("app.domain.graph.curator_node.get_national_library_client") as mock_get_nl,
    ):
        result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert result is not None
    assert result["verified"] is True
    assert result["isbn"] == "9780132350884"
    assert result["source"] == "CORE_API_GOOGLE"
    assert result["genre"] == "TECHNOLOGY"  # mapped from subject='Computers'
    assert result["publisher"] == "Prentice Hall"
    # National Library must NOT be called for verified Core API items
    mock_get_nl.assert_not_called()


@pytest.mark.asyncio
async def test_verify_candidate_google_books_track_b_missing_isbn():
    """[내부 단위 검증] Agent 서지 검증기에 ISBN 결측 Mock 도서 주입 시 Track B 분기 동작 검증.

    주의: 실환경 Core API의 Google Books 경로는 현재 유효 ISBN 필수 정책에 따라 ISBN 결측 도서를
    사전 Drop하므로 실환경에서는 본 경로로 진입하지 않습니다 (이번 베타는 Track A 유효 ISBN 도서만 지원).
    본 테스트는 실환경 Google Books 연동 성공 증거가 아니며, Agent 내부의 Track B 방어 분기
    (출판사/표지/쪽수 3대 조건 충족 시 수용, 불충족 시 거부)가 올바르게 작동하는지 확인하는 격리된 Mock 단위 테스트입니다.
    (국립중앙도서관 등 타 경로의 Track B 검증은 별도로 유효하게 보존됨)
    """
    cand: Dict[str, Any] = {
        "title": "Designing Data-Intensive Applications",
        "author": "Martin Kleppmann",
        "reason": "신뢰할 수 있고 확장 가능한 분산 시스템을 구축하는 지침서",
        "era": "classic",
    }

    # Case 1: Track B satisfied (publisher >= 2, valid http cover, page_count > 0)
    mock_core_items_valid = [
        {
            "book_id": "google_102",
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "publisher": "O'Reilly Media",
            "isbn": None,  # Missing ISBN
            "genre": None,
            "kdc": None,
            "subject": "Computers",
            "cover_url": "https://books.google.com/covers/ddia.jpg",
            "page_count": 616,
            "description": "The big ideas behind reliable, scalable, and maintainable systems.",
            "data_source": "GOOGLE",
        }
    ]

    mock_core_client = AsyncMock()
    mock_core_client.search_books.return_value = mock_core_items_valid

    with (
        patch(
            "app.domain.graph.curator_node.get_core_api_client",
            return_value=mock_core_client,
        ),
        patch("app.domain.graph.curator_node.get_national_library_client") as mock_get_nl,
    ):
        result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert result is not None
    assert result["verified"] is True
    assert result["isbn"] == ""
    assert result["source"] == "CORE_API_GOOGLE"
    assert result["genre"] == "TECHNOLOGY"
    mock_get_nl.assert_not_called()

    # Case 2: Track B fails due to page_count == 0
    mock_core_items_invalid = [
        {
            "book_id": "google_103",
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "publisher": "O'Reilly Media",
            "isbn": None,
            "cover_url": "https://books.google.com/covers/ddia.jpg",
            "page_count": 0,  # Invalid page count
            "data_source": "GOOGLE",
        }
    ]
    mock_core_client.search_books.return_value = mock_core_items_invalid
    mock_nl_client = AsyncMock()
    mock_nl_client.search_book.return_value = None

    with (
        patch(
            "app.domain.graph.curator_node.get_core_api_client",
            return_value=mock_core_client,
        ),
        patch(
            "app.domain.graph.curator_node.get_national_library_client",
            return_value=mock_nl_client,
        ),
    ):
        failed_result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert failed_result is None


@pytest.mark.asyncio
async def test_verify_candidate_google_books_invalid_isbn_rejected():
    """Verify candidate with checksum-invalid ISBN is strictly rejected."""
    cand: Dict[str, Any] = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "reason": "소프트웨어 장인 정신",
        "era": "classic",
    }

    mock_core_items = [
        {
            "book_id": "google_104",
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "publisher": "Prentice Hall",
            "isbn": "9780132350880",  # Invalid checksum
            "cover_url": "https://books.google.com/covers/cleancode.jpg",
            "page_count": 464,
            "data_source": "GOOGLE",
        }
    ]

    mock_core_client = AsyncMock()
    mock_core_client.search_books.return_value = mock_core_items
    mock_nl_client = AsyncMock()
    mock_nl_client.search_book.return_value = None

    with (
        patch(
            "app.domain.graph.curator_node.get_core_api_client",
            return_value=mock_core_client,
        ),
        patch(
            "app.domain.graph.curator_node.get_national_library_client",
            return_value=mock_nl_client,
        ),
    ):
        result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert result is None


# ---------------------------------------------------------------------------
# 5. Edition Intent ORIGINAL with English Book
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edition_intent_original_accepts_pure_english_book():
    """Verify edition_intent='ORIGINAL' accepts pure English books without Korean keywords."""
    cand: Dict[str, Any] = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "reason": "원서 추천",
        "era": "classic",
    }

    mock_core_items = [
        {
            "book_id": "google_105",
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "publisher": "Prentice Hall",
            "isbn": "9780132350884",
            "genre": None,
            "subject": "Computers",
            "cover_url": "https://books.google.com/covers/cleancode.jpg",
            "page_count": 464,
            # No Korean words like '원서' or '영문' in description
            "description": "A Handbook of Agile Software Craftsmanship.",
            "data_source": "GOOGLE",
        }
    ]

    mock_core_client = AsyncMock()
    mock_core_client.search_books.return_value = mock_core_items

    with patch(
        "app.domain.graph.curator_node.get_core_api_client",
        return_value=mock_core_client,
    ):
        result = await _verify_single_candidate(cand, edition_intent="ORIGINAL")

    assert result is not None
    assert result["verified"] is True
    assert result["source"] == "CORE_API_GOOGLE"


# ---------------------------------------------------------------------------
# 6. Domestic Books Regression Unaffected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_domestic_book_verification_regression_unaffected():
    """Verify domestic Korean book verification path (YES24 & National Library) remains 100% intact."""
    cand: Dict[str, Any] = {
        "title": "데미안",
        "author": "헤르만 헤세",
        "reason": "자아를 찾는 성장 소설",
        "era": "classic",
    }

    # 1. Domestic Core API item (YES24 with KDC)
    mock_core_items = [
        {
            "book_id": "yes24_101",
            "title": "데미안",
            "author": "헤르만 헤세",
            "publisher": "민음사",
            "isbn": "9788937460449",
            "genre": None,
            "kdc": "813.6",
            "subject": "문학",
            "cover_url": "https://image.yes24.com/demian.jpg",
            "page_count": 240,
            "description": "내 속에서 솟아 나오려는 것, 바로 그것을 나는 살아보려 했다.",
            "data_source": "YES24",
        }
    ]

    mock_core_client = AsyncMock()
    mock_core_client.search_books.return_value = mock_core_items

    with patch(
        "app.domain.graph.curator_node.get_core_api_client",
        return_value=mock_core_client,
    ):
        result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert result is not None
    assert result["verified"] is True
    assert result["source"] == "CORE_API"
    assert result["genre"] == "LITERATURE"  # Mapped from KDC 813.6
    assert result["isbn"] == "9788937460449"

    # 2. National Library fallback when Core API returns empty
    mock_core_client_empty = AsyncMock()
    mock_core_client_empty.search_books.return_value = []

    mock_nl_client = AsyncMock()
    mock_nl_client.search_book.return_value = {
        "title": "데미안",
        "author": "헤르만 헤세",
        "publisher": "민음사",
        "isbn": "9788937460449",
        "genre": "LITERATURE",
        "cover_url": "https://nl.go.kr/demian.jpg",
        "page_count": 240,
        "description": "국립중앙도서관 정식 서지",
    }

    with (
        patch(
            "app.domain.graph.curator_node.get_core_api_client",
            return_value=mock_core_client_empty,
        ),
        patch(
            "app.domain.graph.curator_node.get_national_library_client",
            return_value=mock_nl_client,
        ),
    ):
        nl_result = await _verify_single_candidate(cand, edition_intent="GENERAL")

    assert nl_result is not None
    assert nl_result["verified"] is True
    assert nl_result["source"] == "NATIONAL_LIBRARY"
    assert nl_result["genre"] == "LITERATURE"
