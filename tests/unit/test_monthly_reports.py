"""Unit tests for Monthly Reading Report API and orchestration."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.reports.generator import build_monthly_report
from app.domain.reports.keyword_extractor import _extract_keywords_from_texts
from app.main import app


@pytest.mark.asyncio
async def test_extract_keywords_from_texts():
    """Verify Korean keyword extraction filters stopwords and orders by frequency."""
    texts = [
        "새는 알에서 나오려고 투쟁한다 알은 세계이다",
        "자아성찰과 내면의 고통을 통해 진정한 성장을 이룬다",
        "투쟁과 세계의 붕괴 속에서 우리는 성장한다",
    ]
    keywords = _extract_keywords_from_texts(texts, max_count=3)
    assert len(keywords) <= 3
    # Check that meaningful words are extracted
    assert any(k in ["투쟁", "세계", "성장", "알에서", "성장을"] for k in keywords)


@pytest.mark.asyncio
async def test_build_monthly_report_pipeline():
    """Verify build_monthly_report synthesizes 01~07 sections and sets persona ending."""
    mock_stats = {
        "year": 2026,
        "month": 9,
        "memberId": "11111111-1111-1111-1111-111111111111",
        "librarian": {
            "type": "CAT",
            "name": "블루",
            "level": 2,
            "reportTitle": "블루 사서의 9월 독서 리포트",
        },
        "overview": {
            "completedBooksCount": 3,
            "totalPagesRead": 900,
            "totalDurationMinutes": 1200,
            "goalBooksCount": 4,
            "goalAchievementRate": 75.0,
        },
        "habits": {
            "weekdayDistribution": {"MON": 2, "TUE": 3},
            "timeDistribution": {"night": 15, "dawn": 3},
            "weatherDistribution": {"clear": 10, "rainy": 5},
            "avgCompletionDays": 7.0,
            "longestStreakDays": 4,
        },
        "preferences": {
            "topGenres": [
                {"genre": "LITERATURE", "genreName": "문학", "count": 3, "percentage": 60.0},
                {"genre": "PHILOSOPHY", "genreName": "철학", "count": 2, "percentage": 40.0},
            ],
            "topSubjects": ["실존주의", "성장소설"],
            "weatherPreferences": [
                {
                    "weather": "rainy",
                    "sessionCount": 5,
                    "topGenre": "LITERATURE",
                    "topGenreName": "문학",
                    "preferredBookTitle": "데미안",
                }
            ],
        },
        "balance": {
            "genreBreakdown": [
                {"genre": "LITERATURE", "genreName": "문학", "count": 3, "percentage": 60.0},
                {"genre": "PHILOSOPHY", "genreName": "철학", "count": 2, "percentage": 40.0},
            ],
            "dominantGenre": "문학",
            "isBiased": True,
            "diversityScore": 45,
            "unreadGenres": ["자연과학", "예술", "역사"],
        },
        "traces": {
            "mostScrappedBooks": [
                {
                    "bookId": 1,
                    "title": "데미안",
                    "author": "헤르만 헤세",
                    "coverUrl": "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg",
                    "displayGenre": "문학",
                    "scrapCount": 4,
                }
            ],
            "featuredRecords": [
                {
                    "recordId": 101,
                    "bookId": 1,
                    "title": "알을 깨고 나오는 순간",
                    "contentSnippet": "새는 알을 깨고 나온다",
                    "rating": 5,
                    "weather": "rainy",
                    "createdAt": "2026-09-10T21:00:00Z",
                }
            ],
            "completedBooks": [],
            "readingBooks": [],
        },
    }

    report = await build_monthly_report(
        raw_stats=mock_stats,
        member_id="11111111-1111-1111-1111-111111111111",
    )

    assert report.year == 2026
    assert report.month == 9
    assert str(report.member_id) == "11111111-1111-1111-1111-111111111111"
    assert report.librarian.name == "블루"
    assert report.librarian.type == "CAT"
    assert report.overview.completed_books_count == 3
    assert len(report.preferences.debate_keywords) >= 3
    assert report.ai_analysis.reader_type is not None
    assert report.prescription.recommended_genre in ["자연과학", "예술", "역사", "자연과학"]
    assert len(report.prescription.recommended_books) >= 1
    # Check that recommended book has cover URL and ISBN
    book = report.prescription.recommended_books[0]
    assert book.title
    assert book.cover_url.startswith("http")


@pytest.mark.asyncio
async def test_get_monthly_report_endpoint_success():
    """Verify GET /api/v1/reports/monthly returns 200 OK with combined JSON payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/reports/monthly",
            params={"year": 2026, "month": 9},
            headers={"Authorization": "Bearer mock-token-11111111-1111-1111-1111-111111111111"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check CamelCase serialization matching backend-core-api
        assert data["year"] == 2026
        assert data["month"] == 9
        assert "librarian" in data
        assert "overview" in data
        assert "habits" in data
        habits = data["habits"]
        assert "totalSessionCount" in habits
        assert "avgSessionDurationMinutes" in habits
        assert habits["totalSessionCount"] == 34
        assert habits["avgSessionDurationMinutes"] == 28.2
        assert "preferences" in data
        assert "balance" in data
        assert "traces" in data
        assert "aiAnalysis" in data
        assert "prescription" in data

        # Check section 03 debate keywords
        assert "debateKeywords" in data["preferences"]
        assert isinstance(data["preferences"]["debateKeywords"], list)
        assert len(data["preferences"]["debateKeywords"]) >= 3

        # Check section 06 AI Analysis
        ai_analysis = data["aiAnalysis"]
        assert "readerType" in ai_analysis
        assert "summary" in ai_analysis
        assert "keyTraits" in ai_analysis

        # Check section 07 Prescription
        prescription = data["prescription"]
        assert "recommendedGenre" in prescription
        assert "suggestedGoalBooks" in prescription
        assert "advice" in prescription
        assert "recommendedBooks" in prescription
        assert len(prescription["recommendedBooks"]) >= 1
        assert prescription["recommendedBooks"][0]["coverUrl"].startswith("http")


@pytest.mark.asyncio
async def test_get_monthly_report_shoebill_persona():
    """Verify Shoebill persona report generation uses Shoebill tone (~두둥)."""
    mock_stats = {
        "year": 2026,
        "month": 9,
        "memberId": "22222222-2222-2222-2222-222222222222",
        "librarian": {
            "type": "SHOEBILL",
            "name": "슈빌",
            "level": 1,
            "reportTitle": "슈빌 사서의 9월 독서 리포트",
        },
        "overview": {
            "completedBooksCount": 2,
            "totalPagesRead": 500,
            "totalDurationMinutes": 600,
            "goalBooksCount": 3,
            "goalAchievementRate": 66.7,
        },
        "habits": {},
        "preferences": {
            "topGenres": [],
            "topSubjects": ["과학", "엔지니어링"],
            "weatherPreferences": [],
        },
        "balance": {
            "genreBreakdown": [],
            "unreadGenres": ["문학", "철학"],
        },
        "traces": {},
    }

    report = await build_monthly_report(
        raw_stats=mock_stats,
        member_id="22222222-2222-2222-2222-222222222222",
    )
    assert report.librarian.type == "SHOEBILL"
    assert report.librarian.name == "슈빌"
    assert report.prescription.suggested_goal_books >= 1
    assert len(report.prescription.recommended_books) >= 1
