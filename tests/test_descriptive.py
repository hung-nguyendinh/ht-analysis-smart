"""Tests for descriptive statistics module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import SurveyData, ColumnInfo, ColumnType
from services.descriptive_stats import (
    compute_descriptive,
    compute_frequency_table,
    compute_overall_mean_by_group,
)


def _make_survey_data(df, likert_cols=None, demo_cols=None, cat_cols=None):
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
        elif cat_cols and col in cat_cols:
            col_type = ColumnType.CATEGORICAL
        sd.columns_info[col] = ColumnInfo(
            name=col,
            original_dtype=str(df[col].dtype),
            detected_type=col_type,
        )
    return sd


class TestComputeDescriptive:
    def test_basic_stats(self):
        df = pd.DataFrame({
            "q1": [1, 2, 3, 4, 5],
            "q2": [5, 4, 3, 2, 1],
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"])
        result = compute_descriptive(sd)

        assert result.analysis_type.value == "descriptive"
        table = result.data["descriptive_table"]
        assert len(table) == 2
        assert table[0]["Mean"] == 3.0
        assert table[0]["N"] == 5

    def test_with_missing_values(self):
        df = pd.DataFrame({
            "q1": [1, 2, np.nan, 4, 5],
        })
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = compute_descriptive(sd)
        table = result.data["descriptive_table"]
        assert table[0]["N"] == 4
        assert table[0]["Missing"] == 1

    def test_no_columns(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        sd = _make_survey_data(df)
        result = compute_descriptive(sd)
        assert "No numeric/Likert columns" in result.summary_text

    def test_all_nan_column(self):
        df = pd.DataFrame({"q1": [np.nan, np.nan, np.nan]})
        sd = _make_survey_data(df, likert_cols=["q1"])
        result = compute_descriptive(sd)
        # Should skip columns that are all NaN
        table = result.data.get("descriptive_table", [])
        assert len(table) == 0  # No valid data to describe


class TestComputeFrequencyTable:
    def test_basic_frequency(self):
        df = pd.DataFrame({"gender": ["Nam", "Nữ", "Nam", "Nam", "Nữ"]})
        sd = _make_survey_data(df, demo_cols=["gender"])
        result = compute_frequency_table(sd, "gender")

        table = result.data["frequency_table"]
        assert len(table) == 2
        # Check counts add up
        total_count = sum(row["Count"] for row in table)
        assert total_count == 5

    def test_with_missing(self):
        df = pd.DataFrame({"gender": ["Nam", "Nữ", None, "Nam", np.nan]})
        sd = _make_survey_data(df, demo_cols=["gender"])
        result = compute_frequency_table(sd, "gender")
        table = result.data["frequency_table"]
        # Should include "(Missing)" entry
        labels = [row["Value"] for row in table]
        assert "(Missing)" in labels

    def test_column_not_found(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        sd = _make_survey_data(df)
        result = compute_frequency_table(sd, "nonexistent")
        assert len(result.warnings) > 0


class TestComputeOverallMeanByGroup:
    def test_grouped_means(self):
        df = pd.DataFrame({
            "gender": ["M", "M", "F", "F"],
            "q1": [4, 5, 2, 3],
            "q2": [3, 4, 1, 2],
        })
        sd = _make_survey_data(df, likert_cols=["q1", "q2"], demo_cols=["gender"])
        result = compute_overall_mean_by_group(sd, "gender")

        records = result.data["grouped_means"]
        assert len(records) == 2

    def test_no_value_cols(self):
        df = pd.DataFrame({"gender": ["M", "F"], "name": ["A", "B"]})
        sd = _make_survey_data(df, demo_cols=["gender"])
        result = compute_overall_mean_by_group(sd, "gender")
        assert len(result.warnings) > 0
