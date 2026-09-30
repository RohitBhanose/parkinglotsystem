"""
setup_db.py - One-click database setup for Smart Parking Management System
Run this ONCE to initialize the ParkingLot MySQL database.
Usage: python setup_db.py
"""
import subprocess, sys, os

print("=== Smart Parking - Database Setup ===\n")

# 1. Install dependencies
print("Step 1: Installing Python dependencies...")
subprocess.run([sys.executable, "-m", "pip", "install", "mysql-connector-python", "python-dotenv", "-q"], check=True)
print("  Done.\n")

# 2. Load .env
from dotenv import load_dotenv
load_dotenv()
import os, mysql.connector

cfg = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "autocommit": True,
}

print("Step 2: Connecting to MySQL...")
try:
    conn = mysql.connector.connect(**cfg)
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    print(f"  Connected! MySQL {cursor.fetchone()[0]}\n")
except Exception as e:
    print(f"  ERROR: {e}")
    print("  Make sure MySQL is running and .env has correct DB_PASSWORD")
    sys.exit(1)

print("Step 3: Running schema...")
cursor.execute("CREATE DATABASE IF NOT EXISTS ParkingLot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cursor.execute("USE ParkingLot")
exec(open(os.path.join(os.path.dirname(__file__), "database", "init_db.py")).read().replace("rohit$20", os.getenv("DB_PASSWORD","")))

print("\nStep 4: Running seed data...")
exec(open(os.path.join(os.path.dirname(__file__), "database", "seed_runner.py")).read().replace("rohit$20", os.getenv("DB_PASSWORD","")))

print("\n=== Setup Complete! Run: streamlit run streamlit_app.py ===")
