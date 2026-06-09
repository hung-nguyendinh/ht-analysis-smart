"""
Data Quality Report — Comprehensive quality scoring and reporting for survey data.
"""
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, AnalysisResult, AnalysisType, ColumnType
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_quality_report(survey_data: SurveyData) -> AnalysisResult:
    """
    Generate a comprehensive data quality report.

    Includes:
    - Dataset overview
    - Per-column quality scores (0-100)
    - Overall dataset quality score (0-100)
    - Missing data patterns
    - Straight-lining detection
    - Scale consistency check

    Args:
        survey_data: Preprocessed SurveyData object

    Returns:
        AnalysisResult containing the quality report
    """
    df = survey_data.df
    warnings = []

    if df.empty:
        return AnalysisResult(
            analysis_type=AnalysisType.QUALITY_REPORT,
            title="Data Quality Report",
            summary_text="Dataset is empty — cannot generate quality report.",
            warnings=["Empty dataset."],
        )

    n_rows, n_cols = df.shape

    # ── 1. Overview ──────────────────────────────────────────────
    total_cells = n_rows * n_cols
    total_missing = df.isna().sum().sum()
    overall_missing_pct = round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0

    overview = {
        "n_respondents": n_rows,
        "n_columns": n_cols,
        "total_cells": total_cells,
        "total_missing": int(total_missing),
        "overall_missing_pct": overall_missing_pct,
        "filename": survey_data.filename,
        "encoding": survey_data.file_encoding,
    }

    # ── 2. Column Quality Scores ─────────────────────────────────
    column_scores = []
    for col in df.columns:
        score = _compute_column_quality_score(df[col], survey_data.columns_info.get(col))
        column_scores.append(score)

    # ── 3. Overall Dataset Quality Score ─────────────────────────
    if column_scores:
        col_score_values = [c["quality_score"] for c in column_scores]
        dataset_score = round(np.mean(col_score_values), 1)
    else:
        dataset_score = 0

    # Adjust for dataset-level issues
    if n_rows < 30:
        dataset_score = max(0, dataset_score - 15)
        warnings.append(f"Sample size ({n_rows}) is small. Results may not be generalizable.")
    elif n_rows < 50:
        dataset_score = max(0, dataset_score - 5)

    # ── 4. Missing Data Patterns ─────────────────────────────────
    missing_patterns = _analyze_missing_patterns(df)

    # ── 5. Straight-lining Detection ─────────────────────────────
    likert_cols = survey_data.get_likert_columns()
    straight_liners = _detect_straight_lining(df, likert_cols)
    if straight_liners["count"] > 0:
        pct = round(straight_liners["count"] / n_rows * 100, 1)
        warnings.append(
            f"{straight_liners['count']} respondent(s) ({pct}%) show straight-lining pattern "
            f"(same answer on all Likert items)."
        )
        dataset_score = max(0, dataset_score - min(10, straight_liners["count"]))

    # ── 6. Scale Consistency ─────────────────────────────────────
    scale_issues = _check_scale_consistency(survey_data)
    if scale_issues:
        warnings.extend(scale_issues)

    # ── Build quality grade ──────────────────────────────────────
    grade = _score_to_grade(dataset_score)

    data = {
        "overview": overview,
        "dataset_score": dataset_score,
        "dataset_grade": grade,
        "column_scores": column_scores,
        "missing_patterns": missing_patterns,
        "straight_lining": straight_liners,
    }

    summary = (
        f"Data Quality Score: {dataset_score}/100 ({grade}). "
        f"{n_rows} respondents, {n_cols} columns, {overall_missing_pct}% missing overall."
    )

    return AnalysisResult(
        analysis_type=AnalysisType.QUALITY_REPORT,
        title="Data Quality Report",
        data=data,
        summary_text=summary,
        warnings=warnings,
    )


def _compute_column_quality_score(series: pd.Series, col_info=None) -> dict:
    """
    Compute quality score (0-100) for a single column.

    Scoring:
    - Missing rate: up to -40 points
    - Variance: up to -20 points (zero variance = penalty)
    - Outliers: up to -15 points
    - Type consistency: up to -10 points
    """
    score = 100.0
    issues = []

    n = len(series)
    missing_count = series.isna().sum()
    missing_pct = missing_count / n * 100 if n > 0 else 0

    # Missing penalty (up to -40)
    if missing_pct > 50:
        score -= 40
        issues.append(f"Critical: {missing_pct:.1f}% missing")
    elif missing_pct > 20:
        score -= missing_pct * 0.6
        issues.append(f"High missing: {missing_pct:.1f}%")
    elif missing_pct > 5:
        score -= missing_pct * 0.3
        issues.append(f"Moderate missing: {missing_pct:.1f}%")

    # Variance check (up to -20)
    valid = series.dropna()
    if len(valid) > 0:
        if valid.nunique() == 1:
            score -= 20
            issues.append("Zero variance (constant value)")
        elif pd.api.types.is_numeric_dtype(valid) and len(valid) > 2:
            cv = valid.std() / valid.mean() if valid.mean() != 0 else 0
            if abs(cv) < 0.01:
                score -= 10
                issues.append("Very low variance")

    # Outlier check for numeric (up to -15)
    if pd.api.types.is_numeric_dtype(valid) and len(valid) >= 10:
        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outlier_count = ((valid < q1 - 1.5 * iqr) | (valid > q3 + 1.5 * iqr)).sum()
            outlier_pct = outlier_count / len(valid) * 100
            if outlier_pct > 10:
                score -= 15
                issues.append(f"{outlier_pct:.1f}% outliers")
            elif outlier_pct > 5:
                score -= 8
                issues.append(f"{outlier_pct:.1f}% outliers")

    score = max(0, round(score, 1))

    col_name = col_info.name if col_info else series.name
    col_type = col_info.detected_type.value if col_info else "unknown"

    return {
        "column": col_name,
        "type": col_type,
        "quality_score": score,
        "n_valid": int(n - missing_count),
        "missing_pct": round(missing_pct, 2),
        "issues": issues,
    }


def _analyze_missing_patterns(df: pd.DataFrame) -> dict:
    """Analyze missing data patterns across the dataset."""
    missing_matrix = df.isna()

    # Column-level missing
    col_missing = missing_matrix.sum().to_dict()

    # Row-level missing
    row_missing = missing_matrix.sum(axis=1)
    complete_rows = int((row_missing == 0).sum())
    rows_with_any_missing = int((row_missing > 0).sum())

    # Find columns that tend to be missing together
    missing_correlation_pairs = []
    cols_with_missing = [c for c in df.columns if missing_matrix[c].sum() > 0]

    if len(cols_with_missing) >= 2 and len(cols_with_missing) <= 50:
        for i in range(len(cols_with_missing)):
            for j in range(i + 1, len(cols_with_missing)):
                c1, c2 = cols_with_missing[i], cols_with_missing[j]
                both_missing = (missing_matrix[c1] & missing_matrix[c2]).sum()
                either_missing = (missing_matrix[c1] | missing_matrix[c2]).sum()
                if either_missing > 0:
                    co_occur = both_missing / either_missing
                    if co_occur > 0.5:
                        missing_correlation_pairs.append({
                            "col1": c1,
                            "col2": c2,
                            "co_occurrence": round(co_occur, 4),
                        })

    return {
        "complete_rows": complete_rows,
        "rows_with_missing": rows_with_any_missing,
        "complete_pct": round(complete_rows / len(df) * 100, 1) if len(df) > 0 else 0,
        "column_missing_counts": col_missing,
        "co_missing_pairs": missing_correlation_pairs[:10],  # Top 10
    }


def _detect_straight_lining(df: pd.DataFrame, likert_cols: list) -> dict:
    """
    Detect respondents who gave the same answer on all Likert items (straight-lining).
    Only checks if there are >= 3 Likert items.
    """
    if len(likert_cols) < 3:
        return {"count": 0, "respondent_indices": [], "threshold": "N/A (< 3 Likert items)"}

    subset = df[likert_cols].dropna(how="any")
    if subset.empty:
        return {"count": 0, "respondent_indices": [], "threshold": "N/A (no complete cases)"}

    # A respondent is straight-lining if std of their Likert responses is 0
    row_std = subset.std(axis=1)
    straight_liners = row_std[row_std == 0].index.tolist()

    return {
        "count": len(straight_liners),
        "respondent_indices": straight_liners[:20],  # Show max 20
        "n_likert_items": len(likert_cols),
    }


def _check_scale_consistency(survey_data: SurveyData) -> list:
    """Check if Likert columns with the same scale are consistent."""
    issues = []
    scale_groups = {}

    for name, info in survey_data.columns_info.items():
        if info.detected_type == ColumnType.LIKERT and info.scale_points:
            scale_groups.setdefault(info.scale_points, []).append(name)

    for scale, cols in scale_groups.items():
        if len(cols) >= 2:
            # Check if any column has values outside expected range
            for col in cols:
                series = survey_data.df[col].dropna()
                if len(series) > 0:
                    min_v, max_v = series.min(), series.max()
                    if min_v < 1 or max_v > scale:
                        issues.append(
                            f"Column '{col}' (scale 1-{scale}) has values "
                            f"outside range: min={min_v}, max={max_v}."
                        )

    return issues


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Good"
    elif score >= 70:
        return "Acceptable"
    elif score >= 60:
        return "Fair"
    elif score >= 50:
        return "Poor"
    else:
        return "Critical"
