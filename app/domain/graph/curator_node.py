"""Book Curator Sub-Agent node: Emotion/weather reasoning + National Library bibliography verification.

Hybrid Curation Principle:
  - All recommendations produce a pair:
      [1 recent trending book (2024-2026)] + [1 timeless classic/steady-seller]
  - LLM generates 3-4 raw candidates → 4-stage National Library validation chain → top 2 returned
"""

import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.domain.graph.state import AgentState
from app.infrastructure.national_library_client import get_national_library_client

logger = logging.getLogger(__name__)

CURATOR_SYSTEM_PROMPT = """당신은 'DPYB 도서 큐레이션 전문 분석관'입니다.
당신에게는 어떠한 감성적인 페르소나나 캐릭터 연기도 요구되지 않습니다.
오직 주어진 사용자의 감정, 상황, 날씨, 독서 취향을 차분하고 객관적으로 분석하여 최적의 실존 한국어 도서를 엄선합니다.

[신구(新舊) 하이브리드 추천 원칙 — 반드시 준수]
모든 추천은 다음 구성을 따릅니다:
  - 1권 (최신): 2023년 이후 출간된 화제의 신간 또는 최근 베스트셀러 (트렌드 반영)
  - 1권 (고전): 시대를 초월한 스테디셀러 또는 세계 명작 (깊이와 내구성)
총 2~3권 후보를 생성하되, 신간 1권 + 스테디셀러 1권의 균형을 반드시 맞추세요.

[출력 형식 — 반드시 준수]
다음 JSON 배열 형식으로만 응답하세요. 마크다운 코드블록이나 잡담을 붙이지 마세요:
[
  {"title": "최신 신간 제목", "author": "저자명", "reason": "추천 사유 (한 줄)", "era": "recent"},
  {"title": "고전/스테디셀러 제목", "author": "저자명", "reason": "추천 사유 (한 줄)", "era": "classic"}
]

[주의사항]
- 실제로 출판된 실존하는 도서만 추천하세요. 지어낸 제목 절대 금지.
- 도서명은 정확한 한국어 출판 제목으로 작성하세요.
- 제목에 《》 꺽쇠는 포함하지 마세요 (순수 제목만).
"""


async def book_curator_node(state: AgentState) -> Dict[str, Any]:
    """Analyze context, generate hybrid book candidates, and verify via 4-stage National Library chain."""
    logger.info("book_curator_node invoked for member_id=%s", state.get("member_id"))

    curator_request = state.get("curator_request") or ""
    messages = state.get("messages", [])

    # If no explicit curator_request was provided, extract context from recent user messages
    if not curator_request:
        for msg in reversed(messages):
            if hasattr(msg, "content") and str(msg.content):
                curator_request = str(msg.content)
                break

    weather_context = state.get("weather_context")
    context_desc = f"분석할 사용자 요청: {curator_request}"
    if weather_context:
        context_desc += f"\n현재 사용자 위치의 실시간 날씨: {weather_context}"

    candidates: List[Dict[str, str]] = []

    # Fast mock in test environment
    if getattr(settings, "app_env", "") == "test":
        candidates = [
            {
                "title": "데미안",
                "author": "헤르만 헤세",
                "reason": "자아를 찾는 여정",
                "era": "classic",
            },
            {
                "title": "불편한 편의점",
                "author": "김호연",
                "reason": "따스한 일상의 위로",
                "era": "recent",
            },
        ]

    # 1. Use low-temperature LLM reasoning to extract optimal book candidates (신구 하이브리드)
    gemini_key = settings.gemini_api_key.strip()
    gemini_fallback_key = getattr(settings, "gemini_fallback_api_key", "").strip()
    openai_key = settings.openai_api_key.strip()
    light_model = getattr(settings, "gemini_light_model", "gemini-3.1-flash-lite")

    llms_to_try: List[Any] = []

    # 1. Primary: Gemini 3.1 Flash Lite with Primary Key (Preserve 3.5 quota for chat)
    if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llms_to_try.append(
                ChatGoogleGenerativeAI(
                    model=light_model,
                    google_api_key=gemini_key,
                    temperature=0.1,
                )
            )
        except Exception as e:
            logger.warning("Failed to initialize primary Gemini light for curator (%s).", e)

    # 2. Secondary: Gemini 3.1 Flash Lite with Fallback Key
    if (
        gemini_fallback_key
        and not gemini_fallback_key.startswith("your_")
        and len(gemini_fallback_key) > 10
    ):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llms_to_try.append(
                ChatGoogleGenerativeAI(
                    model=light_model,
                    google_api_key=gemini_fallback_key,
                    temperature=0.1,
                )
            )
        except Exception as e:
            logger.warning("Failed to initialize fallback Gemini light for curator (%s).", e)

    # 3. Tertiary: Gemini 3.5 Flash Lite
    if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llms_to_try.append(
                ChatGoogleGenerativeAI(
                    model=settings.gemini_model,
                    google_api_key=gemini_key,
                    temperature=0.1,
                )
            )
        except Exception as e:
            logger.warning("Failed to initialize Gemini 3.5 for curator (%s).", e)

    # 4. Fallback: OpenAI gpt-4o-mini
    if openai_key and not openai_key.startswith("your_") and len(openai_key) > 10:
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            llms_to_try.append(
                ChatOpenAI(
                    model=settings.openai_model,
                    api_key=SecretStr(openai_key),
                    temperature=0.1,
                )
            )
        except Exception as e:
            logger.warning("Failed to initialize OpenAI for curator (%s).", e)

    response = None
    if not candidates:
        for candidate_llm in llms_to_try:
            try:
                prompt = [
                    SystemMessage(content=CURATOR_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "다음 컨텍스트와 추천 요청을 분석하여 "
                            "신간 1권 + 고전/스테디셀러 1권으로 구성된 최적의 도서 추천 JSON을 반환해주세요:\n\n"
                            f"{context_desc}"
                        )
                    ),
                ]
                response = await candidate_llm.ainvoke(prompt)
                if response:
                    break
            except Exception as e:
                logger.warning("Curator candidate LLM call failed (%s). Trying next candidate.", e)

    if response:
        try:
            from app.domain.graph.nodes import extract_message_text

            content = extract_message_text(response.content).strip()

            # Clean json codeblocks if any
            clean_json = re.sub(r"^```(?:json)?\s*", "", content, flags=re.MULTILINE)
            clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE).strip()

            parsed = json.loads(clean_json)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "title" in item:
                        candidates.append(
                            {
                                "title": str(item.get("title", "")),
                                "author": str(item.get("author", "")),
                                "reason": str(item.get("reason", "")),
                                "era": str(item.get("era", "classic")),
                            }
                        )
        except Exception as e:
            logger.warning(
                "Curator LLM candidate extraction failed (%s). Using fallback catalog.", e
            )

    # Deterministic hybrid fallback candidates if LLM extraction returned empty
    if not candidates:
        if "비" in curator_request or "우울" in curator_request or "울적" in curator_request:
            candidates = [
                {
                    "title": "죽고 싶지만 떡볶이는 먹고 싶어",
                    "author": "백세희",
                    "reason": "가벼운 우울과 일상의 온기를 함께 담은 진솔한 기록",
                    "era": "recent",
                },
                {
                    "title": "바람이 분다 당신이 좋다",
                    "author": "이병률",
                    "reason": "쓸쓸한 감성에 울림을 주는 감성 산문의 고전",
                    "era": "classic",
                },
            ]
        elif "성장" in curator_request or "용기" in curator_request or "도전" in curator_request:
            candidates = [
                {
                    "title": "아몬드",
                    "author": "손원평",
                    "reason": "감정을 찾아가는 특별한 성장 이야기",
                    "era": "recent",
                },
                {
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "reason": "내면의 알을 깨고 진정한 자신을 마주하는 불멸의 고전",
                    "era": "classic",
                },
            ]
        elif (
            "토론" in curator_request or "피날레" in curator_request or "마무리" in curator_request
        ):
            candidates = [
                {
                    "title": "밝은 밤",
                    "author": "최은영",
                    "reason": "삶의 연대와 치유를 섬세하게 담은 한국 현대 소설",
                    "era": "recent",
                },
                {
                    "title": "소크라테스 익스프레스",
                    "author": "에릭 와이너",
                    "reason": "토론의 여운을 철학적 사유로 확장해 주는 인문 고전",
                    "era": "classic",
                },
            ]
        else:
            candidates = [
                {
                    "title": "달러구트 꿈 백화점",
                    "author": "이미예",
                    "reason": "몽환적이고 따스한 판타지로 일상을 환기시키는 최근 화제작",
                    "era": "recent",
                },
                {
                    "title": "어린 왕자",
                    "author": "앙투안 드 생텍쥐페리",
                    "reason": "마음의 눈으로 본질을 바라보게 해주는 영혼의 쉼표",
                    "era": "classic",
                },
            ]

    # 2. Verify all candidates against National Library 4-stage validation chain
    nl_client = get_national_library_client()
    verified_books: List[Dict[str, Any]] = []

    for candidate in candidates[:3]:
        biblio = await nl_client.search_book(
            title=candidate["title"],
            author=candidate.get("author", ""),
        )
        if biblio:
            verified_books.append(
                {
                    "title": biblio.get("title", candidate["title"]),
                    "author": biblio.get("author", candidate.get("author", "")),
                    "publisher": biblio.get("publisher", ""),
                    "isbn": biblio.get("isbn", ""),
                    "cover_url": biblio.get("cover_url", ""),
                    "page_count": biblio.get("page_count"),
                    "genre": biblio.get("genre"),
                    "description": biblio.get("description", candidate.get("reason", "")),
                    "reason": candidate.get("reason", ""),
                    "era": candidate.get("era", "classic"),
                    "verified": True,
                    "source": biblio.get("source", "NATIONAL_LIBRARY"),
                }
            )

    logger.info("Curator successfully verified %d books.", len(verified_books))

    # Return curated_books and clear curator_request so master persona takes back control
    return {
        "curated_books": verified_books,
        "curator_request": None,
    }
