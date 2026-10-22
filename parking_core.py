"""
parking_core.py - Python bridge to the C++ parking core (parkinglot.exe).

The C++ executable owns the parking business rules: fare calculation,
slot allocation, session state and CSV records (see src/ and README.md).
This module only starts it, passes arguments, and turns its one-line JSON
reply into Python dicts. No parking rule is re-implemented here.

Errors from the core arrive as {"ok": false, "error_code": ..., "message": ...}
and are raised as ParkingCoreError so the UI can show the message.
"""

import json
import os
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("PARKING_CONFIG_PATH", BASE_DIR / "config" / "parking.cfg"))
CSV_PATH = Path(os.getenv("PARKING_CSV_PATH", BASE_DIR / "parking_data.csv"))
TIMEOUT_SECONDS = 30

_EXE_NAME = "parkinglot.exe" if os.name == "nt" else "parkinglot"
_CANDIDATES = [
    BASE_DIR / "build" / _EXE_NAME,             # build.bat, CMake + Ninja/Makefiles
    BASE_DIR / "build" / "Release" / _EXE_NAME,  # CMake + Visual Studio
    BASE_DIR / "build" / "Debug" / _EXE_NAME,
]


class ParkingCoreError(RuntimeError):
    """A failure reported by (or while starting) the C++ core."""

    def __init__(self, message: str, code: str = "CORE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


def find_executable() -> Path:
    override = os.getenv("PARKING_CORE_EXE")
    if override:
        path = Path(override)
        if path.is_file():
            return path
        raise ParkingCoreError(f"PARKING_CORE_EXE points to {path}, which does not exist", "CORE_MISSING")
    for candidate in _CANDIDATES:
        if candidate.is_file():
            return candidate
    raise ParkingCoreError(
        "The C++ parking core is not built yet. Run build.bat "
        "(or: cmake -S . -B build && cmake --build build).",
        "CORE_MISSING",
    )


def run(command: str, *args, data_path=None) -> dict:
    """Run one core command and return its JSON reply (raises ParkingCoreError)."""
    cmd = [str(find_executable()), command, *(str(a) for a in args),
           "--data", str(data_path or CSV_PATH)]
    if CONFIG_PATH.is_file():
        cmd += ["--config", str(CONFIG_PATH)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              timeout=TIMEOUT_SECONDS, cwd=BASE_DIR)
    except subprocess.TimeoutExpired:
        raise ParkingCoreError(f"The C++ core did not answer within {TIMEOUT_SECONDS}s", "CORE_TIMEOUT")
    except OSError as e:
        raise ParkingCoreError(f"Could not start the C++ core: {e}", "CORE_MISSING")

    try:
        reply = json.loads(proc.stdout)
    except json.JSONDecodeError:
        detail = (proc.stdout or proc.stderr or "").strip()[:300]
        raise ParkingCoreError(f"Unexpected reply from the C++ core (exit code {proc.returncode}): {detail}")
    if not reply.get("ok"):
        raise ParkingCoreError(reply.get("message", "Unknown error"), reply.get("error_code", "CORE_ERROR"))
    return reply


def _fare_dict(reply: dict) -> dict:
    """C++ fare JSON -> the dict shape db.py has always returned for fares."""
    return {
        "status":         "ACTIVE",
        "total_duration": reply["total_duration"],
        "base_minutes":   reply["base_minutes"],
        "base_rate":      reply["base_rate"],
        "base_amount":    reply["base_amount"],
        "peak_minutes":   reply["peak_minutes"],
        "peak_surcharge": reply["peak_rate"],
        "peak_amount":    reply["peak_amount"],
        "total_amount":   reply["total_amount"],
        "is_rush_hour":   1 if reply["is_rush_hour"] else 0,
    }


def calculate_fare(entry_ts: float, exit_ts: float, vehicle_type: str = "CAR") -> dict:
    """Fare breakdown for a stay between two UNIX timestamps (C++ ParkingFeeStrategy)."""
    return _fare_dict(run("fare", int(entry_ts), int(exit_ts), "--type", vehicle_type))


def fare_from_reply(reply: dict) -> dict:
    return _fare_dict(reply)


@lru_cache(maxsize=1)
def get_rates() -> dict:
    """Tariff settings from config/parking.cfg, as the C++ core reads them."""
    return run("rates")


def peak_window_label(rates: dict) -> str:
    hours = f"{rates['peak_start_hour']:02d}:00–{rates['peak_end_hour']:02d}:00"
    return f"Weekends & {hours}" if rates.get("weekend_is_peak") else hours


def to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp) if timestamp is not None else None
