"""
Descriptive Statistics Page — Mean, Std, Freq table.
Includes user-friendly explanations and help text.
"""
import streamlit as st
import pandas as pd

from ui.styles import metric_card, section_header
from ui.analysis_helpers import get_numeric_column_names, render_column_picker
from ui.export_helpers import render_result_downloads
from services.descriptive_stats import compute_descriptive, compute_frequency_table


def render_descriptive_page():
    """Render the Descriptive Statistics page."""
    st.markdown("## 📈 Thống Kê Mô Tả")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)

    if not all_cols:
        st.warning("⚠️ Không có cột nào trong dữ liệu.")
        return

    # ── Tabs ──────────────────────────────────────────────
    tab_desc, tab_freq = st.tabs(["📊 Thống kê mô tả", "📋 Bảng tần số"])

    with tab_desc:
        _render_descriptive_tab(survey_data, df, all_cols, numeric_cols)

    with tab_freq:
        _render_frequency_tab(survey_data, all_cols)


def _render_descriptive_tab(survey_data, df, all_cols, numeric_cols):
    """Render descriptive statistics table."""
    st.markdown(section_header("Chuẩn bị phân tích"), unsafe_allow_html=True)

    default_cols = numeric_cols if numeric_cols else all_cols[:min(5, len(all_cols))]

    selected_cols = render_column_picker(
        df,
        key="desc_cols",
        label="Chọn các cột để phân tích",
        all_columns=all_cols,
        default_columns=default_cols,
        recommended_columns=numeric_cols,
        columns_info=survey_data.columns_info,
        min_columns=1,
        help_text="Nên chọn cột số/Likert. Bảng bên dưới cho phép tìm kiếm, lọc nhanh và xem ví dụ dữ liệu trước khi chọn.",
    )

    if not selected_cols:
        st.info("⬆️ Chọn ít nhất **1 cột** để bắt đầu phân tích.")
        return

    # --- Explanations Expander ---
    with st.expander("❓ Giải thích các chỉ số (Click để xem)", expanded=False):
        st.markdown("""
| Chỉ số | Ý nghĩa dễ hiểu |
| :--- | :--- |
| **N** | Số lượng người trả lời hợp lệ cho mục này (không tính các ô trống). |
| **Mean (Trung bình)** | Giá trị trung bình cộng. Cho biết mức độ đánh giá 'đại diện' của cả nhóm. |
| **Median (Trung vị)** | Giá trị nằm ở chính giữa khi sắp xếp dữ liệu. Giúp thấy điểm thực tế nếu có nhiều trả lời cực đoan. |
| **Std (Độ lệch chuẩn)** | Đo sự biến thiên. **Std nhỏ** = câu trả lời đồng thuận; **Std lớn** = câu trả lời phân tán, khác biệt nhau nhiều. |
| **Min / Max** | Điểm thấp nhất và cao nhất mà người dùng đã chọn. |
| **Skewness (Độ nghiêng)** | Cho biết dữ liệu lệch về phía nào. **< 0**: Nhiều người chọn mức cao; **> 0**: Nhiều người chọn mức thấp. |
| **Kurtosis (Độ nhọn)** | Đo mức độ tập trung đỉnh. Trị số càng lớn dữ liệu càng tập trung quanh trung bình. |
        """)

    # Ensure columns are numeric — try to convert
    valid_cols = []
    skipped_cols = []
    for c in selected_cols:
        if c in numeric_cols:
            valid_cols.append(c)
        else:
            # Try coercion
            coerced = pd.to_numeric(df[c], errors="coerce")
            if coerced.notna().sum() > 0:
                valid_cols.append(c)
            else:
                skipped_cols.append(c)

    if skipped_cols:
        st.warning(f"⚠️ Bỏ qua cột không chuyển được sang số: {', '.join(skipped_cols)}")

    if not valid_cols:
        st.error("❌ Không có cột số nào hợp lệ. Vui lòng chọn lại.")
        return

    # Convert selected columns to numeric in a temp df for analysis
    _ensure_numeric(survey_data, valid_cols)

    if st.button("🔍 Chạy phân tích", type="primary", use_container_width=True, key="desc_run"):
        with st.spinner("Đang tính toán..."):
            result = compute_descriptive(survey_data, columns=valid_cols)
        st.session_state["desc_result"] = result

    result = st.session_state.get("desc_result")
    if result is None:
        return

    # Summary
    st.markdown(section_header("Kết quả"), unsafe_allow_html=True)
    st.success(result.summary_text)

    table_records = result.data.get("descriptive_table", [])
    if not table_records:
        st.warning("No valid descriptive table to display.")
        return

    if table_records:
        df_result = pd.DataFrame(table_records)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card(str(len(df_result)), "Số biến", "blue"), unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card(f"{df_result['N'].max():,}", "Max N (Cỡ mẫu)", "teal"), unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card(f"{df_result['Mean'].mean():.3f}", "Grand Mean (TB Tổng)", "green"), unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card(f"{df_result['Std'].mean():.3f}", "Avg Std (Biến thiên TB)", "orange"), unsafe_allow_html=True)

    st.markdown(section_header("Bảng thống kê chi tiết"), unsafe_allow_html=True)
    st.dataframe(df_result, use_container_width=True, hide_index=True)
    render_result_downloads(result, "descriptive_report", "desc_export")

    if result.warnings:
        for w in result.warnings:
            st.warning(w)

    # Skewness hint
    if "Skewness" in df_result.columns:
        skewed = df_result[df_result["Skewness"].abs() > 1]["Column"].tolist()
        if skewed:
            with st.expander(f"💡 Lưu ý về độ lệch ({len(skewed)} cột)", expanded=True):
                st.info("Các cột sau có độ lệch cao (|Skewness| > 1). Điều này có nghĩa là câu trả lời tập trung nhiều về một phía (quá cao hoặc quá thấp).")
                for c in skewed:
                    val = df_result[df_result["Column"] == c]["Skewness"].values[0]
                    direction = "phải (đa số chọn mức thấp)" if val > 0 else "trái (đa số chọn mức cao)"
                    st.write(f"• **{c}**: Lệch {direction} (Skew = {val})")

    st.markdown("---")
    if st.button("🤖 Phân tích chuyên sâu bằng AI", key="ai_desc_btn"):
        with st.spinner("AI đang giải thích và chẩn đoán nguyên nhân..."):
            from services.analysis_manager import AnalysisManager
            am = AnalysisManager(st.session_state["survey_data"])
            ai_explanation = am.explain_single_with_ai(result)
            st.info(f"**AI Insight:**\n\n{ai_explanation}")


def _render_frequency_tab(survey_data, all_cols):
    """Render frequency table for a single column."""
    st.markdown(section_header("Bảng tần số cho một cột"), unsafe_allow_html=True)

    col = st.selectbox(
        "Chọn cột để xem tần suất:",
        all_cols,
        key="freq_col",
        help="Thường dùng cho các biến định danh (vd: Giới tính, Tỉnh thành) để xem số lượng và tỷ lệ %."
    )

    if st.button("📋 Tạo bảng tần số", type="primary", use_container_width=True, key="freq_run"):
        with st.spinner("Đang tính..."):
            result = compute_frequency_table(survey_data, column=col)

        st.success(result.summary_text)

        freq_records = result.data.get("frequency_table", [])
        if freq_records:
            st.markdown("**Chi tiết phân bổ:**")
            st.dataframe(pd.DataFrame(freq_records), use_container_width=True, hide_index=True)
            render_result_downloads(result, f"frequency_{col}", "freq_export")


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df (in-place coercion)."""
    for col in columns:
        if not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")
