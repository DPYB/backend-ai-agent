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
