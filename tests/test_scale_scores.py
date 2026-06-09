"""Tests for composite scale score creation."""
import pandas as pd

from models.data_schema import ColumnInfo, ColumnType, SurveyData
from services.correlation import compute_pairwise_correlation
from services.regression import compute_linear_regression
from services.scale_scores import create_scale_score


def _make_survey_data(df, numeric_cols=None):
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = True
    for col in df.columns:
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=ColumnType.LIKERT if numeric_cols and col in numeric_cols else ColumnType.UNKNOWN,
        )
    return sd


def test_create_scale_score_mean_column():
    df = pd.DataFrame({
        "q1": [1, 2, 3, 4],
        "q2": [3, 4, 5, 6],
        "outcome": [2, 3, 4, 5],
    })
    sd = _make_survey_data(df, numeric_cols=["q1", "q2", "outcome"])

    summary = create_scale_score(sd, "Scale_A", ["q1", "q2"])

    assert summary["column"] == "Scale_A"
    assert sd.df["Scale_A"].tolist() == [2.0, 3.0, 4.0, 5.0]
    assert sd.columns_info["Scale_A"].detected_type == ColumnType.NUMERIC
    assert "Scale_A" in sd.get_numeric_columns()


def test_scale_score_can_feed_correlation_and_regression():
    df = pd.DataFrame({
        "q1": [1, 2, 3, 4, 5, 6],
        "q2": [2, 3, 4, 5, 6, 7],
        "outcome": [2, 3, 4, 5, 6, 7],
    })
    sd = _make_survey_data(df, numeric_cols=["q1", "q2", "outcome"])
    create_scale_score(sd, "Scale_A", ["q1", "q2"])

    corr = compute_pairwise_correlation(sd, "Scale_A", "outcome")
    reg = compute_linear_regression(sd, "outcome", ["Scale_A"])

    assert corr.data["significant"] == True
    assert corr.data["r"] == 1.0
    assert reg.data["r_squared"] == 1.0
