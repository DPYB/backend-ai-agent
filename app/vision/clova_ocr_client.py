"""Backward-compatibility module redirecting to gemini_ocr_client."""

from app.vision.gemini_ocr_client import (
    ClovaOcrClient,
    ClovaOcrResult,
    GeminiOcrClient,
    GeminiOcrResult,
    clova_ocr_client,
    gemini_ocr_client,
)

__all__ = [
    "ClovaOcrClient",
    "ClovaOcrResult",
    "clova_ocr_client",
    "GeminiOcrClient",
    "GeminiOcrResult",
    "gemini_ocr_client",
]
