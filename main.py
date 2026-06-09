"""
Entry point for the Streamlit application.
Currently a stub to verify imports for Phase 1, 2 & 3.
"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    print("HT Analysis Smart - Phase 1, 2 & 3 Verification")
    
    # Phase 1 import check
    try:
        from config.likert_mapping import auto_detect_mapping
        from config.rules import MISSING_THRESHOLD_DROP
        from models.data_schema import SurveyData
        from utils.logger import get_logger
        from utils.helpers import is_missing_value
        from services.data_loader import load_file
        from services.validator import validate_data
        from services.preprocessing import preprocess_pipeline
        print("[OK] All Phase 1 modules imported successfully!")
    except ImportError as e:
        print(f"[ERROR] Phase 1 import error: {e}")
        sys.exit(1)

    # Phase 2 import check
    try:
        from models.data_schema import AnalysisResult, AnalysisType
        from services.descriptive_stats import compute_descriptive, compute_frequency_table
        from services.reliability import compute_cronbach_alpha, compute_item_total_correlation
        from services.correlation import compute_correlation_matrix, compute_pairwise_correlation
        from services.comparison import compare_groups
        from services.regression import compute_linear_regression
        from services.analysis_manager import AnalysisManager
        print("[OK] All Phase 2 modules imported successfully!")
    except ImportError as e:
        print(f"[ERROR] Phase 2 import error: {e}")
        sys.exit(1)

    # Phase 3 import check
    try:
        from services.data_quality_report import generate_quality_report
        from services.suggestion import generate_suggestions
        from services.explainer import explain_result, explain_all
        print("[OK] All Phase 3 modules imported successfully!")
    except ImportError as e:
        print(f"[ERROR] Phase 3 import error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
