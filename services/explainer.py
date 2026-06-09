"""
Result Explainer — Interprets statistical results in plain Vietnamese/English.
"""
from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from services.llm_client import LLMClient
from utils.logger import get_logger

logger = get_logger(__name__)


def explain_result(result: AnalysisResult, lang: str = "vi") -> str:
    """
    Generate a plain-language explanation for a single analysis result.

    Args:
        result: AnalysisResult to explain
        lang: Language code ("vi" for Vietnamese, "en" for English)

    Returns:
        Human-readable explanation string
    """
    dispatch = {
        AnalysisType.DESCRIPTIVE: _explain_descriptive,
        AnalysisType.FREQUENCY: _explain_frequency,
        AnalysisType.RELIABILITY: _explain_reliability,
        AnalysisType.CORRELATION: _explain_correlation,
        AnalysisType.COMPARISON: _explain_comparison,
        AnalysisType.REGRESSION: _explain_regression,
        AnalysisType.QUALITY_REPORT: _explain_quality_report,
    }

    handler = dispatch.get(result.analysis_type)
    if handler is None:
        return f"Không có giải thích cho loại phân tích: {result.analysis_type.value}"

    return handler(result, lang)


def explain_with_ai(result: AnalysisResult, lang: str = "vi") -> str:
    """
    Use LLM to generate deep, focused insights for each specific analysis type.
    Dispatches to specialized prompt builders that extract actual numbers from result.data.
    """
    prompt_builders = {
        AnalysisType.RELIABILITY: _build_reliability_ai_prompt,
        AnalysisType.REGRESSION: _build_regression_ai_prompt,
        AnalysisType.CORRELATION: _build_correlation_ai_prompt,
        AnalysisType.COMPARISON: _build_comparison_ai_prompt,
        AnalysisType.DESCRIPTIVE: _build_descriptive_ai_prompt,
    }

    builder = prompt_builders.get(result.analysis_type)
    if builder is None:
        # Fallback generic
        basic = explain_result(result, lang)
        prompt = (
            f"Kết quả phân tích ({result.analysis_type.value}):\n{basic}\n\n"
            "Hãy giải thích ý nghĩa thực tế của kết quả này trong bối cảnh khảo sát, "
            "nêu nguyên nhân có thể và đề xuất cải thiện. Viết bằng tiếng Việt, tối đa 4 đoạn."
        )
    else:
        prompt = builder(result)

    system_prompt = (
        "Bạn là chuyên gia phân tích dữ liệu khảo sát với hơn 15 năm kinh nghiệm. "
        "Hãy phân tích kết quả thống kê được cung cấp và đưa ra nhận định chuyên sâu. "
        "Tập trung vào: (1) Chẩn đoán nguyên nhân gốc rễ từ góc độ thiết kế bảng hỏi và tâm lý đáp viên, "
        "(2) Đánh giá mức độ nghiêm trọng cụ thể, (3) Đề xuất hành động cải thiện chi tiết. "
        "Viết bằng tiếng Việt, rõ ràng, có cấu trúc heading markdown. "
        "KHÔNG lặp lại các con số đã cho — hãy tập trung vào GIẢI THÍCH và GỢI Ý."
    )

    client = LLMClient.get_default()
    try:
        return client.generate(prompt, system_prompt=system_prompt, max_tokens=1500)
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return f"Không thể gọi AI phân tích: {e}"


# ──────────────────────────────────────────────────────────────────
# SPECIALIZED AI PROMPT BUILDERS
# ──────────────────────────────────────────────────────────────────

def _build_reliability_ai_prompt(result: AnalysisResult) -> str:
    """Build a focused prompt for Cronbach's Alpha results."""
    data = result.data or {}
    alpha = data.get("alpha", "N/A")
    n_items = data.get("n_items", 0)
    n_valid = data.get("n_valid", 0)
    interp = data.get("interpretation", "")
    items = data.get("item_statistics", [])

    # Identify problematic items
    weak_items = [i for i in items if i.get("corrected_item_total_corr", 1) < 0.3]
    improve_items = [
        i for i in items
        if i.get("alpha_if_deleted") and i["alpha_if_deleted"] > (alpha if isinstance(alpha, (int, float)) else 0)
    ]

    weak_text = ""
    if weak_items:
        details = ", ".join(
            [f"'{i['item']}' (r={i.get('corrected_item_total_corr', 'N/A')})" for i in weak_items]
        )
        weak_text = f"\n- Các item có tương quan biến-tổng THẤP (<0.3): {details}"

    improve_text = ""
    if improve_items:
        details = ", ".join(
            [f"'{i['item']}' (Alpha nếu xóa={i['alpha_if_deleted']})" for i in improve_items]
        )
        improve_text = f"\n- Các item mà nếu loại bỏ sẽ cải thiện Alpha: {details}"

    return (
        f"## Phân tích Cronbach's Alpha\n"
        f"- Alpha = {alpha} ({interp}), Số items = {n_items}, N = {n_valid}"
        f"{weak_text}{improve_text}\n\n"
        f"Hãy phân tích chi tiết:\n"
        f"1. **Chẩn đoán nguyên nhân**: Tại sao các item có tương quan thấp? "
        f"Nguyên nhân có thể từ cách diễn đạt câu hỏi (mơ hồ, đa nghĩa, reverse-coded), "
        f"hay do item đo lường khái niệm khác với các item còn lại?\n"
        f"2. **Tâm lý đáp viên**: Liệu có dấu hiệu mệt mỏi khảo sát (survey fatigue), "
        f"trả lời qua loa, hay thiếu hiểu biết về chủ đề?\n"
        f"3. **Đề xuất cải thiện cụ thể**: Nên sửa lại nội dung câu hỏi như thế nào? "
        f"Nên loại item nào? Nên nhóm lại thang đo ra sao?\n"
        f"4. **Đánh giá tổng thể**: Với Alpha hiện tại, thang đo có đủ tin cậy "
        f"để sử dụng trong phân tích tiếp theo không?"
    )


def _build_regression_ai_prompt(result: AnalysisResult) -> str:
    """Build a focused prompt for Linear Regression results."""
    data = result.data or {}
    r_sq = data.get("r_squared", 0)
    adj_r_sq = data.get("adj_r_squared", 0)
    f_stat = data.get("f_statistic", 0)
    f_p = data.get("f_p_value", 1)
    dw = data.get("durbin_watson")
    n = data.get("n", 0)
    coefs = data.get("coefficients", [])

    # Classify predictors
    sig_preds = []
    nonsig_preds = []
    vif_issues = []
    for c in coefs:
        if c.get("variable") == "(Constant)":
            continue
        p = c.get("p_value")
        vif = c.get("vif")
        beta = c.get("beta_standardized", "N/A")
        name = c.get("variable", "")
        if p is not None and p < 0.05:
            sig_preds.append(f"'{name}' (β={beta}, p={p})")
        elif p is not None:
            nonsig_preds.append(f"'{name}' (β={beta}, p={p})")
        if vif is not None and vif >= 5:
            vif_issues.append(f"'{name}' (VIF={vif})")

    model_status = "có ý nghĩa" if f_p < 0.05 else "KHÔNG có ý nghĩa"
    dw_text = f", Durbin-Watson = {dw}" if dw else ""

    return (
        f"## Phân tích Hồi quy tuyến tính\n"
        f"- R² = {r_sq}, Adjusted R² = {adj_r_sq}, N = {n}\n"
        f"- F = {f_stat}, p = {f_p} → Mô hình {model_status}{dw_text}\n"
        f"- Biến CÓ ý nghĩa: {', '.join(sig_preds) if sig_preds else 'Không có'}\n"
        f"- Biến KHÔNG có ý nghĩa: {', '.join(nonsig_preds) if nonsig_preds else 'Không có'}\n"
        f"- Vấn đề VIF (≥5): {', '.join(vif_issues) if vif_issues else 'Không có'}\n\n"
        f"Hãy phân tích chi tiết:\n"
        f"1. **Đánh giá mô hình**: R² ở mức nào? Mô hình giải thích tốt hay yếu? "
        f"So với các nghiên cứu khảo sát xã hội tương tự thì R² này có chấp nhận được không?\n"
        f"2. **Chẩn đoán biến không có ý nghĩa**: Tại sao các biến đó không đạt? "
        f"Có phải do đo lường chưa chính xác, do multicollinearity, hay khái niệm không liên quan?\n"
        f"3. **Vấn đề đa cộng tuyến**: Nếu có VIF cao, giải thích nguyên nhân "
        f"và đề xuất cách xử lý (loại biến, gộp biến, hay dùng PCA).\n"
        f"4. **Đề xuất cải thiện mô hình**: Nên thêm/bớt biến nào? "
        f"Có nên thử mô hình phi tuyến hoặc moderator/mediator không?\n"
        f"5. **Kiểm tra giả định**: Durbin-Watson cho thấy gì về tự tương quan phần dư?"
    )


def _build_correlation_ai_prompt(result: AnalysisResult) -> str:
    """Build a focused prompt for Correlation results."""
    data = result.data or {}
    sig_pairs = data.get("significant_pairs", [])

    # Categorize pairs
    strong = [p for p in sig_pairs if p.get("strength") in ("strong",)]
    moderate = [p for p in sig_pairs if p.get("strength") == "moderate"]
    weak = [p for p in sig_pairs if p.get("strength") == "weak"]
    very_high = [p for p in sig_pairs if abs(p.get("r", 0)) >= 0.85]

    def fmt_pairs(pairs, limit=5):
        return ", ".join(
            [f"'{p['var1']}' × '{p['var2']}' (r={p['r']})" for p in pairs[:limit]]
        )

    strong_text = f"\n- Tương quan MẠNH: {fmt_pairs(strong)}" if strong else ""
    moderate_text = f"\n- Tương quan TRUNG BÌNH: {fmt_pairs(moderate)}" if moderate else ""
    weak_text = f"\n- Tương quan YẾU: {fmt_pairs(weak)}" if weak else ""
    multicol_text = f"\n- ⚠️ Cặp rất cao (r≥0.85, nghi đa cộng tuyến): {fmt_pairs(very_high)}" if very_high else ""

    return (
        f"## Phân tích Tương quan\n"
        f"- Tổng số cặp có ý nghĩa (p<0.05): {len(sig_pairs)}"
        f"{strong_text}{moderate_text}{weak_text}{multicol_text}\n\n"
        f"Hãy phân tích chi tiết:\n"
        f"1. **Giải thích ý nghĩa thực tế**: Các mối tương quan mạnh nhất có ý nghĩa gì "
        f"trong bối cảnh nghiên cứu khảo sát? Mối quan hệ này hợp lý không?\n"
        f"2. **Cảnh báo đa cộng tuyến**: Nếu có cặp r≥0.85, giải thích tại sao "
        f"và hậu quả khi đưa đồng thời vào mô hình hồi quy.\n"
        f"3. **Phân biệt tương quan và nhân quả**: Nhấn mạnh rằng tương quan KHÔNG "
        f"đồng nghĩa nhân quả, và gợi ý cách kiểm chứng thêm.\n"
        f"4. **Đề xuất phân tích tiếp theo**: Dựa trên kết quả tương quan, "
        f"nên chạy regression với biến nào? Có nên dùng mediator/moderator không?"
    )


def _build_comparison_ai_prompt(result: AnalysisResult) -> str:
    """Build a focused prompt for Group Comparison (T-test/ANOVA) results."""
    data = result.data or {}
    test_name = data.get("test_name", "")
    p = data.get("p_value", 1)
    sig = data.get("significant", False)
    effect = data.get("effect_size")
    effect_interp = data.get("effect_interpretation", "")
    effect_label = data.get("effect_size_label", "")
    groups = data.get("group_statistics", [])
    n_groups = data.get("n_groups", 0)

    group_text = "\n".join(
        [f"  - Nhóm '{g['group']}': Mean={g['mean']}, SD={g['std']}, N={g['n']}" for g in groups]
    )

    sig_text = "CÓ ý nghĩa thống kê" if sig else "KHÔNG có ý nghĩa thống kê"
    effect_text = f", {effect_label}={effect} ({effect_interp})" if effect is not None else ""

    # Post-hoc info
    post_hoc = data.get("post_hoc", {})
    ph_text = ""
    if post_hoc:
        ph_results = post_hoc.get("results", [])
        sig_pairs = [r for r in ph_results if r.get("significant")]
        if sig_pairs:
            ph_text = "\n- Post-hoc: Các cặp khác biệt có ý nghĩa: " + ", ".join(
                [f"'{r['group1']}' vs '{r['group2']}' (p={r['p_value']})" for r in sig_pairs[:5]]
            )

    return (
        f"## Phân tích So sánh nhóm ({test_name})\n"
        f"- Kết quả: {sig_text} (p={p}){effect_text}\n"
        f"- Số nhóm: {n_groups}\n"
        f"- Thống kê theo nhóm:\n{group_text}{ph_text}\n\n"
        f"Hãy phân tích chi tiết:\n"
        f"1. **Giải thích sự khác biệt**: {'Nhóm nào cao/thấp hơn và tại sao?' if sig else 'Tại sao không tìm thấy sự khác biệt? Do cỡ mẫu nhỏ, do biến nhóm không phù hợp, hay thực sự không khác biệt?'}\n"
        f"2. **Effect size**: Mức độ ảnh hưởng thực tế ra sao? "
        f"{'Effect size lớn nhưng p≥0.05 có nghĩa gì?' if not sig and effect_interp in ('large', 'medium') else 'Mức effect size này có ý nghĩa thực tiễn không?'}\n"
        f"3. **Nguyên nhân từ thiết kế khảo sát**: Cách phân nhóm có hợp lý không? "
        f"Các nhóm có cỡ mẫu cân bằng không? Có ảnh hưởng của confounding variables không?\n"
        f"4. **Đề xuất cụ thể**: Nên làm gì tiếp theo để có kết luận mạnh hơn?"
    )


def _build_descriptive_ai_prompt(result: AnalysisResult) -> str:
    """Build a focused prompt for Descriptive Statistics results."""
    data = result.data or {}
    table = data.get("descriptive_table", [])

    # Find notable patterns
    high_std = [r for r in table if r.get("Std", 0) > 1.5]
    skewed = [r for r in table if abs(r.get("Skewness", 0)) > 1]
    low_means = [r for r in table if r.get("Scale") and r.get("Mean", 5) < 2.5]
    high_means = [r for r in table if r.get("Scale") and r.get("Mean", 0) >= 4.2]

    summary_lines = [f"- Tổng số biến phân tích: {len(table)}"]
    if high_std:
        names = ", ".join([f"'{r['Column']}' (SD={r['Std']})" for r in high_std[:5]])
        summary_lines.append(f"- Biến có độ lệch chuẩn CAO (>1.5): {names}")
    if skewed:
        names = ", ".join([f"'{r['Column']}' (skew={r.get('Skewness')})" for r in skewed[:5]])
        summary_lines.append(f"- Biến có phân phối LỆCH (|skewness|>1): {names}")
    if low_means:
        names = ", ".join([f"'{r['Column']}' (M={r['Mean']})" for r in low_means[:5]])
        summary_lines.append(f"- Biến có Mean THẤP (<2.5 trên thang Likert): {names}")
    if high_means:
        names = ", ".join([f"'{r['Column']}' (M={r['Mean']})" for r in high_means[:5]])
        summary_lines.append(f"- Biến có Mean RẤT CAO (≥4.2): {names}")

    return (
        f"## Phân tích Thống kê mô tả\n"
        + "\n".join(summary_lines)
        + "\n\nHãy phân tích chi tiết:\n"
        f"1. **Nhận xét về phân bố dữ liệu**: Các biến có phân bố chuẩn không? "
        f"Những biến nào bị lệch và điều này ảnh hưởng gì đến phân tích tiếp theo?\n"
        f"2. **Giải thích xu hướng trả lời**: Tại sao một số biến có Mean rất cao/thấp? "
        f"Có phải do social desirability bias, câu hỏi dẫn dắt, hay phản ánh thực tế?\n"
        f"3. **Độ phân tán cao**: Các biến có SD lớn cho thấy điều gì về sự đồng thuận "
        f"của người trả lời? Có cần phân nhóm để phân tích sâu hơn không?\n"
        f"4. **Đề xuất**: Cần làm gì trước khi chạy phân tích nâng cao "
        f"(reliability, regression, v.v.)?"
    )


def explain_all(survey_data: SurveyData, lang: str = "vi") -> list:
    """
    Explain all analysis results in a SurveyData object.

    Args:
        survey_data: SurveyData with completed analyses
        lang: Language code

    Returns:
        List of dicts with title and explanation for each result
    """
    explanations = []
    for result in survey_data.analysis_results:
        explanations.append({
            "type": result.analysis_type.value,
            "title": result.title,
            "explanation": explain_result(result, lang),
        })
    return explanations


# ──────────────────────────────────────────────────────────────────
# EXPLAINERS
# ──────────────────────────────────────────────────────────────────

def _explain_descriptive(result: AnalysisResult, lang: str) -> str:
    """Explain descriptive statistics results."""
    table = result.data.get("descriptive_table", [])
    if not table:
        return "Không có dữ liệu thống kê mô tả để giải thích."

    lines = []
    lines.append("📊 **Thống kê mô tả:**\n")

    for row in table:
        col = row["Column"]
        mean = row["Mean"]
        std = row["Std"]
        n = row["N"]
        scale = row.get("Scale", "")

        # Interpret mean on Likert scale
        if scale:
            max_point = int(scale.split("-")[1])
            level = _interpret_mean_level(mean, max_point)
            lines.append(
                f"- **{col}**: Giá trị trung bình = {mean} (SD = {std}), "
                f"trên thang {scale} điểm → Mức đánh giá **{level}** (N = {n})."
            )
        else:
            lines.append(
                f"- **{col}**: Trung bình = {mean}, Độ lệch chuẩn = {std} (N = {n})."
            )

        # Skewness interpretation
        skew = row.get("Skewness", 0)
        if abs(skew) > 1:
            direction = "lệch phải (xu hướng trả lời thấp)" if skew > 0 else "lệch trái (xu hướng trả lời cao)"
            lines.append(f"  ⚠️ Phân phối {direction} (skewness = {skew}).")

    return "\n".join(lines)


def _explain_frequency(result: AnalysisResult, lang: str) -> str:
    """Explain frequency table results."""
    table = result.data.get("frequency_table", [])
    if not table:
        return "Không có bảng tần suất để giải thích."

    lines = [f"📋 **{result.title}:**\n"]

    # Find the most common value
    valid_rows = [r for r in table if r["Value"] != "(Missing)"]
    if valid_rows:
        top = max(valid_rows, key=lambda r: r["Count"])
        lines.append(
            f"- Giá trị phổ biến nhất: **{top['Value']}** ({top['Count']} lượt, {top['Percent']}%)."
        )
        lines.append(f"- Tổng cộng có {len(valid_rows)} giá trị khác nhau.")

    missing_rows = [r for r in table if r["Value"] == "(Missing)"]
    if missing_rows:
        m = missing_rows[0]
        lines.append(f"- Số lượng thiếu (missing): {m['Count']} ({m['Percent']}%).")

    return "\n".join(lines)


def _explain_reliability(result: AnalysisResult, lang: str) -> str:
    """Explain Cronbach's Alpha results."""
    alpha = result.data.get("alpha")
    if alpha is None:
        return "Không thể tính Cronbach's Alpha — không đủ dữ liệu."

    n_items = result.data.get("n_items", 0)
    n_valid = result.data.get("n_valid", 0)
    interp = result.data.get("interpretation", "")

    interp_vi = {
        "Excellent": "Xuất sắc",
        "Good": "Tốt",
        "Acceptable": "Chấp nhận được",
        "Questionable": "Đáng ngờ",
        "Poor": "Kém",
        "Unacceptable": "Không chấp nhận được",
    }

    lines = ["🔒 **Phân tích độ tin cậy (Cronbach's Alpha):**\n"]
    lines.append(
        f"- Cronbach's Alpha = **{alpha}** → Mức **{interp_vi.get(interp, interp)}**."
    )
    lines.append(f"- Số items: {n_items}, Số cases hợp lệ: {n_valid}.")

    if alpha >= 0.7:
        lines.append("- ✅ Thang đo đạt độ tin cậy đủ để sử dụng trong phân tích.")
    else:
        lines.append("- ⚠️ Thang đo chưa đạt ngưỡng tin cậy 0.70. Cần xem xét cải thiện.")

    # Item analysis
    items = result.data.get("item_statistics", [])
    weak_items = [i for i in items if i.get("corrected_item_total_corr", 1) < 0.3]
    if weak_items:
        names = ", ".join([i["item"] for i in weak_items])
        lines.append(
            f"\n- ⚠️ Items có tương quan thấp (<0.30): **{names}**. "
            "Cân nhắc loại bỏ để cải thiện Alpha."
        )

    # Best item to remove
    improve_items = [
        i for i in items
        if i.get("alpha_if_deleted") and i["alpha_if_deleted"] > alpha
    ]
    if improve_items:
        best = max(improve_items, key=lambda x: x["alpha_if_deleted"])
        lines.append(
            f"- 💡 Nếu bỏ item '{best['item']}', Alpha sẽ tăng lên {best['alpha_if_deleted']}."
        )

    return "\n".join(lines)


def _explain_correlation(result: AnalysisResult, lang: str) -> str:
    """Explain correlation results."""
    sig_pairs = result.data.get("significant_pairs", [])

    lines = ["🔗 **Phân tích tương quan:**\n"]

    if not sig_pairs:
        lines.append("- Không phát hiện cặp biến nào có tương quan có ý nghĩa thống kê (p < 0.05).")
        return "\n".join(lines)

    lines.append(f"- Tìm thấy **{len(sig_pairs)} cặp biến** có tương quan có ý nghĩa.\n")

    strength_vi = {
        "strong": "mạnh",
        "moderate": "trung bình",
        "weak": "yếu",
        "negligible": "không đáng kể",
    }

    # Show top 5 significant pairs
    for pair in sig_pairs[:5]:
        r = pair["r"]
        direction = "thuận" if r > 0 else "nghịch"
        strength = strength_vi.get(pair.get("strength", ""), pair.get("strength", ""))
        lines.append(
            f"- **{pair['var1']}** × **{pair['var2']}**: "
            f"r = {r} (tương quan {direction}, mức {strength}), p = {pair['p']}."
        )

    if len(sig_pairs) > 5:
        lines.append(f"\n- ...và {len(sig_pairs) - 5} cặp nữa.")

    return "\n".join(lines)


def _explain_comparison(result: AnalysisResult, lang: str) -> str:
    """Explain group comparison results."""
    data = result.data
    if not data:
        return "Không có kết quả so sánh nhóm."

    test_name = data.get("test_name", "Unknown")
    stat = data.get("statistic")
    p = data.get("p_value")
    sig = data.get("significant", False)
    effect = data.get("effect_size")
    effect_label = data.get("effect_size_label", "")
    effect_interp = data.get("effect_interpretation", "")
    groups = data.get("group_statistics", [])

    effect_vi = {
        "large": "lớn",
        "medium": "trung bình",
        "small": "nhỏ",
        "negligible": "không đáng kể",
    }

    lines = [f"⚖️ **So sánh nhóm ({test_name}):**\n"]

    # Group descriptives
    if groups:
        for g in groups:
            lines.append(f"- Nhóm **{g['group']}**: M = {g['mean']}, SD = {g['std']}, N = {g['n']}.")

    lines.append("")

    if sig:
        lines.append(
            f"- ✅ **Có sự khác biệt có ý nghĩa thống kê** giữa các nhóm "
            f"({test_name}: statistic = {stat}, p = {p})."
        )
        if effect is not None:
            lines.append(
                f"- Mức ảnh hưởng: {effect_label} = {effect} "
                f"(mức **{effect_vi.get(effect_interp, effect_interp)}**)."
            )

        # Identify which group is higher
        if len(groups) == 2:
            g1, g2 = groups[0], groups[1]
            higher = g1 if g1["mean"] > g2["mean"] else g2
            lower = g2 if g1["mean"] > g2["mean"] else g1
            diff = round(abs(g1["mean"] - g2["mean"]), 4)
            lines.append(
                f"- 💡 Nhóm **{higher['group']}** có điểm cao hơn nhóm **{lower['group']}** "
                f"(chênh lệch = {diff})."
            )
    else:
        lines.append(
            f"- ❌ **Không có sự khác biệt có ý nghĩa thống kê** giữa các nhóm "
            f"(p = {p} ≥ 0.05)."
        )
        lines.append("- Các nhóm có mức đánh giá tương tự nhau.")

    return "\n".join(lines)


def _explain_regression(result: AnalysisResult, lang: str) -> str:
    """Explain regression results."""
    data = result.data
    if not data:
        return "Không có kết quả hồi quy."

    r_sq = data.get("r_squared", 0)
    adj_r_sq = data.get("adj_r_squared", 0)
    f_stat = data.get("f_statistic")
    f_p = data.get("f_p_value")
    n = data.get("n", 0)
    coefs = data.get("coefficients", [])

    lines = ["📈 **Phân tích hồi quy tuyến tính:**\n"]

    # Model fit
    lines.append(f"- R² = **{r_sq}** (mô hình giải thích **{r_sq*100:.1f}%** phương sai).")
    lines.append(f"- Adjusted R² = {adj_r_sq}, N = {n}.")

    if f_p is not None:
        if f_p < 0.05:
            lines.append(
                f"- ✅ Mô hình có ý nghĩa thống kê (F = {f_stat}, p = {f_p})."
            )
        else:
            lines.append(
                f"- ❌ Mô hình không có ý nghĩa thống kê (F = {f_stat}, p = {f_p})."
            )

    # Coefficients
    predictors = [c for c in coefs if c["variable"] != "(Constant)"]
    if predictors:
        lines.append("\n**Hệ số hồi quy:**\n")

        # Sort by absolute beta_standardized
        sorted_preds = sorted(
            predictors,
            key=lambda c: abs(c.get("beta_standardized", 0) or 0),
            reverse=True,
        )

        for c in sorted_preds:
            sig_marker = "✅" if c.get("significant") else "❌"
            beta_std = c.get("beta_standardized")
            beta_text = f", β = {beta_std}" if beta_std is not None else ""

            direction = ""
            if c["B"] > 0:
                direction = "ảnh hưởng thuận (tăng)"
            elif c["B"] < 0:
                direction = "ảnh hưởng nghịch (giảm)"

            lines.append(
                f"- {sig_marker} **{c['variable']}**: B = {c['B']}{beta_text}, "
                f"p = {c.get('p_value', 'N/A')} → {direction}."
            )

    # Interpretation
    lines.append("")
    if r_sq >= 0.5:
        lines.append("💡 Mô hình giải thích tốt biến phụ thuộc (R² ≥ 50%).")
    elif r_sq >= 0.25:
        lines.append("💡 Mô hình giải thích ở mức trung bình.")
    elif r_sq >= 0.1:
        lines.append("⚠️ Mô hình giải thích yếu. Có thể cần thêm biến dự báo.")
    else:
        lines.append("⚠️ Mô hình giải thích rất yếu (R² < 10%). Nên xem xét lại biến độc lập.")

    return "\n".join(lines)


def _explain_quality_report(result: AnalysisResult, lang: str) -> str:
    """Explain data quality report."""
    data = result.data
    if not data:
        return "Không có báo cáo chất lượng dữ liệu."

    overview = data.get("overview", {})
    score = data.get("dataset_score", 0)
    grade = data.get("dataset_grade", "N/A")
    straight = data.get("straight_lining", {})
    missing_patterns = data.get("missing_patterns", {})

    grade_vi = {
        "Excellent": "Xuất sắc",
        "Good": "Tốt",
        "Acceptable": "Chấp nhận được",
        "Fair": "Trung bình",
        "Poor": "Kém",
        "Critical": "Nghiêm trọng",
    }

    lines = ["🏥 **Báo cáo chất lượng dữ liệu:**\n"]
    lines.append(
        f"- Điểm chất lượng tổng: **{score}/100** ({grade_vi.get(grade, grade)})."
    )
    lines.append(
        f"- Tổng số respondents: {overview.get('n_respondents', 'N/A')}, "
        f"Số cột: {overview.get('n_columns', 'N/A')}."
    )
    lines.append(
        f"- Tỉ lệ missing tổng thể: {overview.get('overall_missing_pct', 0)}%."
    )

    complete_pct = missing_patterns.get("complete_pct", 0)
    lines.append(
        f"- {complete_pct}% respondents trả lời đầy đủ tất cả câu hỏi."
    )

    # Straight-lining
    sl_count = straight.get("count", 0)
    if sl_count > 0:
        lines.append(
            f"\n⚠️ Phát hiện **{sl_count} respondent(s)** trả lời giống nhau trên tất cả "
            f"items Likert (straight-lining). Cân nhắc loại bỏ."
        )

    # Column quality issues
    col_scores = data.get("column_scores", [])
    bad_cols = [c for c in col_scores if c["quality_score"] < 60]
    if bad_cols:
        lines.append(f"\n⚠️ {len(bad_cols)} cột có chất lượng thấp (< 60/100):")
        for c in bad_cols[:5]:
            issues_text = "; ".join(c.get("issues", []))
            lines.append(f"  - '{c['column']}': {c['quality_score']}/100 — {issues_text}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _interpret_mean_level(mean: float, max_point: int) -> str:
    """Interpret a mean score on a Likert scale."""
    ratio = mean / max_point

    if max_point == 5:
        if mean >= 4.2:
            return "rất cao"
        elif mean >= 3.4:
            return "cao"
        elif mean >= 2.6:
            return "trung bình"
        elif mean >= 1.8:
            return "thấp"
        else:
            return "rất thấp"
    elif max_point == 7:
        if mean >= 5.8:
            return "rất cao"
        elif mean >= 4.6:
            return "cao"
        elif mean >= 3.4:
            return "trung bình"
        elif mean >= 2.2:
            return "thấp"
        else:
            return "rất thấp"
    else:
        # Generic interpretation based on ratio
        if ratio >= 0.84:
            return "rất cao"
        elif ratio >= 0.68:
            return "cao"
        elif ratio >= 0.52:
            return "trung bình"
        elif ratio >= 0.36:
            return "thấp"
        else:
            return "rất thấp"
