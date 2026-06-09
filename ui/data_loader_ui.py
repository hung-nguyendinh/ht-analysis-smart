"""
Helper to load Streamlit UploadedFile objects into SurveyData.
"""
import tempfile
import os

from services.data_loader import load_file
from services.validator import validate_data
from services.preprocessing import preprocess_pipeline
from services.data_quality_report import generate_quality_report
from models.data_schema import SurveyData
from utils.logger import get_logger

logger = get_logger(__name__)


def load_uploaded_file(uploaded_file, sheet_name: str | None = None) -> SurveyData:
    """
    Load a Streamlit UploadedFile into a SurveyData object.

    Saves the uploaded file to a temp directory, loads it using the
    existing data_loader, then cleans up the temp file.

    Args:
        uploaded_file: Streamlit UploadedFile object
        sheet_name: Optional sheet name to load

    Returns:
        SurveyData with data loaded (not yet validated/preprocessed)
    """
    # Determine file extension
    filename = uploaded_file.name
    suffix = os.path.splitext(filename)[1].lower()

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        survey_data = load_file(tmp_path, sheet_name=sheet_name)
        survey_data.filename = filename  # Use original filename
        return survey_data
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def process_uploaded_file(uploaded_file, sheet_name: str | None = None) -> SurveyData:
    """
    Full pipeline: load → validate → preprocess → quality report.

    Args:
        uploaded_file: Streamlit UploadedFile object
        sheet_name: Optional sheet name to load

    Returns:
        Fully processed SurveyData
    """
    # 1. Load
    survey_data = load_uploaded_file(uploaded_file, sheet_name=sheet_name)

    # 2. Validate
    survey_data = validate_data(survey_data)

    # 3. Preprocess
    survey_data = preprocess_pipeline(survey_data)

    # 4. Quality report
    quality_result = generate_quality_report(survey_data)
    survey_data.add_analysis(quality_result)

    return survey_data
