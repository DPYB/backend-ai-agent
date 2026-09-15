"""Extract representative debate keywords from debate insights and reading traces."""

import logging
import re
from typing import Any, Dict, List

from app.infrastructure.db.repository import get_agent_vector_repository

logger = logging.getLogger(__name__)


def _extract_keywords_from_texts(texts: List[str], max_count: int = 5) -> List[str]:
    """Simple Korean keyword extraction using frequency and stopwords filtering."""
    if not texts:
        return []

    stopwords = {
        "대한",
        "관한",
        "통해",
        "위해",
        "그리고",
        "하지만",
        "우리는",
        "오늘",
        "생각",
        "대화",
        "토론",
        "이유",
        "어떤",
        "자신",
        "가장",
        "모든",
        "있는",
        "하는",
        "된다",
        "있다",
        "한다",
        "것이다",
        "대해",
        "이번",
    }

    word_freq: Dict[str, int] = {}
    for text in texts:
        # Extract Korean nouns/words (2~8 chars)
        words = re.findall(r"[가-힣]{2,8}", text)
        for w in words:
            if w in stopwords:
                continue
            word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_count]]


async def extract_monthly_debate_keywords(
    member_id: str,
    year: int,
    month: int,
    stats_data: Dict[str, Any],
) -> List[str]:
    """Extract 3~5 key debate keywords from debate insights or fallback to traces/subjects."""
    repo = get_agent_vector_repository()
    insights = await repo.get_member_monthly_debate_insights(member_id, year, month, limit=10)

    combined_texts: List[str] = []
    for insight in insights:
        if insight.get("topic"):
            combined_texts.append(str(insight["topic"]))
        if insight.get("summary"):
            combined_texts.append(str(insight["summary"]))

    # Also augment from traces (featured records snippets)
    traces = stats_data.get("traces", {})
    for record in traces.get("featuredRecords", traces.get("featured_records", [])):
        if record.get("title"):
            combined_texts.append(str(record["title"]))
        if record.get("contentSnippet") or record.get("content_snippet"):
            combined_texts.append(
                str(record.get("contentSnippet") or record.get("content_snippet"))
            )

    keywords = _extract_keywords_from_texts(combined_texts, max_count=5)

    # Fallback to top_subjects if no debate/record texts found
    if len(keywords) < 3:
        preferences = stats_data.get("preferences", {})
        subjects = preferences.get("topSubjects", preferences.get("top_subjects", []))
        for subj in subjects:
            if subj not in keywords:
                keywords.append(subj)
            if len(keywords) >= 5:
                break

    # Final fallback default representative topics
    defaults = ["실존적 성장", "인간의 본질", "타인과의 연대", "사유의 깊이", "선택과 용기"]
    for d in defaults:
        if len(keywords) >= 3:
            break
        if d not in keywords:
            keywords.append(d)

    return keywords[:5]
