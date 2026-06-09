"""Tests for data quality report module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.data_quality_report import (
    generate_quality_report,
    _compute_column_quality_score,
    _detect_straight_lining,
    _score_to_grade,
)


def _make_survey_data(df, likert_cols=None, demo_cols=None):
    """Helper to create a preprocessed SurveyData."""
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
            missing_count=df[col].isna().sum(),
            missing_ratio=df[col].isna().sum() / len(df) if len(df) > 0 else 0,
            unique_count=df[col].nunique(dropna=True),
        )
    return sd


class TestQualityReport:
    def test_basic_report(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, 50),
            "q2": np.random.randint(1, 6, 50),
            "gender": np.random.choice(["M", "F"], 50),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"], demo_cols=["gender"])
        result = generate_quality_report(sd)

        assert result.analysis_type.value == "quality_report"
        assert "dataset_score" in result.data
        assert "overview" in result.data
        assert "column_scores" in result.data
        assert result.data["dataset_score"] > 0

    def test_empty_dataset(self):
        sd = SurveyData(df=pd.DataFrame())
        sd.is_preprocessed = True
        result = generate_quality_report(sd)
        assert "empty" in result.summary_text.lower() or "Empty" in result.summary_text

    def test_high_missing_penalty(self):
        df = pd.DataFrame({
            "q1": [1, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        })
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_quality_report(sd)

        col_scores = result.data["column_scores"]
        assert col_scores[0]["quality_score"] < 70  # Should be penalized

    def test_perfect_data_high_score(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, 100),
            "q2": np.random.randint(1, 6, 100),
            "q3": np.random.randint(1, 6, 100),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2", "q3"])
        result = generate_quality_report(sd)
        assert result.data["dataset_score"] >= 80

    def test_small_sample_warning(self):
        df = pd.DataFrame({"q1": [1, 2, 3, 4, 5]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_quality_report(sd)
        assert any("sample" in w.lower() or "small" in w.lower() or "Sample" in w for w in result.warnings)


class TestStraightLining:
    def test_detect_straight_liners(self):
        df = pd.DataFrame({
            "q1": [3, 3, 1, 2, 4],
            "q2": [3, 3, 5, 3, 2],
            "q3": [3, 3, 2, 4, 1],
        })
        result = _detect_straight_lining(df, ["q1", "q2", "q3"])
        assert result["count"] == 2  # First two respondents: all 3s

    def test_no_straight_liners(self):
        df = pd.DataFrame({
            "q1": [1, 2, 3],
            "q2": [3, 1, 2],
            "q3": [2, 3, 1],
        })
        result = _detect_straight_lining(df, ["q1", "q2", "q3"])
        assert result["count"] == 0

    def test_too_few_likert_items(self):
        df = pd.DataFrame({"q1": [1, 2, 3]})
        result = _detect_straight_lining(df, ["q1"])
        assert result["count"] == 0


class TestScoreToGrade:
    def test_grades(self):
        assert _score_to_grade(95) == "Excellent"
        assert _score_to_grade(85) == "Good"
        assert _score_to_grade(75) == "Acceptable"
        assert _score_to_grade(65) == "Fair"
        assert _score_to_grade(55) == "Poor"
        assert _score_to_grade(40) == "Critical"


class TestColumnQualityScore:
    def test_perfect_column(self):
        series = pd.Series([1, 2, 3, 4, 5] * 10, name="q1")
        score = _compute_column_quality_score(series)
        assert score["quality_score"] >= 90

    def test_all_missing(self):
        series = pd.Series([np.nan] * 10, name="q1")
        score = _compute_column_quality_score(series)
        assert score["quality_score"] <= 60

    def test_constant_column(self):
        series = pd.Series([3] * 20, name="q1")
        score = _compute_column_quality_score(series)
        assert score["quality_score"] < 85  # Zero variance penalty
