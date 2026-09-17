"""Google Gemini Flash Vision based Book Sentence Scraping OCR Client."""

import base64
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_OCR_SYSTEM_PROMPT = """당신은 '책 문장 스크랩 전문 OCR 추출기'입니다.
업로드된 도서 사진에서 독자가 기록하고 기억하고자 하는 본문 문장을 정확하게 추출해야 합니다.

[추출 규칙]
1. 사진에 인쇄된 한국어 및 외국어 책 본문 텍스트를 원문 그대로 정확하게 추출하세요.
2. 각 행의 줄바꿈(\\n)과 문단 호흡을 자연스럽게 유지하세요.
3. 책 상/하단의 페이지 번호(예: - 123 -, p.45), 챕터 헤더, 여백의 잡음, 손가락/그림자 등은 본문 내용이 아니므로 절대 추출에 포함하지 마세요.
4. 오직 추출된 본문 텍스트만 출력하세요. 어떠한 인사말, 안내문, 코드블록(```), 따옴표도 붙이지 마세요.
"""

GEMINI_COVER_SYSTEM_PROMPT = """당신은 '도서 표지/뒷표지 서지 정보 및 바코드 ISBN 전문 인식기'입니다.
업로드된 책 표지 또는 뒷표지 사진을 정밀 분석하여 다음 정보를 JSON 형식으로 추출하세요.

[핵심 추출 지침]
1. isbn: 바코드 하단 또는 주변에 인쇄된 13자리 숫자(978 또는 979로 시작하는 ISBN)를 정확히 읽어내세요. 하이픈이나 공백이 있어도 괜찮습니다. 바코드 선 자체보다 그 밑에 적힌 인쇄 숫자를 사람 눈처럼 똑똑하게 읽으세요.
2. title: 도서 정식 제목 (앞표지에서 가장 크고 굵게 강조된 실제 책 이름).
   ⚠️ [뒷표지 방어 규칙]: 만약 사진에 '추천사', '리뷰', '가격(원)', '바코드' 등이 주로 보인다면 이는 책의 '뒷표지'입니다. 뒷표지의 자극적인 홍보 문구(예: "올해 최고의 감동!", "100만 독자가 극찬한 책")를 절대 도서 제목으로 착각하지 마세요! 도서 정식 명칭을 100% 명확히 식별할 수 없다면 title에는 반드시 null을 반환하세요.
3. author: 저자명 (지은이, 글, 저자 표기). 명확하지 않으면 null을 반환하세요.
4. publisher: 출판사명. 명확하지 않으면 null을 반환하세요.
5. lines: 사진에서 식별된 주요 텍스트 줄 목록.

[출력 형식]
반드시 마크다운 코드블록(```)이나 부연 설명 없이, 오직 아래 JSON 규격으로만 출력하세요:
{
  "isbn": "9788934939603 또는 null",
  "title": "도서 제목 또는 null",
  "author": "저자명 또는 null",
  "publisher": "출판사명 또는 null",
  "lines": ["식별된 텍스트 줄 1", "줄 2"]
}
"""


class GeminiOcrResult(BaseModel):
    """Result of Gemini Flash Vision OCR text extraction."""

    text: str
    lines: List[str]
    request_id: str
    confidence: Optional[float] = None


class CoverOcrResult(BaseModel):
    """Structured result of book cover / back cover OCR extraction."""

    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    lines: List[str] = []
    raw_text: str = ""
    request_id: str = ""


class GeminiOcrClient:
    """Client for Google Gemini Flash Vision based OCR with OpenAI fallback."""

    def __init__(self) -> None:
        self.gemini_api_key = settings.gemini_api_key.strip()
        self.gemini_fallback_api_key = getattr(settings, "gemini_fallback_api_key", "").strip()
        self.gemini_model = settings.gemini_model
        self.gemini_light_model = getattr(settings, "gemini_light_model", "gemini-3.1-flash-lite")
        self.openai_api_key = settings.openai_api_key.strip()
        self.openai_model = settings.openai_model

    def _normalize_mime_type(self, image_format: str) -> str:
        fmt = image_format.lower()
        if "png" in fmt:
            return "image/png"
        if "webp" in fmt:
            return "image/webp"
        if "gif" in fmt:
            return "image/gif"
        return "image/jpeg"

    async def extract_text(
        self, image_bytes: bytes, image_format: str = "image/jpeg"
    ) -> GeminiOcrResult:
        """Extract text from book image using Gemini Flash Vision (or OpenAI fallback)."""
        request_id = str(uuid.uuid4())

        # 1. Check if Gemini keys are available
        has_gemini = bool(
            self.gemini_api_key
            and not self.gemini_api_key.startswith("your_")
            and len(self.gemini_api_key) > 10
        )
        has_fallback_gemini = bool(
            self.gemini_fallback_api_key
            and not self.gemini_fallback_api_key.startswith("your_")
            and len(self.gemini_fallback_api_key) > 10
        )
        has_openai = bool(
            self.openai_api_key
            and not self.openai_api_key.startswith("your_")
            and len(self.openai_api_key) > 10
        )

        if not has_gemini and not has_fallback_gemini and not has_openai:
            logger.warning("Neither Gemini nor OpenAI API keys are configured for OCR.")
            return GeminiOcrResult(
                text="테스트 모드: Gemini OCR 설정이 되어 있지 않습니다.",
                lines=["테스트 모드: Gemini OCR 설정이 되어 있지 않습니다."],
                request_id=request_id,
                confidence=1.0,
            )

        mime_type = self._normalize_mime_type(image_format)
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{image_b64}"

        from typing import Union

        human_content: List[Union[str, Dict[Any, Any]]] = [
            {
                "type": "text",
                "text": "이 책 사진에서 페이지 번호와 주변 잡음을 제외하고, 밑줄/본문 문장 텍스트를 줄바꿈을 살려 원문 그대로 추출해주세요.",
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            },
        ]

        messages: List[Any] = [
            SystemMessage(content=GEMINI_OCR_SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

        extracted_text = ""

        # Candidates to try: (1) Light Model with Primary Key, (2) Light Model with Fallback Key, (3) 3.5 Model, (4) OpenAI
        candidate_configs: List[Dict[str, Any]] = []
        if has_gemini:
            candidate_configs.append(
                {"provider": "gemini", "model": self.gemini_light_model, "key": self.gemini_api_key}
            )
        if has_fallback_gemini:
            candidate_configs.append(
                {
                    "provider": "gemini",
                    "model": self.gemini_light_model,
                    "key": self.gemini_fallback_api_key,
                }
            )
        if has_gemini:
            candidate_configs.append(
                {"provider": "gemini", "model": self.gemini_model, "key": self.gemini_api_key}
            )
        if has_openai:
            candidate_configs.append(
                {"provider": "openai", "model": self.openai_model, "key": self.openai_api_key}
            )

        for cfg in candidate_configs:
            try:
                if cfg["provider"] == "gemini":
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    gemini_llm = ChatGoogleGenerativeAI(
                        model=cfg["model"],
                        google_api_key=cfg["key"],
                    )
                    res = await gemini_llm.ainvoke(messages)
                    content = getattr(res, "content", "")
                    if isinstance(content, list):
                        extracted_text = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                    else:
                        extracted_text = str(content)
                elif cfg["provider"] == "openai":
                    from langchain_openai import ChatOpenAI
                    from pydantic import SecretStr

                    openai_llm = ChatOpenAI(
                        model=cfg["model"],
                        api_key=SecretStr(cfg["key"]),
                        temperature=0.0,
                    )
                    res = await openai_llm.ainvoke(messages)
                    content = getattr(res, "content", "")
                    if isinstance(content, list):
                        extracted_text = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                    else:
                        extracted_text = str(content)

                if extracted_text.strip():
                    break
            except Exception as e:
                logger.warning(
                    "OCR candidate failed for provider=%s, model=%s (%s). Trying next.",
                    cfg["provider"],
                    cfg["model"],
                    e,
                )

        # Clean markdown codeblocks if any
        clean_text = extracted_text.strip()
        clean_text = re.sub(r"^```(?:text|markdown)?\s*", "", clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE).strip()

        if not clean_text:
            clean_text = "텍스트를 인식하지 못했습니다. 이미지가 선명한지 확인해 주세요."

        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        if not lines:
            lines = [clean_text]

        return GeminiOcrResult(
            text=clean_text,
            lines=lines,
            request_id=request_id,
            confidence=0.98 if clean_text else 0.0,
        )

    async def extract_cover_info(
        self, image_bytes: bytes, image_format: str = "image/jpeg"
    ) -> CoverOcrResult:
        """Extract book metadata (ISBN, title, author, publisher, lines) from cover/back cover using Vision AI."""
        import json

        from app.vision.isbn_utils import extract_isbn_candidates

        request_id = str(uuid.uuid4())

        has_gemini = bool(
            self.gemini_api_key
            and not self.gemini_api_key.startswith("your_")
            and len(self.gemini_api_key) > 10
        )
        has_fallback_gemini = bool(
            self.gemini_fallback_api_key
            and not self.gemini_fallback_api_key.startswith("your_")
            and len(self.gemini_fallback_api_key) > 10
        )
        has_openai = bool(
            self.openai_api_key
            and not self.openai_api_key.startswith("your_")
            and len(self.openai_api_key) > 10
        )

        if not has_gemini and not has_fallback_gemini and not has_openai:
            logger.warning("Neither Gemini nor OpenAI API keys are configured for Cover OCR.")
            return CoverOcrResult(
                request_id=request_id,
                raw_text="테스트 모드: Vision OCR 키가 설정되어 있지 않습니다.",
            )

        mime_type = self._normalize_mime_type(image_format)
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{image_b64}"

        from typing import Union

        human_content: List[Union[str, Dict[Any, Any]]] = [
            {
                "type": "text",
                "text": (
                    "이 책 표지 또는 뒷표지 사진에서 바코드 아래에 인쇄된 13자리 ISBN 숫자, "
                    "책 제목, 저자명, 출판사명 및 주요 텍스트를 정확하게 추출하여 JSON 형식으로 반환하세요."
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            },
        ]

        messages: List[Any] = [
            SystemMessage(content=GEMINI_COVER_SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

        raw_response = ""
        candidate_configs: List[Dict[str, Any]] = []
        if has_gemini:
            candidate_configs.append(
                {"provider": "gemini", "model": self.gemini_light_model, "key": self.gemini_api_key}
            )
        if has_fallback_gemini:
            candidate_configs.append(
                {
                    "provider": "gemini",
                    "model": self.gemini_light_model,
                    "key": self.gemini_fallback_api_key,
                }
            )
        if has_gemini:
            candidate_configs.append(
                {"provider": "gemini", "model": self.gemini_model, "key": self.gemini_api_key}
            )
        if has_openai:
            candidate_configs.append(
                {"provider": "openai", "model": self.openai_model, "key": self.openai_api_key}
            )

        for cfg in candidate_configs:
            try:
                if cfg["provider"] == "gemini":
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    gemini_llm = ChatGoogleGenerativeAI(
                        model=cfg["model"],
                        google_api_key=cfg["key"],
                    )
                    res = await gemini_llm.ainvoke(messages)
                    content = getattr(res, "content", "")
                    raw_response = (
                        "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                        if isinstance(content, list)
                        else str(content)
                    )
                elif cfg["provider"] == "openai":
                    from langchain_openai import ChatOpenAI
                    from pydantic import SecretStr

                    openai_llm = ChatOpenAI(
                        model=cfg["model"],
                        api_key=SecretStr(cfg["key"]),
                        temperature=0.0,
                    )
                    res = await openai_llm.ainvoke(messages)
                    content = getattr(res, "content", "")
                    raw_response = (
                        "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                        if isinstance(content, list)
                        else str(content)
                    )

                if raw_response.strip():
                    break
            except Exception as e:
                logger.warning(
                    "Cover OCR candidate failed for provider=%s, model=%s (%s). Trying next.",
                    cfg["provider"],
                    cfg["model"],
                    e,
                )

        clean_resp = raw_response.strip()
        clean_resp = re.sub(r"^```(?:json)?\s*", "", clean_resp, flags=re.MULTILINE)
        clean_resp = re.sub(r"\s*```$", "", clean_resp, flags=re.MULTILINE).strip()

        parsed_data: Dict[str, Any] = {}
        try:
            # Look for JSON object substring
            json_match = re.search(r"\{.*\}", clean_resp, flags=re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(0))
        except Exception as err:
            logger.debug("Failed to parse Cover OCR as pure JSON (%s). Using text extraction.", err)

        isbn = parsed_data.get("isbn") if isinstance(parsed_data, dict) else None
        title = parsed_data.get("title") if isinstance(parsed_data, dict) else None
        author = parsed_data.get("author") if isinstance(parsed_data, dict) else None
        publisher = parsed_data.get("publisher") if isinstance(parsed_data, dict) else None
        lines = parsed_data.get("lines") if isinstance(parsed_data, dict) else []

        if not isinstance(lines, list):
            lines = [str(lines)] if lines else []

        # If lines are empty, fallback to raw response split lines
        if not lines and clean_resp:
            lines = [
                line.strip()
                for line in clean_resp.splitlines()
                if line.strip() and not line.startswith("{")
            ]

        # Secondary search for ISBN inside raw response or lines
        if not isbn:
            isbn_cands = extract_isbn_candidates(clean_resp)
            if isbn_cands:
                isbn = isbn_cands[0]

        return CoverOcrResult(
            isbn=str(isbn).strip() if isbn else None,
            title=str(title).strip() if title else None,
            author=str(author).strip() if author else None,
            publisher=str(publisher).strip() if publisher else None,
            lines=[str(line).strip() for line in lines if str(line).strip()],
            raw_text=clean_resp,
            request_id=request_id,
        )


gemini_ocr_client = GeminiOcrClient()

# Backward compatibility aliases
ClovaOcrResult = GeminiOcrResult
ClovaOcrClient = GeminiOcrClient
clova_ocr_client = gemini_ocr_client
