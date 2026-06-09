"""
HT Analysis Smart — Streamlit Application
Main entry point for the survey data analysis UI.
"""
import sys
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
    st.markdown("# 📊 HT Analysis")
    st.markdown("**Smart Survey Analyzer**")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        [
            "📤 Upload",
            "📊 Preview",
            "📈 Descriptive",
            "🔬 Reliability",
            "🧩 EFA",
            "🔗 Correlation",
            "📉 Regression",
            "🧪 T-test / ANOVA",
        ],
        label_visibility="collapsed",
        key="nav_radio",
    )

    st.markdown("---")

    # Session info
    if "survey_data" in st.session_state:
        sd = st.session_state["survey_data"]
        st.markdown(f"📄 **{sd.filename}**")
        st.markdown(f"📏 {sd.df.shape[0]} rows × {sd.df.shape[1]} cols")

        likert_n = len(sd.get_likert_columns())
        demo_n = len(sd.get_demographic_columns())
        st.markdown(f"📊 {likert_n} Likert · 👤 {demo_n} Demo")

        if st.button("🗑️ Xóa dữ liệu", use_container_width=True):
            for key in ["survey_data", "uploaded_filename", "uploaded_size"]:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.markdown("_Chưa có dữ liệu._")

    st.markdown("---")
    st.caption("v1.0")


# ── Main Content ────────────────────────────────────────
if page == "📤 Upload":
    render_upload_page()
elif page == "📊 Preview":
    render_preview_page()
elif page == "📈 Descriptive":
    render_descriptive_page()
elif page == "🔬 Reliability":
    render_reliability_page()
elif page == "🧩 EFA":
    render_efa_page()
elif page == "🔗 Correlation":
    render_correlation_page()
elif page == "📉 Regression":
    render_regression_page()
elif page == "🧪 T-test / ANOVA":
    render_comparison_page()
