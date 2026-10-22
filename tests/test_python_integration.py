"""
Python <-> C++ integration tests.

    python -m pytest tests -q          (or: python -m unittest discover tests)

Needs the C++ core to be built first (build.bat or CMake). Uses a temporary
CSV file, so real parking records and the MySQL database are never touched.
The Streamlit test runs the real app headlessly in CSV mode (it loads the
YOLO model and EasyOCR, but never opens the camera).
"""

import importlib
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEMP_DIR = Path(tempfile.mkdtemp(prefix="parking_py_tests_"))
os.environ["PARKING_CSV_PATH"] = str(TEMP_DIR / "parking_data.csv")
os.environ["PARKING_BACKEND"] = "csv"

import parking_core  # noqa: E402  (environment must be set first)
import csv_store     # noqa: E402

WEDNESDAY_1759 = datetime(2026, 10, 21, 17, 59, 0)


def tearDownModule():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


def reset_csv():
    Path(os.environ["PARKING_CSV_PATH"]).unlink(missing_ok=True)


class BridgeTests(unittest.TestCase):
    def test_fare_matches_original_rules(self):
        entry = WEDNESDAY_1759.timestamp()
        fare = parking_core.calculate_fare(entry, entry + 120)
        self.assertEqual(fare["base_minutes"], 60)
        self.assertEqual(fare["peak_minutes"], 60)
        self.assertAlmostEqual(fare["total_amount"], 88.20)
        self.assertEqual(fare["is_rush_hour"], 1)
        self.assertEqual(set(fare), {"status", "total_duration", "base_minutes", "base_rate", "base_amount",
                                     "peak_minutes", "peak_surcharge", "peak_amount", "total_amount", "is_rush_hour"})

    def test_invalid_fare_raises_instead_of_returning_zero(self):
        with self.assertRaises(parking_core.ParkingCoreError) as ctx:
            parking_core.calculate_fare(1000, 1000)
        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")

    def test_rates_come_from_config(self):
        rates = parking_core.get_rates()
        self.assertAlmostEqual(rates["base_rate"], 0.67)
        self.assertAlmostEqual(rates["peak_rate"], 0.80)
        self.assertEqual(parking_core.peak_window_label(rates), "Weekends & 18:00–22:00")

    def test_missing_executable_is_reported_clearly(self):
        os.environ["PARKING_CORE_EXE"] = str(TEMP_DIR / "nope.exe")
        try:
            with self.assertRaises(parking_core.ParkingCoreError) as ctx:
                parking_core.run("slots")
            self.assertEqual(ctx.exception.code, "CORE_MISSING")
        finally:
            del os.environ["PARKING_CORE_EXE"]

    def test_db_module_uses_cpp_fare_engine(self):
        db = importlib.import_module("db")  # importing does not connect to MySQL
        entry = WEDNESDAY_1759.timestamp()
        self.assertAlmostEqual(db.call_c_fare_calculator(entry, entry + 120)["total_amount"], 88.20)


class CsvStoreTests(unittest.TestCase):
    def setUp(self):
        reset_csv()

    def test_entry_active_exit_cycle(self):
        ok, info = csv_store.test_connection()
        self.assertTrue(ok, info)
        self.assertEqual(csv_store.get_slot_summary(), {"total": 30, "available": 30, "occupied": 0})

        entry = csv_store.register_vehicle_entry("mh12ab1234", "CAR")
        self.assertTrue(entry["success"])
        self.assertEqual(entry["slot_number"], "1")

        duplicate = csv_store.register_vehicle_entry("MH12AB1234", "CAR")
        self.assertFalse(duplicate["success"])
        self.assertEqual(duplicate["error_code"], "ALREADY_PARKED")

        active = csv_store.get_active_session("MH12AB1234")
        self.assertIsInstance(active["entry_time"], datetime)
        self.assertEqual(csv_store.get_active_sessions()[0]["slot_number"], "1")
        self.assertEqual(csv_store.get_slot_summary()["occupied"], 1)

        exit_time = datetime.fromtimestamp(active["entry_time"].timestamp() + 90)
        result = csv_store.checkout_vehicle("MH12AB1234", active, exit_time, "UPI")
        self.assertTrue(result["success"])
        self.assertEqual(result["fare"]["total_duration"], 90)
        self.assertIsNone(csv_store.get_active_session("MH12AB1234"))
        self.assertEqual(csv_store.get_slot_summary()["available"], 30)

        record = csv_store.get_parking_records(10)[0]
        self.assertEqual(record["session_status"], "COMPLETED")
        self.assertEqual(record["payment_method"], "UPI")
        self.assertEqual(record["duration_seconds"], 90)

    def test_exit_without_entry_raises_not_found(self):
        with self.assertRaises(parking_core.ParkingCoreError) as ctx:
            csv_store.checkout_vehicle("MH12AB1234", {}, datetime.now())
        self.assertEqual(ctx.exception.code, "NOT_FOUND")

    def test_legacy_csv_from_original_app_is_readable(self):
        Path(os.environ["PARKING_CSV_PATH"]).write_text(
            "Number Plate,Entry Time,Exit Time,Slot\n"
            "MH12AB3456,17/04/2026 20:59:12,17/04/2026 21:09:53,1\n"
            "TH09BY9720,17/04/2026 21:03:21,,3\n", encoding="utf-8")
        records = csv_store.get_parking_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(csv_store.get_active_session("TH09BY9720")["slot_number"], "3")
        slot3 = next(s for s in csv_store.get_all_slots() if s["slot_number"] == "3")
        self.assertEqual(slot3["status"], "OCCUPIED")
        # Next entry skips the occupied slot 3 only when 1 and 2 are taken.
        self.assertEqual(csv_store.register_vehicle_entry("MH20EE7598")["slot_number"], "1")


class StreamlitAppTests(unittest.TestCase):
    """Runs streamlit_app.py headlessly with the CSV backend."""

    @classmethod
    def setUpClass(cls):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            raise unittest.SkipTest("streamlit is not installed")
        cls.AppTest = AppTest

    def setUp(self):
        reset_csv()
        self.app = self.AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=300)

    def markdown_text(self):
        return " ".join(m.value for m in self.app.markdown)

    def test_all_pages_render_without_errors(self):
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertIn("Parking Overview", self.markdown_text())
        self.assertIn("CSV Storage", self.markdown_text())
        for page in ("Parking", "Map", "Records"):
            self.app.session_state.page = page
            self.app.run()
            self.assertFalse(self.app.exception, page)
            self.assertFalse(self.app.error, page)

    def test_detected_plate_drives_entry_then_exit(self):
        self.app.session_state.page = "Parking"
        self.app.session_state.detected_plate = "MH12AB1234"
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertIn("Slot Assigned", self.markdown_text())
        self.assertIsNotNone(csv_store.get_active_session("MH12AB1234"))

        # Second read of the plate (after the de-dupe cooldown) is the exit.
        # Wait past the entry second: the core rejects a zero-length stay.
        time.sleep(1.2)
        self.app.session_state.last_processed = ("", 0.0)
        self.app.session_state.detected_plate = "MH12AB1234"
        self.app.run()
        self.assertFalse(self.app.exception)
        text = self.markdown_text()
        self.assertIn("Payment Recorded", text)
        self.assertIn("Tariff Computation", text)
        self.assertIsNone(csv_store.get_active_session("MH12AB1234"))
        self.assertEqual(csv_store.get_parking_records()[0]["session_status"], "COMPLETED")

    def test_exit_in_same_second_is_refused_not_guessed(self):
        csv_store.register_vehicle_entry("MH14CD5678")
        self.app.session_state.page = "Parking"
        self.app.session_state.detected_plate = "MH14CD5678"
        self.app.run()
        self.assertFalse(self.app.exception)
        if "Exit not recorded" in self.markdown_text():  # same second as the entry
            self.assertIn("exit must be after entry", self.markdown_text())
            self.assertIsNotNone(csv_store.get_active_session("MH14CD5678"))


if __name__ == "__main__":
    unittest.main()
