"""Book Curator Sub-Agent node: Emotion/weather reasoning + National Library bibliography verification."""

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
오직 주어진 사용자의 감정, 상황, 날씨, 독서 취향을 차분하고 객관적으로 분석하여 가장 어울리는 실존 한국어 도서 2~3권을 엄선합니다.

[출력 형식]
반드시 다음 JSON 배열 형식으로만 응답해야 하며, 다른 어떠한 마크다운이나 잡담을 붙이지 마세요:
[
  {"title": "책제목1", "author": "저자1", "reason": "추천 사유 (한 줄 요약)"},
  {"title": "책제목2", "author": "저자2", "reason": "추천 사유 (한 줄 요약)"}
]
"""


async def book_curator_node(state: AgentState) -> Dict[str, Any]:
    """Analyze context, generate book candidates with low temperature, and verify via National Library."""
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

    # 1. Use low-temperature LLM reasoning to extract optimal book candidates
    gemini_key = settings.gemini_api_key.strip()
    openai_key = settings.openai_api_key.strip()
    llm: Any = None

    if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=gemini_key,
                temperature=0.1,
            )
        except Exception as e:
            logger.warning("Failed to initialize Gemini for curator (%s).", e)

    if not llm and openai_key and not openai_key.startswith("your_") and len(openai_key) > 10:
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=SecretStr(openai_key),
                temperature=0.1,
            )
        except Exception as e:
            logger.warning("Failed to initialize OpenAI for curator (%s).", e)

    if llm:
        try:
            prompt = [
                SystemMessage(content=CURATOR_SYSTEM_PROMPT),
                HumanMessage(
                    content=f"다음 컨텍스트와 추천 요청을 분석하여 최적의 도서 2~3권을 추천 JSON으로 반환해주세요:\n\n{context_desc}"
                ),
            ]
            response = await llm.ainvoke(prompt)
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
                            }
                        )
        except Exception as e:
            logger.warning(
                "Curator LLM candidate extraction failed (%s). Using fallback catalog.", e
            )

    # Deterministic fallback candidates if LLM extraction returned empty
    if not candidates:
        if "비" in curator_request or "우울" in curator_request or "울적" in curator_request:
            candidates = [
                {
                    "title": "바람이 분다 당신이 좋다",
                    "author": "이병률",
                    "reason": "비 오는 날 쓸쓸한 마음에 온기를 전하는 감성 산문집",
                },
                {
                    "title": "불편한 편의점",
                    "author": "김호연",
                    "reason": "고단한 일상과 상처를 포근하게 보듬어주는 힐링 소설",
                },
            ]
        elif "성장" in curator_request or "용기" in curator_request or "도전" in curator_request:
            candidates = [
                {
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "reason": "내면의 알을 깨고 진정한 자신을 마주하는 불멸의 고전",
                },
            ]
        else:
            candidates = [
                {
                    "title": "어린 왕자",
                    "author": "앙투안 드 생텍쥐페리",
                    "reason": "마음의 눈으로 본질을 바라보게 해주는 영혼의 쉼표",
                },
                {
                    "title": "불편한 편의점",
                    "author": "김호연",
                    "reason": "따스한 이웃들의 온정으로 일상의 피로를 씻어주는 이야기",
                },
            ]

    # 2. Verify all candidates against National Library of Korea bibliography API
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
                    "description": biblio.get("description", candidate.get("reason", "")),
                    "reason": candidate.get("reason", ""),
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
