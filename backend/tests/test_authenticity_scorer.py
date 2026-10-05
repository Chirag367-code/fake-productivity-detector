"""
Test suite for AuthenticityScorer with new Biometric CV features and Injection guards.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.agent.authenticity_scorer import AuthenticityScorer

def _make_features(
    avg_typing_speed=200.0,
    typing_rhythm_variance=60.0,
    flight_cv=0.8,
    dwell_cv=0.4,
    injected_ratio=0.0,
    robotic_interval_ratio=0.0,
    pause_ratio=0.12,
    mouse_velocity_mean=400.0,
    mouse_velocity_std=200.0,
    mouse_direction_change_freq=15.0,
    total_keystrokes=5000,
    total_mouse_events=3000,
    total_active_seconds=21600.0,
):
    return {
        "avg_typing_speed": avg_typing_speed,
        "typing_rhythm_variance": typing_rhythm_variance,
        "flight_cv": flight_cv,
        "dwell_cv": dwell_cv,
        "injected_ratio": injected_ratio,
        "robotic_interval_ratio": robotic_interval_ratio,
        "pause_ratio": pause_ratio,
        "mouse_velocity_mean": mouse_velocity_mean,
        "mouse_velocity_std": mouse_velocity_std,
        "mouse_direction_change_freq": mouse_direction_change_freq,
        "total_keystrokes": total_keystrokes,
        "total_mouse_events": total_mouse_events,
        "total_active_seconds": total_active_seconds,
        "active_window_categories": [
            {"category": "Code/IDE", "seconds": 12000},
            {"category": "Browser", "seconds": 5000},
        ],
    }


def test_genuine_average_worker():
    """An average typist (200ms) with normal CVs should score Highly Productive."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=220,    # Average
        flight_cv=0.75,          # Natural
        dwell_cv=0.35,           # Natural
        injected_ratio=0.0,
    )
    result = scorer.score(features)
    print(f"  Genuine average: {result.authenticity_score:.1f}")
    assert result.authenticity_score >= 80, f"Expected >= 80, got {result.authenticity_score}"


def test_elite_typist():
    """An elite typist (110ms) should NOT be penalized as a bot."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=110,    # Elite
        flight_cv=0.6,           # Natural for fast typist
        dwell_cv=0.25,
        injected_ratio=0.0,
    )
    result = scorer.score(features)
    print(f"  Elite Typist: {result.authenticity_score:.1f}")
    assert result.authenticity_score >= 80, f"Expected >= 80, got {result.authenticity_score}"


def test_software_injection_macro():
    """Software injection (> 5% injected_ratio) MUST cap the score heavily (<= 40)."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=150,    # Seems normal
        flight_cv=0.8,           # Seems normal
        dwell_cv=0.4,
        injected_ratio=0.95,     # 95% injected by pyautogui
    )
    result = scorer.score(features)
    print(f"  Injected Bot: {result.authenticity_score:.1f} (Confidence: {result.confidence})")
    assert result.authenticity_score <= 40, f"Expected <= 40, got {result.authenticity_score}"
    assert "Bot Injection" in result.confidence


def test_hardware_macro_zero_cv():
    """A hardware macro (0% injection flag) but 0% CV should score low."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=150,    
        flight_cv=0.01,          # Robotic consistency
        dwell_cv=0.01,           # Robotic consistency
        injected_ratio=0.0,      # Hardware (not software injected)
    )
    result = scorer.score(features)
    print(f"  Hardware Macro (No CV): {result.authenticity_score:.1f}")
    assert result.authenticity_score <= 50, f"Expected <= 50, got {result.authenticity_score}"


def test_insufficient_data():
    """< 50 keystrokes returns None for stats. Scorer must return neutral 50 with Low Confidence."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=None,
        total_keystrokes=15,     # Insufficient
    )
    result = scorer.score(features)
    print(f"  Insufficient Data: {result.authenticity_score:.1f} (Confidence: {result.confidence})")
    assert "Low" in result.confidence

def main():
    tests = [
        test_genuine_average_worker,
        test_elite_typist,
        test_software_injection_macro,
        test_hardware_macro_zero_cv,
        test_insufficient_data
    ]
    for t in tests:
        t()
    print("[✓] All tests passed.")

if __name__ == "__main__":
    main()
