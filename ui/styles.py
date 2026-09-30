"""
ui/styles.py - Visual design system for the parking terminal.

Presentation only. No business logic, OCR, or database calls live here -
this module's only job is to make the existing app look and feel like a
production terminal instead of a Streamlit dashboard.
"""

import streamlit as st

COLORS = {
    "bg":             "#F7F7F5",
    "surface":        "#FFFFFF",
    "border":         "#E6E4DF",
    "text":           "#111111",
    "muted":          "#6B6B6B",
    "faint":          "#9A9A94",
    "accent":         "#2563EB",
    "accent_dark":    "#1D4ED8",
    "accent_soft":    "#EEF3FF",
    "success":        "#16A34A",
    "success_soft":   "#ECFDF5",
    "success_border": "#BBF7D0",
    "warning":        "#B45309",
    "warning_soft":   "#FFFBEB",
    "warning_border": "#FDE68A",
    "error":          "#DC2626",
    "error_soft":     "#FEF2F2",
    "error_border":   "#FECACA",
}


def inject():
    """Inject the terminal's global stylesheet. Call once per page render."""
    c = COLORS
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class^="st-emotion"], [class*=" st-emotion"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}

    /* ---------- hide Streamlit chrome ---------- */
    #MainMenu, header[data-testid="stHeader"], footer,
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], .stAppDeployButton,
    [data-testid="stElementToolbar"] {{
        display: none !important;
    }}

    .stApp {{ background: {c['bg']}; }}
    .block-container {{
        max-width: 1080px;
        padding-top: 1.75rem;
        padding-bottom: 3rem;
    }}

    /* ---------- top bar ---------- */
    .st-key-nav_bar {{ margin-bottom: 0.75rem; }}
    .pk-wordmark {{
        font-weight: 800;
        font-size: 1.05rem;
        letter-spacing: 0.14em;
        color: {c['text']};
        padding-top: 0.5rem;
    }}
    .st-key-nav_bar .stButton > button {{
        background: transparent !important;
        border: none !important;
        color: {c['muted']} !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
        padding: 0.5rem 0.3rem !important;
    }}
    .st-key-nav_bar .stButton > button:hover {{
        color: {c['accent']} !important;
        transform: none !important;
    }}
    .pk-nav-active .stButton > button {{
        color: {c['text']} !important;
        font-weight: 700 !important;
    }}

    /* ---------- buttons ---------- */
    .stButton > button {{
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.65rem 1.5rem;
        transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
    }}
    button[data-testid="stBaseButton-primary"] {{
        background: {c['accent']} !important;
        border: 1px solid {c['accent']} !important;
        color: #fff !important;
    }}
    button[data-testid="stBaseButton-primary"]:hover {{
        background: {c['accent_dark']} !important;
        border-color: {c['accent_dark']} !important;
        transform: translateY(-1px);
    }}
    button[data-testid="stBaseButton-secondary"] {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text']} !important;
    }}
    button[data-testid="stBaseButton-secondary"]:hover {{
        border-color: {c['accent']} !important;
        color: {c['accent']} !important;
        transform: translateY(-1px);
    }}

    /* ---------- text input ---------- */
    .stTextInput input {{
        border-radius: 12px !important;
        border: 1px solid {c['border']} !important;
        padding: 0.7rem 1rem !important;
        font-size: 1.1rem !important;
        text-align: center;
        letter-spacing: 0.05em;
        font-weight: 600;
    }}
    .stTextInput input:focus {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 3px {c['accent_soft']} !important;
    }}
    .stTextInput label {{
        color: {c['muted']} !important;
        font-size: 0.85rem !important;
        justify-content: center !important;
        display: flex !important;
    }}

    /* ---------- cards ---------- */
    .pk-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 20px;
        padding: 2.25rem 2rem;
        text-align: center;
        animation: pkFadeUp 0.45s ease both;
    }}
    .pk-card-narrow {{ max-width: 440px; margin: 0 auto 1rem auto; }}

    .pk-eyebrow {{
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {c['muted']};
        margin-bottom: 0.5rem;
    }}
    .pk-title {{
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0 0 0.35rem 0;
        line-height: 1.25;
    }}
    .pk-subtitle {{
        color: {c['muted']};
        font-size: 1rem;
        margin-bottom: 0;
    }}
    .pk-plate {{
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 0.07em;
        margin: 0.8rem 0;
        font-variant-numeric: tabular-nums;
    }}
    .pk-line {{
        display: flex;
        justify-content: space-between;
        padding: 0.55rem 0;
        border-bottom: 1px solid {c['border']};
        font-size: 0.95rem;
        text-align: left;
    }}
    .pk-line:last-of-type {{ border-bottom: none; }}
    .pk-line .label {{ color: {c['muted']}; }}
    .pk-line .value {{ font-weight: 600; }}
    .pk-total {{
        display: flex; justify-content: space-between; align-items: baseline;
        margin-top: 1rem; padding-top: 1.1rem;
        border-top: 1px solid {c['border']};
    }}
    .pk-total .label {{ font-size: 1rem; color: {c['muted']}; font-weight: 600; }}
    .pk-total .value {{ font-size: 2rem; font-weight: 800; color: {c['accent']}; }}

    .pk-badge {{
        display: inline-block;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }}
    .pk-badge.success {{ background:{c['success_soft']}; color:{c['success']}; border:1px solid {c['success_border']}; }}
    .pk-badge.warning {{ background:{c['warning_soft']}; color:{c['warning']}; border:1px solid {c['warning_border']}; }}
    .pk-badge.error   {{ background:{c['error_soft']};   color:{c['error']};   border:1px solid {c['error_border']}; }}

    /* ---------- camera stage ---------- */
    .st-key-camera_stage {{
        position: relative;
        border-radius: 24px;
        overflow: hidden;
        background: #0b0b0c;
        border: 1px solid {c['border']};
        aspect-ratio: 4 / 3;
        margin: 0 auto 1.25rem auto;
    }}
    .st-key-camera_stage [data-testid="stElementContainer"] {{
        position: absolute;
        inset: 0;
    }}
    /* Fill every level between the (now absolute, full-bleed) element
       container and the <img> itself. These stay in normal flow - only the
       element container above is taken out of flow - so percentage heights
       cascade all the way down instead of collapsing to 0. */
    .st-key-camera_stage [data-testid="stFullScreenFrame"],
    .st-key-camera_stage [data-testid="stFullScreenFrame"] > div,
    .st-key-camera_stage [data-testid="stImage"],
    .st-key-camera_stage [data-testid="stImageContainer"] {{
        height: 100% !important;
        width: 100% !important;
    }}
    .st-key-camera_stage [data-testid="stImageContainer"] img {{
        width: 100%; height: 100%; object-fit: cover; display: block;
    }}

    .pk-guide {{
        position: absolute;
        top: 30%; left: 8%; right: 8%; bottom: 30%;
        pointer-events: none;
        z-index: 3;
    }}
    .pk-corner {{
        position: absolute; width: 26px; height: 26px;
        border-color: rgba(255,255,255,0.92);
        filter: drop-shadow(0 1px 3px rgba(0,0,0,0.55));
    }}
    .pk-corner.tl {{ top:0; left:0; border-top:3px solid; border-left:3px solid; border-radius:6px 0 0 0; }}
    .pk-corner.tr {{ top:0; right:0; border-top:3px solid; border-right:3px solid; border-radius:0 6px 0 0; }}
    .pk-corner.bl {{ bottom:0; left:0; border-bottom:3px solid; border-left:3px solid; border-radius:0 0 0 6px; }}
    .pk-corner.br {{ bottom:0; right:0; border-bottom:3px solid; border-right:3px solid; border-radius:0 0 6px 0; }}

    .pk-scanline {{
        position: absolute; left: 8%; right: 8%; top: 30%;
        height: 2px;
        background: linear-gradient(90deg, transparent, {c['accent']} 20%, #93c5fd 50%, {c['accent']} 80%, transparent);
        box-shadow: 0 0 8px 1px rgba(37,99,235,0.7);
        animation: pkScan 2.4s ease-in-out infinite;
        z-index: 4;
    }}

    .pk-hint {{
        position: absolute; left:0; right:0; bottom: 14px;
        text-align: center; z-index: 5;
        color: rgba(255,255,255,0.95);
        font-size: 0.85rem; font-weight: 500;
        text-shadow: 0 1px 4px rgba(0,0,0,0.6);
    }}
    .pk-dot {{
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: #93c5fd; margin-right: 7px;
        animation: pkPulse 1.4s ease-in-out infinite;
        vertical-align: middle;
    }}

    /* ---------- checkmark ---------- */
    .pk-check {{ width: 60px; height: 60px; margin: 0 auto 0.75rem auto; display: block; }}
    .pk-check circle {{
        stroke: {c['success']}; stroke-width: 2.5; fill: none;
        stroke-dasharray: 158; stroke-dashoffset: 158;
        animation: pkCircle 0.5s ease-out forwards;
    }}
    .pk-check path {{
        stroke: {c['success']}; stroke-width: 3.5; fill: none;
        stroke-linecap: round; stroke-linejoin: round;
        stroke-dasharray: 40; stroke-dashoffset: 40;
        animation: pkCheck 0.35s 0.45s ease-out forwards;
    }}

    /* ---------- availability ---------- */
    .pk-availnum {{
        font-size: 3.2rem; font-weight: 800; line-height: 1;
        color: {c['text']};
    }}
    .pk-slotgrid {{
        display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
        margin-top: 0.4rem;
    }}
    .pk-slot {{ width: 15px; height: 15px; border-radius: 50%; }}
    .pk-slot.open     {{ background: {c['surface']}; border: 1.5px solid #C9C7C1; }}
    .pk-slot.occupied {{ background: {c['text']}; }}
    .pk-zone-label {{
        color: {c['muted']}; font-size: 0.8rem; font-weight: 600;
        letter-spacing: 0.08em; margin: 1rem 0 0.35rem 0; text-transform: uppercase;
    }}

    /* ---------- tabs (Operator page) ---------- */
    button[data-baseweb="tab"] {{
        color: {c['muted']} !important;
        font-weight: 500 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {c['text']} !important;
        font-weight: 700 !important;
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {c['accent']} !important;
    }}

    /* ---------- misc ---------- */
    hr {{ border-color: {c['border']}; }}
    [data-testid="stMetric"] {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 0.9rem 1rem;
    }}
    .pk-footnote {{
        text-align:center; color:{c['faint']}; font-size:0.8rem; margin-top:0.75rem;
    }}

    @keyframes pkFadeUp {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pkScan {{
        0%   {{ top: 30%; opacity: 0; }}
        12%  {{ opacity: 1; }}
        50%  {{ top: 68%; opacity: 1; }}
        62%  {{ opacity: 0; }}
        100% {{ top: 30%; opacity: 0; }}
    }}
    @keyframes pkPulse {{
        0%, 100% {{ opacity: 0.4; transform: scale(0.85); }}
        50%      {{ opacity: 1;   transform: scale(1.15); }}
    }}
    @keyframes pkCircle {{ to {{ stroke-dashoffset: 0; }} }}
    @keyframes pkCheck  {{ to {{ stroke-dashoffset: 0; }} }}

    @media (max-width: 640px) {{
        .pk-title {{ font-size: 1.3rem; }}
        .pk-plate {{ font-size: 1.5rem; }}
        .pk-availnum {{ font-size: 2.4rem; }}
    }}
    </style>
    """, unsafe_allow_html=True)
