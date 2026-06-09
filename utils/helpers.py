"""
Helper utilities for text normalization, encoding detection, and safe conversions.
"""
import re
import unicodedata
from typing import Optional

import chardet

from config.rules import (
    UNICODE_FORM,
    NORMALIZE_LOWERCASE,
    NORMALIZE_STRIP,
    NORMALIZE_COLLAPSE_SPACES,
    MISSING_VALUES,
)


def normalize_text(text: str) -> str:
    """
    Normalize a text value: Unicode NFC, strip, lowercase, collapse spaces.

    Args:
        text: Raw text string

    Returns:
        Normalized text string
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    result = text

    # Unicode normalization
    result = unicodedata.normalize(UNICODE_FORM, result)

    # Strip whitespace
    if NORMALIZE_STRIP:
        result = result.strip()

    # Collapse multiple spaces
    if NORMALIZE_COLLAPSE_SPACES:
        result = re.sub(r"\s+", " ", result)

    # Lowercase
    if NORMALIZE_LOWERCASE:
        result = result.lower()

    return result


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding using chardet.

    Args:
        file_path: Path to the file

    Returns:
        Detected encoding string (e.g., 'utf-8', 'windows-1252')
    """
    with open(file_path, "rb") as f:
        raw_data = f.read(100_000)  # Read up to 100KB for detection

    result = chardet.detect(raw_data)
    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)

    # Default to utf-8 if detection confidence is low
    if confidence < 0.5 or encoding is None:
        encoding = "utf-8"

    # Normalize encoding name
    encoding = encoding.lower().replace("-", "_")

    # Map common aliases
    encoding_map = {
        "ascii": "utf-8",
        "iso_8859_1": "latin-1",
        "windows_1252": "cp1252",
        "utf_8_sig": "utf-8-sig",
    }
    encoding = encoding_map.get(encoding, encoding)

    return encoding


def is_missing_value(value) -> bool:
    """
    Check if a value should be treated as missing/NA.

    Args:
        value: Any value to check

    Returns:
        True if the value represents a missing value
    """
    if value is None:
        return True

    if isinstance(value, float):
        import math
        return math.isnan(value)

    text = normalize_text(str(value))
    return text in MISSING_VALUES


def safe_convert_numeric(value, default=None) -> Optional[float]:
    """
    Safely convert a value to numeric (float).

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if value is None:
        return default

    if isinstance(value, (int, float)):
        import math
        return default if math.isnan(value) else float(value)

    try:
        text = str(value).strip().replace(",", ".")
        return float(text)
    except (ValueError, TypeError):
        return default


def detect_header_row(file_path: str, max_rows: int = 10) -> int:
    """
    Detect which row contains the actual header in a file.
    Skips metadata/title rows that sometimes appear at the top of survey exports.

    Args:
        file_path: Path to the file
        max_rows: Maximum rows to check

    Returns:
        0-indexed row number of the header
    """
    import pandas as pd
    from pathlib import Path

    ext = Path(file_path).suffix.lower()

    try:
        if ext in (".xlsx", ".xls"):
            preview = pd.read_excel(file_path, header=None, nrows=max_rows)
        else:
            encoding = detect_encoding(file_path)
            preview = pd.read_csv(
                file_path, header=None, nrows=max_rows,
                encoding=encoding, on_bad_lines="skip"
            )
    except Exception:
        return 0

    if preview.empty:
        return 0

    best_row = 0
    best_score = 0

    for idx in range(min(max_rows, len(preview))):
        row = preview.iloc[idx]
        non_null = row.dropna()

        if len(non_null) == 0:
            continue

        # Score based on:
        # 1. Number of non-null values (more is better)
        # 2. All values are strings (headers are usually text)
        # 3. All values are unique (headers should be unique)
        all_str = all(isinstance(v, str) for v in non_null)
        all_unique = len(non_null) == len(set(non_null.astype(str)))

        score = len(non_null)
        if all_str:
            score += len(non_null) * 2
        if all_unique:
            score += len(non_null)

        if score > best_score:
            best_score = score
            best_row = idx

    return best_row
