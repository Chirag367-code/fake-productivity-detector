import sqlite3
import os

path = os.path.expanduser('~/.fpd-agent/agent_events.db')
print('DB path:', path)
print('DB exists:', os.path.exists(path))

if not os.path.exists(path):
    print("AGENT DATABASE NOT FOUND - Agent is NOT capturing data")
    exit(1)

conn = sqlite3.connect(path)
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [r[0] for r in rows])

for table in ['keystroke_events', 'mouse_events', 'window_events']:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    latest = conn.execute(f"SELECT MAX(timestamp) FROM {table}").fetchone()[0]
    print(f'{table}: count={count}, latest_timestamp={latest}')

conn.close()