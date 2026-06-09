"""
Analysis Manager — Orchestrator for all statistical analysis modules.
"""
from models.data_schema import SurveyData, AnalysisType
from services.descriptive_stats import compute_descriptive, compute_frequency_table, compute_overall_mean_by_group
from services.reliability import compute_cronbach_alpha, compute_item_total_correlation
from services.correlation import compute_correlation_matrix, compute_pairwise_correlation
from services.comparison import compare_groups
from services.regression import compute_linear_regression
from services.efa import compute_efa
from services.scale_scores import (
    create_factor_scores_from_efa,
    create_scale_score,
)
from services.data_quality_report import generate_quality_report
from services.suggestion import generate_suggestions
from services.explainer import explain_result, explain_all, explain_with_ai
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisManager:
    """
    Orchestrator that manages and runs all statistical analyses on SurveyData.
    Results are stored in survey_data.analysis_results.
    """

    def __init__(self, survey_data: SurveyData):
        if not survey_data.is_preprocessed:
            raise ValueError("SurveyData must be preprocessed before analysis. Run preprocess_pipeline() first.")
        self.survey_data = survey_data
        logger.info("AnalysisManager initialized.")

    # ----------------------------------------------------------------
    # Descriptive Statistics
    # ----------------------------------------------------------------

    def run_descriptive(self, columns: list = None):
        """Run descriptive statistics and store result."""
        result = compute_descriptive(self.survey_data, columns)
        self.survey_data.add_analysis(result)
        logger.info(f"Descriptive stats completed: {result.summary_text}")
        return result

    def run_frequency(self, column: str):
        """Run frequency table for a single column and store result."""
        result = compute_frequency_table(self.survey_data, column)
        self.survey_data.add_analysis(result)
        logger.info(f"Frequency table completed for: {column}")
        return result

    def run_group_means(self, group_col: str, value_cols: list = None):
        """Run grouped means analysis and store result."""
        result = compute_overall_mean_by_group(self.survey_data, group_col, value_cols)
        self.survey_data.add_analysis(result)
        logger.info(f"Group means completed for: {group_col}")
        return result

    # ----------------------------------------------------------------
    # Reliability
    # ----------------------------------------------------------------

    def run_reliability(self, columns: list = None):
        """Run Cronbach's Alpha analysis and store result."""
        result = compute_cronbach_alpha(self.survey_data, columns)
        self.survey_data.add_analysis(result)
        logger.info(f"Reliability analysis completed: {result.summary_text}")
        return result

    def run_item_analysis(self, columns: list = None):
        """Run item-total correlation analysis and store result."""
        result = compute_item_total_correlation(self.survey_data, columns)
        self.survey_data.add_analysis(result)
        logger.info(f"Item analysis completed: {result.summary_text}")
        return result

    # ----------------------------------------------------------------
    # Correlation
    # ----------------------------------------------------------------

    def run_correlation(self, columns: list = None, method: str = "pearson"):
        """Run correlation matrix analysis and store result."""
        result = compute_correlation_matrix(self.survey_data, columns, method)
        self.survey_data.add_analysis(result)
        logger.info(f"Correlation analysis completed: {result.summary_text}")
        return result

    def run_pairwise_correlation(self, col_a: str, col_b: str, method: str = "pearson"):
        """Run pairwise correlation and store result."""
        result = compute_pairwise_correlation(self.survey_data, col_a, col_b, method)
        self.survey_data.add_analysis(result)
        logger.info(f"Pairwise correlation completed: {col_a} × {col_b}")
        return result

    # ----------------------------------------------------------------
    # Group Comparison
    # ----------------------------------------------------------------

    def run_comparison(self, group_col: str, value_col: str, test: str = "auto"):
        """Run group comparison test and store result."""
        result = compare_groups(self.survey_data, group_col, value_col, test)
        self.survey_data.add_analysis(result)
        logger.info(f"Comparison completed: {result.summary_text}")
        return result

    # ----------------------------------------------------------------
    # Regression
    # ----------------------------------------------------------------

    def run_regression(self, dependent_col: str, independent_cols: list):
        """Run linear regression and store result."""
        result = compute_linear_regression(self.survey_data, dependent_col, independent_cols)
        self.survey_data.add_analysis(result)
        logger.info(f"Regression completed: {result.summary_text}")
        return result

    # ----------------------------------------------------------------
    # Exploratory Factor Analysis
    # ----------------------------------------------------------------

    def run_efa(self, columns: list = None, n_factors: int = None,
                rotation: str = "varimax", loading_threshold: float = 0.5):
        """Run Exploratory Factor Analysis and store result."""
        result = compute_efa(
            self.survey_data, columns, n_factors, rotation, loading_threshold
        )
        self.survey_data.add_analysis(result)
        logger.info(f"EFA completed: {result.summary_text}")
        return result

    # ----------------------------------------------------------------
    # Scale / Factor Scores
    # ----------------------------------------------------------------

    def create_scale_score(
        self,
        new_col_name: str,
        item_cols: list,
        method: str = "mean",
        min_valid_items: int = None,
        overwrite: bool = False,
    ) -> dict:
        """Create a composite score column for correlation/regression."""
        result = create_scale_score(
            self.survey_data,
            new_col_name=new_col_name,
            item_cols=item_cols,
            method=method,
            min_valid_items=min_valid_items,
            overwrite=overwrite,
        )
        logger.info(f"Scale score created: {result['column']}")
        return result

    def create_factor_scores_from_efa(
        self,
        efa_result,
        prefix: str = "Factor",
        min_valid_items: int = None,
        overwrite: bool = False,
    ) -> list:
        """Create mean score columns from the factor groups in an EFA result."""
        efa_data = getattr(efa_result, "data", efa_result)
        results = create_factor_scores_from_efa(
            self.survey_data,
            efa_data=efa_data,
            prefix=prefix,
            min_valid_items=min_valid_items,
            overwrite=overwrite,
        )
        logger.info(f"Factor score columns created: {len(results)}")
        return results

    # ----------------------------------------------------------------
    # Phase 3: Quality, Suggestions, Explanations
    # ----------------------------------------------------------------

    def run_quality_report(self):
        """Generate comprehensive data quality report and store result."""
        result = generate_quality_report(self.survey_data)
        self.survey_data.add_analysis(result)
        logger.info(f"Quality report completed: {result.summary_text}")
        return result

    def run_suggestions(self):
        """Generate smart suggestions and store result."""
        result = generate_suggestions(self.survey_data)
        self.survey_data.add_analysis(result)
        logger.info(f"Suggestions generated: {result.summary_text}")
        return result

    def run_explanations(self, lang: str = "vi") -> list:
        """Generate plain-language explanations for all completed analyses."""
        return explain_all(self.survey_data, lang)

    def explain_single(self, result, lang: str = "vi") -> str:
        """Explain a single analysis result."""
        return explain_result(result, lang)

    def explain_single_with_ai(self, result, lang: str = "vi") -> str:
        """Explain a single analysis result with deep AI qualitative reasoning."""
        return explain_with_ai(result, lang)

    # ----------------------------------------------------------------
    # Batch Analysis
    # ----------------------------------------------------------------

    def run_all_basic(self):
        """
        Run all basic analyses automatically:
        1. Data quality report
        2. Descriptive stats for all numeric/Likert columns
        3. Frequency tables for all categorical/demographic columns
        4. Cronbach's Alpha for all Likert columns (if >= 2 items)
        5. Correlation matrix for all Likert columns (if >= 2)
        6. Smart suggestions

        Returns:
            dict with summary of all analyses run
        """
        results_summary = {}

        # 1. Quality report
        qr = self.run_quality_report()
        results_summary["quality_report"] = qr.summary_text

        # 2. Descriptive stats
        desc = self.run_descriptive()
        results_summary["descriptive"] = desc.summary_text

        # 3. Frequency tables for categorical and demographic columns
        cat_cols = self.survey_data.get_categorical_columns()
        demo_cols = self.survey_data.get_demographic_columns()
        freq_cols = cat_cols + demo_cols

        for col in freq_cols:
            self.run_frequency(col)
        results_summary["frequency_tables"] = f"{len(freq_cols)} tables generated"

        # 4. Reliability (if enough Likert items)
        likert_cols = self.survey_data.get_likert_columns()
        if len(likert_cols) >= 2:
            rel = self.run_reliability(likert_cols)
            results_summary["reliability"] = rel.summary_text
        else:
            results_summary["reliability"] = "Skipped (fewer than 2 Likert items)"

        # 5. Correlation matrix
        if len(likert_cols) >= 2:
            corr = self.run_correlation(likert_cols)
            results_summary["correlation"] = corr.summary_text
        else:
            results_summary["correlation"] = "Skipped (fewer than 2 numeric columns)"

        # 6. Smart suggestions
        sug = self.run_suggestions()
        results_summary["suggestions"] = sug.summary_text

        self.survey_data.log(f"Basic analysis batch completed: {len(self.survey_data.analysis_results)} results.")
        return results_summary

    def get_results_summary(self) -> list:
        """Get a summary of all analysis results."""
        return [
            {
                "type": r.analysis_type.value,
                "title": r.title,
                "summary": r.summary_text,
                "warnings_count": len(r.warnings),
            }
            for r in self.survey_data.analysis_results
        ]
