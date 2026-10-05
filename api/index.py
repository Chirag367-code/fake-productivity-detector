import sys
import os

# Add the 'backend' folder to the Python path so absolute imports like 'from app.config import settings' work on Vercel
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

# Import the FastAPI app instance from backend/app/main.py
from app.main import app
