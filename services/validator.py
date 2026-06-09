"""
Service for validating survey data structure and quality.
Updated with Vietnamese messages and clearer suggestions.
"""
from models.data_schema import SurveyData, DataIssue, IssueSeverity
from config.rules import (
    MIN_ROWS,
    MIN_VALID_PER_COLUMN,
    MISSING_THRESHOLD_DROP,
    MISSING_THRESHOLD_WARN,
    RESPONDENT_MISSING_THRESHOLD,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def validate_data(survey_data: SurveyData) -> SurveyData:
    """
    Validate the loaded SurveyData object.
    Checks for structural integrity, missing values, duplicates, etc.
    """
    if not survey_data.is_loaded:
        survey_data.validation.add_issue(DataIssue(
            severity=IssueSeverity.ERROR,
            column=None,
            row=None,
            message="Dữ liệu chưa được tải lên.",
            suggestion="Vui lòng kiểm tra lại bước tải file.",
        ))
        return survey_data

    df = survey_data.df
    survey_data.log("Bắt đầu kiểm định dữ liệu.")

    # 1. Dataset-level validation
    if df.empty:
        survey_data.validation.add_issue(DataIssue(
            severity=IssueSeverity.ERROR,
            column=None,
            row=None,
            message="Tập dữ liệu rỗng.",
            suggestion="File của bạn không có dữ liệu hoặc định dạng không đúng. Hãy kiểm tra lại file gốc.",
        ))
        survey_data.is_validated = True
        return survey_data

    if len(df) < MIN_ROWS:
        survey_data.validation.add_issue(DataIssue(
            severity=IssueSeverity.WARNING,
            column=None,
            row=None,
            message=f"Dữ liệu chỉ có {len(df)} dòng. Kết quả thống kê có thể không tin cậy.",
            suggestion=f"Khuyên dùng ít nhất {MIN_ROWS} mẫu để phân tích có ý nghĩa.",
        ))

    # 2. Duplicate checking
    dupes = df.duplicated().sum()
    if dupes > 0:
        survey_data.validation.add_issue(DataIssue(
            severity=IssueSeverity.WARNING,
            column=None,
            row=None,
            message=f"Phát hiện {dupes} dòng dữ liệu trùng lặp hoàn toàn.",
            suggestion="Hãy kiểm tra xem có người trả lời hai lần không. Nên loại bỏ trùng lặp trước khi phân tích.",
        ))

    # 3. Column-level validation (Missing values)
    for col in df.columns:
        valid_count = df[col].count()  # Count of non-NA values
        missing_count = len(df) - valid_count
        missing_ratio = missing_count / len(df)

        if valid_count < MIN_VALID_PER_COLUMN:
            survey_data.validation.add_issue(DataIssue(
                severity=IssueSeverity.ERROR,
                column=col,
                row=None,
                message=f"Cột '{col}' chỉ có {valid_count} câu trả lời hợp lệ.",
                suggestion=f"Số lượng quá ít (tối thiểu {MIN_VALID_PER_COLUMN}). Cột này nên bị loại khỏi phân tích.",
            ))

        elif missing_ratio >= MISSING_THRESHOLD_DROP:
            survey_data.validation.add_issue(DataIssue(
                severity=IssueSeverity.ERROR,
                column=col,
                row=None,
                message=f"Cột '{col}' bị trống đến {missing_ratio*100:.1f}%.",
                suggestion=f"Tỷ lệ trống vượt ngưỡng {MISSING_THRESHOLD_DROP*100}%. Cột này không còn giá trị thống kê.",
            ))

        elif missing_ratio >= MISSING_THRESHOLD_WARN:
            survey_data.validation.add_issue(DataIssue(
                severity=IssueSeverity.WARNING,
                column=col,
                row=None,
                message=f"Cột '{col}' bị trống {missing_ratio*100:.1f}%.",
                suggestion="Cần lưu ý khi phân tích hoặc dùng phương pháp thay thế (imputation).",
            ))

        # Check for single-value columns (zero variance)
        if valid_count > 0 and df[col].nunique(dropna=True) == 1:
            val = df[col].dropna().iloc[0]
            survey_data.validation.add_issue(DataIssue(
                severity=IssueSeverity.WARNING,
                column=col,
                row=None,
                message=f"Cột '{col}' tất cả đều chọn cùng 1 giá trị là '{val}'.",
                suggestion="Cột này không có biến thiên, không thể dùng để so sánh hay tính tương quan.",
            ))

    # 4. Row-level validation (Respondent quality)
    row_missing_ratio = df.isna().sum(axis=1) / len(df.columns)
    bad_respondents = (row_missing_ratio >= RESPONDENT_MISSING_THRESHOLD).sum()

    if bad_respondents > 0:
        survey_data.validation.add_issue(DataIssue(
            severity=IssueSeverity.WARNING,
            column=None,
            row=None,
            message=f"Phát hiện {bad_respondents} người trả lời bỏ trống >= {RESPONDENT_MISSING_THRESHOLD*100}% số câu hỏi.",
            suggestion="Đây là những mẫu trả lời kém chất lượng. Nên cân nhắc loại bỏ các dòng này.",
        ))

    survey_data.is_validated = True
    summary = survey_data.validation.summary()
    survey_data.log(f"Hoàn thành kiểm định: {summary}")
    logger.info(summary)

    return survey_data
