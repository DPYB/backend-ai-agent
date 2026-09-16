"""Vision API endpoints for Barcode Scanning and Google Gemini Flash Vision OCR."""

import base64
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.vision.barcode_service import barcode_service
from app.vision.gemini_ocr_client import gemini_ocr_client

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])
ocr_router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


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


class OcrSentenceResponse(BaseModel):
    """Sentence OCR response matching frontend recordApi expectations."""

    text: str = Field(description="추출된 문장 텍스트")
    lines: List[str] = Field(default_factory=list, description="줄단위 텍스트 목록")
    scrap_image_url: Optional[str] = Field(default=None, description="스크랩 이미지 Data URL")
    scrap_id: Optional[int] = Field(default=None, description="저장된 스크랩 ID (기본 null)")


class OcrCoverResponse(BaseModel):
    """Cover/barcode OCR response matching frontend recordApi expectations."""

    isbn: Optional[str] = Field(default=None, description="인식된 ISBN")
    title_candidate: str = Field(default="", description="제목 후보")
    author_candidates: List[str] = Field(default_factory=list, description="저자 후보 목록")
    lines: List[str] = Field(default_factory=list, description="인식된 줄 목록")
    book: Optional[Dict[str, Any]] = Field(default=None, description="조회된 도서 메타데이터")
    already_registered: bool = Field(default=False, description="서재 중복 등록 여부")


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


async def _handle_sentence_ocr(
    image: UploadFile,
    book_id: Optional[str] = None,
    page_number: Optional[str] = None,
    memo: Optional[str] = None,
    save_scrap: bool = False,
) -> OcrSentenceResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )
    image_bytes = await image.read()
    result = await gemini_ocr_client.extract_text(image_bytes, image.content_type)
    b64_str = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{image.content_type};base64,{b64_str}"
    return OcrSentenceResponse(
        text=result.text,
        lines=result.lines,
        scrap_image_url=data_url,
        scrap_id=None,
    )


async def _handle_cover_ocr(image: UploadFile) -> OcrCoverResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )
    image_bytes = await image.read()
    isbn = barcode_service.scan_isbn(image_bytes)

    lines: List[str] = []
    title_cand = ""
    author_cand: List[str] = []

    if not isbn:
        result = await gemini_ocr_client.extract_text(image_bytes, image.content_type)
        lines = result.lines
        for line in lines:
            digits = re.sub(r"\D", "", line)
            match = re.search(r"97[89]\d{10}", digits)
            if match:
                isbn = match.group(0)
                break
        if lines:
            title_cand = lines[0]
            if len(lines) > 1:
                author_cand = [lines[1]]

    book_info: Optional[Dict[str, Any]] = None
    if isbn:
        from app.infrastructure.national_library_client import get_national_library_client

        nl_client = get_national_library_client()
        book_doc = await nl_client.search_by_isbn(isbn)
        if book_doc:
            title_cand = book_doc.get("title", title_cand)
            if book_doc.get("author"):
                author_cand = [str(book_doc.get("author"))]
            book_info = {
                "title": book_doc.get("title"),
                "author": book_doc.get("author"),
                "isbn": isbn,
                "publisher": book_doc.get("publisher"),
                "totalPages": book_doc.get("page_count"),
                "coverUrl": book_doc.get("cover_url"),
                "genre": book_doc.get("genre"),
            }

    return OcrCoverResponse(
        isbn=isbn,
        title_candidate=title_cand,
        author_candidates=author_cand,
        lines=lines,
        book=book_info,
        already_registered=False,
    )


@ocr_router.post("/sentences", response_model=OcrSentenceResponse)
async def perform_ocr_sentence(
    image: UploadFile = File(...),
    book_id: Optional[str] = Form(None),
    page_number: Optional[str] = Form(None),
    memo: Optional[str] = Form(None),
    save_scrap: bool = Query(False),
) -> OcrSentenceResponse:
    """문장 스크랩 이미지 OCR 추출 (하위 호환)."""
    return await _handle_sentence_ocr(image, book_id, page_number, memo, save_scrap)


@ocr_router.post("/covers", response_model=OcrCoverResponse)
async def perform_ocr_cover(
    image: UploadFile = File(...),
) -> OcrCoverResponse:
    """표지/바코드 이미지에서 ISBN 및 도서 메타데이터 인식 (하위 호환)."""
    return await _handle_cover_ocr(image)


@router.post("/ocr/sentences", response_model=OcrSentenceResponse)
async def perform_vision_ocr_sentence(
    image: UploadFile = File(...),
    book_id: Optional[str] = Form(None),
    page_number: Optional[str] = Form(None),
    memo: Optional[str] = Form(None),
    save_scrap: bool = Query(False),
) -> OcrSentenceResponse:
    return await _handle_sentence_ocr(image, book_id, page_number, memo, save_scrap)


@router.post("/ocr/covers", response_model=OcrCoverResponse)
async def perform_vision_ocr_cover(
    image: UploadFile = File(...),
) -> OcrCoverResponse:
    return await _handle_cover_ocr(image)
