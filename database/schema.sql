-- ============================================================
-- Smart Parking Management System - ParkingLot Database Schema
-- MySQL 8.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS ParkingLot
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ParkingLot;

-- TABLE: vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    number_plate    VARCHAR(20)     NOT NULL,
    vehicle_type    ENUM('CAR','BIKE','TRUCK','OTHER') NOT NULL DEFAULT 'CAR',
    owner_name      VARCHAR(100)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (vehicle_id),
    UNIQUE KEY uq_number_plate (number_plate),
    INDEX idx_number_plate (number_plate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TABLE: parking_slots
CREATE TABLE IF NOT EXISTS parking_slots (
    slot_id         INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    slot_number     VARCHAR(10)     NOT NULL,
    slot_type       ENUM('STANDARD','COMPACT','LARGE') NOT NULL DEFAULT 'STANDARD',
    floor           TINYINT UNSIGNED NOT NULL DEFAULT 1,
    zone            CHAR(1)         NOT NULL DEFAULT 'A',
    status          ENUM('AVAILABLE','OCCUPIED','MAINTENANCE') NOT NULL DEFAULT 'AVAILABLE',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (slot_id),
    UNIQUE KEY uq_slot_number (slot_number),
    INDEX idx_status (status),
    INDEX idx_floor_zone (floor, zone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TABLE: rush_hours
CREATE TABLE IF NOT EXISTS rush_hours (
    rush_hour_id    INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    description     VARCHAR(100)    NOT NULL,
    rule_type       ENUM('WEEKEND','TIMERANGE') NOT NULL,
    start_time      TIME            NULL,
    end_time        TIME            NULL,
    multiplier      DECIMAL(4,2)    NOT NULL DEFAULT 1.00,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rush_hour_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TABLE: pricing_rules
CREATE TABLE IF NOT EXISTS pricing_rules (
    rule_id             INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    vehicle_type        ENUM('CAR','BIKE','TRUCK','OTHER') NOT NULL,
    base_rate_per_min   DECIMAL(8,4)    NOT NULL DEFAULT 0.6700,
    peak_rate_per_min   DECIMAL(8,4)    NOT NULL DEFAULT 0.8000,
    effective_from      DATE            NOT NULL,
    effective_to        DATE            NULL,
    is_active           TINYINT(1)      NOT NULL DEFAULT 1,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_id),
    INDEX idx_vehicle_type (vehicle_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TABLE: parking_sessions
CREATE TABLE IF NOT EXISTS parking_sessions (
    session_id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    vehicle_id          INT UNSIGNED    NOT NULL,
    slot_id             INT UNSIGNED    NOT NULL,
    entry_time          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exit_time           DATETIME        NULL,
    duration_seconds    INT UNSIGNED    NULL,
    base_minutes        INT UNSIGNED    NULL DEFAULT 0,
    peak_minutes        INT UNSIGNED    NULL DEFAULT 0,
    base_rate           DECIMAL(8,4)    NULL,
    peak_rate           DECIMAL(8,4)    NULL,
    base_amount         DECIMAL(10,2)   NULL DEFAULT 0.00,
    peak_amount         DECIMAL(10,2)   NULL DEFAULT 0.00,
    total_fare          DECIMAL(10,2)   NULL DEFAULT 0.00,
    is_rush_hour        TINYINT(1)      NOT NULL DEFAULT 0,
    session_status      ENUM('ACTIVE','COMPLETED','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
    payment_status      ENUM('PENDING','PAID','WAIVED') NOT NULL DEFAULT 'PENDING',
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id),
    FOREIGN KEY fk_session_vehicle (vehicle_id) REFERENCES vehicles(vehicle_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY fk_session_slot (slot_id) REFERENCES parking_slots(slot_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_vehicle_id (vehicle_id),
    INDEX idx_slot_id (slot_id),
    INDEX idx_session_status (session_status),
    INDEX idx_entry_time (entry_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TABLE: payments
CREATE TABLE IF NOT EXISTS payments (
    payment_id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    session_id          INT UNSIGNED    NOT NULL,
    amount              DECIMAL(10,2)   NOT NULL,
    payment_method      ENUM('CASH','UPI','CARD','WAIVED') NOT NULL DEFAULT 'CASH',
    payment_time        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_status      ENUM('SUCCESS','FAILED','REFUNDED') NOT NULL DEFAULT 'SUCCESS',
    transaction_ref     VARCHAR(100)    NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (payment_id),
    UNIQUE KEY uq_session_payment (session_id),
    FOREIGN KEY fk_payment_session (session_id) REFERENCES parking_sessions(session_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_payment_time (payment_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- TRIGGER: Mark slot OCCUPIED on entry
DELIMITER ;;
CREATE TRIGGER trg_slot_occupied_on_entry
    AFTER INSERT ON parking_sessions
    FOR EACH ROW
BEGIN
    IF NEW.session_status = 'ACTIVE' THEN
        UPDATE parking_slots SET status = 'OCCUPIED', updated_at = NOW() WHERE slot_id = NEW.slot_id;
    END IF;
END;;
DELIMITER ;

-- TRIGGER: Mark slot AVAILABLE on exit/cancel
DELIMITER ;;
CREATE TRIGGER trg_slot_available_on_exit
    AFTER UPDATE ON parking_sessions
    FOR EACH ROW
BEGIN
    IF OLD.session_status = 'ACTIVE' AND NEW.session_status IN ('COMPLETED','CANCELLED') THEN
        UPDATE parking_slots SET status = 'AVAILABLE', updated_at = NOW() WHERE slot_id = NEW.slot_id;
    END IF;
END;;
DELIMITER ;

-- TRIGGER: Prevent duplicate active sessions
DELIMITER ;;
CREATE TRIGGER trg_prevent_duplicate_entry
    BEFORE INSERT ON parking_sessions
    FOR EACH ROW
BEGIN
    DECLARE active_count INT;
    SELECT COUNT(*) INTO active_count FROM parking_sessions WHERE vehicle_id = NEW.vehicle_id AND session_status = 'ACTIVE';
    IF active_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Vehicle already has an active parking session';
    END IF;
END;;
DELIMITER ;

-- STORED PROCEDURE: RegisterVehicleEntry
DELIMITER ;;
CREATE PROCEDURE RegisterVehicleEntry(IN p_number_plate VARCHAR(20), IN p_vehicle_type VARCHAR(10), OUT p_session_id INT, OUT p_slot_number VARCHAR(10), OUT p_message VARCHAR(200))
BEGIN
    DECLARE v_vehicle_id INT DEFAULT 0;
    DECLARE v_slot_id INT DEFAULT 0;
    DECLARE v_slot_num VARCHAR(10) DEFAULT NULL;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; SET p_session_id=-1; SET p_slot_number=NULL; SET p_message='DB error during entry'; END;
    START TRANSACTION;
    INSERT INTO vehicles (number_plate, vehicle_type) VALUES (p_number_plate, p_vehicle_type) ON DUPLICATE KEY UPDATE updated_at=NOW();
    SELECT vehicle_id INTO v_vehicle_id FROM vehicles WHERE number_plate = p_number_plate;
    IF EXISTS (SELECT 1 FROM parking_sessions WHERE vehicle_id=v_vehicle_id AND session_status='ACTIVE') THEN
        ROLLBACK; SET p_session_id=-2; SET p_slot_number=NULL; SET p_message='Vehicle already has an active session';
    ELSE
        SELECT slot_id, slot_number INTO v_slot_id, v_slot_num FROM parking_slots WHERE status='AVAILABLE' ORDER BY slot_id LIMIT 1 FOR UPDATE;  -- lock the row: concurrent entries cannot pick the same slot
        IF v_slot_id IS NULL THEN
            ROLLBACK; SET p_session_id=-3; SET p_slot_number=NULL; SET p_message='No available parking slots';
        ELSE
            INSERT INTO parking_sessions (vehicle_id, slot_id) VALUES (v_vehicle_id, v_slot_id);
            SET p_session_id=LAST_INSERT_ID(); SET p_slot_number=v_slot_num; SET p_message=CONCAT('Entry recorded. Slot: ',v_slot_num);
            COMMIT;
        END IF;
    END IF;
END;;
DELIMITER ;

-- STORED PROCEDURE: ProcessVehicleExit
DELIMITER ;;
CREATE PROCEDURE ProcessVehicleExit(IN p_number_plate VARCHAR(20), IN p_base_minutes INT, IN p_peak_minutes INT, IN p_base_amount DECIMAL(10,2), IN p_peak_amount DECIMAL(10,2), IN p_total_fare DECIMAL(10,2), IN p_is_rush_hour TINYINT, IN p_payment_method VARCHAR(10), OUT p_session_id INT, OUT p_message VARCHAR(200))
BEGIN
    DECLARE v_vehicle_id INT DEFAULT 0;
    DECLARE v_session_id INT DEFAULT 0;
    DECLARE v_entry_time DATETIME;
    DECLARE v_duration_sec INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; SET p_session_id=-1; SET p_message='DB error during exit'; END;
    START TRANSACTION;
    SELECT vehicle_id INTO v_vehicle_id FROM vehicles WHERE number_plate=p_number_plate;
    IF v_vehicle_id IS NULL THEN
        ROLLBACK; SET p_session_id=-2; SET p_message='Vehicle not found';
    ELSE
        SELECT session_id, entry_time INTO v_session_id, v_entry_time FROM parking_sessions WHERE vehicle_id=v_vehicle_id AND session_status='ACTIVE' ORDER BY entry_time DESC LIMIT 1;
        IF v_session_id IS NULL THEN
            ROLLBACK; SET p_session_id=-3; SET p_message='No active session found';
        ELSE
            SET v_duration_sec=TIMESTAMPDIFF(SECOND,v_entry_time,NOW());
            IF v_duration_sec<=0 THEN SET v_duration_sec=60; END IF;
            UPDATE parking_sessions SET exit_time=NOW(), duration_seconds=v_duration_sec, base_minutes=p_base_minutes, peak_minutes=p_peak_minutes, base_amount=p_base_amount, peak_amount=p_peak_amount, total_fare=p_total_fare, is_rush_hour=p_is_rush_hour, session_status='COMPLETED', payment_status='PAID', updated_at=NOW() WHERE session_id=v_session_id;
            INSERT INTO payments (session_id, amount, payment_method, payment_status) VALUES (v_session_id, p_total_fare, p_payment_method, 'SUCCESS');
            SET p_session_id=v_session_id; SET p_message=CONCAT('Exit processed. Fare: Rs.',p_total_fare);
            COMMIT;
        END IF;
    END IF;
END;;
DELIMITER ;

-- FUNCTION: CalculateParkingDuration
DELIMITER ;;
CREATE FUNCTION CalculateParkingDuration(p_entry_time DATETIME, p_exit_time DATETIME) RETURNS INT DETERMINISTIC
BEGIN
    DECLARE dur INT;
    SET dur=TIMESTAMPDIFF(SECOND,p_entry_time,p_exit_time);
    RETURN IF(dur<60,60,dur);
END;;
DELIMITER ;

-- FUNCTION: CalculateBaseFare
DELIMITER ;;
CREATE FUNCTION CalculateBaseFare(p_base_minutes INT, p_base_rate DECIMAL(8,4)) RETURNS DECIMAL(10,2) DETERMINISTIC
BEGIN
    RETURN ROUND(p_base_minutes * p_base_rate, 2);
END;;
DELIMITER ;

-- VIEWS
CREATE OR REPLACE VIEW active_parking_sessions AS
SELECT ps.session_id, v.number_plate, v.vehicle_type, sl.slot_number, sl.zone, ps.entry_time, TIMESTAMPDIFF(MINUTE,ps.entry_time,NOW()) AS minutes_parked
FROM parking_sessions ps JOIN vehicles v ON v.vehicle_id=ps.vehicle_id JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_status='ACTIVE';

CREATE OR REPLACE VIEW parking_history AS
SELECT ps.session_id, v.number_plate, v.vehicle_type, sl.slot_number, ps.entry_time, ps.exit_time, ps.duration_seconds, ps.base_minutes, ps.peak_minutes, ps.base_amount, ps.peak_amount, ps.total_fare, ps.is_rush_hour, ps.session_status, ps.payment_status, py.payment_method, py.payment_time
FROM parking_sessions ps JOIN vehicles v ON v.vehicle_id=ps.vehicle_id JOIN parking_slots sl ON sl.slot_id=ps.slot_id LEFT JOIN payments py ON py.session_id=ps.session_id ORDER BY ps.entry_time DESC;

CREATE OR REPLACE VIEW daily_revenue AS
SELECT DATE(ps.exit_time) AS revenue_date, COUNT(ps.session_id) AS total_sessions, SUM(ps.total_fare) AS total_revenue, AVG(ps.total_fare) AS avg_fare, MIN(ps.total_fare) AS min_fare, MAX(ps.total_fare) AS max_fare, SUM(ps.is_rush_hour) AS rush_hour_sessions
FROM parking_sessions ps WHERE ps.session_status='COMPLETED' AND ps.exit_time IS NOT NULL GROUP BY DATE(ps.exit_time) ORDER BY revenue_date DESC;

CREATE OR REPLACE VIEW slot_availability AS
SELECT slot_id, slot_number, slot_type, floor, zone, status, CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END AS is_available FROM parking_slots ORDER BY slot_id;

CREATE OR REPLACE VIEW vehicle_parking_history AS
SELECT v.vehicle_id, v.number_plate, v.vehicle_type, COUNT(ps.session_id) AS total_visits, SUM(ps.total_fare) AS total_spent, AVG(ps.total_fare) AS avg_fare_per_visit, MAX(ps.entry_time) AS last_visit, SUM(ps.is_rush_hour) AS rush_hour_visits
FROM vehicles v LEFT JOIN parking_sessions ps ON ps.vehicle_id=v.vehicle_id AND ps.session_status='COMPLETED' GROUP BY v.vehicle_id,v.number_plate,v.vehicle_type ORDER BY total_visits DESC;

CREATE OR REPLACE VIEW rush_hour_sessions AS
SELECT ps.session_id, v.number_plate, ps.entry_time, ps.exit_time, ps.base_amount, ps.peak_amount, ps.total_fare, ROUND((ps.peak_amount/NULLIF(ps.total_fare,0))*100,2) AS peak_pct
FROM parking_sessions ps JOIN vehicles v ON v.vehicle_id=ps.vehicle_id WHERE ps.is_rush_hour=1 AND ps.session_status='COMPLETED';
