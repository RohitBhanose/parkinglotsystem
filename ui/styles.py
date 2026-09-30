"""
ui/styles.py - Visual design system for the parking terminal.

Matches the Material Design 3 dark/amber "DBMS console" reference supplied
by the user (Google Stitch export: Image 2/4/6/8.html) - same palette,
Space Grotesk + Inter type, Material Symbols icons, tight border radii and
technical/telemetry visual language. Presentation only: no business logic,
OCR, or database calls live here.

Every text-bearing rule sets its own `color` explicitly rather than relying
on inheritance, so the page renders the same regardless of the visitor's
browser/OS light-vs-dark preference.
"""

import streamlit as st

COLORS = {
    "bg":              "#111417",   # surface / background
    "surface_lowest":  "#0b0e11",   # header/footer bar
    "surface_low":     "#191c1f",   # primary card background
    "surface":         "#1d2023",   # secondary card / pill background
    "surface_high":    "#272a2d",   # hover / raised chip background
    "surface_highest": "#323538",   # borders, dividers, inactive chips
    "text":            "#e1e2e6",   # on-surface
    "muted":           "#b9c9d3",   # secondary
    "variant":         "#d4c4b0",   # on-surface-variant
    "faint":           "#9d8f7c",   # outline
    "accent":          "#ffc665",   # primary (amber)
    "accent_container":"#e5a93c",   # primary-container (hover/deep)
    "on_accent":       "#432c00",   # on-primary
    "accent_soft":     "rgba(255,198,101,0.12)",
    "tertiary":        "#afd2ff",   # vacant / info blue
    "tertiary_soft":   "rgba(175,210,255,0.12)",
    "error":           "#ffb4ab",
    "error_soft":      "rgba(255,180,171,0.12)",
}


def inject():
    """Inject the terminal's global stylesheet. Call once per page render."""
    c = COLORS
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

    html, body, .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}

    .material-symbols-outlined {{
        font-family: 'Material Symbols Outlined';
        font-weight: normal;
        font-style: normal;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        vertical-align: middle;
    }}

    /* ---------- hide Streamlit chrome ---------- */
    #MainMenu, header[data-testid="stHeader"], footer,
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], .stAppDeployButton,
    [data-testid="stElementToolbar"] {{
        display: none !important;
    }}

    html, body {{ background: {c['bg']} !important; }}
    .stApp {{ background: {c['bg']} !important; color: {c['text']}; }}
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label {{ color: {c['text']}; }}
    .block-container {{
        max-width: 1200px;
        padding-top: 1.25rem;
        padding-bottom: 3rem;
    }}

    /* ---------- top bar ---------- */
    .st-key-nav_bar {{
        background: {c['surface_lowest']};
        border: 1px solid {c['surface_highest']};
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        margin-bottom: 1.25rem;
    }}
    .pk-wordmark {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.12em;
        color: {c['text']} !important;
        padding-top: 0.4rem;
        text-transform: uppercase;
    }}
    .st-key-nav_bar .stButton > button {{
        background: transparent !important;
        border: 1px solid transparent !important;
        color: {c['muted']} !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border-radius: 4px !important;
        box-shadow: none !important;
        padding: 0.4rem 0.85rem !important;
        white-space: nowrap !important;
    }}
    .st-key-nav_bar .stButton > button p {{ white-space: nowrap !important; }}
    @media (max-width: 900px) {{
        .st-key-nav_bar .stButton > button {{
            font-size: 0.7rem !important;
            padding: 0.4rem 0.4rem !important;
        }}
    }}
    .st-key-nav_bar .stButton > button:hover {{
        color: {c['text']} !important;
        background: {c['surface']} !important;
    }}
    [class*="st-key-navitem_"][class*="_active"] .stButton > button {{
        background: {c['surface_high']} !important;
        color: {c['accent']} !important;
        border: 1px solid {c['surface_highest']} !important;
    }}
    [class*="st-key-navitem_"][class*="_active"] .stButton > button p {{
        color: {c['accent']} !important;
    }}
    .pk-status-pill {{
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: {c['surface']}; border: 1px solid {c['surface_highest']};
        padding: 0.35rem 0.75rem; border-radius: 4px;
        font-family: 'Space Grotesk', sans-serif; font-size: 0.7rem;
        font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
        color: {c['accent']} !important;
    }}
    .pk-dot {{
        display: inline-block; width: 7px; height: 7px; border-radius: 50%;
        background: {c['accent']}; animation: pkPulse 1.6s ease-in-out infinite;
    }}
    .pk-dot.error {{ background: {c['error']}; }}

    /* ---------- buttons ---------- */
    .stButton > button {{
        border-radius: 6px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.6rem 1.4rem;
        transition: transform 0.12s ease, background 0.15s ease, border-color 0.15s ease;
    }}
    button[data-testid="stBaseButton-primary"] {{
        background: {c['accent']} !important;
        border: 1px solid {c['accent']} !important;
        color: {c['on_accent']} !important;
    }}
    button[data-testid="stBaseButton-primary"] p {{ color: {c['on_accent']} !important; font-weight: 700 !important; }}
    button[data-testid="stBaseButton-primary"]:hover {{
        background: {c['accent_container']} !important;
        border-color: {c['accent_container']} !important;
        transform: translateY(-1px);
    }}
    button[data-testid="stBaseButton-secondary"] {{
        background: {c['surface_high']} !important;
        border: 1px solid {c['surface_highest']} !important;
        color: {c['text']} !important;
    }}
    button[data-testid="stBaseButton-secondary"] p {{ color: {c['text']} !important; }}
    button[data-testid="stBaseButton-secondary"]:hover {{
        border-color: {c['accent']} !important;
        color: {c['accent']} !important;
    }}
    button[data-testid="stBaseButton-secondary"]:hover p {{ color: {c['accent']} !important; }}

    /* ---------- text input ---------- */
    .stTextInput input {{
        background: {c['surface_lowest']} !important;
        border-radius: 6px !important;
        border: 1px solid {c['surface_highest']} !important;
        color: {c['text']} !important;
        padding: 0.65rem 1rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.04em;
        font-weight: 600;
    }}
    .stTextInput input::placeholder {{ color: {c['faint']} !important; opacity: 0.7; }}
    .stTextInput input:focus {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 3px {c['accent_soft']} !important;
    }}
    .stTextInput label, .stTextInput label p {{
        color: {c['muted']} !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}

    /* ---------- generic cards ---------- */
    .pk-card {{
        background: {c['surface_low']};
        border: 1px solid {c['surface_highest']};
        border-radius: 8px;
        padding: 1.25rem;
    }}
    .pk-card-pad-lg {{ padding: 1.75rem; }}

    .pk-eyebrow {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase;
        color: {c['accent']} !important;
        display: flex; align-items: center; gap: 0.4rem;
        margin-bottom: 0.35rem;
    }}
    .pk-h1 {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.9rem; font-weight: 700; letter-spacing: -0.01em;
        color: {c['text']} !important; margin: 0;
    }}
    .pk-h2 {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.15rem; font-weight: 600;
        color: {c['text']} !important; margin: 0;
    }}
    .pk-muted {{ color: {c['muted']} !important; font-size: 0.85rem; }}
    .pk-mono {{ font-family: 'Space Grotesk', sans-serif; letter-spacing: 0.03em; }}

    /* Stat card (dashboard) */
    .pk-stat {{
        background: {c['surface_low']}; border: 1px solid {c['surface_highest']};
        border-radius: 8px; padding: 1.1rem 1.25rem;
        display: flex; flex-direction: column; gap: 0.6rem;
    }}
    .pk-stat.accent {{ background: {c['surface']}; border-color: {c['surface_highest']}; }}
    .pk-stat-head {{ display: flex; align-items: center; justify-content: space-between; }}
    .pk-stat-label {{
        font-family: 'Space Grotesk', sans-serif; font-size: 0.68rem; font-weight: 700;
        letter-spacing: 0.1em; text-transform: uppercase; color: {c['muted']} !important;
    }}
    .pk-stat.accent .pk-stat-label {{ color: {c['accent']} !important; }}
    .pk-stat-icon {{ color: {c['muted']} !important; font-size: 20px; }}
    .pk-stat.accent .pk-stat-icon {{ color: {c['accent']} !important; }}
    .pk-stat-value {{ display: flex; align-items: baseline; gap: 0.4rem; }}
    .pk-stat-value .num {{
        font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700;
        color: {c['text']} !important;
    }}
    .pk-stat.accent .pk-stat-value .num {{ color: {c['accent']} !important; }}
    .pk-stat-value .unit {{ font-size: 0.78rem; color: {c['muted']} !important; }}
    .pk-stat-foot {{ font-size: 0.78rem; color: {c['muted']} !important; }}

    /* Utilization bar */
    .pk-barwrap {{
        width: 100%; height: 10px; background: {c['surface_highest']};
        border-radius: 999px; overflow: hidden;
    }}
    .pk-barfill {{ height: 100%; background: {c['accent']}; border-radius: 999px; }}

    /* Activity feed row */
    .pk-activity-row {{
        display: grid; grid-template-columns: 90px 110px 90px 1fr;
        gap: 0.5rem; align-items: center; padding: 0.6rem 0.5rem;
        border-radius: 4px; font-size: 0.85rem;
    }}
    .pk-activity-row:nth-child(even) {{ background: {c['surface_lowest']}; }}
    .pk-activity-time {{ font-family: 'Space Grotesk', sans-serif; color: {c['muted']} !important; font-size: 0.78rem; }}
    .pk-activity-plate {{ font-family: 'Space Grotesk', sans-serif; color: {c['text']} !important; letter-spacing: 0.05em; font-weight: 600; }}
    .pk-activity-detail {{ color: {c['muted']} !important; font-size: 0.82rem; }}
    .pk-activity-detail b {{ color: {c['text']} !important; }}

    .pk-badge {{
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.2rem 0.55rem; border-radius: 4px;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    }}
    .pk-badge.entered  {{ background: {c['surface_highest']}; color: {c['accent']} !important; }}
    .pk-badge.exited   {{ background: {c['surface']}; color: {c['muted']} !important; }}
    .pk-badge.active   {{ background: {c['accent_soft']}; color: {c['accent']} !important; }}
    .pk-badge.completed{{ background: {c['surface_highest']}; color: {c['muted']} !important; }}
    .pk-badge.rush     {{ background: {c['accent_soft']}; color: {c['accent']} !important; }}
    .pk-badge.standard {{ background: {c['surface_highest']}; color: {c['muted']} !important; }}

    /* Action link (dashboard quick actions) */
    .pk-action {{
        display: flex; align-items: center; justify-content: space-between;
        background: {c['surface_high']}; border-radius: 6px; padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
    }}
    .pk-action-left {{ display: flex; align-items: center; gap: 0.75rem; }}
    .pk-action-icon {{
        width: 36px; height: 36px; border-radius: 6px; background: {c['surface']};
        display: flex; align-items: center; justify-content: center; color: {c['accent']} !important;
    }}
    .pk-action-title {{ font-weight: 600; color: {c['text']} !important; font-size: 0.9rem; }}
    .pk-action-sub {{ color: {c['muted']} !important; font-size: 0.78rem; }}

    /* ---------- camera stage ---------- */
    .st-key-camera_stage {{
        position: relative;
        border-radius: 8px;
        overflow: hidden;
        background: #000000;
        border: 1px solid {c['surface_highest']};
        aspect-ratio: 16 / 10;
        margin: 0 auto;
    }}
    .st-key-camera_stage [data-testid="stElementContainer"] {{ position: absolute; inset: 0; }}
    .st-key-camera_stage [data-testid="stFullScreenFrame"],
    .st-key-camera_stage [data-testid="stFullScreenFrame"] > div,
    .st-key-camera_stage [data-testid="stImage"],
    .st-key-camera_stage [data-testid="stImageContainer"] {{
        height: 100% !important; width: 100% !important;
    }}
    .st-key-camera_stage [data-testid="stImageContainer"] img {{
        width: 100%; height: 100%; object-fit: cover; display: block;
    }}
    .pk-guide {{ position: absolute; top: 30%; left: 15%; right: 15%; bottom: 30%; pointer-events: none; z-index: 3; }}
    .pk-corner {{ position: absolute; width: 24px; height: 24px; border-color: {c['accent']}; }}
    .pk-corner.tl {{ top:0; left:0; border-top:2px solid; border-left:2px solid; }}
    .pk-corner.tr {{ top:0; right:0; border-top:2px solid; border-right:2px solid; }}
    .pk-corner.bl {{ bottom:0; left:0; border-bottom:2px solid; border-left:2px solid; }}
    .pk-corner.br {{ bottom:0; right:0; border-bottom:2px solid; border-right:2px solid; }}
    .pk-scanline {{
        position: absolute; left: 15%; right: 15%; top: 30%; height: 2px;
        background: {c['accent']}; box-shadow: 0 0 10px 1px rgba(255,198,101,0.8);
        animation: pkScan 2.4s ease-in-out infinite; z-index: 4;
    }}
    .pk-hint {{
        position: absolute; left:0; right:0; bottom: 12px; text-align: center; z-index: 5;
        font-family: 'Space Grotesk', sans-serif;
        color: {c['text']} !important; font-size: 0.75rem; font-weight: 600;
        letter-spacing: 0.08em; text-transform: uppercase;
    }}
    .pk-cam-tag {{
        position: absolute; top: 10px; left: 10px; z-index: 5;
        background: rgba(11,14,17,0.85); padding: 0.3rem 0.6rem; border-radius: 4px;
        font-family: 'Space Grotesk', sans-serif; font-size: 0.68rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase; color: {c['text']} !important;
        display: flex; align-items: center; gap: 0.35rem;
    }}
    .pk-cam-tag .material-symbols-outlined {{ font-size: 14px; color: {c['accent']} !important; }}
    .pk-live-tag {{
        position: absolute; top: 10px; right: 10px; z-index: 5;
        background: rgba(11,14,17,0.85); padding: 0.3rem 0.6rem; border-radius: 4px;
        font-family: 'Space Grotesk', sans-serif; font-size: 0.68rem; font-weight: 700;
        letter-spacing: 0.1em; text-transform: uppercase; color: {c['accent']} !important;
    }}

    /* Plate / slot readout blocks */
    .pk-readout {{
        background: {c['surface']}; border-radius: 8px; padding: 1rem 1.25rem;
        display: flex; align-items: center; gap: 1rem;
    }}
    .pk-readout-icon {{
        width: 44px; height: 44px; border-radius: 8px; background: {c['surface_high']};
        display: flex; align-items: center; justify-content: center; color: {c['accent']} !important;
        font-size: 26px; flex-shrink: 0;
    }}
    .pk-readout-plate {{
        font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700;
        letter-spacing: 0.06em; color: {c['text']} !important;
    }}
    .pk-slotbox {{
        background: {c['surface']}; border-radius: 8px; padding: 1.4rem;
        display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.3rem;
    }}
    .pk-slotbox .num {{
        font-family: 'Space Grotesk', sans-serif; font-size: 2.6rem; font-weight: 700;
        color: {c['accent']} !important; letter-spacing: -0.01em; line-height: 1.1;
    }}
    .pk-kv-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }}
    .pk-kv {{ background: {c['surface']}; border-radius: 6px; padding: 0.75rem 0.9rem; display: flex; flex-direction: column; gap: 0.25rem; }}
    .pk-kv-label {{ font-family: 'Space Grotesk', sans-serif; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: {c['muted']} !important; }}
    .pk-kv-value {{ font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 600; color: {c['text']} !important; }}

    .pk-fareline {{ display: flex; justify-content: space-between; padding: 0.4rem 0; font-size: 0.88rem; color: {c['text']} !important; }}
    .pk-fareline .lbl {{ color: {c['muted']} !important; }}
    .pk-farerush {{ color: {c['accent']} !important; display: flex; align-items: center; gap: 0.3rem; }}
    .pk-faretotal {{
        display: flex; justify-content: space-between; align-items: baseline;
        padding-top: 0.7rem; margin-top: 0.5rem; border-top: 1px solid {c['surface_highest']};
    }}
    .pk-faretotal .lbl {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; text-transform: uppercase; font-size: 0.8rem; color: {c['text']} !important; }}
    .pk-faretotal .val {{ font-family: 'Space Grotesk', sans-serif; font-size: 1.7rem; font-weight: 700; color: {c['accent']} !important; }}

    .pk-confirm-box {{
        background: {c['surface_high']}; border-radius: 6px; padding: 0.85rem 1rem;
        display: flex; align-items: center; gap: 0.85rem;
    }}
    .pk-confirm-icon {{
        width: 34px; height: 34px; border-radius: 50%; background: {c['accent']};
        color: {c['on_accent']} !important; display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; font-size: 18px;
    }}
    .pk-confirm-title {{ font-weight: 700; color: {c['text']} !important; font-size: 0.9rem; }}
    .pk-confirm-sub {{ color: {c['muted']} !important; font-size: 0.78rem; }}

    /* ---------- slot grid (Map page) ---------- */
    .pk-zone-head {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.5rem 0.25rem; margin-top: 0.5rem;
    }}
    .pk-zone-title {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: {c['text']} !important; font-size: 1rem; }}
    .pk-zone-sub {{ font-family: 'Space Grotesk', sans-serif; color: {c['muted']} !important; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }}

    .st-key-slotgrid .stButton > button {{
        height: 4.4rem; width: 100%;
        background: {c['surface_lowest']} !important;
        border: 1px solid {c['surface_highest']} !important;
        border-radius: 6px !important;
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important;
        font-family: 'Space Grotesk', sans-serif !important;
        padding: 0.3rem !important;
        white-space: pre-line !important;
        line-height: 1.25 !important;
    }}
    .st-key-slotgrid .stButton > button p {{ white-space: pre-line !important; }}
    .st-key-slotgrid .pk-slot-occupied .stButton > button {{
        background: {c['surface']} !important;
        color: {c['accent']} !important;
        border-color: {c['surface_highest']} !important;
    }}
    .st-key-slotgrid .pk-slot-available .stButton > button {{
        color: {c['tertiary']} !important;
    }}
    .st-key-slotgrid .pk-slot-maintenance .stButton > button {{
        color: {c['error']} !important;
        border-style: dashed !important;
    }}
    .st-key-slotgrid .pk-slot-selected .stButton > button {{
        border: 2px solid {c['accent']} !important;
        box-shadow: 0 0 0 2px {c['accent_soft']};
    }}

    /* ---------- tabs ---------- */
    button[data-baseweb="tab"] {{ color: {c['muted']} !important; }}
    button[data-baseweb="tab"] p {{ color: inherit !important; font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {c['accent']} !important; }}
    div[data-baseweb="tab-highlight"] {{ background-color: {c['accent']} !important; }}
    div[data-baseweb="tab-border"] {{ background-color: {c['surface_highest']} !important; }}

    /* ---------- dataframes / metrics ---------- */
    [data-testid="stDataFrame"] {{ border: 1px solid {c['surface_highest']}; border-radius: 8px; overflow: hidden; }}
    [data-testid="stMetric"] {{
        background: {c['surface_low']}; border: 1px solid {c['surface_highest']};
        border-radius: 8px; padding: 0.9rem 1rem;
    }}
    [data-testid="stMetric"] label, [data-testid="stMetricLabel"] {{ color: {c['muted']} !important; }}
    [data-testid="stMetricValue"] {{ color: {c['text']} !important; font-family: 'Space Grotesk', sans-serif !important; }}

    /* ---------- records table ---------- */
    .pk-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    .pk-table th {{
        text-align: left; font-family: 'Space Grotesk', sans-serif; font-size: 0.65rem;
        font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: {c['muted']} !important;
        background: {c['surface_lowest']}; padding: 0.6rem 0.75rem; border-bottom: 1px solid {c['surface_highest']};
    }}
    .pk-table td {{ padding: 0.6rem 0.75rem; border-bottom: 1px solid {c['surface']}; color: {c['text']} !important; }}
    .pk-table tr:hover td {{ background: {c['surface']}; }}
    .pk-table .mono {{ font-family: 'Space Grotesk', sans-serif; color: {c['muted']} !important; font-size: 0.8rem; }}
    .pk-table .plate {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; letter-spacing: 0.04em; }}

    hr {{ border-color: {c['surface_highest']}; }}
    .pk-footnote {{ text-align:center; color:{c['faint']} !important; font-size:0.78rem; margin-top:0.75rem; }}

    @keyframes pkScan {{
        0%   {{ top: 30%; opacity: 0; }}
        12%  {{ opacity: 1; }}
        50%  {{ top: 68%; opacity: 1; }}
        62%  {{ opacity: 0; }}
        100% {{ top: 30%; opacity: 0; }}
    }}
    @keyframes pkPulse {{
        0%, 100% {{ opacity: 0.5; }}
        50%      {{ opacity: 1; }}
    }}

    @media (max-width: 640px) {{
        .pk-h1 {{ font-size: 1.4rem; }}
        .pk-activity-row {{ grid-template-columns: 1fr; }}
    }}
    </style>
    """, unsafe_allow_html=True)
