# Smart Parking Management System

A Smart Parking Management System with OCR-based license plate recognition, C-based fare calculation, rush-hour pricing, and MySQL (ParkingLot) database for full persistence.

---

## Overview

Originally a CSV-file-based parking system, this project has been upgraded to use a proper MySQL relational database while preserving all original functionality:

- **YOLO + EasyOCR** for number plate detection
- **C binary (parkinglot.exe)** for fare calculation with rush-hour pricing
- **MySQL 8.0 (ParkingLot database)** for all persistent data
- **Streamlit** web UI

---

## Technology Stack

| Layer | Technology |
|---|---|
| Number Plate Detection | YOLOv8 (best.pt) |
| OCR | EasyOCR |
| Fare Calculation | C (parkinglot.c / parkinglot.exe) |
| Database | MySQL 8.0 |
| Database Library | mysql-connector-python |
| UI | Streamlit |
| Config | python-dotenv |

---

## System Architecture

`
Camera / Image
      |
   YOLO Detection
      |
  EasyOCR (OCR)
      |
  Number Plate
      |
  ┌──────────────┐
  │  db.py       │  ─────────────>  MySQL: ParkingLot
  │  (Python)    │                    vehicles
  │              │                    parking_slots
  │  Stored Procs│                    parking_sessions
  │  + Triggers  │                    payments
  └──────┬───────┘                    pricing_rules
         |                            rush_hours
  parkinglot.exe (C)
  Fare Calculation
  Rush-Hour Pricing
         |
  Streamlit UI
`

---

## MySQL Database

**Database:** ParkingLot  
**Host:** localhost  
**Port:** 3306  
**User:** root (configurable via .env)

---

## Tables

### vehicles
| Column | Type | Notes |
|---|---|---|
| vehicle_id | INT UNSIGNED PK | Auto-increment |
| number_plate | VARCHAR(20) UNIQUE | Not null |
| vehicle_type | ENUM | CAR/BIKE/TRUCK/OTHER |
| owner_name | VARCHAR(100) | Optional |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto |

### parking_slots
| Column | Type | Notes |
|---|---|---|
| slot_id | INT UNSIGNED PK | Auto-increment |
| slot_number | VARCHAR(10) UNIQUE | '1'-'30' |
| slot_type | ENUM | STANDARD/COMPACT/LARGE |
| floor | TINYINT | 1 or 2 |
| zone | CHAR(1) | A/B/C/D |
| status | ENUM | AVAILABLE/OCCUPIED/MAINTENANCE |

### parking_sessions
| Column | Type | Notes |
|---|---|---|
| session_id | INT UNSIGNED PK | Auto-increment |
| vehicle_id | INT FK | References vehicles |
| slot_id | INT FK | References parking_slots |
| entry_time | DATETIME | Auto on insert |
| exit_time | DATETIME | NULL until exit |
| duration_seconds | INT | Computed on exit |
| base_minutes | INT | Non-rush minutes |
| peak_minutes | INT | Rush-hour minutes |
| base_rate | DECIMAL | Rs/min (from C: 0.67) |
| peak_rate | DECIMAL | Rs/min (from C: 0.80) |
| base_amount | DECIMAL | base_minutes * base_rate |
| peak_amount | DECIMAL | peak_minutes * peak_rate |
| total_fare | DECIMAL | base + peak |
| is_rush_hour | TINYINT | 1 if any peak minutes |
| session_status | ENUM | ACTIVE/COMPLETED/CANCELLED |
| payment_status | ENUM | PENDING/PAID/WAIVED |

### payments
| Column | Type | Notes |
|---|---|---|
| payment_id | INT UNSIGNED PK | Auto-increment |
| session_id | INT UNIQUE FK | References parking_sessions |
| amount | DECIMAL | Fare amount |
| payment_method | ENUM | CASH/UPI/CARD/WAIVED |
| payment_time | DATETIME | Auto |
| payment_status | ENUM | SUCCESS/FAILED/REFUNDED |
| transaction_ref | VARCHAR | UPI/card ref ID |

### rush_hours
| Column | Type | Notes |
|---|---|---|
| rush_hour_id | INT PK | Auto-increment |
| description | VARCHAR | Human-readable name |
| rule_type | ENUM | WEEKEND or TIMERANGE |
| start_time | TIME | For TIMERANGE rules |
| end_time | TIME | For TIMERANGE rules |
| multiplier | DECIMAL | Price multiplier |
| is_active | TINYINT | 1=active |

### pricing_rules
| Column | Type | Notes |
|---|---|---|
| rule_id | INT PK | Auto-increment |
| vehicle_type | ENUM | CAR/BIKE/TRUCK/OTHER |
| base_rate_per_min | DECIMAL | Rs 0.67 for CAR |
| peak_rate_per_min | DECIMAL | Rs 0.80 for CAR |
| effective_from | DATE | Validity start |
| effective_to | DATE | Validity end (NULL = ongoing) |
| is_active | TINYINT | 1=active |

---

## Relationships

`
vehicles ─────────< parking_sessions >──────── parking_slots
                          │
                          └────────< payments
`

- **vehicles → parking_sessions**: 1 vehicle can have many sessions (one ACTIVE at a time)
- **parking_slots → parking_sessions**: 1 slot can have many sessions (one ACTIVE at a time)
- **parking_sessions → payments**: 1 session has at most 1 payment (UNIQUE FK)

---

## Normalization

**1NF**: All columns are atomic. No repeating groups.  
**2NF**: No partial dependencies. All non-key columns depend on the full PK.  
**3NF**: No transitive dependencies. Pricing is in its own table, not duplicated across sessions (rates stored at time of transaction for audit).

---

## Views

| View | Purpose |
|---|---|
| active_parking_sessions | All currently parked vehicles with slot and duration |
| parking_history | Complete history with vehicle, slot, fare, payment |
| daily_revenue | Revenue grouped by date |
| slot_availability | All slots with availability flag |
| vehicle_parking_history | Per-vehicle aggregated stats |
| rush_hour_sessions | Sessions where rush-hour pricing was applied |

---

## Stored Procedures

**RegisterVehicleEntry(number_plate, vehicle_type)**
- Upserts vehicle record
- Checks for existing active session (prevents duplicates)
- Finds first available slot
- Creates parking session
- Returns: session_id, slot_number, message

**ProcessVehicleExit(number_plate, base_minutes, peak_minutes, base_amount, peak_amount, total_fare, is_rush_hour, payment_method)**
- Finds active session
- Updates session with exit time and fare breakdown
- Creates payment record
- Returns: session_id, message

---

## Functions

**CalculateParkingDuration(entry_time, exit_time)** → INT (seconds, minimum 60)

**CalculateBaseFare(base_minutes, base_rate)** → DECIMAL

---

## Triggers

**trg_slot_occupied_on_entry** (AFTER INSERT on parking_sessions)
- Sets slot status to OCCUPIED when a new ACTIVE session is created

**trg_slot_available_on_exit** (AFTER UPDATE on parking_sessions)
- Sets slot status to AVAILABLE when session becomes COMPLETED or CANCELLED

**trg_prevent_duplicate_entry** (BEFORE INSERT on parking_sessions)
- Raises error if vehicle already has an ACTIVE session

---

## C Fare Calculation (preserved)

The **parkinglot.c** / **parkinglot.exe** binary receives two UNIX timestamps:

`
parkinglot.exe <entry_unix_ts> <exit_unix_ts>
`

Output:
`
STATUS=ACTIVE
TOTAL_DURATION=<minutes>
BASE_MINUTES=<n>
BASE_RATE=0.67
BASE_AMOUNT=<Rs>
PEAK_MINUTES=<n>
PEAK_SURCHARGE=0.80
PEAK_AMOUNT=<Rs>
TOTAL_AMOUNT=<Rs>
`

Rush-hour logic in C:
- **Weekend** (Sunday=0 or Saturday=6): peak rate applies all day
- **Evening** (18:00–22:00 on any day): peak rate applies

---

## Vehicle Entry Flow

`
OCR detects plate
    ↓
db.register_vehicle_entry(plate)
    ↓  (calls stored procedure RegisterVehicleEntry)
INSERT INTO vehicles (if new)
    ↓
Check for existing ACTIVE session (trigger/proc blocks duplicate)
    ↓
Find first AVAILABLE slot
    ↓
INSERT INTO parking_sessions (ACTIVE)
    ↓
Trigger: parking_slots.status = OCCUPIED
    ↓
Entry time stored in MySQL
`

---

## Vehicle Exit Flow

`
OCR detects plate
    ↓
db.get_active_session(plate)  →  gets entry_time from MySQL
    ↓
call_c_fare_calculator(entry_ts, exit_ts)  →  parkinglot.exe
    ↓
fare breakdown: base_amount + peak_amount = total_fare
    ↓
db.process_vehicle_exit(plate, fare_data)
    ↓  (calls stored procedure ProcessVehicleExit)
UPDATE parking_sessions SET exit_time, fare, status=COMPLETED
    ↓
Trigger: parking_slots.status = AVAILABLE
    ↓
INSERT INTO payments
`

---

## Rush-Hour Pricing

The C binary loops through each second of the parking duration and checks:
- Is it a weekend? → Peak rate (Rs 0.80/min)
- Is it 18:00–22:00? → Peak rate (Rs 0.80/min)
- Otherwise → Base rate (Rs 0.67/min)

This exactly mirrors the ush_hours table in MySQL which documents:
- Weekend rule (WEEKEND type)
- Evening peak 18:00–22:00 (TIMERANGE type)

---

## Environment Variables

Create a .env file (never commit it):

`
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ParkingLot
DB_USER=root
DB_PASSWORD=your_password_here
`

See .env.example for the template.

---

## Installation & Running

### Prerequisites
- Python 3.x
- MySQL 8.0 (running)
- GCC (if recompiling parkinglot.c)

### Setup

`ash
# 1. Install Python dependencies
pip install streamlit ultralytics easyocr opencv-python mysql-connector-python python-dotenv

# 2. Copy env template and fill in your MySQL password
cp .env.example .env

# 3. The database is already created. To recreate from scratch:
python database/init_db.py      # creates schema
python database/seed_runner.py  # inserts sample data

# 4. Run the application
streamlit run streamlit_app.py
`

---

## Database Files

| File | Purpose |
|---|---|
| database/schema.sql | Complete DDL: tables, indexes, views, triggers, procedures, functions |
| database/seed.sql | Sample data INSERT statements |
| database/queries.sql | 20 demonstration queries for viva |

---

## SQL Features Demonstrated

SELECT, INSERT, UPDATE, DELETE, INNER JOIN, LEFT JOIN, GROUP BY, HAVING, ORDER BY, COUNT, SUM, AVG, MIN, MAX, Subqueries, Views, Indexes, Foreign Keys, Constraints, Transactions, Stored Procedures, Functions, Triggers, ENUM types, CHECK constraints, ON DUPLICATE KEY UPDATE, SIGNAL SQLSTATE, TIMESTAMPDIFF, CASE WHEN, NULLIF, COALESCE

---

## Sample Queries (queries.sql)

1. Find all currently parked vehicles
2. Available slots
3. Parking history for specific vehicle
4. Total revenue (SUM)
5. Daily revenue (GROUP BY)
6. Most frequent parkers (HAVING)
7. Avg duration by vehicle type
8. Rush-hour sessions
9. Occupied slots (INNER JOIN)
10. Completed sessions with payments (LEFT JOIN)
11. Above-average spenders (Subquery)
12. Slot utilization report
13. Rush vs normal revenue
14. Use active_parking_sessions VIEW
15. Use vehicle_parking_history VIEW
16. Verify foreign keys (information_schema)
17. List all indexes
18. List all triggers
19. List all routines
20. Full transaction demonstration