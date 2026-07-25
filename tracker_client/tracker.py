import time
import sqlite3
import sys
import logging
import requests
import pygetwindow as gw
from pynput import mouse, keyboard

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = 'productivity.db'
API_URL = 'http://localhost:8000/api/v1/analyze/quick'

# Thresholds
IDLE_THRESHOLD_SECONDS = 120 # 2 minutes of no input = idle
BREAK_THRESHOLD_SECONDS = 600 # 10 minutes of idle = break

class ProductivityTracker:
    def __init__(self):
        self.last_activity_time = time.time()
        self.is_idle = False
        self.current_idle_start = 0
        
        # Daily aggregations
        self.task_seconds = 0
        self.idle_seconds = 0
        self.social_media_seconds = 0
        self.break_count = 0
        self.tasks_completed = 0
        
        self.social_media_keywords = ['facebook', 'twitter', 'instagram', 'youtube', 'tiktok', 'reddit', 'whatsapp']
        
        self.setup_db()
        
    def setup_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS activity_logs 
                     (timestamp TEXT, window_title TEXT, event_type TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS daily_summary
                     (date TEXT, task_hours REAL, idle_hours REAL, social_media_hours REAL, break_frequency INTEGER, tasks_completed INTEGER)''')
        conn.commit()
        conn.close()

    def on_activity(self, *args, **kwargs):
        now = time.time()
        
        if self.is_idle:
            idle_duration = now - self.current_idle_start
            self.idle_seconds += idle_duration
            if idle_duration > BREAK_THRESHOLD_SECONDS:
                self.break_count += 1
                logging.info(f"Break detected! Duration: {idle_duration:.1f}s")
            self.is_idle = False
            
        self.last_activity_time = now

    def get_active_window_title(self):
        try:
            active_window = gw.getActiveWindow()
            return active_window.title.lower() if active_window else ""
        except Exception:
            return ""

    def monitor_activity(self):
        logging.info("Starting background monitor...")
        
        # Start input hooks
        mouse_listener = mouse.Listener(on_move=self.on_activity, on_click=self.on_activity, on_scroll=self.on_activity)
        keyboard_listener = keyboard.Listener(on_press=self.on_activity)
        
        mouse_listener.start()
        keyboard_listener.start()
        
        try:
            while True:
                time.sleep(1)
                now = time.time()
                
                # Check for idle
                if now - self.last_activity_time > IDLE_THRESHOLD_SECONDS and not self.is_idle:
                    self.is_idle = True
                    self.current_idle_start = self.last_activity_time
                    logging.info("User is now idle.")
                
                # If not idle, allocate time to task or social media
                if not self.is_idle:
                    window_title = self.get_active_window_title()
                    is_social = any(kw in window_title for kw in self.social_media_keywords)
                    
                    if is_social:
                        self.social_media_seconds += 1
                    else:
                        self.task_seconds += 1

                # Every 10 seconds, print a quick status for debug mode
                if int(now) % 10 == 0:
                    logging.info(f"Task: {self.task_seconds}s | Social: {self.social_media_seconds}s | Idle: {self.idle_seconds}s | Breaks: {self.break_count}")
                    
                # Every 1 minute, send data to API for demonstration purposes
                # In real life, this might be hourly or daily.
                if int(now) % 60 == 0 and self.task_seconds > 0:
                    self.send_to_backend()
                    
        except KeyboardInterrupt:
            logging.info("Stopping tracker...")
            mouse_listener.stop()
            keyboard_listener.stop()
            sys.exit(0)

    def send_to_backend(self):
        # Convert seconds to hours for the API
        payload = {
            "task_hours": round(self.task_seconds / 3600.0, 4),
            "idle_hours": round(self.idle_seconds / 3600.0, 4),
            "social_media_usage": round(self.social_media_seconds / 3600.0, 4),
            "break_frequency": self.break_count,
            "tasks_completed": self.tasks_completed
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                logging.info(f"✅ Data sent successfully! Backend categorized you as: {data.get('category_rule_based')}")
            else:
                logging.error(f"❌ Failed to send data: {response.status_code} {response.text}")
        except Exception as e:
            logging.error(f"❌ Error connecting to backend: {e}")

if __name__ == "__main__":
    print("========================================")
    print(" FAKE PRODUCTIVITY DETECTOR - Phase 1 ")
    print(" Silent Background Tracker (Debug Mode) ")
    print("========================================")
    print("Press Ctrl+C to stop.")
    
    tracker = ProductivityTracker()
    tracker.monitor_activity()
