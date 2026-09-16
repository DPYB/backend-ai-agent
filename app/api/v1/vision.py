"""Vision API endpoints for Barcode Scanning and Google Gemini Flash Vision OCR."""

from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.vision.barcode_service import barcode_service
from app.vision.gemini_ocr_client import gemini_ocr_client

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


class BarcodeScanResponse(BaseModel):
    """Barcode scanning result payload."""

    isbn: Optional[str] = Field(default=None, description="추출된 13자리 도서 ISBN (없으면 null)")
    found: bool = Field(description="바코드 인식 성공 여부")


class OcrResponse(BaseModel):
    """Gemini Flash Vision OCR text extraction result payload."""

    text: str = Field(description="줄바꿈으로 합쳐진 전체 OCR 텍스트")
    lines: List[str] = Field(description="줄단위 텍스트 목록")
    confidence: Optional[float] = Field(default=None, description="인식 신뢰도")
    request_id: str = Field(description="요청 식별자")


@router.post("/scan-barcode", response_model=BarcodeScanResponse)
async def scan_barcode(image: UploadFile = File(...)) -> BarcodeScanResponse:
    """책 바코드 이미지(EAN13)로부터 ISBN-13 추출."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )

    image_bytes = await image.read()
    isbn = barcode_service.scan_isbn(image_bytes)
    return BarcodeScanResponse(isbn=isbn, found=(isbn is not None))


@router.post("/ocr", response_model=OcrResponse)
async def perform_ocr(image: UploadFile = File(...)) -> OcrResponse:
    """책 문장 이미지에서 Google Gemini Flash Vision 지능형 OCR 텍스트 추출."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )

    image_bytes = await image.read()
    result = await gemini_ocr_client.extract_text(image_bytes, image.content_type)
    return OcrResponse(
        text=result.text,
        lines=result.lines,
        confidence=result.confidence,
        request_id=result.request_id,
    )
