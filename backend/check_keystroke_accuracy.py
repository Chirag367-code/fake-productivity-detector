"""
Script to manually verify keystroke accuracy and test the hardware injection flag.
"""

import time
import sys
import os
import threading
from pathlib import Path

# Add backend to path so we can import the feature extractor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.agent.capture import _init_db, _get_connection, event_queue

def test_pyautogui_injection(target_sentence):
    """Fires simulated keys using pyautogui to test if the injected flag works."""
    try:
        import pyautogui
    except ImportError:
        print("\n[!] pyautogui is not installed. Skipping injection test.")
        print("    Run: pip install pyautogui")
        return
        
    print(f"\n> Automatically typing in 3 seconds... DO NOT TOUCH THE KEYBOARD!")
    time.sleep(3)
    
    start = time.perf_counter()
    pyautogui.write(target_sentence, interval=0.05)  # 50ms interval macro
    end = time.perf_counter()
    
    print("\n[✓] PyAutoGUI injection complete.")
    
def get_latest_injected_ratio(conn):
    """Check the SQLite DB for the injected ratio of the last batch."""
    # Look at the last minute of events
    cutoff = time.time() - 60
    rows = conn.execute(
        "SELECT is_injected FROM keystroke_events WHERE timestamp >= ?", 
        (cutoff,)
    ).fetchall()
    
    if not rows:
        return 0.0
        
    injected_count = sum(1 for r in rows if r[0] == 1)
    return injected_count / len(rows)

def main():
    _init_db()
    conn = _get_connection()
    
    print("========================================")
    print(" Typing Calibration & Injection Script")
    print("========================================")
    
    target_sentence = "The quick brown fox jumps over the lazy dog."
    
    print("\n--- TEST 1: MANUAL TYPING ---")
    print("Type the following sentence naturally:")
    print(f"> {target_sentence}\n")
    
    input("Press Enter when ready to start typing...")
    
    print("\nType here: ", end="", flush=True)
    start = time.perf_counter()
    typed = input()
    end = time.perf_counter()
    
    if not typed:
        print("No input detected.")
        return
        
    duration = end - start
    chars = len(typed)
    
    wpm = (chars / 5.0) / (duration / 60.0)
    avg_inter_key_ms = (duration * 1000.0) / chars
    
    time.sleep(1.5) # Wait for background writer queue
    manual_injected_ratio = get_latest_injected_ratio(conn)
    
    print("\nManual Results:")
    print(f"  Measured WPM:             {wpm:.1f} words/min")
    print(f"  Avg Inter-key interval:   {avg_inter_key_ms:.1f} ms")
    print(f"  Injected Ratio (DB):      {manual_injected_ratio * 100:.1f}%")
    
    print("\n--- TEST 2: MACRO INJECTION ---")
    print("This will simulate a macro typing the exact same sentence.")
    input("Press Enter to begin Test 2 (make sure you don't type while it runs)...")
    
    # We need the background listener running to catch the events
    from app.agent.capture import KeystrokeCapture
    cap = KeystrokeCapture()
    cap.start()
    
    test_pyautogui_injection(target_sentence)
    
    time.sleep(2) # Wait for background writer queue
    cap.stop()
    
    bot_injected_ratio = get_latest_injected_ratio(conn)
    
    print("\nMacro Results:")
    print(f"  Injected Ratio (DB):      {bot_injected_ratio * 100:.1f}%")
    
    print("\n--- CONCLUSION ---")
    if bot_injected_ratio > 0.5 and manual_injected_ratio < 0.1:
        print("[✓] PASS: The win32_event_filter correctly distinguished you from the macro!")
    else:
        print("[X] FAIL: The injection flag didn't separate human from bot effectively.")

if __name__ == "__main__":
    main()
