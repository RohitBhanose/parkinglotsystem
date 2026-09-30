-- ============================================================
-- queries.sql - DBMS Demonstration Queries for ParkingLot
-- These queries demonstrate SQL concepts for academic viva
-- ============================================================

USE ParkingLot;

-- ============================================================
-- 1. BASIC SELECT - All currently parked vehicles
-- ============================================================
SELECT v.number_plate, v.vehicle_type, sl.slot_number, ps.entry_time,
       TIMESTAMPDIFF(MINUTE, ps.entry_time, NOW()) AS minutes_parked
FROM parking_sessions ps
JOIN vehicles v      ON v.vehicle_id  = ps.vehicle_id
JOIN parking_slots sl ON sl.slot_id   = ps.slot_id
WHERE ps.session_status = 'ACTIVE'
ORDER BY ps.entry_time;

-- ============================================================
-- 2. Available slots (using view)
-- ============================================================
SELECT * FROM slot_availability WHERE is_available = 1;

-- ============================================================
-- 3. Parking history for a specific vehicle (parameterize as needed)
-- ============================================================
SELECT * FROM parking_history WHERE number_plate = 'MH12AB1234';

-- ============================================================
-- 4. Total revenue using SUM and COUNT
-- ============================================================
SELECT
    COUNT(session_id)   AS total_sessions,
    SUM(total_fare)     AS total_revenue,
    AVG(total_fare)     AS avg_fare,
    MIN(total_fare)     AS min_fare,
    MAX(total_fare)     AS max_fare
FROM parking_sessions
WHERE session_status = 'COMPLETED';

-- ============================================================
-- 5. Daily revenue (GROUP BY + ORDER BY)
-- ============================================================
SELECT * FROM daily_revenue ORDER BY revenue_date DESC LIMIT 7;

-- ============================================================
-- 6. Most frequently parked vehicles (GROUP BY + ORDER BY + LIMIT)
-- ============================================================
SELECT v.number_plate, v.vehicle_type, COUNT(ps.session_id) AS total_visits,
       SUM(ps.total_fare) AS total_spent
FROM vehicles v
JOIN parking_sessions ps ON ps.vehicle_id = v.vehicle_id
WHERE ps.session_status = 'COMPLETED'
GROUP BY v.vehicle_id, v.number_plate, v.vehicle_type
HAVING total_visits >= 1
ORDER BY total_visits DESC
LIMIT 10;

-- ============================================================
-- 7. Average parking duration per vehicle type
-- ============================================================
SELECT v.vehicle_type,
       COUNT(ps.session_id)                          AS sessions,
       AVG(ps.duration_seconds / 60)                 AS avg_duration_minutes,
       AVG(ps.total_fare)                             AS avg_fare
FROM parking_sessions ps
JOIN vehicles v ON v.vehicle_id = ps.vehicle_id
WHERE ps.session_status = 'COMPLETED'
GROUP BY v.vehicle_type
ORDER BY avg_fare DESC;

-- ============================================================
-- 8. Vehicles that parked during rush hours (is_rush_hour flag)
-- ============================================================
SELECT v.number_plate, ps.entry_time, ps.exit_time,
       ps.base_amount, ps.peak_amount, ps.total_fare
FROM parking_sessions ps
JOIN vehicles v ON v.vehicle_id = ps.vehicle_id
WHERE ps.is_rush_hour = 1 AND ps.session_status = 'COMPLETED'
ORDER BY ps.entry_time DESC;

-- ============================================================
-- 9. Currently occupied slots with vehicle info (INNER JOIN)
-- ============================================================
SELECT sl.slot_number, sl.zone, sl.floor, v.number_plate, v.vehicle_type, ps.entry_time
FROM parking_slots sl
JOIN parking_sessions ps ON ps.slot_id    = sl.slot_id AND ps.session_status = 'ACTIVE'
JOIN vehicles         v  ON v.vehicle_id  = ps.vehicle_id
ORDER BY sl.slot_number;

-- ============================================================
-- 10. Completed sessions with payment info (LEFT JOIN)
-- ============================================================
SELECT ps.session_id, v.number_plate, ps.total_fare,
       py.payment_method, py.payment_time, py.payment_status
FROM parking_sessions ps
JOIN  vehicles v ON v.vehicle_id  = ps.vehicle_id
LEFT  JOIN payments py ON py.session_id = ps.session_id
WHERE ps.session_status = 'COMPLETED'
ORDER BY ps.exit_time DESC;

-- ============================================================
-- 11. Vehicles that spent more than average (Subquery)
-- ============================================================
SELECT v.number_plate, SUM(ps.total_fare) AS total_spent
FROM parking_sessions ps
JOIN vehicles v ON v.vehicle_id = ps.vehicle_id
WHERE ps.session_status = 'COMPLETED'
GROUP BY v.vehicle_id, v.number_plate
HAVING total_spent > (
    SELECT AVG(total_fare) FROM parking_sessions WHERE session_status = 'COMPLETED'
)
ORDER BY total_spent DESC;

-- ============================================================
-- 12. Slot utilization report
-- ============================================================
SELECT sl.slot_number, sl.zone,
       COUNT(ps.session_id)  AS times_used,
       SUM(ps.total_fare)    AS revenue_generated,
       sl.status             AS current_status
FROM parking_slots sl
LEFT JOIN parking_sessions ps ON ps.slot_id = sl.slot_id AND ps.session_status = 'COMPLETED'
GROUP BY sl.slot_id, sl.slot_number, sl.zone, sl.status
ORDER BY times_used DESC;

-- ============================================================
-- 13. Rush hour revenue vs non-rush revenue
-- ============================================================
SELECT
    CASE WHEN is_rush_hour = 1 THEN 'Rush Hour' ELSE 'Normal Hour' END AS period_type,
    COUNT(session_id)   AS sessions,
    SUM(total_fare)     AS total_revenue,
    AVG(total_fare)     AS avg_fare
FROM parking_sessions
WHERE session_status = 'COMPLETED'
GROUP BY is_rush_hour;

-- ============================================================
-- 14. Use the active_parking_sessions VIEW
-- ============================================================
SELECT * FROM active_parking_sessions ORDER BY minutes_parked DESC;

-- ============================================================
-- 15. Use the vehicle_parking_history VIEW
-- ============================================================
SELECT * FROM vehicle_parking_history WHERE total_visits > 0 ORDER BY total_visits DESC;

-- ============================================================
-- 16. Check foreign key relationships - verify referential integrity
-- ============================================================
SELECT
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'ParkingLot'
ORDER BY TABLE_NAME;

-- ============================================================
-- 17. List all indexes
-- ============================================================
SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'ParkingLot'
ORDER BY TABLE_NAME, INDEX_NAME;

-- ============================================================
-- 18. View all triggers
-- ============================================================
SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, ACTION_TIMING
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'ParkingLot';

-- ============================================================
-- 19. View all stored procedures and functions
-- ============================================================
SELECT ROUTINE_NAME, ROUTINE_TYPE, CREATED
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = 'ParkingLot'
ORDER BY ROUTINE_TYPE, ROUTINE_NAME;

-- ============================================================
-- 20. Complete transaction example (for viva demonstration)
-- Vehicle entry transaction:
--   BEGIN; INSERT vehicle; find slot; INSERT session; UPDATE slot; COMMIT;
-- ============================================================
-- CALL RegisterVehicleEntry('TEST01AA0000', 'CAR', @sid, @slot, @msg);
-- SELECT @sid, @slot, @msg;
