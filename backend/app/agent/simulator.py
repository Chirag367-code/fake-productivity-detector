"""
Realistic agent behavior simulator — professionally calibrated.

Simulates a local behavioral agent that is actively capturing events on the
user's machine. Generates realistic keystroke timing, mouse movement, and
window-switch events that accumulate over time — mimicking what a real
agent would capture.

Key realism improvements over naive simulation:
  - Keystroke timing uses burst/pause patterns (5-20 rapid keys → think pause)
  - Mouse movement has acceleration/deceleration phases with micro-corrections
  - Window dwell times are category-dependent (productive: 5-25 min)
  - Natural idle gaps every 30-90 minutes simulate breaks
  - Daily personality profiles create realistic day-to-day variation

Privacy: The simulator generates ONLY synthetic metadata (timing intervals,
movement vectors, window titles) — never real user content.
"""

import logging
import math
import random
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Realistic window titles (synthetic — never real user content)
# ------------------------------------------------------------------
WINDOW_TITLES: Dict[str, List[str]] = {
    "Code/IDE": [
        "Visual Studio Code - main.py",
        "Visual Studio Code - App.tsx",
        "PyCharm - backend/app/main.py",
        "Visual Studio Code - index.html",
        "IntelliJ IDEA - Server.java",
        "Visual Studio Code - README.md",
        "PyCharm - models/database.py",
        "Visual Studio Code - package.json",
    ],
    "Word/Office": [
        "Microsoft Word - Project Report.docx",
        "Microsoft Excel - data_analysis.xlsx",
        "Google Docs - Meeting Notes",
        "Microsoft PowerPoint - Presentation.pptx",
        "Notion - Project Planning",
        "Google Sheets - Budget 2026",
    ],
    "Browser": [
        "Google Chrome - Stack Overflow",
        "Google Chrome - GitHub",
        "Google Chrome - MDN Web Docs",
        "Google Chrome - Gmail",
        "Google Chrome - LinkedIn",
        "Google Chrome - Medium - Programming",
        "Google Chrome - Dev.to",
        "Google Chrome - Reddit - programming",
    ],
    "Communication": [
        "Slack - team-project",
        "Discord - Dev Server",
        "Microsoft Teams - Standup Meeting",
        "Zoom - Client Call",
        "Telegram - Work Group",
        "Slack - general",
    ],
    "Entertainment": [
        "YouTube - Music",
        "YouTube - Tutorial",
        "Netflix - Browser",
        "Spotify - Premium",
        "Twitch - Programming",
        "YouTube - Podcast",
    ],
    "Terminal/CLI": [
        "Windows Terminal - PowerShell",
        "Windows Terminal - cmd",
        "Terminal - bash",
        "Windows Terminal - WSL: Ubuntu",
        "Command Prompt - npm run dev",
        "Windows Terminal - git",
    ],
    "Email": [
        "Gmail - Inbox",
        "Outlook - Inbox",
        "Thunderbird - Inbox",
        "Gmail - Sent",
    ],
    "Design": [
        "Figma - UI Design",
        "Adobe Photoshop - banner.png",
        "Canva - Presentation",
        "Figma - Prototype",
    ],
    "Other": [
        "File Explorer",
        "Settings",
        "Task Manager",
        "Calculator",
        "System Tray",
    ],
}

# ------------------------------------------------------------------
# Daily personality profiles — create natural day-to-day variation
# ------------------------------------------------------------------
# Each profile defines how the simulated user behaves that day.
# The active profile is chosen randomly per session to ensure
# the trend chart shows realistic score variation.
DAILY_PROFILES = {
    "focused_developer": {
        "description": "Deep focus coding day",
        "category_weights": [
            ("Code/IDE", 0.45), ("Terminal/CLI", 0.20), ("Browser", 0.15),
            ("Communication", 0.08), ("Word/Office", 0.05), ("Email", 0.04),
            ("Entertainment", 0.02), ("Design", 0.01),
        ],
        "typing_speed_range": (80, 220),      # Fast, consistent typist
        "typing_variance_range": (35, 80),     # Low variance — focused
        "pause_probability": 0.10,             # Few pauses — in the zone
        "idle_gap_probability": 0.03,          # Rarely idle
        "window_dwell_range": (10, 45),        # Demo: Fast switching (10-45s)
    },
    "balanced_worker": {
        "description": "Normal productive day with some breaks",
        "category_weights": [
            ("Code/IDE", 0.30), ("Browser", 0.22), ("Communication", 0.15),
            ("Terminal/CLI", 0.10), ("Word/Office", 0.10), ("Email", 0.06),
            ("Entertainment", 0.05), ("Design", 0.02),
        ],
        "typing_speed_range": (120, 300),      # Average speed
        "typing_variance_range": (50, 120),    # Moderate variance
        "pause_probability": 0.14,             # Natural pauses
        "idle_gap_probability": 0.06,          # Occasional breaks
        "window_dwell_range": (5, 30),         # Demo: Fast switching (5-30s)
    },
    "meeting_heavy": {
        "description": "Lots of meetings and communication",
        "category_weights": [
            ("Communication", 0.35), ("Browser", 0.20), ("Code/IDE", 0.18),
            ("Email", 0.10), ("Word/Office", 0.08), ("Terminal/CLI", 0.05),
            ("Entertainment", 0.03), ("Design", 0.01),
        ],
        "typing_speed_range": (150, 350),      # Slower — typing messages
        "typing_variance_range": (60, 140),    # Higher variance
        "pause_probability": 0.18,             # More pauses (listening)
        "idle_gap_probability": 0.08,          # More idle (in meetings)
        "window_dwell_range": (5, 20),         # Demo: Fast switching (5-20s)
    },
    "distracted_day": {
        "description": "Low productivity, lots of entertainment",
        "category_weights": [
            ("Entertainment", 0.30), ("Browser", 0.25), ("Communication", 0.20),
            ("Code/IDE", 0.10), ("Email", 0.05), ("Word/Office", 0.05),
            ("Terminal/CLI", 0.03), ("Design", 0.02),
        ],
        "typing_speed_range": (200, 500),      # Slow, inconsistent
        "typing_variance_range": (80, 200),    # High variance
        "pause_probability": 0.25,             # Lots of pauses
        "idle_gap_probability": 0.12,          # Frequently idle
        "window_dwell_range": (2, 15),         # Demo: Fast switching (2-15s)
    },
    "research_day": {
        "description": "Lots of reading and research",
        "category_weights": [
            ("Browser", 0.40), ("Code/IDE", 0.20), ("Word/Office", 0.15),
            ("Communication", 0.10), ("Terminal/CLI", 0.05), ("Email", 0.05),
            ("Entertainment", 0.03), ("Design", 0.02),
        ],
        "typing_speed_range": (130, 280),
        "typing_variance_range": (55, 110),
        "pause_probability": 0.16,
        "idle_gap_probability": 0.05,
        "window_dwell_range": (15, 60),        # Demo: Fast switching (15-60s)
    },
}

PROFILE_WEIGHTS = {
    "focused_developer": 0.30,
    "balanced_worker": 0.30,
    "meeting_heavy": 0.15,
    "distracted_day": 0.10,
    "research_day": 0.15,
}


def _pick_daily_profile() -> Dict[str, Any]:
    """Pick a daily personality profile (weighted random)."""
    names = list(PROFILE_WEIGHTS.keys())
    weights = [PROFILE_WEIGHTS[n] for n in names]
    chosen = random.choices(names, weights=weights, k=1)[0]
    return DAILY_PROFILES[chosen]


# ------------------------------------------------------------------
# Session state — persists across requests so events accumulate
# ------------------------------------------------------------------
class _SessionState:
    """Tracks simulated agent state so events accumulate over time."""

    def __init__(self) -> None:
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._last_scan: Dict[str, float] = {}
        self._session_start: Dict[str, float] = {}
        self._last_window: Dict[str, str] = {}
        self._last_window_time: Dict[str, float] = {}
        self._last_key_time: Dict[str, float] = {}
        self._last_mouse_pos: Dict[str, Tuple[float, float]] = {}
        self._last_mouse_time: Dict[str, float] = {}
        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_or_init(self, user_id: str) -> None:
        """Initialize session state for a user if not present."""
        with self._lock:
            if user_id not in self._events:
                now = time.time()
                # Start the session 5 minutes in the past so the first scan
                # generates a realistic burst of events (like a real agent
                # that's been running for a while).
                session_start = now - 300.0
                self._events[user_id] = []
                self._last_scan[user_id] = session_start
                self._session_start[user_id] = session_start
                self._last_window[user_id] = "Visual Studio Code - main.py"
                self._last_window_time[user_id] = session_start
                self._last_key_time[user_id] = session_start
                self._last_mouse_pos[user_id] = (960.0, 540.0)
                self._last_mouse_time[user_id] = session_start
                self._profiles[user_id] = _pick_daily_profile()

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get the daily profile for a user."""
        with self._lock:
            return self._profiles.get(user_id, DAILY_PROFILES["balanced_worker"])

    def get_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all events for a user."""
        with self._lock:
            return list(self._events.get(user_id, []))

    def get_last_scan(self, user_id: str) -> float:
        """Get timestamp of last scan for a user."""
        with self._lock:
            return self._last_scan.get(user_id, time.time())

    def get_session_start(self, user_id: str) -> float:
        """Get session start timestamp for a user."""
        with self._lock:
            return self._session_start.get(user_id, time.time())

    def set_last_scan(self, user_id: str, ts: float) -> None:
        """Update last scan timestamp."""
        with self._lock:
            self._last_scan[user_id] = ts

    def append_events(self, user_id: str, events: List[Dict[str, Any]]) -> None:
        """Append new events for a user."""
        with self._lock:
            self._events.setdefault(user_id, []).extend(events)
            # Cap at ~50k events per user to prevent unbounded growth
            if len(self._events[user_id]) > 50_000:
                self._events[user_id] = self._events[user_id][-50_000:]

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Get current state for a user (for telemetry)."""
        with self._lock:
            return {
                "last_window": self._last_window.get(user_id, ""),
                "last_window_time": self._last_window_time.get(user_id, 0),
                "last_key_time": self._last_key_time.get(user_id, 0),
                "last_mouse_pos": self._last_mouse_pos.get(user_id, (0, 0)),
                "last_mouse_time": self._last_mouse_time.get(user_id, 0),
            }

    def update_state(self, user_id: str, **kwargs: Any) -> None:
        """Update state fields for a user."""
        with self._lock:
            for k, v in kwargs.items():
                if k == "last_window":
                    self._last_window[user_id] = v
                elif k == "last_window_time":
                    self._last_window_time[user_id] = v
                elif k == "last_key_time":
                    self._last_key_time[user_id] = v
                elif k == "last_mouse_pos":
                    self._last_mouse_pos[user_id] = v
                elif k == "last_mouse_time":
                    self._last_mouse_time[user_id] = v


# Singleton session state
_session = _SessionState()


def has_active_session(user_id: str) -> bool:
    """
    Check whether the simulator has an active session for a user.

    Used by the /agent/scan route to distinguish "falling back to simulator
    for the first time" (where a genuine real record must be preserved)
    from "simulator already running" (where new simulated events must
    keep accumulating on every scan).
    """
    with _session._lock:
        return user_id in _session._events


# ------------------------------------------------------------------
# Event generation — professionally calibrated
# ------------------------------------------------------------------
def _generate_keystrokes(
    user_id: str,
    count: int,
    start_ts: float,
    end_ts: float,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate realistic keystroke timing events with burst/pause patterns.

    Human typing has:
      - Typing bursts: 5-20 rapid keys at consistent speed
      - Think pauses between bursts: 1-8 seconds (reading, thinking)
      - Speed variation within bursts: ±20% of base speed
      - Occasional typos/corrections: brief speed spike
      - Overall speed varies by person and task
    """
    events: List[Dict[str, Any]] = []
    state = _session.get_state(user_id)
    last_key_time = state["last_key_time"] or start_ts

    speed_lo, speed_hi = profile.get("typing_speed_range", (100, 280))
    pause_prob = profile.get("pause_probability", 0.12)

    ts = max(last_key_time, start_ts)

    # Burst state: track how many keys are in the current burst
    burst_remaining = 0
    burst_speed = random.uniform(speed_lo, speed_hi)

    for _ in range(count):
        if burst_remaining <= 0:
            # Start a new typing burst
            burst_remaining = random.randint(5, 25)
            # Each burst has a slightly different base speed (task switching,
            # different types of content)
            burst_speed = random.uniform(speed_lo, speed_hi)

            # Think pause before the new burst (reading/thinking)
            if events:  # Don't pause before the very first keystroke
                if random.random() < pause_prob:
                    # Long think pause: 2-8 seconds
                    pause = random.uniform(2.0, 8.0)
                    ts += pause
                elif random.random() < 0.15:
                    # Short micro-pause: 0.5-2 seconds (re-reading, cursor position)
                    ts += random.uniform(0.5, 2.0)

        burst_remaining -= 1

        # Inter-key interval within burst: base speed ± natural variation
        # Human typing has ~15-25% coefficient of variation within a burst
        cv = random.uniform(0.12, 0.28)
        interval = burst_speed * (1.0 + random.gauss(0, cv))
        interval = max(30.0, interval)  # Physical minimum

        # Occasional fast double-tap (common keys like 'e', 't', space)
        if random.random() < 0.05:
            interval = random.uniform(30.0, 60.0)

        # Occasional slow key (reaching for uncommon key, shift combos)
        if random.random() < 0.08:
            interval = random.uniform(250.0, 450.0)

        ts += interval / 1000.0  # Convert ms to seconds

        if ts > end_ts:
            break

        # For the first event, calculate the true gap from the last scan
        if not events:
            true_gap_ms = (ts - last_key_time) * 1000.0
            if true_gap_ms < 300_000:  # same 5-min cap as capture.py
                interval = true_gap_ms

        events.append({
            "type": "keystroke",
            "timestamp": ts,
            "inter_key_ms": round(interval, 1),
        })

    if events:
        _session.update_state(user_id, last_key_time=events[-1]["timestamp"])

    return events


def _generate_mouse_moves(
    user_id: str,
    count: int,
    start_ts: float,
    end_ts: float,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate realistic mouse movement events with acceleration model.

    Human mouse movement:
      - Moves in smooth arcs with acceleration and deceleration
      - Has natural overshoot and micro-corrections near targets
      - Velocity follows log-normal distribution (mostly moderate, occasional fast)
      - Pauses at click targets (reading, deciding)
      - Occasional large jumps (switching UI areas)
    """
    events: List[Dict[str, Any]] = []
    state = _session.get_state(user_id)
    last_pos = state["last_mouse_pos"] or (960.0, 540.0)
    last_mouse_time = state["last_mouse_time"] or start_ts

    ts = max(last_mouse_time, start_ts)
    x, y = last_pos

    # Movement state machine
    move_remaining = 0
    target_x, target_y = x, y
    current_speed = 0.0
    max_speed = 0.0

    for _ in range(count):
        if move_remaining <= 0:
            # Start a new movement sequence toward a target

            # Occasionally pause (mouse resting — reading, thinking)
            if events and random.random() < 0.08:
                ts += random.uniform(0.3, 2.0)

            # Pick target: mostly small movements, occasionally large
            if random.random() < 0.06:
                # Large jump to new UI area
                target_x = random.uniform(100, 1820)
                target_y = random.uniform(100, 980)
                move_remaining = random.randint(8, 20)
            elif random.random() < 0.15:
                # Medium movement (switching between panels)
                target_x = x + random.uniform(-300, 300)
                target_y = y + random.uniform(-200, 200)
                move_remaining = random.randint(5, 12)
            else:
                # Small precise movement (within a UI element)
                target_x = x + random.uniform(-40, 40)
                target_y = y + random.uniform(-25, 25)
                move_remaining = random.randint(2, 6)

            target_x = max(0, min(1920, target_x))
            target_y = max(0, min(1080, target_y))

            # Calculate max speed for this movement (log-normal distribution)
            distance = math.sqrt((target_x - x) ** 2 + (target_y - y) ** 2)
            max_speed = max(50.0, distance * random.uniform(3.0, 8.0))
            current_speed = 0.0

        move_remaining -= 1

        # Time between samples (realistic polling: 8-60ms)
        dt = random.uniform(0.008, 0.060)
        ts += dt

        if ts > end_ts:
            break

        # Acceleration/deceleration model:
        # Speed ramps up at start, sustains in middle, decelerates at end
        total_dist = math.sqrt((target_x - x) ** 2 + (target_y - y) ** 2)
        if total_dist < 1.0:
            move_remaining = 0
            continue

        # Smooth speed profile
        if move_remaining > 3:
            # Accelerating
            current_speed = min(current_speed + max_speed * 0.3, max_speed)
        elif move_remaining > 1:
            # Sustained
            current_speed = max_speed * random.uniform(0.7, 1.0)
        else:
            # Decelerating (approaching target)
            current_speed = max_speed * random.uniform(0.2, 0.5)

        # Move toward target with natural imprecision
        step_size = current_speed * dt
        if step_size > total_dist:
            step_size = total_dist

        angle = math.atan2(target_y - y, target_x - x)
        # Add micro-correction noise (human hands aren't perfectly steady)
        angle += random.gauss(0, 0.08)

        dx = step_size * math.cos(angle)
        dy = step_size * math.sin(angle)

        x = max(0, min(1920, x + dx))
        y = max(0, min(1080, y + dy))

        events.append({
            "type": "mouse",
            "timestamp": ts,
            "x": round(x, 1),
            "y": round(y, 1),
        })

    if events:
        last = events[-1]
        _session.update_state(
            user_id,
            last_mouse_pos=(last["x"], last["y"]),
            last_mouse_time=last["timestamp"],
        )

    return events


def _generate_window_switches(
    user_id: str,
    count: int,
    start_ts: float,
    end_ts: float,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate realistic window switch events with category-dependent dwell times.

    Real users spend different amounts of time in different window types:
      - Code/IDE: 5-25 minutes (deep focus sessions)
      - Communication: 1-5 minutes (quick replies)
      - Entertainment: 2-15 minutes (varies widely)
      - Browser: 2-10 minutes (research/reading)

    Also inserts natural idle gaps (breaks, bathroom, coffee).
    """
    events: List[Dict[str, Any]] = []
    state = _session.get_state(user_id)
    current_window = state["last_window"] or "Visual Studio Code - main.py"
    last_window_time = state["last_window_time"] or start_ts

    category_weights = profile.get("category_weights", [
        ("Code/IDE", 0.30), ("Browser", 0.20), ("Terminal/CLI", 0.12),
        ("Communication", 0.12), ("Word/Office", 0.10), ("Email", 0.06),
        ("Entertainment", 0.05), ("Design", 0.05),
    ])
    dwell_lo, dwell_hi = profile.get("window_dwell_range", (120, 900))
    idle_gap_prob = profile.get("idle_gap_probability", 0.05)

    # Category-specific dwell time multipliers
    dwell_multipliers = {
        "Code/IDE": 1.8,       # Long focus sessions
        "Terminal/CLI": 1.3,   # Moderate (running commands, reading output)
        "Word/Office": 1.5,    # Document work
        "Browser": 1.0,        # Default
        "Communication": 0.6,  # Quick interactions
        "Entertainment": 0.9,  # Moderate
        "Email": 0.7,          # Quick checks
        "Design": 1.4,         # Creative focus
        "Other": 0.4,          # Brief (file explorer, settings)
    }

    ts = last_window_time

    for _ in range(count):
        # Pick the next window category
        cat = random.choices(
            [c for c, _ in category_weights],
            weights=[w for _, w in category_weights],
        )[0]

        # Category-specific dwell time
        multiplier = dwell_multipliers.get(cat, 1.0)
        base_dwell = random.uniform(dwell_lo, dwell_hi)
        duration = base_dwell * multiplier

        ts += duration

        # Skip switches that already happened before this scan window
        if ts < start_ts:
            continue

        if ts > end_ts:
            break

        # Insert natural idle gap (break, bathroom, coffee)
        if random.random() < idle_gap_prob:
            idle_duration = random.uniform(120, 300)  # 2-5 minute break
            ts += idle_duration
            if ts > end_ts:
                break

        title = random.choice(WINDOW_TITLES[cat])

        # Don't record if same as current (no switch happened)
        if title != current_window:
            events.append({
                "type": "window",
                "timestamp": ts,
                "title": title,
            })
            current_window = title

    if events:
        _session.update_state(
            user_id,
            last_window=current_window,
            last_window_time=events[-1]["timestamp"],
        )

    return events


# ------------------------------------------------------------------
# Feature extraction from simulated events
# ------------------------------------------------------------------
def _categorize_window(title: str) -> str:
    """Match a window title to a category."""
    lower = title.lower()
    for cat, titles in WINDOW_TITLES.items():
        for t in titles:
            if t.lower() in lower or lower in t.lower():
                return cat
    return "Other"


def extract_features_from_events(
    events: List[Dict[str, Any]],
    target_date: date,
) -> Dict[str, Any]:
    """
    Extract aggregate features from simulated events for a given date.

    Mirrors the structure of feature_extraction.extract_features() so the
    existing AuthenticityScorer can consume it directly.
    """
    # Filter events to the target date
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

    day_events = [e for e in events if start_ts <= e["timestamp"] <= end_ts]

    # ---- Keystroke features ----
    key_intervals = [e["inter_key_ms"] for e in day_events if e["type"] == "keystroke"]
    total_keystrokes = len(key_intervals)

    if key_intervals:
        # Separate true typing intervals from pauses (> 2s) so the average
        # typing speed reflects active typing only (same logic as the real
        # feature_extraction module).
        typing_intervals = [x for x in key_intervals if x <= 2000]
        num_pauses = sum(1 for x in key_intervals if x > 2000)
        pause_ratio = num_pauses / len(key_intervals)

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

    # ---- Mouse features ----
    mouse_events = [e for e in day_events if e["type"] == "mouse"]
    total_mouse_events = len(mouse_events)
    velocities: List[float] = []
    direction_changes = 0
    prev_angle: Optional[float] = None

    for i in range(1, len(mouse_events)):
        t1 = mouse_events[i - 1]["timestamp"]
        x1 = mouse_events[i - 1]["x"]
        y1 = mouse_events[i - 1]["y"]
        t2 = mouse_events[i]["timestamp"]
        x2 = mouse_events[i]["x"]
        y2 = mouse_events[i]["y"]

        dt = t2 - t1
        if dt <= 0:
            continue
        dx = x2 - x1
        dy = y2 - y1
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            continue  # no movement — not a velocity sample
        vel = dist / dt
        # Same realistic velocity ceiling as feature_extraction so the
        # score reflects the same distribution as real captures.
        vel = min(vel, 3000.0)
        velocities.append(vel)

        angle = math.atan2(dy, dx)
        if prev_angle is not None:
            diff = abs(angle - prev_angle)
            if diff > math.radians(45):
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

    if len(mouse_events) >= 2:
        time_span_min = (mouse_events[-1]["timestamp"] - mouse_events[0]["timestamp"]) / 60.0
        dir_change_freq = direction_changes / time_span_min if time_span_min > 0 else 0.0
    else:
        dir_change_freq = 0.0

    # ---- Window category features ----
    window_events = [e for e in day_events if e["type"] == "window"]
    total_window_events = len(window_events)
    category_seconds: Dict[str, float] = {}
    prev_ts: Optional[float] = None
    prev_cat: Optional[str] = None

    for e in window_events:
        cat = _categorize_window(e["title"])
        if prev_ts is not None and prev_cat is not None:
            duration = e["timestamp"] - prev_ts
            if duration > 0 and duration < 3600:
                category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration
        prev_ts = e["timestamp"]
        prev_cat = cat

    # Add time from last window to end of day (or now)
    if prev_ts is not None and prev_cat is not None:
        end_boundary = min(end_ts, time.time())
        if end_boundary > prev_ts:
            duration = end_boundary - prev_ts
            if duration > 0 and duration < 3600:
                category_seconds[prev_cat] = category_seconds.get(prev_cat, 0) + duration

    window_categories = [
        {"category": cat, "seconds": round(secs, 1)}
        for cat, secs in sorted(category_seconds.items(), key=lambda x: -x[1])
    ]

    total_active_seconds = sum(c["seconds"] for c in window_categories)

    return {
        "avg_typing_speed": round(avg_typing_speed, 2),
        "typing_rhythm_variance": round(typing_rhythm_variance, 2),
        "pause_ratio": round(pause_ratio, 4),
        "mouse_velocity_mean": round(mouse_velocity_mean, 2),
        "mouse_velocity_std": round(mouse_velocity_std, 2),
        "mouse_direction_change_freq": round(dir_change_freq, 2),
        "active_window_categories": window_categories,
        "total_keystrokes": total_keystrokes,
        "total_mouse_events": total_mouse_events,
        "total_window_events": total_window_events,
        "total_active_seconds": round(total_active_seconds, 1),
    }


# ------------------------------------------------------------------
# Main simulation entry point
# ------------------------------------------------------------------
def simulate_agent_scan(user_id: str) -> Dict[str, Any]:
    """
    Simulate a fresh agent scan.

    Generates new events since the last scan (as if the agent has been
    capturing in the background), extracts features, and returns the
    updated state. Uses daily personality profiles for realistic variation.

    Returns:
        Dict with:
          - features: extracted features from all events
          - new_events: count of new events generated
          - total_events: total events in session
          - session_start: session start timestamp
          - last_scan: last scan timestamp
          - agent_version: simulated agent version
          - is_running: whether the agent is "running"
    """
    _session.get_or_init(user_id)

    now = time.time()
    last_scan = _session.get_last_scan(user_id)
    profile = _session.get_profile(user_id)

    # Time since last scan (cap at 5 minutes to avoid huge generation)
    elapsed = min(now - last_scan, 300.0)

    # Generate events proportional to elapsed time
    # Rates are profile-dependent but generally:
    # ~1.5-3.5 keystrokes/sec, ~3-8 mouse moves/sec
    key_count = int(elapsed * random.uniform(1.5, 3.5))
    mouse_count = int(elapsed * random.uniform(3.0, 8.0))

    # Window switches: category-dependent dwell time means we need enough
    # iterations to cover the span since the last switch
    state = _session.get_state(user_id)
    last_window_time = state.get("last_window_time") or last_scan
    window_span = max(now - last_window_time, 0)
    dwell_lo = profile.get("window_dwell_range", (120, 900))[0]
    window_count = max(1, int(window_span / max(dwell_lo, 2)) + 2)

    new_events: List[Dict[str, Any]] = []
    new_events.extend(_generate_keystrokes(user_id, key_count, last_scan, now, profile))
    new_events.extend(_generate_mouse_moves(user_id, mouse_count, last_scan, now, profile))
    new_events.extend(_generate_window_switches(user_id, window_count, last_scan, now, profile))

    # Sort by timestamp
    new_events.sort(key=lambda e: e["timestamp"])

    # Append to session
    _session.append_events(user_id, new_events)

    # Update last scan
    _session.set_last_scan(user_id, now)

    # Extract features for today
    features = extract_features_from_events(_session.get_events(user_id), date.today())

    total_events = (
        features.get("total_keystrokes", 0)
        + features.get("total_mouse_events", 0)
        + features.get("total_window_events", 0)
    )

    return {
        "features": features,
        "new_events": len(new_events),
        "total_events": total_events,
        "session_start": _session.get_session_start(user_id),
        "last_scan": now,
        "agent_version": "2.0.0",
        "is_running": True,
        "events_since_scan": len(new_events),
    }


def get_agent_status(user_id: str) -> Dict[str, Any]:
    """
    Get current agent status/telemetry for a user.

    Returns:
        Dict with agent status, event counts, session info, and health.
    """
    _session.get_or_init(user_id)

    events = _session.get_events(user_id)
    state = _session.get_state(user_id)
    session_start = _session.get_session_start(user_id)
    last_scan = _session.get_last_scan(user_id)
    now = time.time()

    # Count events by type
    keystrokes = sum(1 for e in events if e["type"] == "keystroke")
    mouse_moves = sum(1 for e in events if e["type"] == "mouse")
    window_switches = sum(1 for e in events if e["type"] == "window")

    # Session duration
    session_seconds = now - session_start
    session_minutes = int(session_seconds / 60)

    # Time since last scan
    seconds_since_scan = int(now - last_scan)

    # Activity rates — per-type so telemetry cards show accurate stats
    denom = max(session_minutes, 1)
    return {
        "is_running": True,
        "agent_version": "2.0.0",
        "session_start": session_start,
        "session_minutes": session_minutes,
        "last_scan": last_scan,
        "seconds_since_scan": seconds_since_scan,
        "total_events": len(events),
        "keystrokes": keystrokes,
        "mouse_moves": mouse_moves,
        "window_switches": window_switches,
        "current_window": state["last_window"],
        "last_activity": max(state["last_key_time"], state["last_mouse_time"]),
        "events_per_minute": round(len(events) / denom, 1),
        "keystrokes_per_minute": round(keystrokes / denom, 1),
        "mouse_moves_per_minute": round(mouse_moves / denom, 1),
    }
