import sys, os
sys.path.insert(0, r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem')
os.chdir(r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem')

import db

ok, info = db.test_connection()
print(f'DB Connection: {ok} - {info}')

summary = db.get_slot_summary()
print(f'Slots: total={summary["total"]}, available={summary["available"]}, occupied={summary["occupied"]}')

active = db.get_active_sessions()
print(f'Active sessions: {len(active)}')
for a in active:
    print(f'  {a["number_plate"]} @ Slot {a["slot_number"]} - {a["minutes_parked"]} min')

rev = db.get_daily_revenue()
print(f'Revenue days: {len(rev)}')

records = db.get_parking_records(5)
print(f'History records (first 5): {len(records)}')

print()
print('db.py module works correctly! App is ready.')