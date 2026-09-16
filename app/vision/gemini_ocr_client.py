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


class GeminiOcrResult(BaseModel):
    """Result of Gemini Flash Vision OCR text extraction."""

    text: str
    lines: List[str]
    request_id: str
    confidence: Optional[float] = None


class GeminiOcrClient:
    """Client for Google Gemini Flash Vision based OCR with OpenAI fallback."""

    def __init__(self) -> None:
        self.gemini_api_key = settings.gemini_api_key.strip()
        self.gemini_model = settings.gemini_model
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

        # 1. Check if Gemini key is available
        has_gemini = bool(
            self.gemini_api_key
            and not self.gemini_api_key.startswith("your_")
            and len(self.gemini_api_key) > 10
        )
        has_openai = bool(
            self.openai_api_key
            and not self.openai_api_key.startswith("your_")
            and len(self.openai_api_key) > 10
        )

        if not has_gemini and not has_openai:
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

        # 2. Try Primary LLM: Google Gemini Flash Vision
        if has_gemini:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                gemini_llm = ChatGoogleGenerativeAI(
                    model=self.gemini_model,
                    google_api_key=self.gemini_api_key,
                    temperature=0.0,
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
            except Exception as e:
                logger.warning("Gemini Vision OCR call failed (%s). Attempting OpenAI fallback.", e)

        # 3. Try Secondary LLM: OpenAI gpt-4o-mini Vision fallback
        if not extracted_text.strip() and has_openai:
            try:
                from langchain_openai import ChatOpenAI
                from pydantic import SecretStr

                openai_llm = ChatOpenAI(
                    model=self.openai_model,
                    api_key=SecretStr(self.openai_api_key),
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
            except Exception as e:
                logger.error("OpenAI Vision OCR fallback also failed (%s).", e)

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


gemini_ocr_client = GeminiOcrClient()

# Backward compatibility aliases
ClovaOcrResult = GeminiOcrResult
ClovaOcrClient = GeminiOcrClient
clova_ocr_client = gemini_ocr_client
