"""
Correlation analysis module — Pearson, Spearman correlation matrices with p-values.
"""
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from utils.logger import get_logger

logger = get_logger(__name__)


def compute_correlation_matrix(
    survey_data: SurveyData,
    columns: list = None,
    method: str = "pearson",
) -> AnalysisResult:
    """
    Compute correlation matrix for numeric/Likert columns.

    Args:
        survey_data: Preprocessed SurveyData object
        columns: Column names to include. If None, auto-detect numeric/Likert columns.
        method: "pearson" or "spearman"

    Returns:
        AnalysisResult with correlation matrix and p-value matrix
    """
    if columns is None:
        columns = survey_data.get_numeric_columns()

    if len(columns) < 2:
        return AnalysisResult(
            analysis_type=AnalysisType.CORRELATION,
            title=f"Correlation Matrix ({method.capitalize()})",
            warnings=["Need at least 2 numeric columns for correlation analysis."],
            parameters={"columns": columns, "method": method},
        )

    df = survey_data.df[columns]
    n = len(columns)

    # Compute correlation matrix
    corr_matrix = pd.DataFrame(
        np.zeros((n, n)), index=columns, columns=columns
    )
    p_matrix = pd.DataFrame(
        np.zeros((n, n)), index=columns, columns=columns
    )
    n_matrix = pd.DataFrame(
        np.zeros((n, n), dtype=int), index=columns, columns=columns
    )

    for i in range(n):
        for j in range(n):
            if i == j:
                corr_matrix.iloc[i, j] = 1.0
                p_matrix.iloc[i, j] = 0.0
                n_matrix.iloc[i, j] = df[columns[i]].count()
            else:
                # Pairwise complete observations
                pair = df[[columns[i], columns[j]]].dropna()
                n_obs = len(pair)
                n_matrix.iloc[i, j] = n_obs

                if n_obs < 3:
                    corr_matrix.iloc[i, j] = np.nan
                    p_matrix.iloc[i, j] = np.nan
                    continue

                if method == "spearman":
                    r, p = scipy_stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
                else:
                    r, p = scipy_stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])

                corr_matrix.iloc[i, j] = round(r, 4)
                p_matrix.iloc[i, j] = round(p, 4)

    # Find significant correlations
    sig_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            p_val = p_matrix.iloc[i, j]
            r_val = corr_matrix.iloc[i, j]
            if not np.isnan(p_val) and p_val < 0.05:
                strength = _interpret_correlation(r_val)
                sig_pairs.append({
                    "var1": columns[i],
                    "var2": columns[j],
                    "r": r_val,
                    "p": p_val,
                    "strength": strength,
                })

    data = {
        "correlation_matrix": corr_matrix.to_dict(),
        "p_value_matrix": p_matrix.to_dict(),
        "n_matrix": n_matrix.to_dict(),
        "significant_pairs": sig_pairs,
    }

    summary = (
        f"{method.capitalize()} correlation matrix for {n} variables. "
        f"Found {len(sig_pairs)} significant correlations (p < 0.05)."
    )

    return AnalysisResult(
        analysis_type=AnalysisType.CORRELATION,
        title=f"Correlation Matrix ({method.capitalize()})",
        data=data,
        summary_text=summary,
        parameters={"columns": columns, "method": method},
    )


def compute_pairwise_correlation(
    survey_data: SurveyData,
    col_a: str,
    col_b: str,
    method: str = "pearson",
) -> AnalysisResult:
    """
    Compute correlation between two specific variables.

    Args:
        survey_data: Preprocessed SurveyData
        col_a: First variable
        col_b: Second variable
        method: "pearson" or "spearman"

    Returns:
        AnalysisResult with r, p-value, and interpretation
    """
    for col in [col_a, col_b]:
        if col not in survey_data.df.columns:
            return AnalysisResult(
                analysis_type=AnalysisType.CORRELATION,
                title=f"Correlation: {col_a} × {col_b}",
                warnings=[f"Column '{col}' not found."],
            )

    pair = survey_data.df[[col_a, col_b]].dropna()
    n_obs = len(pair)

    if n_obs < 3:
        return AnalysisResult(
            analysis_type=AnalysisType.CORRELATION,
            title=f"Correlation: {col_a} × {col_b}",
            warnings=[f"Not enough valid observations ({n_obs}). Need at least 3."],
            parameters={"col_a": col_a, "col_b": col_b, "method": method},
        )

    if method == "spearman":
        r, p = scipy_stats.spearmanr(pair[col_a], pair[col_b])
    else:
        r, p = scipy_stats.pearsonr(pair[col_a], pair[col_b])

    r = round(r, 4)
    p = round(p, 4)
    strength = _interpret_correlation(r)
    sig = "significant" if p < 0.05 else "not significant"

    return AnalysisResult(
        analysis_type=AnalysisType.CORRELATION,
        title=f"Correlation: {col_a} × {col_b}",
        data={
            "r": r,
            "p_value": p,
            "n": n_obs,
            "method": method,
            "strength": strength,
            "significant": p < 0.05,
        },
        summary_text=(
            f"{method.capitalize()} r = {r} (p = {p}), {strength}, {sig}. "
            f"N = {n_obs}."
        ),
        parameters={"col_a": col_a, "col_b": col_b, "method": method},
    )


def _interpret_correlation(r: float) -> str:
    """Interpret correlation coefficient strength (Cohen's guidelines)."""
    abs_r = abs(r)
    if abs_r >= 0.7:
        return "strong"
    elif abs_r >= 0.4:
        return "moderate"
    elif abs_r >= 0.2:
        return "weak"
    else:
        return "negligible"
