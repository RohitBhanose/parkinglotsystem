"""
csv_store.py - CSV storage backend for the Streamlit app (PARKING_BACKEND=csv).

Offers the same functions streamlit_app.py uses from db.py, so the UI runs
unchanged without MySQL. Every operation is executed by the C++ core
(ParkingLot + CsvParkingRepository, via parking_core.py); this module only
converts the replies into the dict shapes db.py returns - datetimes instead
of UNIX timestamps, same key names as the MySQL views.
"""

import parking_core
from parking_core import ParkingCoreError

BACKEND_LABEL = "CSV"

_SLOT_KEYS = ("slot_id", "slot_number", "slot_type", "floor", "zone", "status")


def _session(transaction: dict) -> dict:
    row = dict(transaction)
    for key in ("entry_time", "exit_time", "payment_time"):
        row[key] = parking_core.to_datetime(row.get(key))
    return row


def test_connection():
    try:
        parking_core.run("slots")
        return True, f"{parking_core.CSV_PATH.name} via C++ core"
    except ParkingCoreError as e:
        return False, e.message


def get_slot_summary():
    return parking_core.run("slots")["summary"]


def get_all_slots():
    return [{key: slot[key] for key in _SLOT_KEYS} for slot in parking_core.run("slots")["slots"]]


def register_vehicle_entry(number_plate: str, vehicle_type: str = "CAR"):
    """Same reply shape as db.register_vehicle_entry: {session_id, slot_number, message, success}."""
    try:
        reply = parking_core.run("entry", number_plate.upper().strip(), "--type", vehicle_type)
    except ParkingCoreError as e:
        return {"session_id": -1, "slot_number": None, "message": e.message,
                "success": False, "error_code": e.code}
    transaction = reply["transaction"]
    return {"session_id": transaction["session_id"], "slot_number": transaction["slot_number"],
            "message": reply["message"], "success": True}


def get_active_session(number_plate: str):
    reply = parking_core.run("active", number_plate.upper().strip())
    return _session(reply["transaction"]) if reply["found"] else None


def checkout_vehicle(number_plate: str, active: dict, exit_time, payment_method: str = "CASH"):
    """
    Exit + fare + payment in one C++ call. Returns {success, message, session_id, fare}.
    `active` is unused here (the core looks the session up itself); it is accepted
    so db.checkout_vehicle and this function are interchangeable.
    """
    reply = parking_core.run("exit", number_plate.upper().strip(), "--method", payment_method,
                             "--at", int(exit_time.timestamp()))
    return {"success": True, "message": reply["message"],
            "session_id": reply["transaction"]["session_id"],
            "fare": parking_core.fare_from_reply(reply["fare"])}


def get_parking_records(limit=200):
    reply = parking_core.run("history", "--limit", int(limit))
    return [_session(t) for t in reply["transactions"]]


def get_active_sessions():
    return [_session(t) for t in parking_core.run("history")["transactions"]
            if t["session_status"] == "ACTIVE"]
