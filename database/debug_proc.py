import mysql.connector

conn = mysql.connector.connect(host='localhost',port=3306,user='root',password='rohit$20',database='ParkingLot',autocommit=False)
c = conn.cursor()

# Test the stored procedure logic manually step by step
print('Testing stored proc logic manually...')

# Step 1: Insert vehicle
c.execute("INSERT INTO vehicles (number_plate, vehicle_type) VALUES ('TESTXX7777','CAR') ON DUPLICATE KEY UPDATE updated_at=NOW()")
conn.commit()
print('Step 1: Vehicle inserted')

# Step 2: Get vehicle_id
c.execute("SELECT vehicle_id FROM vehicles WHERE number_plate='TESTXX7777'")
vid = c.fetchone()[0]
print(f'Step 2: vehicle_id={vid}')

# Step 3: Check active session
c.execute("SELECT COUNT(*) FROM parking_sessions WHERE vehicle_id=%s AND session_status='ACTIVE'", (vid,))
cnt = c.fetchone()[0]
print(f'Step 3: active sessions={cnt}')

# Step 4: Find available slot
c.execute("SELECT slot_id, slot_number FROM parking_slots WHERE status='AVAILABLE' ORDER BY slot_id LIMIT 1")
slot_row = c.fetchone()
print(f'Step 4: available slot={slot_row}')

# Step 5: Insert session
if slot_row:
    c.execute("INSERT INTO parking_sessions (vehicle_id, slot_id) VALUES (%s,%s)", (vid, slot_row[0]))
    conn.commit()
    sess_id = c.lastrowid
    print(f'Step 5: session inserted, id={sess_id}')

    # Step 6: Verify slot occupied
    c.execute("SELECT status FROM parking_slots WHERE slot_id=%s", (slot_row[0],))
    slot_status = c.fetchone()[0]
    print(f'Step 6: slot status after trigger={slot_status}')

    print('\nNow testing DIRECT CALL approach...')
    # Exit via Python directly (not stored proc)
    c.execute("""
        UPDATE parking_sessions
        SET exit_time=NOW(), duration_seconds=3300,
            base_minutes=55, peak_minutes=0,
            base_amount=36.85, peak_amount=0.00, total_fare=36.85,
            is_rush_hour=0, session_status='COMPLETED', payment_status='PAID',
            updated_at=NOW()
        WHERE session_id=%s
    """, (sess_id,))
    c.execute("INSERT INTO payments (session_id, amount, payment_method, payment_status) VALUES (%s,36.85,'CASH','SUCCESS')", (sess_id,))
    conn.commit()
    print('Step 7: exit processed')

    # Check slot freed
    c.execute("SELECT status FROM parking_slots WHERE slot_id=%s", (slot_row[0],))
    slot_after = c.fetchone()[0]
    print(f'Step 8: slot after exit={slot_after} (AVAILABLE expected)')

    # Cleanup
    c.execute("DELETE FROM payments WHERE session_id=%s", (sess_id,))
    c.execute("DELETE FROM parking_sessions WHERE session_id=%s", (sess_id,))
    c.execute("DELETE FROM vehicles WHERE number_plate='TESTXX7777'")
    conn.commit()
    print('Cleanup done')

print('\nNow diagnosing stored procedure error...')
# Try calling with callproc (Python mysql-connector style)
conn2 = mysql.connector.connect(host='localhost',port=3306,user='root',password='rohit$20',database='ParkingLot',autocommit=True)
c2 = conn2.cursor()
try:
    args = ('DIAGTEST001', 'CAR', 0, '', '')
    result = c2.callproc('RegisterVehicleEntry', args)
    print(f'callproc result: {result}')
    # Fetch OUT via stored results
    for res in c2.stored_results():
        print(f'stored result: {res.fetchall()}')
except Exception as e:
    print(f'callproc error: {e}')

# Clean up if inserted
c2.execute("DELETE FROM parking_sessions WHERE vehicle_id=(SELECT vehicle_id FROM vehicles WHERE number_plate='DIAGTEST001')")
c2.execute("DELETE FROM vehicles WHERE number_plate='DIAGTEST001'")
c2.close()
conn2.close()

c.close()
conn.close()
print('\nDiagnostics complete')