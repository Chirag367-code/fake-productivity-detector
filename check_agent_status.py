import psutil
import sys

print("=== Checking for running agent processes ===")
found = False
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
    try:
        cmdline = p.info['cmdline'] or []
        cmd_str = ' '.join(cmdline).lower()
        if 'run_agent' in cmd_str or 'run_agent.py' in cmd_str:
            found = True
            print(f'  PID={p.info["pid"]}, status={p.info["status"]}')
            print(f'  CMD: {" ".join(cmdline[:5])}...')
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if not found:
    print("  No agent process found - agent is NOT running")

print()
print("=== Checking if backend is running ===")
import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:8000/health', timeout=3)
    print(f'  Backend IS running at http://localhost:8000')
    print(f'  Response: {resp.read().decode()[:100]}')
except Exception as e:
    print(f'  Backend is NOT running: {e}')

print()
print("=== Checking local database ===")
import sqlite3
import os
from datetime import datetime

path = os.path.expanduser('~/.fpd-agent/agent_events.db')
if os.path.exists(path):
    conn = sqlite3.connect(path)
    for table in ['keystroke_events', 'mouse_events', 'window_events']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        latest = conn.execute(f"SELECT MAX(timestamp) FROM {table}").fetchone()[0]
        if latest:
            dt = datetime.fromtimestamp(latest)
            print(f'  {table}: {count} events, latest={dt}')
        else:
            print(f'  {table}: {count} events')
    conn.close()
else:
    print(f'  Database not found at {path}')

print()
print("=== Checking config ===")
import json
config_path = os.path.expanduser('~/.fpd-agent/config.json')
if os.path.exists(config_path):
    cfg = json.loads(open(config_path).read())
    print(f'  user_id: {cfg.get("user_id")}')
    print(f'  backend_url: {cfg.get("backend_url")}')
    print(f'  opt_out: {cfg.get("opt_out")}')
    print(f'  last_sync_date: {cfg.get("last_sync_date")}')
    print(f'  api_key set: {bool(cfg.get("api_key"))}')
else:
    print(f'  Config not found at {config_path}')