"""Barcode scanning service using Pillow and pyzbar (EAN13 / ISBN-13)."""

import logging
from io import BytesIO
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

try:
    from pyzbar.pyzbar import ZBarSymbol, decode

    _PYZBAR_AVAILABLE = True
except ImportError:
    logger.warning("pyzbar native library not available.")
    _PYZBAR_AVAILABLE = False


class BarcodeService:
    """Service to scan ISBN-13 barcodes from book cover/back images."""

    @staticmethod
    def scan_isbn(image_bytes: bytes) -> Optional[str]:
        """업로드된 이미지에서 ISBN-13 바코드 값을 추출한다."""
        if not _PYZBAR_AVAILABLE:
            logger.warning("pyzbar is not available on this environment.")
            return None

        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # EAN13(도서 ISBN 형식) 심볼 우선 스캔
                decoded_objects = decode(img, symbols=[ZBarSymbol.EAN13])
                if not decoded_objects:
                    # 모든 바코드 심볼 폴백 스캔
                    decoded_objects = decode(img)

                for obj in decoded_objects:
                    barcode_data = obj.data.decode("utf-8").strip()
                    # 도서 ISBN은 대개 978 또는 979로 시작하는 13자리
                    if barcode_data.startswith(("978", "979")) and len(barcode_data) == 13:
                        return barcode_data
                    if len(barcode_data) == 13 and barcode_data.isdigit():
                        return barcode_data

                return None
        except Exception as e:
            logger.warning("Barcode decoding failed: %s", e)
            return None


barcode_service = BarcodeService()
