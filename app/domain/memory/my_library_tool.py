"""My Library (Bookshelf) tool for querying user's registered books and reading status."""

import logging
from typing import Optional

from langchain_core.tools import tool

from app.infrastructure.core_api_client import get_core_api_client

logger = logging.getLogger(__name__)


@tool("search_my_library")
async def search_my_library(member_id: str, status_filter: Optional[str] = None) -> str:
    """사용자가 서재(bookshelf)에 등록해 둔 책 목록과 독서 상태를 조회합니다.

    사용자가 현재 어떤 책을 읽고 있는지(READING), 어떤 책을 완독했는지(COMPLETED),
    어떤 책을 읽고 싶어 하는지(WISH) 파악하여 맞춤형 사서 대화나 토론을 나눌 때 호출합니다.

    Args:
        member_id: 사용자의 고유 식별자 (UUID)
        status_filter: 독서 상태 필터 ('READING', 'COMPLETED', 'WISH' 또는 None=전체)

    Returns:
        사용자의 서재 등록 도서 목록과 상태가 포함된 설명 텍스트
    """
    logger.info(
        "Querying bookshelf for member_id=%s with status_filter=%s",
        member_id,
        status_filter,
    )
    # Bypass for unauthenticated guest users
    if (
        not member_id
        or member_id in ("None", "guest", "undefined")
        or member_id.startswith("guest-")
    ):
        logger.info("Skipping search_my_library: Unauthenticated guest user.")
        return "현재 로그인하지 않은 게스트 상태이므로 개인 서재가 없습니다. 도서 추천이나 일반 독서 대화를 바로 진행합니다."

    try:
        client = get_core_api_client()
        bookshelf = await client.get_my_bookshelf(member_id=member_id)
        books = bookshelf.get("books", [])

        if status_filter:
            books = [b for b in books if b.get("status", "").upper() == status_filter.upper()]

        if not books:
            filter_desc = f"'{status_filter}' 상태의 " if status_filter else ""
            return f"사용자({member_id})의 서재에 {filter_desc}등록된 도서가 없습니다."

        status_map = {
            "READING": "📖 읽는 중",
            "COMPLETED": "✅ 완독함",
            "WISH": "⭐ 읽고 싶은 책",
        }

        results = []
        for i, book in enumerate(books, 1):
            title = book.get("title", "제목 미상")
            author = book.get("author", "저자 미상")
            st = status_map.get(book.get("status", ""), book.get("status", "상태 미정"))
            rating = f" (평점: {book['rating']}점)" if book.get("rating") else ""
            results.append(f"[{i}] <{title}> - {author} [{st}]{rating}")

        header = f"📚 사용자({member_id})의 서재 도서 목록 (총 {len(results)}권):"
        return header + "\n" + "\n".join(results)

    except Exception as e:
        logger.error("Error in search_my_library: %s", e)
        return f"내 서재 도서 조회 중 오류가 발생했습니다: {str(e)}"
