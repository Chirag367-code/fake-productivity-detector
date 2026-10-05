"""
Feature extraction module.

Converts a day's buffered raw events (from the local SQLite store) into
aggregate statistical features used by the authenticity scorer.
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
    lower = title.lower()
    for category, keywords in WINDOW_CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return category
    return DEFAULT_CATEGORY

def _get_day_range(target_date: date) -> Tuple[float, float]:
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    return start_dt.timestamp(), end_dt.timestamp()

def extract_features(target_date: Optional[date] = None) -> Dict[str, Any]:
    if target_date is None:
        target_date = date.today()

    start_ts, end_ts = _get_day_range(target_date)
    conn = _get_connection()
    features: Dict[str, Any] = {}

    try:
        # ---- Keystroke features ----
        rows = conn.execute(
            """
            SELECT inter_key_ms, 
                   IFNULL(is_modifier, 0) as is_mod,
                   IFNULL(dwell_ms, 0) as dwell,
                   IFNULL(flight_ms, 0) as flight,
                   IFNULL(is_injected, 0) as injected
            FROM keystroke_events 
            WHERE timestamp >= ? AND timestamp <= ?
            """,
            (start_ts, end_ts),
        ).fetchall()

        total_keystrokes = len(rows)
        
        # Calculate OS-level injected ratio across ALL keystrokes
        injected_count = sum(1 for r in rows if r[4] == 1)
        injected_ratio = injected_count / total_keystrokes if total_keystrokes > 0 else 0.0
        
        features["total_keystrokes"] = total_keystrokes
        features["injected_ratio"] = round(injected_ratio, 4)

        # Filter out modifiers and injected keys for organic typing WPM statistics
        typing_events = [r for r in rows if r[1] == 0 and r[4] == 0]
        intervals = [r[0] for r in typing_events]
        
        # Active typing intervals cap at 2000ms (2s)
        typing_intervals = [x for x in intervals if 0 < x <= 2000]
        # Pauses are gaps > 2s
        num_pauses = sum(1 for x in intervals if x > 2000)
        pause_ratio = num_pauses / len(intervals) if intervals else 0.0
        features["pause_ratio"] = round(pause_ratio, 4)
        
        # Guard: Minimum 50 organic typing events for reliable statistical distributions
        if len(typing_intervals) >= 50:
            # Basic Speed & Rhythm
            avg_typing_speed = sum(typing_intervals) / len(typing_intervals)
            variance = sum((x - avg_typing_speed) ** 2 for x in typing_intervals) / len(typing_intervals)
            typing_rhythm_variance = math.sqrt(variance)
            
            # Secondary robotic interval heuristic (sub-5ms) 
            robotic_count = sum(1 for x in typing_intervals if x < 5)
            robotic_interval_ratio = robotic_count / len(typing_intervals)
            
            # Flight Coefficient of Variation (exclude long pauses)
            flights = [r[3] for r in typing_events if 0 < r[3] <= 2000]
            if len(flights) > 1:
                mean_flight = sum(flights) / len(flights)
                flight_cv = math.sqrt(sum((x - mean_flight)**2 for x in flights) / len(flights)) / mean_flight if mean_flight > 0 else 0.0
            else:
                flight_cv = 0.0
                
            # Dwell Coefficient of Variation
            dwells = [r[2] for r in typing_events if 0 < r[2] <= 500] # Ignore >500ms dwells as held keys
            if len(dwells) > 1:
                mean_dwell = sum(dwells) / len(dwells)
                dwell_cv = math.sqrt(sum((x - mean_dwell)**2 for x in dwells) / len(dwells)) / mean_dwell if mean_dwell > 0 else 0.0
            else:
                dwell_cv = 0.0
                
            features["avg_typing_speed"] = round(avg_typing_speed, 2)
            features["typing_rhythm_variance"] = round(typing_rhythm_variance, 2)
            features["robotic_interval_ratio"] = round(robotic_interval_ratio, 4)
            features["flight_cv"] = round(flight_cv, 4)
            features["dwell_cv"] = round(dwell_cv, 4)
        else:
            # Insufficient data
            features["avg_typing_speed"] = None
            features["typing_rhythm_variance"] = None
            features["robotic_interval_ratio"] = None
            features["flight_cv"] = None
            features["dwell_cv"] = None

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
                continue
            vel = min(dist / dt, 3000.0)
            velocities.append(vel)

            angle = math.atan2(dy, dx)
            if prev_angle is not None:
                if abs(angle - prev_angle) > math.radians(45):
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
                if 0 < duration < 3600:
                    category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration
            prev_ts = ts
            prev_cat = cat

        if prev_ts is not None and prev_cat is not None:
            end_boundary = min(end_ts, time.time())
            if end_boundary > prev_ts:
                duration = end_boundary - prev_ts
                if 0 < duration < 3600:
                    category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration

        window_categories = [
            {"category": cat, "seconds": round(secs, 1)}
            for cat, secs in sorted(category_seconds.items(), key=lambda x: -x[1])
        ]

        features["active_window_categories"] = window_categories
        features["total_window_events"] = total_window_events
        features["total_active_seconds"] = round(sum(c["seconds"] for c in window_categories), 1)

    finally:
        conn.close()

    return features

def get_available_dates() -> List[str]:
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
        dates = {datetime.fromtimestamp(r[0]).date().isoformat() for r in rows}
        return sorted(dates, reverse=True)
    finally:
        conn.close()
