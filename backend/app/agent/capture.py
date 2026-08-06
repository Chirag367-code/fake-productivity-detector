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
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Platform-appropriate window title detection
# ------------------------------------------------------------------
try:
    import sys as _sys

    if _sys.platform == "win32":
        import win32gui  # type: ignore

        def _get_active_window_title() -> str:
            """Get active window title on Windows using win32gui."""
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                return win32gui.GetWindowText(hwnd) or ""
            return ""
    else:
        # Linux / Mac fallback
        try:
            import Xlib.display  # type: ignore

            def _get_active_window_title() -> str:
                """Get active window title via X11 (Linux)."""
                try:
                    disp = Xlib.display.Display()
                    window = disp.get_input_focus().focus
                    wmname = window.get_wm_name()
                    disp.close()
                    return wmname or ""
                except Exception:
                    return ""
        except ImportError:
            # Mac fallback via pygetwindow
            try:
                import pygetwindow as gw  # type: ignore

                def _get_active_window_title() -> str:
                    try:
                        w = gw.getActiveWindow()
                        return w.title if w else ""
                    except Exception:
                        return ""
            except ImportError:
                # No library available — return empty string
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
    """Get (or create) the local SQLite database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _init_db() -> None:
    """Create event tables if they do not exist."""
    conn = _get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS keystroke_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,       -- time.time() seconds
                inter_key_ms REAL NOT NULL        -- ms since previous keystroke
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

            CREATE INDEX IF NOT EXISTS idx_keystroke_ts
                ON keystroke_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_mouse_ts
                ON mouse_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_window_ts
                ON window_events(timestamp);
            """
        )
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------
# Capture classes
# ------------------------------------------------------------------
class KeystrokeCapture:
    """
    Captures inter-key intervals (timing only — never which keys).

    Uses pynput.keyboard.Listener to observe key presses, recording only
    the time delta between successive key-down events.
    """

    def __init__(self) -> None:
        self._last_time: Optional[float] = None
        self._running = False
        self._listener = None
        self._conn_lock = threading.Lock()

    def _on_press(self, _key) -> None:
        """Callback for pynput key press — records only timing."""
        now = time.time()
        if self._last_time is not None:
            delta_ms = (now - self._last_time) * 1000.0
            # Ignore absurdly long gaps (likely computer was suspended)
            if delta_ms < 300_000:  # 5-minute cap
                conn = _get_connection()
                try:
                    with self._conn_lock:
                        conn.execute(
                            "INSERT INTO keystroke_events (timestamp, inter_key_ms) VALUES (?, ?)",
                            (now, delta_ms),
                        )
                        conn.commit()
                finally:
                    conn.close()
        self._last_time = now

    def start(self) -> None:
        """Start listening for keystroke timing events."""
        if self._running:
            return
        try:
            from pynput import keyboard  # type: ignore

            self._running = True
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.daemon = True
            self._listener.start()
            logger.info("Keystroke capture started (timing only)")
        except ImportError:
            logger.warning("pynput not installed — keystroke capture disabled")

    def stop(self) -> None:
        """Stop listening."""
        if self._listener and self._running:
            self._listener.stop()
            self._running = False
            logger.info("Keystroke capture stopped")


class MouseCapture:
    """
    Captures mouse movement vectors (position, velocity, direction changes).

    Uses pynput.mouse.Listener — records only x/y coordinates at each
    movement event. Click targets are never recorded.
    """

    def __init__(self) -> None:
        self._running = False
        self._listener = None
        self._conn_lock = threading.Lock()
        self._last_pos: Optional[tuple[float, float]] = None
        self._last_time: Optional[float] = None

    def _on_move(self, x: int, y: int) -> None:
        """Callback for mouse move — stores raw position."""
        now = time.time()
        conn = _get_connection()
        try:
            with self._conn_lock:
                conn.execute(
                    "INSERT INTO mouse_events (timestamp, x, y) VALUES (?, ?, ?)",
                    (now, float(x), float(y)),
                )
                conn.commit()
        finally:
            conn.close()
        self._last_pos = (float(x), float(y))
        self._last_time = now

    def start(self) -> None:
        """Start listening for mouse movement events."""
        if self._running:
            return
        try:
            from pynput import mouse  # type: ignore

            self._running = True
            self._listener = mouse.Listener(on_move=self._on_move)
            self._listener.daemon = True
            self._listener.start()
            logger.info("Mouse capture started (movement vectors only)")
        except ImportError:
            logger.warning("pynput not installed — mouse capture disabled")

    def stop(self) -> None:
        """Stop listening."""
        if self._listener and self._running:
            self._listener.stop()
            self._running = False
            logger.info("Mouse capture stopped")


class WindowCapture:
    """
    Captures active foreground window title at regular intervals.

    Only the window title string is recorded — never the content of the
    window.
    """

    def __init__(self, poll_interval: float = 5.0) -> None:
        self._running = False
        self._poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._last_title: str = ""
        self._conn_lock = threading.Lock()

    def _poll_loop(self) -> None:
        """Poll active window title on a timer."""
        while self._running:
            title = _get_active_window_title()
            if title and title != self._last_title:
                conn = _get_connection()
                try:
                    with self._conn_lock:
                        conn.execute(
                            "INSERT INTO window_events (timestamp, title) VALUES (?, ?)",
                            (time.time(), title),
                        )
                        conn.commit()
                finally:
                    conn.close()
                self._last_title = title
            # Sleep between polls (unless stopped during sleep)
            for _ in range(int(self._poll_interval * 10)):
                if not self._running:
                    return
                time.sleep(0.1)

    def start(self) -> None:
        """Start periodic window title capture."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Window title capture started (title only)")

    def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            logger.info("Window title capture stopped")


# ------------------------------------------------------------------
# Convenience: purge old raw events (keep only 14 days)
# ------------------------------------------------------------------
def purge_old_events(days: int = 14) -> None:
    """
    Delete raw events older than `days` to prevent unbounded storage growth.
    """
    cutoff = time.time() - days * 86_400
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM keystroke_events WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM mouse_events WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM window_events WHERE timestamp < ?", (cutoff,))
        conn.commit()
        logger.info(f"Purged events older than {days} days")
    finally:
        conn.close()


# ------------------------------------------------------------------
# Module-level init
# ------------------------------------------------------------------
_init_db()