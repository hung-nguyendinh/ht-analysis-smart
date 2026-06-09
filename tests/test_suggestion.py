"""Tests for smart suggestion module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType, AnalysisResult, AnalysisType
from services.suggestion import generate_suggestions


def _make_survey_data(df, likert_cols=None, demo_cols=None, cat_cols=None, preprocessed=True):
    """Helper to create a SurveyData."""
    sd = SurveyData(df=df)
    sd.is_loaded = True
    sd.is_preprocessed = preprocessed
    sd.is_validated = True
    for col in df.columns:
        col_type = ColumnType.UNKNOWN
        if likert_cols and col in likert_cols:
            col_type = ColumnType.LIKERT
        elif demo_cols and col in demo_cols:
            col_type = ColumnType.DEMOGRAPHIC
        elif cat_cols and col in cat_cols:
            col_type = ColumnType.CATEGORICAL
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
            missing_count=df[col].isna().sum(),
            missing_ratio=df[col].isna().sum() / len(df) if len(df) > 0 else 0,
            unique_count=df[col].nunique(dropna=True),
        )
    return sd


class TestCleaningSuggestions:
    def test_small_sample_warning(self):
        df = pd.DataFrame({"q1": [1, 2, 3, 4, 5]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        cleaning = [s for s in suggestions if s["category"] == "cleaning"]
        assert any("mẫu" in s["title"].lower() or "cỡ" in s["title"].lower() for s in cleaning)

    def test_high_missing_column_drop(self):
        df = pd.DataFrame({
            "q1": [1, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        })
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        assert any("xóa" in s["title"].lower() or "Nên xóa" in s["title"] for s in suggestions)

    def test_empty_dataset(self):
        df = pd.DataFrame()
        sd = _make_survey_data(df)
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        assert any("trống" in s["title"].lower() for s in suggestions)


class TestAnalysisSuggestions:
    def test_suggests_descriptive(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, 30),
            "q2": np.random.randint(1, 6, 30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        analysis_suggestions = [s for s in suggestions if s["category"] == "analysis"]
        assert any("mô tả" in s["title"].lower() or "Descriptive" in s["title"] for s in analysis_suggestions)

    def test_suggests_cronbach(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, 30),
            "q2": np.random.randint(1, 6, 30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        assert any("tin cậy" in s["title"].lower() or "Cronbach" in s["title"] for s in suggestions)

    def test_suggests_comparison_with_demo(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "gender": np.random.choice(["M", "F"], 30),
            "q1": np.random.randint(1, 6, 30),
        })
        sd = _make_survey_data(df, likert_cols=["q1"], demo_cols=["gender"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        assert any("so sánh" in s["title"].lower() or "T-test" in s["title"] for s in suggestions)


class TestPostAnalysisSuggestions:
    def test_low_alpha_suggestion(self):
        """After running reliability with low alpha, should suggest improvements."""
        np.random.seed(42)
        df = pd.DataFrame({
            "q1": np.random.randint(1, 6, 30),
            "q2": np.random.randint(1, 6, 30),
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])

        # Simulate a reliability result with low alpha
        sd.analysis_results.append(AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            data={
                "alpha": 0.45,
                "item_statistics": [
                    {"item": "q1", "corrected_item_total_corr": 0.2, "alpha_if_deleted": 0.55},
                    {"item": "q2", "corrected_item_total_corr": 0.2, "alpha_if_deleted": 0.55},
                ],
            },
        ))

        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]
        post = [s for s in suggestions if s["category"] == "post_analysis"]
        assert len(post) > 0

    def test_priority_ordering(self):
        """Suggestions should be sorted by priority (high first)."""
        np.random.seed(42)
        df = pd.DataFrame({"q1": [1, 2, 3, 4, 5]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_suggestions(sd)
        suggestions = result.data["suggestions"]

        if len(suggestions) >= 2:
            priority_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(suggestions) - 1):
                assert priority_order[suggestions[i]["priority"]] <= priority_order[suggestions[i + 1]["priority"]]

    def test_suggestion_count_in_summary(self):
        df = pd.DataFrame({"q1": [1, 2, 3, 4, 5]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = generate_suggestions(sd)
        assert "suggestions" in result.summary_text.lower() or "suggestion" in result.summary_text.lower()
