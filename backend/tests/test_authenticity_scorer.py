"""
Test script for the recalibrated AuthenticityScorer.

Verifies that the scorer correctly classifies different behavioral profiles
into the expected score ranges, ensuring professional-grade accuracy.

Run with: python -m pytest backend/tests/test_authenticity_scorer.py -v
Or standalone: python backend/tests/test_authenticity_scorer.py
"""

import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent.authenticity_scorer import AuthenticityScorer, get_authenticity_scorer


def _make_features(
    avg_typing_speed=150.0,
    typing_rhythm_variance=60.0,
    pause_ratio=0.12,
    mouse_velocity_mean=400.0,
    mouse_velocity_std=200.0,
    mouse_direction_change_freq=15.0,
    total_keystrokes=5000,
    total_mouse_events=3000,
    total_window_events=30,
    total_active_seconds=21600.0,
    active_window_categories=None,
):
    """Helper to build a feature dict with sensible defaults."""
    if active_window_categories is None:
        active_window_categories = [
            {"category": "Code/IDE", "seconds": 12000},
            {"category": "Browser", "seconds": 5000},
            {"category": "Terminal/CLI", "seconds": 3000},
        ]
    return {
        "avg_typing_speed": avg_typing_speed,
        "typing_rhythm_variance": typing_rhythm_variance,
        "pause_ratio": pause_ratio,
        "mouse_velocity_mean": mouse_velocity_mean,
        "mouse_velocity_std": mouse_velocity_std,
        "mouse_direction_change_freq": mouse_direction_change_freq,
        "total_keystrokes": total_keystrokes,
        "total_mouse_events": total_mouse_events,
        "total_window_events": total_window_events,
        "total_active_seconds": total_active_seconds,
        "active_window_categories": active_window_categories,
    }


def test_genuine_productive_worker():
    """A genuine productive worker should score 75-95 (Highly Productive)."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=150,           # Normal skilled typist
        typing_rhythm_variance=65,       # Natural variance
        pause_ratio=0.12,               # Healthy pause pattern
        mouse_velocity_mean=420,         # Active but natural
        mouse_velocity_std=210,          # Good variability
        mouse_direction_change_freq=18,  # Normal navigation
        total_keystrokes=6000,
        total_mouse_events=4000,
        total_active_seconds=25200,      # 7 hours
        active_window_categories=[
            {"category": "Code/IDE", "seconds": 14000},
            {"category": "Terminal/CLI", "seconds": 4000},
            {"category": "Browser", "seconds": 5000},
            {"category": "Communication", "seconds": 1500},
        ],
    )
    result = scorer.score(features)
    print(f"  Genuine productive: {result.authenticity_score:.1f} ({result.category})")
    assert 72 <= result.authenticity_score <= 98, (
        f"Expected 72-98, got {result.authenticity_score}"
    )
    return result


def test_automation_detected():
    """Automation patterns should score 20-45 (Fake Productivity)."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=30,             # Way too fast (automation)
        typing_rhythm_variance=8,        # Almost zero variance (robotic)
        pause_ratio=0.02,               # No pauses (continuous)
        mouse_velocity_mean=1200,        # Unrealistically fast
        mouse_velocity_std=60,           # Suspiciously uniform
        mouse_direction_change_freq=3,   # Linear paths (scripted)
        total_keystrokes=15000,
        total_mouse_events=2000,
        total_active_seconds=7200,       # 2 hours
        active_window_categories=[
            {"category": "Entertainment", "seconds": 5000},
            {"category": "Browser", "seconds": 2000},
        ],
    )
    result = scorer.score(features)
    print(f"  Automation detected: {result.authenticity_score:.1f} ({result.category})")
    assert result.authenticity_score <= 50, (
        f"Expected ≤50, got {result.authenticity_score}"
    )
    return result


def test_distracted_user():
    """Mostly entertainment + erratic patterns should score 35-55."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=350,            # Slow, inconsistent
        typing_rhythm_variance=180,      # Very erratic
        pause_ratio=0.35,               # Lots of pauses
        mouse_velocity_mean=200,         # Slow mouse
        mouse_velocity_std=120,          # Moderate variability
        mouse_direction_change_freq=7,   # Low engagement
        total_keystrokes=800,
        total_mouse_events=1200,
        total_active_seconds=10800,      # 3 hours
        active_window_categories=[
            {"category": "Entertainment", "seconds": 6000},
            {"category": "Browser", "seconds": 3000},
            {"category": "Communication", "seconds": 1500},
            {"category": "Code/IDE", "seconds": 300},
        ],
    )
    result = scorer.score(features)
    print(f"  Distracted user: {result.authenticity_score:.1f} ({result.category})")
    assert result.authenticity_score <= 60, (
        f"Expected ≤60, got {result.authenticity_score}"
    )
    return result


def test_moderate_productivity():
    """Mixed day with some productive work should score 55-78."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=220,            # Average typist
        typing_rhythm_variance=90,       # Moderate variance
        pause_ratio=0.18,               # Normal pauses
        mouse_velocity_mean=320,         # Moderate movement
        mouse_velocity_std=180,          # Normal variability
        mouse_direction_change_freq=12,  # Moderate navigation
        total_keystrokes=3000,
        total_mouse_events=2500,
        total_active_seconds=18000,      # 5 hours
        active_window_categories=[
            {"category": "Browser", "seconds": 7000},
            {"category": "Communication", "seconds": 4000},
            {"category": "Code/IDE", "seconds": 4000},
            {"category": "Word/Office", "seconds": 2000},
            {"category": "Entertainment", "seconds": 1000},
        ],
    )
    result = scorer.score(features)
    print(f"  Moderate productivity: {result.authenticity_score:.1f} ({result.category})")
    assert 50 <= result.authenticity_score <= 82, (
        f"Expected 50-82, got {result.authenticity_score}"
    )
    return result


def test_mostly_idle():
    """Very little activity should score 30-55 (low confidence)."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=450,            # Very slow (barely typing)
        typing_rhythm_variance=150,      # High variance
        pause_ratio=0.50,               # Half pauses
        mouse_velocity_mean=150,         # Barely moving
        mouse_velocity_std=80,           # Low variability
        mouse_direction_change_freq=5,   # Minimal navigation
        total_keystrokes=200,
        total_mouse_events=400,
        total_active_seconds=3600,       # 1 hour
        active_window_categories=[
            {"category": "Browser", "seconds": 2000},
            {"category": "Communication", "seconds": 1000},
            {"category": "Code/IDE", "seconds": 600},
        ],
    )
    result = scorer.score(features)
    print(f"  Mostly idle: {result.authenticity_score:.1f} ({result.category})")
    assert result.authenticity_score <= 60, (
        f"Expected ≤60, got {result.authenticity_score}"
    )
    return result


def test_no_data():
    """Empty features should score neutral (~50)."""
    scorer = AuthenticityScorer()
    features = _make_features(
        avg_typing_speed=0,
        typing_rhythm_variance=0,
        pause_ratio=0,
        mouse_velocity_mean=0,
        mouse_velocity_std=0,
        mouse_direction_change_freq=0,
        total_keystrokes=0,
        total_mouse_events=0,
        total_active_seconds=0,
        active_window_categories=[],
    )
    result = scorer.score(features)
    print(f"  No data (neutral): {result.authenticity_score:.1f} ({result.category})")
    assert 30 <= result.authenticity_score <= 60, (
        f"Expected 30-60, got {result.authenticity_score}"
    )
    return result


def test_deep_focus_bonus():
    """Deep focus in Code/IDE should score higher than scattered work."""
    scorer = AuthenticityScorer()

    # Deep focus: mostly Code/IDE
    focused = _make_features(
        avg_typing_speed=140,
        typing_rhythm_variance=55,
        pause_ratio=0.10,
        mouse_velocity_mean=400,
        mouse_velocity_std=200,
        mouse_direction_change_freq=15,
        total_keystrokes=6000,
        total_mouse_events=3500,
        total_active_seconds=25200,
        active_window_categories=[
            {"category": "Code/IDE", "seconds": 18000},
            {"category": "Terminal/CLI", "seconds": 4000},
            {"category": "Browser", "seconds": 3000},
        ],
    )

    # Scattered: same total time but split across many categories
    scattered = _make_features(
        avg_typing_speed=140,
        typing_rhythm_variance=55,
        pause_ratio=0.10,
        mouse_velocity_mean=400,
        mouse_velocity_std=200,
        mouse_direction_change_freq=15,
        total_keystrokes=6000,
        total_mouse_events=3500,
        total_active_seconds=25200,
        active_window_categories=[
            {"category": "Code/IDE", "seconds": 5000},
            {"category": "Browser", "seconds": 5000},
            {"category": "Communication", "seconds": 5000},
            {"category": "Word/Office", "seconds": 5000},
            {"category": "Email", "seconds": 3000},
            {"category": "Entertainment", "seconds": 2000},
        ],
    )

    focused_result = scorer.score(focused)
    scattered_result = scorer.score(scattered)
    print(f"  Deep focus: {focused_result.authenticity_score:.1f} vs Scattered: {scattered_result.authenticity_score:.1f}")
    assert focused_result.authenticity_score > scattered_result.authenticity_score, (
        f"Expected focused ({focused_result.authenticity_score}) > scattered ({scattered_result.authenticity_score})"
    )
    return focused_result, scattered_result


def test_score_stability():
    """Small changes in features should NOT cause large score jumps."""
    scorer = AuthenticityScorer()
    base_features = _make_features()
    base_result = scorer.score(base_features)

    # Slightly modify typing speed
    modified = _make_features(avg_typing_speed=155)
    modified_result = scorer.score(modified)

    diff = abs(base_result.authenticity_score - modified_result.authenticity_score)
    print(f"  Score stability: base={base_result.authenticity_score:.1f}, "
          f"modified={modified_result.authenticity_score:.1f}, diff={diff:.2f}")
    assert diff < 5.0, (
        f"Small feature change caused {diff:.2f} point jump — too unstable!"
    )
    return base_result, modified_result


def main():
    """Run all scoring accuracy tests."""
    print("\n" + "=" * 60)
    print("  AuthenticityScorer Calibration Tests")
    print("=" * 60 + "\n")

    tests = [
        ("Genuine Productive Worker", test_genuine_productive_worker),
        ("Automation Detection", test_automation_detected),
        ("Distracted User", test_distracted_user),
        ("Moderate Productivity", test_moderate_productivity),
        ("Mostly Idle", test_mostly_idle),
        ("No Data (Neutral)", test_no_data),
        ("Deep Focus Bonus", test_deep_focus_bonus),
        ("Score Stability", test_score_stability),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] {name}\n")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name} — {e}\n")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {name} — {e}\n")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
