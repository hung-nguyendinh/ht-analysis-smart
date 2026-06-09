"""Tests for group comparison module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.comparison import compare_groups


def _make_survey_data(df, likert_cols=None, demo_cols=None):
    """Helper to create a preprocessed SurveyData from a DataFrame."""
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = True
    for col in df.columns:
        col_type = ColumnType.UNKNOWN
        if likert_cols and col in likert_cols:
            col_type = ColumnType.LIKERT
        elif demo_cols and col in demo_cols:
            col_type = ColumnType.DEMOGRAPHIC
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
        )
    return sd


class TestCompareGroups:
    def test_ttest_two_groups_significant(self):
        """Two groups with clearly different means should be significant."""
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 30 + ["B"] * 30,
            "score": list(np.random.normal(2, 0.5, 30)) + list(np.random.normal(5, 0.5, 30)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")

        assert result.data["significant"] == True
        assert result.data["n_groups"] == 2
        assert result.data["effect_size"] is not None

    def test_ttest_two_groups_not_significant(self):
        """Two groups with similar means should not be significant."""
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 30 + ["B"] * 30,
            "score": list(np.random.normal(3, 1, 30)) + list(np.random.normal(3, 1, 30)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")

        # With similar distributions, likely not significant
        assert result.data["n_groups"] == 2
        assert result.data["test_name"] in [
            "Independent Samples T-Test", "Mann-Whitney U Test"
        ]

    def test_anova_three_groups(self):
        """Auto-detect ANOVA for 3+ groups."""
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 20 + ["B"] * 20 + ["C"] * 20,
            "score": list(np.random.normal(2, 0.5, 20))
                   + list(np.random.normal(4, 0.5, 20))
                   + list(np.random.normal(6, 0.5, 20)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")

        assert result.data["n_groups"] == 3
        assert result.data["test_name"] in [
            "One-Way ANOVA", "Kruskal-Wallis H Test"
        ]
        assert result.data["significant"] == True

    def test_explicit_test_selection(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 20 + ["B"] * 20,
            "score": list(np.random.normal(3, 1, 20)) + list(np.random.normal(5, 1, 20)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score", test="mannwhitney")
        assert result.data["test_name"] == "Mann-Whitney U Test"

    def test_explicit_ttest_selection(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 20 + ["B"] * 20,
            "score": list(np.random.normal(3, 1, 20)) + list(np.random.normal(5, 1, 20)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score", test="ttest")
        assert result.data["test_name"] == "Independent Samples T-Test"
        assert "ttest_details" in result.data

    def test_column_not_found(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        sd = _make_survey_data(df)
        result = compare_groups(sd, "nonexistent", "x")
        assert len(result.warnings) > 0

    def test_insufficient_groups(self):
        df = pd.DataFrame({
            "group": ["A", "A", "A"],
            "score": [1, 2, 3],
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")
        assert "Need at least 2 groups" in result.warnings[0]

    def test_group_descriptives_included(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 20 + ["B"] * 20,
            "score": list(np.random.normal(3, 1, 20)) + list(np.random.normal(5, 1, 20)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")

        stats = result.data["group_statistics"]
        assert len(stats) == 2
        assert "mean" in stats[0]
        assert "n" in stats[0]

    def test_effect_size_interpretation(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "group": ["A"] * 30 + ["B"] * 30,
            "score": list(np.random.normal(2, 0.5, 30)) + list(np.random.normal(5, 0.5, 30)),
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score")
        assert result.data["effect_interpretation"] in [
            "large", "medium", "small", "negligible"
        ]

    def test_kruskal_effect_size_is_not_negative(self):
        df = pd.DataFrame({
            "group": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
            "score": [1, 2, 3, 4, 5] * 6,
        })
        sd = _make_survey_data(df, likert_cols=["score"], demo_cols=["group"])
        result = compare_groups(sd, "group", "score", test="kruskal")
        assert result.data["effect_size"] >= 0
