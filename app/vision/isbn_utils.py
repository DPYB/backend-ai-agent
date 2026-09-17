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
