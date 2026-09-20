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
    """사용자가 새로운 책, 소설, 에세이, 시, 인문학 등 독서 자료를 추천받거나 찾고자 하는 의도를 보일 때 반드시 호출하는 전용 도구입니다.

    호출해야 하는 경우:
    - 감정 상태, 위로, 동기부여 등 처한 상황에 어울리는 도서를 권해달라고 할 때 (예: '나 연수 떨어졌어.. 다시 일어날 수 있는 도서 있으면 추천해줄래?', '마음이 울적할 때 읽을 책')
    - 완곡하거나 탐색적인 독서 요청 (예: '요즘 읽을 만한 거 없을까?', '어떤 책 읽으면 좋을지 고민돼')
    - 특정 도서 지목/서재 등록/결과 카드 요청 (예: '《데미안》 추천해줘', '프로젝트 헤일메리 등록할래')
    - 베스트셀러, 신간, 테마별 도서 추천을 직접 원할 때

    호출하지 말아야 하는 경우:
    - '시간 있으면 이야기하자', '이거 해줄래?' 등 일상적인 대화나 단순 스몰톡
    - 이미 추천받은 도서에 대해 감상을 나누거나 질의응답을 이어갈 때
    - 내 서재에 있는 기존 책을 조회할 때 (이때는 search_my_library 호출)

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
