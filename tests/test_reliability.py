"""Tests for reliability analysis module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.reliability import (
    compute_cronbach_alpha,
    compute_item_total_correlation,
    _cronbach_alpha_raw,
)


def _make_survey_data(df, likert_cols=None):
    """Helper to create a preprocessed SurveyData from a DataFrame."""
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = True
    for col in df.columns:
        col_type = ColumnType.LIKERT if (likert_cols and col in likert_cols) else ColumnType.UNKNOWN
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
        )
    return sd


class TestCronbachAlphaRaw:
    def test_high_reliability(self):
        """Items that are highly correlated should have high alpha."""
        np.random.seed(42)
        base = np.random.randint(1, 6, size=50)
        df = pd.DataFrame({
            "q1": base,
            "q2": base + np.random.randint(0, 2, size=50),
            "q3": base + np.random.randint(-1, 1, size=50),
        })
        alpha, n = _cronbach_alpha_raw(df)
        assert alpha is not None
        assert alpha > 0.7
        assert n == 50

    def test_low_reliability(self):
        """Random uncorrelated items should have low alpha."""
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, size=50),
            "q2": np.random.randint(1, 6, size=50),
            "q3": np.random.randint(1, 6, size=50),
        })
        alpha, n = _cronbach_alpha_raw(df)
        assert alpha is not None
        assert alpha < 0.5

    def test_insufficient_items(self):
        df = pd.DataFrame({"q1": [1, 2, 3, 4, 5]})
        alpha, n = _cronbach_alpha_raw(df)
        assert alpha is None

    def test_zero_variance(self):
        df = pd.DataFrame({
            "q1": [3, 3, 3, 3],
            "q2": [3, 3, 3, 3],
        })
        alpha, n = _cronbach_alpha_raw(df)
        assert alpha == 0.0


class TestComputeCronbachAlpha:
    def test_with_likert_columns(self):
        np.random.seed(42)
        base = np.random.randint(1, 6, size=30)
        df = pd.DataFrame({
            "q1": base,
            "q2": base + np.random.randint(0, 2, size=30),
            "q3": base + np.random.randint(-1, 1, size=30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2", "q3"])
        result = compute_cronbach_alpha(sd)

        assert result.data["alpha"] is not None
        assert result.data["n_items"] == 3
        assert result.data["interpretation"] in [
            "Excellent", "Good", "Acceptable", "Questionable", "Poor", "Unacceptable"
        ]

    def test_with_specific_columns(self):
        np.random.seed(42)
        base = np.random.randint(1, 6, size=30)
        df = pd.DataFrame({
            "q1": base,
            "q2": base,
            "other": np.random.randint(1, 10, size=30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])
        result = compute_cronbach_alpha(sd, columns=["q1", "q2"])
        assert result.data["n_items"] == 2

    def test_too_few_items(self):
        df = pd.DataFrame({"q1": [1, 2, 3]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = compute_cronbach_alpha(sd)
        assert "at least 2 items" in result.summary_text

    def test_item_statistics_included(self):
        np.random.seed(42)
        base = np.random.randint(1, 6, size=30)
        df = pd.DataFrame({
            "q1": base,
            "q2": base + np.random.randint(0, 2, size=30),
            "q3": base + np.random.randint(-1, 1, size=30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2", "q3"])
        result = compute_cronbach_alpha(sd)
        items = result.data["item_statistics"]
        assert len(items) == 3
        assert "corrected_item_total_corr" in items[0]
        assert "alpha_if_deleted" in items[0]


class TestItemTotalCorrelation:
    def test_basic(self):
        np.random.seed(42)
        base = np.random.randint(1, 6, size=30)
        df = pd.DataFrame({
            "q1": base,
            "q2": base + np.random.randint(0, 2, size=30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])
        result = compute_item_total_correlation(sd)
        assert result.data["item_statistics"] is not None
        assert len(result.data["item_statistics"]) == 2
