"""
ui/components.py - Reusable customer-facing UI blocks for the parking terminal.

Presentation only: every function here just renders markup from plain values
it is given. None of them touch the camera, YOLO, EasyOCR, plate_ocr, or the
database - that logic stays in streamlit_app.py exactly as it worked before.
"""

import re
import streamlit as st


def _md(html: str):
    """
    Render raw HTML through st.markdown safely.

    Streamlit's markdown parser still applies standard Markdown rules before
    passing HTML through: 4+ leading spaces on a line is read as a fenced
    code block. Python source indentation inside a triple-quoted f-string
    would otherwise trigger that, so every line is stripped first.
    """
    st.markdown(
        "\n".join(line.strip() for line in html.strip().splitlines()),
        unsafe_allow_html=True,
    )


# ── formatting helpers ──────────────────────────────────────────────

def plate_pretty(plate: str) -> str:
    """'MH12AB1234' -> 'MH 12 AB 1234' (falls back to the raw string)."""
    if not plate:
        return ""
    parts = re.findall(r"[A-Z]+|[0-9]+", plate.upper())
    return " ".join(parts) if parts else plate


def format_duration(total_seconds) -> str:
    """1234 -> '20m'; 7384 -> '2h 3m'."""
    total_seconds = max(0, int(total_seconds or 0))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m"
    return f"{s}s"


# ── top bar ──────────────────────────────────────────────────────────

def render_topbar(current_page: str):
    """Minimal wordmark + three quiet text links. No sidebar, no big nav."""
    with st.container(key="nav_bar"):
        col_brand, col_a, col_b, col_c = st.columns([4, 1, 1, 1])
        with col_brand:
            _md("<div class='pk-wordmark'>PARKING</div>")
        with col_a:
            if st.button("Terminal", key="nav_terminal", width="stretch"):
                st.session_state.page = "Scan"
        with col_b:
            if st.button("Availability", key="nav_avail", width="stretch"):
                st.session_state.page = "Availability"
        with col_c:
            if st.button("Operator", key="nav_operator", width="stretch"):
                st.session_state.page = "Operator"


# ── camera stage ─────────────────────────────────────────────────────

def camera_stage(slot):
    """
    Render the camera frame chrome (rounded stage, corner guide, animated
    scan line, hint caption) into `slot` (an st.empty()) and return the
    image placeholder the caller should update every frame.

    Purely visual - the camera capture / YOLO / OCR loop lives in the caller.
    """
    with slot.container(key="camera_stage"):
        frame_ph = st.empty()
        _md("""
            <div class="pk-guide">
                <div class="pk-corner tl"></div>
                <div class="pk-corner tr"></div>
                <div class="pk-corner bl"></div>
                <div class="pk-corner br"></div>
            </div>
            <div class="pk-scanline"></div>
            <div class="pk-hint"><span class="pk-dot"></span>Position your plate inside the frame</div>
        """)
    return frame_ph


# ── check icon ───────────────────────────────────────────────────────

_CHECK_SVG = (
    '<svg class="pk-check" viewBox="0 0 52 52">'
    '<circle cx="26" cy="26" r="23" />'
    '<path d="M14.5 27.2l7.2 7.2 15.8-15.8" />'
    '</svg>'
)


# ── state cards ──────────────────────────────────────────────────────

def entry_success_card(plate: str, slot_number: str, entry_time_str: str):
    _md(f"""
        <div class="pk-card pk-card-narrow">
            {_CHECK_SVG}
            <div class="pk-title">You're all set</div>
            <div class="pk-plate">{plate_pretty(plate)}</div>
            <div class="pk-line"><span class="label">Parking slot</span><span class="value">{slot_number}</span></div>
            <div class="pk-line"><span class="label">Entry time</span><span class="value">{entry_time_str}</span></div>
        </div>
        <div class="pk-footnote">Have a great day.</div>
    """)


def exit_billing_card(plate: str, duration_str: str, base_amount: float,
                       peak_amount: float, total_amount: float, is_rush: bool):
    peak_row = ""
    if peak_amount and peak_amount > 0:
        peak_row = (
            f'<div class="pk-line"><span class="label">Peak-hour adjustment</span>'
            f'<span class="value">₹{peak_amount:.2f}</span></div>'
        )
    rush_badge = (
        '<div class="pk-badge warning">Peak-hour pricing applied</div>' if is_rush else ""
    )
    _md(f"""
        <div class="pk-card pk-card-narrow">
            <div class="pk-eyebrow">Parking summary</div>
            <div class="pk-plate">{plate_pretty(plate)}</div>
            {rush_badge}
            <div class="pk-line"><span class="label">Duration</span><span class="value">{duration_str}</span></div>
            <div class="pk-line"><span class="label">Parking</span><span class="value">₹{base_amount:.2f}</span></div>
            {peak_row}
            <div class="pk-total"><span class="label">Total due</span><span class="value">₹{total_amount:.2f}</span></div>
        </div>
    """)


def welcome_card(subtitle: str = "Scan your vehicle"):
    _md(f"""
        <div style="text-align:center; margin-bottom: 1.5rem;">
            <div class="pk-eyebrow">Parking</div>
            <div class="pk-title" style="font-size:1.9rem;">{subtitle}</div>
            <div class="pk-subtitle">Position your number plate in front of the camera</div>
        </div>
    """)


def plate_detected_banner(plate: str):
    _md(f"""
        <div class="pk-card pk-card-narrow" style="padding: 1.5rem 2rem;">
            <div class="pk-eyebrow">Vehicle detected</div>
            <div class="pk-plate">{plate_pretty(plate)}</div>
        </div>
    """)


def info_card(title: str, message: str, tone: str = "warning"):
    """Generic single-message card. tone: warning | error | success."""
    _md(f"""
        <div class="pk-card pk-card-narrow">
            <div class="pk-title" style="font-size:1.3rem;">{title}</div>
            <div class="pk-subtitle">{message}</div>
        </div>
    """)


def no_plate_card():
    info_card(
        "We couldn't read your plate",
        "Please position your vehicle so the plate is clearly visible and try again.",
    )


def service_unavailable_card():
    info_card(
        "We're unable to process entries right now",
        "Please ask the parking attendant for assistance.",
        tone="error",
    )


def duplicate_scan_card(plate: str):
    info_card(
        "Already checked in",
        f"{plate_pretty(plate)} was just processed a moment ago. "
        "Please scan again shortly to check out.",
    )


def processing_failed_card():
    info_card(
        "We couldn't complete that request",
        "Please try again, or ask the parking attendant for help.",
        tone="error",
    )


def manual_entry_block(prefill: str = ""):
    """
    Elegant fallback text entry. Returns (submitted: bool, value: str).
    Assigning `prefill` to the widget key must happen before the widget is
    created, or Streamlit ignores it - callers should do that themselves
    right before invoking this (kept out of here so it stays a pure render).
    """
    _md(
        "<div style='text-align:center; color:#6B6B6B; font-size:0.9rem; "
        "margin-bottom:0.5rem;'>Can't scan your plate? Enter it manually</div>"
    )
    value = st.text_input(
        "Number plate", placeholder="MH 12 AB 1234", key="manual_input",
        label_visibility="collapsed",
    )
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        submitted = st.button("Continue", type="primary", width="stretch",
                              key="manual_submit")
    return submitted, value


# ── availability ─────────────────────────────────────────────────────

def availability_summary(available: int, total: int):
    _md(f"""
        <div style="text-align:center; margin: 0.5rem 0 1.5rem 0;">
            <div class="pk-availnum">{available}</div>
            <div class="pk-subtitle">of {total} spaces available</div>
        </div>
    """)


def slot_grid_by_zone(slots: list):
    """slots: list of dicts with 'zone' and 'status'. Minimal dot grid."""
    zones = {}
    for s in slots:
        zones.setdefault(s.get("zone", "?"), []).append(s)

    html = ['<div class="pk-card">']
    for zone in sorted(zones):
        html.append(f'<div class="pk-zone-label">Zone {zone}</div><div class="pk-slotgrid">')
        for s in zones[zone]:
            cls = "occupied" if s.get("status") == "OCCUPIED" else "open"
            html.append(f'<div class="pk-slot {cls}" title="Slot {s.get("slot_number","")}"></div>')
        html.append("</div>")
    html.append("</div>")
    _md("".join(html))
    _md('<div class="pk-footnote">● occupied &nbsp;&nbsp; ○ available</div>')
