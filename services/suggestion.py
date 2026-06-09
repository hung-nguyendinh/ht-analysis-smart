"""
Smart Suggestion Engine — Data cleaning, analysis, and post-analysis recommendations.
"""
from models.data_schema import (
    SurveyData, AnalysisResult, AnalysisType, ColumnType, IssueSeverity,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# Priority levels
HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def generate_suggestions(survey_data: SurveyData) -> AnalysisResult:
    """
    Generate smart suggestions based on data characteristics and analysis results.

    Three categories:
    1. Data cleaning suggestions (pre-analysis)
    2. Analysis suggestions (what tests to run)
    3. Post-analysis suggestions (based on completed analyses)

    Args:
        survey_data: SurveyData object (validated and/or preprocessed)

    Returns:
        AnalysisResult containing categorized suggestions
    """
    suggestions = []

    # 1. Data cleaning suggestions
    suggestions.extend(_cleaning_suggestions(survey_data))

    # 2. Analysis suggestions
    suggestions.extend(_analysis_suggestions(survey_data))

    # 3. Post-analysis suggestions
    suggestions.extend(_post_analysis_suggestions(survey_data))

    # Sort by priority
    priority_order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    suggestions.sort(key=lambda s: priority_order.get(s["priority"], 99))

    summary = (
        f"{len(suggestions)} suggestions generated: "
        f"{sum(1 for s in suggestions if s['priority'] == HIGH)} high, "
        f"{sum(1 for s in suggestions if s['priority'] == MEDIUM)} medium, "
        f"{sum(1 for s in suggestions if s['priority'] == LOW)} low priority."
    )

    return AnalysisResult(
        analysis_type=AnalysisType.SUGGESTION,
        title="Smart Suggestions",
        data={"suggestions": suggestions},
        summary_text=summary,
        parameters={"n_suggestions": len(suggestions)},
    )


# ──────────────────────────────────────────────────────────────────
# 1. DATA CLEANING SUGGESTIONS
# ──────────────────────────────────────────────────────────────────

def _cleaning_suggestions(survey_data: SurveyData) -> list:
    """Generate data cleaning suggestions based on validation results."""
    suggestions = []
    df = survey_data.df

    if df.empty:
        return [{
            "category": "cleaning",
            "priority": HIGH,
            "title": "Dataset trống",
            "action": "Kiểm tra lại file dữ liệu đã upload.",
            "reason": "Không có dữ liệu để phân tích.",
        }]

    n_rows = len(df)

    # Check sample size
    if n_rows < 30:
        suggestions.append({
            "category": "cleaning",
            "priority": HIGH,
            "title": "Cỡ mẫu quá nhỏ",
            "action": f"Thu thập thêm respondents. Hiện tại chỉ có {n_rows} respondents.",
            "reason": "Cỡ mẫu < 30 không đủ cho các phép kiểm thống kê đáng tin cậy.",
        })
    elif n_rows < 100:
        suggestions.append({
            "category": "cleaning",
            "priority": LOW,
            "title": "Cỡ mẫu vừa phải",
            "action": f"Cỡ mẫu hiện tại ({n_rows}) có thể đủ cho phân tích cơ bản, nhưng kết quả sẽ tin cậy hơn nếu có >= 100 respondents.",
            "reason": "Các phép kiểm thống kê hoạt động tốt hơn với mẫu lớn.",
        })

    # Column-level cleaning
    for col_name, col_info in survey_data.columns_info.items():
        # High missing columns
        if col_info.missing_ratio > 0.5:
            suggestions.append({
                "category": "cleaning",
                "priority": HIGH,
                "title": f"Nên xóa cột '{col_name}'",
                "action": f"Loại bỏ cột này khỏi phân tích.",
                "reason": f"Tỉ lệ missing quá cao ({col_info.missing_ratio*100:.1f}%). Dữ liệu không đủ tin cậy.",
            })
        elif col_info.missing_ratio > 0.2:
            suggestions.append({
                "category": "cleaning",
                "priority": MEDIUM,
                "title": f"Xem xét xử lý missing ở cột '{col_name}'",
                "action": "Cân nhắc imputation (thay thế bằng mean/median) hoặc loại bỏ các cases thiếu.",
                "reason": f"Cột có {col_info.missing_ratio*100:.1f}% missing. Cần xử lý trước khi phân tích.",
            })

        # Zero variance columns
        if col_info.unique_count <= 1 and col_info.detected_type != ColumnType.ID:
            suggestions.append({
                "category": "cleaning",
                "priority": MEDIUM,
                "title": f"Cột '{col_name}' không có biến thiên",
                "action": "Loại bỏ cột này khỏi phân tích thống kê.",
                "reason": "Cột chỉ có 1 giá trị duy nhất, không cung cấp thông tin phân biệt.",
            })

    # Validation issues
    if survey_data.is_validated:
        errors = survey_data.validation.get_issues_by_severity(IssueSeverity.ERROR)
        if errors:
            suggestions.append({
                "category": "cleaning",
                "priority": HIGH,
                "title": f"Có {len(errors)} lỗi nghiêm trọng trong dữ liệu",
                "action": "Xem chi tiết lỗi trong phần Validation và xử lý trước khi phân tích.",
                "reason": "Các lỗi này có thể ảnh hưởng đáng kể đến kết quả phân tích.",
            })

    return suggestions


# ──────────────────────────────────────────────────────────────────
# 2. ANALYSIS SUGGESTIONS
# ──────────────────────────────────────────────────────────────────

def _analysis_suggestions(survey_data: SurveyData) -> list:
    """Suggest which analyses to run based on data structure."""
    suggestions = []

    if not survey_data.is_preprocessed:
        return suggestions

    likert_cols = survey_data.get_likert_columns()
    demo_cols = survey_data.get_demographic_columns()
    numeric_cols = survey_data.get_numeric_columns()
    cat_cols = survey_data.get_categorical_columns()

    # Already-run analyses
    completed_types = {r.analysis_type for r in survey_data.analysis_results}

    # Descriptive should always be run
    if AnalysisType.DESCRIPTIVE not in completed_types and numeric_cols:
        suggestions.append({
            "category": "analysis",
            "priority": HIGH,
            "title": "Chạy thống kê mô tả (Descriptive Statistics)",
            "action": f"Tính Mean, Std, Median cho {len(numeric_cols)} cột số.",
            "reason": "Thống kê mô tả là bước đầu tiên bắt buộc trong mọi phân tích khảo sát.",
        })

    # Cronbach's Alpha
    if AnalysisType.RELIABILITY not in completed_types and len(likert_cols) >= 2:
        suggestions.append({
            "category": "analysis",
            "priority": HIGH,
            "title": "Kiểm tra độ tin cậy (Cronbach's Alpha)",
            "action": f"Tính Cronbach's Alpha cho {len(likert_cols)} items Likert.",
            "reason": "Cần kiểm tra xem thang đo có đo lường nhất quán hay không trước khi phân tích sâu.",
        })

    # Correlation
    if AnalysisType.CORRELATION not in completed_types and len(numeric_cols) >= 2:
        suggestions.append({
            "category": "analysis",
            "priority": MEDIUM,
            "title": "Phân tích tương quan (Correlation)",
            "action": f"Tính ma trận tương quan Pearson cho {len(numeric_cols)} biến số.",
            "reason": "Xem xét mối quan hệ giữa các biến trước khi chạy regression.",
        })

    # Group comparison
    if AnalysisType.COMPARISON not in completed_types and (demo_cols or cat_cols) and likert_cols:
        group_cols = demo_cols + cat_cols
        suggestions.append({
            "category": "analysis",
            "priority": MEDIUM,
            "title": "So sánh nhóm (T-test / ANOVA)",
            "action": f"So sánh điểm Likert giữa các nhóm: {', '.join(group_cols[:3])}.",
            "reason": "Phân tích sự khác biệt giữa các nhóm nhân khẩu học (giới tính, tuổi, v.v.).",
        })

    # Regression
    if AnalysisType.REGRESSION not in completed_types and len(numeric_cols) >= 2:
        suggestions.append({
            "category": "analysis",
            "priority": LOW,
            "title": "Phân tích hồi quy (Regression)",
            "action": "Xác định biến phụ thuộc và chạy Linear Regression.",
            "reason": "Regression giúp xác định biến nào có ảnh hưởng và mức ảnh hưởng đến biến kết quả.",
        })

    # Frequency tables for categorical
    if cat_cols or demo_cols:
        freq_types = [r for r in survey_data.analysis_results if r.analysis_type == AnalysisType.FREQUENCY]
        all_cat = cat_cols + demo_cols
        if len(freq_types) < len(all_cat):
            suggestions.append({
                "category": "analysis",
                "priority": LOW,
                "title": "Bảng tần suất cho biến phân loại",
                "action": f"Tạo bảng tần suất cho {len(all_cat)} biến phân loại/nhân khẩu.",
                "reason": "Hiểu phân bố mẫu theo từng nhóm (giới tính, tuổi, trình độ, v.v.).",
            })

    return suggestions


# ──────────────────────────────────────────────────────────────────
# 3. POST-ANALYSIS SUGGESTIONS
# ──────────────────────────────────────────────────────────────────

def _post_analysis_suggestions(survey_data: SurveyData) -> list:
    """Generate suggestions based on completed analysis results."""
    suggestions = []

    for result in survey_data.analysis_results:
        if result.analysis_type == AnalysisType.RELIABILITY:
            suggestions.extend(_reliability_suggestions(result))
        elif result.analysis_type == AnalysisType.CORRELATION:
            suggestions.extend(_correlation_suggestions(result))
        elif result.analysis_type == AnalysisType.COMPARISON:
            suggestions.extend(_comparison_suggestions(result))
        elif result.analysis_type == AnalysisType.REGRESSION:
            suggestions.extend(_regression_suggestions(result))

    return suggestions


def _reliability_suggestions(result: AnalysisResult) -> list:
    """Suggestions based on reliability results."""
    suggestions = []
    alpha = result.data.get("alpha")

    if alpha is None:
        return suggestions

    if alpha < 0.6:
        # Find items to potentially remove
        items = result.data.get("item_statistics", [])
        low_items = [
            item["item"] for item in items
            if item.get("corrected_item_total_corr", 1) < 0.3
        ]
        improve_items = [
            item for item in items
            if item.get("alpha_if_deleted") and item["alpha_if_deleted"] > alpha
        ]

        if low_items:
            suggestions.append({
                "category": "post_analysis",
                "priority": HIGH,
                "title": "Loại bỏ items có tương quan thấp",
                "action": f"Cân nhắc loại bỏ: {', '.join(low_items)}. Corrected item-total correlation < 0.30.",
                "reason": f"Cronbach's Alpha hiện tại = {alpha} (thấp). Loại bỏ items yếu sẽ cải thiện độ tin cậy.",
            })

        if improve_items:
            best = max(improve_items, key=lambda x: x["alpha_if_deleted"])
            suggestions.append({
                "category": "post_analysis",
                "priority": MEDIUM,
                "title": f"Loại '{best['item']}' sẽ tăng Alpha lên {best['alpha_if_deleted']}",
                "action": f"Thử bỏ item '{best['item']}' và chạy lại Cronbach's Alpha.",
                "reason": "Alpha-if-deleted cho thấy thang đo sẽ tốt hơn nếu không có item này.",
            })

    elif alpha < 0.7:
        suggestions.append({
            "category": "post_analysis",
            "priority": MEDIUM,
            "title": "Độ tin cậy ở mức chấp nhận được nhưng chưa tốt",
            "action": "Xem xét lại nội dung các items và kiểm tra item-total correlations.",
            "reason": f"Alpha = {alpha}. Ngưỡng tối thiểu thường là 0.70.",
        })

    return suggestions


def _correlation_suggestions(result: AnalysisResult) -> list:
    """Suggestions based on correlation results."""
    suggestions = []
    sig_pairs = result.data.get("significant_pairs", [])

    # Strong correlations → suggest regression
    strong_pairs = [p for p in sig_pairs if p.get("strength") in ("strong", "moderate")]
    if strong_pairs:
        top = strong_pairs[0]
        suggestions.append({
            "category": "post_analysis",
            "priority": MEDIUM,
            "title": "Phát hiện tương quan mạnh — nên thử Regression",
            "action": f"Thử chạy hồi quy với '{top['var1']}' và '{top['var2']}' (r={top['r']}).",
            "reason": "Tương quan mạnh gợi ý có thể có quan hệ nhân quả đáng nghiên cứu.",
        })

    # Very high correlation → multicollinearity warning
    very_high = [p for p in sig_pairs if abs(p.get("r", 0)) >= 0.85]
    if very_high:
        pairs_text = "; ".join([f"{p['var1']}×{p['var2']} (r={p['r']})" for p in very_high[:3]])
        suggestions.append({
            "category": "post_analysis",
            "priority": HIGH,
            "title": "Cảnh báo: Tương quan rất cao (đa cộng tuyến)",
            "action": f"Không nên đưa đồng thời vào Regression: {pairs_text}.",
            "reason": "Tương quan > 0.85 gây đa cộng tuyến, làm sai lệch hệ số hồi quy.",
        })

    return suggestions


def _comparison_suggestions(result: AnalysisResult) -> list:
    """Suggestions based on comparison results."""
    suggestions = []

    p_value = result.data.get("p_value")
    if p_value is None:
        return suggestions

    if p_value >= 0.05:
        n_groups = result.data.get("n_groups", 0)
        group_stats = result.data.get("group_statistics", [])
        total_n = sum(g.get("n", 0) for g in group_stats)

        if total_n < 50:
            suggestions.append({
                "category": "post_analysis",
                "priority": MEDIUM,
                "title": "Kết quả không có ý nghĩa — có thể do cỡ mẫu nhỏ",
                "action": f"Tăng cỡ mẫu (hiện tại N={total_n}). Cần ít nhất 30 mỗi nhóm.",
                "reason": "Cỡ mẫu nhỏ làm giảm power thống kê, khó phát hiện sự khác biệt thực.",
            })

    effect = result.data.get("effect_size")
    effect_interp = result.data.get("effect_interpretation", "")
    if effect is not None and effect_interp in ("large", "medium") and p_value >= 0.05:
        suggestions.append({
            "category": "post_analysis",
            "priority": MEDIUM,
            "title": "Effect size lớn nhưng chưa đạt ý nghĩa thống kê",
            "action": "Thu thập thêm dữ liệu để tăng power.",
            "reason": f"Effect size = {effect} ({effect_interp}) nhưng p = {p_value}.",
        })

    return suggestions


def _regression_suggestions(result: AnalysisResult) -> list:
    """Suggestions based on regression results."""
    suggestions = []

    r_sq = result.data.get("r_squared", 0)
    f_p = result.data.get("f_p_value", 1)
    dw = result.data.get("durbin_watson")

    if f_p >= 0.05:
        suggestions.append({
            "category": "post_analysis",
            "priority": HIGH,
            "title": "Mô hình hồi quy không có ý nghĩa thống kê",
            "action": "Xem xét lại biến độc lập hoặc thử mô hình khác.",
            "reason": f"F-test p = {f_p} ≥ 0.05. Mô hình không giải thích tốt biến phụ thuộc.",
        })

    if r_sq < 0.1 and f_p < 0.05:
        suggestions.append({
            "category": "post_analysis",
            "priority": MEDIUM,
            "title": "R² rất thấp — mô hình giải thích yếu",
            "action": "Thêm biến độc lập hoặc xem xét các yếu tố khác.",
            "reason": f"R² = {r_sq}. Mô hình chỉ giải thích {r_sq*100:.1f}% phương sai.",
        })

    if dw is not None and (dw < 1.5 or dw > 2.5):
        suggestions.append({
            "category": "post_analysis",
            "priority": MEDIUM,
            "title": "Có thể có tự tương quan trong phần dư",
            "action": "Kiểm tra lại dữ liệu hoặc thử các biến dạng lag.",
            "reason": f"Durbin-Watson = {dw}. Giá trị lý tưởng là gần 2.0.",
        })

    # Check individual predictors
    coefs = result.data.get("coefficients", [])
    non_sig_predictors = [
        c["variable"] for c in coefs
        if c["variable"] != "(Constant)" and c.get("p_value") is not None and c["p_value"] >= 0.05
    ]
    if non_sig_predictors:
        suggestions.append({
            "category": "post_analysis",
            "priority": LOW,
            "title": "Một số biến độc lập không có ý nghĩa thống kê",
            "action": f"Cân nhắc loại bỏ: {', '.join(non_sig_predictors)}.",
            "reason": "Các biến không có ý nghĩa (p ≥ 0.05) không đóng góp vào mô hình.",
        })

    return suggestions
