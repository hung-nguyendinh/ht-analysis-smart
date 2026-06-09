"""Tests for result explainer module."""
import pytest
import pandas as pd
import numpy as np

from models.data_schema import AnalysisResult, AnalysisType
from services.explainer import explain_result, explain_all, _interpret_mean_level


class TestExplainDescriptive:
    def test_basic_explanation(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title="Descriptive Statistics",
            data={
                "descriptive_table": [
                    {"Column": "q1", "Mean": 3.8, "Std": 0.9, "N": 50, "Scale": "1-5",
                     "Median": 4.0, "Min": 1, "Max": 5, "Skewness": -0.3, "Kurtosis": -0.5},
                ]
            },
        )
        text = explain_result(result)
        assert "q1" in text
        assert "3.8" in text
        assert "cao" in text  # Mean 3.8 on 5-point = "cao"

    def test_empty_table(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title="Descriptive Statistics",
            data={"descriptive_table": []},
        )
        text = explain_result(result)
        assert "Không có" in text

    def test_high_skewness_warning(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            title="Descriptive Statistics",
            data={
                "descriptive_table": [
                    {"Column": "q1", "Mean": 2.0, "Std": 1.0, "N": 50,
                     "Median": 2.0, "Min": 1, "Max": 5, "Skewness": 1.5, "Kurtosis": 0},
                ]
            },
        )
        text = explain_result(result)
        assert "lệch" in text


class TestExplainReliability:
    def test_good_alpha(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            data={
                "alpha": 0.85,
                "n_items": 5,
                "n_valid": 100,
                "interpretation": "Good",
                "item_statistics": [],
            },
        )
        text = explain_result(result)
        assert "0.85" in text
        assert "Tốt" in text
        assert "đạt" in text.lower() or "✅" in text

    def test_low_alpha_with_weak_items(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            data={
                "alpha": 0.55,
                "n_items": 3,
                "n_valid": 50,
                "interpretation": "Poor",
                "item_statistics": [
                    {"item": "q1", "corrected_item_total_corr": 0.15, "alpha_if_deleted": 0.65},
                    {"item": "q2", "corrected_item_total_corr": 0.45, "alpha_if_deleted": 0.40},
                    {"item": "q3", "corrected_item_total_corr": 0.50, "alpha_if_deleted": 0.38},
                ],
            },
        )
        text = explain_result(result)
        assert "q1" in text  # Should flag weak item
        assert "⚠️" in text

    def test_no_alpha(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.RELIABILITY,
            title="Cronbach's Alpha",
            data={},
        )
        text = explain_result(result)
        assert "Không thể" in text


class TestExplainCorrelation:
    def test_with_significant_pairs(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.CORRELATION,
            title="Correlation Matrix",
            data={
                "significant_pairs": [
                    {"var1": "q1", "var2": "q2", "r": 0.72, "p": 0.001, "strength": "strong"},
                ]
            },
        )
        text = explain_result(result)
        assert "q1" in text
        assert "q2" in text
        assert "0.72" in text
        assert "mạnh" in text

    def test_no_significant_pairs(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.CORRELATION,
            title="Correlation Matrix",
            data={"significant_pairs": []},
        )
        text = explain_result(result)
        assert "Không" in text


class TestExplainComparison:
    def test_significant_result(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.COMPARISON,
            title="Group Comparison",
            data={
                "test_name": "Independent Samples T-Test",
                "statistic": 3.5,
                "p_value": 0.001,
                "significant": True,
                "effect_size": 0.85,
                "effect_size_label": "Cohen's d",
                "effect_interpretation": "large",
                "group_statistics": [
                    {"group": "Male", "mean": 3.2, "std": 0.8, "n": 30},
                    {"group": "Female", "mean": 4.1, "std": 0.7, "n": 30},
                ],
            },
        )
        text = explain_result(result)
        assert "✅" in text
        assert "khác biệt" in text
        assert "Female" in text  # Higher group

    def test_not_significant_result(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.COMPARISON,
            title="Group Comparison",
            data={
                "test_name": "Independent Samples T-Test",
                "statistic": 0.5,
                "p_value": 0.62,
                "significant": False,
                "effect_size": 0.1,
                "effect_size_label": "Cohen's d",
                "effect_interpretation": "negligible",
                "group_statistics": [
                    {"group": "A", "mean": 3.1, "std": 0.9, "n": 20},
                    {"group": "B", "mean": 3.2, "std": 0.8, "n": 20},
                ],
            },
        )
        text = explain_result(result)
        assert "❌" in text or "Không có" in text


class TestExplainRegression:
    def test_significant_model(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title="Linear Regression",
            data={
                "r_squared": 0.65,
                "adj_r_squared": 0.63,
                "f_statistic": 45.0,
                "f_p_value": 0.0001,
                "n": 50,
                "coefficients": [
                    {"variable": "(Constant)", "B": 1.5, "p_value": 0.01, "significant": True},
                    {"variable": "x1", "B": 0.8, "p_value": 0.001, "significant": True, "beta_standardized": 0.45},
                ],
            },
        )
        text = explain_result(result)
        assert "65.0%" in text
        assert "✅" in text
        assert "x1" in text

    def test_no_data(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title="Linear Regression",
            data={},
        )
        text = explain_result(result)
        assert "Không có" in text


class TestExplainQualityReport:
    def test_basic_explanation(self):
        result = AnalysisResult(
            analysis_type=AnalysisType.QUALITY_REPORT,
            title="Data Quality Report",
            data={
                "overview": {"n_respondents": 100, "n_columns": 10, "overall_missing_pct": 5.0},
                "dataset_score": 85,
                "dataset_grade": "Good",
                "column_scores": [],
                "missing_patterns": {"complete_pct": 90},
                "straight_lining": {"count": 0},
            },
        )
        text = explain_result(result)
        assert "85" in text
        assert "Tốt" in text


class TestInterpretMeanLevel:
    def test_5point_scale(self):
        assert _interpret_mean_level(4.5, 5) == "rất cao"
        assert _interpret_mean_level(3.8, 5) == "cao"
        assert _interpret_mean_level(3.0, 5) == "trung bình"
        assert _interpret_mean_level(2.0, 5) == "thấp"
        assert _interpret_mean_level(1.2, 5) == "rất thấp"

    def test_7point_scale(self):
        assert _interpret_mean_level(6.0, 7) == "rất cao"
        assert _interpret_mean_level(5.0, 7) == "cao"
        assert _interpret_mean_level(4.0, 7) == "trung bình"
        assert _interpret_mean_level(2.5, 7) == "thấp"
        assert _interpret_mean_level(1.5, 7) == "rất thấp"


class TestExplainAll:
    def test_explain_multiple_results(self):
        from models.data_schema import SurveyData
        sd = SurveyData()
        sd.analysis_results = [
            AnalysisResult(
                analysis_type=AnalysisType.DESCRIPTIVE,
                title="Descriptive",
                data={"descriptive_table": [
                    {"Column": "q1", "Mean": 3.5, "Std": 1.0, "N": 50, "Median": 3.5,
                     "Min": 1, "Max": 5, "Skewness": 0, "Kurtosis": 0},
                ]},
            ),
            AnalysisResult(
                analysis_type=AnalysisType.RELIABILITY,
                title="Reliability",
                data={"alpha": 0.8, "n_items": 3, "n_valid": 50,
                      "interpretation": "Good", "item_statistics": []},
            ),
        ]

        results = explain_all(sd)
        assert len(results) == 2
        assert results[0]["type"] == "descriptive"
        assert results[1]["type"] == "reliability"
        assert len(results[0]["explanation"]) > 0
