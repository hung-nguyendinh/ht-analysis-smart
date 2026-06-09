"""
Correlation Page — Pearson / Spearman correlation matrix.
Full statistics with user-friendly explanations and guidance.
"""
import pandas as pd
import streamlit as st

from services.correlation import compute_correlation_matrix
from ui.analysis_helpers import get_numeric_column_names, render_column_picker
from ui.export_helpers import render_result_downloads
from ui.styles import metric_card, section_header


def render_correlation_page():
    """Render the Correlation Analysis page."""
    st.markdown("## 🔗 Phân Tích Tương Quan")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)

    if len(all_cols) < 2:
        st.warning("⚠️ Cần ít nhất 2 cột để tính tương quan.")
        return

    # ═══════════════════════════════════════════════════════════════
    # STEP 1 — Cài đặt
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 1 — Chọn biến & Phương pháp"), unsafe_allow_html=True)

    default_cols = numeric_cols[:min(8, len(numeric_cols))] if numeric_cols else all_cols[:min(5, len(all_cols))]

    method = st.selectbox(
        "Phương pháp:",
        options=["pearson", "spearman"],
        key="corr_method",
        help="Pearson: Cho dữ liệu chuẩn/khoảng. Spearman: Cho dữ liệu thứ bậc (Likert) hoặc không chuẩn.",
    )
    selected_cols = render_column_picker(
        df,
        key="corr_cols",
        label="Chọn các cột để xem mối tương quan",
        all_columns=all_cols,
        default_columns=default_cols,
        recommended_columns=numeric_cols,
        columns_info=survey_data.columns_info,
        min_columns=2,
        help_text="Chọn ít nhất 2 cột số/Likert. Với mô hình luận văn, nên ưu tiên biến tổng hợp sau Cronbach/EFA.",
    )

    if len(selected_cols) < 2:
        st.info("⬆️ Chọn ít nhất **2 cột**.")
        return

    st.info(
        "Workflow tip: for thesis models, prefer composite scale/factor score columns "
        "created after Cronbach/EFA instead of correlating every raw questionnaire item."
    )

    # --- Explanations Expander ---
    with st.expander("❓ Giải thích về Phân tích tương quan", expanded=False):
        st.markdown(f"""
**Tương quan là gì?**
- Đo lường mức độ 'đi cùng nhau' giữa 2 biến.
- Nếu Biến A tăng, Biến B cũng tăng → **Tương quan thuận (+)**.
- Nếu Biến A tăng, Biến B lại giảm → **Tương quan nghịch (-)**.

**Hệ số r (Correlation Coefficient):**
- Giá trị từ **-1** đến **1**.
- **|r| > 0.7**: Tương quan rất mạnh.
- **0.5 < |r| < 0.7**: Tương quan mạnh.
- **0.3 < |r| < 0.5**: Tương quan vừa.
- **|r| < 0.3**: Tương quan yếu / không đáng kể.

**p-value:**
- Cần **p < 0.05** để chứng minh mối tương quan đó là có ý nghĩa (không phải do ngẫu nhiên).
        """)

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

    _ensure_numeric(survey_data, valid_cols)

    if st.button("🔍 Tính tương quan", type="primary", use_container_width=True, key="corr_run"):
        with st.spinner("Đang tính ma trận tương quan..."):
            result = compute_correlation_matrix(survey_data, columns=valid_cols, method=method)
        st.session_state["corr_result"] = result

    result = st.session_state.get("corr_result")
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
    # RESULTS
    # ═══════════════════════════════════════════════════════════════
    data = result.data
    sig_pairs = data.get("significant_pairs", [])

    st.markdown(section_header("📋 Kết Quả Phân Tích"), unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card(str(len(valid_cols)), "Biến phân tích", "blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(str(len(sig_pairs)), "Cặp có ý nghĩa (p < 0.05)", "green"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(method.capitalize(), "Phương pháp dùng", "teal"), unsafe_allow_html=True)

    # ── Correlation Matrix ──
    st.markdown(section_header("📸 Ma Trận Tương Quan (Heatmap)"), unsafe_allow_html=True)
    
    corr_dict = data.get("correlation_matrix", {})
    p_dict = data.get("p_value_matrix", {})

    if corr_dict:
        corr_df = pd.DataFrame(corr_dict)
        styled = corr_df.style.background_gradient(
            cmap="RdYlGn", vmin=-1, vmax=1
        ).format("{:.3f}")
        st.dataframe(styled, use_container_width=True)
        st.caption("🟢 Màu xanh: Tương quan thuận | 🔴 Màu đỏ: Tương quan nghịch | ⚪ Màu trắng: Không tương quan.")

    with st.expander("🔎 Xem ma trận Chi tiết (p-value)", expanded=False):
        st.markdown("**Bảng giá trị p-value:** (Càng nhỏ càng có ý nghĩa)")
        p_df = pd.DataFrame(p_dict)
        styled_p = p_df.style.background_gradient(
            cmap="RdYlGn_r", vmin=0, vmax=0.1
        ).format("{:.4f}")
        st.dataframe(styled_p, use_container_width=True)

    # ── Significant Pairs Table ──
    if sig_pairs:
        st.markdown(section_header(f"💡 Phát hiện {len(sig_pairs)} mối liên hệ có ý nghĩa"), unsafe_allow_html=True)
        
        st.info("Bảng dưới đây liệt kê các cặp biến có mối liên hệ thực sự (p < 0.05).")

        sig_df = pd.DataFrame(sig_pairs)
        sig_df.columns = ["Biến 1", "Biến 2", "Hệ số r", "p-value", "Mức độ"]
        sig_df = sig_df.sort_values("Hệ số r", key=abs, ascending=False)

        def color_strength(row):
            strength_colors = {
                "strong": "background-color: #d4edda; font-weight: bold",
                "moderate": "background-color: #d1ecf1",
                "weak": "background-color: #fff3cd",
                "negligible": "background-color: #f8f9fa",
            }
            # Add emoji to 'Mức độ'
            color = strength_colors.get(row["Mức độ"], "")
            return [color] * len(row)

        st.dataframe(
            sig_df.style.apply(color_strength, axis=1).format({
                "Hệ số r": "{:.3f}",
                "p-value": "{:.4f}"
            }),
            use_container_width=True,
            hide_index=True,
        )
        
        # Summary findings tooltip
        strong_pairs = sig_df[sig_df["Mức độ"] == "strong"]
        if not strong_pairs.empty:
            with st.expander("✨ Phát hiện quan trọng (Tương quan mạnh)", expanded=True):
                for _, row in strong_pairs.head(3).iterrows():
                    st.success(f"• **{row['Biến 1']}** và **{row['Biến 2']}** có mối liên hệ rất chặt chẽ (r = {row['Hệ số r']:.3f}).")
    else:
        st.warning("⚠️ Không tìm thấy cặp biến nào có mối liên hệ có ý nghĩa thống kê (p < 0.05).")

    st.markdown("---")
    render_result_downloads(result, "correlation_report", "corr_export")

    if st.button("🤖 Phân tích chuyên sâu bằng AI", key="ai_corr_btn"):
        with st.spinner("AI đang giải thích và chẩn đoán nguyên nhân..."):
            from services.analysis_manager import AnalysisManager
            am = AnalysisManager(st.session_state["survey_data"])
            ai_explanation = am.explain_single_with_ai(result)
            st.info(f"**AI Insight:**\n\n{ai_explanation}")


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df."""
    for col in columns:
        if col in survey_data.df.columns and not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")
