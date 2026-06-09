"""
Preview Page — Data table, column info, quality report, and charts.
Includes detailed validation reporting (Errors vs Warnings).
"""
import pandas as pd
import streamlit as st

from models.data_schema import AnalysisType, ColumnType, IssueSeverity
from ui.styles import metric_card, quality_badge, section_header


def render_preview_page():
    """Render the data preview page."""
    st.markdown("## 📊 Data Preview")

    if "survey_data" not in st.session_state:
        st.info("📤 Chưa có dữ liệu. Vui lòng upload file ở trang **Upload**.")
        return

    survey_data = st.session_state["survey_data"]
    df = survey_data.df

    # ── Tabs ──────────────────────────────────────────────
    tab_data, tab_columns, tab_quality, tab_missing = st.tabs([
        "📋 Dữ liệu", "🏷️ Thông tin cột", "🏥 Chất lượng & Lỗi", "❓ Missing Data"
    ])

    with tab_data:
        _render_data_tab(df)

    with tab_columns:
        _render_columns_tab(survey_data)

    with tab_quality:
        _render_quality_tab(survey_data)

    with tab_missing:
        _render_missing_tab(survey_data)


def _render_data_tab(df: pd.DataFrame):
    """Render the data table tab."""
    st.markdown(section_header("Bảng dữ liệu"), unsafe_allow_html=True)

    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Tìm kiếm", placeholder="Nhập từ khóa đề lọc...", key="data_search")
    with col2:
        n_rows = st.selectbox("Số dòng hiển thị", [20, 50, 100, "Tất cả"], key="n_rows_select")

    # Filter
    display_df = df.copy()
    if search:
        mask = display_df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]
        st.caption(f"Tìm thấy {len(display_df)} / {len(df)} dòng phù hợp.")

    # Display
    if n_rows != "Tất cả":
        display_df = display_df.head(int(n_rows))

    st.dataframe(
        display_df,
        use_container_width=True,
        height=500,
    )

    st.caption(f"Tổng: {len(df)} dòng × {len(df.columns)} cột")


def _render_columns_tab(survey_data):
    """Render column information tab."""
    st.markdown(section_header("Thông tin các cột"), unsafe_allow_html=True)

    # Build column info table
    rows = []
    for col_name, info in survey_data.columns_info.items():
        type_emoji = {
            ColumnType.LIKERT: "📊",
            ColumnType.DEMOGRAPHIC: "👤",
            ColumnType.CATEGORICAL: "🏷️",
            ColumnType.NUMERIC: "🔢",
            ColumnType.ID: "🔑",
            ColumnType.OPEN_ENDED: "💬",
            ColumnType.UNKNOWN: "❓",
        }
        emoji = type_emoji.get(info.detected_type, "")

        rows.append({
            "Cột": col_name,
            "Loại": f"{emoji} {info.detected_type.value}",
            "DType gốc": info.original_dtype,
            "Missing": f"{info.missing_count} ({info.missing_ratio*100:.1f}%)",
            "Unique": info.unique_count,
            "Scale": info.scale_name or "—",
            "Converted": "✅" if info.is_converted else "—",
        })

    col_df = pd.DataFrame(rows)
    st.dataframe(col_df, use_container_width=True, hide_index=True, height=400)


def _render_quality_tab(survey_data):
    """Render quality report tab."""
    st.markdown(section_header("Kiểm định chất lượng"), unsafe_allow_html=True)

    # 1. Score Overview
    quality_results = survey_data.get_analysis_by_type(AnalysisType.QUALITY_REPORT)
    if quality_results:
        qr = quality_results[0]
        data = qr.data
        score = data.get("dataset_score", 0)
        grade = data.get("dataset_grade", "N/A")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"#### Điểm tổng quát: \n {quality_badge(score, grade)}", unsafe_allow_html=True)
        with c2:
            st.info(f"💡 **Đánh giá:** {grade}. {score}/100. " + 
                    ("Dữ liệu rất tốt." if score > 80 else "Dữ liệu cần làm sạch thêm." if score > 50 else "Dữ liệu có nhiều lỗi."))

    # 2. Validation Details (The "Full" part the user asked for)
    st.markdown("### 🏥 Chi tiết lỗi & Cảnh báo")
    
    val = survey_data.validation
    if not val.issues:
        st.success("✅ **Không có lỗi**: Chúc mừng! Dữ liệu của bạn sạch và đạt chuẩn để phân tích.")
    else:
        # Categorize
        errors = [i for i in val.issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in val.issues if i.severity == IssueSeverity.WARNING]

        if errors:
            st.error(f"❌ **Phát hiện {len(errors)} LỖI NGHIÊM TRỌNG (Cần xử lý ngay)**")
            for i, err in enumerate(errors):
                with st.expander(f"Lỗi {i+1}: {err.message}", expanded=True):
                    st.write(f"**Vị trí:** {err.column if err.column else 'Toàn tập dữ liệu'}")
                    st.markdown(f"**👉 Giải pháp:** {err.suggestion}")
        
        if warnings:
            st.warning(f"⚠️ **Phát hiện {len(warnings)} CẢNH BÁO (Nên lưu ý)**")
            for i, warn in enumerate(warnings):
                with st.expander(f"Cảnh báo {i+1}: {warn.message}", expanded=False):
                    st.write(f"**Vị trí:** {warn.column if warn.column else 'Toàn tập dữ liệu'}")
                    st.markdown(f"**👉 Giải pháp:** {warn.suggestion}")

    # 3. Column-level scores (from quality report)
    if quality_results:
        st.markdown(section_header("Chỉ số chi tiết từng cột"), unsafe_allow_html=True)
        qr_data = quality_results[0].data
        col_scores = qr_data.get("column_scores", [])
        if col_scores:
            score_rows = []
            for c in col_scores:
                score_rows.append({
                    "Cột": c["column"],
                    "Điểm": c["quality_score"],
                    "Valid": c["n_valid"],
                    "Missing %": f"{c['missing_pct']}%",
                    "Phát hiện": "; ".join(c.get("issues", [])) or "Sạch ✅",
                })
            score_df = pd.DataFrame(score_rows)
            st.dataframe(score_df, use_container_width=True, hide_index=True)


def _render_missing_tab(survey_data):
    """Render missing data analysis tab."""
    df = survey_data.df
    st.markdown(section_header("Tổng quan Missing Data"), unsafe_allow_html=True)

    missing_counts = df.isna().sum()
    missing_pct = (missing_counts / len(df) * 100).round(2)

    missing_df = pd.DataFrame({
        "Cột": missing_counts.index,
        "Số missing": missing_counts.values,
        "Tỉ lệ (%)": missing_pct.values,
    }).sort_values("Tỉ lệ (%)", ascending=False)

    has_missing = missing_df[missing_df["Số missing"] > 0]

    if has_missing.empty:
        st.success("✅ Không có missing data! Dữ liệu hoàn chỉnh 100%.")
        return

    total_missing = int(missing_counts.sum())
    total_cells = df.shape[0] * df.shape[1]
    cols_with_missing = len(has_missing)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card(f"{total_missing:,}", "Tổng cells missing", "orange"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(f"{total_missing / total_cells * 100:.1f}%", "Tỉ lệ tổng", "blue"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(f"{cols_with_missing}/{len(df.columns)}", "Cột có missing", "teal"), unsafe_allow_html=True)

    st.bar_chart(has_missing.set_index("Cột")[["Tỉ lệ (%)"]].head(20), color="#f5576c")
    st.dataframe(has_missing, use_container_width=True, hide_index=True)
