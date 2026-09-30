-- ============================================================
-- seed.sql - Sample data for ParkingLot database
-- ============================================================

USE ParkingLot;

-- Parking Slots (30 slots matching PARKING_SLOTS in the app)
INSERT INTO parking_slots (slot_number, slot_type, floor, zone) VALUES
('1','STANDARD',1,'A'), ('2','STANDARD',1,'A'), ('3','STANDARD',1,'A'),
('4','STANDARD',1,'A'), ('5','STANDARD',1,'A'), ('6','STANDARD',1,'A'),
('7','STANDARD',1,'A'), ('8','STANDARD',1,'A'), ('9','STANDARD',1,'A'),
('10','STANDARD',1,'A'), ('11','STANDARD',1,'A'), ('12','STANDARD',1,'A'),
('13','STANDARD',1,'B'), ('14','STANDARD',1,'B'), ('15','STANDARD',1,'B'),
('16','STANDARD',1,'B'), ('17','STANDARD',1,'B'), ('18','STANDARD',1,'B'),
('19','COMPACT',1,'B'), ('20','COMPACT',1,'B'), ('21','COMPACT',1,'B'),
('22','COMPACT',2,'C'), ('23','COMPACT',2,'C'), ('24','COMPACT',2,'C'),
('25','LARGE',2,'C'), ('26','LARGE',2,'C'), ('27','LARGE',2,'C'),
('28','LARGE',2,'D'), ('29','LARGE',2,'D'), ('30','LARGE',2,'D');

-- Rush Hour Rules (mirrors parkinglot.c logic)
INSERT INTO rush_hours (description, rule_type, start_time, end_time, multiplier, is_active) VALUES
('Weekend (Sat/Sun) - All Day', 'WEEKEND', NULL, NULL, 1.19, 1),
('Evening Peak (6PM - 10PM)', 'TIMERANGE', '18:00:00', '22:00:00', 1.19, 1);

-- Pricing Rules (base_rate=0.67, peak_rate=0.80 from parkinglot.c)
INSERT INTO pricing_rules (vehicle_type, base_rate_per_min, peak_rate_per_min, effective_from, is_active) VALUES
('CAR',   0.6700, 0.8000, CURDATE(), 1),
('BIKE',  0.4000, 0.5000, CURDATE(), 1),
('TRUCK', 1.2000, 1.5000, CURDATE(), 1),
('OTHER', 0.6700, 0.8000, CURDATE(), 1);

-- Sample Vehicles
INSERT INTO vehicles (number_plate, vehicle_type, owner_name) VALUES
('MH12AB1234', 'CAR',  'Rohit Bhanose'),
('MH14CD5678', 'CAR',  'Priya Sharma'),
('MH01EF9012', 'BIKE', 'Amit Patel'),
('MH02GH3456', 'TRUCK','Suresh Transport'),
('MH04IJ7890', 'CAR',  'Kavita Nair'),
('MH06KL2345', 'CAR',  'Ravi Kumar'),
('MH09MN6789', 'BIKE', 'Sneha Joshi'),
('DL01OP1234', 'CAR',  'Anjali Singh');

-- Completed Sessions (historical data)
INSERT INTO parking_sessions (vehicle_id, slot_id, entry_time, exit_time, duration_seconds, base_minutes, peak_minutes, base_rate, peak_rate, base_amount, peak_amount, total_fare, is_rush_hour, session_status, payment_status) VALUES
(1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL '09:00:00' HOUR_SECOND,
       DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL '11:30:00' HOUR_SECOND,
       9000, 150, 0, 0.67, 0.80, 100.50, 0.00, 100.50, 0, 'COMPLETED', 'PAID'),
(2, 2, DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL '19:00:00' HOUR_SECOND,
       DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL '21:00:00' HOUR_SECOND,
       7200, 0, 120, 0.67, 0.80, 0.00, 96.00, 96.00, 1, 'COMPLETED', 'PAID'),
(3, 3, DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '08:00:00' HOUR_SECOND,
       DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '09:00:00' HOUR_SECOND,
       3600, 60, 0, 0.67, 0.80, 40.20, 0.00, 40.20, 0, 'COMPLETED', 'PAID'),
(4, 4, DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '10:00:00' HOUR_SECOND,
       DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '14:00:00' HOUR_SECOND,
       14400, 240, 0, 0.67, 0.80, 160.80, 0.00, 160.80, 0, 'COMPLETED', 'PAID'),
(5, 5, DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '18:30:00' HOUR_SECOND,
       DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL '20:30:00' HOUR_SECOND,
       7200, 0, 120, 0.67, 0.80, 0.00, 96.00, 96.00, 1, 'COMPLETED', 'PAID'),
(6, 6, NOW() - INTERVAL 5 HOUR, NOW() - INTERVAL 3 HOUR,
       7200, 120, 0, 0.67, 0.80, 80.40, 0.00, 80.40, 0, 'COMPLETED', 'PAID'),
(1, 7, NOW() - INTERVAL 3 HOUR, NOW() - INTERVAL 1 HOUR,
       7200, 0, 120, 0.67, 0.80, 0.00, 96.00, 96.00, 1, 'COMPLETED', 'PAID');

-- Payments for completed sessions
INSERT INTO payments (session_id, amount, payment_method, payment_status) VALUES
(1, 100.50, 'CASH', 'SUCCESS'),
(2, 96.00,  'UPI',  'SUCCESS'),
(3, 40.20,  'CASH', 'SUCCESS'),
(4, 160.80, 'CARD', 'SUCCESS'),
(5, 96.00,  'UPI',  'SUCCESS'),
(6, 80.40,  'CASH', 'SUCCESS'),
(7, 96.00,  'UPI',  'SUCCESS');

-- One Active Session (vehicle currently parked)
INSERT INTO parking_sessions (vehicle_id, slot_id, entry_time, session_status, payment_status) VALUES
(7, 8, NOW() - INTERVAL 45 MINUTE, 'ACTIVE', 'PENDING');
-- Note: trigger trg_slot_occupied_on_entry will mark slot 8 as OCCUPIED automatically
