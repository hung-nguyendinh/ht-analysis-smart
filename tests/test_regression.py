"""Tests for linear regression module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.regression import compute_linear_regression


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


class TestSimpleRegression:
    def test_perfect_linear(self):
        """y = 2x + 1 should give R² = 1.0"""
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [3, 5, 7, 9, 11, 13, 15, 17, 19, 21],
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["x"])

        assert result.data["r_squared"] == 1.0
        assert result.data["adj_r_squared"] == 1.0

        # Check coefficient: slope should be 2
        coefs = result.data["coefficients"]
        x_coef = [c for c in coefs if c["variable"] == "x"][0]
        assert round(x_coef["B"], 1) == 2.0

        # Intercept should be 1
        intercept = [c for c in coefs if c["variable"] == "(Constant)"][0]
        assert round(intercept["B"], 1) == 1.0

    def test_no_correlation(self):
        """Random data should have low R²."""
        np.random.seed(42)
        df = pd.DataFrame({
            "x": np.random.randn(50),
            "y": np.random.randn(50),
        })
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["x"])

        assert result.data["r_squared"] < 0.2

    def test_f_statistic_significant(self):
        """Strong relationship should produce significant F."""
        np.random.seed(42)
        x = np.arange(30, dtype=float)
        y = 3 * x + 10 + np.random.normal(0, 2, 30)
        df = pd.DataFrame({"x": x, "y": y})
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["x"])

        assert result.data["f_p_value"] < 0.05


class TestMultipleRegression:
    def test_two_predictors(self):
        np.random.seed(42)
        n = 50
        x1 = np.random.randn(n)
        x2 = np.random.randn(n)
        y = 2 * x1 + 3 * x2 + 5 + np.random.normal(0, 0.5, n)
        df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

        sd = _make_survey_data(df, numeric_cols=["x1", "x2", "y"])
        result = compute_linear_regression(sd, "y", ["x1", "x2"])

        assert result.data["r_squared"] > 0.8
        assert result.data["n"] == 50


class TestRegressionEdgeCases:
    def test_column_not_found(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["nonexistent"])
        assert len(result.warnings) > 0

    def test_insufficient_data(self):
        df = pd.DataFrame({"x": [1], "y": [2]})
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["x"])
        assert "Not enough valid observations" in result.warnings[0]

    def test_no_independent_vars(self):
        df = pd.DataFrame({"y": [1, 2, 3]})
        sd = _make_survey_data(df)
        result = compute_linear_regression(sd, "y", [])
        assert "at least 1 independent" in result.warnings[0]

    def test_durbin_watson_present(self):
        np.random.seed(42)
        x = np.arange(30, dtype=float)
        y = 2 * x + np.random.normal(0, 1, 30)
        df = pd.DataFrame({"x": x, "y": y})
        sd = _make_survey_data(df, numeric_cols=["x", "y"])
        result = compute_linear_regression(sd, "y", ["x"])
        assert "durbin_watson" in result.data

    def test_standardized_beta_present(self):
        np.random.seed(42)
        n = 50
        x1 = np.random.randn(n)
        y = 3 * x1 + np.random.normal(0, 0.5, n)
        df = pd.DataFrame({"x1": x1, "y": y})
        sd = _make_survey_data(df, numeric_cols=["x1", "y"])
        result = compute_linear_regression(sd, "y", ["x1"])

        coefs = result.data["coefficients"]
        x1_coef = [c for c in coefs if c["variable"] == "x1"][0]
        assert "beta_standardized" in x1_coef
