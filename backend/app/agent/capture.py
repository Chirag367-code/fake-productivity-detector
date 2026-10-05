"""
Raw behavioral event capture module.

Captures ONLY passive metadata:
  - Keystroke timing: inter-key intervals, typing speed, pause duration
    (never WHICH keys were pressed or their content)
  - Mouse movement vectors: velocity, acceleration, directional change frequency
    (never click targets or on-screen content)
  - Active foreground window TITLE (e.g. "Visual Studio Code")
    (never window content)

All raw events are buffered locally in an SQLite database and are NEVER
sent over the network.
"""

import logging
import sqlite3
import threading
import time
import queue
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Platform-appropriate window title detection
# ------------------------------------------------------------------
try:
    if sys.platform == "win32":
        import win32gui  # type: ignore
        def _get_active_window_title() -> str:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                return win32gui.GetWindowText(hwnd) or ""
            return ""
    else:
        try:
            import Xlib.display  # type: ignore
            def _get_active_window_title() -> str:
                try:
                    disp = Xlib.display.Display()
                    window = disp.get_input_focus().focus
                    wmname = window.get_wm_name()
                    disp.close()
                    return wmname or ""
                except Exception:
                    return ""
        except ImportError:
            try:
                import pygetwindow as gw  # type: ignore
                def _get_active_window_title() -> str:
                    try:
                        w = gw.getActiveWindow()
                        return w.title if w else ""
                    except Exception:
                        return ""
            except ImportError:
                def _get_active_window_title() -> str:
                    return ""
except Exception:
    def _get_active_window_title() -> str:
        return ""


# ------------------------------------------------------------------
# SQLite local event store
# ------------------------------------------------------------------
DB_PATH = Path.home() / ".fpd-agent" / "agent_events.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _init_db() -> None:
    conn = _get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS keystroke_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,       
                inter_key_ms REAL NOT NULL        
            );
            CREATE TABLE IF NOT EXISTS mouse_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                x           REAL NOT NULL,
                y           REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS window_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                title       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_keystroke_ts ON keystroke_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_mouse_ts ON mouse_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_window_ts ON window_events(timestamp);
            """
        )
        
        # Idempotent schema migration for rich timings and injection flags
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(keystroke_events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "dwell_ms" not in columns:
            conn.execute("ALTER TABLE keystroke_events ADD COLUMN dwell_ms REAL DEFAULT 0")
        if "flight_ms" not in columns:
            conn.execute("ALTER TABLE keystroke_events ADD COLUMN flight_ms REAL DEFAULT 0")
        if "is_modifier" not in columns:
            conn.execute("ALTER TABLE keystroke_events ADD COLUMN is_modifier INTEGER DEFAULT 0")
        if "is_injected" not in columns:
            conn.execute("ALTER TABLE keystroke_events ADD COLUMN is_injected INTEGER DEFAULT 0")
            
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------
# Background Event Writer (Non-blocking I/O)
# ------------------------------------------------------------------
event_queue = queue.Queue()
_writer_thread = None
_writer_running = False

def _event_writer_loop():
    conn = _get_connection()
    while _writer_running:
        try:
            events = []
            try:
                events.append(event_queue.get(timeout=1.0))
            except queue.Empty:
                continue
                
            while True:
                try:
                    events.append(event_queue.get_nowait())
                except queue.Empty:
                    break
                    
            if events:
                key_events = [e for e in events if e[0] == 'key']
                mouse_events = [e for e in events if e[0] == 'mouse']
                win_events = [e for e in events if e[0] == 'window']
                
                if key_events:
                    conn.executemany(
                        "INSERT INTO keystroke_events (timestamp, inter_key_ms, dwell_ms, flight_ms, is_modifier, is_injected) VALUES (?, ?, ?, ?, ?, ?)",
                        [(e[1], e[2], e[3], e[4], e[5], e[6]) for e in key_events]
                    )
                if mouse_events:
                    conn.executemany(
                        "INSERT INTO mouse_events (timestamp, x, y) VALUES (?, ?, ?)",
                        [(e[1], e[2], e[3]) for e in mouse_events]
                    )
                if win_events:
                    conn.executemany(
                        "INSERT INTO window_events (timestamp, title) VALUES (?, ?)",
                        [(e[1], e[2]) for e in win_events]
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Event writer error: {e}")
            time.sleep(1)
    conn.close()

def _start_writer():
    global _writer_thread, _writer_running
    if not _writer_running:
        _writer_running = True
        _writer_thread = threading.Thread(target=_event_writer_loop, daemon=True)
        _writer_thread.start()


# ------------------------------------------------------------------
# Low-level Windows Hook Filter
# ------------------------------------------------------------------
_thread_local = threading.local()

def _win32_event_filter(msg, data):
    """
    Filter to capture the LLKHF_INJECTED flag from Windows KBDLLHOOKSTRUCT.
    MUST run quickly and return True to avoid suppressing legit events.
    """
    try:
        flags = data.flags
        # 0x10 = LLKHF_INJECTED (SendInput), 0x02 = LLKHF_LOWER_IL_INJECTED (JournalPlayback)
        _thread_local.is_injected = bool(flags & 0x10 or flags & 0x02)
    except AttributeError:
        _thread_local.is_injected = False
    
    return True # NEVER suppress the event!


# ------------------------------------------------------------------
# Capture classes
# ------------------------------------------------------------------
class KeystrokeCapture:
    def __init__(self) -> None:
        self._keys_down = {}  
        self._last_press_perf: Optional[float] = None
        self._last_release_perf: Optional[float] = None
        self._running = False
        self._thread = None

    def _is_modifier(self, key) -> bool:
        try:
            name = getattr(key, "name", "").lower()
            return any(m in name for m in ['shift', 'ctrl', 'alt', 'cmd', 'menu', 'caps_lock'])
        except Exception:
            return False

    def _on_press(self, key) -> None:
        try:
            if key is None:
                return

            if key in self._keys_down:
                return  # Filter auto-repeat

            now_perf = time.perf_counter()
            now_wall = time.time()

            inter_key_ms = 0.0
            if self._last_press_perf is not None:
                inter_key_ms = (now_perf - self._last_press_perf) * 1000.0

            flight_ms = 0.0
            if self._last_release_perf is not None:
                flight_ms = (now_perf - self._last_release_perf) * 1000.0
            
            is_mod = 1 if self._is_modifier(key) else 0
            
            # Read real injected flag from the win32 event filter
            is_injected = 1 if getattr(_thread_local, 'is_injected', False) else 0

            self._keys_down[key] = (now_perf, now_wall, inter_key_ms, flight_ms, is_mod, is_injected)
            self._last_press_perf = now_perf
        except Exception as e:
            logger.debug(f"Error in on_press: {e}")

    def _on_release(self, key) -> None:
        try:
            if key is None:
                return
                
            now_perf = time.perf_counter()
            self._last_release_perf = now_perf

            if key in self._keys_down:
                press_perf, press_wall, inter_key_ms, flight_ms, is_mod, is_injected = self._keys_down.pop(key)
                dwell_ms = (now_perf - press_perf) * 1000.0
                
                if inter_key_ms < 300_000:
                    event_queue.put(('key', press_wall, inter_key_ms, dwell_ms, flight_ms, is_mod, is_injected))
        except Exception as e:
            logger.debug(f"Error in on_release: {e}")

    def _run_listener(self) -> None:
        from pynput import keyboard
        
        kwargs = {}
        if sys.platform == "win32":
            kwargs["win32_event_filter"] = _win32_event_filter

        while self._running:
            try:
                with keyboard.Listener(on_press=self._on_press, on_release=self._on_release, **kwargs) as listener:
                    listener.join()
            except Exception as e:
                logger.error(f"Keystroke listener crashed: {e}. Restarting...")
                time.sleep(1)

    def start(self) -> None:
        if self._running:
            return
        try:
            _start_writer()
            self._running = True
            self._thread = threading.Thread(target=self._run_listener, daemon=True)
            self._thread.start()
            logger.info("Keystroke capture started (timing only)")
        except ImportError:
            logger.warning("pynput not installed — keystroke capture disabled")

    def stop(self) -> None:
        self._running = False
        logger.info("Keystroke capture stopped")


class MouseCapture:
    def __init__(self) -> None:
        self._running = False
        self._thread = None
        self._last_pos: Optional[tuple[float, float]] = None

    def _on_move(self, x: int, y: int) -> None:
        event_queue.put(('mouse', time.time(), float(x), float(y)))
        self._last_pos = (float(x), float(y))

    def _run_listener(self) -> None:
        from pynput import mouse
        while self._running:
            try:
                with mouse.Listener(on_move=self._on_move) as listener:
                    listener.join()
            except Exception as e:
                logger.error(f"Mouse listener crashed: {e}. Restarting...")
                time.sleep(1)

    def start(self) -> None:
        if self._running:
            return
        try:
            _start_writer()
            self._running = True
            self._thread = threading.Thread(target=self._run_listener, daemon=True)
            self._thread.start()
            logger.info("Mouse capture started")
        except ImportError:
            logger.warning("pynput not installed")

    def stop(self) -> None:
        self._running = False


class WindowCapture:
    def __init__(self, poll_interval: float = 5.0) -> None:
        self._running = False
        self._poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._last_title: str = ""

    def _poll_loop(self) -> None:
        while self._running:
            title = _get_active_window_title()
            if title and title != self._last_title:
                event_queue.put(('window', time.time(), title))
                self._last_title = title
            for _ in range(int(self._poll_interval * 10)):
                if not self._running:
                    return
                time.sleep(0.1)

    def start(self) -> None:
        if self._running:
            return
        _start_writer()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Window title capture started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


def purge_old_events(days: int = 14) -> None:
    cutoff = time.time() - days * 86_400
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM keystroke_events WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM mouse_events WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM window_events WHERE timestamp < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()

_init_db()