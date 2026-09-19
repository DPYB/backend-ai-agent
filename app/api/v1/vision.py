"""Vision API endpoints for Barcode Scanning and Google Gemini Flash Vision OCR."""

import base64
import io
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from PIL import Image
from pydantic import BaseModel, Field

from app.vision.barcode_service import barcode_service
from app.vision.gemini_ocr_client import gemini_ocr_client

logger = logging.getLogger(__name__)


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


def _crop_image_if_requested(image_bytes: bytes, crop_box: Optional[str]) -> bytes:
    """JSON 형식의 crop_box [x, y, width, height] 또는 [left, top, right, bottom]이 주어지면 Pillow로 자르기."""
    if not crop_box or not crop_box.strip():
        return image_bytes
    try:
        data = json.loads(crop_box)
        if isinstance(data, dict):
            left = float(data.get("x", 0))
            top = float(data.get("y", 0))
            width = float(data.get("width", 0))
            height = float(data.get("height", 0))
            right = left + width
            bottom = top + height
        elif isinstance(data, (list, tuple)) and len(data) == 4:
            left, top, right, bottom = [float(v) for v in data]
        else:
            logger.warning("유효하지 않은 crop_box 형식: %s", crop_box)
            return image_bytes

        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            img_w, img_h = pil_img.size
            # 0.0 ~ 1.0 정규화 비율 좌표인 경우 실제 픽셀로 변환
            if 0.0 <= left <= 1.0 and 0.0 <= top <= 1.0 and right <= 1.0 and bottom <= 1.0:
                left = left * img_w
                top = top * img_h
                right = right * img_w
                bottom = bottom * img_h

            # 바운더리 클램핑
            left = max(0, min(int(left), img_w - 1))
            top = max(0, min(int(top), img_h - 1))
            right = max(left + 1, min(int(right), img_w))
            bottom = max(top + 1, min(int(bottom), img_h))

            cropped = pil_img.crop((left, top, right, bottom))
            out_buf = io.BytesIO()
            # 원본 포맷 유지 (기본 JPEG)
            img_format = pil_img.format or "JPEG"
            cropped.save(out_buf, format=img_format)
            logger.info(
                "서버 사이드 이미지 크롭 완료: (%d, %d, %d, %d) on %s",
                left,
                top,
                right,
                bottom,
                pil_img.size,
            )
            return out_buf.getvalue()
    except Exception as exc:
        logger.warning("crop_box 처리 실패, 원본 이미지 유지: %s", exc)
        return image_bytes


async def _handle_sentence_ocr(
    image: UploadFile,
    book_id: Optional[str] = None,
    page_number: Optional[str] = None,
    memo: Optional[str] = None,
    save_scrap: bool = False,
    crop_box: Optional[str] = None,
) -> OcrSentenceResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )
    raw_bytes = await image.read()
    image_bytes = _crop_image_if_requested(raw_bytes, crop_box)
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

    from app.infrastructure.national_library_client import get_national_library_client

    nl_client = get_national_library_client()

    # -------------------------------------------------------------
    # [1단계]: 바코드(ISBN) 무조건 최우선 탐색 (OpenCV 리사이즈 + 대비 + 4방향 회전)
    # -------------------------------------------------------------
    isbn = barcode_service.scan_isbn(image_bytes)

    lines: List[str] = []
    title_cand = ""
    author_cand: List[str] = []
    book_info: Optional[Dict[str, Any]] = None

    if isbn:
        # [핵심 방어]: ISBN 바코드가 잡혔으면 OCR은 쳐다보지도 말고 바로 도서관 API로 직행!
        # 뒷표지의 추천사나 광고 문구("올해 최고의 감동!")가 제목으로 오인되는 것을 100% 원천 차단
        logger.info("바코드 ISBN %s 검출 성공. OCR 텍스트 무시하고 서지 DB 직행.", isbn)
        book_doc = await nl_client.fetch_and_fill_book_info_by_isbn(isbn)
        if book_doc:
            title_cand = book_doc.get("title", "")
            if book_doc.get("author"):
                author_cand = [str(book_doc.get("author"))]
            book_info = {
                "title": book_doc.get("title"),
                "author": book_doc.get("author"),
                "isbn": isbn,
                "publisher": book_doc.get("publisher"),
                "totalPages": book_doc.get("page_count") or 0,
                "coverUrl": book_doc.get("cover_url"),
                "genre": book_doc.get("genre"),
            }

        return OcrCoverResponse(
            isbn=isbn,
            title_candidate=title_cand,
            author_candidates=author_cand,
            lines=[],
            book=book_info,
            already_registered=False,
        )

    # -------------------------------------------------------------
    # [2단계]: 바코드 미검출 시에만 Gemini Vision OCR 가동
    # -------------------------------------------------------------
    logger.info("바코드 미검출. 표지/뒷표지 이미지로 간주하고 Gemini Vision OCR 가동.")
    cover_result = await gemini_ocr_client.extract_cover_info(image_bytes, image.content_type)
    lines = cover_result.lines
    title_cand = cover_result.title or ""
    if cover_result.author:
        author_cand = [cover_result.author]

    # 2-1. Vision AI가 이미지 속 인쇄된 13자리 ISBN 숫자를 읽어낸 경우 (뒷표지 숫자 등)
    if cover_result.isbn:
        from app.vision.isbn_utils import find_first_valid_isbn

        isbn = find_first_valid_isbn(cover_result.isbn)

    if not isbn:
        from app.vision.isbn_utils import find_first_valid_isbn

        combined_text = f"{cover_result.raw_text}\n" + "\n".join(lines)
        isbn = find_first_valid_isbn(combined_text)

    # 2-2. Vision OCR에서 ISBN을 건졌다면, 뒷표지 텍스트(lines)는 무시하고 정식 ISBN 서지 조회
    if isbn:
        logger.info("Vision OCR에서 인쇄된 ISBN %s 검출 성공. 서지 DB 조회.", isbn)
        book_doc = await nl_client.fetch_and_fill_book_info_by_isbn(isbn)
        if book_doc:
            doc_title = book_doc.get("title", "")
            if doc_title and not doc_title.startswith("도서_"):
                title_cand = doc_title
            elif not title_cand:
                title_cand = doc_title

            if book_doc.get("author") and not str(book_doc.get("author")).startswith(
                "국립중앙도서관"
            ):
                author_cand = [str(book_doc.get("author"))]
            book_info = {
                "title": title_cand or book_doc.get("title"),
                "author": (author_cand[0] if author_cand else book_doc.get("author")),
                "isbn": isbn,
                "publisher": book_doc.get("publisher"),
                "totalPages": book_doc.get("page_count") or 0,
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

    # 2-3. ISBN이 전혀 없는 앞표지 사진인 경우: 제목/저자 기반 국립도서관 검색
    if title_cand:
        search_author = author_cand[0] if author_cand else ""
        book_doc = await nl_client.search_book(title_cand, search_author)
        if book_doc:
            isbn = book_doc.get("isbn")
            title_cand = book_doc.get("title", title_cand)
            if book_doc.get("author"):
                author_cand = [str(book_doc.get("author"))]
            book_info = {
                "title": book_doc.get("title"),
                "author": book_doc.get("author"),
                "isbn": isbn,
                "publisher": book_doc.get("publisher"),
                "totalPages": book_doc.get("page_count") or 0,
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
    crop_box: Optional[str] = Form(None),
) -> OcrSentenceResponse:
    """문장 스크랩 이미지 OCR 추출 (하위 호환 및 선택적 크롭 지원)."""
    return await _handle_sentence_ocr(image, book_id, page_number, memo, save_scrap, crop_box)


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
    crop_box: Optional[str] = Form(None),
) -> OcrSentenceResponse:
    return await _handle_sentence_ocr(image, book_id, page_number, memo, save_scrap, crop_box)


@router.post("/ocr/covers", response_model=OcrCoverResponse)
async def perform_vision_ocr_cover(
    image: UploadFile = File(...),
) -> OcrCoverResponse:
    return await _handle_cover_ocr(image)
