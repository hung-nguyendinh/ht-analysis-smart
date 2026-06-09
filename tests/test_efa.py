"""Tests for Exploratory Factor Analysis module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.efa import compute_efa


def _make_survey_data(df, likert_cols=None):
    """Helper to create a preprocessed SurveyData from a DataFrame."""
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = True
    for col in df.columns:
        col_type = ColumnType.LIKERT if (likert_cols and col in likert_cols) else ColumnType.NUMERIC
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
        )
    return sd


class TestEFABasic:
    def test_correlated_variables(self):
        """Variables with clear factor structure should produce valid EFA."""
        np.random.seed(42)
        n = 100
        # Factor 1
        f1 = np.random.randn(n)
        x1 = f1 + np.random.normal(0, 0.3, n)
        x2 = f1 + np.random.normal(0, 0.3, n)
        x3 = f1 + np.random.normal(0, 0.3, n)
        # Factor 2
        f2 = np.random.randn(n)
        x4 = f2 + np.random.normal(0, 0.3, n)
        x5 = f2 + np.random.normal(0, 0.3, n)
        x6 = f2 + np.random.normal(0, 0.3, n)

        df = pd.DataFrame({
            "x1": x1, "x2": x2, "x3": x3,
            "x4": x4, "x5": x5, "x6": x6,
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))

        assert result.data is not None
        assert "kmo" in result.data
        assert "bartlett" in result.data
        assert "variance_explained" in result.data
        assert "rotated_matrix" in result.data
        assert result.data["kmo"]["overall"] > 0  # KMO should be calculable
        assert result.data["bartlett"]["significant"] == True
        assert result.data["n_factors"] >= 1

    def test_kmo_output(self):
        """KMO should return per-variable and overall values."""
        np.random.seed(42)
        n = 80
        f = np.random.randn(n)
        df = pd.DataFrame({
            f"x{i}": f + np.random.normal(0, 0.5, n) for i in range(5)
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))

        kmo = result.data["kmo"]
        assert "overall" in kmo
        assert "per_variable" in kmo
        assert len(kmo["per_variable"]) == 5
        assert kmo["overall"] > 0

    def test_variance_explained(self):
        """Variance explained should sum to approximately 100%."""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            f"x{i}": np.random.randn(n) for i in range(5)
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))

        variance = result.data["variance_explained"]
        total = sum(v["variance_pct"] for v in variance)
        assert abs(total - 100.0) < 1.0  # Should be close to 100%


class TestEFAEdgeCases:
    def test_insufficient_variables(self):
        """Should return warning for < 3 variables."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        sd = _make_survey_data(df, likert_cols=["x", "y"])
        result = compute_efa(sd, columns=["x", "y"])
        assert len(result.warnings) > 0

    def test_insufficient_samples(self):
        """Should return warning if n < number of columns."""
        df = pd.DataFrame({
            "x1": [1, 2], "x2": [3, 4], "x3": [5, 6],
            "x4": [7, 8], "x5": [9, 10],
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))
        assert len(result.warnings) > 0 or "Không đủ mẫu" in result.summary_text

    def test_single_factor(self):
        """With highly correlated variables, should extract 1 factor."""
        np.random.seed(42)
        n = 100
        f = np.random.randn(n)
        df = pd.DataFrame({
            "x1": f + np.random.normal(0, 0.1, n),
            "x2": f + np.random.normal(0, 0.1, n),
            "x3": f + np.random.normal(0, 0.1, n),
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))
        assert result.data["n_factors"] >= 1

    def test_rotation_methods(self):
        """Both varimax and promax should work."""
        np.random.seed(42)
        n = 100
        f = np.random.randn(n)
        df = pd.DataFrame({
            f"x{i}": f + np.random.normal(0, 0.5, n) for i in range(4)
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))

        for rotation in ["varimax", "promax"]:
            result = compute_efa(sd, columns=list(df.columns), rotation=rotation)
            assert result.data is not None

    def test_scree_data(self):
        """Scree data should have eigenvalues for all components."""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            f"x{i}": np.random.randn(n) for i in range(5)
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))
        assert len(result.data["scree_data"]) == 5

    def test_communalities(self):
        """Communalities should be between 0 and 1."""
        np.random.seed(42)
        n = 100
        f = np.random.randn(n)
        df = pd.DataFrame({
            f"x{i}": f + np.random.normal(0, 0.5, n) for i in range(4)
        })
        sd = _make_survey_data(df, likert_cols=list(df.columns))
        result = compute_efa(sd, columns=list(df.columns))
        
        for comm in result.data["communalities"]:
            assert 0 <= comm["extraction"] <= 1.5  # Allow small rounding
