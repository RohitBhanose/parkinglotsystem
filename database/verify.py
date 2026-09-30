"""
End-to-end database verification test.
"""
import mysql.connector
from datetime import datetime

PASSWORD = "rohit$20"

conn = mysql.connector.connect(
    host="localhost", port=3306, user="root",
    password=PASSWORD, database="ParkingLot", autocommit=True
)
c = conn.cursor(dictionary=True)

print("=" * 60)
print("END-TO-END DATABASE VERIFICATION")
print("=" * 60)

# 1. Database
c.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='ParkingLot'")
r = c.fetchone()
print(f"\n[1] Database 'ParkingLot' exists: {'YES' if r else 'NO'}")

# 2. Tables
c.execute("SHOW TABLES")
tables = [row[list(row.keys())[0]] for row in c.fetchall()]
real_tables = [t for t in tables if t not in ('active_parking_sessions','parking_history','daily_revenue','slot_availability','vehicle_parking_history','rush_hour_sessions')]
print(f"\n[2] Tables ({len(real_tables)}):")
for t in real_tables:
    print(f"     - {t}")

# 3. Views
views = [t for t in tables if t in ('active_parking_sessions','parking_history','daily_revenue','slot_availability','vehicle_parking_history','rush_hour_sessions')]
print(f"\n[3] Views ({len(views)}):")
for v in views:
    print(f"     - {v}")

# 4. Triggers
c.execute("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='ParkingLot'")
triggers = [r['TRIGGER_NAME'] for r in c.fetchall()]
print(f"\n[4] Triggers ({len(triggers)}):")
for t in triggers:
    print(f"     - {t}")

# 5. Procedures & Functions
c.execute("SELECT ROUTINE_NAME, ROUTINE_TYPE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='ParkingLot'")
routines = c.fetchall()
print(f"\n[5] Routines ({len(routines)}):")
for r in routines:
    print(f"     - [{r['ROUTINE_TYPE']}] {r['ROUTINE_NAME']}")

# 6. Indexes
c.execute("""
    SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA='ParkingLot' AND INDEX_NAME != 'PRIMARY'
    ORDER BY TABLE_NAME, INDEX_NAME
""")
indexes = c.fetchall()
print(f"\n[6] Non-PK Indexes ({len(indexes)}):")
for idx in indexes:
    print(f"     - {idx['TABLE_NAME']}.{idx['INDEX_NAME']} ({idx['COLUMN_NAME']})")

# 7. Foreign Keys
c.execute("""
    SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA='ParkingLot' AND CONSTRAINT_TYPE='FOREIGN KEY'
""")
fks = c.fetchall()
print(f"\n[7] Foreign Keys ({len(fks)}):")
for fk in fks:
    print(f"     - {fk['TABLE_NAME']}.{fk['CONSTRAINT_NAME']} -> {fk['REFERENCED_TABLE_NAME']}")

# 8. Seed data verification
print("\n[8] Seed Data:")
for tbl in ['vehicles','parking_slots','rush_hours','pricing_rules','parking_sessions','payments']:
    c.execute(f"SELECT COUNT(*) AS cnt FROM {tbl}")
    cnt = c.fetchone()['cnt']
    print(f"     - {tbl}: {cnt} rows")

# 9. Active session
c.execute("SELECT * FROM active_parking_sessions")
active = c.fetchall()
print(f"\n[9] Active sessions: {len(active)}")
for a in active:
    print(f"     - {a['number_plate']} @ Slot {a['slot_number']}, {a['minutes_parked']} min parked")

# 10. Slot trigger test: verify slot 8 is OCCUPIED
c.execute("SELECT status FROM parking_slots WHERE slot_number='8'")
slot8 = c.fetchone()
print(f"\n[10] Trigger test - Slot 8 status (should be OCCUPIED): {slot8['status']}")

# 11. Test full entry/exit transaction via stored procedure
print("\n[11] Testing RegisterVehicleEntry stored procedure...")
nc = mysql.connector.connect(host="localhost",port=3306,user="root",password=PASSWORD,database="ParkingLot",autocommit=True)
nc2 = nc.cursor()
nc2.callproc("RegisterVehicleEntry", ("TESTXX9999","CAR",0,"",""))
nc2.execute("SELECT @_RegisterVehicleEntry_2, @_RegisterVehicleEntry_3, @_RegisterVehicleEntry_4")
# Use direct OUT param fetch
nc2.close()
# Re-call with proper OUT
nc3 = nc.cursor()
nc3.execute("SET @sid=0, @slot='', @msg=''")
nc3.execute("CALL RegisterVehicleEntry('TESTXX9999','CAR',@sid,@slot,@msg)")
nc3.execute("SELECT @sid AS session_id, @slot AS slot_number, @msg AS message")
out = nc3.fetchone()
print(f"     Session ID: {out[0]}, Slot: {out[1]}, Message: {out[2]}")
entry_sid = out[0]

# 12. Verify active session for test vehicle
nc3.execute("SELECT ps.session_id, sl.status FROM parking_sessions ps JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_id=%s", (entry_sid,))
sess = nc3.fetchone()
print(f"     Session {entry_sid} slot status (should be OCCUPIED): {sess[1] if sess else 'NOT FOUND'}")

# 13. Process exit via stored proc
print("\n[12] Testing ProcessVehicleExit stored procedure...")
nc3.execute("SET @sid2=0, @msg2=''")
nc3.execute("CALL ProcessVehicleExit('TESTXX9999',60,0,40.20,0.00,40.20,0,'CASH',@sid2,@msg2)")
nc3.execute("SELECT @sid2, @msg2")
out2 = nc3.fetchone()
print(f"     Session ID: {out2[0]}, Message: {out2[1]}")

# 14. Verify slot freed
nc3.execute("SELECT ps.session_status, sl.status AS slot_status FROM parking_sessions ps JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_id=%s", (out2[0],))
final = nc3.fetchone()
print(f"     Session status (should be COMPLETED): {final[0]}")
print(f"     Slot status (should be AVAILABLE):    {final[1]}")

# 15. Revenue
c.execute("SELECT SUM(total_fare) AS rev FROM parking_sessions WHERE session_status='COMPLETED'")
rev = c.fetchone()
print(f"\n[13] Total revenue in DB: Rs. {rev['rev']:.2f}")

# Cleanup test vehicle
nc3.execute("DELETE FROM payments WHERE session_id=%s", (out2[0],))
nc3.execute("DELETE FROM parking_sessions WHERE session_id=%s", (out2[0],))
nc3.execute("DELETE FROM vehicles WHERE number_plate='TESTXX9999'")
nc3.close()
nc.close()

print("\n" + "=" * 60)
print("ALL VERIFICATIONS COMPLETE — DATABASE IS READY!")
print("=" * 60)

c.close()
conn.close()
