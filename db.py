"""
db.py - MySQL database layer for Smart Parking Management System
Handles all database operations using mysql-connector-python.
Credentials loaded from .env via python-dotenv.

Slot allocation and persistence run in the database's stored procedures;
fares come from the C++ core (parking_core.py -> parkinglot.exe).
"""

import os
from datetime import datetime
from dotenv import load_dotenv

import parking_core

load_dotenv()

BACKEND_LABEL = "MySQL"

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
def _as_int(value):
    """
    OUT params come back as int, str or bytes depending on the connector
    version; comparing a str against 0 raises TypeError and would surface as
    a failed registration even though the row was written.
    """
    if value is None:
        return 0
    if isinstance(value, bytes):
        value = value.decode("utf-8", "ignore")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
    session_id = _as_int(result[2])
    return {
        "session_id":  session_id,
        "slot_number": result[3],
        "message":     result[4],
        "success":     session_id > 0
    }

# ── C++ fare calculator bridge ───────────────────────────────────
def call_c_fare_calculator(entry_ts: float, exit_ts: float) -> dict:
    """
    Fare breakdown from the C++ core for two UNIX timestamps (same dict
    shape as before). Raises parking_core.ParkingCoreError on failure
    instead of silently returning a zero fare.
    """
    return parking_core.calculate_fare(entry_ts, exit_ts)

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
    session_id = _as_int(result[8])
    return {
        "session_id": session_id,
        "message":    result[9],
        "success":    session_id > 0
    }

def checkout_vehicle(number_plate: str, active: dict, exit_time: datetime, payment_method: str = "CASH"):
    """
    Exit in MySQL mode: fare from the C++ core, then ProcessVehicleExit.
    Every vehicle is billed with the CAR tariff here, exactly as before.
    Returns {session_id, message, success, fare}; fare errors raise ParkingCoreError.
    """
    fare = call_c_fare_calculator(active["entry_time"].timestamp(), exit_time.timestamp())
    result = process_vehicle_exit(number_plate, fare, payment_method)
    result["fare"] = fare
    return result

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