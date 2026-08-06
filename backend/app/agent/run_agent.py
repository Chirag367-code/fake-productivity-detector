"""
Entry point for the local behavioral agent.

Starts the capture listeners (keystroke timing, mouse movement, window title)
as daemon threads, then runs a main loop that:
  1. Periodically purges old raw events
  2. Checks if it's time to sync aggregated data to the backend
  3. Runs the sync if conditions are met

Usage:
    python -m app.agent.run_agent [--config PATH] [--user-id UUID] [--backend-url URL] [--api-key KEY]

Options:
    --config PATH      Path to custom config file (default: ~/.fpd-agent/config.json)
    --user-id UUID     Override user ID from config
    --backend-url URL  Override backend URL from config
    --api-key KEY      Override API key from config
    --sync-only        Run sync once and exit (no daemon mode)
    --status           Show current agent status and exit
    --opt-out          Disable telemetry capture (stops if running)
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure we can import from the backend package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.agent.capture import (
    KeystrokeCapture,
    MouseCapture,
    WindowCapture,
    purge_old_events,
)
from app.agent.sync_client import (
    _load_config,
    _save_config,
    CONFIG_PATH,
    build_sync_payload,
    sync_to_backend,
    should_sync,
)

logger = logging.getLogger("fpd-agent")


# ------------------------------------------------------------------
# Agent orchestrator
# ------------------------------------------------------------------
class BehavioralAgent:
    """
    Orchestrates capture, feature extraction, and sync.

    Runs as a daemon that:
      - Listens for keystroke timing (not content)
      - Listens for mouse movement vectors
      - Polls active window title
      - Synces aggregated data daily to backend
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Capture modules
        self.key_capture = KeystrokeCapture()
        self.mouse_capture = MouseCapture()
        self.window_capture = WindowCapture(poll_interval=5.0)

    def start(self) -> None:
        """Start all capture listeners and the main loop."""
        if self._running:
            logger.warning("Agent is already running")
            return

        self._running = True
        logger.info("=" * 50)
        logger.info("FPD Behavioral Agent Starting")
        logger.info("=" * 50)
        logger.info(f"Backend URL: {self.config.get('backend_url', 'http://localhost:8000')}")
        logger.info(f"User ID: {self.config.get('user_id', 'NOT SET')}")
        logger.info(f"Sync interval: {self.config.get('sync_interval_hours', 24)}h")
        logger.info("")
        logger.info("Privacy notice:")
        logger.info("  - Captures ONLY keystroke TIMING (never content)")
        logger.info("  - Captures ONLY mouse movement VECTORS (never click targets)")
        logger.info("  - Captures ONLY window TITLES (never window content)")
        logger.info("  - Raw events NEVER leave this machine")
        logger.info("=" * 50)

        # Start capture listeners
        self.key_capture.start()
        self.mouse_capture.start()
        self.window_capture.start()

        # Start main loop in a background thread
        self._thread = threading.Thread(target=self._main_loop, daemon=True)
        self._thread.start()

        logger.info("Agent is running in background. Press Ctrl+C to stop.")

    def stop(self) -> None:
        """Stop all capture listeners."""
        logger.info("Stopping agent...")
        self._running = False
        self.key_capture.stop()
        self.mouse_capture.stop()
        self.window_capture.stop()
        logger.info("Agent stopped.")

    def _main_loop(self) -> None:
        """Main loop: periodic purge + sync check."""
        purge_interval = 3600  # every hour
        sync_check_interval = 300  # every 5 minutes
        last_purge = 0
        last_sync_check = 0

        while self._running:
            now = time.time()

            # Purge old events hourly
            if now - last_purge >= purge_interval:
                try:
                    purge_old_events(days=14)
                except Exception as e:
                    logger.warning(f"Purge error: {e}")
                last_purge = now

            # Check sync every 5 minutes
            if now - last_sync_check >= sync_check_interval:
                try:
                    self._check_sync()
                except Exception as e:
                    logger.warning(f"Sync check error: {e}")
                last_sync_check = now

            time.sleep(10)

    def _check_sync(self) -> None:
        """Check if sync is needed and perform it."""
        if should_sync(self.config):
            logger.info("Sync condition met — starting sync...")
            uid = self.config.get("user_id", "")
            if not uid:
                logger.warning("No user_id configured — skipping sync")
                return

            payload = build_sync_payload(uid)
            if payload is None:
                logger.info("No data to sync yet")
                return

            import asyncio

            success = asyncio.run(sync_to_backend(payload, self.config))

            if success:
                self.config["last_sync_date"] = date.today().isoformat()
                _save_config(self.config)
                logger.info("Daily sync completed successfully")
            else:
                logger.warning("Sync failed — will retry")
        else:
            logger.debug("No sync needed at this time")


# ------------------------------------------------------------------
# Signal handling
# ------------------------------------------------------------------
_agent_instance: Optional[BehavioralAgent] = None


def _signal_handler(signum, frame) -> None:
    """Handle Ctrl+C / SIGTERM gracefully."""
    logger.info(f"Received signal {signum}")
    if _agent_instance:
        _agent_instance.stop()
    sys.exit(0)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fake Productivity Detector — Local Behavioral Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.agent.run_agent
  python -m app.agent.run_agent --user-id abc-123 --backend-url http://localhost:8000
  python -m app.agent.run_agent --sync-only
  python -m app.agent.run_agent --status
  python -m app.agent.run_agent --opt-out
        """,
    )
    parser.add_argument("--config", type=str, help="Path to custom config file")
    parser.add_argument("--user-id", type=str, help="Override user ID")
    parser.add_argument("--backend-url", type=str, help="Override backend URL")
    parser.add_argument("--api-key", type=str, help="Override API key (Supabase anon key)")
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Run sync once and exit (no daemon mode)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current agent status and exit",
    )
    parser.add_argument(
        "--opt-out",
        action="store_true",
        help="Disable telemetry capture",
    )
    return parser.parse_args(argv)


def show_status(config: Dict[str, Any]) -> None:
    """Display current agent status."""
    print("=" * 50)
    print("FPD Agent Status")
    print("=" * 50)
    print(f"  User ID:           {config.get('user_id', 'NOT SET')}")
    print(f"  Backend URL:       {config.get('backend_url', 'http://localhost:8000')}")
    print(f"  Sync interval:     {config.get('sync_interval_hours', 24)}h")
    print(f"  Last sync date:    {config.get('last_sync_date', 'Never')}")
    print(f"  Opt-out:           {config.get('opt_out', False)}")
    print(f"  Config file:       {CONFIG_PATH}")
    print(f"  DB file:           ~/.fpd-agent/agent_events.db")
    print()
    print("  Privacy boundaries:")
    print("    ✓ Keystroke timing only (never content)")
    print("    ✓ Mouse movement vectors only (never click targets)")
    print("    ✓ Active window titles only (never content)")
    print("    ✓ Raw events stored locally only")
    print()

    # Show today's data summary if available
    from .feature_extraction import extract_features

    try:
        features = extract_features()
        total_events = (
            features.get("total_keystrokes", 0)
            + features.get("total_mouse_events", 0)
            + features.get("total_window_events", 0)
        )
        print(f"  Today's captured events: {total_events}")
        if total_events > 0:
            print(f"    Keystrokes:  {features.get('total_keystrokes', 0)}")
            print(f"    Mouse moves: {features.get('total_mouse_events', 0)}")
            print(f"    Window switches: {features.get('total_window_events', 0)}")
    except Exception as e:
        print(f"  Data read error: {e}")

    print("=" * 50)


def main(argv: Optional[list] = None) -> int:
    """
    Main entry point.

    Returns exit code (0 = success).
    """
    args = parse_args(argv)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load config
    if args.config:
        CONFIG_PATH = Path(args.config)
    config = _load_config()

    # Apply CLI overrides
    if args.user_id:
        config["user_id"] = args.user_id
    if args.backend_url:
        config["backend_url"] = args.backend_url
    if args.api_key:
        config["api_key"] = args.api_key
    if args.opt_out:
        config["opt_out"] = True
        _save_config(config)
        print("Agent has been opted out. Run with --opt-out=false to re-enable.")
        return 0

    # Status mode
    if args.status:
        show_status(config)
        return 0

    # Sync-only mode
    if args.sync_only:
        from .sync_client import run_sync

        print("Running one-time sync...")
        success = run_sync(user_id=config.get("user_id"))
        print(f"Sync {'succeeded' if success else 'failed'}")
        return 0 if success else 1

    # Daemon mode
    global _agent_instance
    _agent_instance = BehavioralAgent(config)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    _agent_instance.start()

    # Keep main thread alive
    try:
        while _agent_instance._running:
            time.sleep(1)
    except KeyboardInterrupt:
        _agent_instance.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())