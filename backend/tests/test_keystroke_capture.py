"""
Test suite to verify that keystroke capture logic accurately filters out noise
and correctly calculates timings based on synthetic event sequences.
"""

import sys
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend package is accessible
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.agent.capture import KeystrokeCapture, event_queue, _init_db

class MockKey:
    def __init__(self, name="a"):
        self.name = name

@pytest.fixture(autouse=True)
def clean_queue():
    """Ensure the event queue is empty before each test."""
    while not event_queue.empty():
        event_queue.get_nowait()
    yield

def test_normal_typing():
    """Verify normal typing records correctly with dwell and flight times."""
    cap = KeystrokeCapture()
    key_a = MockKey("a")
    key_b = MockKey("b")

    # Type 'a'
    with patch('time.perf_counter', return_value=1.0), patch('time.time', return_value=100.0):
        cap._on_press(key_a)
    with patch('time.perf_counter', return_value=1.1):  # 100ms dwell
        cap._on_release(key_a)

    # Type 'b' 200ms later
    with patch('time.perf_counter', return_value=1.3), patch('time.time', return_value=100.3):
        cap._on_press(key_b)
    with patch('time.perf_counter', return_value=1.4):  # 100ms dwell
        cap._on_release(key_b)

    assert event_queue.qsize() == 2
    
    # Event 1: 'a'
    e1 = event_queue.get()
    assert e1[0] == 'key'
    assert e1[3] == 100.0  # dwell_ms
    assert e1[4] == 0.0    # flight_ms (first key)
    assert e1[5] == 0      # is_modifier

    # Event 2: 'b'
    e2 = event_queue.get()
    assert e2[0] == 'key'
    assert e2[2] == 300.0  # inter_key_ms (press 1.0 -> press 1.3)
    assert e2[3] == 100.0  # dwell_ms
    assert e2[4] == 200.0  # flight_ms (release 1.1 -> press 1.3)
    assert e2[5] == 0      # is_modifier

def test_auto_repeat_filtering():
    """Verify holding down a key (auto-repeat) is filtered out."""
    cap = KeystrokeCapture()
    key = MockKey("a")

    with patch('time.perf_counter', return_value=1.0), patch('time.time', return_value=100.0):
        cap._on_press(key)
    
    # Auto-repeat fires multiple presses without release
    with patch('time.perf_counter', return_value=1.03), patch('time.time', return_value=100.03):
        cap._on_press(key)
        
    with patch('time.perf_counter', return_value=1.06), patch('time.time', return_value=100.06):
        cap._on_press(key)

    with patch('time.perf_counter', return_value=1.5): # 500ms total dwell
        cap._on_release(key)

    assert event_queue.qsize() == 1
    e = event_queue.get()
    assert e[3] == 500.0  # Dwell should be from first press to release

def test_modifier_detection():
    """Verify modifier keys are flagged correctly."""
    cap = KeystrokeCapture()
    
    shift_key = MockKey("shift")
    ctrl_key = MockKey("ctrl_l")
    char_key = MockKey("a")

    with patch('time.perf_counter', return_value=1.0): cap._on_press(shift_key)
    with patch('time.perf_counter', return_value=1.1): cap._on_press(char_key)
    with patch('time.perf_counter', return_value=1.2): cap._on_release(char_key)
    with patch('time.perf_counter', return_value=1.3): cap._on_release(shift_key)

    assert event_queue.qsize() == 2
    
    e1 = event_queue.get() # char_key release
    assert e1[5] == 0 # is_modifier = False
    
    e2 = event_queue.get() # shift_key release
    assert e2[5] == 1 # is_modifier = True
