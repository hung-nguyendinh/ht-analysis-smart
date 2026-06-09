"""Tests for correlation analysis module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.correlation import (
    compute_correlation_matrix,
    compute_pairwise_correlation,
    _interpret_correlation,
)


def _make_survey_data(df, numeric_cols=None):
    """Helper to create a preprocessed SurveyData from a DataFrame."""
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = True
    for col in df.columns:
        col_type = ColumnType.LIKERT if (numeric_cols and col in numeric_cols) else ColumnType.UNKNOWN
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
        )
    return sd


class TestCorrelationMatrix:
    def test_perfect_positive(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_correlation_matrix(sd)

        corr = result.data["correlation_matrix"]
        assert round(corr["x"]["y"], 2) == 1.0  # Perfect positive correlation

    def test_matrix_symmetry(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "a": np.random.randn(30),
            "b": np.random.randn(30),
            "c": np.random.randn(30),
        })
        sd = _make_survey_data(df, numeric_cols=["a", "b", "c"])
        result = compute_correlation_matrix(sd)
        corr = result.data["correlation_matrix"]

        # Symmetry check
        assert corr["a"]["b"] == corr["b"]["a"]
        assert corr["a"]["c"] == corr["c"]["a"]

    def test_diagonal_is_one(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [5, 4, 3, 2, 1],
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_correlation_matrix(sd)
        corr = result.data["correlation_matrix"]

        assert corr["x"]["x"] == 1.0
        assert corr["y"]["y"] == 1.0

    def test_spearman_method(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [1, 2, 3, 4, 5],
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_correlation_matrix(sd, method="spearman")
        assert "Spearman" in result.title

    def test_too_few_columns(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        sd = _make_survey_data(df, numeric_cols=["x"])
        result = compute_correlation_matrix(sd)
        assert len(result.warnings) > 0

    def test_significant_pairs_detected(self):
        """Two highly correlated vars should show up in significant pairs."""
        df = pd.DataFrame({
            "x": list(range(30)),
            "y": list(range(30)),
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_correlation_matrix(sd)
        assert len(result.data["significant_pairs"]) > 0


class TestPairwiseCorrelation:
    def test_basic(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_pairwise_correlation(sd, "x", "y")
        assert result.data["r"] == 1.0
        assert result.data["significant"] == True

    def test_column_not_found(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        sd = _make_survey_data(df)
        result = compute_pairwise_correlation(sd, "x", "nonexistent")
        assert len(result.warnings) > 0

    def test_insufficient_data(self):
        df = pd.DataFrame({"x": [1, np.nan], "y": [2, np.nan]})
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_pairwise_correlation(sd, "x", "y")
        assert "Not enough" in result.warnings[0]


class TestInterpretCorrelation:
    def test_strong(self):
        assert _interpret_correlation(0.8) == "strong"
        assert _interpret_correlation(-0.75) == "strong"

    def test_moderate(self):
        assert _interpret_correlation(0.5) == "moderate"

    def test_weak(self):
        assert _interpret_correlation(0.25) == "weak"

    def test_negligible(self):
        assert _interpret_correlation(0.1) == "negligible"
