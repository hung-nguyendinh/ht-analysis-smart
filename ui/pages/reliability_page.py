"""
Reliability Page — Cronbach's Alpha, Item-Total Correlation.
Full statistics with user-friendly explanations and guidance.
"""
import pandas as pd
import streamlit as st

from services.reliability import compute_cronbach_alpha
from services.scale_scores import create_scale_score
from ui.analysis_helpers import get_numeric_column_names, render_column_picker
from ui.export_helpers import render_result_downloads
from ui.styles import metric_card, section_header


_ALPHA_COLOR = {
    "Excellent": "teal",
    "Good": "green",
    "Acceptable": "blue",
    "Questionable": "orange",
    "Poor": "orange",
    "Unacceptable": "red",
}


def render_reliability_page():
    """Render the Reliability Analysis page."""
    st.markdown("## 🔬 Phân Tích Độ Tin Cậy — Cronbach's Alpha")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)

    if len(all_cols) < 2:
        st.warning("⚠️ Cần ít nhất 2 cột để tính Cronbach's Alpha.")
        return

    # ═══════════════════════════════════════════════════════════════
    # STEP 1 — Chọn items
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 1 — Chọn các Items phân tích"), unsafe_allow_html=True)

    default_cols = numeric_cols if len(numeric_cols) >= 2 else all_cols[:min(5, len(all_cols))]

    selected_cols = render_column_picker(
        df,
        key="rel_cols",
        label="Chọn các items thuộc cùng một thang đo",
        all_columns=all_cols,
        default_columns=default_cols,
        recommended_columns=numeric_cols,
        columns_info=survey_data.columns_info,
        min_columns=2,
        help_text="Chỉ nên chọn các items cùng đo lường một khái niệm, ví dụ các câu hỏi về 'Sự hài lòng'.",
    )

    if len(selected_cols) < 2:
        st.info("⬆️ Chọn ít nhất **2 cột** để bắt đầu phân tích.")
        return

    # Filter/convert to numeric
    valid_cols = []
    skipped = []
    for c in selected_cols:
        if c in numeric_cols:
            valid_cols.append(c)
        else:
            coerced = pd.to_numeric(df[c], errors="coerce")
            if coerced.notna().sum() > 0:
                valid_cols.append(c)
            else:
                skipped.append(c)

    if skipped:
        st.warning(f"⚠️ Bỏ qua cột không chuyển được sang số: {', '.join(skipped)}")

    if len(valid_cols) < 2:
        st.error("❌ Cần ít nhất 2 cột số. Vui lòng chọn thêm.")
        return

    # --- Explanations Expander ---
    with st.expander("❓ Giải thích về Cronbach's Alpha", expanded=False):
        st.markdown("""
**Cronbach's Alpha là gì?**
- Là hệ số dùng để kiểm tra xem các câu hỏi (items) có cùng đo lường một khái niệm hay không.
- Ví dụ: 5 câu hỏi cùng hỏi về 'Dịch vụ khách hàng' thì người dùng trả lời nên có sự thống nhất giữa các câu đó.

**Các chỉ số quan trọng:**
1. **Cronbach's Alpha tổng**: Độ tin cậy chung của thang đo. Nên ≥ 0.70.
2. **Corrected Item-Total Correlation**: Độ tương quan của từng câu với tổng thể. Nên ≥ 0.30. Nếu nhỏ hơn, câu hỏi đó có thể bị 'lạc đề'.
3. **Cronbach's Alpha if Item Deleted**: Nếu xóa câu này đi, Alpha tổng sẽ là bao nhiêu? Nếu Alpha này cao hơn Alpha tổng hiện tại, việc xóa câu này sẽ làm thang đo tốt hơn.
        """)

    _ensure_numeric(survey_data, valid_cols)

    if st.button("🔍 Chạy phân tích", type="primary", use_container_width=True, key="rel_run"):
        with st.spinner("Đang tính toán..."):
            result = compute_cronbach_alpha(survey_data, columns=valid_cols)
        st.session_state["rel_result"] = result

    result = st.session_state.get("rel_result")
    if result is None:
        return

    st.markdown("---")

    if result.warnings:
        for w in result.warnings:
            st.warning(w)

    if not result.data:
        st.error(result.summary_text)
        return

    # ═══════════════════════════════════════════════════════════════
    # RESULTS — Key Metrics
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("📋 Kết Quả Độ Tin Cậy"), unsafe_allow_html=True)

    alpha = result.data.get("alpha", 0)
    interp = result.data.get("interpretation", "N/A")
    n_items = result.data.get("n_items", 0)
    n_valid = result.data.get("n_valid", 0)
    color = _ALPHA_COLOR.get(interp, "blue")

    # Verdict Box
    if alpha >= 0.7:
        st.success(f"✅ Thang đo đạt độ tin cậy tốt (**Alpha = {alpha:.4f}**, Đánh giá: **{interp}**).")
    elif alpha >= 0.6:
        st.warning(f"⚠️ Thang đo có độ tin cậy tạm chấp nhận được (**Alpha = {alpha:.4f}**, Đánh giá: **{interp}**).")
    else:
        st.error(f"❌ Thang đo KHÔNG đạt độ tin cậy (**Alpha = {alpha:.4f}**, Đánh giá: **{interp}**). Cần xem xét loại bỏ item.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(f"{alpha:.4f}", "Cronbach's Alpha", color), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(interp, "Mức độ tin cậy", color), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(str(n_items), "Số Items", "blue"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card(f"{n_valid:,}", "Mẫu hợp lệ (N)", "teal"), unsafe_allow_html=True)

    with st.expander("ℹ️ Thang đánh giá chuẩn (Nunnally & Bernstein, 1994)"):
        st.markdown("""
| Hệ số Alpha | Đánh giá | Ý nghĩa |
| :--- | :--- | :--- |
| **0.9 – 1.0** | **Excellent** | Rất tốt, thang đo rất chặt chẽ. |
| **0.8 – 0.9** | **Good** | Tốt, thang đo đảm bảo chất lượng. |
| **0.7 – 0.8** | **Acceptable** | Chấp nhận được (thường dùng trong nghiên cứu xã hội). |
| **0.6 – 0.7** | **Questionable** | Có thể dùng được nếu là nghiên cứu mới hoặc sơ bộ. |
| **0.5 – 0.6** | **Poor** | Kém, cần chỉnh sửa lại câu hỏi. |
| **< 0.5** | **Unacceptable** | Không thể sử dụng thang đo này. |
        """)

    # ═══════════════════════════════════════════════════════════════
    # ITEM STATISTICS
    # ═══════════════════════════════════════════════════════════════
    item_stats = result.data.get("item_statistics", [])
    if item_stats:
        st.markdown(section_header("📊 Phân Tích Từng Biến (Item Statistics)"), unsafe_allow_html=True)
        
        st.info("💡 **Gợi ý:** Để thang đo tốt nhất, các câu hỏi nên có 'Corrected Item-Total correlation' > 0.3.")

        item_df = pd.DataFrame(item_stats)
        item_df.columns = [
            "Biến (Item)", "Trung bình", "Độ lệch chuẩn",
            "Tương quan biến-tổng", "Alpha nếu loại bỏ",
            "Scale Mean nếu loại bỏ", "Scale Variance nếu loại bỏ",
        ]

        def highlight_low(row):
            styles = [""] * len(row)
            # Highlight low correlation
            if row["Tương quan biến-tổng"] < 0.3:
                styles[3] = "background-color: #ffcccc"
            # Highlight alpha-if-deleted if it improves overall alpha
            if row["Alpha nếu loại bỏ"] > alpha:
                styles[4] = "background-color: #d4edda; font-weight: bold"
            return styles

        st.dataframe(
            item_df.style.apply(highlight_low, axis=1).format({
                "Trung bình": "{:.3f}",
                "Độ lệch chuẩn": "{:.3f}",
                "Tương quan biến-tổng": "{:.4f}",
                "Alpha nếu loại bỏ": "{:.4f}",
                "Scale Mean nếu loại bỏ": "{:.4f}",
                "Scale Variance nếu loại bỏ": "{:.4f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        
        st.caption("🔴 Ô màu đỏ: Tương quan thấp (< 0.3). 🟢 Ô màu xanh: Alpha tăng lên nếu xóa câu này.")

        # Summary findings
        low_items = item_df[item_df["Tương quan biến-tổng"] < 0.3]["Biến (Item)"].tolist()
        improving_items = item_df[item_df["Alpha nếu loại bỏ"] > alpha]["Biến (Item)"].tolist()

        if low_items or improving_items:
            with st.expander("💡 Kết luận & Gợi ý xử lý", expanded=True):
                if low_items:
                    st.warning(f"**Item có tương quan thấp:** {', '.join(low_items)}. Những câu này có thể không ăn nhập với các câu còn lại. Nên xem xét loại bỏ.")
                if improving_items:
                    st.success(f"**Cơ hội cải thiện:** Loại bỏ các câu: {', '.join(improving_items)} sẽ giúp nâng chỉ số Alpha tổng lên cao hơn hiện tại.")
                if not low_items and not improving_items and alpha >= 0.7:
                    st.markdown("✨ **Thang đo của bạn rất tốt.** Không cần loại bỏ item nào.")

        st.info(
            "Workflow tip: after Cronbach's Alpha, create a mean score column "
            "for the accepted scale, then use that composite variable in Pearson and regression."
        )
        _render_scale_score_creator(
            survey_data,
            result.parameters.get("columns", valid_cols),
            key_prefix="rel_scale",
        )
        render_result_downloads(result, "reliability_report", "rel_export")

        st.markdown("---")
        if st.button("🤖 Phân tích chuyên sâu bằng AI", key="ai_rel_btn"):
            with st.spinner("AI đang giải thích và chẩn đoán nguyên nhân..."):
                from services.analysis_manager import AnalysisManager
                am = AnalysisManager(st.session_state["survey_data"])
                ai_explanation = am.explain_single_with_ai(result)
                st.info(f"**AI Insight:**\n\n{ai_explanation}")


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df."""
    for col in columns:
        if not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")


def _render_scale_score_creator(survey_data, item_cols, key_prefix: str):
    """Render controls to create a composite score column from selected items."""
    item_cols = [col for col in item_cols if col in survey_data.df.columns]
    if len(item_cols) < 2:
        return

    default_name = f"Score_{item_cols[0].split('_')[0]}"
    with st.expander("Create composite scale score", expanded=False):
        st.caption(
            "Use this after accepting the Cronbach/EFA items. "
            "The new numeric column appears in Correlation and Regression."
        )
        score_name = st.text_input(
            "New score column name",
            value=default_name,
            key=f"{key_prefix}_name",
        )
        min_valid = st.number_input(
            "Minimum valid items required",
            min_value=1,
            max_value=len(item_cols),
            value=len(item_cols),
            key=f"{key_prefix}_min_valid",
        )
        overwrite = st.checkbox(
            "Overwrite if the column already exists",
            value=False,
            key=f"{key_prefix}_overwrite",
        )
        if st.button("Create mean score column", key=f"{key_prefix}_create"):
            try:
                summary = create_scale_score(
                    survey_data,
                    new_col_name=score_name,
                    item_cols=item_cols,
                    method="mean",
                    min_valid_items=int(min_valid),
                    overwrite=overwrite,
                )
                st.success(
                    f"Created '{summary['column']}' from {summary['n_items']} items "
                    f"({summary['valid_n']} valid cases)."
                )
            except ValueError as exc:
                st.error(str(exc))
