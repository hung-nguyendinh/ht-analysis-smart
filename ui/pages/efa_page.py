"""
EFA Page — Exploratory Factor Analysis.
KMO, Bartlett, Communalities, Variance Explained, Rotated Component Matrix.
"""
import pandas as pd
import streamlit as st

from services.efa import compute_efa
from services.scale_scores import create_factor_scores_from_efa
from ui.analysis_helpers import get_numeric_column_names, render_column_picker
from ui.export_helpers import render_result_downloads
from ui.styles import metric_card, section_header


def render_efa_page():
    """Render the EFA page."""
    st.markdown("## 🔬 Phân Tích Nhân Tố Khám Phá — EFA")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    all_cols = list(df.columns)
    numeric_cols = get_numeric_column_names(df)

    if len(numeric_cols) < 3:
        st.warning("⚠️ Cần ít nhất 3 cột số để chạy EFA.")
        return

    # ═══════════════════════════════════════════════════════════════
    # STEP 1 — Chọn biến
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("Bước 1 — Chọn biến"), unsafe_allow_html=True)

    default_cols = numeric_cols if len(numeric_cols) <= 20 else numeric_cols[:20]
    selected_cols = render_column_picker(
        df,
        key="efa_cols",
        label="Chọn các biến đưa vào phân tích nhân tố",
        all_columns=all_cols,
        default_columns=default_cols,
        recommended_columns=numeric_cols,
        columns_info=survey_data.columns_info,
        min_columns=3,
        help_text="Chọn các biến Likert/số cần rút gọn thành nhân tố. Có thể lọc nhanh nhóm Số/Likert để tránh chọn nhầm biến định danh.",
    )

    if len(selected_cols) < 3:
        st.info("⬆️ Chọn ít nhất **3 biến** để bắt đầu.")
        return

    # STEP 2 — Options
    st.markdown(section_header("Bước 2 — Tuỳ chọn"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        rotation = st.selectbox(
            "Phương pháp xoay (Rotation):",
            ["varimax", "promax"],
            key="efa_rotation",
            help="Varimax: xoay trực giao (phổ biến). Promax: xoay xiên (cho phép tương quan giữa nhân tố).",
        )
    with col2:
        auto_factors = st.checkbox("Tự động xác định số nhân tố (Eigenvalue > 1)", value=True, key="efa_auto")
        n_factors = None
        if not auto_factors:
            n_factors = st.number_input("Số nhân tố:", min_value=1, max_value=len(selected_cols), value=3, key="efa_nf")
    with col3:
        loading_threshold = st.selectbox(
            "Ngưỡng Factor Loading:",
            [0.3, 0.4, 0.5, 0.6],
            index=2,
            key="efa_threshold",
            help="Biến có loading < ngưỡng sẽ được cảnh báo.",
        )

    with st.expander("❓ Giải thích về EFA", expanded=False):
        st.markdown("""
**EFA (Exploratory Factor Analysis) là gì?**
- Phương pháp rút gọn nhiều biến quan sát thành ít **nhân tố** hơn.
- Giúp xác định cấu trúc ẩn trong dữ liệu khảo sát.

**Các bước kiểm tra:**
1. **KMO ≥ 0.5**: Dữ liệu phù hợp cho EFA
2. **Bartlett's Test Sig < 0.05**: Ma trận tương quan KHÔNG phải ma trận đơn vị
3. **Eigenvalue > 1**: Quy tắc chọn số nhân tố
4. **Cumulative Variance ≥ 50%**: Nhân tố trích phải giải thích ≥ 50% phương sai
5. **Factor Loading ≥ 0.5**: Biến phải tải đáng kể lên nhân tố
6. **Không có cross-loading**: Biến chỉ nên tải lên 1 nhân tố
        """)

    _ensure_numeric(survey_data, selected_cols)

    st.markdown("---")
    if st.button("🔍 Chạy EFA", type="primary", use_container_width=True, key="efa_run"):
        with st.spinner("Đang phân tích nhân tố..."):
            result = compute_efa(
                survey_data,
                columns=selected_cols,
                n_factors=n_factors,
                rotation=rotation,
                loading_threshold=loading_threshold,
            )
        st.session_state["efa_result"] = result

    result = st.session_state.get("efa_result")
    if result is None:
        return

    st.markdown("---")

    if result.warnings:
        for w in result.warnings:
            st.warning(f"⚠️ {w}")

    if not result.data:
        st.error(result.summary_text)
        return

    data = result.data
    _render_efa_results(survey_data, data, result)


def _render_efa_results(survey_data, data: dict, result):
    """Render full EFA results."""

    # ═══════════════════════════════════════════════════════════════
    # A — KMO & BARTLETT
    # ═══════════════════════════════════════════════════════════════
    st.markdown(section_header("📋 Kiểm Định Điều Kiện EFA"), unsafe_allow_html=True)

    kmo = data.get("kmo", {})
    bartlett = data.get("bartlett", {})
    kmo_overall = kmo.get("overall", 0)
    kmo_interp = kmo.get("interpretation", "N/A")
    bartlett_sig = bartlett.get("significant", False)
    bartlett_p = bartlett.get("p_value", 1)

    # Verdict
    kmo_ok = kmo_overall >= 0.5
    bartlett_ok = bartlett_sig

    if kmo_ok and bartlett_ok:
        st.success("✅ Dữ liệu **ĐẠT** điều kiện chạy EFA.")
    elif kmo_ok:
        st.warning("⚠️ KMO đạt nhưng Bartlett's Test không có ý nghĩa.")
    elif bartlett_ok:
        st.warning("⚠️ Bartlett's Test đạt nhưng KMO quá thấp.")
    else:
        st.error("❌ Dữ liệu KHÔNG phù hợp cho EFA.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        color = "green" if kmo_ok else "red"
        st.markdown(metric_card(f"{kmo_overall:.4f}", "KMO", color), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(kmo_interp, "Đánh giá KMO", color), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(f"{bartlett.get('chi_square', 0):.2f}", "Bartlett χ²", "blue"), unsafe_allow_html=True)
    with c4:
        b_color = "green" if bartlett_ok else "red"
        st.markdown(metric_card(f"{bartlett_p:.6f}", "Bartlett Sig.", b_color), unsafe_allow_html=True)

    with st.expander("ℹ️ Thang đánh giá KMO"):
        st.markdown("""
| KMO | Đánh giá | Ý nghĩa |
|:---|:---|:---|
| **0.9–1.0** | Marvelous | Rất tuyệt vời |
| **0.8–0.9** | Meritorious | Tốt |
| **0.7–0.8** | Middling | Khá |
| **0.6–0.7** | Mediocre | Tạm được |
| **0.5–0.6** | Miserable | Tệ |
| **< 0.5** | Unacceptable | Không nên chạy EFA |
        """)

    # ═══════════════════════════════════════════════════════════════
    # B — COMMUNALITIES
    # ═══════════════════════════════════════════════════════════════
    communalities = data.get("communalities", [])
    if communalities:
        with st.expander("📊 Communalities", expanded=False):
            comm_df = pd.DataFrame(communalities)
            comm_df.columns = ["Biến", "Initial", "Extraction"]

            def highlight_low_comm(row):
                styles = [""] * len(row)
                if row["Extraction"] < 0.5:
                    styles[2] = "background-color: #fff3cd"
                return styles

            st.dataframe(
                comm_df.style.apply(highlight_low_comm, axis=1).format({
                    "Initial": "{:.4f}",
                    "Extraction": "{:.4f}",
                }),
                use_container_width=True, hide_index=True,
            )
            st.caption("🟡 Extraction < 0.5: biến giải thích ít cho nhân tố chung.")

    # ═══════════════════════════════════════════════════════════════
    # C — TOTAL VARIANCE EXPLAINED
    # ═══════════════════════════════════════════════════════════════
    variance = data.get("variance_explained", [])
    if variance:
        st.markdown(section_header("📈 Total Variance Explained"), unsafe_allow_html=True)

        cum_extracted = data.get("cumulative_variance_extracted", 0)
        n_factors = data.get("n_factors", 0)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(metric_card(str(n_factors), "Số nhân tố trích", "blue"), unsafe_allow_html=True)
        with c2:
            cum_color = "green" if cum_extracted >= 50 else "orange"
            st.markdown(metric_card(f"{cum_extracted:.1f}%", "Tổng phương sai giải thích", cum_color), unsafe_allow_html=True)

        var_df = pd.DataFrame(variance)
        var_df.columns = ["Component", "Eigenvalue", "% Variance", "Cumulative %", "Extracted?"]
        var_df["Extracted?"] = var_df["Extracted?"].map({True: "✅", False: ""})

        def highlight_extracted(row):
            if row["Extracted?"] == "✅":
                return ["background-color: #d4edda"] * len(row)
            return [""] * len(row)

        st.dataframe(
            var_df.style.apply(highlight_extracted, axis=1).format({
                "Eigenvalue": "{:.4f}",
                "% Variance": "{:.2f}",
                "Cumulative %": "{:.2f}",
            }),
            use_container_width=True, hide_index=True,
        )

        # Scree Plot
        scree = data.get("scree_data", [])
        if scree:
            with st.expander("📉 Scree Plot", expanded=True):
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(scree) + 1)),
                    y=scree,
                    mode="lines+markers",
                    name="Eigenvalue",
                    line=dict(color="#2196F3", width=2),
                    marker=dict(size=8),
                ))
                fig.add_hline(y=1, line_dash="dash", line_color="red",
                             annotation_text="Eigenvalue = 1")
                fig.update_layout(
                    title="Scree Plot",
                    xaxis_title="Component",
                    yaxis_title="Eigenvalue",
                    template="plotly_white",
                    height=400,
                )
                st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════
    # D — ROTATED COMPONENT MATRIX
    # ═══════════════════════════════════════════════════════════════
    rotated = data.get("rotated_matrix", [])
    if rotated:
        st.markdown(section_header("🔄 Rotated Component Matrix"), unsafe_allow_html=True)

        rotation_method = data.get("rotation_method", "varimax").capitalize()
        threshold = data.get("loading_threshold", 0.5)
        st.caption(f"Rotation: **{rotation_method}** | Ngưỡng loading: **{threshold}**")

        rot_df = pd.DataFrame(rotated)

        # Columns to display
        factor_cols = [c for c in rot_df.columns if c.startswith("Factor_")]
        display_cols = ["variable"] + factor_cols
        display_df = rot_df[display_cols].copy()
        display_df = display_df.rename(columns={"variable": "Biến"})

        def highlight_loading(val):
            try:
                v = float(val)
                if abs(v) >= threshold:
                    return "background-color: #c8e6c9; font-weight: bold"
                elif abs(v) >= threshold - 0.1:
                    return "background-color: #fff9c4"
            except (ValueError, TypeError):
                pass
            return ""

        styled = display_df.style.map(
            highlight_loading,
            subset=factor_cols,
        ).format({col: "{:.4f}" for col in factor_cols})

        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption(f"🟢 Loading ≥ {threshold} | 🟡 Loading gần ngưỡng")

    # Cross-loading warning
    cross = data.get("cross_loadings", [])
    if cross:
        with st.expander("⚠️ Cross-Loading (biến tải lên nhiều nhân tố)", expanded=True):
            cross_df = pd.DataFrame(cross)
            cross_df["factors"] = cross_df["factors"].apply(lambda x: ", ".join([f"F{f}" for f in x]))
            cross_df["loadings"] = cross_df["loadings"].apply(lambda x: ", ".join([f"{v:.3f}" for v in x]))
            cross_df.columns = ["Biến", "Nhân tố", "Loading"]
            st.dataframe(cross_df, use_container_width=True, hide_index=True)
            st.info("💡 **Gợi ý:** Biến có cross-loading nên được xem xét loại bỏ hoặc gán vào nhân tố có loading cao nhất.")

    # ═══════════════════════════════════════════════════════════════
    # E — FACTOR GROUPING SUMMARY
    # ═══════════════════════════════════════════════════════════════
    if rotated:
        st.markdown(section_header("💡 Tóm Tắt Nhóm Nhân Tố"), unsafe_allow_html=True)

        n_factors = data.get("n_factors", 0)
        for f in range(1, n_factors + 1):
            items = [
                r for r in rotated
                if r.get("assigned_factor") == f and r.get("meets_threshold", False)
            ]
            if items:
                item_names = [r["variable"] for r in items]
                loadings = [r.get(f"Factor_{f}", 0) for r in items]
                avg_loading = sum(abs(l) for l in loadings) / len(loadings)
                st.markdown(
                    f"**Nhân tố {f}** ({len(items)} biến, TB loading = {avg_loading:.3f}): "
                    f"`{'`, `'.join(item_names)}`"
                )

    st.info(
        "Workflow tip: after EFA, create factor score columns from accepted item groups, "
        "then use those composite variables for Pearson and regression."
    )
    _render_factor_score_creator(survey_data, data)
    render_result_downloads(result, "efa_report", "efa_export")


def _ensure_numeric(survey_data, columns):
    """Ensure specified columns are numeric dtype in survey_data.df."""
    for col in columns:
        if col in survey_data.df.columns and not pd.api.types.is_numeric_dtype(survey_data.df[col]):
            survey_data.df[col] = pd.to_numeric(survey_data.df[col], errors="coerce")


def _render_factor_score_creator(survey_data, efa_data: dict):
    """Render controls to create mean score columns from EFA factor groups."""
    rotated = efa_data.get("rotated_matrix", [])
    n_factors = int(efa_data.get("n_factors", 0) or 0)
    groups = []

    for factor_idx in range(1, n_factors + 1):
        items = [
            row["variable"]
            for row in rotated
            if row.get("assigned_factor") == factor_idx and row.get("meets_threshold", False)
        ]
        if len(items) >= 2:
            groups.append({
                "factor": factor_idx,
                "n_items": len(items),
                "items": ", ".join(items),
            })

    with st.expander("Create factor score columns", expanded=False):
        if not groups:
            st.info("No factor has at least 2 accepted items, so no factor score can be created automatically.")
            return

        st.dataframe(pd.DataFrame(groups), use_container_width=True, hide_index=True)
        prefix = st.text_input("Column prefix", value="Factor", key="efa_score_prefix")
        allow_partial = st.checkbox(
            "Allow scores when at least 1 item is valid",
            value=False,
            key="efa_score_partial",
        )
        min_valid_items = 1 if allow_partial else None

        if st.button("Create factor score columns", key="efa_create_factor_scores"):
            try:
                created = create_factor_scores_from_efa(
                    survey_data,
                    efa_data=efa_data,
                    prefix=prefix,
                    min_valid_items=min_valid_items,
                    overwrite=True,
                )
                if created:
                    names = ", ".join(item["column"] for item in created)
                    st.success(f"Created factor score column(s): {names}.")
                else:
                    st.warning("No factor score columns were created.")
            except ValueError as exc:
                st.error(str(exc))
