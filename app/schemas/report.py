"""Pydantic schemas for Monthly Reading Report aligned with backend-core-api."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that automatically converts snake_case fields to camelCase in serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class RecommendedBookItem(CamelModel):
    """Recommended book item with camelCase serialization matching frontend expectations."""

    title: str = Field(..., description="Book title (도서명)")
    author: str = Field(
        default="", description="Author name without extraneous notes (순수 저자명)"
    )
    isbn: str = Field(default="", description="13-digit standard ISBN (13자리 정식 ISBN)")
    publisher: Optional[str] = Field(default=None, description="Publisher name (출판사)")
    page_count: Optional[int] = Field(
        default=None, description="Total page count as integer (총 쪽수)"
    )
    genre: Optional[str] = Field(
        default=None, description="Book genre or KDC main category (도서 장르/대분류)"
    )
    cover_url: Optional[str] = Field(
        default=None, description="High-resolution book cover image URL (고화질 표지 URL)"
    )
    reason: Optional[str] = Field(
        default=None, description="AI recommendation context or rationale (추천 사유)"
    )
    description: Optional[str] = Field(
        default=None, description="Book summary or description (도서 소개/줄거리)"
    )


class LibrarianReportInfo(CamelModel):
    """01. Librarian metadata for the report."""

    type: str = Field(description="사서 종류 (CAT, SHOEBILL, SEA_SLUG, GECKO)")
    name: str = Field(description="사서 이름 (예: 블루)")
    level: int = Field(default=1, description="사서 레벨")
    report_title: str = Field(description="리포트 타이틀 (예: 블루 사서의 월간 독서 리포트)")


class MonthlyOverview(CamelModel):
    """01. Monthly reading overview statistics."""

    completed_books_count: int = Field(description="이번 달 완독 권수")
    total_pages_read: int = Field(description="이번 달 누적 독서 페이지")
    total_duration_minutes: int = Field(description="이번 달 총 독서 시간 (분)")
    goal_books_count: int = Field(default=3, description="이번 달 목표 권수")
    goal_achievement_rate: float = Field(description="목표 달성률 (%)")


class ReadingHabits(CamelModel):
    """02. Reading habits (distribution, streaks, sessions)."""

    weekday_distribution: Dict[str, int] = Field(
        default_factory=dict, description="요일별 독서 횟수 (MON, TUE, ...)"
    )
    time_distribution: Dict[str, int] = Field(
        default_factory=dict, description="시간대별 독서 횟수 (dawn, day, evening, night)"
    )
    weather_distribution: Dict[str, int] = Field(
        default_factory=dict, description="날씨별 독서 횟수 (clear, rainy, cloudy, snowy, ...)"
    )
    avg_completion_days: Optional[float] = Field(
        default=None, description="평균 완독 소요 기간 (일)"
    )
    longest_streak_days: int = Field(default=0, description="해당 월 최장 연속 독서일 (Streak)")
    total_session_count: int = Field(
        default=0, description="해당 월 총 독서 세션 횟수 (reading_sessions 집계)"
    )
    avg_session_duration_minutes: Optional[float] = Field(
        default=None, description="1회 평균 독서 집중 시간 (분 단위)"
    )


class GenrePreferenceItem(CamelModel):
    """Individual genre preference breakdown item."""

    genre: str
    genre_name: str
    count: int
    percentage: float


class WeatherPreferenceItem(CamelModel):
    """Weather-linked reading preference item."""

    weather: str
    session_count: int
    top_genre: Optional[str] = None
    top_genre_name: Optional[str] = None
    preferred_book_title: Optional[str] = None


class ReadingPreferences(CamelModel):
    """03. Reading preferences including top genres, subjects, and debate keywords."""

    top_genres: List[GenrePreferenceItem] = Field(default_factory=list)
    top_subjects: List[str] = Field(default_factory=list, description="주요 세부 주제 태그")
    weather_preferences: List[WeatherPreferenceItem] = Field(
        default_factory=list, description="날씨별 선호 장르 및 도서"
    )
    debate_keywords: List[str] = Field(
        default_factory=list, description="AI Agent 토론/메모 분석 기반 주요 토론 키워드 (3~5개)"
    )


class GenreBalanceItem(CamelModel):
    """KDC genre balance share item."""

    genre: str
    genre_name: str
    count: int
    percentage: float


class ReadingBalance(CamelModel):
    """04. Reading balance & diversity metrics."""

    genre_breakdown: List[GenreBalanceItem] = Field(default_factory=list)
    dominant_genre: Optional[str] = Field(default=None, description="가장 편중된 장르명")
    is_biased: bool = Field(default=False, description="편독 여부 (특정 장르 >= 60%)")
    diversity_score: int = Field(default=0, description="장르 다양성 점수 (0~100)")
    unread_genres: List[str] = Field(
        default_factory=list, description="이번 달 읽지 않은 KDC 대분류 목록"
    )


class ScrappedBookItem(CamelModel):
    """Most scrapped book summary."""

    book_id: int
    title: str
    author: str
    cover_url: Optional[str] = None
    display_genre: Optional[str] = None
    scrap_count: int


class FeaturedRecordItem(CamelModel):
    """Featured best reading record."""

    record_id: int
    book_id: int
    title: str
    content_snippet: str
    rating: Optional[int] = None
    weather: Optional[str] = None
    created_at: datetime


class ReportBookSummary(CamelModel):
    """Book summary item in reading traces."""

    book_id: int
    title: str
    author: str
    cover_url: Optional[str] = None
    display_genre: Optional[str] = None
    current_page: int
    total_pages: Optional[int] = None
    completed_at: Optional[datetime] = None


class ReadingTraces(CamelModel):
    """05. Reading traces (scraps, records, completed books)."""

    most_scrapped_books: List[ScrappedBookItem] = Field(default_factory=list)
    featured_records: List[FeaturedRecordItem] = Field(default_factory=list)
    completed_books: List[ReportBookSummary] = Field(default_factory=list)
    reading_books: List[ReportBookSummary] = Field(default_factory=list)


class AiAnalysis(CamelModel):
    """06. AI Analysis generated by LLM with librarian persona."""

    reader_type: str = Field(
        description="독서가 유형 네이밍 (예: '새벽의 몰입형 탐구자', '감성적 사색가')",
        examples=["새벽의 몰입형 탐구자"],
    )
    summary: str = Field(
        description="독서 성향 요약 및 페르소나 말투의 심층 분석 문장",
        examples=[
            "밤보다 오전에 독서 집중도가 높은 편이며, 생각할 거리를 던져주는 철학 도서를 자주 선택하셨다냥."
        ],
    )
    key_traits: List[str] = Field(
        default_factory=list,
        description="핵심 독서 특징 태그 3~4개 (예: ['오전 집중형', '철학/사색 선호', '기록 애호가'])",
    )


class Prescription(CamelModel):
    """07. Next month prescription generated by LLM."""

    recommended_genre: str = Field(
        description="미독서 장르를 고려한 다음 달 추천 도전 장르",
        examples=["자연과학"],
    )
    suggested_goal_books: int = Field(
        description="회원의 페이스에 맞춘 다음 달 제안 목표 권수",
        examples=[4],
    )
    advice: str = Field(
        description="다음 달 독서를 위한 사서의 따뜻한 조언과 행동 유도 문장",
        examples=[
            "지금의 꾸준한 페이스를 이어가면서, 아직 발길이 닿지 않은 자연과학 분야에서 가벼운 교양서 1권을 더해보면 시야가 훨씬 넓어질 거다냥."
        ],
    )
    recommended_books: List[RecommendedBookItem] = Field(
        default_factory=list,
        description="국립중앙도서관 실존 서지 검증 기반 맞춤 추천 도서 1~2권",
    )


class MonthlyReportResponse(CamelModel):
    """Complete Monthly Reading Report response payload combining Core API 01~05 and AI Agent 06~07."""

    year: int = Field(description="리포트 연도")
    month: int = Field(description="리포트 월")
    member_id: UUID = Field(description="회원 UUID")
    librarian: LibrarianReportInfo = Field(description="01. 사서 정보")
    overview: MonthlyOverview = Field(description="01. 월간 독서 통계 개요")
    habits: ReadingHabits = Field(description="02. 독서 습관")
    preferences: ReadingPreferences = Field(description="03. 독서 선호도 및 토론 키워드")
    balance: ReadingBalance = Field(description="04. 독서 균형 및 다양성")
    traces: ReadingTraces = Field(description="05. 독서 흔적 (스크랩, 기록, 완독)")
    ai_analysis: AiAnalysis = Field(description="06. AI가 발견한 나의 독서 성향")
    prescription: Prescription = Field(description="07. 다음 달 독서 처방 및 맞춤 도서")
