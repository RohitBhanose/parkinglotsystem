"""
ui/components.py - Reusable UI blocks matching the Material-3 dark/amber
"DBMS console" reference design (Image 2/4/6/8.html).

Presentation only: every function here renders markup from the plain values
it is given. None of them touch the camera, YOLO, EasyOCR, plate_ocr, or the
database - that logic stays in streamlit_app.py. Every value rendered here
must come from a real storage-backend call or a real computed value - no placeholder
sensor counts, camera names, or hardware telemetry that this project doesn't
actually have.
"""

import re
import streamlit as st

from ui.styles import COLORS


def _md(html: str):
    """
    Render raw HTML through st.markdown safely.

    Streamlit's markdown parser reads 4+ leading spaces as a fenced code
    block even with unsafe_allow_html=True, so every line is stripped first -
    otherwise Python's own source indentation inside an f-string would corrupt
    the output.
    """
    st.markdown(
        "\n".join(line.strip() for line in html.strip().splitlines()),
        unsafe_allow_html=True,
    )


def icon(name: str, size: int = 20, extra_style: str = "") -> str:
    """Inline Material Symbols icon span."""
    return (
        f'<span class="material-symbols-outlined" '
        f'style="font-size:{size}px;{extra_style}">{name}</span>'
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

NAV_ITEMS = [("Dashboard", "space_dashboard"), ("Parking", "sensor_door"),
             ("Map", "map"), ("Records", "receipt_long")]


def render_topbar(current_page: str, db_ok: bool):
    """Header bar: wordmark, pill nav matching the reference exactly, status pill."""
    with st.container(key="nav_bar"):
        col_brand, col_nav, col_status = st.columns([2, 4, 2])
        with col_brand:
            _md(f"<div class='pk-wordmark'>{icon('local_parking', 20)} PARK-DBMS</div>")
        with col_nav:
            cols = st.columns(len(NAV_ITEMS))
            for col, (label, ico) in zip(cols, NAV_ITEMS):
                with col:
                    # st.markdown's own opening/closing tags don't actually
                    # nest around the button (each markdown call is its own
                    # HTML fragment, parsed and auto-closed independently) -
                    # so the active-state wrapper has to be a real container,
                    # whose key becomes a stable, targetable CSS class.
                    # NOTE: no st.rerun() here - calling it inside this
                    # per-item loop (each iteration wrapped in its own
                    # dynamically-keyed container) was observed to leave
                    # navigation stuck on the current page in the real
                    # browser, even though it behaved correctly under
                    # AppTest. Streamlit already reruns automatically after
                    # a button click, so the page switch itself works fine
                    # without it - the only cost is that this item's own
                    # highlight reflects the click one render later.
                    state = "active" if current_page == label else "idle"
                    with st.container(key=f"navitem_{label.lower()}_{state}"):
                        if st.button(label, key=f"nav_{label.lower()}", width="stretch"):
                            st.session_state.page = label
        with col_status:
            dot_cls = "" if db_ok else "error"
            label = "SYSTEM ONLINE" if db_ok else "DB OFFLINE"
            _md(
                f"<div style='text-align:right;padding-top:0.35rem;'>"
                f"<span class='pk-status-pill'><span class='pk-dot {dot_cls}'></span>{label}</span>"
                f"</div>"
            )


# ── dashboard: stat cards ───────────────────────────────────────────

def stat_card(label: str, value, unit: str, sub: str, ico: str, accent: bool = False):
    cls = "pk-stat accent" if accent else "pk-stat"
    _md(f"""
        <div class="{cls}">
            <div class="pk-stat-head">
                <span class="pk-stat-label">{label}</span>
                {icon(ico, 20, "color:inherit;")}
            </div>
            <div class="pk-stat-value"><span class="num">{value}</span><span class="unit">{unit}</span></div>
            <div class="pk-stat-foot">{sub}</div>
        </div>
    """)


def utilization_bar(occupied: int, total: int):
    pct = round((occupied / total) * 100) if total else 0
    _md(f"""
        <div class="pk-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
                <span class="pk-h2">Overall Lot Density</span>
                <span class="pk-muted pk-mono">{pct}% utilized</span>
            </div>
            <div class="pk-barwrap"><div class="pk-barfill" style="width:{pct}%;"></div></div>
            <div style="display:flex;gap:1.25rem;margin-top:0.6rem;">
                <span class="pk-muted">{icon('square', 12, f'color:{COLORS["accent"]};vertical-align:middle;')} {occupied} Occupied</span>
                <span class="pk-muted">{icon('square', 12, f'color:{COLORS["surface_highest"]};vertical-align:middle;')} {total - occupied} Vacant</span>
            </div>
        </div>
    """)


def activity_feed(records: list):
    """
    records: list of dicts with number_plate, slot_number, entry_time,
    exit_time, total_fare, session_status - straight from
    db.get_parking_records(), most recent first, already sliced by the
    caller.
    """
    rows = ['<div class="pk-card"><div class="pk-h2" style="margin-bottom:0.75rem;">Real-Time Access Log</div>']
    if not records:
        rows.append('<div class="pk-muted">No activity recorded yet.</div>')
    for r in records:
        exited = r.get("exit_time") is not None
        ts = r.get("exit_time") or r.get("entry_time")
        time_str = ts.strftime("%H:%M:%S") if ts else "--:--:--"
        plate = plate_pretty(r.get("number_plate", ""))
        if exited:
            fare = r.get("total_fare")
            detail = f"Settled Fare: <b>₹{float(fare):.2f}</b>" if fare is not None else "Settled"
            badge = '<span class="pk-badge exited">EXITED</span>'
        else:
            slot = r.get("slot_number", "-")
            detail = f"Assigned Slot: <b>{slot}</b>"
            badge = '<span class="pk-badge entered">ENTERED</span>'
        rows.append(f"""
            <div class="pk-activity-row">
                <span class="pk-activity-time">{time_str}</span>
                <span class="pk-activity-plate">{plate}</span>
                <span>{badge}</span>
                <span class="pk-activity-detail">{detail}</span>
            </div>
        """)
    rows.append("</div>")
    _md("".join(rows))


def action_link(title: str, sub: str, ico: str):
    _md(f"""
        <div class="pk-action">
            <div class="pk-action-left">
                <div class="pk-action-icon">{icon(ico, 20)}</div>
                <div>
                    <div class="pk-action-title">{title}</div>
                    <div class="pk-action-sub">{sub}</div>
                </div>
            </div>
            {icon('chevron_right', 18, f'color:{COLORS["muted"]};')}
        </div>
    """)


def system_status_box(db_ok: bool, db_info: str, model_ready: bool,
                      storage_label: str = "MySQL", core_ok: bool = True):
    _md(f"""
        <div class="pk-card" style="font-family:'Space Grotesk',sans-serif;">
            <div style="display:flex;justify-content:space-between;color:{COLORS['muted']};
                        font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
                        padding-bottom:0.5rem;border-bottom:1px solid {COLORS['surface_highest']};margin-bottom:0.5rem;">
                <span>System Status</span>
                <span style="color:{COLORS['accent']};">{'STABLE' if db_ok and model_ready and core_ok else 'DEGRADED'}</span>
            </div>
            <div class="pk-fareline"><span class="lbl">{storage_label} Storage:</span>
                <span>{'CONNECTED' if db_ok else 'UNAVAILABLE'}</span></div>
            <div class="pk-fareline"><span class="lbl">Plate Recognition (YOLO + OCR):</span>
                <span>{'READY' if model_ready else 'LOADING'}</span></div>
            <div class="pk-fareline"><span class="lbl">C++ Parking Core (parkinglot.exe):</span>
                <span>{'READY' if core_ok else 'UNAVAILABLE'}</span></div>
        </div>
    """)


# ── camera stage (Parking page) ─────────────────────────────────────

def camera_stage(slot, cam_label: str):
    """
    Render the camera frame chrome into `slot` (an st.empty()) and return the
    image placeholder the caller should update every frame. Purely visual -
    the capture / YOLO / OCR loop lives in the caller.
    """
    with slot.container(key="camera_stage"):
        frame_ph = st.empty()
        _md(f"""
            <div class="pk-cam-tag">{icon('videocam', 14)} {cam_label}</div>
            <div class="pk-live-tag">{icon('sensors', 12)} LIVE</div>
            <div class="pk-guide">
                <div class="pk-corner tl"></div>
                <div class="pk-corner tr"></div>
                <div class="pk-corner bl"></div>
                <div class="pk-corner br"></div>
            </div>
            <div class="pk-scanline"></div>
            <div class="pk-hint">Position plate within frame</div>
        """)
    return frame_ph


def detected_plate_readout(plate: str, vehicle_type: str = "CAR"):
    _md(f"""
        <div class="pk-readout">
            <div class="pk-readout-icon">{icon('directions_car', 26)}</div>
            <div>
                <div class="pk-eyebrow" style="margin-bottom:0.15rem;">Detected Vehicle</div>
                <div class="pk-readout-plate">{plate_pretty(plate)}</div>
                <div class="pk-muted pk-mono" style="margin-top:0.15rem;">{vehicle_type}</div>
            </div>
        </div>
    """)


def slot_allocation_box(slot_number: str, zone: str, floor):
    _md(f"""
        <div class="pk-slotbox">
            <span class="pk-eyebrow">Designated Parking Space</span>
            <div class="num">SLOT {slot_number}</div>
            <div class="pk-muted pk-mono">{icon('navigation', 14)} Zone {zone} &bull; Floor {floor}</div>
        </div>
    """)


def kv_grid(pairs: list):
    """pairs: list of (label, value) tuples."""
    cells = "".join(
        f'<div class="pk-kv"><span class="pk-kv-label">{label}</span>'
        f'<span class="pk-kv-value">{value}</span></div>'
        for label, value in pairs
    )
    _md(f'<div class="pk-kv-grid">{cells}</div>')


def confirmation_box(title: str, sub: str, ico: str = "check"):
    _md(f"""
        <div class="pk-confirm-box">
            <div class="pk-confirm-icon">{icon(ico, 18)}</div>
            <div>
                <div class="pk-confirm-title">{title}</div>
                <div class="pk-confirm-sub">{sub}</div>
            </div>
        </div>
    """)


def exit_summary_box(plate: str, slot_number: str, entry_time_str: str, exit_time_str: str, duration_str: str):
    _md(f"""
        <div class="pk-card">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div class="pk-readout" style="padding:0;background:transparent;">
                    <div class="pk-readout-icon">{icon('badge', 22)}</div>
                    <div>
                        <div class="pk-eyebrow" style="margin-bottom:0.1rem;">Verified Vehicle</div>
                        <div class="pk-h2">{plate_pretty(plate)}</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="pk-eyebrow" style="justify-content:flex-end;margin-bottom:0.1rem;">Current Bay</div>
                    <div class="pk-h2" style="color:{COLORS['accent']};">SLOT {slot_number}</div>
                </div>
            </div>
        </div>
    """)
    kv_grid([("Entry Time", entry_time_str), ("Exit Time", exit_time_str), ("Duration", duration_str)])


def fare_breakdown_box(base_amount: float, peak_amount: float, base_minutes: int,
                        peak_minutes: int, total_amount: float, is_rush: bool, base_rate: float = 0.67):
    peak_row = ""
    if peak_amount and peak_amount > 0:
        peak_row = (
            f'<div class="pk-fareline"><span class="lbl pk-farerush">{icon("bolt", 14)} '
            f'Peak-Hour Surcharge ({peak_minutes} min)</span><span>+₹{peak_amount:.2f}</span></div>'
        )
    _md(f"""
        <div class="pk-card">
            <div class="pk-eyebrow">Tariff Computation</div>
            <div class="pk-fareline"><span class="lbl">Base Parking ({base_minutes} min @ ₹{base_rate:.2f}/min)</span><span>₹{base_amount:.2f}</span></div>
            {peak_row}
            <div class="pk-faretotal"><span class="lbl">Total Payable</span><span class="val">₹{total_amount:.2f}</span></div>
        </div>
    """)


# ── error / info states ──────────────────────────────────────────────

def info_card(title: str, message: str, ico: str = "info"):
    _md(f"""
        <div class="pk-card" style="text-align:center;padding:2rem 1.5rem;">
            <div style="color:{COLORS['accent']};margin-bottom:0.5rem;">{icon(ico, 32)}</div>
            <div class="pk-h2" style="margin-bottom:0.35rem;">{title}</div>
            <div class="pk-muted">{message}</div>
        </div>
    """)


def no_plate_card():
    info_card("We couldn't read that plate",
              "Position the vehicle so the plate is clearly visible and scan again.",
              "search_off")


def service_unavailable_card(storage_label: str = "MySQL"):
    info_card("Storage unavailable",
              f"Entries can't be processed right now. Check the {storage_label} storage connection.",
              "cloud_off")


def duplicate_scan_card(plate: str):
    info_card("Already processed",
              f"{plate_pretty(plate)} was just processed a moment ago. Scan again shortly to check out.",
              "history")


def processing_failed_card():
    info_card("Request failed", "Please try again.", "error")


def manual_entry_block(prefill: str = ""):
    """
    Elegant fallback text entry. Returns (submitted: bool, value: str).
    Assigning `prefill` to the widget key must happen before the widget is
    created, or Streamlit ignores it - callers should do that themselves
    right before invoking this (kept out of here so it stays a pure render).
    """
    value = st.text_input(
        "Manual Vehicle Identification", placeholder="ENTER REGISTRATION (E.G. MH12AB1234)",
        key="manual_input",
    )
    submitted = st.button("Submit Plate", type="primary", key="manual_submit")
    return submitted, value


# ── availability / slot grid ─────────────────────────────────────────

def availability_summary(available: int, total: int):
    stat_card("Available Bays", available, "Open Now",
              "Ready for instant check-in", "check_circle", accent=True)
