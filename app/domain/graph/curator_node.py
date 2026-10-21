"""Book Curator Sub-Agent node: Emotion/weather reasoning + National Library bibliography verification.

Uses Pydantic structured output (.with_structured_output) with zero regex parsing failures,
open-book prompt injection from Redis trending books, and graceful random masterpiece fallbacks.

Hybrid Curation Principle:
  - All recommendations produce a pair:
      [1 recent trending book from open-book catalog] + [1 timeless classic/steady-seller]
  - Pydantic enforces the exact JSON schema on the LLM
  - 4-stage National Library validation chain verifies real-world publication & ISBN
"""

import asyncio
import hashlib
import json
import logging
import random
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import settings
from app.domain.graph.state import AgentState
from app.infrastructure.core_api_client import get_core_api_client
from app.infrastructure.national_library_client import (
    _normalize_to_core_genre,
    clean_book_title,
    get_national_library_client,
    map_kdc_to_genre,
)
from app.infrastructure.redis_session import get_redis_session_manager
from app.infrastructure.trending_books import get_trending_books_text

logger = logging.getLogger(__name__)


def _is_similar_title(a: str, b: str, threshold: float = 0.55) -> bool:
    """Return True if normalized title 'a' and 'b' are similar enough.

    Handles cases like subtitle truncation ('데미안 : 에밀 싱클레어의 청춘 이야기'),
    bracket tags ('데미안 (민음사)'), or minor typographical variations.
    Safely prevents short title false positive containment (e.g. '이방인' vs '이방인의 노래').
    """
    if not a or not b:
        return False

    raw_a = re.sub(r"[《》〈〉「」『』\"'\[\]\(\)]", "", a).strip().lower()
    raw_b = re.sub(r"[《》〈〉「」『』\"'\[\]\(\)]", "", b).strip().lower()
    if raw_a == raw_b:
        return True

    # Check for edition/bracket tags stripped match
    clean_a = clean_book_title(a).strip().lower()
    clean_b = clean_book_title(b).strip().lower()
    if not clean_a or not clean_b:
        return False
    if clean_a == clean_b:
        return True

    # Short title guard: if either title is <= 3 characters (e.g. '모모', '이방인', '코스모스')
    # do NOT allow arbitrary substring containment like '이방인의 노래' or '코스모스 화원'.
    # Only allow if the longer title starts with the shorter title followed by a delimiter
    # (colon, hyphen, whitespace) representing an explicit subtitle or edition.
    len_a, len_b = len(clean_a), len(clean_b)
    if len_a <= 3 or len_b <= 3:
        shorter, longer = (clean_a, clean_b) if len_a <= len_b else (clean_b, clean_a)
        # Check if longer starts with shorter + delimiter (e.g. '데미안 : 에밀...', '모모 - 시간의...')
        if re.match(rf"^{re.escape(shorter)}\s*[:\-_,\(]\s*", longer) or re.match(
            rf"^{re.escape(shorter)}\s+", longer
        ):
            # If followed by delimiter, verify SequenceMatcher ratio or explicit separator
            if any(sep in longer for sep in [":", "-", "–", "(", "["]):
                return True
        # For short titles, reject arbitrary substring matching and rely on ratio >= 0.85
        return SequenceMatcher(None, clean_a, clean_b).ratio() >= 0.85

    # For titles longer than 3 characters, check subtitle prefix or containment
    raw_a_nows = raw_a.replace(" ", "")
    raw_b_nows = raw_b.replace(" ", "")
    clean_a_nows = clean_a.replace(" ", "")
    clean_b_nows = clean_b.replace(" ", "")

    if raw_a_nows == raw_b_nows or clean_a_nows == clean_b_nows:
        return True

    # If one is a clean prefix of the other (e.g. subtitle truncated)
    if clean_b_nows.startswith(clean_a_nows) or clean_a_nows.startswith(clean_b_nows):
        return True

    # Series/particles normalized check
    core_a = re.sub(r"[\d\s:·\-_,./\(\)\[\]]", "", a).replace("와", "").replace("과", "").lower()
    core_b = re.sub(r"[\d\s:·\-_,./\(\)\[\]]", "", b).replace("와", "").replace("과", "").lower()
    if (
        core_a
        and core_b
        and (core_a == core_b or core_a.startswith(core_b) or core_b.startswith(core_a))
    ):
        return True

    return SequenceMatcher(None, clean_a_nows, clean_b_nows).ratio() >= threshold


# ---------------------------------------------------------------------------
# ISBN Validation & Conversion Helpers (EAN-13 & Modulo 11)
# ---------------------------------------------------------------------------


def validate_isbn10(isbn10: str) -> bool:
    """Validate an ISBN-10 string using the Modulo 11 check digit algorithm."""
    if not isbn10 or not isinstance(isbn10, str):
        return False
    clean = re.sub(r"[-\s]", "", isbn10).upper()
    if len(clean) != 10:
        return False
    if not clean[:9].isdigit():
        return False
    last_char = clean[9]
    if not (last_char.isdigit() or last_char == "X"):
        return False
    s = sum(int(clean[i]) * (10 - i) for i in range(9))
    check = 10 if last_char == "X" else int(last_char)
    s += check
    return (s % 11) == 0


def calculate_isbn13_check_digit(raw12: str) -> str:
    """Calculate the 13th check digit for a 12-digit string according to EAN-13 rules."""
    if not raw12 or len(raw12) != 12 or not raw12.isdigit():
        raise ValueError(f"raw12 must be a 12-digit numeric string, got '{raw12}'")
    s = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(raw12))
    check = (10 - (s % 10)) % 10
    return str(check)


def validate_isbn13(isbn13: str) -> bool:
    """Validate an ISBN-13 string using the EAN-13 check digit algorithm."""
    if not isbn13 or not isinstance(isbn13, str):
        return False
    clean = re.sub(r"[-\s]", "", isbn13)
    if len(clean) != 13 or not clean.isdigit():
        return False
    expected_check = calculate_isbn13_check_digit(clean[:12])
    return clean[12] == expected_check


def convert_isbn10_to_isbn13(isbn10: str) -> Optional[str]:
    """Convert a valid ISBN-10 to an ISBN-13 by recalculating the 13th check digit.

    Rules:
      1. Verify valid ISBN-10 check digit first.
      2. Take first 9 digits and prefix with '978' (12 digits).
      3. Calculate 13th check digit using EAN-13 alternating weights (1, 3).
    """
    if not validate_isbn10(isbn10):
        return None
    clean = re.sub(r"[-\s]", "", isbn10).upper()
    raw12 = "978" + clean[:9]
    check_digit = calculate_isbn13_check_digit(raw12)
    return raw12 + check_digit


def normalize_and_validate_isbn(
    isbn_raw: Optional[str],
) -> Tuple[Optional[str], Literal["VALID_13", "CONVERTED_10", "INVALID", "MISSING"]]:
    """Normalize and categorize an input ISBN string.

    Returns:
      (normalized_isbn, status)
      - VALID_13: Valid 13-digit ISBN
      - CONVERTED_10: Valid 10-digit ISBN converted to ISBN-13
      - INVALID: Malformed or checksum-failed ISBN
      - MISSING: Empty or omitted ISBN
    """
    if isbn_raw is None or not str(isbn_raw).strip():
        return None, "MISSING"
    clean = re.sub(r"[-\s]", "", str(isbn_raw)).strip().upper()
    if not clean:
        return None, "MISSING"
    if len(clean) == 13:
        if validate_isbn13(clean):
            return clean, "VALID_13"
        return None, "INVALID"
    elif len(clean) == 10:
        if validate_isbn10(clean):
            conv13 = convert_isbn10_to_isbn13(clean)
            return conv13, "CONVERTED_10"
        return None, "INVALID"
    return None, "INVALID"


# ---------------------------------------------------------------------------
# Author Normalization & Conservative Matching Helpers
# ---------------------------------------------------------------------------


def _extract_primary_author(raw_author: str) -> str:
    """Extract primary author from string, removing translator/editor roles.

    e.g. '조지 오웰 지음, 박경희 옮김' -> '조지 오웰'
         '헤르만 헤세 저 / 정현규 역' -> '헤르만 헤세'
         'Orwell, George' -> 'Orwell, George'
    """
    if not raw_author:
        return ""

    raw = raw_author.strip()

    # Split into candidate segments by delimiters
    # If comma is present with explicit role markers, treat comma as a segment delimiter.
    # Otherwise keep comma for western name 'Last, First' convention.
    has_role_markers = any(
        role in raw
        for role in ["지음", "옮김", "번역", "역자", "글", "그림", "저자", "원작", "저", "역"]
    )
    if has_role_markers and "," in raw:
        segments = re.split(r"[,;/]|\s+외\b", raw)
    else:
        segments = re.split(r"[;/]|\s+외\b", raw)

    chosen_seg = ""
    # 1. Prefer segments with author markers ('지음', '원작', '글') or '저'
    for seg in segments:
        s = seg.strip()
        if any(marker in s for marker in ["지음", "원작", "글"]) or (
            "저" in s and not any(r in s for r in ["역자", "옮김", "번역"])
        ):
            chosen_seg = s
            break

    # 2. If no explicit author marker, pick first segment without translator/illustrator markers
    if not chosen_seg:
        for seg in segments:
            s = seg.strip()
            if not any(
                r in s
                for r in ["옮김", "번역", "역", "해설", "그림", "일러스트", "감수", "편", "엮음"]
            ):
                chosen_seg = s
                break

    if not chosen_seg and segments:
        chosen_seg = segments[0].strip()

    # Clean roles and brackets from chosen segment
    cleaned = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", chosen_seg)
    cleaned = re.sub(
        r"(?:지음|지은이|글|저자|원작|저)\b|\b(?:지음|지은이|글|저자|원작|저)",
        "",
        cleaned,
    ).strip()
    return cleaned


def _is_matching_author(expected_author: str, candidate_author: str) -> bool:
    """Conservatively check if candidate author matches expected author.

    - If expected_author is empty/unspecified, returns True (permits title-only lookup).
    - Distinguishes primary author from translator.
    - Supports western inverted name representations ('George Orwell' <-> 'Orwell, George').
    - Strict avoidance of set-based false positives ('김영하' != '김하영').
    - Rejects single-character surname matches.
    """
    if not expected_author or not expected_author.strip():
        return True
    if not candidate_author or not candidate_author.strip():
        return False

    p_exp = _extract_primary_author(expected_author)
    p_cand = _extract_primary_author(candidate_author)
    if not p_exp or not p_cand:
        return False

    # Exact normalized string match (ignoring whitespace and delimiters)
    norm_exp = re.sub(r"[\s·・•\.\,\-_/]", "", p_exp).lower()
    norm_cand = re.sub(r"[\s·・•\.\,\-_/]", "", p_cand).lower()
    if norm_exp == norm_cand:
        return True

    # Token-level conservative matching (handles 'Last, First' vs 'First Last')
    tokens_exp = [t.lower() for t in re.split(r"[\s·・•\.\,\-_/]+", p_exp) if t]
    tokens_cand = [t.lower() for t in re.split(r"[\s·・•\.\,\-_/]+", p_cand) if t]

    if not tokens_exp or not tokens_cand:
        return False

    # Two-token Western name inversion: e.g. ['george', 'orwell'] <-> ['orwell', 'george']
    if len(tokens_exp) == 2 and len(tokens_cand) == 2:
        if tokens_exp == tokens_cand or tokens_exp == tokens_cand[::-1]:
            return True

    # Korean / Asian short names (<= 4 chars): Require exact normalized character match!
    # Explicitly do NOT use set matching to prevent '김영하' <-> '김하영' false positive.
    if len(norm_exp) <= 4 or len(norm_cand) <= 4:
        return norm_exp == norm_cand

    # For longer foreign names (>= 5 chars, e.g. '헤르만 헤세', '알베르 카뮈')
    if set(tokens_exp) == set(tokens_cand):
        return True

    return SequenceMatcher(None, norm_exp, norm_cand).ratio() >= 0.85


# ---------------------------------------------------------------------------
# Edition Intent Extraction & Bibliography Caching
# ---------------------------------------------------------------------------


def extract_edition_intent(request_text: Optional[str]) -> Optional[str]:
    """Extract edition intent from user request for cache partitioning.

    Returns:
      - 'COMICS': Comics / Webtoon / Graphic novel
      - 'CHILDREN': Children / Fairy tale / Youth
      - 'ORIGINAL': Original language / Foreign edition
      - 'PUB:{publisher}': Explicit publisher request
      - 'GENERAL': Standard book recommendation
      - None: Ambiguous or conflicting intent (bypasses cache)
    """
    if not request_text:
        return "GENERAL"

    clean = request_text.strip().lower()

    intents = []
    if any(k in clean for k in ["만화", "웹툰", "코믹", "그래픽노블"]):
        intents.append("COMICS")
    if any(k in clean for k in ["어린이", "아동", "동화", "그림책", "유아"]):
        intents.append("CHILDREN")
    if any(k in clean for k in ["원서", "영문판", "영어판", "외서", "원문"]):
        intents.append("ORIGINAL")

    known_publishers = [
        "민음사",
        "문학동네",
        "열린책들",
        "창비",
        "시공사",
        "웅진",
        "김영사",
        "을유문화사",
        "펭귄",
    ]
    for pub in known_publishers:
        if pub in clean:
            intents.append(f"PUB:{pub}")

    # If multiple distinct categories conflict, bypass cache to avoid pollution
    if len(intents) > 1:
        base_types = {i.split(":")[0] for i in intents}
        if len(base_types) > 1:
            return None
        return intents[0]

    if len(intents) == 1:
        return intents[0]

    return "GENERAL"


def get_biblio_cache_key(title: str, author: str, edition_intent: str) -> str:
    """Build a deterministic SHA-256 cache key reflecting title, author, and edition intent."""
    clean_t = re.sub(r"[\s《》〈〉「」『』\"'\[\]\(\)]", "", title).lower()
    clean_a = re.sub(r"[\s·・•\.\,\-_/]", "", author).lower()
    h = hashlib.sha256(f"{clean_t}::{clean_a}".encode("utf-8")).hexdigest()[:16]
    return f"book_biblio:v1:{edition_intent}:{h}"


async def get_cached_biblio(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve verified bibliography from Redis/in-memory cache."""
    try:
        redis_mgr = get_redis_session_manager()
        raw = await redis_mgr.get(cache_key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("Failed to retrieve biblio cache for %s: %s", cache_key, e)
    return None


async def set_cached_biblio(cache_key: str, data: Dict[str, Any], ttl_seconds: int = 86400) -> None:
    """Save verified bibliography to Redis/in-memory cache with 24h TTL."""
    try:
        redis_mgr = get_redis_session_manager()
        serialized = json.dumps(data, ensure_ascii=False)
        await redis_mgr.set(cache_key, serialized, ex=ttl_seconds)
    except Exception as e:
        logger.warning("Failed to store biblio cache for %s: %s", cache_key, e)


# 1. Pydantic Structured Output Schemas & Helpers
MAX_CURATED_BOOKS: int = 10


def parse_requested_book_count(request_text: Optional[str]) -> int:
    """Parse requested number of books from user prompt.

    - Default: 1 book for generic recommendations.
    - Exploratory/comparative requests ('두세 권', '다양하게', '비교' 등): 2~3 books (defaults to 3).
    - Explicit count (Arabic numbers or Korean numerals): parsed up to MAX_CURATED_BOOKS (10).
    """
    if not request_text:
        return 1

    clean = request_text.strip()

    # 1. Explicit Arabic numbers (e.g. '3권', '5권', '10권')
    match = re.search(r"(\d+)\s*권", clean)
    if match:
        count = int(match.group(1))
        return max(1, min(MAX_CURATED_BOOKS, count))

    # 2. Korean numeral words (e.g. '열 권', '다섯 권', '세 권', '한 권')
    korean_counts = {
        "열": 10,
        "아홉": 9,
        "여덟": 8,
        "일곱": 7,
        "여섯": 6,
        "다섯": 5,
        "네": 4,
        "세": 3,
        "두": 2,
        "한": 1,
    }
    for word, cnt in korean_counts.items():
        if re.search(rf"\b{word}\s*권", clean) or re.search(
            rf"(?:딱|오직|그냥)?\s*{word}\s*권", clean
        ):
            return cnt

    # 3. Approximate ranges
    if any(r in clean for r in ["두세 권", "두, 세 권", "2~3권", "2-3권"]):
        return 3
    if any(r in clean for r in ["서너 권", "3~4권", "3-4권"]):
        return 3

    # 4. Exploratory / comparative keywords -> 3 books
    exploratory_keywords = ["두세", "비교", "다양하게", "골고루", "여러 권", "몇 권", "다채롭게"]
    if any(k in clean for k in exploratory_keywords):
        return 3

    # 5. Explicit single-book keywords
    if any(k in clean for k in ["한 권만", "한권만", "딱 한 권", "1권만", "단 한 권"]):
        return 1

    return 1


class BookCandidate(BaseModel):
    """Pydantic model representing a single recommended book candidate."""

    title: str = Field(..., description="정확한 도서 제목 (단행본 기준, 괄호나 특수기호 제외)")
    author: str = Field(..., description="저자명")
    reason: str = Field(
        ..., description="사용자 상황 및 감정에 100% 공명하는 구체적인 추천 사유 (1~2줄)"
    )
    era: Literal["trend", "recent", "life_pick", "classic"] = Field(
        ...,
        description="오픈북 트렌드 도서면 'trend' 또는 'recent', 감정 맞춤 인생책이면 'life_pick' 또는 'classic'",
    )


class CuratorResponse(BaseModel):
    """Pydantic schema enforcing book recommendations and targeted book intent."""

    target_title: Optional[str] = Field(
        None,
        description=(
            "사용자가 특정 책을 직접 추천/등록해달라고 명시(예: '《데미안》 등록해줘', '프로젝트 헤일메리 추천해줘')했거나, "
            "직전 대화의 그 책을 등록해달라고 지칭했을 때만 해당 도서의 정확한 제목. "
            "단순 독서 취향 질문, 상황 설명, 또는 '다른 책 추천해줘', '이전에 추천받은 거랑 비슷한 책' 같은 메타/비교 질문일 경우 반드시 null"
        ),
    )
    recommendations: List[BookCandidate] = Field(
        ...,
        min_length=1,
        max_length=10,
        description=(
            "사용자 요청에 맞춘 추천 도서 목록입니다. "
            "기본 추천은 가장 적합한 1권(원픽), 비교/탐색형 요청은 2~3권, "
            "사용자가 특정 권수(N권)를 명시한 경우 해당 권수만큼(최대 10권) 구성하세요."
        ),
    )


MAX_RECOMMENDED_HISTORY: int = 10

# 2. Curator System Prompt with Emotion-focused Pairing Directive
CURATOR_SYSTEM_PROMPT = """당신은 최고 수준의 도서 큐레이터입니다.
사용자의 발화 의도, 최근 대화 맥락, 감정, 상황, 날씨를 차분히 분석하여 적절한 권수의 도서를 추천합니다.

[핵심 지침: 의도 식별 및 추천 권수 정책]
1. [지목 도서(target_title) 식별]:
   - 사용자가 '《데미안》 등록해줘', '프로젝트 헤일메리 추천해줘'처럼 특정 도서를 직접 지정하거나,
     직전 대화 히스토리에서 언급된 그 책을 등록/추천해달라고 지칭할 때 target_title에 그 책의 순수 제목을 기재하세요.
   - '비 오는 날 읽을 책', '다른 책 추천해줘', '이전에 추천받은 책과 비슷한 도서 추천해줘'처럼 일반적인 추천/메타 질의인 경우 target_title은 반드시 null로 두어야 합니다.
2. [추천 권수(recommendations) 결정 원칙]:
   - 기본 추천: 권수 언급이 없는 일반 추천 요청은 가장 적합하고 울림을 주는 '1권(원픽)'을 추천합니다.
   - 비교·탐색형 추천: '두세 권 골라줘', '비교해줘', '다양하게 추천해줘' 등의 요청은 '2~3권'을 추천합니다.
   - 명시적 권수 요청: 사용자가 '3권', '5권', '10권' 등 구체적인 권수를 요청한 경우, 그 요청에 맞춰 최대 10권까지 추천 목록을 구성합니다.
3. [도서 선정 및 페어링]:
   - 아래 [오늘의 화제작 오픈북] 데이터 안에 적합한 도서가 있다면 적극 반영하세요 (era: 'trend').
   - 시대와 장르를 불문하고 사용자의 마음에 깊은 위로와 통찰을 줄 수 있는 인생책/고전 스테디셀러를 자유롭게 구성하세요 (era: 'life_pick' 또는 'classic').
   - 4권 이상 추천 시에도 검증되지 않은 책을 억지로 날조하지 마세요.
4. [다양성 및 중복 방지]:
   - 최근 이미 추천된 도서 목록에 있는 도서는 절대 추천하지 마세요.
"""


def _get_random_elegant_fallback(
    exclude_titles: Optional[List[str]] = None,
    count: int = 1,
) -> List[Dict[str, Any]]:
    """Return timeless masterpieces when external LLM or library APIs fail.

    Provides honest fallback books while respecting recommended_history to avoid duplicates.
    """
    excluded = set(exclude_titles or [])
    masterpieces: List[Dict[str, Any]] = [
        {
            "title": "어린 왕자",
            "author": "앙투안 드 생텍쥐페리",
            "reason": "마음의 눈으로 본질을 바라보게 해주는 영혼의 쉼표 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "데미안",
            "author": "헤르만 헤세",
            "reason": "내면의 알을 깨고 진정한 자신을 마주하는 불멸의 고전 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "코스모스",
            "author": "칼 세이건",
            "reason": "광대한 우주 속 인류의 숭고한 탐구 여정 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "모모",
            "author": "미하엘 엔데",
            "reason": "바쁘게 쫓기는 현대인에게 시간의 진정한 의미를 묻는 책 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "이방인",
            "author": "알베르 카뮈",
            "reason": "부조리한 세상과 정직하게 맞선 인간의 실존적 초상 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "소크라테스 익스프레스",
            "author": "에릭 와이너",
            "reason": "14명의 철학자와 함께 떠나는 유쾌한 사유의 여정 (시스템 지연으로 시대를 초월한 명작을 추천합니다)",
            "era": "classic",
            "fallback": True,
        },
        {
            "title": "불편한 편의점",
            "author": "김호연",
            "reason": "골목길 편의점에서 피어나는 따뜻한 이웃들의 온기 (시스템 지연으로 화제작을 추천합니다)",
            "era": "recent",
            "fallback": True,
        },
        {
            "title": "달러구트 꿈 백화점",
            "author": "이미예",
            "reason": "지친 하루의 끝, 잠든 이들에게 건네는 몽환적인 위로 (시스템 지연으로 화제작을 추천합니다)",
            "era": "recent",
            "fallback": True,
        },
    ]
    # Filter out recent books if possible
    available = [m for m in masterpieces if m["title"] not in excluded]
    if len(available) < count:
        available = masterpieces
    sample_size = min(len(available), max(1, count))
    return random.sample(available, sample_size)


# --- Module-Level LLM Cache & Fallback Helper ---
_cached_curator_llm: Any = None


def is_valid_api_key(key: Optional[str]) -> bool:
    """Return True if api key is non-empty, not a placeholder, and sufficiently long."""
    if not key:
        return False
    clean = key.strip()
    return not clean.startswith("your_") and len(clean) > 10


def get_cached_curator_chain() -> Optional[Any]:
    """Build and cache resilient LLM chain with LangChain native fallbacks."""
    global _cached_curator_llm
    if _cached_curator_llm is not None:
        return _cached_curator_llm

    gemini_key = settings.gemini_api_key.strip()
    gemini_fallback_key = getattr(settings, "gemini_fallback_api_key", "").strip()
    openai_key = settings.openai_api_key.strip()
    light_model = getattr(settings, "gemini_light_model", "gemini-3.1-flash-lite")

    llm_candidates: List[Any] = []

    # 1. Primary Gemini light
    if is_valid_api_key(gemini_key):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm1 = ChatGoogleGenerativeAI(
                model=light_model,
                google_api_key=gemini_key,
                timeout=15.0,
                max_retries=0,
            )
            llm_candidates.append(llm1.with_structured_output(CuratorResponse))
        except Exception as e:
            logger.warning("Failed to init primary Gemini light (%s)", e)

    # 2. Fallback Gemini key
    if is_valid_api_key(gemini_fallback_key):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm2 = ChatGoogleGenerativeAI(
                model=light_model,
                google_api_key=gemini_fallback_key,
                timeout=15.0,
                max_retries=0,
            )
            llm_candidates.append(llm2.with_structured_output(CuratorResponse))
        except Exception as e:
            logger.warning("Failed to init fallback Gemini light (%s)", e)

    # 3. Gemini 3.5 model
    if is_valid_api_key(gemini_key):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm3 = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=gemini_key,
                timeout=15.0,
                max_retries=0,
            )
            llm_candidates.append(llm3.with_structured_output(CuratorResponse))
        except Exception as e:
            logger.warning("Failed to init Gemini 3.5 (%s)", e)

    # 4. OpenAI gpt-4o-mini
    if is_valid_api_key(openai_key):
        try:
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr

            llm4 = ChatOpenAI(
                model=settings.openai_model,
                api_key=SecretStr(openai_key),
                temperature=0.2,
                timeout=15.0,
                max_retries=0,
            )
            llm_candidates.append(llm4.with_structured_output(CuratorResponse))
        except Exception as e:
            logger.warning("Failed to init OpenAI fallback (%s)", e)

    if not llm_candidates:
        return None

    primary = llm_candidates[0]
    fallbacks = llm_candidates[1:]
    _cached_curator_llm = primary.with_fallbacks(fallbacks) if fallbacks else primary
    return _cached_curator_llm


# --- 5-Stage Pipeline Functions ---


def resolve_context(state: AgentState) -> Dict[str, Any]:
    """1. Extract user intent, conversation history, and recommendation history."""
    curator_request = state.get("curator_request") or ""
    messages = state.get("messages", [])

    if not curator_request:
        # Check only HumanMessages to avoid picking assistant output
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) and hasattr(msg, "content") and str(msg.content):
                curator_request = str(msg.content)
                break
            elif not isinstance(msg, HumanMessage) and getattr(msg, "type", "") == "human":
                curator_request = str(msg.content)
                break

    if not curator_request:
        curator_request = "마음을 달래줄 좋은 책을 추천해줘."

    # Format recent conversation turns (up to 6) to help LLM resolve references like '아까 그 책'
    recent_msgs = messages[-6:] if len(messages) > 6 else messages
    conversation_lines = []
    for m in recent_msgs:
        m_type = getattr(m, "type", "message")
        content_preview = str(getattr(m, "content", ""))[:200].strip()
        if content_preview:
            conversation_lines.append(f"{m_type}: {content_preview}")
    conversation_text = "\n".join(conversation_lines) if conversation_lines else "없음"

    # Recommendation history tracking
    raw_history = list(state.get("recommended_history") or [])
    for msg in messages:
        content_str = str(getattr(msg, "content", ""))
        for match in re.findall(r"###\s*📖\s*([^\n\r]+)", content_str):
            clean_title = match.strip()
            if clean_title and clean_title not in raw_history:
                raw_history.append(clean_title)
    recommended_history = raw_history[-MAX_RECOMMENDED_HISTORY:]

    negative_constraint_text = ""
    if recommended_history:
        past_list_str = "\n".join(f"- {t}" for t in recommended_history)
        negative_constraint_text = (
            f"\n\n[중복 추천 제외 목록 (최근 이미 추천한 도서)]\n"
            f"{past_list_str}\n"
            f"위 목록에 있는 도서는 이번 턴에서 추천하지 마시고, 다른 적합한 도서를 선택해 주세요."
        )

    weather_context = state.get("weather_context") or "맑음"

    return {
        "curator_request": curator_request,
        "conversation_text": conversation_text,
        "recommended_history": recommended_history,
        "negative_constraint_text": negative_constraint_text,
        "weather_context": weather_context,
    }


async def generate_candidates(
    ctx: Dict[str, Any], open_book_text: str
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """2. Generate book candidates and optional target_title via structured LLM chain."""
    req_count = parse_requested_book_count(ctx.get("curator_request"))

    # Fast mock in testing environment if configured
    if getattr(settings, "app_env", "") == "test" or settings.is_testing:
        req = ctx["curator_request"]
        target = None
        if "프로젝트 헤일메리" in req:
            target = "프로젝트 헤일메리"
        elif "《데미안》" in req or "데미안 등록" in req:
            target = "데미안"

        # Mock candidate catalog pool (up to 10 verified candidates)
        test_catalog = [
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
            {
                "title": "코스모스",
                "author": "칼 세이건",
                "reason": "광대한 우주 속 인류의 숭고한 탐구 여정",
                "era": "classic",
            },
            {
                "title": "모모",
                "author": "미하엘 엔데",
                "reason": "시간의 소중함을 일깨우는 이야기",
                "era": "classic",
            },
            {
                "title": "어린 왕자",
                "author": "앙투안 드 생텍쥐페리",
                "reason": "마음으로 보는 소중한 것들",
                "era": "classic",
            },
            {
                "title": "달러구트 꿈 백화점",
                "author": "이미예",
                "reason": "지친 하루의 끝, 잠든 이들에게 건네는 몽환적인 위로",
                "era": "recent",
            },
            {
                "title": "이방인",
                "author": "알베르 카뮈",
                "reason": "부조리한 세상과 정직하게 맞선 인간의 실존적 초상",
                "era": "classic",
            },
            {
                "title": "소크라테스 익스프레스",
                "author": "에릭 와이너",
                "reason": "14명의 철학자와 함께 떠나는 유쾌한 사유의 여정",
                "era": "classic",
            },
            {
                "title": "사피엔스",
                "author": "유발 하라리",
                "reason": "인류 문명의 기원과 미래",
                "era": "recent",
            },
            {
                "title": "세네카",
                "author": "세네카",
                "reason": "인생의 짧음에 대하여",
                "era": "classic",
            },
        ]
        excluded = set(ctx.get("recommended_history") or [])
        available = [c for c in test_catalog if c["title"] not in excluded]
        if len(available) < req_count:
            available = test_catalog
        return target, available[:req_count]

    chain_llm = get_cached_curator_chain()
    if not chain_llm:
        logger.warning("No configured LLM candidates found. Using random fallback.")
        return None, _get_random_elegant_fallback(ctx["recommended_history"], count=req_count)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CURATOR_SYSTEM_PROMPT),
            (
                "human",
                "최근 대화 맥락:\n{conversation}\n\n"
                "현재 사용자 요청: {request}\n"
                "날씨 컨텍스트: {weather}\n\n"
                "{open_book}"
                "{negative_constraint}",
            ),
        ]
    )
    runnable = prompt | chain_llm

    try:
        response_obj: Any = await asyncio.wait_for(
            runnable.ainvoke(
                {
                    "conversation": ctx.get("conversation_text", "없음"),
                    "request": ctx["curator_request"],
                    "weather": ctx["weather_context"],
                    "open_book": open_book_text,
                    "negative_constraint": ctx["negative_constraint_text"],
                }
            ),
            timeout=35.0,
        )

        target_title: Optional[str] = None
        candidates: List[Dict[str, str]] = []

        if isinstance(response_obj, CuratorResponse):
            target_title = response_obj.target_title
            candidates = [book.model_dump() for book in response_obj.recommendations]
        elif isinstance(response_obj, dict):
            target_title = response_obj.get("target_title")
            candidates = response_obj.get("recommendations", [])

        if candidates:
            return target_title, candidates
    except Exception as e:
        logger.warning("Curator LLM invocation failed (%s). Using fallback.", e)

    return None, _get_random_elegant_fallback(ctx["recommended_history"], count=req_count)


async def _verify_single_candidate(
    cand: Dict[str, Any],
    edition_intent: Optional[str] = "GENERAL",
) -> Optional[Dict[str, Any]]:
    """Verify a single candidate book using hierarchical verification (Cache -> Core API -> National Library).

    1. Cache Check: If edition_intent is provided, lookup Redis/in-memory cache.
    2. Tier 1: Core API (YES24) search with 2.5s timeout.
    3. Tier 2: National Library fallback with 3.5s timeout.
    Enforces Track A (valid ISBN) or Track B (strict 3-condition verification for missing ISBN).
    """
    title = cand.get("title", "")
    author = cand.get("author", "")
    if not title or len(title.strip()) < 2:
        return None

    clean_t = title.strip().strip("《》〈〉「」『』\"'")

    # 1. Cache Check
    cache_key: Optional[str] = None
    if edition_intent is not None:
        cache_key = get_biblio_cache_key(clean_t, author, edition_intent)
        cached = await get_cached_biblio(cache_key)
        if cached:
            logger.info("[BIBLIO_CACHE_HIT] '%s' (%s)", clean_t, cache_key)
            return cached

    # 2. Tier 1: Core API (YES24) Search
    core_client = get_core_api_client()
    try:
        core_items = await asyncio.wait_for(
            core_client.search_books(query=clean_t, limit=5),
            timeout=2.5,
        )
        for item in core_items:
            cand_title = item.get("title", "")
            cand_author = item.get("author", "")

            # Title & Author Matching
            if not _is_similar_title(clean_t, cand_title):
                continue
            if author and not _is_matching_author(author, cand_author):
                continue

            # Check Edition Intent Compatibility
            desc = (item.get("description") or "").lower()
            title_lower = cand_title.lower()
            pub_lower = (item.get("publisher") or "").lower()

            if edition_intent == "COMICS":
                if not any(k in title_lower or k in desc for k in ["만화", "웹툰", "코믹"]):
                    continue
            elif edition_intent == "CHILDREN":
                if not any(
                    k in title_lower or k in desc for k in ["어린이", "아동", "동화", "그림책"]
                ):
                    continue
            elif edition_intent == "ORIGINAL":
                if not any(k in title_lower or k in desc for k in ["원서", "영문", "영어판"]):
                    continue
            elif edition_intent and edition_intent.startswith("PUB:"):
                target_pub = edition_intent.split(":", 1)[1].lower()
                if target_pub not in pub_lower:
                    continue
            elif edition_intent == "GENERAL":
                # Demote explicit comic or children adaptations when general edition is requested
                if any(k in title_lower for k in ["(만화)", "[만화]", "어린이 만화"]):
                    continue

            # ISBN Validation: Track A vs Track B
            norm_isbn, isbn_status = normalize_and_validate_isbn(item.get("isbn"))
            is_valid = False

            if isbn_status in ("VALID_13", "CONVERTED_10"):
                is_valid = True
            elif isbn_status == "MISSING":
                # Track B: Strict 3 conditions must be satisfied
                has_pub = len((item.get("publisher") or "").strip()) >= 2
                has_cover = str(item.get("cover_url") or "").startswith("http")
                has_pages = (item.get("page_count") or 0) > 0
                if has_pub and has_cover and has_pages:
                    is_valid = True
                else:
                    logger.info(
                        "[BIBLIO_REJECT] Core API candidate '%s' missing ISBN failed Track B (pub=%s, cover=%s, pages=%s)",
                        cand_title,
                        has_pub,
                        has_cover,
                        has_pages,
                    )
            else:
                # INVALID ISBN
                logger.info(
                    "[BIBLIO_REJECT] Core API candidate '%s' has INVALID ISBN (%s)",
                    cand_title,
                    item.get("isbn"),
                )

            if is_valid:
                raw_genre = item.get("genre")
                if raw_genre and str(raw_genre).strip().upper() != "NONE":
                    final_genre: Optional[str] = _normalize_to_core_genre(str(raw_genre))
                elif item.get("kdc"):
                    final_genre = map_kdc_to_genre(
                        kdc=str(item.get("kdc")),
                        subject=str(item.get("subject") or ""),
                        title=clean_t,
                    )
                else:
                    final_genre = cand.get("genre")

                verified_data = {
                    "title": item.get("title", clean_t),
                    "author": item.get("author", author or "저자 미상"),
                    "publisher": item.get("publisher", ""),
                    "isbn": norm_isbn or "",
                    "cover_url": item.get("cover_url", ""),
                    "page_count": item.get("page_count"),
                    "genre": final_genre,
                    "description": item.get("description") or cand.get("reason", ""),
                    "reason": cand.get("reason", ""),
                    "era": cand.get("era", "classic"),
                    "verified": True,
                    "source": "CORE_API",
                }
                if cache_key:
                    await set_cached_biblio(cache_key, verified_data)
                logger.info(
                    "[BIBLIO_SUCCESS] Core API verified '%s' (ISBN: %s, Source: CORE_API)",
                    clean_t,
                    norm_isbn or "Track-B",
                )
                return verified_data
    except Exception as e:
        logger.info("[BIBLIO_FALLBACK] Core API search failed/timed out for '%s' (%s)", clean_t, e)

    # 3. Tier 2: National Library Fallback Search
    logger.info("[BIBLIO_FALLBACK] Falling back to National Library for '%s'", clean_t)
    nl_client = get_national_library_client()
    try:
        biblio = await asyncio.wait_for(
            nl_client.search_book(title=clean_t, author=author),
            timeout=3.5,
        )
        if biblio:
            found_title = biblio.get("title", "")
            found_author = biblio.get("author", "")

            # Title & Author Matching
            if not _is_similar_title(clean_t, found_title):
                logger.info(
                    "[BIBLIO_REJECT] National Library title mismatch for '%s' (found '%s')",
                    clean_t,
                    found_title,
                )
                return None
            if author and not _is_matching_author(author, found_author):
                logger.info(
                    "[BIBLIO_REJECT] National Library author mismatch for '%s' (expected '%s', found '%s')",
                    clean_t,
                    author,
                    found_author,
                )
                return None

            # ISBN Validation: Track A vs Track B
            norm_isbn, isbn_status = normalize_and_validate_isbn(biblio.get("isbn"))
            is_valid = False

            if isbn_status in ("VALID_13", "CONVERTED_10"):
                is_valid = True
            elif isbn_status == "MISSING":
                has_pub = len((biblio.get("publisher") or "").strip()) >= 2
                has_cover = str(biblio.get("cover_url") or "").startswith("http")
                has_pages = (biblio.get("page_count") or 0) > 0
                if has_pub and has_cover and has_pages:
                    is_valid = True
                else:
                    logger.info(
                        "[BIBLIO_REJECT] National Library candidate '%s' failed Track B",
                        clean_t,
                    )
            else:
                logger.info(
                    "[BIBLIO_REJECT] National Library candidate '%s' has INVALID ISBN (%s)",
                    clean_t,
                    biblio.get("isbn"),
                )

            if is_valid:
                verified_data = {
                    "title": biblio.get("title", clean_t),
                    "author": biblio.get("author", author or "저자 미상"),
                    "publisher": biblio.get("publisher", ""),
                    "isbn": norm_isbn or "",
                    "cover_url": biblio.get("cover_url", ""),
                    "page_count": biblio.get("page_count"),
                    "genre": biblio.get("genre") or cand.get("genre"),
                    "description": biblio.get("description", cand.get("reason", "")),
                    "reason": cand.get("reason", ""),
                    "era": cand.get("era", "classic"),
                    "verified": True,
                    "source": "NATIONAL_LIBRARY",
                }
                if cache_key:
                    await set_cached_biblio(cache_key, verified_data)
                logger.info(
                    "[BIBLIO_SUCCESS] National Library verified '%s' (ISBN: %s, Source: NATIONAL_LIBRARY)",
                    clean_t,
                    norm_isbn or "Track-B",
                )
                return verified_data
    except Exception as e:
        logger.warning("National Library verification failed for '%s' (%s)", clean_t, e)

    logger.warning("[BIBLIO_REJECT] Verification completely failed for '%s'", clean_t)
    return None


async def resolve_targeted(
    target_title: Optional[str],
    edition_intent: Optional[str] = "GENERAL",
) -> Optional[Dict[str, Any]]:
    """3. Verify targeted book directly using hierarchical verification."""
    if not target_title or len(target_title.strip()) < 2:
        return None

    clean_target = target_title.strip().strip("《》〈〉「」『』\"'")
    cand = {
        "title": clean_target,
        "author": "",
        "reason": f"사용자께서 직접 서재 등록 및 추천을 요청하신 도서 《{clean_target}》입니다.",
        "era": "targeted",
    }
    verified = await _verify_single_candidate(cand, edition_intent=edition_intent)
    if verified:
        verified["description"] = f"요청하신 도서 《{verified['title']}》의 정식 서지 정보입니다."
        verified["reason"] = (
            f"사용자께서 직접 서재 등록 및 추천을 요청하신 도서 《{verified['title']}》입니다."
        )
        verified["era"] = "targeted"
        return verified
    return None


async def verify_candidates(
    candidates: List[Dict[str, Any]],
    edition_intent: Optional[str] = "GENERAL",
) -> List[Dict[str, Any]]:
    """4. Parallel hierarchical verification of candidates (asyncio.gather)."""
    results = await asyncio.gather(
        *[_verify_single_candidate(c, edition_intent=edition_intent) for c in candidates],
        return_exceptions=True,
    )
    verified: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, dict) and r.get("verified"):
            verified.append(r)
    return verified


async def assemble_curated_books(
    targeted: Optional[Dict[str, Any]],
    verified: List[Dict[str, Any]],
    recommended_history: List[str],
    requested_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """5. Assemble verified books without forced fallback injections.

    Returns only books that successfully passed bibliography verification.
    If verified books are fewer than requested, returns only the verified books
    without fabricating or forcing classic fallback books.
    """
    final_books: List[Dict[str, Any]] = []

    # Priority 1: Targeted book if present
    if targeted:
        final_books.append(targeted)

    # Add verified books that don't duplicate the targeted book or recently recommended history
    for b in verified:
        if requested_count is not None and len(final_books) >= requested_count:
            break
        b_title = str(b.get("title", ""))
        b_isbn = str(b.get("isbn", ""))
        if any(
            fb.get("title") == b_title or (fb.get("isbn") and fb.get("isbn") == b_isbn)
            for fb in final_books
        ):
            continue
        # Deduplicate against recommended_history (unless explicitly targeted)
        if any(_is_similar_title(b_title, hist) for hist in recommended_history):
            continue
        final_books.append(b)

    # NOTE: Forced classic fallback injection (if len(final_books) < 2) is completely removed.
    # We strictly return only books verified in the national library bibliography.

    if requested_count is not None:
        return final_books[:requested_count]
    return final_books


async def book_curator_node(state: AgentState) -> Dict[str, Any]:
    """Orchestrate the 5-stage book curation pipeline with zero heuristic regexes."""
    logger.info("book_curator_node invoked for member_id=%s", state.get("member_id"))

    # Stage 1: Resolve Context
    ctx = resolve_context(state)
    requested_count = parse_requested_book_count(ctx["curator_request"])
    edition_intent = extract_edition_intent(ctx["curator_request"])

    # Fetch trending open-book catalog
    open_book_text = await get_trending_books_text(limit=30)

    # Stage 2: Generate Candidates & Target Title via Structured LLM
    target_title, raw_candidates = await generate_candidates(ctx, open_book_text)

    # Stage 3 & 4: Resolve Targeted Book and Candidates in Parallel
    targeted_task = resolve_targeted(target_title, edition_intent=edition_intent)

    # Check if raw_candidates are already emergency fallback books
    is_fallback_candidates = any(c.get("fallback") for c in raw_candidates)
    if is_fallback_candidates:
        targeted_book = await targeted_task
        verified_books = []
    else:
        candidates_task = verify_candidates(raw_candidates, edition_intent=edition_intent)
        targeted_book, verified_books = await asyncio.gather(targeted_task, candidates_task)

    # Stage 5: Assemble Verified Books (async)
    curated_books = await assemble_curated_books(
        targeted=targeted_book,
        verified=verified_books,
        recommended_history=ctx["recommended_history"],
        requested_count=requested_count,
    )

    # Update recommended history
    new_history = list(ctx["recommended_history"])
    for b in curated_books:
        t = b.get("title")
        if t and t not in new_history:
            new_history.append(t)
    new_history = new_history[-MAX_RECOMMENDED_HISTORY:]

    # Check if a target book was requested but could not be verified
    target_unresolved = None
    if target_title and not targeted_book:
        target_unresolved = target_title

    logger.info("Curator successfully assembled %d books.", len(curated_books))

    return {
        "curated_books": curated_books,
        "curator_request": None,
        "curator_attempted": True,
        "recommended_history": new_history,
        "target_unresolved": target_unresolved,
    }
