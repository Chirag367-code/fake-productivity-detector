# Fake Productivity Detector - Phase 1 Tracker

This is the silent background tracker script (Phase 1) described in the project report. It monitors real-time user behavior using `pynput`, detects active windows using `pygetwindow`, and stores data in a local `sqlite3` database before sending it to the FastAPI backend.

## Installation

1. Navigate to this directory in a terminal.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Debug Mode (Visible)
Run this command to see the tracker actively logging your stats in the terminal:
```bash
python tracker.py
```

### Silent Mode (Background)
On Windows, you can run the script completely silently using `pythonw`:
```bash
pythonw tracker.py
```
*(To stop it in silent mode, you will need to open Task Manager and end the `pythonw.exe` process).*
