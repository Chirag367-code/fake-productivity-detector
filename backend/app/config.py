"""
Configuration module for Fake Productivity Detector Backend.

This module handles all environment variables and application settings
using Pydantic for validation and type safety.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        app_name: Name of the application
        app_version: Current version
        debug: Debug mode flag
        supabase_url: Supabase project URL
        supabase_key: Supabase anonymous/public key
        supabase_service_key: Supabase service role key (for admin operations)
        jwt_secret: JWT secret for token verification
        cors_origins: Allowed CORS origins
        log_level: Logging level
    """
    
    # Application Settings
    app_name: str = Field(default="Fake Productivity Detector API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/production)")
    
    # Supabase Configuration
    supabase_url: str = Field(
        default="",
        description="Supabase project URL (set via SUPABASE_URL env var)"
    )
    supabase_key: str = Field(
        default="",
        description="Supabase anonymous key (set via SUPABASE_KEY env var)"
    )
    supabase_service_key: Optional[str] = Field(
        default=None,
        description="Supabase service role key (set via SUPABASE_SERVICE_KEY env var)"
    )
    supabase_jwt_secret: Optional[str] = Field(
        default=None,
        description="Supabase JWT secret for token verification"
    )
    
    # CORS Settings  (stored as a comma-separated string in .env)
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8080",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        import json
        raw = self.cors_origins_str
        # Try JSON array first, then fall back to comma-split
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return [o.strip() for o in raw.split(",") if o.strip()]
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # ML Model Paths (resolved relative to this file's directory)
    # Prefixed with ml_ to avoid Pydantic protected 'model_' namespace.
    ml_model_path: str = Field(default="", description="Path to trained ML model (auto-resolved if empty)")
    ml_scaler_path: str = Field(default="", description="Path to feature scaler (auto-resolved if empty)")
    
    
    class Config:
        # Load backend/.env relative to *this* file so the correct .env is
        # used regardless of the working directory the server is started from.
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Ignore extra variables (e.g. VITE_* from the frontend .env) so
        # Pydantic does not raise "Extra inputs are not permitted".
        extra = "ignore"
        # Allow 'model_path' style fields without Pydantic warning.
        protected_namespaces = ("settings_",)
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to ensure settings are only loaded once.
    
    Returns:
        Settings: Application settings instance
    """
    s = Settings()
    # Resolve ML model paths relative to this file's location if not set
    _app_dir = os.path.dirname(os.path.abspath(__file__))
    if not s.ml_model_path:
        s.ml_model_path = os.path.join(_app_dir, 'ml', 'models', 'random_forest_model.joblib')
    if not s.ml_scaler_path:
        s.ml_scaler_path = os.path.join(_app_dir, 'ml', 'scaler.pkl')
    return s


# Scoring Configuration
class ScoringConfig:
    """
    Configuration for productivity scoring algorithm.
    
    Weights for each factor in the scoring formula:
    score = (task_hours × TASK_WEIGHT) + (tasks_completed × TASKS_COMPLETED_WEIGHT)
            - (idle_hours × IDLE_WEIGHT) - (social_media × SOCIAL_MEDIA_WEIGHT)
            - (break_frequency × BREAK_WEIGHT)
    """
    
    TASK_WEIGHT: float = 8.0
    IDLE_WEIGHT: float = 6.0
    SOCIAL_MEDIA_WEIGHT: float = 7.0
    BREAK_WEIGHT: float = 2.0
    TASKS_COMPLETED_WEIGHT: float = 5.0
    
    MIN_SCORE: float = 0.0
    MAX_SCORE: float = 100.0
    
    # Category thresholds
    HIGHLY_PRODUCTIVE_MIN: float = 80.0
    MODERATELY_PRODUCTIVE_MIN: float = 50.0


# Category Labels
class ProductivityCategory:
    """Productivity category constants."""
    
    HIGHLY_PRODUCTIVE: str = "Highly Productive"
    MODERATELY_PRODUCTIVE: str = "Moderately Productive"
    FAKE_PRODUCTIVITY: str = "Fake Productivity"


# Database Table Names
class TableNames:
    """Supabase table names."""
    
    PRODUCTIVITY_ANALYSIS: str = "productivity_analysis"
    USERS: str = "users"
    KV_STORE: str = "kv_store_a0c5b0f2"


# Export settings instance
settings = get_settings()
