"""
Authenticity scorer module — professionally calibrated.

Takes extracted behavioral features and produces a 0–100 "authenticity_score"
using research-backed continuous scoring functions. Includes hardware-level
injection detection and biometric flight/dwell CV analysis.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import ScoringConfig, ProductivityCategory

logger = logging.getLogger(__name__)

def _sigmoid(x: float, center: float, steepness: float = 1.0) -> float:
    z = steepness * (x - center)
    z = max(-20.0, min(20.0, z))
    return 1.0 / (1.0 + math.exp(-z))

def _piecewise_score(x: float, breakpoints: List[tuple]) -> float:
    if not breakpoints:
        return 50.0
    if x <= breakpoints[0][0]:
        return breakpoints[0][1]
    if x >= breakpoints[-1][0]:
        return breakpoints[-1][1]
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
    authenticity_score: float
    category: str
    breakdown: Dict[str, Any]
    confidence: str = "High"


class AuthenticityScorer:
    def __init__(self) -> None:
        self.config = ScoringConfig()

    def _score_typing_speed(self, avg_speed_ms: float) -> float:
        """
        Score average typing speed (mean inter-key interval in ms).
        
        Calibrated against real human benchmarks (approximate):
          - Elite (100-120 WPM): ~100-120ms
          - Fast (80-100 WPM): ~120-170ms
          - Average (40-80 WPM): ~170-300ms
          - Slow (25-40 WPM): ~300-480ms
        """
        return _piecewise_score(avg_speed_ms, [
            (0.0, 10.0),    # Impossible speed → definitely automation
            (50.0, 30.0),   # Very suspicious (likely macro)
            (95.0, 75.0),   # Extremely fast, possible but rare
            (100.0, 90.0),  # Elite typist (DO NOT penalize)
            (120.0, 95.0),  # Fast typist
            (170.0, 95.0),  # Average-fast typist
            (300.0, 85.0),  # Average typist
            (480.0, 65.0),  # Slow typist
            (800.0, 40.0),  # Very slow — barely typing
        ])

    def _score_typing_variance(self, variance: float) -> float:
        """Score inter-key variance."""
        return _piecewise_score(variance, [
            (0.0, 10.0),    
            (10.0, 30.0),   
            (25.0, 70.0),   
            (40.0, 85.0),   
            (60.0, 95.0),   
            (100.0, 85.0),  
            (140.0, 72.0),  
            (200.0, 55.0),  
            (300.0, 35.0),  
        ])

    def _score_flight_cv(self, flight_cv: float) -> float:
        """
        Score flight time Coefficient of Variation (std / mean).
        Human typing flight CV is generally 0.5 - 1.0. 
        Near zero implies a scripted macro or robotic loop.
        """
        return _piecewise_score(flight_cv, [
            (0.0, 5.0),      # Perfectly robotic
            (0.10, 25.0),    # Highly suspicious
            (0.25, 60.0),    # Borderline
            (0.40, 85.0),    # Natural lower bound
            (0.60, 95.0),    # Optimal natural
            (1.00, 95.0),    # High variability (still natural)
            (1.50, 75.0),    # Erratic
        ])

    def _score_dwell_cv(self, dwell_cv: float) -> float:
        """
        Score dwell time Coefficient of Variation (std / mean).
        Human dwell CV is usually > 0.2. Near zero is suspicious.
        """
        return _piecewise_score(dwell_cv, [
            (0.0, 5.0),      
            (0.05, 20.0),    
            (0.15, 60.0),    
            (0.25, 95.0),    
            (0.50, 90.0),    
            (0.80, 75.0),    
        ])

    def _score_pause_pattern(self, pause_ratio: float) -> float:
        return _piecewise_score(pause_ratio, [
            (0.00, 55.0),   
            (0.03, 70.0),   
            (0.10, 92.0),   
            (0.15, 95.0),   
            (0.30, 78.0),   
            (0.50, 48.0),   
            (0.90, 15.0),   
        ])

    def _score_mouse_naturalness(self, v_mean: float, v_std: float, dir_freq: float, count: int) -> float:
        if count < 5: return 50.0
        v_score = _piecewise_score(v_mean, [
            (0.0, 20.0), (100.0, 65.0), (350.0, 92.0), (700.0, 88.0), (1500.0, 50.0), (2500.0, 25.0)
        ])
        cv = v_std / v_mean if v_mean > 0 else 0
        var_score = _piecewise_score(cv, [
            (0.0, 20.0), (0.15, 55.0), (0.50, 95.0), (0.90, 78.0), (1.80, 40.0)
        ])
        dir_score = _piecewise_score(dir_freq, [
            (0.0, 30.0), (5.0, 70.0), (20.0, 95.0), (50.0, 70.0), (100.0, 40.0)
        ])
        return (v_score * 0.40) + (var_score * 0.35) + (dir_score * 0.25)

    def _score_window_quality(self, categories: List[Dict[str, Any]]) -> float:
        prod_secs = sum(c["seconds"] for c in categories if c["category"] in {"Code/IDE", "Terminal/CLI", "Word/Office", "Email", "Design"})
        neut_secs = sum(c["seconds"] for c in categories if c["category"] in {"Browser", "Communication", "Other"})
        dist_secs = sum(c["seconds"] for c in categories if c["category"] == "Entertainment")
        
        total = prod_secs + neut_secs + dist_secs
        if total <= 0: return 50.0

        p_ratio = prod_secs / total
        n_ratio = neut_secs / total
        d_ratio = dist_secs / total

        base = math.sqrt(p_ratio) * 85.0
        bonus = n_ratio * 25.0
        penalty = (d_ratio ** 0.7) * 60.0

        return max(0.0, min(100.0, base + bonus - penalty))

    def _score_focus_depth(self, categories: List[Dict[str, Any]], total: float) -> float:
        if total <= 0 or not categories: return 50.0
        prod_cats = {"Code/IDE", "Terminal/CLI", "Word/Office", "Design"}
        max_prod = max([c["seconds"] for c in categories if c["category"] in prod_cats], default=0.0)
        return _piecewise_score(max_prod / total, [
            (0.0, 30.0), (0.2, 60.0), (0.4, 82.0), (0.65, 95.0), (1.0, 95.0)
        ])

    def _score_activity_volume(self, total: float) -> float:
        confidence = _sigmoid(total / 3600.0, center=2.0, steepness=1.2)
        return 20.0 + confidence * 80.0

    def score(self, features: Dict[str, Any]) -> AuthenticityResult:
        total_active = features.get("total_active_seconds", 0.0)
        total_keys = features.get("total_keystrokes", 0)
        total_mouse = features.get("total_mouse_events", 0)
        
        injected_ratio = features.get("injected_ratio", 0.0)
        
        # Check guard clause
        avg_typing_speed = features.get("avg_typing_speed")
        has_typing = avg_typing_speed is not None and total_keys >= 50
        
        confidence_str = "High"

        if has_typing:
            t_speed = self._score_typing_speed(avg_typing_speed)
            t_var = self._score_typing_variance(features.get("typing_rhythm_variance", 0.0))
            f_cv = self._score_flight_cv(features.get("flight_cv", 0.0))
            d_cv = self._score_dwell_cv(features.get("dwell_cv", 0.0))
            p_score = self._score_pause_pattern(features.get("pause_ratio", 0.0))
            
            # Heavy penalty if secondary robotic interval is high
            robotic_penalty = features.get("robotic_interval_ratio", 0.0) * 80.0
            
            typing_score = (t_speed * 0.20 + t_var * 0.25 + f_cv * 0.25 + d_cv * 0.15 + p_score * 0.15) - robotic_penalty
            typing_score = max(0.0, min(100.0, typing_score))
        else:
            typing_score = 50.0
            confidence_str = "Low (Insufficient Typing Data)"

        m_score = self._score_mouse_naturalness(
            features.get("mouse_velocity_mean", 0.0),
            features.get("mouse_velocity_std", 0.0),
            features.get("mouse_direction_change_freq", 0.0),
            total_mouse
        )
        
        w_cats = features.get("active_window_categories", [])
        w_score = self._score_window_quality(w_cats)
        f_depth = self._score_focus_depth(w_cats, total_active)
        v_score = self._score_activity_volume(total_active)

        # New weights incorporating biometric CV
        raw_score = (
            typing_score * 0.40
            + m_score * 0.15
            + w_score * 0.25
            + f_depth * 0.10
            + v_score * 0.10
        )

        normalized = max(self.config.MIN_SCORE, min(self.config.MAX_SCORE, raw_score))

        # Hard Bot Guard: If injected_ratio > 5%, cap final score heavily.
        # Rationale for 40: A score of 40 is well within "Fake Productivity" (<50). 
        # This guarantees that even if a bot perfectly simulates window switches and 
        # mouse movements, the explicit OS injection flag overrides it and forces a fail.
        if injected_ratio > 0.05:
            normalized = min(normalized, 40.0)
            confidence_str = "High (Bot Injection Detected)"

        if normalized >= self.config.HIGHLY_PRODUCTIVE_MIN:
            category = ProductivityCategory.HIGHLY_PRODUCTIVE
        elif normalized >= self.config.MODERATELY_PRODUCTIVE_MIN:
            category = ProductivityCategory.MODERATELY_PRODUCTIVE
        else:
            category = ProductivityCategory.FAKE_PRODUCTIVITY

        breakdown = {
            "typing_aggregate_score": round(typing_score, 2),
            "mouse_naturalness_score": round(m_score, 2),
            "window_quality_score": round(w_score, 2),
            "focus_depth_score": round(f_depth, 2),
            "injected_ratio": injected_ratio,
            "flight_cv": features.get("flight_cv", 0.0),
            "dwell_cv": features.get("dwell_cv", 0.0),
            "avg_typing_speed_ms": avg_typing_speed if has_typing else 0,
        }

        return AuthenticityResult(
            authenticity_score=round(normalized, 2),
            category=category,
            breakdown=breakdown,
            confidence=confidence_str
        )

_scorer_instance: Optional[AuthenticityScorer] = None

def get_authenticity_scorer() -> AuthenticityScorer:
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = AuthenticityScorer()
    return _scorer_instance