"""
Group Comparison Page — T-test, ANOVA, Mann-Whitney, Kruskal-Wallis.
Full statistics with user-friendly explanations and guidance.
"""
from copy import deepcopy

import pandas as pd
import streamlit as st

from services.comparison import compare_groups
from ui.analysis_helpers import get_categorical_column_names, get_numeric_column_names
from ui.export_helpers import render_result_downloads
from ui.styles import metric_card, section_header


# ── Test description reference ────────────────────────────────────────────────
_TEST_INFO = {
    "auto": {
        "title": "🤖 Tự động",
        "desc": "Hệ thống tự chọn T-test hoặc ANOVA dựa trên số nhóm, độ chuẩn và phương sai đều.",
        "when": "Khuyên dùng khi bạn không chắc chắn về loại kiểm định.",
    },
    "ttest": {
        "title": "📊 T-test Độc lập",
        "desc": "So sánh trung bình của **đúng 2 nhóm độc lập**. Giả định phân phối chuẩn và phương sai đều.",
        "when": "Dùng khi: 2 nhóm, dữ liệu xấp xỉ chuẩn (Shapiro-Wilk: p > 0.05).",
        "condition": 2,
    },
    "mannwhitney": {
        "title": "🔀 Mann-Whitney U",
        "desc": "So sánh phân phối của **2 nhóm** không cần giả định phân phối chuẩn (phi tham số).",
        "when": "Dùng khi: 2 nhóm, dữ liệu KHÔNG chuẩn hoặc thang đo thứ bậc (Likert).",
        "condition": 2,
    },
    "anova": {
        "title": "📐 One-Way ANOVA",
        "desc": "So sánh trung bình của **3 nhóm trở lên** đồng thời. Giả định phân phối chuẩn và phương sai đều.",
        "when": "Dùng khi: ≥ 3 nhóm, dữ liệu xấp xỉ chuẩn.",
        "condition": 3,
    },
    "kruskal": {
        "title": "🎲 Kruskal-Wallis H",
        "desc": "So sánh phân phối của **3 nhóm trở lên** không cần giả định chuẩn (phi tham số).",
        "when": "Dùng khi: ≥ 3 nhóm, dữ liệu KHÔNG chuẩn hoặc thang đo thứ bậc.",
        "condition": 3,
    },
}

_EFFECT_GUIDE = {
    "cohen_d": {
        "name": "Cohen's d",
        "rows": [
            ("≥ 0.80", "Large", "🟢", "Khác biệt lớn, rõ ràng"),
            ("0.50–0.79", "Medium", "🟡", "Khác biệt vừa, đáng chú ý"),
            ("0.20–0.49", "Small", "🟠", "Khác biệt nhỏ, cần thêm data"),
            ("< 0.20", "Negligible", "🔴", "Gần như không khác biệt"),
        ],
    },
    "eta_squared": {
        "name": "Eta-squared (η²)",
        "rows": [
            ("≥ 0.14", "Large", "🟢", "Nhóm giải thích lớn phương sai"),
            ("0.06–0.13", "Medium", "🟡", "Giải thích vừa phải"),
            ("0.01–0.05", "Small", "🟠", "Giải thích ít"),
            ("< 0.01", "Negligible", "🔴", "Không đáng kể"),
        ],
    },
    "r": {
        "name": "r (Rank-biserial)",
        "rows": [
            ("≥ 0.50", "Large", "🟢", "Ảnh hưởng lớn"),
            ("0.30–0.49", "Medium", "🟡", "Ảnh hưởng vừa"),
            ("0.10–0.29", "Small", "🟠", "Ảnh hưởng nhỏ"),
            ("< 0.10", "Negligible", "🔴", "Không đáng kể"),
        ],
    },
}


def render_comparison_page():
    """Render the Group Comparison page."""
    st.markdown("## 🧪 So Sánh Nhóm — T-test / ANOVA")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)
    cat_cols = get_categorical_column_names(df)

    if len(all_cols) < 2:
        st.warning("⚠️ Cần ít nhất 2 cột: 1 cột nhóm + 1 cột giá trị.")
        return

    # ═══════════════════════════════════════════════════════════════
    # STEP 1 — Chọn biến
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 1 — Chọn biến"), unsafe_allow_html=True)

    group_default_idx = 0
    if cat_cols and cat_cols[0] in all_cols:
        group_default_idx = all_cols.index(cat_cols[0])

    col1, col2 = st.columns(2)
    with col1:
        group_col = st.selectbox(
            "📌 Biến nhóm (Group Variable):",
            options=all_cols,
            index=group_default_idx,
            key="cmp_group",
            help="Cột phân loại nhóm. Vd: Giới tính, Trình độ, Địa điểm...",
        )
    with col2:
        value_options = [c for c in all_cols if c != group_col]
        val_default_idx = 0
        for i, c in enumerate(value_options):
            if c in numeric_cols:
                val_default_idx = i
                break
        value_col = st.selectbox(
            "📊 Biến phân tích (Dependent Variable):",
            options=value_options,
            index=val_default_idx,
            key="cmp_value",
            help="Cột số cần so sánh giữa các nhóm. Vd: điểm đánh giá Likert.",
        )

    # ═══════════════════════════════════════════════════════════════
    # STEP 2 — Xem cấu trúc nhóm
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 2 — Cấu trúc nhóm"), unsafe_allow_html=True)

    group_counts = df[group_col].value_counts()
    all_groups = [str(x) for x in group_counts.index]
    n_groups_total = len(all_groups)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        summary_df = pd.DataFrame({
            "Tên nhóm": all_groups,
            "N": group_counts.values,
            "Tỷ lệ (%)": [f"{v / group_counts.sum() * 100:.1f}%" for v in group_counts.values],
        })
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with col_b:
        if n_groups_total == 2:
            st.success(f"✅ **2 nhóm** → Nên dùng:\n**T-test** hoặc **Mann-Whitney U**")
        elif n_groups_total >= 3:
            st.info(f"ℹ️ **{n_groups_total} nhóm** → Nên dùng:\n**ANOVA** hoặc **Kruskal-Wallis**")
        else:
            st.warning(f"⚠️ Chỉ có {n_groups_total} nhóm.")

    # Group filter
    selected_group_names = st.multiselect(
        "🎯 Chọn lọc nhóm cụ thể (để trống = tất cả):",
        options=all_groups,
        default=[],
        key="cmp_group_filter",
        help="Chọn đúng nhóm bạn muốn so sánh. Ví dụ: nếu muốn T-test 2 nhóm từ dữ liệu có 4 nhóm.",
    )

    # ═══════════════════════════════════════════════════════════════
    # STEP 3 — Chọn kiểm định
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 3 — Chọn kiểm định"), unsafe_allow_html=True)

    # Detect effective group count
    n_eff = len(selected_group_names) if selected_group_names else n_groups_total

    test_options = {
        "🤖 Tự động (Khuyên dùng)": "auto",
        "📊 T-test Độc lập (Chỉ 2 nhóm)": "ttest",
        "🔀 Mann-Whitney U (Chỉ 2 nhóm)": "mannwhitney",
        "📐 One-Way ANOVA (≥ 2 nhóm)": "anova",
        "🎲 Kruskal-Wallis H (≥ 2 nhóm)": "kruskal",
    }
    test_label = st.selectbox(
        "Loại kiểm định:",
        list(test_options.keys()),
        key="cmp_test",
    )
    test = test_options[test_label]
    test_key = test if test != "auto" else "auto"

    if test_key in _TEST_INFO:
        info = _TEST_INFO[test_key]
        with st.expander(f"ℹ️ {info['title']} — Giải thích chi tiết", expanded=False):
            st.markdown(f"**Mô tả:** {info['desc']}")
            st.markdown(f"**Khi nào dùng:** {info['when']}")
            # Warn if test is incompatible with group count
            if "condition" in info:
                cond = info["condition"]
                if cond == 2 and n_eff > 2:
                    st.warning(f"⚠️ {info['title'].split()[1]} phù hợp cho 2 nhóm. Bạn đang có {n_eff} nhóm → nên dùng ANOVA/Kruskal-Wallis.")
                elif cond == 3 and n_eff < 3:
                    st.info(f"ℹ️ {info['title'].split()[1]} thường dùng cho ≥ 3 nhóm. Với 2 nhóm, T-test/Mann-Whitney hiệu quả hơn.")

    # ═══════════════════════════════════════════════════════════════
    # Filter & Run
    # ═══════════════════════════════════════════════════════════════
    filtered_survey_data = survey_data
    if selected_group_names:
        filtered_survey_data = deepcopy(survey_data)
        original_types = df[group_col].unique()
        type_map = {str(x): x for x in original_types}
        actual_groups = [type_map[name] for name in selected_group_names]
        filtered_survey_data.df = df[df[group_col].isin(actual_groups)].copy()

    _ensure_numeric(filtered_survey_data, [value_col])

    st.markdown("---")
    if st.button("🔍 Chạy kiểm định", type="primary", use_container_width=True, key="cmp_run"):
        with st.spinner("Đang phân tích..."):
            result = compare_groups(
                filtered_survey_data,
                group_col=group_col,
                value_col=value_col,
                test=test,
            )
        st.session_state["cmp_result"] = (result, group_col, value_col)

    stored = st.session_state.get("cmp_result")
    if stored is None:
        return

    result, res_group_col, res_value_col = stored

    st.markdown("---")

    if result.warnings:
        for w in result.warnings:
            st.warning(f"⚠️ {w}")

    if not result.data:
        st.error(result.summary_text)
        return

    data = result.data
    _render_results(data, result)


def _render_results(data: dict, result):
    """Render full results with explanations."""
    is_sig = data.get("significant", False)
    p_val = data.get("p_value", 1.0)
    stat = data.get("statistic", 0)
    test_name = data.get("test_name", "")
    effect = data.get("effect_size")
    effect_label = data.get("effect_size_label", "Effect Size")
    effect_interp = data.get("effect_interpretation", "")
    n_groups = data.get("n_groups", 0)

    sig_color = "green" if is_sig else "orange"
    p_label = "p < 0.05" if p_val < 0.05 else "p ≥ 0.05"

    # ═══════════════════════════════════════════════════════════════
    # A — KẾT QUẢ TỔNG QUAN
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("📋 Kết Quả Tổng Quan"), unsafe_allow_html=True)

    # Big verdict
    if is_sig:
        st.success(
            f"✅ **Có sự khác biệt có ý nghĩa thống kê** giữa các nhóm "
            f"({test_name}, p = {p_val:.4f} < 0.05)."
        )
        st.markdown(
            "> 💡 **Diễn giải:** Các nhóm có trung bình/phân phối khác nhau một cách thực sự, "
            "không phải do ngẫu nhiên. Sự khác biệt này đáng tin cậy với mức α = 5%."
        )
    else:
        st.warning(
            f"⚠️ **Không có sự khác biệt có ý nghĩa thống kê** giữa các nhóm "
            f"({test_name}, p = {p_val:.4f} ≥ 0.05)."
        )
        st.markdown(
            "> 💡 **Diễn giải:** Chưa đủ bằng chứng để kết luận các nhóm khác nhau. "
            "Sự chênh lệch quan sát được có thể do ngẫu nhiên gây ra."
        )

    # Key metric cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(f"{stat:.4f}", "Giá trị thống kê\n(Test Statistic)", "blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(f"{p_val:.4f}", f"p-value ({p_label})", sig_color), unsafe_allow_html=True)
    with c3:
        eff_str = f"{effect:.4f}" if effect is not None else "N/A"
        st.markdown(metric_card(f"{eff_str}", effect_label, "teal"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card(effect_interp.capitalize(), "Mức độ ảnh hưởng", "teal"), unsafe_allow_html=True)

    # Explanation of each metric
    with st.expander("❓ Giải thích các chỉ số", expanded=False):
        st.markdown(f"""
**Test Statistic ({stat:.4f})**
- Trị số tính toán từ dữ liệu để so sánh với phân phối lý thuyết.
- Giá trị càng lớn (về tuyệt đối) thì sự khác biệt giữa các nhóm càng lớn.
- Với T-test: t; với ANOVA: F; với Mann-Whitney: U; với Kruskal-Wallis: H.

**p-value ({p_val:.4f})**
- Xác suất quan sát được sự khác biệt này (hoặc lớn hơn) nếu các nhóm thực sự giống nhau.
- **p < 0.05**: Kết luận có khác biệt ý nghĩa (sai lầm < 5%).
- **p ≥ 0.05**: Chưa đủ bằng chứng để kết luận có khác biệt.

**{effect_label} ({eff_str})**
- Đo lường **mức độ thực tế** của sự khác biệt (không chỉ có ý nghĩa hay không).
- p-value nhỏ không đồng nghĩa với khác biệt lớn; cần xem effect size.
        """)

        # Effect size table
        _render_effect_guide(effect_label, effect, effect_interp)

    # ═══════════════════════════════════════════════════════════════
    # B — THỐNG KÊ THEO NHÓM
    # ═══════════════════════════════════════════════════════════════
    group_stats = data.get("group_statistics", [])
    if group_stats:
        st.markdown(section_header("📊 A. Group Statistics (Thống kê mô tả)"), unsafe_allow_html=True)

        gs_df = pd.DataFrame(group_stats)
        gs_cols_map = {
            "group": "Nhóm",
            "n": "N",
            "mean": "Mean",
            "std": "Std. Deviation",
            "se_mean": "Std. Error Mean",
            "median": "Median",
        }
        gs_df = gs_df.rename(columns=gs_cols_map)

        # Highlight max/min mean
        if "Mean" in gs_df.columns:
            max_mean = gs_df["Mean"].max()
            min_mean = gs_df["Mean"].min()

            def highlight_mean(row):
                if row["Mean"] == max_mean:
                    return ["background-color: #d4edda"] * len(row)
                elif row["Mean"] == min_mean:
                    return ["background-color: #fff3cd"] * len(row)
                return [""] * len(row)

            st.dataframe(gs_df.style.apply(highlight_mean, axis=1), use_container_width=True, hide_index=True)
            st.caption("🟢 Nhóm có Mean cao nhất | 🟡 Nhóm có Mean thấp nhất")
        else:
            st.dataframe(gs_df, use_container_width=True, hide_index=True)

        with st.expander("❓ Giải thích thống kê nhóm", expanded=False):
            st.markdown("""
**N (Cỡ mẫu):** Số người/quan sát hợp lệ trong nhóm đó.

**Mean (Trung bình):** Giá trị trung bình của biến phân tích trong nhóm.
Nhóm có Mean cao hơn có xu hướng đánh giá/đo lường cao hơn.

**Std (Độ lệch chuẩn):** Mức độ phân tán quanh Mean.
Std nhỏ → các giá trị trong nhóm tập trung; Std lớn → phân tán nhiều.

**Median:** Giá trị giữa khi sắp xếp theo thứ tự. Ít bị ảnh hưởng bởi ngoại lệ.
So sánh Mean và Median: nếu khác biệt lớn, dữ liệu có thể lệch (skewed).
            """)

    # ═══════════════════════════════════════════════════════════════
    # C — KIỂM TRA GIẢ ĐỊNH
    # ═══════════════════════════════════════════════════════════════
    assumptions = data.get("assumptions", {})
    if assumptions:
        normality = assumptions.get("normality", {})
        ev = assumptions.get("equal_variance", {})

        # Determine overall assumption status
        all_normal = all(info.get("is_normal", False) for info in normality.values()) if normality else True
        equal_var = ev.get("equal_var", True) if ev else True

        with st.expander("🔎 Kiểm Tra Giả Định (Normality & Equal Variance)", expanded=True):
            st.markdown("""
> **Tại sao cần kiểm tra giả định?**
> T-test và ANOVA yêu cầu dữ liệu xấp xỉ phân phối chuẩn và phương sai đồng nhất.
> Nếu vi phạm, nên dùng phiên bản phi tham số (Mann-Whitney, Kruskal-Wallis).
            """)

            # ── Normality ──
            if normality:
                st.markdown("#### 📐 Kiểm định Shapiro-Wilk (Phân phối chuẩn)")
                norm_rows = []
                for grp, info in normality.items():
                    is_norm = info.get("is_normal", False)
                    norm_rows.append({
                        "Nhóm": grp,
                        "Cỡ mẫu (N)": info.get("n", ""),
                        "W-Statistic": info.get("statistic", ""),
                        "p-value": info.get("p_value", ""),
                        "Phân phối chuẩn?": "✅ Chuẩn" if is_norm else "❌ Không chuẩn",
                    })
                norm_df = pd.DataFrame(norm_rows)

                def highlight_norm(row):
                    if "❌" in str(row["Phân phối chuẩn?"]):
                        return ["background-color: #fff3cd"] * len(row)
                    return ["background-color: #d4edda"] * len(row)

                st.dataframe(norm_df.style.apply(highlight_norm, axis=1), use_container_width=True, hide_index=True)

                if all_normal:
                    st.success("✅ Tất cả nhóm đạt phân phối chuẩn (p > 0.05). Đủ điều kiện dùng T-test/ANOVA.")
                else:
                    st.warning("⚠️ Một hoặc nhiều nhóm KHÔNG đạt phân phối chuẩn (p ≤ 0.05). Nên dùng Mann-Whitney U hoặc Kruskal-Wallis.")

                with st.expander("❓ Hiểu về Shapiro-Wilk", expanded=False):
                    st.markdown("""
**Shapiro-Wilk Test:**
- H₀: Dữ liệu có phân phối chuẩn
- **p > 0.05**: Chấp nhận H₀ → Dữ liệu chuẩn ✅
- **p ≤ 0.05**: Bác bỏ H₀ → Dữ liệu KHÔNG chuẩn ❌

**Lưu ý:** Với cỡ mẫu lớn (N > 50), ngay cả lệch nhỏ cũng làm p < 0.05.
Trong trường hợp này, xem thêm biểu đồ Q-Q hoặc dùng test phi tham số cho an toàn.
                    """)

            # ── Equal Variance ──
            if ev:
                st.markdown("#### ⚖️ Kiểm định Levene (Đồng nhất phương sai)")
                lev_stat = ev.get("statistic", "N/A")
                lev_p = ev.get("p_value", "N/A")
                has_equal_var = ev.get("equal_var", True)

                col_lev1, col_lev2 = st.columns(2)
                with col_lev1:
                    st.metric("Levene Statistic", f"{lev_stat}" if lev_stat != "N/A" else "N/A")
                with col_lev2:
                    st.metric("p-value", f"{lev_p}" if lev_p != "N/A" else "N/A")

                if has_equal_var:
                    st.success("✅ Phương sai đồng nhất (p > 0.05). Điều kiện T-test/ANOVA được thỏa mãn.")
                else:
                    st.warning("⚠️ Phương sai KHÔNG đồng nhất (p ≤ 0.05). T-test vẫn chạy được với Welch correction; ANOVA nên thay bằng Kruskal-Wallis.")

                with st.expander("❓ Hiểu về Levene Test", expanded=False):
                    st.markdown("""
**Levene's Test:**
- H₀: Tất cả nhóm có phương sai bằng nhau (Equal Variance)
- **p > 0.05**: Phương sai đều ✅ → T-test/ANOVA chuẩn
- **p ≤ 0.05**: Phương sai không đều ❌

**Nếu vi phạm:**
- T-test: Dùng phiên bản Welch (equal_var=False) — đã được áp dụng tự động.
- ANOVA: Xem xét chuyển sang Kruskal-Wallis hoặc Welch ANOVA.
                    """)

    # ═══════════════════════════════════════════════════════════════
    # D2 — T-TEST DETAILS (Independent Samples Test - SPSS Format)
    # ═══════════════════════════════════════════════════════════════
    ttest_details = data.get("ttest_details")
    if ttest_details:
        st.markdown(section_header("📊 B. Independent Samples Test"), unsafe_allow_html=True)
        
        lev_stat = ev.get("statistic", "N/A") if ev else "N/A"
        lev_p = ev.get("p_value", "N/A") if ev else "N/A"
        
        # Build DataFrame exactly like SPSS
        eq_assm = ttest_details.get("equal_assumed", {})
        eq_not_assm = ttest_details.get("equal_not_assumed", {})
        
        spss_rows = [
            {
                "Assumptions": "Equal variances assumed",
                "F (Levene)": lev_stat,
                "Sig. (Levene)": lev_p,
                "t": eq_assm.get("t"),
                "df": eq_assm.get("df"),
                "Sig. (2-tailed)": eq_assm.get("Sig"),
                "Mean Difference": eq_assm.get("Mean Difference"),
                "Std. Error Difference": eq_assm.get("Std. Error Difference"),
                "95% CI Lower": eq_assm.get("ci_lower"),
                "95% CI Upper": eq_assm.get("ci_upper"),
            },
            {
                "Assumptions": "Equal variances not assumed",
                "F (Levene)": "",  # Empty for second row in SPSS
                "Sig. (Levene)": "",
                "t": eq_not_assm.get("t"),
                "df": eq_not_assm.get("df"),
                "Sig. (2-tailed)": eq_not_assm.get("Sig"),
                "Mean Difference": eq_not_assm.get("Mean Difference"),
                "Std. Error Difference": eq_not_assm.get("Std. Error Difference"),
                "95% CI Lower": eq_not_assm.get("ci_lower"),
                "95% CI Upper": eq_not_assm.get("ci_upper"),
            }
        ]
        spss_df = pd.DataFrame(spss_rows)
        
        # Highlight the appropriate row based on Levene's test result
        equal_var_assumed = ev.get("equal_var", True) if ev else True
        
        def highlight_spss(row):
            if (row["Assumptions"] == "Equal variances assumed" and equal_var_assumed) or \
               (row["Assumptions"] == "Equal variances not assumed" and not equal_var_assumed):
                return ["background-color: #d4edda; font-weight: bold"] * len(row)
            return [""] * len(row)

        st.dataframe(spss_df.style.apply(highlight_spss, axis=1), use_container_width=True, hide_index=True)
        st.caption("🟢 Dòng được **tô viền xanh/in đậm** là kết quả bạn nên chọn dựa trên kiểm định phương sai Levene.")
        
    else:
        # Fallback for Mann-Whitney / Kruskal / etc
        mean_diff = data.get("mean_difference")
        if mean_diff is not None:
            st.markdown(section_header("📏 Chi Tiết Kiểm Định Tương Đương"), unsafe_allow_html=True)
            ci = data.get("confidence_interval_95", {})
            se_diff = data.get("std_error_difference", "N/A")

            detail_df = pd.DataFrame([{
                "Mean Difference": mean_diff,
                "Std. Error Difference": se_diff,
                "95% CI Lower": ci.get("lower", "N/A"),
                "95% CI Upper": ci.get("upper", "N/A"),
            }])
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════
    # D3 — POST HOC (Tukey/Bonferroni)
    # ═══════════════════════════════════════════════════════════════
    post_hoc = data.get("post_hoc")
    if post_hoc:
        st.markdown(section_header("🔍 Post Hoc — So Sánh Từng Cặp Nhóm"), unsafe_allow_html=True)

        method = post_hoc.get("method", "")
        st.caption(f"Phương pháp: **{method}** | Số cặp so sánh: {post_hoc.get('n_comparisons', 0)}")

        ph_results = post_hoc.get("results", [])
        if ph_results:
            ph_df = pd.DataFrame(ph_results)
            ph_display = ph_df[["group1", "group2", "mean_difference", "p_value", "significant", "ci_lower", "ci_upper"]].copy()
            ph_display.columns = ["Nhóm 1", "Nhóm 2", "Mean Diff", "Sig.", "Có ý nghĩa?", "95% CI Lower", "95% CI Upper"]
            ph_display["Có ý nghĩa?"] = ph_display["Có ý nghĩa?"].map({True: "✅ Có", False: "❌ Không"})

            def highlight_ph(row):
                if "✅" in str(row["Có ý nghĩa?"]):
                    return ["background-color: #d4edda"] * len(row)
                return [""] * len(row)

            st.dataframe(
                ph_display.style.apply(highlight_ph, axis=1),
                use_container_width=True, hide_index=True,
            )
            st.caption("🟢 Sig. < 0.05: Hai nhóm khác biệt có ý nghĩa thống kê")

            with st.expander("❓ Giải thích Post Hoc"):
                st.markdown(f"""
**{method}** so sánh từng cặp nhóm:
- **Mean Diff**: Chênh lệch trung bình giữa hai nhóm.
- **Sig.**: p-value sau khi hiệu chỉnh cho nhiều so sánh.
- **95% CI**: Khoảng tin cậy 95% của chênh lệch. Nếu không chứa 0 → khác biệt có ý nghĩa.
                """)

    # ═══════════════════════════════════════════════════════════════
    # D — KẾT LUẬN & GỢI Ý
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("💡 Kết Luận & Gợi Ý"), unsafe_allow_html=True)

    group_stats = data.get("group_statistics", [])
    gs_df_summary = pd.DataFrame(group_stats) if group_stats else None

    if is_sig and gs_df_summary is not None and "mean" in gs_df_summary.columns:
        max_row = gs_df_summary.loc[gs_df_summary["mean"].idxmax()]
        min_row = gs_df_summary.loc[gs_df_summary["mean"].idxmin()]
        st.markdown(f"""
**Tóm tắt phát hiện:**
- Nhóm **"{max_row['group']}"** có điểm trung bình cao nhất: **{max_row['mean']:.3f}**
- Nhóm **"{min_row['group']}"** có điểm trung bình thấp nhất: **{min_row['mean']:.3f}**
- Chênh lệch giữa 2 nhóm cực trị: **{max_row['mean'] - min_row['mean']:.3f}**
- Kiểm định {test_name}: p = {p_val:.4f} → **Khác biệt có ý nghĩa thống kê**
- Effect size: {effect_label} = {effect:.4f} → Mức độ **{effect_interp}**
        """)

        if n_groups >= 3:
            st.info(
                "📌 **Gợi ý tiếp theo:** Với ANOVA/Kruskal-Wallis, kết quả chỉ cho biết *có* sự khác biệt. "
                "Để biết **nhóm nào khác nhóm nào**, cần chạy thêm **Post-hoc Test** (Tukey HSD, Bonferroni, v.v.)."
            )
    elif not is_sig:
        st.markdown(f"""
**Tóm tắt:**
- p = {p_val:.4f} ≥ 0.05 → **Không đủ bằng chứng** kết luận các nhóm khác nhau.
- Có thể do: cỡ mẫu nhỏ, biến thiên trong nhóm lớn, hoặc thực sự không khác biệt.
        """)
        st.info(
            "📌 **Gợi ý:** Xem xét tăng cỡ mẫu, kiểm tra lại biến nhóm có thực sự phân chia đúng không, "
            "hoặc thử test phi tham số (Mann-Whitney/Kruskal-Wallis) nếu chưa dùng."
        )

    st.caption(f"📄 Báo cáo đầy đủ: {result.summary_text}")

    st.markdown("---")
    render_result_downloads(result, "comparison_report", "cmp_export")

    if st.button("🤖 Phân tích chuyên sâu bằng AI", key="ai_cmp_btn"):
        with st.spinner("AI đang giải thích và chẩn đoán nguyên nhân..."):
            from services.analysis_manager import AnalysisManager
            am = AnalysisManager(st.session_state["survey_data"])
            ai_explanation = am.explain_single_with_ai(result)
            st.info(f"**AI Insight:**\n\n{ai_explanation}")


def _render_effect_guide(effect_label: str, effect, effect_interp: str):
    """Render effect size interpretation guide."""
    # Detect which guide to use
    if "Cohen" in effect_label:
        key = "cohen_d"
    elif "η²" in effect_label or "Eta" in effect_label:
        key = "eta_squared"
    else:
        key = "r"

    guide = _EFFECT_GUIDE.get(key, _EFFECT_GUIDE["cohen_d"])

    st.markdown(f"**Thang đánh giá {guide['name']}:**")
    rows = []
    for rng, label, emoji, meaning in guide["rows"]:
        is_current = label.lower() == (effect_interp or "").lower()
        rows.append({
            "": emoji,
            "Ngưỡng": rng,
            "Mức độ": f"**{label}**" if is_current else label,
            "Ý nghĩa": f"**{meaning}** ← Kết quả của bạn" if is_current else meaning,
        })
    st.table(pd.DataFrame(rows))


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df."""
    for col in columns:
        if col in survey_data.df.columns and not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")
