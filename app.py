"""
HT Analysis Smart — Streamlit Application
Main entry point for the survey data analysis UI.
"""
import sys
from html import escape
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from ui.styles import get_custom_css
from ui.pages.upload_page import render_upload_page
from ui.pages.preview_page import render_preview_page
from ui.pages.descriptive_page import render_descriptive_page
from ui.pages.reliability_page import render_reliability_page
from ui.pages.comparison_page import render_comparison_page
from ui.pages.correlation_page import render_correlation_page
from ui.pages.regression_page import render_regression_page
from ui.pages.efa_page import render_efa_page


# ── Page Config ─────────────────────────────────────────
st.set_page_config(
    page_title="HT Analysis Smart",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject Custom CSS ───────────────────────────────────
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">
                <span class="material-symbols-rounded">query_stats</span>
            </div>
            <div class="brand-copy">
                <div class="brand-eyebrow">RESEARCH WORKSPACE</div>
                <div class="brand-title">HT Analysis</div>
                <div class="brand-subtitle">Smart Survey Analyzer</div>
            </div>
        </div>
        <div class="sidebar-section-label">Không gian phân tích</div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation
    page = st.radio(
        "Navigation",
        [
            "Upload",
            "Preview",
            "Descriptive",
            "Reliability",
            "EFA",
            "Correlation",
            "Regression",
            "T-test / ANOVA",
        ],
        label_visibility="collapsed",
        key="nav_radio",
    )

    # Session info
    st.markdown(
        '<div class="sidebar-section-label data-label">Trạng thái dữ liệu</div>',
        unsafe_allow_html=True,
    )
    if "survey_data" in st.session_state:
        sd = st.session_state["survey_data"]
        safe_filename = escape(str(sd.filename))
        likert_n = len(sd.get_likert_columns())
        demo_n = len(sd.get_demographic_columns())
        st.markdown(
            f"""
            <div class="dataset-card">
                <div class="dataset-topline">
                    <span class="status-dot"></span>
                    <span>Sẵn sàng phân tích</span>
                </div>
                <div class="dataset-name">{safe_filename}</div>
                <div class="dataset-stats">
                    <span><strong>{sd.df.shape[0]}</strong> dòng</span>
                    <span><strong>{sd.df.shape[1]}</strong> cột</span>
                </div>
                <div class="dataset-tags">
                    <span>{likert_n} Likert</span>
                    <span>{demo_n} nhân khẩu học</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Xóa dữ liệu", use_container_width=True):
            for key in ["survey_data", "uploaded_filename", "uploaded_size"]:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.markdown(
            """
            <div class="dataset-card dataset-empty">
                <div class="empty-visual">
                    <span></span><span></span><span></span>
                </div>
                <div class="dataset-name">Chưa có dữ liệu</div>
                <div class="dataset-hint">Tải lên tệp khảo sát để bắt đầu khám phá.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="sidebar-footer">
            <span>HT Lab</span>
            <span class="version-chip">v1.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main Content ────────────────────────────────────────
if page == "Upload":
    render_upload_page()
elif page == "Preview":
    render_preview_page()
elif page == "Descriptive":
    render_descriptive_page()
elif page == "Reliability":
    render_reliability_page()
elif page == "EFA":
    render_efa_page()
elif page == "Correlation":
    render_correlation_page()
elif page == "Regression":
    render_regression_page()
elif page == "T-test / ANOVA":
    render_comparison_page()
