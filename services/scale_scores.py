"""
Utilities for creating scale or factor score columns from survey items.
"""
import re
import unicodedata

import pandas as pd

from models.data_schema import SurveyData, ColumnInfo, ColumnType


def sanitize_score_name(name: str) -> str:
    """Return a stable, spreadsheet-friendly column name."""
    folded = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"\s+", "_", folded.strip())
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "", cleaned)
    return cleaned or "Scale_Score"


def create_scale_score(
    survey_data: SurveyData,
    new_col_name: str,
    item_cols: list,
    method: str = "mean",
    min_valid_items: int | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Create a composite score column from selected item columns.

    The new column is registered as numeric metadata so it is immediately
    available to correlation, regression, and group-comparison workflows.
    """
    if survey_data.df.empty:
        raise ValueError("Cannot create a scale score from an empty dataset.")

    if len(item_cols) < 2:
        raise ValueError("Select at least 2 item columns to create a scale score.")

    missing_cols = [col for col in item_cols if col not in survey_data.df.columns]
    if missing_cols:
        raise ValueError(f"Column(s) not found: {', '.join(missing_cols)}")

    method = method.lower().strip()
    if method not in {"mean", "sum"}:
        raise ValueError("method must be either 'mean' or 'sum'.")

    new_col_name = sanitize_score_name(new_col_name)
    if new_col_name in survey_data.df.columns and not overwrite:
        raise ValueError(f"Column '{new_col_name}' already exists.")

    if min_valid_items is None:
        min_valid_items = len(item_cols)
    min_valid_items = int(min_valid_items)
    if min_valid_items < 1 or min_valid_items > len(item_cols):
        raise ValueError("min_valid_items must be between 1 and the number of selected items.")

    item_data = survey_data.df[item_cols].apply(pd.to_numeric, errors="coerce")
    valid_counts = item_data.notna().sum(axis=1)

    if method == "sum":
        score = item_data.sum(axis=1, min_count=min_valid_items)
    else:
        score = item_data.mean(axis=1)
        score = score.where(valid_counts >= min_valid_items)

    valid_n = int(score.notna().sum())
    if valid_n == 0:
        raise ValueError("No valid score could be created with the selected items and minimum-valid rule.")

    survey_data.df[new_col_name] = score
    missing_count = int(score.isna().sum())
    survey_data.columns_info[new_col_name] = ColumnInfo(
        name=new_col_name,
        original_dtype=str(score.dtype),
        detected_type=ColumnType.NUMERIC,
        scale_name="Composite Scale Score",
        missing_count=missing_count,
        missing_ratio=missing_count / len(score) if len(score) else 0,
        unique_count=int(score.nunique(dropna=True)),
        is_converted=True,
    )
    survey_data.log(
        f"Created {method} scale score '{new_col_name}' from {len(item_cols)} items "
        f"with {valid_n} valid cases."
    )

    return {
        "column": new_col_name,
        "method": method,
        "items": item_cols,
        "n_items": len(item_cols),
        "min_valid_items": min_valid_items,
        "valid_n": valid_n,
        "missing_n": missing_count,
    }


def create_factor_scores_from_efa(
    survey_data: SurveyData,
    efa_data: dict,
    prefix: str = "Factor",
    min_valid_items: int | None = None,
    overwrite: bool = False,
) -> list[dict]:
    """Create one mean score column for each usable EFA factor grouping."""
    rotated = efa_data.get("rotated_matrix", []) if efa_data else []
    n_factors = int(efa_data.get("n_factors", 0) or 0) if efa_data else 0
    created = []

    for factor_idx in range(1, n_factors + 1):
        item_cols = [
            row["variable"]
            for row in rotated
            if row.get("assigned_factor") == factor_idx and row.get("meets_threshold", False)
        ]
        if len(item_cols) < 2:
            continue

        created.append(
            create_scale_score(
                survey_data=survey_data,
                new_col_name=f"{prefix}_{factor_idx}",
                item_cols=item_cols,
                method="mean",
                min_valid_items=min_valid_items,
                overwrite=overwrite,
            )
        )

    return created
