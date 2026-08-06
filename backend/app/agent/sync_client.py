"""
Sync client for the local behavioral agent.

Once per day (or on a configurable interval), POSTs ONLY the aggregated
authenticity_score + summary stats (not raw events) to the backend
/agent/sync endpoint, using the existing Supabase-authenticated API pattern.
"""

import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from .feature_extraction import extract_features
from .authenticity_scorer import get_authenticity_scorer

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Local config
# ------------------------------------------------------------------
CONFIG_DIR = Path.home() / ".fpd-agent"
CONFIG_PATH: Path = CONFIG_DIR / "config.json"  # exported for run_agent.py

DEFAULT_CONFIG: Dict[str, Any] = {
    "sync_interval_hours": 24,
    "backend_url": "http://localhost:8000",
    "api_key": "",  # Supabase anon key or service role key
    "user_id": "",
    "opt_out": False,
    "last_sync_date": None,  # ISO date string
}


def _load_config() -> Dict[str, Any]:
    """Load local agent config, creating defaults if missing."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg: Dict[str, Any] = json.load(f)
                # Merge with defaults for any missing keys
                for k, v in DEFAULT_CONFIG.items():
                    cfg.setdefault(k, v)
                return cfg
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read config: {e}")
    return dict(DEFAULT_CONFIG)


def _save_config(cfg: Dict[str, Any]) -> None:
    """Save local agent config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to save config: {e}")


# ------------------------------------------------------------------
# Sync logic
# ------------------------------------------------------------------
def should_sync(cfg: Dict[str, Any]) -> bool:
    """
    Check if it's time to sync based on last sync date and interval.

    Returns True if no sync has been done today.
    """
    if cfg.get("opt_out", False):
        return False
    last_sync = cfg.get("last_sync_date")
    today = date.today().isoformat()
    return last_sync != today


def build_sync_payload(user_id: str, target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """
    Build the sync payload from today's extracted features.

    Args:
        user_id: The user ID to associate with the sync
        target_date: Date to sync (defaults to today)

    Returns:
        Dict with user_id, date, authenticity_score, summary_stats
        or None if no data available.
    """
    if target_date is None:
        target_date = date.today()

    # Extract features from local SQLite
    features = extract_features(target_date)

    # Check if there's any data
    if features.get("total_keystrokes", 0) == 0 and features.get("total_mouse_events", 0) == 0:
        logger.info(f"No events found for {target_date.isoformat()} — skipping sync")
        return None

    # Score the features
    scorer = get_authenticity_scorer()
    result = scorer.score(features)

    # Build summary stats (never raw events)
    summary_stats = {
        "avg_typing_speed": features.get("avg_typing_speed", 0),
        "typing_rhythm_variance": features.get("typing_rhythm_variance", 0),
        "pause_ratio": features.get("pause_ratio", 0),
        "mouse_velocity_mean": features.get("mouse_velocity_mean", 0),
        "mouse_velocity_std": features.get("mouse_velocity_std", 0),
        "mouse_direction_change_freq": features.get("mouse_direction_change_freq", 0),
        "total_keystrokes": features.get("total_keystrokes", 0),
        "total_mouse_events": features.get("total_mouse_events", 0),
        "total_active_seconds": features.get("total_active_seconds", 0),
        "top_window_categories": features.get("active_window_categories", [])[:5],
        "breakdown": result.breakdown,
    }

    payload = {
        "user_id": user_id,
        "event_date": target_date.isoformat(),
        "authenticity_score": result.authenticity_score,
        "category": result.category,
        "summary_stats": summary_stats,
    }

    return payload


async def sync_to_backend(payload: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    """
    POST the aggregated payload to the backend /agent/sync endpoint.

    Uses the Supabase anon key as a Bearer token (matching the existing
    authFetch pattern used by the frontend).

    Args:
        payload: The sync payload (aggregated stats only)
        cfg: Local agent config

    Returns:
        True if sync succeeded, False otherwise.
    """
    backend_url = cfg.get("backend_url", "http://localhost:8000").rstrip("/")
    api_key = cfg.get("api_key", "")
    endpoint = f"{backend_url}/api/v1/agent/sync"

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload, headers=headers)

        if response.status_code in (200, 201):
            logger.info(f"Sync successful for {payload.get('date')}: {response.json()}")
            return True
        else:
            logger.error(
                f"Sync failed (HTTP {response.status_code}): {response.text[:500]}"
            )
            return False
    except httpx.RequestError as e:
        logger.error(f"Sync network error: {e}")
        return False


def run_sync(user_id: Optional[str] = None) -> bool:
    """
    Convenience synchronous wrapper for sync_to_backend.

    Can be called from run_agent.py or a cron job.

    Args:
        user_id: Override user ID. If None, uses config value.

    Returns:
        True if sync succeeded.
    """
    cfg = _load_config()
    uid = user_id or cfg.get("user_id", "")
    if not uid:
        logger.error("No user_id configured — set user_id in ~/.fpd-agent/config.json")
        return False

    # Skip should_sync check when running manually so we can test repeatedly
    payload = build_sync_payload(uid)
    if payload is None:
        return False

    import asyncio

    success = asyncio.run(sync_to_backend(payload, cfg))

    if success:
        cfg["last_sync_date"] = date.today().isoformat()
        _save_config(cfg)

    return success