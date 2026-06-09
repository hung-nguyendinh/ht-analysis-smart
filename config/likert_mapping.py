"""
Likert scale mappings for Vietnamese and English survey responses.
Auto-detect function to match column values to appropriate scale.
"""

# ============================================================
# 5-POINT LIKERT SCALES
# ============================================================

LIKERT_5_VI = {
    "hoàn toàn không đồng ý": 1,
    "không đồng ý": 2,
    "trung lập": 3,
    "bình thường": 3,
    "phân vân": 3,
    "đồng ý": 4,
    "hoàn toàn đồng ý": 5,
}

LIKERT_5_EN = {
    "strongly disagree": 1,
    "disagree": 2,
    "neutral": 3,
    "undecided": 3,
    "agree": 4,
    "strongly agree": 5,
}

# ============================================================
# 5-POINT FREQUENCY SCALES
# ============================================================

FREQUENCY_5_VI = {
    "không bao giờ": 1,
    "hiếm khi": 2,
    "thỉnh thoảng": 3,
    "thường xuyên": 4,
    "luôn luôn": 5,
    "rất thường xuyên": 5,
}

FREQUENCY_5_EN = {
    "never": 1,
    "rarely": 2,
    "sometimes": 3,
    "often": 4,
    "frequently": 4,
    "always": 5,
    "very often": 5,
}

# ============================================================
# 5-POINT SATISFACTION SCALES
# ============================================================

SATISFACTION_5_VI = {
    "rất không hài lòng": 1,
    "không hài lòng": 2,
    "bình thường": 3,
    "hài lòng": 4,
    "rất hài lòng": 5,
}

SATISFACTION_5_EN = {
    "very dissatisfied": 1,
    "dissatisfied": 2,
    "neutral": 3,
    "satisfied": 4,
    "very satisfied": 5,
}

# ============================================================
# 7-POINT LIKERT SCALES
# ============================================================

LIKERT_7_VI = {
    "hoàn toàn không đồng ý": 1,
    "không đồng ý": 2,
    "hơi không đồng ý": 3,
    "trung lập": 4,
    "bình thường": 4,
    "hơi đồng ý": 5,
    "đồng ý": 6,
    "hoàn toàn đồng ý": 7,
}

LIKERT_7_EN = {
    "strongly disagree": 1,
    "disagree": 2,
    "somewhat disagree": 3,
    "neutral": 4,
    "undecided": 4,
    "somewhat agree": 5,
    "agree": 6,
    "strongly agree": 7,
}

# ============================================================
# YES / NO SCALES
# ============================================================

YES_NO_VI = {
    "có": 1,
    "không": 0,
    "co": 1,
    "khong": 0,
}

YES_NO_EN = {
    "yes": 1,
    "no": 0,
    "y": 1,
    "n": 0,
}

# ============================================================
# IMPORTANCE SCALES
# ============================================================

IMPORTANCE_5_VI = {
    "hoàn toàn không quan trọng": 1,
    "không quan trọng": 2,
    "bình thường": 3,
    "quan trọng": 4,
    "rất quan trọng": 5,
}

IMPORTANCE_5_EN = {
    "not important at all": 1,
    "not important": 2,
    "neutral": 3,
    "moderately important": 3,
    "important": 4,
    "very important": 5,
}

# ============================================================
# ALL MAPPINGS (ordered by priority for auto-detection)
# ============================================================

ALL_MAPPINGS = [
    {"name": "Likert 5 (VI)", "scale": 5, "mapping": LIKERT_5_VI, "lang": "vi"},
    {"name": "Likert 5 (EN)", "scale": 5, "mapping": LIKERT_5_EN, "lang": "en"},
    {"name": "Frequency 5 (VI)", "scale": 5, "mapping": FREQUENCY_5_VI, "lang": "vi"},
    {"name": "Frequency 5 (EN)", "scale": 5, "mapping": FREQUENCY_5_EN, "lang": "en"},
    {"name": "Satisfaction 5 (VI)", "scale": 5, "mapping": SATISFACTION_5_VI, "lang": "vi"},
    {"name": "Satisfaction 5 (EN)", "scale": 5, "mapping": SATISFACTION_5_EN, "lang": "en"},
    {"name": "Likert 7 (VI)", "scale": 7, "mapping": LIKERT_7_VI, "lang": "vi"},
    {"name": "Likert 7 (EN)", "scale": 7, "mapping": LIKERT_7_EN, "lang": "en"},
    {"name": "Yes/No (VI)", "scale": 2, "mapping": YES_NO_VI, "lang": "vi"},
    {"name": "Yes/No (EN)", "scale": 2, "mapping": YES_NO_EN, "lang": "en"},
    {"name": "Importance 5 (VI)", "scale": 5, "mapping": IMPORTANCE_5_VI, "lang": "vi"},
    {"name": "Importance 5 (EN)", "scale": 5, "mapping": IMPORTANCE_5_EN, "lang": "en"},
]


def auto_detect_mapping(values):
    """
    Given a list/Series of text values from a column, detect the best Likert mapping.

    Args:
        values: iterable of string values (column values)

    Returns:
        dict with keys: name, scale, mapping, lang, match_ratio
        or None if no mapping matches >= 50% of non-null values
    """
    import unicodedata

    # Normalize and get unique non-null text values
    unique_vals = set()
    total_count = 0
    for v in values:
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            continue
        s = str(v).strip().lower()
        s = unicodedata.normalize("NFC", s)
        if s:
            unique_vals.add(s)
            total_count += 1

    if not unique_vals or total_count == 0:
        return None

    best_match = None
    best_ratio = 0.0

    for entry in ALL_MAPPINGS:
        mapping = entry["mapping"]
        matched = sum(1 for v in unique_vals if v in mapping)
        ratio = matched / len(unique_vals) if unique_vals else 0

        if ratio > best_ratio:
            best_ratio = ratio
            best_match = {
                "name": entry["name"],
                "scale": entry["scale"],
                "mapping": entry["mapping"],
                "lang": entry["lang"],
                "match_ratio": ratio,
            }

    # Require at least 50% of unique values to match
    if best_match and best_match["match_ratio"] >= 0.5:
        return best_match

    return None
