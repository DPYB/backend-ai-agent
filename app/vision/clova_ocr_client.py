"""Naver Cloud Clova OCR General API V2 client."""

import base64
import logging
import time
import uuid
from typing import List, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClovaOcrResult(BaseModel):
    """Result of Naver Clova OCR text extraction."""

    text: str
    lines: List[str]
    request_id: str
    confidence: Optional[float] = None


class ClovaOcrClient:
    """Client for Naver Cloud Clova OCR General API V2."""

    def __init__(self):
        self.url = settings.naver_clova_api_url
        self.secret_key = settings.naver_clova_secret_key

    async def extract_text(self, image_bytes: bytes, image_format: str = "jpg") -> ClovaOcrResult:
        """Call Naver Clova OCR API and parse text into structured line-by-line output."""
        if not self.url or not self.secret_key:
            logger.warning("Naver Clova OCR credentials are not configured.")
            # Graceful fallback for test/offline environments
            return ClovaOcrResult(
                text="테스트 모드: Clova OCR 설정이 되어 있지 않습니다.",
                lines=["테스트 모드: Clova OCR 설정이 되어 있지 않습니다."],
                request_id=str(uuid.uuid4()),
                confidence=1.0,
            )

        request_id = str(uuid.uuid4())
        image_base64 = base64.b64encode(image_bytes).decode("ascii")

        body = {
            "version": "V2",
            "requestId": request_id,
            "timestamp": int(time.time() * 1000),
            "lang": "ko",
            "images": [
                {
                    "format": "jpg" if "jp" in image_format.lower() else "png",
                    "name": "reading-sentence",
                    "data": image_base64,
                }
            ],
            "enableTableDetection": False,
        }
        headers = {
            "X-OCR-SECRET": self.secret_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

        image_res = data["images"][0]
        fields = image_res.get("fields", [])
        lines: List[str] = []
        current_line: List[str] = []
        confidences: List[float] = []

        for f in fields:
            txt = f.get("inferText", "").strip()
            if txt:
                current_line.append(txt)
            if "inferConfidence" in f:
                confidences.append(float(f["inferConfidence"]))
            if f.get("lineBreak"):
                lines.append(" ".join(current_line))
                current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        full_text = "\n".join(lines)
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else None

        return ClovaOcrResult(
            text=full_text,
            lines=lines,
            request_id=request_id,
            confidence=round(avg_confidence, 4) if avg_confidence else None,
        )


clova_ocr_client = ClovaOcrClient()
