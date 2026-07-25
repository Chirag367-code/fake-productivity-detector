"""
Main FastAPI Application Entry Point.

Fake Productivity Detector Backend API
Academic Project - Data Science

This module initializes the FastAPI application and mounts all API routers.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure absolute package imports work whether running as a package or script.
import sys
if __package__ is None:
    # Running as a script: add parent `backend` directory to sys.path so
    # `import app.*` works with absolute imports.
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

from app.config import settings
from app.routes import analysis, csv_upload, history, reports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("="*50)
    logger.info("Starting Fake Productivity Detector API")
    logger.info("="*50)
    logger.info(f"Environment: {settings.log_level}")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    logger.info(f"Debug Mode: {settings.debug}")
    
    # Check for ML model availability; auto-train if missing
    model_path = os.path.join(os.path.dirname(__file__), 'ml', 'models', 'random_forest_model.joblib')
    if os.path.exists(model_path):
        logger.info(f"ML Model found: {model_path}")
        try:
            from app.services.ml_model import MLClassifier
            clf = MLClassifier(model_type='random_forest', model_path=model_path)
            info = clf.get_model_info()
            logger.info(f"Model Info: Type={info['model_type']}, Trained={info['is_trained']}, Accuracy={info['accuracy']}")
        except Exception as e:
            logger.warning(f"Could not load model info: {e}")
    else:
        logger.warning("No pre-trained ML model found. Auto-training with synthetic data...")
        try:
            from app.ml.train_model import generate_synthetic_data, train_and_evaluate
            model_dir = os.path.join(os.path.dirname(__file__), 'ml', 'models')
            data = generate_synthetic_data(n_samples=1000)
            results = train_and_evaluate(data, model_type='random_forest', model_dir=model_dir)
            logger.info(f"Auto-trained model saved. Accuracy: {results['test_accuracy']:.4f}")
        except Exception as e:
            logger.error(f"Auto-training failed (non-critical): {e}")
            logger.info("The API will still work — ML predictions will use an untrained model.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fake Productivity Detector API")


# Create FastAPI application
app = FastAPI(
    title="Fake Productivity Detector API",
    description="""
    ## Academic Project: Fake Productivity Detector Using Data Science
    
    This API provides endpoints for analyzing user productivity metrics and
    detecting fake productivity patterns using rule-based scoring and
    machine learning classification.
    
    ### Features
    
    - **Single Analysis**: Analyze individual productivity data
    - **Batch CSV Upload**: Process multiple entries via CSV file
    - **History Management**: View and manage analysis history
    - **Reports**: Generate comprehensive productivity reports
    
    ### Productivity Formula
    
    ```
    Raw Score = (Task Hours × 8) + (Tasks Completed × 5) 
                - (Idle Hours × 6) - (Social Media Hours × 7) 
                - (Break Frequency × 2)
    
    Final Score = max(0, min(100, Raw Score))
    ```
    
    ### Classification
    
    - **Highly Productive**: Score 80-100
    - **Moderately Productive**: Score 50-79
    - **Fake Productivity**: Score 0-49
    
    ### Tech Stack
    
    - FastAPI (Python 3.11)
    - Supabase (PostgreSQL)
    - Scikit-learn (ML Classification)
    - Pandas & NumPy (Data Processing)
    """,
    version="1.0.0",
    contact={
        "name": "Academic Project",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    description="Welcome message and API status"
)
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": "Fake Productivity Detector API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check API health status"
)
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(
    "/info",
    tags=["Health"],
    summary="API information",
    description="Get detailed API information"
)
async def api_info():
    """Get detailed API information."""
    return {
        "name": "Fake Productivity Detector API",
        "version": "1.0.0",
        "description": "Academic project for detecting fake productivity using data science",
        "features": [
            "Rule-based productivity scoring",
            "ML-based classification",
            "CSV batch processing",
            "History management",
            "Analytics reports"
        ],
        "scoring": {
            "formula": "score = (task_hours * 8) + (tasks_completed * 5) - (idle_hours * 6) - (social_media_hours * 7) - (break_frequency * 2)",
            "categories": {
                "highly_productive": "80-100",
                "moderately_productive": "50-79",
                "fake_productivity": "0-49"
            }
        },
        "endpoints": {
            "analysis": "/api/v1/analyze",
            "csv_upload": "/api/v1/upload-csv",
            "history": "/api/v1/history",
            "reports": "/api/v1/reports"
        }
    }


# Mount API routers with /api/v1 prefix
app.include_router(
    analysis.router,
    prefix="/api/v1"
)

app.include_router(
    csv_upload.router,
    prefix="/api/v1"
)

app.include_router(
    history.router,
    prefix="/api/v1"
)

app.include_router(
    reports.router,
    prefix="/api/v1"
)


# Development server entry point
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",          # import string required for --reload
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
