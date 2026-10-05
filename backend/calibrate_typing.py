"""
Manual calibration script to verify keystroke timing accuracy on this machine.
Run this script, type a known sentence, and compare the output WPM and 
average inter-key interval with what you expect.
"""

import time
import sys

def main():
    print("========================================")
    print(" Typing Calibration Script")
    print("========================================")
    print("Type the following sentence as naturally as possible:")
    
    target_sentence = "The quick brown fox jumps over the lazy dog."
    print(f"\n> {target_sentence}\n")
    
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
    cpm = chars / (duration / 60.0)
    avg_inter_key_ms = (duration * 1000.0) / chars
    
    print("\nResults:")
    print("-" * 30)
    print(f"Time taken:               {duration:.2f} seconds")
    print(f"Characters typed:         {chars}")
    print(f"Measured WPM:             {wpm:.1f} words/min")
    print(f"Measured CPM:             {cpm:.1f} chars/min")
    print(f"Avg Inter-key interval:   {avg_inter_key_ms:.1f} ms")
    print("-" * 30)
    
    if abs(chars - len(target_sentence)) > 5:
        print("\nNote: You typed significantly more or fewer characters than the target.")

    print("\nIf the WPM shown here roughly matches your expected typing speed,")
    print("but the Agent Monitor shows something wildly different (like 400 WPM),")
    print("then the agent's keystroke capture was previously bottlenecked by")
    print("auto-repeat bugs or blocking SQLite calls. The latest fixes should")
    print("bring the Agent Monitor into alignment with these calibrated numbers.")

if __name__ == "__main__":
    main()
