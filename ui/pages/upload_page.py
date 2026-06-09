"""
Upload Page — File upload with auto-processing pipeline.
"""
import streamlit as st
import time
import os
import tempfile

from ui.data_loader_ui import process_uploaded_file
from ui.styles import metric_card, info_box
from models.data_schema import ColumnType
from services.data_loader import get_excel_sheets


def render_upload_page():
    """Render the file upload page."""
    st.markdown("## 📤 Upload Dữ Liệu Khảo Sát")
    st.markdown(
        "Upload file khảo sát (.csv, .xlsx, .xls). "
        "Hệ thống sẽ tự động load, validate, preprocess và tạo báo cáo."
    )

    # ── File uploader ──────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Chọn file khảo sát",
        type=["csv", "xlsx", "xls"],
        help="Hỗ trợ: CSV (UTF-8, Latin-1), Excel (.xlsx, .xls)",
        key="file_uploader",
    )

    if uploaded_file is not None:
        # Show file info
        file_size_kb = uploaded_file.size / 1024
        size_str = f"{file_size_kb:.1f} KB" if file_size_kb < 1024 else f"{file_size_kb / 1024:.1f} MB"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(metric_card(uploaded_file.name, "Tên file", "blue"), unsafe_allow_html=True)
        with col2:
            st.markdown(metric_card(size_str, "Kích thước", "teal"), unsafe_allow_html=True)
        with col3:
            file_type = uploaded_file.name.rsplit(".", 1)[-1].upper()
            st.markdown(metric_card(file_type, "Định dạng", "green"), unsafe_allow_html=True)

        st.markdown("---")

        # Check if already processed this file
        if (
            "survey_data" in st.session_state
            and st.session_state.get("uploaded_filename") == uploaded_file.name
            and st.session_state.get("uploaded_size") == uploaded_file.size
        ):
            st.success("✅ File đã được xử lý. Chuyển sang **📊 Preview** để xem dữ liệu.")
            _show_quick_summary(st.session_state["survey_data"])
            return

        # Select sheet if it's an Excel file
        sheet_name = None
        if file_type in ("XLSX", "XLS"):
            # We need to save to a temp file to read sheets if we don't want to load everything
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type.lower()}") as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            
            sheets = get_excel_sheets(tmp_path)
            os.unlink(tmp_path)
            
            if len(sheets) > 1:
                st.info(f"📂 File này có {len(sheets)} sheets. Vui lòng chọn sheet cần phân tích:")
                sheet_name = st.selectbox("Chọn Sheet", sheets, index=0)
            elif len(sheets) == 1:
                sheet_name = sheets[0]

        # Process the file
        if st.button("🚀 Bắt đầu xử lý", type="primary", use_container_width=True):
            _process_file(uploaded_file, sheet_name=sheet_name)


def _process_file(uploaded_file, sheet_name=None):
    """Run the full processing pipeline with progress feedback."""
    progress_bar = st.progress(0, text="Đang chuẩn bị...")
    status = st.empty()

    try:
        # Step 1: Load
        status.info("📂 Đang đọc file...")
        progress_bar.progress(10, text="Đang đọc file...")
        time.sleep(0.3)

        # Step 2-4: Full pipeline (load → validate → preprocess → quality)
        status.info("⚙️ Đang xử lý dữ liệu (validate → preprocess → quality report)...")
        progress_bar.progress(30, text="Đang validate và preprocess...")

        survey_data = process_uploaded_file(uploaded_file, sheet_name=sheet_name)

        progress_bar.progress(80, text="Hoàn tất xử lý...")
        time.sleep(0.2)

        # Save to session state
        st.session_state["survey_data"] = survey_data
        st.session_state["uploaded_filename"] = uploaded_file.name
        st.session_state["uploaded_size"] = uploaded_file.size

        progress_bar.progress(100, text="✅ Hoàn tất!")
        status.empty()

        st.success("✅ Xử lý thành công! Chuyển sang **📊 Preview** để xem dữ liệu.")

        _show_quick_summary(survey_data)

    except Exception as e:
        progress_bar.empty()
        status.empty()
        st.error(f"❌ Lỗi khi xử lý file: {str(e)}")
        st.exception(e)


def _show_quick_summary(survey_data):
    """Show a quick summary after processing."""
    st.markdown("---")
    st.markdown("### 📋 Tổng quan nhanh")

    rows, cols = survey_data.df.shape

    # Column type counts
    type_counts = {}
    for info in survey_data.columns_info.values():
        t = info.detected_type.value
        type_counts[t] = type_counts.get(t, 0) + 1

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(f"{rows:,}", "Respondents", "blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(f"{cols}", "Cột", "teal"), unsafe_allow_html=True)
    with c3:
        likert_count = type_counts.get("likert", 0)
        st.markdown(metric_card(f"{likert_count}", "Likert Items", "green"), unsafe_allow_html=True)
    with c4:
        demo_count = type_counts.get("demographic", 0)
        st.markdown(metric_card(f"{demo_count}", "Demographic", "orange"), unsafe_allow_html=True)

    # Quality score (from quality report)
    from models.data_schema import AnalysisType
    quality_results = survey_data.get_analysis_by_type(AnalysisType.QUALITY_REPORT)
    if quality_results:
        qr = quality_results[0]
        score = qr.data.get("dataset_score", 0)
        grade = qr.data.get("dataset_grade", "N/A")
        st.markdown(f"**Chất lượng dữ liệu:** {score}/100 ({grade})")

        if qr.warnings:
            with st.expander(f"⚠️ {len(qr.warnings)} cảnh báo", expanded=False):
                for w in qr.warnings:
                    st.warning(w)

    # Processing log
    if survey_data.processing_log:
        with st.expander("📝 Processing Log", expanded=False):
            for log_entry in survey_data.processing_log:
                st.text(f"  • {log_entry}")

    # Validation summary
    if survey_data.is_validated:
        val = survey_data.validation
        if val.errors > 0:
            st.error(f"Validation: {val.errors} errors, {val.warnings} warnings")
        elif val.warnings > 0:
            st.warning(f"Validation: {val.warnings} warnings")
        else:
            st.success("Validation: Không có lỗi")
