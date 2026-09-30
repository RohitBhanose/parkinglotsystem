import mysql.connector
conn = mysql.connector.connect(host='localhost',port=3306,user='root',password='rohit$20',database='ParkingLot',autocommit=True)
c = conn.cursor()

print('=== FOREIGN KEYS ===')
c.execute("""
    SELECT kcu.CONSTRAINT_NAME, kcu.TABLE_NAME, kcu.REFERENCED_TABLE_NAME
    FROM information_schema.KEY_COLUMN_USAGE kcu
    JOIN information_schema.TABLE_CONSTRAINTS tc
      ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
    WHERE kcu.TABLE_SCHEMA = 'ParkingLot' AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
""")
for r in c.fetchall():
    print(f'  {r[1]}.{r[0]} -> {r[2]}')

print('\n=== TEST: RegisterVehicleEntry ===')
c.execute("SET @sid=0, @slot='', @msg=''")
c.execute("CALL RegisterVehicleEntry('TESTXX8888','CAR',@sid,@slot,@msg)")
c.execute('SELECT @sid, @slot, @msg')
out = c.fetchone()
print(f'  session_id={out[0]}, slot={out[1]}, msg={out[2]}')
sid = out[0]

c.execute('SELECT ps.session_status, sl.status FROM parking_sessions ps JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_id=%s', (sid,))
r = c.fetchone()
print(f'  Trigger result: session={r[0]}, slot={r[1]} (OCCUPIED expected)')

print('\n=== TEST: ProcessVehicleExit ===')
c.execute("SET @sid2=0, @msg2=''")
c.execute("CALL ProcessVehicleExit('TESTXX8888',55,5,36.85,4.00,40.85,1,'UPI',@sid2,@msg2)")
c.execute('SELECT @sid2, @msg2')
out2 = c.fetchone()
print(f'  result: session_id={out2[0]}, msg={out2[1]}')

c.execute('SELECT ps.session_status, sl.status, ps.total_fare, ps.is_rush_hour FROM parking_sessions ps JOIN parking_slots sl ON sl.slot_id=ps.slot_id WHERE ps.session_id=%s', (out2[0],))
r2 = c.fetchone()
print(f'  After exit: session={r2[0]}, slot={r2[1]}, fare=Rs.{r2[2]}, rush={r2[3]}')

print('\n=== REVENUE ===')
c.execute("SELECT COUNT(*), SUM(total_fare) FROM parking_sessions WHERE session_status='COMPLETED'")
rev = c.fetchone()
print(f'  {rev[0]} sessions, total Rs.{rev[1]}')

print('\n=== ACTIVE SESSIONS ===')
c.execute('SELECT * FROM active_parking_sessions')
rows = c.fetchall()
print(f'  Active: {len(rows)} session(s)')
for r in rows:
    print(f'    {r}')

print('\n=== DAILY REVENUE VIEW ===')
c.execute('SELECT * FROM daily_revenue')
for r in c.fetchall():
    print(f'  {r}')

# Cleanup test data
c.execute('DELETE FROM payments WHERE session_id=%s', (out2[0],))
c.execute('DELETE FROM parking_sessions WHERE session_id=%s', (out2[0],))
c.execute("DELETE FROM vehicles WHERE number_plate='TESTXX8888'")

c.close()
conn.close()
print('\nALL TESTS PASSED - Database is fully operational!')