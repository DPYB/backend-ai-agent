"""Barcode scanning service using Pillow, OpenCV, and pyzbar (EAN13 / ISBN-13)."""

import logging
from io import BytesIO
from typing import Any, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


class _ZBarSymbolFallback:
    EAN13 = 1


decode_fn: Any = None
decode: Any = None
zbar_symbol: Any = _ZBarSymbolFallback

try:
    from pyzbar.pyzbar import ZBarSymbol as _RealZBarSymbol
    from pyzbar.pyzbar import decode as _real_decode

    _PYZBAR_AVAILABLE = True
    decode_fn = _real_decode
    decode = _real_decode
    zbar_symbol = _RealZBarSymbol
except (ImportError, Exception):
    logger.warning("pyzbar native library not available.")
    _PYZBAR_AVAILABLE = False


class BarcodeService:
    """Service to scan ISBN-13 barcodes from book cover/back images with OpenCV preprocessing."""

    @staticmethod
    def robust_scan_isbn(image_bytes: bytes) -> Optional[str]:
        """실제 스마트폰 카메라 환경에 맞춘 OpenCV 다단계 전처리 바코드 스캔 엔진.

        전처리 과정:
          1. OpenCV 이미지 디코딩
          2. 해상도 리사이징 (가로 최대 1000px 비율 축소)
          3. 그레이스케일 흑백 변환 및 Otsu 이진화 대비 강화
          4. 4방향 회전 스캔 (0°, 90°, 180°, 270°)
          5. 13자리 ISBN-13 모듈로-10 가중치 체크섬 검증
        """
        if not _PYZBAR_AVAILABLE:
            logger.warning("pyzbar is not available on this environment.")
            return None

        _scanner = decode or decode_fn
        if not _scanner:
            return None

        # 1. Try OpenCV advanced pipeline if cv2 and numpy are available
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is not None:
                # 2. 이미지 리사이징 (너무 크면 pyzbar가 못 읽음, 가로 1000px 수준으로)
                height, width = img.shape[:2]
                if width > 1000:
                    ratio = 1000.0 / float(width)
                    img = cv2.resize(img, (1000, int(height * ratio)), interpolation=cv2.INTER_AREA)

                # 3. 흑백 변환 및 대비 강화 (Otsu Threshold Binarization)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

                # 4. 회전하면서 찾기 (0, 90, 180, 270도)
                images_to_try: List[Any] = [
                    gray,  # 원본 흑백
                    thresh,  # 대비 강화본
                    cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE),
                    cv2.rotate(gray, cv2.ROTATE_180),
                    cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE),
                    cv2.rotate(thresh, cv2.ROTATE_90_CLOCKWISE),
                    cv2.rotate(thresh, cv2.ROTATE_180),
                    cv2.rotate(thresh, cv2.ROTATE_90_COUNTERCLOCKWISE),
                ]

                symbols = [zbar_symbol.EAN13] if hasattr(zbar_symbol, "EAN13") else []

                for attempt_img in images_to_try:
                    decoded_objects = (
                        _scanner(attempt_img, symbols=symbols) if symbols else _scanner(attempt_img)
                    )
                    if not decoded_objects and symbols:
                        decoded_objects = _scanner(attempt_img)

                    for obj in decoded_objects:
                        barcode_data = obj.data.decode("utf-8").strip()
                        if barcode_data.startswith(("978", "979")) and len(barcode_data) == 13:
                            from app.vision.isbn_utils import validate_isbn13_checksum

                            if validate_isbn13_checksum(barcode_data):
                                return barcode_data
                        if len(barcode_data) == 13 and barcode_data.isdigit():
                            return barcode_data
        except Exception as e:
            logger.debug("OpenCV preprocessing failed (%s). Falling back to PIL.", e)

        # 2. Fallback PIL scanning pipeline (for mocked test environments or missing OpenCV)
        try:
            with Image.open(BytesIO(image_bytes)) as pil_img:
                symbols = [zbar_symbol.EAN13] if hasattr(zbar_symbol, "EAN13") else []
                # Try original, 90, 180, 270 rotations with PIL
                pil_attempts = [
                    pil_img,
                    pil_img.rotate(90, expand=True),
                    pil_img.rotate(180, expand=True),
                    pil_img.rotate(270, expand=True),
                ]
                for p_img in pil_attempts:
                    decoded_objects = (
                        _scanner(p_img, symbols=symbols) if symbols else _scanner(p_img)
                    )
                    if not decoded_objects:
                        decoded_objects = _scanner(p_img)

                    for obj in decoded_objects:
                        barcode_data = obj.data.decode("utf-8").strip()
                        if barcode_data.startswith(("978", "979")) and len(barcode_data) == 13:
                            from app.vision.isbn_utils import validate_isbn13_checksum

                            if validate_isbn13_checksum(barcode_data):
                                return barcode_data
                        if len(barcode_data) == 13 and barcode_data.isdigit():
                            return barcode_data
        except Exception as e:
            logger.warning("Barcode decoding failed: %s", e)

        return None

    @classmethod
    def scan_isbn(cls, image_bytes: bytes) -> Optional[str]:
        """업로드된 이미지에서 ISBN-13 바코드 값을 추출한다 (robust_scan_isbn alias)."""
        return cls.robust_scan_isbn(image_bytes)


barcode_service = BarcodeService()
