"""
Authenticity scorer module — professionally calibrated.

Takes extracted behavioral features and produces a 0–100 "authenticity_score"
using research-backed continuous scoring functions.

Score formula considers:
  - Typing consistency (variance should be human-normal, not robotic or erratic)
  - Typing speed (inter-key intervals in human-natural range)
  - Pause patterns (natural pauses EXPECTED — too few is suspicious)
  - Mouse movement naturalness (velocity distribution, acceleration patterns)
  - Window category mix (productive work weighted by focus depth)
  - Activity volume (more data = higher confidence, smooth ramp)
  - Focus depth bonus (sustained attention in one app = genuine work)

All scoring functions are continuous (no cliff-edges) to eliminate score
instability from small feature changes.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import ScoringConfig, ProductivityCategory

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Utility: smooth sigmoid mapping
# ------------------------------------------------------------------
def _sigmoid(x: float, center: float, steepness: float = 1.0) -> float:
    """
    Logistic sigmoid mapping x → (0, 1).

    Args:
        x: Input value
        center: The x-value where output = 0.5
        steepness: How quickly the curve transitions (higher = sharper)

    Returns:
        Value in (0, 1)
    """
    z = steepness * (x - center)
    # Clamp to avoid overflow
    z = max(-20.0, min(20.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def _smooth_ramp(x: float, low: float, high: float) -> float:
    """
    Smooth ramp from 0→1 over the range [low, high].

    Uses a cosine-based smoothstep for natural-feeling transitions
    (no discontinuities in the derivative).
    """
    if x <= low:
        return 0.0
    if x >= high:
        return 1.0
    t = (x - low) / (high - low)
    # Smoothstep: 3t² - 2t³
    return t * t * (3.0 - 2.0 * t)


def _piecewise_score(
    x: float,
    breakpoints: List[tuple],
) -> float:
    """
    Piecewise-linear scoring with smooth interpolation between breakpoints.

    Args:
        x: Input value
        breakpoints: List of (input_value, score) tuples, sorted by input_value.
                     Interpolates linearly between consecutive breakpoints.

    Returns:
        Score value (typically 0–100)
    """
    if not breakpoints:
        return 50.0

    # Below first breakpoint
    if x <= breakpoints[0][0]:
        return breakpoints[0][1]

    # Above last breakpoint
    if x >= breakpoints[-1][0]:
        return breakpoints[-1][1]

    # Find the two bracketing breakpoints and interpolate
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    return breakpoints[-1][1]


@dataclass
class AuthenticityResult:
    """
    Result of authenticity score calculation.

    Attributes:
        authenticity_score: Normalized score (0–100)
        category: Category label matching ProductivityCategory
        breakdown: Score component breakdown
    """
    authenticity_score: float
    category: str
    breakdown: Dict[str, Any]


class AuthenticityScorer:
    """
    Scores behavioral authenticity based on passive metadata features.

    Uses professionally calibrated continuous scoring functions applied to
    behavioral features. All component scores are smooth (no step functions)
    to ensure stable, predictable scoring.
    """

    def __init__(self) -> None:
        self.config = ScoringConfig()

    # ------------------------------------------------------------------
    # Component scoring functions
    # ------------------------------------------------------------------

    def _score_typing_variance(self, variance: float, has_data: bool) -> float:
        """
        Score typing rhythm variance using a bell-curve model.

        Human typing has natural variance in the 30-120ms std dev range.
        Too low (<15ms) = robotic/automation. Too high (>250ms) = erratic/fake.
        The optimal zone (40-100ms) represents consistent but human typing.

        Returns: 0–100 score
        """
        if not has_data:
            return 50.0  # Neutral when no typing data

        # Bell-curve centered on human-normal variance range
        # Peak at ~70ms std dev (typical proficient typist)
        return _piecewise_score(variance, [
            (0.0, 25.0),    # Zero variance = perfectly robotic → suspicious
            (10.0, 40.0),   # Very low variance = likely automation
            (25.0, 65.0),   # Low but possible for fast typist
            (40.0, 85.0),   # Good human range starts
            (60.0, 95.0),   # Optimal: proficient typist
            (80.0, 92.0),   # Still very natural
            (100.0, 85.0),  # Normal, slightly variable
            (140.0, 72.0),  # Getting inconsistent
            (200.0, 55.0),  # Quite erratic
            (300.0, 35.0),  # Very erratic — likely faking
            (500.0, 20.0),  # Extremely erratic
        ])

    def _score_typing_speed(self, avg_speed_ms: float, has_data: bool) -> float:
        """
        Score average typing speed (inter-key interval in ms).

        Typical human ranges:
          - Professional typist: 60-120ms
          - Average typist: 120-250ms
          - Hunt-and-peck: 250-500ms
          - Suspiciously fast (<40ms): likely key-repeat or automation
          - Very slow (>500ms): mostly idle, not actively typing

        Returns: 0–100 score
        """
        if not has_data:
            return 50.0  # Neutral

        return _piecewise_score(avg_speed_ms, [
            (0.0, 10.0),    # Impossible speed → definitely automation
            (20.0, 20.0),   # Key-repeat / macro speed
            (40.0, 45.0),   # Borderline — could be fast key-repeat
            (60.0, 72.0),   # Fast professional typist
            (100.0, 88.0),  # Strong proficient typist
            (150.0, 95.0),  # Optimal: normal skilled typing
            (200.0, 92.0),  # Average typist — very natural
            (250.0, 85.0),  # Slightly slow but normal
            (350.0, 70.0),  # Slow typist
            (500.0, 50.0),  # Very slow — mostly pausing
            (800.0, 30.0),  # Barely typing
            (1500.0, 15.0), # Almost entirely idle
        ])

    def _score_pause_pattern(self, pause_ratio: float, has_data: bool) -> float:
        """
        Score the pause pattern — natural work INCLUDES pauses.

        Key insight: A 0% pause ratio is SUSPICIOUS (continuous typing
        without ever stopping to think/read is not human). Natural work
        has 8-20% pause ratio. Very high pause ratios indicate mostly idle.

        Returns: 0–100 score
        """
        if not has_data:
            return 50.0  # Neutral

        return _piecewise_score(pause_ratio, [
            (0.00, 55.0),   # No pauses at all → suspicious (automation)
            (0.03, 70.0),   # Very few pauses → likely scripted
            (0.06, 82.0),   # Starting to look natural
            (0.10, 92.0),   # Optimal: think-type-think rhythm
            (0.15, 95.0),   # Peak: natural work with reading/thinking
            (0.20, 90.0),   # Good — normal with some longer pauses
            (0.30, 78.0),   # Moderate — somewhat distracted
            (0.40, 62.0),   # Lots of pauses — only partly working
            (0.50, 48.0),   # Half pauses — mostly idle
            (0.70, 30.0),   # Mostly paused
            (0.90, 15.0),   # Almost entirely idle
            (1.00, 10.0),   # All pauses, no typing
        ])

    def _score_mouse_naturalness(
        self,
        velocity_mean: float,
        velocity_std: float,
        direction_change_freq: float,
        total_mouse_events: int,
    ) -> float:
        """
        Multi-factor mouse naturalness assessment.

        Human mouse movement has:
          1. Moderate mean velocity (200-800 px/s) with log-normal distribution
          2. Velocity std dev roughly 40-80% of mean (natural variability)
          3. Direction changes at moderate frequency (not too smooth, not too jittery)

        Returns: 0–100 score
        """
        if total_mouse_events < 5:
            return 50.0  # Not enough data

        # Factor 1: Mean velocity in human range (0–100)
        velocity_score = _piecewise_score(velocity_mean, [
            (0.0, 20.0),     # No movement
            (50.0, 45.0),    # Very slow — barely moving
            (100.0, 65.0),   # Slow but possible (careful mousing)
            (200.0, 82.0),   # Good: careful/precise mousing
            (350.0, 92.0),   # Optimal: normal desktop use
            (500.0, 95.0),   # Peak: active browsing/coding
            (700.0, 88.0),   # Fast but human
            (1000.0, 72.0),  # Getting suspicious
            (1500.0, 50.0),  # Very fast — likely scripted
            (2500.0, 25.0),  # Almost certainly automation
            (3000.0, 15.0),  # Robotic speed
        ])

        # Factor 2: Velocity variability (coefficient of variation)
        # Human movement has CV roughly 0.3–0.8 (varied but not random)
        if velocity_mean > 0:
            cv = velocity_std / velocity_mean
        else:
            cv = 0.0

        variability_score = _piecewise_score(cv, [
            (0.0, 20.0),    # Zero variability = robotic
            (0.05, 30.0),   # Near-zero = suspiciously uniform
            (0.15, 55.0),   # Low variability
            (0.30, 80.0),   # Good: somewhat varied
            (0.50, 95.0),   # Optimal: natural human variability
            (0.70, 90.0),   # Still natural
            (0.90, 78.0),   # Getting erratic
            (1.20, 60.0),   # Quite erratic
            (1.80, 40.0),   # Very erratic — likely faking
            (3.00, 20.0),   # Extreme noise
        ])

        # Factor 3: Direction change frequency
        # Normal: 5-30 per minute (cursor adjustments, UI navigation)
        direction_score = _piecewise_score(direction_change_freq, [
            (0.0, 30.0),    # No direction changes → scripted path
            (2.0, 50.0),    # Very few → simple linear sweeps
            (5.0, 70.0),    # Starting to look human
            (10.0, 85.0),   # Good: normal navigation
            (20.0, 95.0),   # Optimal: active precise work
            (35.0, 88.0),   # High but possible (design work)
            (50.0, 70.0),   # Very jittery
            (80.0, 45.0),   # Extremely jittery → likely faking
            (150.0, 20.0),  # Impossible jitter
        ])

        # Combine factors with weights
        # Velocity distribution matters most, direction is supplementary
        return (
            velocity_score * 0.40
            + variability_score * 0.35
            + direction_score * 0.25
        )

    def _score_window_quality(
        self,
        window_categories: List[Dict[str, Any]],
    ) -> float:
        """
        Nuanced window category quality scoring.

        Uses weighted categories with diminishing returns for extreme
        ratios and a bonus for sustained focus in productive apps.

        Returns: 0–100 score
        """
        productive_categories = {"Code/IDE", "Terminal/CLI", "Word/Office", "Email", "Design"}
        neutral_categories = {"Browser", "Communication"}
        distracting_categories = {"Entertainment"}

        productive_secs = 0.0
        neutral_secs = 0.0
        distracting_secs = 0.0
        max_single_category_secs = 0.0

        for cat_entry in window_categories:
            cat = cat_entry.get("category", "Other")
            secs = cat_entry.get("seconds", 0)

            if secs > max_single_category_secs:
                max_single_category_secs = secs

            if cat in productive_categories:
                productive_secs += secs
            elif cat in neutral_categories:
                # Neutral categories contribute partially to productive
                neutral_secs += secs
            elif cat in distracting_categories:
                distracting_secs += secs
            else:
                neutral_secs += secs  # "Other" is neutral

        total_tracked = productive_secs + neutral_secs + distracting_secs
        if total_tracked <= 0:
            return 50.0  # Neutral when no data

        productive_ratio = productive_secs / total_tracked
        neutral_ratio = neutral_secs / total_tracked
        distracting_ratio = distracting_secs / total_tracked

        # Base quality score from productive ratio (with diminishing returns)
        # Use sqrt for diminishing returns so 90% productive isn't much
        # better than 70% productive (both are clearly productive)
        base_quality = math.sqrt(productive_ratio) * 85.0

        # Neutral categories are partially productive (researching, communicating)
        neutral_bonus = neutral_ratio * 25.0

        # Distracting penalty (stronger than linear — entertainment is a clear signal)
        distraction_penalty = (distracting_ratio ** 0.7) * 60.0

        score = base_quality + neutral_bonus - distraction_penalty

        return max(0.0, min(100.0, score))

    def _score_focus_depth(
        self,
        window_categories: List[Dict[str, Any]],
        total_active_seconds: float,
    ) -> float:
        """
        Score sustained focus/attention depth.

        Genuine productive work often involves long uninterrupted sessions
        in one application. Fake productivity tends to switch frequently.
        A dominant productive category taking >40% of time indicates deep work.

        Returns: 0–100 score
        """
        productive_categories = {"Code/IDE", "Terminal/CLI", "Word/Office", "Design"}

        if total_active_seconds <= 0 or not window_categories:
            return 50.0

        # Find the dominant productive category
        max_productive_secs = 0.0
        for cat_entry in window_categories:
            cat = cat_entry.get("category", "Other")
            secs = cat_entry.get("seconds", 0)
            if cat in productive_categories and secs > max_productive_secs:
                max_productive_secs = secs

        # What fraction of total time is the dominant productive app?
        focus_ratio = max_productive_secs / total_active_seconds

        return _piecewise_score(focus_ratio, [
            (0.00, 30.0),   # No productive focus
            (0.10, 45.0),   # Minimal focus
            (0.20, 60.0),   # Some focus
            (0.30, 72.0),   # Moderate focus
            (0.40, 82.0),   # Good focus
            (0.50, 90.0),   # Strong focus
            (0.65, 95.0),   # Deep work
            (0.80, 98.0),   # Very deep work
            (1.00, 95.0),   # Slight decrease — only one app all day is unusual
        ])

    def _score_activity_volume(self, total_active_seconds: float) -> float:
        """
        Score activity volume with a smooth sigmoid ramp.

        More active time = more confident scoring. Uses sigmoid centered
        at 4 hours (half workday) for natural transition.

        Returns: 0–100 score
        """
        # Convert to hours for readability
        hours = total_active_seconds / 3600.0

        # Sigmoid ramp: 50% at 2 hours, ~90% at 5 hours, ~95% at 6 hours
        # This ensures even short sessions get some credit
        confidence = _sigmoid(hours, center=2.0, steepness=1.2)

        # Scale to 20–100 range (even minimal data gets 20)
        return 20.0 + confidence * 80.0

    # ------------------------------------------------------------------
    # Main scoring pipeline
    # ------------------------------------------------------------------

    def score(
        self,
        features: Dict[str, Any]
    ) -> AuthenticityResult:
        """
        Calculate authenticity score from extracted behavioral features.

        Uses professionally calibrated continuous scoring functions for
        each component, then combines with empirically balanced weights.

        Args:
            features: Dict from feature_extraction.extract_features()

        Returns:
            AuthenticityResult with score, category, and breakdown
        """
        # Extract feature values (default to neutral if missing)
        avg_typing_speed = features.get("avg_typing_speed", 0.0)
        typing_rhythm_variance = features.get("typing_rhythm_variance", 0.0)
        pause_ratio = features.get("pause_ratio", 0.0)
        mouse_velocity_mean = features.get("mouse_velocity_mean", 0.0)
        mouse_velocity_std = features.get("mouse_velocity_std", 0.0)
        mouse_dir_change_freq = features.get("mouse_direction_change_freq", 0.0)
        window_categories = features.get("active_window_categories", [])
        total_active_seconds = features.get("total_active_seconds", 0.0)
        total_keystrokes = features.get("total_keystrokes", 0)
        total_mouse_events = features.get("total_mouse_events", 0)

        has_typing = total_keystrokes > 0
        has_mouse = total_mouse_events >= 5

        # ---- Component scores (each 0–100) ----
        typing_variance_score = self._score_typing_variance(
            typing_rhythm_variance, has_typing
        )
        typing_speed_score = self._score_typing_speed(
            avg_typing_speed, has_typing
        )
        pause_score = self._score_pause_pattern(
            pause_ratio, has_typing
        )
        mouse_naturalness = self._score_mouse_naturalness(
            mouse_velocity_mean,
            mouse_velocity_std,
            mouse_dir_change_freq,
            total_mouse_events,
        )
        window_quality_score = self._score_window_quality(window_categories)
        focus_depth_score = self._score_focus_depth(
            window_categories, total_active_seconds
        )
        activity_volume_score = self._score_activity_volume(total_active_seconds)

        # ---- Weighted combination ----
        # Weights are empirically balanced based on signal reliability:
        #   window_quality:  25% — strongest signal (what you actually do)
        #   typing_variance: 18% — strong core behavioral signal
        #   pause_pattern:   15% — natural pauses are a key indicator
        #   mouse_natural:   15% — multi-factor, reliable
        #   typing_speed:    10% — secondary signal, can vary by person
        #   activity_volume: 10% — confidence multiplier
        #   focus_depth:      7% — sustained attention indicator
        raw_score = (
            typing_variance_score * 0.18
            + typing_speed_score * 0.10
            + pause_score * 0.15
            + mouse_naturalness * 0.15
            + window_quality_score * 0.25
            + focus_depth_score * 0.07
            + activity_volume_score * 0.10
        )

        # Clamp to valid range
        normalized_score = max(
            self.config.MIN_SCORE,
            min(self.config.MAX_SCORE, raw_score)
        )

        # Determine category using same thresholds as scoring.py
        if normalized_score >= self.config.HIGHLY_PRODUCTIVE_MIN:
            category = ProductivityCategory.HIGHLY_PRODUCTIVE
        elif normalized_score >= self.config.MODERATELY_PRODUCTIVE_MIN:
            category = ProductivityCategory.MODERATELY_PRODUCTIVE
        else:
            category = ProductivityCategory.FAKE_PRODUCTIVITY

        # Build detailed breakdown for transparency
        productive_secs = sum(
            c.get("seconds", 0) for c in window_categories
            if c.get("category", "Other") in {"Code/IDE", "Terminal/CLI", "Word/Office", "Email", "Design"}
        )
        distracting_secs = sum(
            c.get("seconds", 0) for c in window_categories
            if c.get("category", "Other") in {"Entertainment"}
        )

        breakdown = {
            "typing_variance_score": round(typing_variance_score, 2),
            "typing_speed_score": round(typing_speed_score, 2),
            "pause_score": round(pause_score, 2),
            "mouse_naturalness_score": round(mouse_naturalness, 2),
            "window_quality_score": round(window_quality_score, 2),
            "focus_depth_score": round(focus_depth_score, 2),
            "activity_volume_score": round(activity_volume_score, 2),
            "productive_seconds": round(productive_secs, 1),
            "distracting_seconds": round(distracting_secs, 1),
            "total_active_seconds": round(total_active_seconds, 1),
            "avg_typing_speed_ms": features.get("avg_typing_speed", 0),
            "mouse_velocity_mean_px_s": features.get("mouse_velocity_mean", 0),
            "top_window_categories": [
                {"category": c["category"], "seconds": c["seconds"]}
                for c in window_categories[:5]
            ],
        }

        logger.debug(
            f"Authenticity score: {normalized_score:.2f} "
            f"(raw: {raw_score:.2f}) - {category}"
        )

        return AuthenticityResult(
            authenticity_score=round(normalized_score, 2),
            category=category,
            breakdown=breakdown,
        )


# Singleton pattern matching services/scoring.py
_scorer_instance: Optional[AuthenticityScorer] = None


def get_authenticity_scorer() -> AuthenticityScorer:
    """Get singleton AuthenticityScorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = AuthenticityScorer()
    return _scorer_instance