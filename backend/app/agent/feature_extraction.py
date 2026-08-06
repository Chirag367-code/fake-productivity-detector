"""
Feature extraction module.

Converts a day's buffered raw events (from the local SQLite store) into
aggregate statistical features used by the authenticity scorer.

Extracted features:
  - avg_typing_speed: mean inter-key interval (ms) — lower = faster typing
  - typing_rhythm_variance: std dev of inter-key intervals
  - pause_ratio: fraction of gaps > 2 seconds (idle pauses)
  - mouse_velocity_mean: mean mouse movement speed (px/s)
  - mouse_velocity_std: std dev of mouse velocity
  - mouse_direction_change_freq: how often direction changes per minute
  - active_window_categories: breakdown of time spent per window category
  - total_events: total number of captured events for the day
"""

import logging
import math
import sqlite3
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .capture import DB_PATH, _get_connection

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Window category keyword matching
# ------------------------------------------------------------------
WINDOW_CATEGORIES: Dict[str, List[str]] = {
    "Code/IDE": ["visual studio", "vscode", "code", "intellij", "pycharm", "sublime", "atom", "vim", "emacs", "xcode", "android studio", "eclipse", "netbeans"],
    "Word/Office": ["word", "excel", "powerpoint", "outlook", "office", "onenote", "notion", "docs", "sheets", "slides", "libreoffice", "openoffice"],
    "Browser": ["chrome", "firefox", "edge", "brave", "opera", "safari", "chromium", "tor browser", "vivaldi"],
    "Communication": ["slack", "discord", "teams", "zoom", "telegram", "whatsapp", "signal", "messenger", "skype", "mattermost", "rocket.chat"],
    "Entertainment": ["youtube", "netflix", "spotify", "twitch", "hulu", "disney+", "prime video", "vlc", "media player", "game", "steam", "epic games"],
    "Terminal/CLI": ["terminal", "cmd", "powershell", "bash", "zsh", "wsl", "putty", "ssh", "command prompt", "windows terminal", "iterm"],
    "Email": ["gmail", "outlook mail", "thunderbird", "mail", "protonmail", "yahoo mail"],
    "Design": ["photoshop", "figma", "sketch", "illustrator", "canva", "gimp", "blender", "after effects", "premiere", "lightroom"],
    "Other": [],
}

DEFAULT_CATEGORY = "Other"


def _categorize_window(title: str) -> str:
    """Match a window title to a category using keyword heuristics."""
    lower = title.lower()
    for category, keywords in WINDOW_CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return category
    return DEFAULT_CATEGORY


# ------------------------------------------------------------------
# Feature extraction
# ------------------------------------------------------------------
def _get_day_range(target_date: date) -> Tuple[float, float]:
    """Get (start_ts, end_ts) for a given date in local time."""
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    # Convert to epoch seconds (naive — assumes local timezone)
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    return start_ts, end_ts


def extract_features(target_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Extract aggregate features from raw events for a given day.

    Args:
        target_date: The date to extract features for. Defaults to today.

    Returns:
        Dict with keys:
          - avg_typing_speed (float): mean inter-key interval in ms
          - typing_rhythm_variance (float): std dev of inter-key intervals
          - pause_ratio (float): fraction of gaps > 2s
          - mouse_velocity_mean (float): mean mouse speed (px/s)
          - mouse_velocity_std (float): std dev of mouse speed
          - mouse_direction_change_freq (float): direction changes per minute
          - active_window_categories (List[Dict]): [{category, seconds}, ...]
          - total_keystrokes (int)
          - total_mouse_events (int)
          - total_window_events (int)
          - total_active_seconds (float): estimated active time
    """
    if target_date is None:
        target_date = date.today()

    start_ts, end_ts = _get_day_range(target_date)
    conn = _get_connection()
    features: Dict[str, Any] = {}

    try:
        # ---- Keystroke features ----
        rows = conn.execute(
            "SELECT inter_key_ms FROM keystroke_events WHERE timestamp >= ? AND timestamp <= ?",
            (start_ts, end_ts),
        ).fetchall()

        intervals = [r[0] for r in rows]
        total_keystrokes = len(intervals)

        if intervals:
            # Separate true typing intervals from pauses (> 2s) so the
            # average typing speed reflects active typing only. Pauses are
            # counted separately in pause_ratio — otherwise the same pause
            # would be punished twice in the authenticity score.
            typing_intervals = [x for x in intervals if x <= 2000]
            num_pauses = sum(1 for x in intervals if x > 2000)
            pause_ratio = num_pauses / len(intervals)

            if typing_intervals:
                avg_typing_speed = sum(typing_intervals) / len(typing_intervals)
                variance = (
                    sum((x - avg_typing_speed) ** 2 for x in typing_intervals)
                    / len(typing_intervals)
                )
                typing_rhythm_variance = math.sqrt(variance)
            else:
                avg_typing_speed = 0.0
                typing_rhythm_variance = 0.0
        else:
            avg_typing_speed = 0.0
            typing_rhythm_variance = 0.0
            pause_ratio = 0.0

        features["avg_typing_speed"] = round(avg_typing_speed, 2)
        features["typing_rhythm_variance"] = round(typing_rhythm_variance, 2)
        features["pause_ratio"] = round(pause_ratio, 4)
        features["total_keystrokes"] = total_keystrokes

        # ---- Mouse features ----
        rows = conn.execute(
            "SELECT timestamp, x, y FROM mouse_events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            (start_ts, end_ts),
        ).fetchall()

        total_mouse_events = len(rows)
        velocities: List[float] = []
        direction_changes = 0
        prev_angle: Optional[float] = None

        for i in range(1, len(rows)):
            t1, x1, y1 = rows[i - 1]
            t2, x2, y2 = rows[i]
            dt = t2 - t1
            if dt <= 0:
                continue
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy)
            if dist == 0:
                continue  # no movement — not a velocity sample
            vel = dist / dt
            # High-frequency mice emit events only 1-2ms apart, which can
            # produce absurd velocity readings (10,000+ px/s) that are not
            # representative of human input. Clamp to a realistic ceiling.
            vel = min(vel, 3000.0)
            velocities.append(vel)

            # Direction change detection
            angle = math.atan2(dy, dx)
            if prev_angle is not None:
                diff = abs(angle - prev_angle)
                if diff > math.radians(45):  # > 45° = direction change
                    direction_changes += 1
            prev_angle = angle

        if velocities:
            mouse_velocity_mean = sum(velocities) / len(velocities)
            mouse_velocity_std = math.sqrt(
                sum((v - mouse_velocity_mean) ** 2 for v in velocities) / len(velocities)
            )
        else:
            mouse_velocity_mean = 0.0
            mouse_velocity_std = 0.0

        # Direction changes per minute
        if len(rows) >= 2:
            time_span_min = (rows[-1][0] - rows[0][0]) / 60.0
            dir_change_freq = direction_changes / time_span_min if time_span_min > 0 else 0.0
        else:
            dir_change_freq = 0.0

        features["mouse_velocity_mean"] = round(mouse_velocity_mean, 2)
        features["mouse_velocity_std"] = round(mouse_velocity_std, 2)
        features["mouse_direction_change_freq"] = round(dir_change_freq, 2)
        features["total_mouse_events"] = total_mouse_events

        # ---- Window category features ----
        rows = conn.execute(
            "SELECT timestamp, title FROM window_events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            (start_ts, end_ts),
        ).fetchall()

        total_window_events = len(rows)
        category_seconds: Dict[str, float] = {}
        prev_ts: Optional[float] = None
        prev_cat: Optional[str] = None

        for ts, title in rows:
            cat = _categorize_window(title)
            if prev_ts is not None and prev_cat is not None:
                duration = ts - prev_ts
                if duration > 0 and duration < 3600:  # cap at 1 hour
                    category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration
            prev_ts = ts
            prev_cat = cat

        # Add the time spent in the current window since the last switch so
        # total_active_seconds reflects the present instead of stopping at
        # the most recent window event.
        if prev_ts is not None and prev_cat is not None:
            end_boundary = min(end_ts, time.time())
            if end_boundary > prev_ts:
                duration = end_boundary - prev_ts
                if duration > 0 and duration < 3600:
                    category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration

        # Build sorted category list
        window_categories = [
            {"category": cat, "seconds": round(secs, 1)}
            for cat, secs in sorted(category_seconds.items(), key=lambda x: -x[1])
        ]

        features["active_window_categories"] = window_categories
        features["total_window_events"] = total_window_events

        # ---- Total active seconds ----
        total_active_seconds = sum(c["seconds"] for c in window_categories)
        features["total_active_seconds"] = round(total_active_seconds, 1)

    finally:
        conn.close()

    return features


# ------------------------------------------------------------------
# Convenience: get all dates with events
# ------------------------------------------------------------------
def get_available_dates() -> List[str]:
    """Return list of ISO date strings that have events in the store."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT timestamp FROM (
                SELECT timestamp FROM keystroke_events
                UNION ALL
                SELECT timestamp FROM mouse_events
                UNION ALL
                SELECT timestamp FROM window_events
            )
            """
        ).fetchall()
        # Convert epoch timestamps to local-timezone dates (matching how
        # events are captured and how _get_day_range filters them).
        dates = {datetime.fromtimestamp(r[0]).date().isoformat() for r in rows}
        return sorted(dates, reverse=True)
    finally:
        conn.close()
