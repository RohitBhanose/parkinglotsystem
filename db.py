"""
db.py - MySQL database layer for Smart Parking Management System
Handles all database operations using mysql-connector-python.
Credentials loaded from .env via python-dotenv.
"""

import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# ── Config from environment ──────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_NAME", "ParkingLot"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset":  "utf8mb4",
    "autocommit": True,
    "connection_timeout": 10,
}

def get_connection():
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed. Run: pip install mysql-connector-python")
    return mysql.connector.connect(**DB_CONFIG)

def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return True, version
    except Exception as e:
        return False, str(e)

# ── Slot operations ──────────────────────────────────────────────
def get_slot_summary():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN status='OCCUPIED'  THEN 1 ELSE 0 END) AS occupied
        FROM parking_slots
    """)
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def get_all_slots():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT slot_id, slot_number, slot_type, floor, zone, status FROM parking_slots ORDER BY slot_id")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

# ── Vehicle entry (uses stored procedure via callproc) ───────────
def register_vehicle_entry(number_plate: str, vehicle_type: str = "CAR"):
    """
    Calls RegisterVehicleEntry stored procedure.
    Returns dict: {session_id, slot_number, message, success}
    """
    conn = get_connection()
    cursor = conn.cursor()
    args = (number_plate.upper().strip(), vehicle_type, 0, "", "")
    result = cursor.callproc("RegisterVehicleEntry", args)
    cursor.close(); conn.close()
    return {
        "session_id":  result[2],
        "slot_number": result[3],
        "message":     result[4],
        "success":     (result[2] is not None and result[2] > 0)
    }

# ── C fare calculator bridge ─────────────────────────────────────
def call_c_fare_calculator(entry_ts: float, exit_ts: float) -> dict:
    """
    Calls parkinglot.exe with UNIX timestamps.
    Returns structured fare breakdown dict.
    """
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parkinglot.exe")
    result = subprocess.run(
        [exe_path, str(int(entry_ts)), str(int(exit_ts))],
        capture_output=True, text=True, timeout=10
    )
    parsed = {}
    for line in result.stdout.strip().splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            parsed[key.strip()] = val.strip()
    return {
        "status":         parsed.get("STATUS", "UNKNOWN"),
        "total_duration": int(parsed.get("TOTAL_DURATION", 1)),
        "base_minutes":   int(parsed.get("BASE_MINUTES", 0)),
        "base_rate":      float(parsed.get("BASE_RATE", 0.67)),
        "base_amount":    float(parsed.get("BASE_AMOUNT", 0.0)),
        "peak_minutes":   int(parsed.get("PEAK_MINUTES", 0)),
        "peak_surcharge": float(parsed.get("PEAK_SURCHARGE", 0.80)),
        "peak_amount":    float(parsed.get("PEAK_AMOUNT", 0.0)),
        "total_amount":   float(parsed.get("TOTAL_AMOUNT", 0.0)),
        "is_rush_hour":   1 if int(parsed.get("PEAK_MINUTES", 0)) > 0 else 0,
    }

# ── Vehicle exit (uses stored procedure via callproc) ────────────
def process_vehicle_exit(number_plate: str, fare_data: dict, payment_method: str = "CASH"):
    """
    Calls ProcessVehicleExit stored procedure.
    Returns dict: {session_id, message, success}
    """
    conn = get_connection()
    cursor = conn.cursor()
    args = (
        number_plate.upper().strip(),
        fare_data.get("base_minutes", 0),
        fare_data.get("peak_minutes", 0),
        fare_data.get("base_amount",  0.0),
        fare_data.get("peak_amount",  0.0),
        fare_data.get("total_amount", 0.0),
        fare_data.get("is_rush_hour", 0),
        payment_method,
        0, ""
    )
    result = cursor.callproc("ProcessVehicleExit", args)
    cursor.close(); conn.close()
    return {
        "session_id": result[8],
        "message":    result[9],
        "success":    (result[8] is not None and result[8] > 0)
    }

# ── Active session lookup ────────────────────────────────────────
def get_active_session(number_plate: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ps.session_id, ps.entry_time, sl.slot_number,
               v.number_plate, v.vehicle_type
        FROM parking_sessions ps
        JOIN vehicles v       ON v.vehicle_id  = ps.vehicle_id
        JOIN parking_slots sl ON sl.slot_id    = ps.slot_id
        WHERE v.number_plate = %s AND ps.session_status = 'ACTIVE'
        ORDER BY ps.entry_time DESC LIMIT 1
    """, (number_plate.upper().strip(),))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

# ── Records & Analytics ──────────────────────────────────────────
def get_parking_records(limit=200):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parking_history LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_active_sessions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM active_parking_sessions ORDER BY minutes_parked DESC")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_daily_revenue():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM daily_revenue LIMIT 30")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def search_vehicle(number_plate: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parking_history WHERE number_plate = %s", (number_plate.upper().strip(),))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows