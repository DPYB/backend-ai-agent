"""Unit tests for Phase 70 performance timing logging in Vision and classify-genre."""

import asyncio
import io
import logging
import re
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.vision.gemini_ocr_client import CoverOcrResult
from app.vision.isbn_utils import mask_isbn


def _create_dummy_image_bytes() -> bytes:
    """Create a minimal 100x100 RGB JPEG image."""
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. mask_isbn 단위 테스트
# ---------------------------------------------------------------------------
def test_mask_isbn_variants():
    """Verify mask_isbn correctly masks 13-digit, 10-digit, and irregular ISBN strings."""
    # 13-digit ISBN
    assert mask_isbn("9791192300000") == "97911****0000"
    assert mask_isbn("978-89-349-3960-3") == "97889****9603"

    # 10-digit ISBN
    assert mask_isbn("8934939607") == "893****607"

    # None or empty
    assert mask_isbn(None) == "NONE"
    assert mask_isbn("") == "NONE"

    # Short or irregular digits
    assert mask_isbn("1234") == "***"
    assert mask_isbn("123456") == "123****56"


# ---------------------------------------------------------------------------
# 2. Cover OCR Timing Logging 테스트
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cover_ocr_timing_logging_barcode_success(caplog):
    """Verify barcode success path: barcode is SUCCESS, VLM is SKIPPED, nl_api is SUCCESS."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("barcode.jpg", img_bytes, "image/jpeg")}

        mock_book_doc = {
            "title": "정의란 무엇인가",
            "author": "마이클 샌델",
            "publisher": "김영사",
            "isbn": "9788934939603",
            "page_count": 400,
            "cover_url": "https://example.com/cover.jpg",
            "genre": "PHILOSOPHY",
            "kdc": "190",
        }

        with (
            patch(
                "app.vision.barcode_service.BarcodeService.scan_isbn",
                return_value="9788934939603",
            ),
            patch(
                "app.infrastructure.national_library_client.NationalLibraryClient.fetch_and_fill_book_info_by_isbn",
                new_callable=AsyncMock,
                return_value=mock_book_doc,
            ),
        ):
            resp = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert resp.status_code == 200

        # Verify PERF_TIMING log
        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=cover_ocr" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "barcode_status=SUCCESS" in log
        assert "vlm_status=SKIPPED" in log
        assert "vlm_ms=0.00" in log
        assert "nl_api_status=SUCCESS" in log
        assert "isbn_masked=97889****9603" in log
        assert re.search(r"correlation_id=[0-9a-f]{8}", log) is not None
        assert re.search(r"total_ms=\d+\.\d{2}", log) is not None
        assert re.search(r"barcode_ms=\d+\.\d{2}", log) is not None
        assert re.search(r"nl_api_ms=\d+\.\d{2}", log) is not None


@pytest.mark.asyncio
async def test_cover_ocr_timing_logging_vlm_isbn_success(caplog):
    """Verify barcode miss + VLM ISBN detected path: barcode NOT_FOUND, VLM SUCCESS, nl_api SUCCESS."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("back_cover.jpg", img_bytes, "image/jpeg")}

        mock_cover_result = CoverOcrResult(
            isbn="9788934939603",
            title="정의란 무엇인가",
            author="마이클 샌델",
            publisher="김영사",
            lines=["정의란 무엇인가"],
            raw_text="ISBN 978-89-349-3960-3",
            request_id="req-vlm-1",
        )
        mock_book_doc = {
            "title": "정의란 무엇인가",
            "author": "마이클 샌델",
            "publisher": "김영사",
            "isbn": "9788934939603",
            "page_count": 400,
            "cover_url": "https://example.com/cover.jpg",
            "genre": "PHILOSOPHY",
            "kdc": "190",
        }

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", return_value=None),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                new_callable=AsyncMock,
                return_value=mock_cover_result,
            ),
            patch(
                "app.infrastructure.national_library_client.NationalLibraryClient.fetch_and_fill_book_info_by_isbn",
                new_callable=AsyncMock,
                return_value=mock_book_doc,
            ),
        ):
            resp = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert resp.status_code == 200

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=cover_ocr" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "barcode_status=NOT_FOUND" in log
        assert "vlm_status=SUCCESS" in log
        assert "nl_api_status=SUCCESS" in log
        assert "isbn_masked=97889****9603" in log


@pytest.mark.asyncio
async def test_cover_ocr_timing_logging_title_search_fallback(caplog):
    """Verify front cover (no ISBN) path: barcode NOT_FOUND, VLM SUCCESS, search_book nl_api SUCCESS."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("front_cover.jpg", img_bytes, "image/jpeg")}

        mock_cover_result = CoverOcrResult(
            isbn=None,
            title="데미안",
            author="헤르만 헤세",
            publisher="민음사",
            lines=["데미안"],
            raw_text="데미안 헤르만 헤세",
            request_id="req-vlm-2",
        )
        mock_book_doc = {
            "title": "데미안",
            "author": "헤르만 헤세",
            "publisher": "민음사",
            "isbn": "9788937460449",
            "page_count": 240,
            "cover_url": "https://example.com/demian.jpg",
            "genre": "LITERATURE",
            "kdc": "853",
        }

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", return_value=None),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                new_callable=AsyncMock,
                return_value=mock_cover_result,
            ),
            patch(
                "app.infrastructure.national_library_client.NationalLibraryClient.search_book",
                new_callable=AsyncMock,
                return_value=mock_book_doc,
            ),
        ):
            resp = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert resp.status_code == 200

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=cover_ocr" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "barcode_status=NOT_FOUND" in log
        assert "vlm_status=SUCCESS" in log
        assert "nl_api_status=SUCCESS" in log
        assert "isbn_masked=97889****0449" in log


@pytest.mark.asyncio
async def test_cover_ocr_timing_precision_with_injected_delay(caplog):
    """Verify that injected sleep delay is faithfully reflected in timing metrics (>= 35ms)."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("delay.jpg", img_bytes, "image/jpeg")}

        def _delayed_scan(_):
            time.sleep(0.04)
            return "9788934939603"

        mock_book_doc = {
            "title": "정의란 무엇인가",
            "author": "마이클 샌델",
            "publisher": "김영사",
            "isbn": "9788934939603",
        }

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", side_effect=_delayed_scan),
            patch(
                "app.infrastructure.national_library_client.NationalLibraryClient.fetch_and_fill_book_info_by_isbn",
                new_callable=AsyncMock,
                return_value=mock_book_doc,
            ),
        ):
            resp = await client.post("/api/v1/vision/ocr/covers", files=files)
            assert resp.status_code == 200

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=cover_ocr" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        # Extract barcode_ms and total_ms
        b_match = re.search(r"barcode_ms=(\d+\.\d{2})", log)
        t_match = re.search(r"total_ms=(\d+\.\d{2})", log)
        assert b_match is not None and t_match is not None
        barcode_ms = float(b_match.group(1))
        total_ms = float(t_match.group(1))

        assert barcode_ms >= 35.0
        assert total_ms >= 35.0


@pytest.mark.asyncio
async def test_cover_ocr_timing_logged_even_on_exception(caplog):
    """Verify that when VLM throws an exception, timing is still logged in finally block and vlm_status=ERROR."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        img_bytes = _create_dummy_image_bytes()
        files = {"image": ("error.jpg", img_bytes, "image/jpeg")}

        with (
            patch("app.vision.barcode_service.BarcodeService.scan_isbn", return_value=None),
            patch(
                "app.vision.gemini_ocr_client.GeminiOcrClient.extract_cover_info",
                new_callable=AsyncMock,
                side_effect=RuntimeError("VLM Service Down"),
            ),
        ):
            with pytest.raises(RuntimeError, match="VLM Service Down"):
                await client.post("/api/v1/vision/ocr/covers", files=files)

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=cover_ocr" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "barcode_status=NOT_FOUND" in log
        assert "vlm_status=ERROR" in log
        assert "nl_api_status=SKIPPED" in log
        assert "isbn_masked=NONE" in log


# ---------------------------------------------------------------------------
# 3. Classify Genre Timing Logging 테스트
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_classify_genre_timing_logging_llm_success(caplog):
    """Verify classify_genre timing logging on LLM success."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        mock_ai_message = AsyncMock()
        mock_ai_message.content = '{"genre": "LITERATURE", "subject": "소설/문학", "confidence": 0.95, "reason": "고전 소설"}'

        with (
            patch("app.api.router.settings.gemini_api_key", "test-key-1234567890"),
            patch(
                "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
                new_callable=AsyncMock,
                return_value=mock_ai_message,
            ),
        ):
            resp = await client.post(
                "/api/v1/classify-genre",
                json={"title": "데미안", "author": "헤르만 헤세"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "LLM"
            assert data["genre"] == "LITERATURE"

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=classify_genre" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "llm_status=SUCCESS" in log
        assert "fallback_status=SKIPPED" in log
        assert "fallback_ms=0.00" in log
        assert "source=LLM" in log
        assert "genre=LITERATURE" in log
        assert re.search(r"correlation_id=[0-9a-f]{8}", log) is not None
        assert re.search(r"total_ms=\d+\.\d{2}", log) is not None
        assert re.search(r"llm_ms=\d+\.\d{2}", log) is not None


@pytest.mark.asyncio
async def test_classify_genre_timing_logging_timeout_fallback(caplog):
    """Verify classify_genre timing logging on timeout fallback."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def _mock_slow_ainvoke(*args, **kwargs):
            await asyncio.sleep(2.5)
            mock_resp = AsyncMock()
            mock_resp.content = '{"genre": "LITERATURE"}'
            return mock_resp

        with (
            patch("app.api.router.settings.gemini_api_key", "test-key-1234567890"),
            patch(
                "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
                side_effect=_mock_slow_ainvoke,
            ),
        ):
            resp = await client.post(
                "/api/v1/classify-genre",
                json={"title": "데미안", "kdc": "853"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "KDC_FALLBACK"

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=classify_genre" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "llm_status=TIMEOUT" in log
        assert "fallback_status=SUCCESS" in log
        assert "source=KDC_FALLBACK" in log
        assert re.search(r"fallback_ms=\d+\.\d{2}", log) is not None


@pytest.mark.asyncio
async def test_classify_genre_timing_logging_no_api_key(caplog):
    """Verify classify_genre timing logging when no API key configured: llm_status=SKIPPED, fallback_status=SUCCESS."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with (
            patch("app.api.router.settings.gemini_api_key", ""),
            patch("app.api.router.settings.gemini_fallback_api_key", ""),
        ):
            resp = await client.post(
                "/api/v1/classify-genre",
                json={"title": "그림의 힘", "kdc": "513.8"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "KDC_FALLBACK"
            assert data["genre"] == "PHILOSOPHY"

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=classify_genre" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "llm_status=SKIPPED" in log
        assert "llm_ms=0.00" in log
        assert "fallback_status=SUCCESS" in log
        assert "source=KDC_FALLBACK" in log
        assert "genre=PHILOSOPHY" in log


@pytest.mark.asyncio
async def test_classify_genre_timing_logging_rate_limit(caplog):
    """Verify classify_genre timing logging on 429 rate limit: llm_status=RATE_LIMIT, fallback_status=SUCCESS."""
    caplog.set_level(logging.INFO)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with (
            patch("app.api.router.settings.gemini_api_key", "test-key-1234567890"),
            patch(
                "langchain_google_genai.ChatGoogleGenerativeAI.ainvoke",
                new_callable=AsyncMock,
                side_effect=Exception("429 RESOURCE_EXHAUSTED Quota exceeded"),
            ),
        ):
            resp = await client.post(
                "/api/v1/classify-genre",
                json={"title": "수학의 정석", "kdc": "410"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "KDC_FALLBACK"

        timing_logs = [
            r.message for r in caplog.records if "[PERF_TIMING] op=classify_genre" in r.message
        ]
        assert len(timing_logs) == 1
        log = timing_logs[0]

        assert "llm_status=RATE_LIMIT" in log
        assert "fallback_status=SUCCESS" in log
        assert "source=KDC_FALLBACK" in log
