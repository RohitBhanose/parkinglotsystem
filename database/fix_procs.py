import mysql.connector

conn = mysql.connector.connect(host='localhost',port=3306,user='root',password='rohit$20',database='ParkingLot',autocommit=True)
c = conn.cursor()

# Drop and recreate procedures without EXIT HANDLER causing rollback confusion
c.execute('DROP PROCEDURE IF EXISTS RegisterVehicleEntry')
c.execute('''
CREATE PROCEDURE RegisterVehicleEntry(
    IN p_number_plate VARCHAR(20),
    IN p_vehicle_type VARCHAR(10),
    OUT p_session_id INT,
    OUT p_slot_number VARCHAR(10),
    OUT p_message VARCHAR(200)
)
BEGIN
    DECLARE v_vehicle_id INT DEFAULT NULL;
    DECLARE v_slot_id    INT DEFAULT NULL;
    DECLARE v_slot_num   VARCHAR(10) DEFAULT NULL;

    -- Upsert vehicle
    INSERT INTO vehicles (number_plate, vehicle_type)
    VALUES (p_number_plate, p_vehicle_type)
    ON DUPLICATE KEY UPDATE updated_at = NOW();

    SELECT vehicle_id INTO v_vehicle_id
    FROM vehicles WHERE number_plate = p_number_plate;

    -- Check existing active session
    IF EXISTS (SELECT 1 FROM parking_sessions WHERE vehicle_id = v_vehicle_id AND session_status = 'ACTIVE') THEN
        SET p_session_id  = -2;
        SET p_slot_number = NULL;
        SET p_message     = 'Vehicle already has an active session';
    ELSE
        SELECT slot_id, slot_number INTO v_slot_id, v_slot_num
        FROM parking_slots WHERE status = 'AVAILABLE' ORDER BY slot_id LIMIT 1;

        IF v_slot_id IS NULL THEN
            SET p_session_id  = -3;
            SET p_slot_number = NULL;
            SET p_message     = 'No available parking slots';
        ELSE
            INSERT INTO parking_sessions (vehicle_id, slot_id)
            VALUES (v_vehicle_id, v_slot_id);

            SET p_session_id  = LAST_INSERT_ID();
            SET p_slot_number = v_slot_num;
            SET p_message     = CONCAT('Entry recorded. Slot: ', v_slot_num);
        END IF;
    END IF;
END
''')
print('RegisterVehicleEntry recreated')

c.execute('DROP PROCEDURE IF EXISTS ProcessVehicleExit')
c.execute('''
CREATE PROCEDURE ProcessVehicleExit(
    IN p_number_plate   VARCHAR(20),
    IN p_base_minutes   INT,
    IN p_peak_minutes   INT,
    IN p_base_amount    DECIMAL(10,2),
    IN p_peak_amount    DECIMAL(10,2),
    IN p_total_fare     DECIMAL(10,2),
    IN p_is_rush_hour   TINYINT,
    IN p_payment_method VARCHAR(10),
    OUT p_session_id    INT,
    OUT p_message       VARCHAR(200)
)
BEGIN
    DECLARE v_vehicle_id   INT DEFAULT NULL;
    DECLARE v_session_id   INT DEFAULT NULL;
    DECLARE v_entry_time   DATETIME;
    DECLARE v_duration_sec INT DEFAULT 60;

    SELECT vehicle_id INTO v_vehicle_id
    FROM vehicles WHERE number_plate = p_number_plate;

    IF v_vehicle_id IS NULL THEN
        SET p_session_id = -2;
        SET p_message    = 'Vehicle not found';
    ELSE
        SELECT session_id, entry_time INTO v_session_id, v_entry_time
        FROM parking_sessions
        WHERE vehicle_id = v_vehicle_id AND session_status = 'ACTIVE'
        ORDER BY entry_time DESC LIMIT 1;

        IF v_session_id IS NULL THEN
            SET p_session_id = -3;
            SET p_message    = 'No active session found';
        ELSE
            SET v_duration_sec = GREATEST(60, TIMESTAMPDIFF(SECOND, v_entry_time, NOW()));

            UPDATE parking_sessions
            SET exit_time        = NOW(),
                duration_seconds = v_duration_sec,
                base_minutes     = p_base_minutes,
                peak_minutes     = p_peak_minutes,
                base_amount      = p_base_amount,
                peak_amount      = p_peak_amount,
                total_fare       = p_total_fare,
                is_rush_hour     = p_is_rush_hour,
                session_status   = 'COMPLETED',
                payment_status   = 'PAID',
                updated_at       = NOW()
            WHERE session_id = v_session_id;

            INSERT INTO payments (session_id, amount, payment_method, payment_status)
            VALUES (v_session_id, p_total_fare, p_payment_method, 'SUCCESS');

            SET p_session_id = v_session_id;
            SET p_message    = CONCAT('Exit processed. Fare: Rs.', p_total_fare);
        END IF;
    END IF;
END
''')
print('ProcessVehicleExit recreated')

# Test RegisterVehicleEntry
args = ('TESTPROCX1', 'CAR', 0, '', '')
result = c.callproc('RegisterVehicleEntry', args)
print(f'Entry result: session_id={result[2]}, slot={result[3]}, msg={result[4]}')
sid = result[2]

if sid and sid > 0:
    # Test ProcessVehicleExit
    args2 = ('TESTPROCX1', 60, 0, 40.20, 0.00, 40.20, 0, 'CASH', 0, '')
    result2 = c.callproc('ProcessVehicleExit', args2)
    print(f'Exit result: session_id={result2[8]}, msg={result2[9]}')

    # Verify
    c.execute('SELECT ps.session_status, sl.status, ps.total_fare FROM parking_sessions ps JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_id=%s', (result2[8],))
    row = c.fetchone()
    print(f'Final state: session={row[0]}, slot={row[1]}, fare={row[2]}')

    # Cleanup
    c.execute('DELETE FROM payments WHERE session_id=%s', (result2[8],))
    c.execute('DELETE FROM parking_sessions WHERE session_id=%s', (result2[8],))
    c.execute("DELETE FROM vehicles WHERE number_plate='TESTPROCX1'")

c.close()
conn.close()
print('Procedures fixed and verified!')