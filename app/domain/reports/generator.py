"""Librarian Persona LLM Generator for Monthly Reading Report (06. AI Analysis & 07. Prescription)."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.domain.reports.keyword_extractor import extract_monthly_debate_keywords
from app.infrastructure.national_library_client import get_national_library_client
from app.schemas.report import (
    AiAnalysis,
    GenreBalanceItem,
    GenrePreferenceItem,
    LibrarianReportInfo,
    MonthlyOverview,
    MonthlyReportResponse,
    Prescription,
    ReadingBalance,
    ReadingHabits,
    ReadingPreferences,
    ReadingTraces,
    RecommendedBookItem,
    WeatherPreferenceItem,
)

logger = logging.getLogger(__name__)


def _get_persona_prompt_and_ending(
    librarian_type: str, librarian_name: str
) -> Tuple[str, str, str]:
    """Return persona tone guidance, ending style, and formatted display name."""
    norm_type = str(librarian_type).upper()
    if norm_type in ("CAT", "RUSSIAN_BLUE", "BLUE"):
        ending = "~냥"
        char_desc = "러시안 블루 고양이, 차분하고 논리적인 INTJ 사색가"
        sample_sentence = "당신의 독서는 겉으로 보이는 줄거리보다 그 안에 숨겨진 이유와 본질을 깊이 파고드는 경향을 보였다냥."
    elif norm_type in ("SHOEBILL", "STORK"):
        ending = "~두둥"
        char_desc = "넙적부리황새, 관찰력이 뛰어나고 원리와 쓸모를 중시하는 ISTP 실용가"
        sample_sentence = "복잡한 공상보다 직접 원리를 확인하고 삶에 적용할 수 있는 구체적인 지식을 찾아 나섰다두둥."
    elif norm_type in ("SEA_SLUG", "LIBRARIAN_3"):
        ending = "~누누"
        char_desc = "갯민숭달팽이, 감수성이 풍부하고 여운과 온기를 사랑하는 INFP 감성가"
        sample_sentence = (
            "문장 하나하나가 마음에 잔잔한 파도처럼 번지는 이야기들에 오래 머물렀어누누..."
        )
    elif norm_type in ("GECKO", "LIBRARIAN_4"):
        ending = "~크크"
        char_desc = "게코 도마뱀, 사람과 사회, 다양한 문화와 관점에 관심이 많은 ENFJ 공감형 탐구자"
        sample_sentence = "사람들의 삶과 그들이 빚어낸 역사와 사회를 다각도로 들여다보는 따스한 시선이 돋보였다크크."
    else:
        ending = "~냥"
        char_desc = "다정한 사서"
        sample_sentence = "한 달간 책과 함께 깊은 성장의 시간을 보냈다냥."

    return char_desc, ending, sample_sentence


def _build_llm_report_prompt(
    librarian_type: str,
    librarian_name: str,
    stats_data: Dict[str, Any],
    debate_keywords: List[str],
) -> Tuple[str, str]:
    """Construct system and human prompt for Gemini LLM report generation."""
    char_desc, ending, sample_sentence = _get_persona_prompt_and_ending(
        librarian_type, librarian_name
    )

    system_prompt = f"""당신은 'DPYB(Don't Paw-get Your Book)'의 전담 사서 '{librarian_name}'({char_desc})입니다.
한 달간 사용자의 독서 통계와 기록을 분석하여 [06. AI가 발견한 나의 독서 성향]과 [07. 다음 달 독서 처방]을 작성하는 막중한 임무를 맡았습니다.

[사서 캐릭터 및 말투 지침]
- 사서 이름: '{librarian_name}'
- 말투 및 종결어미: 사서 페르소나에 걸맞은 어조를 유지하며, 종결어미 '{ending}'을 응답 문맥에 맞게 자연스럽게 1~2회 절제하여 사용하세요 (모든 문장에 남발 금지).
- 예시 톤: "{sample_sentence}"
- 06번과 07번 분석 조언 문장은 사용자의 독서 여정을 깊이 이해하고 응원하는 사서의 애정이 듬뿍 담겨야 합니다.

[출력 형식 필수 규칙]
반드시 다음 JSON 단일 객체 형식으로만 응답하세요 (어떠한 마크다운 코드블록 외 잡담 금지):
{{
  "readerType": "독서가 유형 네이밍 (예: '새벽의 몰입형 탐구자', '주말의 감성 사색가')",
  "summary": "독서 성향 분석 문장 (2~3문장, 사서 페르소나 어투 적용, 시간대/날씨/장르/스크랩 결합)",
  "keyTraits": ["특징 태그1", "특징 태그2", "특징 태그3"],
  "recommendedGenre": "다음 달 도전 장르 (반드시 unreadGenres 중 1개 선택)",
  "suggestedGoalBooks": 4,
  "advice": "다음 달 독서 처방 조언 및 실천 가이드 (2문장 내외, 사서 어투 적용)",
  "recommendedBooks": [
    {{"title": "추천도서명1", "author": "저자1", "reason": "이 책을 처방한 사유 (한 줄)"}},
    {{"title": "추천도서명2", "author": "저자2", "reason": "이 책을 처방한 사유 (한 줄)"}}
  ]
}}
"""

    overview = stats_data.get("overview", {})
    habits = stats_data.get("habits", {})
    prefs = stats_data.get("preferences", {})
    balance = stats_data.get("balance", {})
    traces = stats_data.get("traces", {})

    unread_genres = balance.get("unreadGenres", balance.get("unread_genres", []))
    unread_genres_str = ", ".join(unread_genres) if unread_genres else "자연과학, 역사, 기술과학"

    total_sessions = habits.get("totalSessionCount", habits.get("total_session_count", 0))
    avg_session_min = habits.get(
        "avgSessionDurationMinutes", habits.get("avg_session_duration_minutes")
    )
    session_summary_str = f"{total_sessions}회"
    if avg_session_min is not None:
        session_summary_str += f" (1회 평균 집중 독서 시간: {avg_session_min:.1f}분)"

    context_summary = f"""
[회원의 이번 달 독서 통계 요약]
- 완독 권수: {overview.get("completedBooksCount", overview.get("completed_books_count", 0))}권
- 누적 페이지: {overview.get("totalPagesRead", overview.get("total_pages_read", 0))}쪽
- 총 독서 시간: {overview.get("totalDurationMinutes", overview.get("total_duration_minutes", 0))}분
- 독서 세션 횟수 및 평균: {session_summary_str}
- 목표 달성률: {overview.get("goalAchievementRate", overview.get("goal_achievement_rate", 0))}%
- 주 활동 요일/시간대: {habits.get("timeDistribution", habits.get("time_distribution", {}))}
- 날씨별 독서 분포: {habits.get("weatherDistribution", habits.get("weather_distribution", {}))}
- 선호 장르 분포: {[g.get("genreName") or g.get("genre_name") for g in prefs.get("topGenres", prefs.get("top_genres", []))]}
- 주요 주제 태그: {prefs.get("topSubjects", prefs.get("top_subjects", []))}
- 토론 대표 키워드: {debate_keywords}
- 장르 다양성 점수: {balance.get("diversityScore", balance.get("diversity_score", 50))}점 (편독 여부: {balance.get("isBiased", balance.get("is_biased", False))})
- 이번 달 읽지 않은 장르(미독서): [{unread_genres_str}]
- 인상 깊은 스크랩 도서: {[b.get("title") for b in traces.get("mostScrappedBooks", traces.get("most_scrapped_books", []))]}
"""
    human_prompt = f"다음 통계를 바탕으로 사서 '{librarian_name}'의 시선에서 [06. AI 분석]과 [07. 다음 달 처방]을 JSON으로 생성해 주세요:\n{context_summary}"
    return system_prompt, human_prompt


def _parse_llm_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robust JSON extraction from LLM response text."""
    if not raw_text:
        return None

    # Try direct parse
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    # Try markdown json block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Try finding outermost braces
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_text[start : end + 1])
        except Exception:
            pass

    return None


async def generate_ai_analysis_and_prescription(
    librarian_type: str,
    librarian_name: str,
    stats_data: Dict[str, Any],
    debate_keywords: List[str],
) -> Tuple[AiAnalysis, Prescription]:
    """Execute LLM call to synthesize 06. AiAnalysis and 07. Prescription with National Library verified books."""
    system_prompt, human_prompt = _build_llm_report_prompt(
        librarian_type, librarian_name, stats_data, debate_keywords
    )

    gemini_key = settings.gemini_api_key.strip()
    gemini_fallback_key = getattr(settings, "gemini_fallback_api_key", "").strip()
    openai_key = settings.openai_api_key.strip()
    raw_content: Optional[str] = None

    # Fast mock in test environment
    if getattr(settings, "app_env", "") == "test":
        raw_content = json.dumps(
            {
                "readerType": "사색하는 몰입형 독서가",
                "summary": "저녁 시간대에 문학과 철학 도서에 깊이 몰입하며 사색적인 독서 습관이 돋보였다냥.",
                "keyTraits": ["저녁 집중형", "인문/철학 선호"],
                "recommendedGenre": "자연과학",
                "suggestedGoalBooks": 4,
                "advice": "이번 달에는 자연과학 분야의 친절한 입문서 1권을 더해보면 좋겠다냥.",
                "recommendedBooks": [
                    {
                        "title": "코스모스",
                        "author": "칼 세이건",
                        "reason": "광대한 우주와 인간 실존 조망",
                    },
                    {
                        "title": "이기적 유전자",
                        "author": "리처드 도킨스",
                        "reason": "생명과 인간 본성에 대한 과학적 시각",
                    },
                ],
            }
        )

    # Candidates: (1) 3.5 Primary Key, (2) 3.5 Fallback Key, (3) 3.1 Light Model, (4) OpenAI
    candidate_cfgs: List[Dict[str, Any]] = []
    if not raw_content:
        if gemini_key and not gemini_key.startswith("your_") and len(gemini_key) > 10:
            candidate_cfgs.append(
                {"model": settings.gemini_model, "key": gemini_key, "provider": "gemini"}
            )
        if (
            gemini_fallback_key
            and not gemini_fallback_key.startswith("your_")
            and len(gemini_fallback_key) > 10
        ):
            candidate_cfgs.append(
                {"model": settings.gemini_model, "key": gemini_fallback_key, "provider": "gemini"}
            )
        light_key = gemini_key or gemini_fallback_key
        light_model = getattr(settings, "gemini_light_model", "gemini-3.1-flash-lite")
        if light_key and not light_key.startswith("your_") and len(light_key) > 10:
            candidate_cfgs.append({"model": light_model, "key": light_key, "provider": "gemini"})
        if openai_key and not openai_key.startswith("your_") and len(openai_key) > 10:
            candidate_cfgs.append(
                {"model": settings.openai_model, "key": openai_key, "provider": "openai"}
            )

        for cfg in candidate_cfgs:
            try:
                if cfg["provider"] == "gemini":
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    llm = ChatGoogleGenerativeAI(
                        model=cfg["model"],
                        google_api_key=cfg["key"],
                    )
                    response = await llm.ainvoke(
                        [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
                    )
                    if hasattr(response, "content") and response.content:
                        raw_content = str(response.content)
                        break
                elif cfg["provider"] == "openai":
                    from langchain_openai import ChatOpenAI
                    from pydantic import SecretStr

                    openai_llm: Any = ChatOpenAI(
                        model=cfg["model"],
                        api_key=SecretStr(cfg["key"]),
                        temperature=0.7,
                    )
                    response = await openai_llm.ainvoke(
                        [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
                    )
                    if hasattr(response, "content") and response.content:
                        raw_content = str(response.content)
                        break
            except Exception as e:
                logger.warning(
                    "Report LLM candidate failed (%s, %s). Trying next.", cfg["model"], e
                )

    parsed = _parse_llm_json_response(raw_content or "")

    # Structured graceful fallback if LLM offline
    if not parsed:
        ending = "~냥"
        if "SHOEBILL" in str(librarian_type).upper():
            ending = "~두둥"
        elif "SEA_SLUG" in str(librarian_type).upper():
            ending = "~누누"
        elif "GECKO" in str(librarian_type).upper():
            ending = "~크크"

        unread_list = stats_data.get("balance", {}).get("unreadGenres", ["자연과학"])
        rec_genre = unread_list[0] if unread_list else "자연과학"

        parsed = {
            "readerType": "사색하는 몰입형 독서가",
            "summary": f"저녁 시간대에 문학과 철학 도서에 깊이 몰입하며, 마음에 닿는 문장을 꾸준히 기록하는 사색적인 독서 습관이 돋보였다{ending}. 책과 함께 스스로의 내면을 단단하게 다져가고 있다{ending}.",
            "keyTraits": ["저녁 집중형", "인문/철학 선호", "기록 애호가"],
            "recommendedGenre": rec_genre,
            "suggestedGoalBooks": 4,
            "advice": f"지금의 안정적인 독서 흐름을 유지하되, 이번 달에는 아직 마주하지 않은 '{rec_genre}' 분야의 친절한 입문서 1권을 더해보면 사유의 폭이 훨씬 다채로워질 거다{ending}.",
            "recommendedBooks": [
                {
                    "title": "코스모스",
                    "author": "칼 세이건",
                    "reason": "광대한 우주 속에서 인간의 실존과 자연과학의 아름다움을 조망하는 필독 교양서",
                },
                {
                    "title": "이기적 유전자",
                    "author": "리처드 도킨스",
                    "reason": "생명과 인간 본성에 대한 새로운 과학적 시각을 열어주는 고전",
                },
            ],
        }

    # Verify and enrich recommended books using NationalLibraryClient
    nl_client = get_national_library_client()
    raw_books = parsed.get("recommendedBooks", [])
    verified_books: List[RecommendedBookItem] = []

    for item in raw_books[:2]:
        title = item.get("title", "")
        author = item.get("author", "")
        reason = item.get("reason", "")
        if not title:
            continue

        biblio = await nl_client.search_book(title, author)
        if biblio:
            verified_books.append(
                RecommendedBookItem(
                    title=str(biblio.get("title", title)),
                    author=str(biblio.get("author", author)),
                    isbn=str(biblio.get("isbn", "")),
                    publisher=biblio.get("publisher"),
                    page_count=biblio.get("page_count"),
                    genre=biblio.get("genre"),
                    cover_url=biblio.get("cover_url"),
                    reason=reason,
                    description=biblio.get("description"),
                )
            )

    # If verification empty, fallback to catalog
    if not verified_books:
        fallback_biblio = nl_client._generate_fallback_biblio("코스모스", "칼 세이건")
        verified_books.append(
            RecommendedBookItem(
                title=fallback_biblio["title"],
                author=fallback_biblio["author"],
                isbn=fallback_biblio["isbn"],
                publisher=fallback_biblio["publisher"],
                page_count=fallback_biblio["page_count"],
                genre=fallback_biblio["genre"],
                cover_url=fallback_biblio["cover_url"],
                reason="미독서 장르인 자연과학의 경이로움을 만나는 가장 탁월한 안내서",
                description=fallback_biblio["description"],
            )
        )

    ai_analysis = AiAnalysis(
        reader_type=parsed.get("readerType", "사색하는 몰입형 독서가"),
        summary=parsed.get("summary", ""),
        key_traits=parsed.get("keyTraits", ["몰입형 독서가", "기록 애호가"]),
    )

    prescription = Prescription(
        recommended_genre=parsed.get("recommendedGenre", "자연과학"),
        suggested_goal_books=int(parsed.get("suggestedGoalBooks", 4)),
        advice=parsed.get("advice", ""),
        recommended_books=verified_books,
    )

    return ai_analysis, prescription


async def build_monthly_report(
    raw_stats: Dict[str, Any],
    token: Optional[str] = None,
    member_id: Optional[str] = None,
) -> MonthlyReportResponse:
    """Orchestrate the full Monthly Reading Report response combining Core stats and AI LLM analysis/prescription."""
    lib_raw = raw_stats.get("librarian", {})
    lib_type = lib_raw.get("type", "CAT")
    lib_name = lib_raw.get("name", "블루")
    year = int(raw_stats.get("year", 2026))
    month = int(raw_stats.get("month", 9))
    effective_mid = member_id or str(
        raw_stats.get("memberId")
        or raw_stats.get("member_id", "00000000-0000-0000-0000-000000000001")
    )

    # 1. Extract 3~5 debate keywords
    debate_keywords = await extract_monthly_debate_keywords(
        member_id=effective_mid,
        year=year,
        month=month,
        stats_data=raw_stats,
    )

    # 2. Synthesize 06. AI Analysis and 07. Prescription via LLM
    ai_analysis, prescription = await generate_ai_analysis_and_prescription(
        librarian_type=lib_type,
        librarian_name=lib_name,
        stats_data=raw_stats,
        debate_keywords=debate_keywords,
    )

    # 3. Model construction and unification
    librarian_info = LibrarianReportInfo(
        type=lib_raw.get("type", "CAT"),
        name=lib_raw.get("name", "블루"),
        level=lib_raw.get("level", 1),
        report_title=lib_raw.get(
            "reportTitle", lib_raw.get("report_title", f"{lib_name} 사서의 {month}월 독서 리포트")
        ),
    )

    overview_raw = raw_stats.get("overview", {})
    overview = MonthlyOverview(
        completed_books_count=overview_raw.get(
            "completedBooksCount", overview_raw.get("completed_books_count", 0)
        ),
        total_pages_read=overview_raw.get(
            "totalPagesRead", overview_raw.get("total_pages_read", 0)
        ),
        total_duration_minutes=overview_raw.get(
            "totalDurationMinutes", overview_raw.get("total_duration_minutes", 0)
        ),
        goal_books_count=overview_raw.get(
            "goalBooksCount", overview_raw.get("goal_books_count", 3)
        ),
        goal_achievement_rate=float(
            overview_raw.get("goalAchievementRate", overview_raw.get("goal_achievement_rate", 0.0))
        ),
    )

    habits_raw = raw_stats.get("habits", {})
    habits = ReadingHabits(
        weekday_distribution=habits_raw.get(
            "weekdayDistribution", habits_raw.get("weekday_distribution", {})
        ),
        time_distribution=habits_raw.get(
            "timeDistribution", habits_raw.get("time_distribution", {})
        ),
        weather_distribution=habits_raw.get(
            "weatherDistribution", habits_raw.get("weather_distribution", {})
        ),
        avg_completion_days=habits_raw.get(
            "avgCompletionDays", habits_raw.get("avg_completion_days")
        ),
        longest_streak_days=habits_raw.get(
            "longestStreakDays", habits_raw.get("longest_streak_days", 0)
        ),
        total_session_count=habits_raw.get(
            "totalSessionCount", habits_raw.get("total_session_count", 0)
        ),
        avg_session_duration_minutes=habits_raw.get(
            "avgSessionDurationMinutes", habits_raw.get("avg_session_duration_minutes")
        ),
    )

    prefs_raw = raw_stats.get("preferences", {})
    top_genres_items = [
        GenrePreferenceItem(
            genre=g.get("genre", "GENERAL"),
            genre_name=g.get("genreName", g.get("genre_name", "")),
            count=g.get("count", 0),
            percentage=float(g.get("percentage", 0.0)),
        )
        for g in prefs_raw.get("topGenres", prefs_raw.get("top_genres", []))
    ]
    weather_pref_items = [
        WeatherPreferenceItem(
            weather=w.get("weather", "clear"),
            session_count=w.get("sessionCount", w.get("session_count", 0)),
            top_genre=w.get("topGenre", w.get("top_genre")),
            top_genre_name=w.get("topGenreName", w.get("top_genre_name")),
            preferred_book_title=w.get("preferredBookTitle", w.get("preferred_book_title")),
        )
        for w in prefs_raw.get("weatherPreferences", prefs_raw.get("weather_preferences", []))
    ]
    preferences = ReadingPreferences(
        top_genres=top_genres_items,
        top_subjects=prefs_raw.get("topSubjects", prefs_raw.get("top_subjects", [])),
        weather_preferences=weather_pref_items,
        debate_keywords=debate_keywords,
    )

    balance_raw = raw_stats.get("balance", {})
    balance_items = [
        GenreBalanceItem(
            genre=b.get("genre", "GENERAL"),
            genre_name=b.get("genreName", b.get("genre_name", "")),
            count=b.get("count", 0),
            percentage=float(b.get("percentage", 0.0)),
        )
        for b in balance_raw.get("genreBreakdown", balance_raw.get("genre_breakdown", []))
    ]
    balance = ReadingBalance(
        genre_breakdown=balance_items,
        dominant_genre=balance_raw.get("dominantGenre", balance_raw.get("dominant_genre")),
        is_biased=bool(balance_raw.get("isBiased", balance_raw.get("is_biased", False))),
        diversity_score=int(
            balance_raw.get("diversityScore", balance_raw.get("diversity_score", 0))
        ),
        unread_genres=balance_raw.get("unreadGenres", balance_raw.get("unread_genres", [])),
    )

    from uuid import UUID

    traces_raw = raw_stats.get("traces", {})
    traces = ReadingTraces(
        most_scrapped_books=traces_raw.get(
            "mostScrappedBooks", traces_raw.get("most_scrapped_books", [])
        ),
        featured_records=traces_raw.get("featuredRecords", traces_raw.get("featured_records", [])),
        completed_books=traces_raw.get("completedBooks", traces_raw.get("completed_books", [])),
        reading_books=traces_raw.get("readingBooks", traces_raw.get("reading_books", [])),
    )

    return MonthlyReportResponse(
        year=year,
        month=month,
        member_id=UUID(effective_mid),
        librarian=librarian_info,
        overview=overview,
        habits=habits,
        preferences=preferences,
        balance=balance,
        traces=traces,
        ai_analysis=ai_analysis,
        prescription=prescription,
    )
