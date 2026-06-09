"""
Descriptive statistics module for survey data analysis.
Computes mean, median, std, skewness, kurtosis, and frequency tables.
"""
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from models.data_schema import SurveyData, AnalysisResult, AnalysisType, ColumnType
from utils.logger import get_logger

logger = get_logger(__name__)


def compute_descriptive(survey_data: SurveyData, columns: list = None) -> AnalysisResult:
    """
    Compute descriptive statistics for numeric/Likert columns.

    Args:
        survey_data: Preprocessed SurveyData object
        columns: List of column names to analyze. If None, auto-detect numeric/Likert columns.

    Returns:
        AnalysisResult containing descriptive statistics DataFrame
    """
    if columns is None:
        columns = survey_data.get_numeric_columns()

    if not columns:
        return AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title="Descriptive Statistics",
            summary_text="No numeric/Likert columns found for descriptive analysis.",
            warnings=["No analyzable columns detected."],
        )

    df = survey_data.df[columns]
    results = []

    for col in columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue

        # Compute mode (may have multiple modes, take the first)
        mode_result = series.mode()
        mode_val = round(mode_result.iloc[0], 4) if len(mode_result) > 0 else None

        row = {
            "Column": col,
            "N": len(series),
            "Missing": df[col].isna().sum(),
            "Mean": round(series.mean(), 4),
            "Std": round(series.std(), 4),
            "Median": round(series.median(), 4),
            "Mode": mode_val,
            "Min": round(series.min(), 4),
            "Max": round(series.max(), 4),
            "Skewness": round(series.skew(), 4),
            "Kurtosis": round(series.kurtosis(), 4),
        }

        # Add scale info if available
        col_info = survey_data.columns_info.get(col)
        if col_info and col_info.scale_points:
            row["Scale"] = f"1-{col_info.scale_points}"

        results.append(row)

    result_df = pd.DataFrame(results)

    summary_parts = [
        f"Descriptive statistics for {len(results)} columns.",
        f"Total respondents (max N): {result_df['N'].max() if not result_df.empty else 0}.",
    ]

    if not result_df.empty:
        overall_mean = result_df["Mean"].mean()
        summary_parts.append(f"Overall mean across items: {overall_mean:.4f}.")

    return AnalysisResult(
        analysis_type=AnalysisType.DESCRIPTIVE,
        title="Descriptive Statistics",
        data={"descriptive_table": result_df.to_dict(orient="records")},
        summary_text=" ".join(summary_parts),
        parameters={"columns": columns},
    )


def compute_frequency_table(survey_data: SurveyData, column: str) -> AnalysisResult:
    """
    Compute frequency table for a single column.

    Args:
        survey_data: Preprocessed SurveyData object
        column: Column name to analyze

    Returns:
        AnalysisResult containing frequency table
    """
    if column not in survey_data.df.columns:
        return AnalysisResult(
            analysis_type=AnalysisType.FREQUENCY,
            title=f"Frequency Table — {column}",
            warnings=[f"Column '{column}' not found in dataset."],
        )

    series = survey_data.df[column]
    freq = series.value_counts(dropna=False).reset_index()
    freq.columns = ["Value", "Count"]
    freq["Percent"] = round(freq["Count"] / len(series) * 100, 2)
    freq["Valid Percent"] = round(
        freq[freq["Value"].notna()]["Count"]
        / series.count() * 100, 2
    ) if series.count() > 0 else 0

    # Cumulative percent for valid values only
    valid_mask = freq["Value"].notna()
    freq.loc[valid_mask, "Cumulative %"] = freq.loc[valid_mask, "Percent"].cumsum()

    # Convert NaN label for display
    freq["Value"] = freq["Value"].fillna("(Missing)")

    return AnalysisResult(
        analysis_type=AnalysisType.FREQUENCY,
        title=f"Frequency Table — {column}",
        data={"frequency_table": freq.to_dict(orient="records")},
        summary_text=f"Column '{column}': {series.nunique()} unique values, {series.isna().sum()} missing.",
        parameters={"column": column},
    )


def compute_overall_mean_by_group(
    survey_data: SurveyData,
    group_col: str,
    value_cols: list = None,
) -> AnalysisResult:
    """
    Compute mean values of numeric columns grouped by a demographic/categorical column.

    Args:
        survey_data: Preprocessed SurveyData object
        group_col: Grouping column (e.g., "Giới tính", "Trình độ")
        value_cols: Columns to compute means for. If None, use all Likert columns.

    Returns:
        AnalysisResult containing grouped means DataFrame
    """
    if value_cols is None:
        value_cols = survey_data.get_likert_columns()

    if not value_cols:
        return AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title=f"Group Means by {group_col}",
            warnings=["No Likert/numeric columns found."],
        )

    if group_col not in survey_data.df.columns:
        return AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title=f"Group Means by {group_col}",
            warnings=[f"Group column '{group_col}' not found."],
        )

    df = survey_data.df[[group_col] + value_cols].copy()
    grouped = df.groupby(group_col)[value_cols].agg(["mean", "count"])

    # Flatten multi-level columns
    result_records = []
    for group_name in grouped.index:
        row = {"Group": str(group_name)}
        for col in value_cols:
            row[f"{col}_mean"] = round(grouped.loc[group_name, (col, "mean")], 4)
            row[f"{col}_n"] = int(grouped.loc[group_name, (col, "count")])
        result_records.append(row)

    return AnalysisResult(
        analysis_type=AnalysisType.DESCRIPTIVE,
        title=f"Group Means by {group_col}",
        data={"grouped_means": result_records},
        summary_text=f"Means of {len(value_cols)} columns grouped by '{group_col}' ({len(result_records)} groups).",
        parameters={"group_col": group_col, "value_cols": value_cols},
    )
