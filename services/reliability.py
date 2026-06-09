"""
Reliability analysis module — Cronbach's Alpha, Item-Total Correlation.
"""
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from utils.logger import get_logger

logger = get_logger(__name__)


def _cronbach_alpha_raw(df: pd.DataFrame):
    """
    Compute Cronbach's Alpha from a DataFrame of item scores.
    Uses the formula: α = (k / (k-1)) * (1 - Σσ²_i / σ²_total)
    where k = number of items, σ²_i = variance of item i, σ²_total = variance of total score.

    Returns:
        (alpha, n_valid) tuple
    """
    df_clean = df.dropna()
    n = len(df_clean)
    k = df_clean.shape[1]

    if k < 2 or n < 2:
        return None, n

    item_variances = df_clean.var(axis=0, ddof=1)
    total_scores = df_clean.sum(axis=1)
    total_variance = total_scores.var(ddof=1)

    if total_variance == 0:
        return 0.0, n

    alpha = (k / (k - 1)) * (1 - item_variances.sum() / total_variance)
    return round(alpha, 4), n


def compute_cronbach_alpha(survey_data: SurveyData, columns: list = None) -> AnalysisResult:
    """
    Compute Cronbach's Alpha for a set of items (columns).

    Args:
        survey_data: Preprocessed SurveyData object
        columns: List of column names. If None, use all Likert columns.

    Returns:
        AnalysisResult with alpha value, item statistics, and interpretation
    """
    if columns is None:
        columns = survey_data.get_likert_columns()

    if len(columns) < 2:
        return AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            summary_text="Need at least 2 items to compute Cronbach's Alpha.",
            warnings=["Insufficient items for reliability analysis."],
            parameters={"columns": columns},
        )

    df = survey_data.df[columns]
    alpha, n_valid = _cronbach_alpha_raw(df)

    if alpha is None:
        return AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            summary_text="Could not compute alpha — insufficient valid data.",
            warnings=["Not enough valid cases after removing missing values."],
            parameters={"columns": columns, "n_valid": n_valid},
        )

    # Interpretation
    if alpha >= 0.9:
        interpretation = "Excellent"
    elif alpha >= 0.8:
        interpretation = "Good"
    elif alpha >= 0.7:
        interpretation = "Acceptable"
    elif alpha >= 0.6:
        interpretation = "Questionable"
    elif alpha >= 0.5:
        interpretation = "Poor"
    else:
        interpretation = "Unacceptable"

    # Item-total correlations and alpha-if-deleted
    item_stats = compute_item_analysis(df, columns)

    data = {
        "alpha": alpha,
        "n_items": len(columns),
        "n_valid": n_valid,
        "interpretation": interpretation,
        "item_statistics": item_stats,
    }

    summary = (
        f"Cronbach's Alpha = {alpha} ({interpretation}) | "
        f"{len(columns)} items, {n_valid} valid cases."
    )

    warnings = []
    if alpha < 0.7:
        warnings.append(
            f"Alpha ({alpha}) is below the commonly accepted threshold of 0.70. "
            "Consider reviewing items with low item-total correlations."
        )

    return AnalysisResult(
        analysis_type=AnalysisType.RELIABILITY,
        title="Cronbach's Alpha",
        data=data,
        summary_text=summary,
        parameters={"columns": columns},
        warnings=warnings,
    )


def compute_item_analysis(df: pd.DataFrame, columns: list) -> list:
    """
    Compute item-level statistics: corrected item-total correlation and alpha-if-deleted.

    Args:
        df: DataFrame with item columns only
        columns: Column names

    Returns:
        List of dicts with per-item statistics
    """
    df_clean = df.dropna()
    if len(df_clean) < 2 or len(columns) < 2:
        return []

    total = df_clean.sum(axis=1)
    scale_mean = total.mean()
    scale_variance = total.var(ddof=1)
    results = []

    for col in columns:
        # Corrected item-total correlation: correlation of item with total minus that item
        corrected_total = total - df_clean[col]
        if corrected_total.std() == 0 or df_clean[col].std() == 0:
            corr = 0.0
        else:
            corr = df_clean[col].corr(corrected_total)

        # Alpha if this item is deleted
        remaining_cols = [c for c in columns if c != col]
        if len(remaining_cols) >= 2:
            alpha_deleted, _ = _cronbach_alpha_raw(df_clean[remaining_cols])
        else:
            alpha_deleted = None

        # Scale Mean if Item Deleted
        scale_mean_if_deleted = round(scale_mean - df_clean[col].mean(), 4)

        # Scale Variance if Item Deleted
        remaining_total = total - df_clean[col]
        scale_variance_if_deleted = round(remaining_total.var(ddof=1), 4)

        results.append({
            "item": col,
            "mean": round(df_clean[col].mean(), 4),
            "std": round(df_clean[col].std(), 4),
            "corrected_item_total_corr": round(corr, 4) if not np.isnan(corr) else 0.0,
            "alpha_if_deleted": alpha_deleted,
            "scale_mean_if_deleted": scale_mean_if_deleted,
            "scale_variance_if_deleted": scale_variance_if_deleted,
        })

    return results


def compute_item_total_correlation(survey_data: SurveyData, columns: list = None) -> AnalysisResult:
    """
    Compute corrected item-total correlations for a set of items.

    Args:
        survey_data: Preprocessed SurveyData
        columns: Item columns. If None, use Likert columns.

    Returns:
        AnalysisResult with item-total correlation table
    """
    if columns is None:
        columns = survey_data.get_likert_columns()

    if len(columns) < 2:
        return AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Item-Total Correlations",
            warnings=["Need at least 2 items."],
            parameters={"columns": columns},
        )

    df = survey_data.df[columns]
    item_stats = compute_item_analysis(df, columns)

    low_corr_items = [
        item["item"] for item in item_stats
        if item["corrected_item_total_corr"] < 0.3
    ]

    warnings = []
    if low_corr_items:
        warnings.append(
            f"Items with low corrected item-total correlation (<0.30): "
            f"{', '.join(low_corr_items)}. Consider removing these items."
        )

    return AnalysisResult(
        analysis_type=AnalysisType.RELIABILITY,
        title="Item-Total Correlations",
        data={"item_statistics": item_stats},
        summary_text=f"Item-total correlations for {len(columns)} items.",
        parameters={"columns": columns},
        warnings=warnings,
    )
