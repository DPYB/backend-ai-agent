"""Unit tests for flexible book curation and forced fallback elimination (Step 1).

Covers:
1. Default recommendation returns exactly 1 book.
2. Explicit 3 books request returns exactly 3 books.
3. Explicit 5 books request returns exactly 5 books.
4. Explicit 10 books request with only 4 verified returns exactly 4 books (no forced fallback).
5. 0 verified books returns empty list ([]) without fabricating classic fallbacks.
6. Body markdown titles/counts match recommended_books array (1~3 books header vs 4+ books numbered list).
"""

import re
from typing import Any, Dict, cast

import pytest
from langchain_core.messages import HumanMessage

from app.domain.graph.curator_node import (
    BookCandidate,
    CuratorResponse,
    assemble_curated_books,
    book_curator_node,
    parse_requested_book_count,
)
from app.domain.graph.nodes import _sanitize_persona_output, cat_node
from app.domain.graph.state import AgentState


def test_parse_requested_book_count():
    """Verify parse_requested_book_count accurately extracts requested numbers or applies defaults."""
    # 1. Default (generic requests)
    assert parse_requested_book_count("책 추천해줘") == 1
    assert parse_requested_book_count("위로가 되는 에세이 찾아줘") == 1
    assert parse_requested_book_count("") == 1
    assert parse_requested_book_count(None) == 1

    # 2. Arabic numerals
    assert parse_requested_book_count("1권 추천해줘") == 1
    assert parse_requested_book_count("3권 추천해줘") == 3
    assert parse_requested_book_count("5권 골라줘") == 5
    assert parse_requested_book_count("10권 알려줘") == 10
    assert parse_requested_book_count("20권 추천해줘") == 10  # capped at 10

    # 3. Korean numerals
    assert parse_requested_book_count("한 권만 추천해줘") == 1
    assert parse_requested_book_count("두 권 골라줘") == 2
    assert parse_requested_book_count("세 권 추천해줘") == 3
    assert parse_requested_book_count("다섯 권 알려줘") == 5
    assert parse_requested_book_count("열 권 추천해줘") == 10

    # 4. Exploratory keywords
    assert parse_requested_book_count("두세 권 추천해줘") == 3
    assert parse_requested_book_count("다양하게 비교해줘") == 3
    assert parse_requested_book_count("여러 권 골고루 추천해줘") == 3


def test_curator_response_schema_flexible_length():
    """Verify CuratorResponse accepts 1 to 10 recommendations."""
    candidate = BookCandidate(
        title="데미안",
        author="헤르만 헤세",
        reason="자아를 찾는 여정",
        era="classic",
    )

    # 1 book (default)
    res_1 = CuratorResponse(recommendations=[candidate])
    assert len(res_1.recommendations) == 1

    # 5 books
    res_5 = CuratorResponse(
        recommendations=[
            BookCandidate(title=f"도서_{i}", author=f"저자_{i}", reason="이유", era="classic")
            for i in range(5)
        ]
    )
    assert len(res_5.recommendations) == 5

    # 10 books (maximum)
    res_10 = CuratorResponse(
        recommendations=[
            BookCandidate(title=f"도서_{i}", author=f"저자_{i}", reason="이유", era="classic")
            for i in range(10)
        ]
    )
    assert len(res_10.recommendations) == 10


@pytest.mark.asyncio
async def test_default_recommendation_returns_exactly_one_book():
    """Test Case 1: Generic recommendation request defaults to exactly 1 book."""
    state = {
        "messages": [HumanMessage(content="마음을 달래줄 좋은 책 추천해줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "curator_request": "마음을 달래줄 좋은 책 추천해줘",
        "curated_books": None,
        "recommended_history": [],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    books = result["curated_books"]
    assert len(books) == 1
    assert books[0]["verified"] is True
    assert len(books[0]["isbn"]) == 13


@pytest.mark.asyncio
async def test_explicit_three_books_request():
    """Test Case 2: Explicit request for 3 books returns exactly 3 books."""
    state = {
        "messages": [HumanMessage(content="3권 추천해줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "curator_request": "3권 추천해줘",
        "curated_books": None,
        "recommended_history": [],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    books = result["curated_books"]
    assert len(books) == 3
    for b in books:
        assert b["verified"] is True
        assert len(b["isbn"]) == 13


@pytest.mark.asyncio
async def test_explicit_five_books_request():
    """Test Case 3: Explicit request for 5 books returns exactly 5 books."""
    state = {
        "messages": [HumanMessage(content="다섯 권 골라줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "curator_request": "다섯 권 골라줘",
        "curated_books": None,
        "recommended_history": [],
    }

    result = await book_curator_node(cast(AgentState, state))
    assert "curated_books" in result
    books = result["curated_books"]
    assert len(books) == 5
    for b in books:
        assert b["verified"] is True
        assert len(b["isbn"]) == 13


@pytest.mark.asyncio
async def test_explicit_ten_books_request_with_only_four_verified_returns_four_books():
    """Test Case 4: 10 books requested, but only 4 verified -> returns 4 books without forced fallback."""
    # When assemble_curated_books receives only 4 verified books out of 10 requested
    verified_4 = [
        {
            "title": f"검증도서_{i}",
            "author": f"저자_{i}",
            "isbn": f"97889000000{i:02d}",
            "publisher": "출판사",
            "verified": True,
            "era": "classic",
        }
        for i in range(1, 5)
    ]

    assembled = await assemble_curated_books(
        targeted=None,
        verified=verified_4,
        recommended_history=[],
        requested_count=10,
    )

    # Must return exactly 4 books, without fabricating 6 classic fallback books
    assert len(assembled) == 4
    for b in assembled:
        assert b["verified"] is True
        assert b.get("fallback") is not True


@pytest.mark.asyncio
async def test_zero_verified_books_returns_empty_list():
    """Test Case 5: 0 verified books -> returns empty list ([]) without forced fallback injection."""
    assembled = await assemble_curated_books(
        targeted=None,
        verified=[],
        recommended_history=[],
        requested_count=3,
    )
    assert assembled == []


def test_sanitize_persona_output_strips_fake_numbered_books_when_no_curated_books():
    """Verify _sanitize_persona_output strips fake numbered book cards when curated_books is empty."""
    fake_output = (
        "독자님께 어울리는 책들을 골라보았습니다.\n\n"
        "1. 《가짜도서1》 - 작가1: 정말 좋은 책입니다.\n"
        "2. 《가짜도서2》 - 작가2: 위로가 됩니다.\n\n"
        "즐거운 독서 되세요."
    )
    sanitized = _sanitize_persona_output(fake_output, curated_books=None, persona_id="CAT")
    # Numbered book lines must be removed to prevent frontend from triggering book cards
    assert "가짜도서1" not in sanitized
    assert "가짜도서2" not in sanitized
    assert "1. 《" not in sanitized


def test_sanitize_persona_output_validates_numbered_books_with_curated_books():
    """Verify _sanitize_persona_output retains verified numbered books and strips fabricated ones."""
    curated = [
        {"title": "데미안", "author": "헤르만 헤세", "verified": True},
        {"title": "코스모스", "author": "칼 세이건", "verified": True},
    ]

    llm_output = (
        "독자님께 추천해 드리는 도서 목록입니다냥.\n\n"
        "1. 《데미안》 - 헤르만 헤세: 참된 자아를 마주하는 이야기\n"
        "2. 《코스모스》 - 칼 세이건: 광대한 우주의 신비\n"
        "3. 《완전날조된책》 - 미상: 존재하지 않는 책\n\n"
        "마음의 평온을 찾으시길 바란다냥."
    )

    sanitized = _sanitize_persona_output(llm_output, curated_books=curated, persona_id="CAT")
    assert "1. 《데미안》" in sanitized
    assert "2. 《코스모스》" in sanitized
    assert "완전날조된책" not in sanitized


@pytest.mark.asyncio
async def test_body_markdown_titles_and_count_match_recommended_books_array():
    """Test Case 6: Verify body markdown titles and counts match recommended_books array exactly."""
    # Sub-case A: 1 book (uses ### 📖 {도서명} heading format)
    state_1: Dict[str, Any] = {
        "messages": [HumanMessage(content="한 권만 추천해줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "curator_request": None,
        "curated_books": [
            {
                "title": "데미안",
                "author": "헤르만 헤세",
                "publisher": "민음사",
                "isbn": "9788937460449",
                "verified": True,
                "reason": "자아를 찾는 여정",
            }
        ],
        "recommended_history": [],
    }

    result_1 = await cat_node(cast(AgentState, state_1))
    last_msg_1 = str(result_1["messages"][-1].content)
    curated_1 = result_1["curated_books"]
    assert len(curated_1) == 1

    # Extract ### 📖 titles from body
    headings_1 = re.findall(r"###\s*📖\s*([^\n\r]+)", last_msg_1)
    assert len(headings_1) == 1
    assert "데미안" in headings_1[0]

    # Sub-case B: 5 books (4+ books use 1. 《도서명》 - 저자 numbered list format)
    curated_5 = [
        {
            "title": f"도서_{i}",
            "author": f"저자_{i}",
            "publisher": "출판사",
            "isbn": f"97889000000{i:02d}",
            "verified": True,
            "reason": f"추천 이유 {i}",
        }
        for i in range(1, 6)
    ]
    state_5: Dict[str, Any] = {
        "messages": [HumanMessage(content="5권 추천해줘")],
        "member_id": "test-member",
        "active_persona": "CAT",
        "librarian_name": "블루",
        "mode": "LIBRARIAN",
        "curator_request": None,
        "curated_books": curated_5,
        "recommended_history": [],
    }

    result_5 = await cat_node(cast(AgentState, state_5))
    last_msg_5 = str(result_5["messages"][-1].content)
    curated_res_5 = result_5["curated_books"]
    assert len(curated_res_5) == 5

    # Extract numbered list titles using frontend regex: ^\d+\.\s*(?:\*\*)?[『《]([^』》]+)[』》]
    numbered_titles = re.findall(r"^\d+\.\s*(?:\*\*)?[『《]([^』》]+)[』》]", last_msg_5, re.M)
    assert len(numbered_titles) == 5
    for i, t in enumerate(numbered_titles, 1):
        assert t == f"도서_{i}"
        assert any(b["title"] == t for b in curated_res_5)
