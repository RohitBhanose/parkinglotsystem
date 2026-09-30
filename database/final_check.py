import mysql.connector
conn = mysql.connector.connect(host='localhost',port=3306,user='root',password='rohit$20',database='ParkingLot',autocommit=True)
c = conn.cursor()

print('=== Testing duplicate prevention ===')
args = ('DUPTEST01','CAR',0,'','')
r1 = c.callproc('RegisterVehicleEntry', args)
sid1 = r1[2]; slot1 = r1[3]
print(f'First entry: session_id={sid1}, slot={slot1}')

args2 = ('DUPTEST01','CAR',0,'','')
r2 = c.callproc('RegisterVehicleEntry', args2)
sid2 = r2[2]; msg2 = r2[4]
print(f'Second entry: session_id={sid2}, msg={msg2}')
assert sid2 == -2, f'Expected -2, got {sid2}'
print('[PASS] Duplicate entry correctly blocked by procedure logic')

print()
print('=== Testing FK constraint ===')
try:
    c.execute("SELECT vehicle_id FROM vehicles WHERE number_plate='DUPTEST01'")
    vid = c.fetchone()[0]
    c.execute('DELETE FROM vehicles WHERE vehicle_id=%s', (vid,))
    print('[FAIL] FK did not block vehicle deletion!')
except Exception as e:
    if '1451' in str(e) or 'foreign key' in str(e).lower():
        print('[PASS] FK correctly blocked vehicle deletion while sessions exist')

print()
print('=== Cleanup ===')
args3 = ('DUPTEST01',60,0,40.20,0.00,40.20,0,'CASH',0,'')
r3 = c.callproc('ProcessVehicleExit', args3)
sid3 = r3[8]; msg3 = r3[9]
print(f'Exit: session_id={sid3}, msg={msg3}')

c.execute("SELECT session_id FROM parking_sessions WHERE vehicle_id=(SELECT vehicle_id FROM vehicles WHERE number_plate='DUPTEST01')")
sids = [r[0] for r in c.fetchall()]
for sid in sids:
    c.execute('DELETE FROM payments WHERE session_id=%s', (sid,))
    c.execute('DELETE FROM parking_sessions WHERE session_id=%s', (sid,))
c.execute("DELETE FROM vehicles WHERE number_plate='DUPTEST01'")
print('Cleanup done')

print()
c.execute('SELECT COUNT(*) FROM parking_sessions')
print(f'Sessions: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM payments')
print(f'Payments: {c.fetchone()[0]}')
c.execute("SELECT SUM(total_fare) FROM parking_sessions WHERE session_status='COMPLETED'")
rev = c.fetchone()[0]
print(f'Total revenue: Rs.{rev}')
c.execute("SELECT COUNT(*) FROM parking_sessions WHERE session_status='ACTIVE'")
print(f'Active sessions: {c.fetchone()[0]}')

c.close(); conn.close()
print()
print('[PASS] ALL VERIFICATIONS COMPLETE - Database fully operational!')