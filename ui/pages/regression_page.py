"""
Regression Page — Linear Regression with Model Summary, ANOVA, Coefficients, Collinearity.
Full statistics with user-friendly explanations and guidance.
"""
import pandas as pd
import streamlit as st

from services.regression import compute_linear_regression
from ui.analysis_helpers import get_numeric_column_names, render_column_picker
from ui.export_helpers import render_result_downloads
from ui.styles import metric_card, modernize_icons, section_header


def render_regression_page():
    """Render the Linear Regression page."""
    st.markdown("## :material/trending_up: Hồi Quy Tuyến Tính — Linear Regression")

    if "survey_data" not in st.session_state:
        st.info("Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)

    if len(numeric_cols) < 2:
        st.warning("Cần ít nhất 2 cột số để chạy hồi quy.")
        return

    # ═══════════════════════════════════════════════════════════════
    # STEP 1 — Chọn biến
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 1 — Chọn biến", "tune"), unsafe_allow_html=True)

    dep_col = st.selectbox(
        "Biến phụ thuộc (Y — Dependent Variable):",
        options=numeric_cols,
        key="reg_dep",
        help="Biến bạn muốn DỰ ĐOÁN. Ví dụ: Sự hài lòng, Ý định mua...",
    )

    indep_options = [c for c in numeric_cols if c != dep_col]
    indep_cols = render_column_picker(
        df,
        key="reg_indep",
        label="Chọn biến độc lập (X — Independent Variables)",
        all_columns=indep_options,
        default_columns=indep_options[:min(5, len(indep_options))],
        recommended_columns=indep_options,
        columns_info=survey_data.columns_info,
        min_columns=1,
        help_text="Các biến bạn cho rằng ảnh hưởng đến biến phụ thuộc. Danh sách đã loại biến Y để tránh chọn trùng.",
    )

    if len(indep_cols) < 1:
        st.info("Chọn ít nhất **1 biến độc lập** để bắt đầu.")
        return

    st.info(
        "Workflow tip: run regression on composite scale/factor score columns created "
        "after Cronbach/EFA. Avoid putting many raw items into the same thesis model."
    )

    with st.expander("Giải thích về Hồi quy tuyến tính", expanded=False, icon=":material/help:"):
        st.markdown("""
**Hồi quy tuyến tính là gì?**
- Kiểm tra mối quan hệ nhân quả: biến X nào ảnh hưởng đến Y, mức độ bao nhiêu.
- Công thức: Y = β₀ + β₁X₁ + β₂X₂ + ... + ε

**Các chỉ số quan trọng:**
1. **R²**: % phương sai của Y được giải thích bởi các X. Càng cao càng tốt.
2. **F-test (ANOVA)**: Kiểm tra mô hình tổng thể có ý nghĩa không (p < 0.05).
3. **Standardized Beta (β)**: So sánh mức độ ảnh hưởng giữa các X (đã chuẩn hóa).
4. **VIF**: Kiểm tra đa cộng tuyến. VIF < 10 là chấp nhận được.
5. **Durbin-Watson**: Kiểm tra tự tương quan phần dư (lý tưởng: 1.5–2.5).
        """)

    _ensure_numeric(survey_data, [dep_col] + indep_cols)

    st.markdown("---")
    if st.button("Chạy hồi quy", type="primary", use_container_width=True, key="reg_run", icon=":material/play_arrow:"):
        with st.spinner("Đang phân tích..."):
            result = compute_linear_regression(survey_data, dep_col, indep_cols)
        st.session_state["reg_result"] = result

    result = st.session_state.get("reg_result")
    if result is None:
        return

    st.markdown("---")

    if result.warnings:
        for w in result.warnings:
            st.warning(w)

    if not result.data:
        st.error(result.summary_text)
        return

    data = result.data
    _render_regression_results(data, result)


def _render_regression_results(data: dict, result):
    """Render full regression results."""
    r = data.get("r", 0)
    r_sq = data.get("r_squared", 0)
    adj_r_sq = data.get("adj_r_squared", 0)
    std_err = data.get("std_error_estimate", 0)
    f_stat = data.get("f_statistic", 0)
    f_p = data.get("f_p_value", 1)
    dw = data.get("durbin_watson", 2)
    n = data.get("n", 0)
    is_sig = f_p < 0.05

    # ═══════════════════════════════════════════════════════════════
    # A — MODEL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Model Summary", "assessment"), unsafe_allow_html=True)

    if is_sig:
        st.success(f"Mô hình có ý nghĩa thống kê (F = {f_stat:.4f}, p = {f_p:.4f} < 0.05).")
    else:
        st.warning(f"Mô hình KHÔNG có ý nghĩa thống kê (F = {f_stat:.4f}, p = {f_p:.4f} ≥ 0.05).")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(f"{r:.4f}", "R", "blue"), unsafe_allow_html=True)
    with c2:
        color = "green" if r_sq >= 0.3 else "orange" if r_sq >= 0.1 else "red"
        st.markdown(metric_card(f"{r_sq:.4f}", "R² (R Square)", color), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(f"{adj_r_sq:.4f}", "Adjusted R²", "teal"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card(f"{std_err:.4f}", "Std. Error", "blue"), unsafe_allow_html=True)

    with st.expander("Giải thích Model Summary", icon=":material/help:"):
        st.markdown(f"""
**R = {r:.4f}**: Hệ số tương quan bội. Đo mức tương quan giữa giá trị dự đoán và thực tế.

**R² = {r_sq:.4f}**: Mô hình giải thích **{r_sq*100:.1f}%** phương sai của biến phụ thuộc.
- R² ≥ 0.50: Mô hình giải thích tốt
- R² ≥ 0.25: Khá
- R² < 0.10: Yếu

**Adjusted R² = {adj_r_sq:.4f}**: R² đã điều chỉnh cho số biến. Đáng tin cậy hơn R².

**Std. Error = {std_err:.4f}**: Sai số chuẩn ước lượng. Càng nhỏ càng tốt.

**Durbin-Watson = {dw:.4f}**: Kiểm tra tự tương quan phần dư.
- 1.5–2.5: Không có tự tương quan
- < 1.5 hoặc > 2.5: Có thể có tự tương quan
        """)

    # ═══════════════════════════════════════════════════════════════
    # B — ANOVA TABLE
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("ANOVA", "experiment"), unsafe_allow_html=True)

    anova_data = [
        {
            "Nguồn": "Regression",
            "SS": data.get("ss_regression", 0),
            "df": data.get("df_regression", 0),
            "MS": data.get("ms_regression", 0),
            "F": f_stat,
            "Sig.": f_p,
        },
        {
            "Nguồn": "Residual",
            "SS": data.get("ss_residual", 0),
            "df": data.get("df_residual", 0),
            "MS": data.get("ms_residual", 0),
            "F": "",
            "Sig.": "",
        },
        {
            "Nguồn": "Total",
            "SS": data.get("ss_total", 0),
            "df": data.get("df_regression", 0) + data.get("df_residual", 0),
            "MS": "",
            "F": "",
            "Sig.": "",
        },
    ]
    anova_df = pd.DataFrame(anova_data)
    st.dataframe(anova_df, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # C — COEFFICIENTS TABLE
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Coefficients", "table_view"), unsafe_allow_html=True)

    coefficients = data.get("coefficients", [])
    if coefficients:
        coef_rows = []
        for c in coefficients:
            row = {
                "Biến": c.get("variable", ""),
                "B": c.get("B", ""),
                "Std. Error": c.get("std_error", ""),
                "Beta (Chuẩn hóa)": c.get("beta_standardized", "—"),
                "t": c.get("t_value", ""),
                "Sig.": c.get("p_value", ""),
            }
            # Add VIF/Tolerance for non-constant
            if c.get("variable") != "(Constant)":
                row["Tolerance"] = c.get("tolerance", "")
                row["VIF"] = c.get("vif", "")
            else:
                row["Tolerance"] = "—"
                row["VIF"] = "—"
            coef_rows.append(row)

        coef_df = pd.DataFrame(coef_rows)

        def highlight_sig(row):
            styles = [""] * len(row)
            sig = row.get("Sig.")
            if sig != "" and sig is not None:
                try:
                    if float(sig) < 0.05:
                        styles[5] = "background-color: #d4edda; font-weight: bold"
                except (ValueError, TypeError):
                    pass
            # VIF warning
            vif = row.get("VIF")
            if vif != "" and vif != "—" and vif is not None:
                try:
                    if float(vif) >= 10:
                        styles[7] = "background-color: #ffcccc; font-weight: bold"
                    elif float(vif) >= 5:
                        styles[7] = "background-color: #fff3cd"
                except (ValueError, TypeError):
                    pass
            return styles

        st.dataframe(
            coef_df.style.apply(highlight_sig, axis=1),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Sig. < 0.05: có ý nghĩa thống kê | VIF ≥ 10: đa cộng tuyến nghiêm trọng | VIF ≥ 5: cần lưu ý")

        with st.expander("Giải thích bảng Coefficients", icon=":material/help:"):
            st.markdown("""
**B (Unstandardized)**: Hệ số hồi quy thô. Khi X tăng 1 đơn vị, Y thay đổi B đơn vị.

**Beta (Standardized)**: Hệ số chuẩn hóa. Dùng để so sánh mức ảnh hưởng giữa các biến X.
|Beta| lớn nhất = biến ảnh hưởng mạnh nhất.

**t-value & Sig.**: Kiểm định giả thuyết H₀: β = 0 (không ảnh hưởng).
- **Sig. < 0.05**: Biến có ảnh hưởng có ý nghĩa
- **Sig. ≥ 0.05**: Chưa đủ bằng chứng

**VIF (Variance Inflation Factor)**: Đo đa cộng tuyến.
- VIF < 2: Rất tốt
- VIF < 5: Chấp nhận
- VIF ≥ 10: Đa cộng tuyến nghiêm trọng → Cần loại biến

**Tolerance = 1/VIF**: Tolerance > 0.1 là chấp nhận.
            """)

        # Significant predictors summary
        sig_predictors = [
            c for c in coefficients
            if c.get("variable") != "(Constant)"
            and c.get("p_value") is not None
            and c.get("p_value") < 0.05
        ]

        if sig_predictors:
            # Sort by absolute beta
            sig_predictors.sort(
                key=lambda x: abs(x.get("beta_standardized", 0) or 0),
                reverse=True,
            )
            st.markdown(section_header("Kết Luận", "lightbulb"), unsafe_allow_html=True)
            st.markdown("**Các biến có ảnh hưởng có ý nghĩa (Sig. < 0.05):**")
            for p in sig_predictors:
                direction = "thuận" if (p.get("B", 0) or 0) > 0 else "nghịch"
                beta = p.get("beta_standardized", "N/A")
                st.markdown(
                    f"- **{p['variable']}**: β = {beta}, B = {p.get('B', '')}, "
                    f"p = {p.get('p_value', ''):.4f} → Ảnh hưởng **{direction}**"
                )

        st.markdown("---")
        render_result_downloads(result, "regression_report", "reg_export")

        if st.button("Phân tích chuyên sâu bằng AI", key="ai_reg_btn", icon=":material/auto_awesome:"):
            with st.spinner("AI đang giải thích và chẩn đoán nguyên nhân..."):
                from services.analysis_manager import AnalysisManager
                am = AnalysisManager(st.session_state["survey_data"])
                ai_explanation = am.explain_single_with_ai(result)
                st.info(f"**AI Insight:**\n\n{modernize_icons(ai_explanation)}")


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df."""
    for col in columns:
        if col in survey_data.df.columns and not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")
