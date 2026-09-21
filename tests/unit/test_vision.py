"""Unit tests for Vision API (Barcode Scan & Google Gemini Flash Vision OCR)."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.vision.barcode_service import BarcodeService
from app.vision.gemini_ocr_client import (
    ClovaOcrClient,
    ClovaOcrResult,
    GeminiOcrClient,
    GeminiOcrResult,
)


def _create_dummy_image_bytes(format: str = "JPEG") -> bytes:
    """Helper to generate in-memory dummy image bytes."""
    buf = BytesIO()
    img = Image.new("RGB", (100, 100), color="white")
    img.save(buf, format=format)
    return buf.getvalue()


def test_barcode_scan_invalid_image():
    """Verify barcode scanner returns None for plain images without barcodes."""
    img_bytes = _create_dummy_image_bytes()
    isbn = BarcodeService.scan_isbn(img_bytes)
    assert isbn is None


def test_barcode_scan_with_mocked_isbn():
    """Verify barcode scanner extracts 13-digit ISBN correctly."""
    img_bytes = _create_dummy_image_bytes()

    mock_obj = MagicMock()
    mock_obj.data = b"9788966260959"

    with (
        patch("app.vision.barcode_service._PYZBAR_AVAILABLE", True),
        patch("app.vision.barcode_service.decode", return_value=[mock_obj], create=True),
    ):
        isbn = BarcodeService.scan_isbn(img_bytes)
        assert isbn == "9788966260959"


@pytest.mark.asyncio
async def test_gemini_ocr_fallback_when_unconfigured():
    """Verify GeminiOcrClient returns fallback when credentials are empty."""
    client = GeminiOcrClient()
    client.gemini_api_key = ""
    client.gemini_fallback_api_key = ""
    client.openai_api_key = ""

    img_bytes = _create_dummy_image_bytes()
    result = await client.extract_text(img_bytes, "image/jpeg")

    assert isinstance(result, GeminiOcrResult)
    assert isinstance(result, ClovaOcrResult)  # Backward-compatibility alias
    assert "테스트 모드" in result.text
    assert len(result.lines) > 0


@pytest.mark.asyncio
async def test_gemini_ocr_extract_text_mocked():
    """Verify GeminiOcrClient correctly parses lines from Gemini Flash response."""
    client = GeminiOcrClient()
    client.gemini_api_key = "valid-test-key-1234567890"

    mock_response = MagicMock()
    mock_response.content = "첫 번째 문장입니다.\n\n두 번째 문장입니다."

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        img_bytes = _create_dummy_image_bytes()
        result = await client.extract_text(img_bytes, "image/jpeg")

        assert isinstance(result, GeminiOcrResult)
        assert len(result.lines) == 2
        assert result.lines[0] == "첫 번째 문장입니다."
        assert result.lines[1] == "두 번째 문장입니다."
        assert "첫 번째 문장입니다.\n\n두 번째 문장입니다." in result.text
        assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_gemini_ocr_openai_fallback_when_gemini_fails():
    """Verify GeminiOcrClient falls back to OpenAI when Gemini call fails."""
    client = GeminiOcrClient()
    client.gemini_api_key = "valid-test-gemini-key-12345"
    client.openai_api_key = "valid-test-openai-key-12345"

    mock_openai_response = MagicMock()
    mock_openai_response.content = "오픈AI 폴백 추출 문장입니다."

    with (
        patch(
            "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Gemini quota exceeded"),
        ),
        patch(
            "langchain_openai.ChatOpenAI.ainvoke",
            new_callable=AsyncMock,
            return_value=mock_openai_response,
        ),
    ):
        img_bytes = _create_dummy_image_bytes()
        result = await client.extract_text(img_bytes, "image/jpeg")

        assert isinstance(result, GeminiOcrResult)
        assert result.lines == ["오픈AI 폴백 추출 문장입니다."]


def test_clova_alias_compatibility():
    """Verify backward-compatibility aliases work seamlessly."""
    assert ClovaOcrClient is GeminiOcrClient
    assert ClovaOcrResult is GeminiOcrResult


@pytest.mark.asyncio
async def test_scan_barcode_endpoint():
    """Verify POST /api/v1/vision/scan-barcode endpoint returns BarcodeScanResponse."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("test.jpg", img_bytes, "image/jpeg")}

        response = await client.post("/api/v1/vision/scan-barcode", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "found" in data
        assert "isbn" in data


@pytest.mark.asyncio
async def test_scan_barcode_endpoint_invalid_media_type():
    """Verify POST /api/v1/vision/scan-barcode rejects non-image files with 415."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"image": ("test.txt", b"not an image", "text/plain")}

        response = await client.post("/api/v1/vision/scan-barcode", files=files)
        assert response.status_code == 415


@pytest.mark.asyncio
async def test_ocr_endpoint():
    """Verify POST /api/v1/vision/ocr endpoint returns OcrResponse."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("sentence.jpg", img_bytes, "image/jpeg")}

        response = await client.post("/api/v1/vision/ocr", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "lines" in data
        assert "request_id" in data


def test_isbn_utils_checksum_and_extraction():
    """Verify ISBN-13 checksum calculation and candidate extraction."""
    from app.vision.isbn_utils import (
        extract_isbn_candidates,
        find_first_valid_isbn,
        validate_isbn13_checksum,
    )

    # Valid ISBNs
    assert validate_isbn13_checksum("9788934939603") is True
    assert validate_isbn13_checksum("9788937460449") is True
    assert validate_isbn13_checksum("9791186704127") is True

    # Invalid ISBNs
    assert validate_isbn13_checksum("9788934939600") is False
    assert validate_isbn13_checksum("1234567890123") is False
    assert validate_isbn13_checksum("short") is False

    # Extraction from noisy OCR text
    sample_ocr = """
    도서출판 김영사
    값 15,000원
    ISBN 978-89-349-3960-3 03810
    바코드 주변 텍스트입니다.
    """
    cands = extract_isbn_candidates(sample_ocr)
    assert "9788934939603" in cands
    assert find_first_valid_isbn(sample_ocr) == "9788934939603"


@pytest.mark.asyncio
async def test_extract_cover_info_json_parsing():
    """Verify GeminiOcrClient.extract_cover_info correctly parses structured JSON response."""
    client = GeminiOcrClient()
    client.gemini_api_key = "valid-test-key-1234567890"

    mock_llm_res = MagicMock()
    mock_llm_res.content = """
    ```json
    {
      "isbn": "978-89-349-3960-3",
      "title": "생각에 관한 생각",
      "author": "대니얼 카너먼",
      "publisher": "김영사",
      "lines": ["생각에 관한 생각", "대니얼 카너먼 지음", "김영사"]
    }
    ```
    """

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
        new_callable=AsyncMock,
        return_value=mock_llm_res,
    ):
        img_bytes = _create_dummy_image_bytes()
        res = await client.extract_cover_info(img_bytes, "image/jpeg")

        assert res.isbn == "978-89-349-3960-3"
        assert res.title == "생각에 관한 생각"
        assert res.author == "대니얼 카너먼"
        assert res.publisher == "김영사"
        assert len(res.lines) == 3


@pytest.mark.asyncio
async def test_cover_ocr_endpoint_with_barcode_failure_and_vision_fallback():
    """Verify POST /api/v1/vision/ocr/covers successfully extracts ISBN via Vision OCR when barcode fails."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("back_cover.jpg", img_bytes, "image/jpeg")}

        from app.vision.gemini_ocr_client import CoverOcrResult

        # 9788934939603 is Michael Sandel's "Justice" (정의란 무엇인가)
        mock_cover_result = CoverOcrResult(
            isbn="9788934939603",
            title="정의란 무엇인가",
            author="마이클 샌델",
            publisher="김영사",
            lines=["정의란 무엇인가", "마이클 샌델"],
            raw_text="ISBN 978-89-349-3960-3",
            request_id="test-req-123",
        )

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", return_value=None),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                new_callable=AsyncMock,
                return_value=mock_cover_result,
            ),
        ):
            response = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert response.status_code == 200
            data = response.json()
            assert data["isbn"] == "9788934939603"
            assert "정의란 무엇인가" in data["title_candidate"]
            assert any("마이클 샌델" in a for a in data["author_candidates"])
            assert data["book"] is not None
            assert data["book"]["isbn"] == "9788934939603"


@pytest.mark.asyncio
async def test_cover_ocr_endpoint_with_title_search_fallback():
    """Verify POST /api/v1/vision/ocr/covers falls back to National Library title search when ISBN is not detected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("front_cover.jpg", img_bytes, "image/jpeg")}

        from app.vision.gemini_ocr_client import CoverOcrResult

        # Cover image with no ISBN visible
        mock_cover_result = CoverOcrResult(
            isbn=None,
            title="데미안",
            author="헤르만 헤세",
            publisher="민음사",
            lines=["데미안", "헤르만 헤세"],
            raw_text="데미안 헤르만 헤세",
            request_id="test-req-456",
        )

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", return_value=None),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                new_callable=AsyncMock,
                return_value=mock_cover_result,
            ),
        ):
            response = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert response.status_code == 200
            data = response.json()
            assert data["title_candidate"] == "데미안"
            assert "헤르만 헤세" in data["author_candidates"]
            assert data["book"] is not None
            assert data["book"]["title"] == "데미안"
            assert data["book"]["isbn"] is not None
            assert len(data["book"]["isbn"]) == 13
            assert data["book"]["isbn"].startswith(("978", "979"))


@pytest.mark.asyncio
async def test_barcode_priority_ignores_ocr_text_on_back_cover():
    """Verify that when barcode (ISBN) is detected, OCR is bypassed to prevent blurb hijacking."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("back_cover_with_blurb.jpg", img_bytes, "image/jpeg")}

        mock_gemini_ocr = AsyncMock()

        # Barcode finds Justice ISBN (9788934939603)
        with (
            patch(
                "app.vision.barcode_service.BarcodeService.scan_isbn", return_value="9788934939603"
            ),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                mock_gemini_ocr,
            ),
        ):
            response = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert response.status_code == 200
            data = response.json()
            assert data["isbn"] == "9788934939603"
            assert data["book"] is not None
            assert data["book"]["isbn"] == "9788934939603"
            # Crucial: OCR was never even called!
            mock_gemini_ocr.assert_not_called()


@pytest.mark.asyncio
async def test_page_count_cross_referencing_when_isbn_lacks_pages():
    """Verify fetch_and_fill_book_info_by_isbn fills missing page count from other editions."""
    from app.infrastructure.national_library_client import get_national_library_client

    nl = get_national_library_client()

    mock_isbn_doc = {
        "title": "데미안",
        "author": "헤르만 헤세",
        "publisher": "민음사",
        "isbn": "9788937460449",
        "cover_url": "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9788937460449.jpg",
        "page_count": None,  # Missing page count
        "genre": "LITERATURE",
        "source": "NATIONAL_LIBRARY_API",
    }

    mock_cross_doc = {
        "title": "데미안",
        "author": "헤르만 헤세",
        "publisher": "북하우스",
        "isbn": "9791164053353",
        "cover_url": "https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/9791164053353.jpg",
        "page_count": 343,  # Found in another edition
        "genre": "LITERATURE",
        "source": "NATIONAL_LIBRARY_API",
    }

    with (
        patch.object(nl, "search_by_isbn", new_callable=AsyncMock, return_value=mock_isbn_doc),
        patch.object(nl, "search_book", new_callable=AsyncMock, return_value=mock_cross_doc),
    ):
        result = await nl.fetch_and_fill_book_info_by_isbn("9788937460449")
        assert result is not None
        assert result["isbn"] == "9788937460449"  # Original ISBN preserved
        assert result["page_count"] == 343  # Page count cross-referenced successfully


@pytest.mark.asyncio
async def test_sentence_ocr_with_crop_box():
    """Verify sentence OCR endpoint handles crop_box parameter correctly."""
    # 200x200 이미지 생성
    buf = BytesIO()
    img = Image.new("RGB", (200, 200), color="blue")
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"image": ("book_page.jpg", img_bytes, "image/jpeg")}
        # crop_box로 [10, 10, 50, 50] 전달
        data = {"crop_box": '{"x": 10, "y": 10, "width": 50, "height": 50}'}

        mock_ocr = AsyncMock(
            return_value=GeminiOcrResult(
                text="크롭된 문장입니다.",
                lines=["크롭된 문장입니다."],
                confidence=0.99,
                request_id="crop-test-id",
            )
        )

        with patch("app.api.v1.vision.gemini_ocr_client.extract_text", mock_ocr):
            response = await client.post("/api/v1/ocr/sentences", files=files, data=data)
            assert response.status_code == 200
            res_data = response.json()
            assert res_data["text"] == "크롭된 문장입니다."
            assert res_data["scrap_image_url"].startswith("data:image/jpeg;base64,")

            # extract_text에 전달된 이미지 바이트가 실제로 크롭되었는지 확인
            called_bytes = mock_ocr.call_args[0][0]
            with Image.open(BytesIO(called_bytes)) as cropped_img:
                assert cropped_img.size == (50, 50)


def test_kdc_candidates_extraction():
    """Verify extract_kdc_candidates extracts 5-digit supplementary and call numbers."""
    from app.vision.isbn_utils import extract_kdc_candidates, find_first_kdc

    # 1. 5-digit supplementary code next to barcode
    ocr_with_supp = "ISBN 978-89-349-3960-3 03320\n가격 15,000원"
    cands = extract_kdc_candidates(ocr_with_supp)
    assert "03320" in cands
    assert find_first_kdc(ocr_with_supp) == "03320"

    # 2. Library call number label
    ocr_with_label = "도서관 청구기호: 813.6-박24ㄱ\n국립중앙도서관"
    cands_label = extract_kdc_candidates(ocr_with_label)
    assert "813.6-박24ㄱ" in cands_label
    assert find_first_kdc(ocr_with_label) == "813.6-박24ㄱ"

    # 3. Simple decimal classification
    ocr_simple = "KDC 320.1 사회과학"
    assert find_first_kdc(ocr_simple) == "320.1"


@pytest.mark.asyncio
async def test_cover_ocr_kdc_passthrough():
    """Verify cover OCR endpoint extracts and passes through kdc field in root and book metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("back_cover.jpg", img_bytes, "image/jpeg")}

        from app.vision.gemini_ocr_client import CoverOcrResult

        mock_cover_result = CoverOcrResult(
            isbn="9788934939603",
            kdc="03320",
            title="정의란 무엇인가",
            author="마이클 샌델",
            publisher="김영사",
            lines=["정의란 무엇인가", "마이클 샌델", "03320"],
            raw_text="ISBN 978-89-349-3960-3 03320",
            request_id="kdc-test-req-id",
        )

        with (
            patch("app.api.v1.vision.barcode_service.scan_isbn", return_value=None),
            patch(
                "app.api.v1.vision.gemini_ocr_client.extract_cover_info",
                new_callable=AsyncMock,
                return_value=mock_cover_result,
            ),
        ):
            response = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert response.status_code == 200
            data = response.json()
            assert data["isbn"] == "9788934939603"
            assert data["kdc"] == "03320"
            assert data["book"] is not None
            assert data["book"]["kdc"] == "03320"
