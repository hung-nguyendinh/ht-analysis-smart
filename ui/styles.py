"""
Custom CSS styles for the Streamlit application.
"""


def get_custom_css() -> str:
    """Return custom CSS for the application."""
    return """
    <style>
    /* ── Google Font ────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif !important;
    }
    .material-symbols-rounded {
        font-family: 'Material Symbols Rounded' !important;
        font-style: normal;
        font-weight: 400;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
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
        height: 100vh;
        height: 100dvh;
        max-height: 100vh;
        max-height: 100dvh;
        overflow: hidden;
        background:
            radial-gradient(circle at 12% 8%, rgba(255, 255, 255, 0.92) 0 7%, transparent 28%),
            radial-gradient(circle at 95% 22%, rgba(255, 255, 255, 0.58) 0 4%, transparent 22%),
            linear-gradient(165deg, #fff7fa 0%, #ffe9f1 48%, #ffdde9 100%);
        border-right: 1px solid rgba(214, 91, 132, 0.14);
        box-shadow: 12px 0 35px rgba(138, 58, 91, 0.08);
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 19rem;
        height: 100%;
        max-height: 100%;
        overflow: hidden;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        box-sizing: border-box;
        height: 100%;
        max-height: 100%;
        margin-top: -2.5rem;
        padding: clamp(0.45rem, 1vh, 0.7rem) 0.9rem 0.75rem;
        overflow: hidden;
        overscroll-behavior: none;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        box-sizing: border-box;
        height: 100%;
        min-height: 0;
        max-height: 100%;
        gap: clamp(0.18rem, 0.45vh, 0.34rem);
        overflow: hidden;
    }
    [data-testid="stSidebar"] hr {
        display: none;
    }

    /* Sidebar brand */
    .sidebar-brand {
        position: relative;
        display: flex;
        align-items: center;
        gap: 0.82rem;
        margin-right: 2.4rem;
        margin-bottom: clamp(0.65rem, 1.5vh, 1rem);
        padding: clamp(0.72rem, 1.5vh, 0.95rem) 0.9rem;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.66);
        border: 1px solid rgba(255, 255, 255, 0.92);
        border-radius: 19px;
        box-shadow: 0 10px 26px rgba(177, 68, 109, 0.10);
        backdrop-filter: blur(12px);
    }
    .sidebar-brand::after {
        content: "";
        position: absolute;
        right: -26px;
        bottom: -34px;
        width: 92px;
        height: 92px;
        border: 1px solid rgba(224, 92, 140, 0.18);
        border-radius: 50%;
        box-shadow: 0 0 0 12px rgba(224, 92, 140, 0.05), 0 0 0 25px rgba(224, 92, 140, 0.04);
    }
    .brand-mark {
        position: relative;
        display: grid;
        flex: 0 0 2.9rem;
        width: 2.9rem;
        height: 2.9rem;
        place-items: center;
        color: #ffffff;
        background: linear-gradient(145deg, #ed6d9f, #c9487c);
        border-radius: 14px;
        box-shadow: 0 9px 18px rgba(201, 72, 124, 0.25);
    }
    .brand-mark::before,
    .brand-mark::after {
        content: "";
        position: absolute;
        width: 3.55rem;
        height: 1.4rem;
        border: 1px solid rgba(201, 72, 124, 0.38);
        border-radius: 50%;
        transform: rotate(35deg);
    }
    .brand-mark::after {
        transform: rotate(-35deg);
    }
    .brand-mark .material-symbols-rounded {
        position: relative;
        z-index: 1;
        font-size: 1.55rem;
        font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 28;
    }
    .brand-copy {
        position: relative;
        z-index: 1;
        min-width: 0;
    }
    .brand-eyebrow {
        margin-bottom: 0.15rem;
        color: #b85b7e;
        font-size: 0.52rem;
        font-weight: 700;
        letter-spacing: 0.15em;
    }
    .brand-title {
        color: #61283f;
        font-size: 1.04rem;
        font-weight: 700;
        line-height: 1.15;
    }
    .brand-subtitle {
        margin-top: 0.18rem;
        color: #9b7080;
        font-size: 0.68rem;
        font-weight: 600;
    }
    .sidebar-section-label {
        margin: 0.15rem 0 clamp(0.3rem, 0.7vh, 0.48rem) 0.7rem;
        color: #a66c82;
        font-size: 0.63rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .sidebar-section-label.data-label {
        margin-top: clamp(0.65rem, 1.4vh, 1rem);
    }

    /* Sidebar navigation */
    [data-testid="stSidebar"] [role="radiogroup"] {
        gap: clamp(0.08rem, 0.32vh, 0.2rem);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        position: relative;
        min-height: clamp(2.35rem, 4.7vh, 2.75rem);
        padding: clamp(0.43rem, 0.9vh, 0.62rem) 0.72rem;
        border: 1px solid transparent;
        border-radius: 13px;
        transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.66);
        border-color: rgba(220, 100, 145, 0.15);
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        color: #ffffff;
        background: linear-gradient(105deg, #df6593 0%, #c94a7d 100%);
        border-color: rgba(255, 255, 255, 0.42);
        box-shadow: 0 8px 18px rgba(190, 69, 116, 0.22);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 700;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label p {
        display: flex;
        align-items: center;
        gap: 0.68rem;
        color: #704357 !important;
        font-size: 0.84rem;
        font-weight: 600;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label p::before {
        display: inline-flex;
        flex: 0 0 1.2rem;
        align-items: center;
        justify-content: center;
        font-family: 'Material Symbols Rounded';
        font-size: 1.18rem;
        font-style: normal;
        font-weight: normal;
        font-variation-settings: 'FILL' 0, 'wght' 450, 'GRAD' 0, 'opsz' 24;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(1) p::before { content: "upload_file"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(2) p::before { content: "dataset"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(3) p::before { content: "monitoring"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(4) p::before { content: "verified"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(5) p::before { content: "hub"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(6) p::before { content: "scatter_plot"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(7) p::before { content: "trending_up"; }
    [data-testid="stSidebar"] [role="radiogroup"] label:nth-of-type(8) p::before { content: "experiment"; }
    [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
        display: none;
    }

    /* Dataset status */
    .dataset-card {
        padding: clamp(0.7rem, 1.35vh, 0.88rem);
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 16px;
        box-shadow: 0 8px 22px rgba(139, 65, 94, 0.08);
    }
    .dataset-topline {
        display: flex;
        align-items: center;
        gap: 0.42rem;
        margin-bottom: clamp(0.35rem, 0.7vh, 0.5rem);
        color: #a25876;
        font-size: 0.64rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .status-dot {
        width: 0.48rem;
        height: 0.48rem;
        background: #62b996;
        border: 2px solid #dff5ec;
        border-radius: 50%;
        box-shadow: 0 0 0 3px rgba(98, 185, 150, 0.12);
    }
    .dataset-name {
        overflow: hidden;
        color: #623249;
        font-size: 0.79rem;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .dataset-stats {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.42rem;
        margin-top: clamp(0.45rem, 0.9vh, 0.65rem);
    }
    .dataset-stats span {
        padding: clamp(0.35rem, 0.75vh, 0.46rem) 0.32rem;
        color: #9a6a7d;
        background: rgba(255, 240, 246, 0.8);
        border-radius: 10px;
        font-size: 0.64rem;
        text-align: center;
    }
    .dataset-stats strong {
        display: block;
        color: #c44d7b;
        font-size: 0.85rem;
    }
    .dataset-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-top: clamp(0.42rem, 0.8vh, 0.58rem);
    }
    .dataset-tags span,
    .version-chip {
        padding: 0.22rem 0.5rem;
        color: #a95476;
        background: #ffeaf2;
        border: 1px solid rgba(213, 91, 137, 0.11);
        border-radius: 999px;
        font-size: 0.58rem;
        font-weight: 700;
    }
    .dataset-empty {
        padding: clamp(0.75rem, 1.5vh, 0.95rem);
        text-align: center;
    }
    .empty-visual {
        display: flex;
        justify-content: center;
        gap: 0.25rem;
        margin-bottom: clamp(0.4rem, 0.8vh, 0.58rem);
    }
    .empty-visual span {
        width: 0.42rem;
        height: 0.42rem;
        background: #e988ae;
        border-radius: 50%;
        box-shadow: 0 0 0 4px rgba(233, 136, 174, 0.11);
    }
    .empty-visual span:nth-child(2) {
        background: #ca5c87;
        transform: translateY(-0.28rem);
    }
    .dataset-hint {
        max-width: 12rem;
        margin: 0.35rem auto 0;
        color: #9b7785;
        font-size: 0.67rem;
        line-height: 1.5;
    }
    [data-testid="stSidebar"] .stButton button {
        min-height: clamp(2.25rem, 4.5vh, 2.6rem);
        margin-top: clamp(0.3rem, 0.7vh, 0.45rem);
        color: #a8486d;
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid rgba(203, 77, 124, 0.15);
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 700;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton button p {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.48rem;
    }
    [data-testid="stSidebar"] .stButton button p::before {
        content: "delete";
        font-family: 'Material Symbols Rounded';
        font-size: 1.05rem;
        font-style: normal;
        font-weight: normal;
        font-variation-settings: 'FILL' 0, 'wght' 450, 'GRAD' 0, 'opsz' 24;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        white-space: nowrap;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        color: #ffffff;
        background: #c94a7d;
        border-color: #c94a7d;
    }
    .sidebar-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: clamp(0.55rem, 1.2vh, 0.85rem) 0.15rem 0;
        padding-top: clamp(0.45rem, 0.9vh, 0.65rem);
        color: #a77d8d;
        border-top: 1px solid rgba(190, 91, 129, 0.12);
        font-size: 0.62rem;
        font-weight: 700;
    }
    [data-testid="stSidebar"] .element-container:has(.sidebar-footer) {
        margin-top: auto;
    }

    /* Preserve readability while fitting genuinely short viewports. */
    @media (max-height: 680px) {
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 0.35rem;
            padding-bottom: 0.4rem;
        }
        .sidebar-brand {
            margin-bottom: 0.5rem;
            padding: 0.62rem 0.75rem;
        }
        .brand-mark {
            flex-basis: 2.55rem;
            width: 2.55rem;
            height: 2.55rem;
        }
        .brand-mark::before,
        .brand-mark::after {
            width: 3.15rem;
            height: 1.2rem;
        }
        .brand-eyebrow {
            display: none;
        }
        .sidebar-section-label {
            margin-bottom: 0.22rem;
            font-size: 0.6rem;
        }
        .sidebar-section-label.data-label {
            margin-top: 0.48rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            min-height: 2.15rem;
            padding: 0.34rem 0.65rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            font-size: 0.8rem;
        }
        .dataset-card {
            padding: 0.62rem 0.7rem;
        }
        .dataset-tags {
            display: none;
        }
        .dataset-stats {
            margin-top: 0.3rem;
        }
        .dataset-stats span {
            padding: 0.3rem 0.28rem;
        }
        .dataset-hint {
            margin-top: 0.25rem;
            line-height: 1.4;
        }
        [data-testid="stSidebar"] .stButton button {
            min-height: 2.1rem;
            margin-top: 0.25rem;
        }
        .sidebar-footer {
            margin-top: 0.42rem;
            padding-top: 0.38rem;
        }
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
