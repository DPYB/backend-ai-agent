from typing import List

from langchain_core.tools import BaseTool, tool

from app.domain.memory.debate_memory_tool import search_debate_memory
from app.domain.memory.my_library_tool import search_my_library
from app.domain.memory.rag_tool import search_scrap_memory
from app.domain.tools.search_books_tool import search_recent_books


@tool
def trigger_debate_conclude(reason: str) -> str:
    """사용자가 토론을 그만두거나, 피날레 및 마무리를 원하거나, 이제 끝내고자 하는 의도를 보일 때 호출하는 도구입니다.

    Args:
        reason: 사용자가 토론 종료 또는 마무리를 원한다고 판단한 이유나 맥락 요약.
    """
    return f"[토론 종료 요청 수락]: {reason}. 전문 도서 큐레이터에게 피날레 연계 추천을 의뢰합니다."


@tool
def request_book_curation(query: str) -> str:
    """사용자가 책 추천, 특정 도서 추천/서재 등록/카드 결과 요청, 또는 읽을 책 선정을 원할 때(예: '프로젝트 헤일메리 추천해줘', '결과로 보여줘', '이 책 등록할래', '읽을만한 책 찾아줘') 전문 큐레이터에게 국립중앙도서관 정식 서지 검증 도서 선정을 의뢰하는 도구입니다.

    Args:
        query: 사용자가 언급한 특정 도서명 또는 요청 사항, 취향, 관심 분야, 감정 상태 설명.
    """
    return f"[도서 큐레이션 요청 접수]: '{query}'에 어울리는 최적의 도서를 국립중앙도서관 정식 서지 검증 체인으로 엄선합니다."


# Universal tools accessible to librarian and debate persona agents
GENERIC_TOOLS: List[BaseTool] = [
    search_scrap_memory,
    search_debate_memory,
    search_recent_books,
    search_my_library,
    trigger_debate_conclude,
    request_book_curation,
]

__all__ = [
    "GENERIC_TOOLS",
    "search_scrap_memory",
    "search_debate_memory",
    "search_recent_books",
    "search_my_library",
    "trigger_debate_conclude",
    "request_book_curation",
]
