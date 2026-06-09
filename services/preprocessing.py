"""
Core preprocessing pipeline for survey data.
"""
import re

import pandas as pd

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from config.likert_mapping import auto_detect_mapping
from config.rules import (
    DEMOGRAPHIC_KEYWORDS_VI,
    DEMOGRAPHIC_KEYWORDS_EN,
    ID_KEYWORDS,
    MAX_UNIQUE_CATEGORICAL,
)
from utils.helpers import is_missing_value, normalize_text, safe_convert_numeric
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_column_type(col_name: str, series: pd.Series) -> ColumnType:
    """Heuristic to detect column type based on name and content."""
    name_lower = normalize_text(col_name)
    compact_name = re.sub(r"[^a-z0-9]", "", name_lower)

    # 1. Check ID keywords
    if any(kw in name_lower.split() or name_lower.startswith(kw) for kw in ID_KEYWORDS):
        return ColumnType.ID

    # 2. Check Demographic keywords
    demo_kws = DEMOGRAPHIC_KEYWORDS_VI + DEMOGRAPHIC_KEYWORDS_EN
    if any(kw in name_lower for kw in demo_kws):
        return ColumnType.DEMOGRAPHIC

    # Common SPSS-style coded demographic names without spaces/diacritics.
    demo_compact_kws = [
        "gioitinh", "dotuoi", "trinhdo", "trinhdohv", "hocvan",
        "chuyennganh", "kinhnghiem", "chungchi", "loaihinh", "capdo",
    ]
    if any(kw in compact_name for kw in demo_compact_kws):
        return ColumnType.DEMOGRAPHIC

    # 3. Content-based detection
    valid_data = series.dropna()
    if len(valid_data) == 0:
        return ColumnType.UNKNOWN

    unique_count = valid_data.nunique()

    # If already numeric
    if pd.api.types.is_numeric_dtype(valid_data):
        # Is it categorical pretending to be numeric? (e.g., 1=Male, 2=Female or 5-point Likert)
        # We'll refine this later in the pipeline, but for now:
        if unique_count <= MAX_UNIQUE_CATEGORICAL:
            # We don't know if it's Likert or Demographic categorical yet
            return ColumnType.NUMERIC
        return ColumnType.NUMERIC

    # If text
    if unique_count <= MAX_UNIQUE_CATEGORICAL:
        return ColumnType.CATEGORICAL

    return ColumnType.OPEN_ENDED


def _coerce_numeric_like_series(series: pd.Series, min_ratio: float = 0.8):
    """Convert object columns that are mostly numeric-looking values."""
    valid = series.dropna()
    if valid.empty:
        return None

    converted = pd.to_numeric(series.apply(safe_convert_numeric), errors="coerce")
    ratio = converted.notna().sum() / len(valid)
    return converted if ratio >= min_ratio else None


def _infer_likert_scale(series: pd.Series):
    """Infer a numeric Likert scale size from observed values."""
    valid = series.dropna()
    if valid.empty:
        return None

    try:
        is_int_like = valid.apply(lambda value: float(value).is_integer()).all()
    except (TypeError, ValueError):
        return None

    if not is_int_like:
        return None

    min_v, max_v = valid.min(), valid.max()
    if min_v == 1 and max_v in [5, 7, 10]:
        return int(max_v)

    return None


def preprocess_pipeline(survey_data: SurveyData) -> SurveyData:
    """
    Main preprocessing pipeline for survey data.
    1. Standardize missing values
    2. Try to map text Likert scales → Numeric
    3. Infer column types
    4. Numeric conversion

    Args:
        survey_data: Validated SurveyData object

    Returns:
        Processed SurveyData object
    """
    if not survey_data.is_loaded:
        survey_data.log("Error: Data must be loaded before preprocessing.")
        return survey_data

    survey_data.log("Starting preprocessing pipeline.")
    df = survey_data.df.copy()

    # Step 1: Standardize Missing Values
    survey_data.log("Standardizing missing values across dataset.")
    for col in df.columns:
        df[col] = df[col].apply(lambda x: None if is_missing_value(x) else x)

    # Step 2 & 3: Process each column (Type infer & Likert mapping)
    for col in df.columns:
        series = df[col]
        col_info = ColumnInfo(
            name=col,
            original_dtype=str(series.dtype),
            missing_count=series.isna().sum(),
            missing_ratio=series.isna().sum() / len(series) if len(series) > 0 else 0,
            unique_count=series.nunique(dropna=True)
        )

        # Baseline detection
        col_type = detect_column_type(col, series)

        # Try Likert mapping if it's textual or categorical
        if not pd.api.types.is_numeric_dtype(series):
            mapping_result = auto_detect_mapping(series)

            if mapping_result:
                # Successfully found a Likert scale match!
                survey_data.log(f"Col '{col}': Detected Likert scale '{mapping_result['name']}' ({mapping_result['match_ratio']*100:.0f}% match).")

                # Apply mapping
                mapping_dict = mapping_result["mapping"]
                
                def map_val(x):
                    if pd.isna(x): return None
                    norm = normalize_text(str(x))
                    return mapping_dict.get(norm, x)

                df[col] = df[col].apply(map_val)
                # Convert the mapped column to numeric safely
                df[col] = pd.to_numeric(df[col].apply(safe_convert_numeric), errors="coerce")

                col_type = ColumnType.LIKERT
                col_info.scale_name = mapping_result["name"]
                col_info.scale_points = mapping_result["scale"]
                col_info.mapping_used = mapping_result["mapping"]
                col_info.is_converted = True

            else:
                numeric_series = _coerce_numeric_like_series(series)
                if numeric_series is not None:
                    df[col] = numeric_series
                    series = df[col]
                    col_info.is_converted = True
                    col_info.unique_count = series.nunique(dropna=True)

                    if col_type == ColumnType.DEMOGRAPHIC:
                        pass
                    else:
                        scale_points = _infer_likert_scale(series)
                        if scale_points:
                            col_type = ColumnType.LIKERT
                            col_info.scale_points = scale_points
                            survey_data.log(f"Col '{col}': Inferred numeric Likert scale (1-{scale_points}).")
                        else:
                            col_type = ColumnType.NUMERIC

                elif col_type != ColumnType.ID and col_type != ColumnType.DEMOGRAPHIC:
                    # If still text and unique count is small, maybe just categorical
                    if col_info.unique_count <= MAX_UNIQUE_CATEGORICAL:
                        col_type = ColumnType.CATEGORICAL
                    else:
                        col_type = ColumnType.OPEN_ENDED

        elif col_type == ColumnType.NUMERIC:
            # If already numeric, let's see if it looks like a Likert scale (1-5, 1-7)
            scale_points = _infer_likert_scale(series)
            if scale_points:
                col_type = ColumnType.LIKERT
                col_info.scale_points = scale_points
                survey_data.log(f"Col '{col}': Inferred numeric Likert scale (1-{scale_points}).")

        col_info.detected_type = col_type
        survey_data.columns_info[col] = col_info

    survey_data.df = df
    survey_data.is_preprocessed = True
    survey_data.log("Preprocessing pipeline completed successfully.")
    
    return survey_data
