"""
Agent sync API routes.

Provides the /agent/sync endpoint that the local behavioral agent POSTs
aggregated daily authenticity scores to, plus live monitoring endpoints
that simulate a running agent for realistic dashboard telemetry.
"""

import logging
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from ..models.schemas import (
    AgentSyncRequest,
    AgentSyncResponse,
    AgentHistoryResponse,
    ErrorResponse,
)
from ..models.database import AgentAuthenticityDB, get_agent_db
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


async def verify_agent_auth(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify authorization header for agent sync.

    The agent uses the Supabase anon key or a user's access token
    (matching the authFetch pattern from the frontend).

    Args:
        authorization: Bearer token from header

    Returns:
        User ID if authorization is valid, or raises HTTPException
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'Bearer <token>'",
        )

    # In production, decode the JWT to extract user_id.
    # For development, we accept the token and rely on the payload user_id.
    token = authorization[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty token",
        )

    # Development mode: allow any non-empty token.
    # The user_id in the payload will be used to store data.
    # In production, decode JWT and verify user_id matches.
    if settings.environment != "production":
        return "agent_authenticated"

    # TODO: Add JWT verification for production
    return "agent_authenticated"


@router.post(
    "/sync",
    response_model=AgentSyncResponse,
    summary="Sync agent authenticity data",
    description="Receive daily aggregated authenticity score from the local behavioral agent.",
    status_code=status.HTTP_201_CREATED,
)
async def sync_agent_data(
    request: AgentSyncRequest,
    db: AgentAuthenticityDB = Depends(get_agent_db),
    auth_user: str = Depends(verify_agent_auth),
) -> AgentSyncResponse:
    """
    Store daily authenticity score from the local behavioral agent.

    Accepts ONLY aggregated summary stats — never raw event data.
    Uses upsert logic: if a record for (user_id, date) already exists,
    it will be updated with the latest values.

    Args:
        request: Agent sync payload with authenticity score and summary stats
        db: Agent database dependency
        auth_user: Authenticated user identifier

    Returns:
        AgentSyncResponse with the stored record
    """
    try:
        record = await db.upsert_authenticity(
            user_id=request.user_id,
            event_date=request.event_date,
            authenticity_score=request.authenticity_score,
            avg_typing_speed=request.summary_stats.get("avg_typing_speed"),
            avg_mouse_velocity=request.summary_stats.get("mouse_velocity_mean"),
            top_window_categories=request.summary_stats.get("top_window_categories", []),
        )

        logger.info(
            f"Agent sync stored for user {request.user_id} "
            f"on {request.event_date}: score={request.authenticity_score}"
        )

        return AgentSyncResponse(
            id=record.get("id"),
            user_id=request.user_id,
            event_date=request.event_date.isoformat() if hasattr(request.event_date, 'isoformat') else str(request.event_date),
            authenticity_score=request.authenticity_score,
            message="Authenticity data synced successfully",
        )

    except Exception as e:
        logger.error(f"Agent sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync agent data: {str(e)}",
        )


@router.get(
    "/history/{user_id}",
    response_model=AgentHistoryResponse,
    summary="Get agent authenticity history",
    description="Retrieve all agent authenticity records for a user.",
)
async def get_agent_history(
    user_id: str,
    db: AgentAuthenticityDB = Depends(get_agent_db),
    limit: int = 100,
    offset: int = 0,
) -> AgentHistoryResponse:
    """
    Get agent authenticity history for a user.

    Args:
        user_id: User identifier
        db: Agent database dependency
        limit: Max records to return
        offset: Pagination offset

    Returns:
        AgentHistoryResponse with list of records
    """
    try:
        records = await db.get_user_authenticity_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        return AgentHistoryResponse(
            user_id=user_id,
            total_records=len(records),
            history=records,
        )

    except Exception as e:
        logger.error(f"Agent history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent history: {str(e)}",
        )


@router.get(
    "/scan/{user_id}",
    response_model=AgentHistoryResponse,
    summary="Run fresh scan and return updated history",
    description=(
        "Simulates a live agent scan: generates new behavioral events since "
        "the last scan (as if the agent has been capturing in the background), "
        "recomputes today's authenticity score, upserts it to storage, and "
        "returns the updated history. Each refresh produces fresh, evolving "
        "data — just like a real agent running on the user's machine."
    ),
)
async def scan_agent_data(
    user_id: str,
    db: AgentAuthenticityDB = Depends(get_agent_db),
    auth_user: str = Depends(verify_agent_auth),
    limit: int = 100,
    offset: int = 0,
) -> AgentHistoryResponse:
    """
    Run a fresh scan of behavioral events.

    Uses the agent simulator to generate realistic new events since the
    last scan, extracts features, computes a fresh authenticity score,
    upserts it, and returns the updated history.

    Args:
        user_id: User identifier
        db: Agent database dependency
        auth_user: Authenticated user
        limit: Max records to return
        offset: Pagination offset

    Returns:
        AgentHistoryResponse with updated list of records
    """
    try:
        from ..agent.authenticity_scorer import get_authenticity_scorer

        scorer = get_authenticity_scorer()
        features = None
        result = None
        used_fallback = False

        # 1) Prefer REAL capture data. The local agent writes events to
        #    ~/.fpd-agent/agent_events.db; if real events exist, score those
        #    so the dashboard reflects actual behavior — never simulated.
        try:
            from ..agent.feature_extraction import extract_features

            features = extract_features(date.today())
            total_events = (
                features.get("total_keystrokes", 0)
                + features.get("total_mouse_events", 0)
                + features.get("total_window_events", 0)
            )
            if total_events > 0:
                result = scorer.score(features)
                logger.info(
                    f"Agent scan for user {user_id}: scored REAL local data "
                    f"score={result.authenticity_score} events={total_events}"
                )
        except Exception as e:
            logger.warning(
                f"Agent scan: real feature extraction failed ({e}) — will fall back"
            )

        # 2) Fall back to the simulator ONLY when there is no real data at
        #    all AND no real (non-simulated) record already exists for today.
        #    This prevents simulated scores from overwriting genuine synced data.
        #
        #    Once the simulator is running, it keeps accumulating events on
        #    every scan (the active session check bypasses the today_record
        #    guard so telemetry continues to evolve live).
        if result is None:
            from ..agent.simulator import has_active_session

            simulator_active = False
            try:
                simulator_active = has_active_session(user_id)
            except Exception:
                simulator_active = False

            today_iso = date.today().isoformat()
            existing = await db.get_user_authenticity_history(user_id, limit=100)
            today_record = next(
                (r for r in existing if r.get("date") == today_iso), None
            )

            if today_record is not None and not simulator_active:
                logger.info(
                    f"Agent scan for user {user_id}: real record exists for today "
                    f"— keeping real score {today_record.get('authenticity_score')}"
                )
            else:
                try:
                    from ..agent.simulator import simulate_agent_scan

                    sim_result = simulate_agent_scan(user_id)
                    features = sim_result["features"]
                    total_events = sim_result["total_events"]

                    if total_events > 0:
                        result = scorer.score(features)
                        used_fallback = True

                        await db.upsert_authenticity(
                            user_id=user_id,
                            event_date=date.today(),
                            authenticity_score=result.authenticity_score,
                            avg_typing_speed=features.get("avg_typing_speed"),
                            avg_mouse_velocity=features.get("mouse_velocity_mean"),
                            top_window_categories=features.get("active_window_categories", [])[:5],
                        )

                        logger.info(
                            f"Agent scan for user {user_id}: no real data — used simulator "
                            f"score={result.authenticity_score} events={total_events} "
                            f"new={sim_result['new_events']}"
                        )
                    else:
                        logger.info(
                            f"Agent scan: no events generated for {date.today().isoformat()} "
                            f"— returning existing history"
                        )
                except ImportError as e:
                    logger.warning(
                        f"Agent scan: simulator unavailable ({e}) — returning existing history"
                    )
                except Exception as e:
                    logger.warning(
                        f"Agent scan: simulation failed ({e}) — returning existing history"
                    )

        # Upsert the real-data score (only reached when real data scored
        # successfully above).
        if result is not None and not used_fallback and features is not None:
            await db.upsert_authenticity(
                user_id=user_id,
                event_date=date.today(),
                authenticity_score=result.authenticity_score,
                avg_typing_speed=features.get("avg_typing_speed"),
                avg_mouse_velocity=features.get("mouse_velocity_mean"),
                top_window_categories=features.get("active_window_categories", [])[:5],
            )
            logger.info(
                f"Agent scan for user {user_id}: upserted real-data score "
                f"score={result.authenticity_score}"
            )

        # Fetch and return updated history
        records = await db.get_user_authenticity_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        return AgentHistoryResponse(
            user_id=user_id,
            total_records=len(records),
            history=records,
        )

    except Exception as e:
        logger.error(f"Agent scan error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan agent data: {str(e)}",
        )


@router.get(
    "/status/{user_id}",
    summary="Get live agent status and telemetry",
    description=(
        "Returns real-time agent status: whether the agent is running, "
        "session duration, event counts (keystrokes, mouse moves, window "
        "switches), current active window, and activity metrics. This gives "
        "the dashboard a live 'agent is working' feel."
    ),
)
async def get_agent_status(
    user_id: str,
    auth_user: str = Depends(verify_agent_auth),
) -> dict:
    """
    Get live agent status and telemetry for a user.

    Args:
        user_id: User identifier
        auth_user: Authenticated user

    Returns:
        Dict with agent status, event counts, and session info
    """
    try:
        from ..agent.simulator import get_agent_status as get_sim_status

        status_data = get_sim_status(user_id)
        return {"status": status_data}

    except Exception as e:
        logger.error(f"Agent status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent status: {str(e)}",
        )


@router.get(
    "/latest/{user_id}",
    summary="Get latest authenticity score",
    description="Get the most recent agent authenticity record for a user.",
)
async def get_latest_authenticity(
    user_id: str,
    db: AgentAuthenticityDB = Depends(get_agent_db),
) -> dict:
    """
    Get the latest authenticity record for a user.

    Args:
        user_id: User identifier
        db: Agent database dependency

    Returns:
        Dict with the latest record or empty object
    """
    try:
        record = await db.get_latest_authenticity(user_id=user_id)
        return {"record": record}

    except Exception as e:
        logger.error(f"Latest authenticity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest authenticity: {str(e)}",
        )


@router.post(
    "/seed-demo",
    summary="Seed demo data for the agent",
    description="Generate 14 days of realistic demo agent data for a user.",
)
async def seed_demo_data(
    user_id: str = Query(..., description="User identifier to seed demo data for"),
    db: AgentAuthenticityDB = Depends(get_agent_db),
) -> dict:
    """
    Generate 14 days of demo data for testing the Agent Monitor.

    Uses the actual AuthenticityScorer to compute scores from simulated
    behavioral features so demo data is perfectly calibrated — no mismatches
    between features and scores.

    This endpoint does NOT require authentication — it is a demo/testing
    utility so the frontend can populate sample data without a valid
    Supabase session.
    """
    try:
        from ..agent.authenticity_scorer import get_authenticity_scorer

        scorer = get_authenticity_scorer()
        today = date.today()
        records_created = 0

        # Define day profiles for realistic 14-day variation.
        # Each profile generates features, then the scorer computes the
        # score — ensuring perfect accuracy alignment.
        day_profiles = [
            # Day 0 (today): focused productive day
            {
                "avg_typing_speed": random.uniform(110, 180),
                "typing_rhythm_variance": random.uniform(40, 75),
                "pause_ratio": random.uniform(0.08, 0.15),
                "mouse_velocity_mean": random.uniform(300, 550),
                "mouse_velocity_std": random.uniform(150, 350),
                "mouse_direction_change_freq": random.uniform(12, 25),
                "total_keystrokes": random.randint(3000, 8000),
                "total_mouse_events": random.randint(2000, 5000),
                "total_window_events": random.randint(20, 60),
                "total_active_seconds": random.uniform(18000, 28800),
                "active_window_categories": [
                    {"category": "Code/IDE", "seconds": random.uniform(10000, 18000)},
                    {"category": "Terminal/CLI", "seconds": random.uniform(2000, 5000)},
                    {"category": "Browser", "seconds": random.uniform(2000, 4000)},
                    {"category": "Communication", "seconds": random.uniform(500, 2000)},
                ],
            },
            # Day 1: balanced workday
            {
                "avg_typing_speed": random.uniform(140, 250),
                "typing_rhythm_variance": random.uniform(55, 100),
                "pause_ratio": random.uniform(0.10, 0.20),
                "mouse_velocity_mean": random.uniform(250, 500),
                "mouse_velocity_std": random.uniform(120, 280),
                "mouse_direction_change_freq": random.uniform(10, 22),
                "total_keystrokes": random.randint(2000, 6000),
                "total_mouse_events": random.randint(1500, 4000),
                "total_window_events": random.randint(30, 80),
                "total_active_seconds": random.uniform(14400, 25200),
                "active_window_categories": [
                    {"category": "Code/IDE", "seconds": random.uniform(6000, 12000)},
                    {"category": "Browser", "seconds": random.uniform(4000, 8000)},
                    {"category": "Communication", "seconds": random.uniform(2000, 5000)},
                    {"category": "Word/Office", "seconds": random.uniform(1000, 3000)},
                ],
            },
            # Day 2: meeting-heavy day
            {
                "avg_typing_speed": random.uniform(180, 320),
                "typing_rhythm_variance": random.uniform(70, 130),
                "pause_ratio": random.uniform(0.15, 0.25),
                "mouse_velocity_mean": random.uniform(200, 400),
                "mouse_velocity_std": random.uniform(100, 250),
                "mouse_direction_change_freq": random.uniform(8, 18),
                "total_keystrokes": random.randint(1200, 3500),
                "total_mouse_events": random.randint(1000, 3000),
                "total_window_events": random.randint(40, 100),
                "total_active_seconds": random.uniform(10800, 21600),
                "active_window_categories": [
                    {"category": "Communication", "seconds": random.uniform(6000, 12000)},
                    {"category": "Browser", "seconds": random.uniform(3000, 6000)},
                    {"category": "Code/IDE", "seconds": random.uniform(2000, 5000)},
                    {"category": "Email", "seconds": random.uniform(1000, 3000)},
                ],
            },
            # Day 3: deep focus coding
            {
                "avg_typing_speed": random.uniform(90, 160),
                "typing_rhythm_variance": random.uniform(35, 65),
                "pause_ratio": random.uniform(0.06, 0.12),
                "mouse_velocity_mean": random.uniform(350, 600),
                "mouse_velocity_std": random.uniform(180, 380),
                "mouse_direction_change_freq": random.uniform(15, 30),
                "total_keystrokes": random.randint(5000, 12000),
                "total_mouse_events": random.randint(3000, 7000),
                "total_window_events": random.randint(15, 40),
                "total_active_seconds": random.uniform(21600, 32400),
                "active_window_categories": [
                    {"category": "Code/IDE", "seconds": random.uniform(14000, 24000)},
                    {"category": "Terminal/CLI", "seconds": random.uniform(3000, 7000)},
                    {"category": "Browser", "seconds": random.uniform(1500, 3000)},
                ],
            },
            # Day 4: research day
            {
                "avg_typing_speed": random.uniform(150, 260),
                "typing_rhythm_variance": random.uniform(50, 100),
                "pause_ratio": random.uniform(0.12, 0.20),
                "mouse_velocity_mean": random.uniform(280, 480),
                "mouse_velocity_std": random.uniform(140, 300),
                "mouse_direction_change_freq": random.uniform(10, 20),
                "total_keystrokes": random.randint(1800, 4500),
                "total_mouse_events": random.randint(2000, 5000),
                "total_window_events": random.randint(35, 90),
                "total_active_seconds": random.uniform(14400, 25200),
                "active_window_categories": [
                    {"category": "Browser", "seconds": random.uniform(8000, 14000)},
                    {"category": "Code/IDE", "seconds": random.uniform(3000, 7000)},
                    {"category": "Word/Office", "seconds": random.uniform(2000, 5000)},
                    {"category": "Communication", "seconds": random.uniform(1000, 2000)},
                ],
            },
            # Day 5: distracted / low productivity day
            {
                "avg_typing_speed": random.uniform(250, 450),
                "typing_rhythm_variance": random.uniform(100, 200),
                "pause_ratio": random.uniform(0.25, 0.45),
                "mouse_velocity_mean": random.uniform(150, 350),
                "mouse_velocity_std": random.uniform(80, 200),
                "mouse_direction_change_freq": random.uniform(5, 12),
                "total_keystrokes": random.randint(500, 2000),
                "total_mouse_events": random.randint(800, 2500),
                "total_window_events": random.randint(50, 120),
                "total_active_seconds": random.uniform(7200, 14400),
                "active_window_categories": [
                    {"category": "Entertainment", "seconds": random.uniform(4000, 10000)},
                    {"category": "Browser", "seconds": random.uniform(3000, 6000)},
                    {"category": "Communication", "seconds": random.uniform(2000, 4000)},
                    {"category": "Code/IDE", "seconds": random.uniform(500, 2000)},
                ],
            },
            # Day 6: solid productive day
            {
                "avg_typing_speed": random.uniform(120, 200),
                "typing_rhythm_variance": random.uniform(45, 85),
                "pause_ratio": random.uniform(0.09, 0.16),
                "mouse_velocity_mean": random.uniform(320, 520),
                "mouse_velocity_std": random.uniform(160, 320),
                "mouse_direction_change_freq": random.uniform(12, 24),
                "total_keystrokes": random.randint(3500, 9000),
                "total_mouse_events": random.randint(2500, 6000),
                "total_window_events": random.randint(25, 55),
                "total_active_seconds": random.uniform(18000, 28800),
                "active_window_categories": [
                    {"category": "Code/IDE", "seconds": random.uniform(8000, 16000)},
                    {"category": "Browser", "seconds": random.uniform(3000, 6000)},
                    {"category": "Terminal/CLI", "seconds": random.uniform(2000, 4000)},
                    {"category": "Word/Office", "seconds": random.uniform(1000, 3000)},
                ],
            },
            # Day 7: design & creative work
            {
                "avg_typing_speed": random.uniform(160, 280),
                "typing_rhythm_variance": random.uniform(55, 110),
                "pause_ratio": random.uniform(0.12, 0.22),
                "mouse_velocity_mean": random.uniform(400, 650),
                "mouse_velocity_std": random.uniform(200, 420),
                "mouse_direction_change_freq": random.uniform(18, 35),
                "total_keystrokes": random.randint(1500, 4000),
                "total_mouse_events": random.randint(4000, 9000),
                "total_window_events": random.randint(20, 50),
                "total_active_seconds": random.uniform(14400, 25200),
                "active_window_categories": [
                    {"category": "Design", "seconds": random.uniform(6000, 12000)},
                    {"category": "Browser", "seconds": random.uniform(3000, 6000)},
                    {"category": "Code/IDE", "seconds": random.uniform(2000, 4000)},
                    {"category": "Communication", "seconds": random.uniform(1000, 2000)},
                ],
            },
            # Day 8: another distracted day (automation-like patterns)
            {
                "avg_typing_speed": random.uniform(25, 50),
                "typing_rhythm_variance": random.uniform(5, 20),
                "pause_ratio": random.uniform(0.02, 0.05),
                "mouse_velocity_mean": random.uniform(800, 1400),
                "mouse_velocity_std": random.uniform(40, 100),
                "mouse_direction_change_freq": random.uniform(2, 6),
                "total_keystrokes": random.randint(8000, 20000),
                "total_mouse_events": random.randint(1000, 3000),
                "total_window_events": random.randint(5, 15),
                "total_active_seconds": random.uniform(3600, 10800),
                "active_window_categories": [
                    {"category": "Entertainment", "seconds": random.uniform(5000, 10000)},
                    {"category": "Browser", "seconds": random.uniform(2000, 4000)},
                ],
            },
            # Day 9: email and admin day
            {
                "avg_typing_speed": random.uniform(170, 300),
                "typing_rhythm_variance": random.uniform(65, 120),
                "pause_ratio": random.uniform(0.14, 0.22),
                "mouse_velocity_mean": random.uniform(250, 420),
                "mouse_velocity_std": random.uniform(110, 260),
                "mouse_direction_change_freq": random.uniform(8, 18),
                "total_keystrokes": random.randint(2000, 5000),
                "total_mouse_events": random.randint(1500, 4000),
                "total_window_events": random.randint(40, 90),
                "total_active_seconds": random.uniform(14400, 21600),
                "active_window_categories": [
                    {"category": "Email", "seconds": random.uniform(5000, 9000)},
                    {"category": "Word/Office", "seconds": random.uniform(4000, 8000)},
                    {"category": "Browser", "seconds": random.uniform(2000, 5000)},
                    {"category": "Communication", "seconds": random.uniform(1500, 3000)},
                ],
            },
            # Day 10: good balanced day
            {
                "avg_typing_speed": random.uniform(130, 220),
                "typing_rhythm_variance": random.uniform(48, 90),
                "pause_ratio": random.uniform(0.10, 0.17),
                "mouse_velocity_mean": random.uniform(300, 520),
                "mouse_velocity_std": random.uniform(140, 310),
                "mouse_direction_change_freq": random.uniform(11, 22),
                "total_keystrokes": random.randint(3000, 7000),
                "total_mouse_events": random.randint(2000, 5000),
                "total_window_events": random.randint(25, 60),
                "total_active_seconds": random.uniform(16200, 27000),
                "active_window_categories": [
                    {"category": "Code/IDE", "seconds": random.uniform(7000, 14000)},
                    {"category": "Browser", "seconds": random.uniform(3000, 6000)},
                    {"category": "Terminal/CLI", "seconds": random.uniform(1500, 3500)},
                    {"category": "Communication", "seconds": random.uniform(1000, 2500)},
                    {"category": "Entertainment", "seconds": random.uniform(300, 1200)},
                ],
            },
            # Day 11: mostly idle / short day
            {
                "avg_typing_speed": random.uniform(300, 500),
                "typing_rhythm_variance": random.uniform(90, 180),
                "pause_ratio": random.uniform(0.30, 0.50),
                "mouse_velocity_mean": random.uniform(150, 300),
                "mouse_velocity_std": random.uniform(70, 180),
                "mouse_direction_change_freq": random.uniform(4, 10),
                "total_keystrokes": random.randint(300, 1000),
                "total_mouse_events": random.randint(500, 1500),
                "total_window_events": random.randint(10, 30),
                "total_active_seconds": random.uniform(3600, 7200),
                "active_window_categories": [
                    {"category": "Browser", "seconds": random.uniform(2000, 4000)},
                    {"category": "Communication", "seconds": random.uniform(1000, 2500)},
                    {"category": "Code/IDE", "seconds": random.uniform(500, 1500)},
                ],
            },
            # Day 12: highly productive terminal work
            {
                "avg_typing_speed": random.uniform(100, 170),
                "typing_rhythm_variance": random.uniform(38, 72),
                "pause_ratio": random.uniform(0.07, 0.14),
                "mouse_velocity_mean": random.uniform(280, 480),
                "mouse_velocity_std": random.uniform(130, 290),
                "mouse_direction_change_freq": random.uniform(10, 20),
                "total_keystrokes": random.randint(4000, 10000),
                "total_mouse_events": random.randint(1500, 4000),
                "total_window_events": random.randint(20, 50),
                "total_active_seconds": random.uniform(18000, 28800),
                "active_window_categories": [
                    {"category": "Terminal/CLI", "seconds": random.uniform(8000, 15000)},
                    {"category": "Code/IDE", "seconds": random.uniform(5000, 10000)},
                    {"category": "Browser", "seconds": random.uniform(2000, 4000)},
                ],
            },
            # Day 13: average mixed day
            {
                "avg_typing_speed": random.uniform(150, 270),
                "typing_rhythm_variance": random.uniform(55, 105),
                "pause_ratio": random.uniform(0.12, 0.20),
                "mouse_velocity_mean": random.uniform(270, 460),
                "mouse_velocity_std": random.uniform(130, 280),
                "mouse_direction_change_freq": random.uniform(9, 19),
                "total_keystrokes": random.randint(2000, 5500),
                "total_mouse_events": random.randint(1800, 4500),
                "total_window_events": random.randint(30, 70),
                "total_active_seconds": random.uniform(12600, 23400),
                "active_window_categories": [
                    {"category": "Browser", "seconds": random.uniform(5000, 9000)},
                    {"category": "Code/IDE", "seconds": random.uniform(3000, 6000)},
                    {"category": "Communication", "seconds": random.uniform(2000, 4000)},
                    {"category": "Word/Office", "seconds": random.uniform(1000, 3000)},
                    {"category": "Entertainment", "seconds": random.uniform(500, 2000)},
                ],
            },
        ]

        for i in range(14):
            event_date = today - timedelta(days=i)
            features = day_profiles[i]

            # Use the real scorer to compute the score from these features
            result = scorer.score(features)
            score = result.authenticity_score

            await db.upsert_authenticity(
                user_id=user_id,
                event_date=event_date,
                authenticity_score=score,
                avg_typing_speed=features["avg_typing_speed"],
                avg_mouse_velocity=features["mouse_velocity_mean"],
                top_window_categories=features["active_window_categories"][:5],
            )
            records_created += 1

        return {"success": True, "message": f"Successfully seeded {records_created} records of demo data"}

    except Exception as e:
        logger.error(f"Seed demo data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed demo data: {str(e)}",
        )