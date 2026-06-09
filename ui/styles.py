"""
Custom CSS styles for the Streamlit application.
"""


def get_custom_css() -> str:
    """Return custom CSS for the application."""
    return """
    <style>
    /* ── Google Font ────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif !important;
    }

    /* ── Main container ───────────────────────────────── */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* ── Metric cards ─────────────────────────────────── */
    .metric-card {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        border-radius: 16px;
        padding: 1.5rem;
        color: #5c4d53;
        text-align: center;
        box-shadow: 0 4px 15px rgba(255, 154, 158, 0.2);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255, 154, 158, 0.35);
    }
    .metric-card .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0.3rem 0;
        color: #d1495b;
    }
    .metric-card .metric-label {
        font-size: 0.95rem;
        font-weight: 600;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Card color variants - Soft pink pastels */
    .metric-card.blue   { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }
    .metric-card.green  { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
    .metric-card.orange { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); }
    .metric-card.teal   { background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%); }

    /* ── Quality badge ────────────────────────────────── */
    .quality-badge {
        display: inline-block;
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.3px;
    }
    .quality-badge.excellent { background: #d4edda; color: #155724; }
    .quality-badge.good      { background: #cce5ff; color: #004085; }
    .quality-badge.acceptable{ background: #fff3cd; color: #856404; }
    .quality-badge.fair       { background: #ffeeba; color: #856404; }
    .quality-badge.poor       { background: #f8d7da; color: #721c24; }
    .quality-badge.critical   { background: #f5c6cb; color: #721c24; }

    /* ── Info box ──────────────────────────────────────── */
    .info-box {
        background: linear-gradient(135deg, #fff0f3 0%, #ffe4e8 100%);
        border-left: 4px solid #ff9a9e;
        border-radius: 0 12px 12px 0;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        color: #5c4d53;
        font-weight: 500;
    }

    /* ── Section header ───────────────────────────────── */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #d1495b;
        margin: 1.5rem 0 0.8rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px dashed #ffc0cb;
    }

    /* ── Upload area ──────────────────────────────────── */
    [data-testid="stFileUploader"] {
        border-radius: 16px;
    }
    [data-testid="stFileUploader"] > div {
        border-radius: 16px;
        background-color: #fff0f5;
        border: 2px dashed #ff9a9e;
    }

    /* ── Dataframe styling ────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #ffe4e8;
    }

    /* ── Sidebar ──────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fff0f5 0%, #ffe4e1 100%);
        border-right: 1px solid #ffc0cb;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #d1495b !important;
        font-weight: 700;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        color: #5c4d53 !important;
        font-weight: 500;
    }

    /* ── Progress bar ─────────────────────────────────── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #ff9a9e, #ffc0cb);
        border-radius: 10px;
    }

    /* ── Target Headers in Main Area ──────────────────── */
    h1, h2, h3 {
        color: #d1495b !important;
    }
    
    /* ── Global Text ──────────────────────────────────── */
    .stMarkdown p {
        color: #5c4d53;
        font-size: 1.05rem;
    }

    </style>
    """


def metric_card(value, label, color="blue") -> str:
    """Generate HTML for a metric card."""
    return f"""
    <div class="metric-card {color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """


def quality_badge(score: float, grade: str) -> str:
    """Generate HTML for a quality score badge."""
    grade_class = grade.lower()
    return f'<span class="quality-badge {grade_class}">{score}/100 — {grade}</span>'


def info_box(text: str) -> str:
    """Generate HTML for an info box."""
    return f'<div class="info-box">{text}</div>'


def section_header(text: str) -> str:
    """Generate HTML for a section header."""
    return f'<div class="section-header">{text}</div>'
