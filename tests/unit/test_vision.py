"""Unit tests for Vision API (Barcode Scan & Clova OCR)."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.vision.barcode_service import BarcodeService
from app.vision.clova_ocr_client import ClovaOcrClient, ClovaOcrResult


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

    with patch("app.vision.barcode_service.decode", return_value=[mock_obj]):
        isbn = BarcodeService.scan_isbn(img_bytes)
        assert isbn == "9788966260959"


@pytest.mark.asyncio
async def test_clova_ocr_fallback_when_unconfigured():
    """Verify ClovaOcrClient returns fallback when credentials are empty."""
    client = ClovaOcrClient()
    client.url = ""
    client.secret_key = ""

    img_bytes = _create_dummy_image_bytes()
    result = await client.extract_text(img_bytes, "image/jpeg")

    assert isinstance(result, ClovaOcrResult)
    assert "테스트 모드" in result.text
    assert len(result.lines) > 0


@pytest.mark.asyncio
async def test_clova_ocr_extract_text_mocked():
    """Verify ClovaOcrClient correctly parses lineBreak into separate lines."""
    client = ClovaOcrClient()
    client.url = "https://mock.clova.api/general"
    client.secret_key = "mock-secret"

    mock_response_data = {
        "images": [
            {
                "fields": [
                    {"inferText": "첫", "inferConfidence": 0.99, "lineBreak": False},
                    {"inferText": "번째", "inferConfidence": 0.98, "lineBreak": False},
                    {"inferText": "줄입니다.", "inferConfidence": 0.97, "lineBreak": True},
                    {"inferText": "두", "inferConfidence": 0.95, "lineBreak": False},
                    {"inferText": "번째", "inferConfidence": 0.96, "lineBreak": True},
                ]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        img_bytes = _create_dummy_image_bytes()
        result = await client.extract_text(img_bytes, "image/jpeg")

        assert len(result.lines) == 2
        assert result.lines[0] == "첫 번째 줄입니다."
        assert result.lines[1] == "두 번째"
        assert "첫 번째 줄입니다.\n두 번째" == result.text
        assert result.confidence is not None
        assert result.confidence > 0.9


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
