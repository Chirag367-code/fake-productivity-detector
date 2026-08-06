"""
Check if the agent is running and verify dependencies.
"""
import subprocess
import sys

# Check if agent process is running
try:
    import psutil
    agent_processes = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = p.info['cmdline'] or []
            if any('run_agent' in (c or '') for c in cmdline):
                agent_processes.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    print(f'Agent processes found: {len(agent_processes)}')
    for p in agent_processes:
        print(f'  PID={p.info["pid"]}, running={p.is_running()}')
except ImportError:
    print('psutil not installed - cannot check processes')

# Check dependencies
print('\n--- Checking dependencies ---')
deps = {
    'pynput': 'pynput',
    'httpx': 'httpx',
    'win32gui': 'pywin32',
}

for name, pkg in deps.items():
    try:
        __import__(name)
        print(f'  ✓ {pkg} ({name}) is installed')
    except ImportError:
        print(f'  ✗ {pkg} ({name}) is NOT installed')

# Check if backend is running
import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:8000/health', timeout=3)
    print(f'\n✓ Backend is running at http://localhost:8000')
    print(f'  Response: {resp.read().decode()[:100]}')
except Exception as e:
    print(f'\n✗ Backend is NOT running: {e}')