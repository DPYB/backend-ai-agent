"""ISBN validation, normalization and extraction utilities."""

import re
from typing import List, Optional


def validate_isbn13_checksum(isbn: str) -> bool:
    """Validate 13-digit ISBN using standard modulo 10 checksum.

    Weights: alternating 1 and 3.
    Sum = sum(d_i * (1 if i % 2 == 0 else 3)) % 10 == 0.
    """
    clean_digits = re.sub(r"\D", "", isbn)
    if len(clean_digits) != 13:
        return False
    if not clean_digits.isdigit():
        return False

    total = 0
    for idx, char in enumerate(clean_digits):
        digit = int(char)
        weight = 1 if idx % 2 == 0 else 3
        total += digit * weight

    return total % 10 == 0


def extract_isbn_candidates(text: str) -> List[str]:
    """Extract and validate 13-digit ISBN candidates from arbitrary text or OCR outputs.

    Matches patterns like '978-89-349-3960-3', 'ISBN 979 11 86704 12 7', '9788937460449'.
    Filters candidates by check digit verification when possible.
    """
    if not text:
        return []

    candidates: List[str] = []

    # 1. Look for standard ISBN pattern with variable group lengths (e.g. 978-89-349-3960-3, ISBN 979 11 86704 12 7)
    # Allows flexible hyphen/space formatting between publisher/item blocks
    standard_pattern = r"(?:ISBN(?:-13)?:?\s*)?(97[89][- ]?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,6}[- ]?\d)"
    matches = re.findall(standard_pattern, text, flags=re.IGNORECASE)
    for m in matches:
        clean = re.sub(r"[- ]", "", m)
        if len(clean) == 13 and clean not in candidates:
            candidates.append(clean)

    # 2. Look for hyphenated or space-separated ISBN strings with arbitrary digit spacing
    hyphen_pattern = r"(?:ISBN(?:-13)?:?\s*)?(97[89][-\s]?(?:\d[-\s]?){9}\d)"
    matches_hyphen = re.findall(hyphen_pattern, text, flags=re.IGNORECASE)
    for m in matches_hyphen:
        clean = re.sub(r"\D", "", m)
        if len(clean) == 13 and clean not in candidates:
            candidates.append(clean)

    # 3. Look for pure 13-digit continuous numbers starting with 978 or 979
    raw_digits_matches = re.findall(r"\b(97[89]\d{10})\b", text)
    for m in raw_digits_matches:
        if m not in candidates:
            candidates.append(m)

    # 4. Aggressive digit-only scan if no candidate found yet (stripping punctuation)
    if not candidates:
        digits_only = re.sub(r"\D", "", text)
        embedded_matches = re.findall(r"(97[89]\d{10})", digits_only)
        for m in embedded_matches:
            if m not in candidates:
                candidates.append(m)

    # Prioritize candidates that pass ISBN-13 checksum
    valid_checksums = [c for c in candidates if validate_isbn13_checksum(c)]
    invalid_checksums = [c for c in candidates if not validate_isbn13_checksum(c)]

    return valid_checksums + invalid_checksums


def find_first_valid_isbn(text: str) -> Optional[str]:
    """Find the best matching 13-digit ISBN from text, returning None if no candidates exist."""
    candidates = extract_isbn_candidates(text)
    return candidates[0] if candidates else None


def extract_kdc_candidates(text: str) -> List[str]:
    """Extract potential KDC / call number or 5-digit ISBN supplementary classification codes.

    1. 5-digit ISBN supplementary codes (e.g., '03320', '93810', '03005')
    2. Library call number labels (e.g., '813.6-박24ㄱ', '320.1', 'K813.6', 'KDC 813.6', 'DDC 005.133')
    Excludes pure 13-digit ISBNs (978..., 979...), prices (15,000 등) and random punctuation.
    """
    if not text:
        return []

    candidates: List[str] = []

    # 1. 5-digit supplementary code: standalone 5-digit number (e.g. 03320, 93810, 03005)
    # Must not be part of longer numbers, and must not be a price (followed by '원')
    supp_5digit_pattern = r"(?:^|[^\d])(\d{5})(?:[^\d]|$)"
    for m in re.finditer(supp_5digit_pattern, text):
        val = m.group(1)
        end_idx = m.end(1)
        surrounding = text[end_idx : end_idx + 4] if end_idx < len(text) else ""
        if "원" in surrounding:
            continue
        if val not in candidates:
            candidates.append(val)

    # 2. Library call number pattern:
    # Explicit prefix or decimal classification followed by optional author code (e.g. '813.6-박24ㄱ', '320.1', 'KDC 813.6')
    call_no_pattern = (
        r"(?:(?:KDC|DDC|분류(?:기호)?)\s*:?\s*)?([A-Z]?\d{3}(?:\.\d+)?(?:-[가-힣ㄱ-ㅎA-Za-z0-9]+)?)"
    )
    for m in re.finditer(call_no_pattern, text, flags=re.IGNORECASE):
        matched = m.group(1).strip()
        # Avoid matching ISBN prefixes like 978 or 979 as call numbers
        if matched.startswith(("978", "979")):
            continue
        start, end = m.span(1)
        # Check that it is not embedded in longer digits or hyphens that look like ISBN
        if start > 0 and text[start - 1] in "0123456789-":
            continue
        if end < len(text) and text[end] in "0123456789-":
            continue
        if matched and matched not in candidates:
            candidates.append(matched)

    return candidates


def find_first_kdc(text: str) -> Optional[str]:
    """Find the best matching KDC candidate or 5-digit supplementary code."""
    cands = extract_kdc_candidates(text)
    return cands[0] if cands else None
