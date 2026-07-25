"""
Pydantic schemas for request/response validation.

This module defines all the data models used for API request validation
and response serialization in the Fake Productivity Detector backend.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class ProductivityCategoryEnum(str, Enum):
    """Enumeration of productivity categories."""
    
    HIGHLY_PRODUCTIVE = "Highly Productive"
    MODERATELY_PRODUCTIVE = "Moderately Productive"
    FAKE_PRODUCTIVITY = "Fake Productivity"


# ==================== Input Schemas ====================

class ActivityDataInput(BaseModel):
    """
    Schema for activity data input (manual analysis).
    
    Attributes:
        task_hours: Hours spent on productive tasks (0-24)
        idle_hours: Hours spent idle (0-24)
        social_media_usage: Hours on social media (0-24)
        break_frequency: Number of breaks taken (0-50)
        tasks_completed: Number of tasks completed (0-100)
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_hours": 6.5,
                "idle_hours": 1.5,
                "social_media_usage": 2.0,
                "break_frequency": 5,
                "tasks_completed": 8
            }
        }
    )
    
    task_hours: float = Field(
        ...,
        ge=0,
        le=24,
        description="Hours spent on productive tasks"
    )
    idle_hours: float = Field(
        ...,
        ge=0,
        le=24,
        description="Hours spent idle"
    )
    social_media_usage: float = Field(
        ...,
        ge=0,
        le=24,
        description="Hours spent on social media"
    )
    break_frequency: int = Field(
        ...,
        ge=0,
        le=50,
        description="Number of breaks taken"
    )
    tasks_completed: int = Field(
        ...,
        ge=0,
        le=100,
        description="Number of tasks completed"
    )
    
    @field_validator('task_hours', 'idle_hours', 'social_media_usage')
    @classmethod
    def validate_hours(cls, v: float) -> float:
        """Ensure hours are rounded to 2 decimal places."""
        return round(v, 2)


class AnalysisRequest(BaseModel):
    """
    Schema for complete analysis request.
    
    Includes user information and activity data.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user@example.com",
                "user_name": "John Doe",
                "activity_data": {
                    "task_hours": 6.5,
                    "idle_hours": 1.5,
                    "social_media_usage": 2.0,
                    "break_frequency": 5,
                    "tasks_completed": 8
                }
            }
        }
    )
    
    user_id: str = Field(..., min_length=1, description="User identifier")
    user_name: str = Field(..., min_length=1, description="User display name")
    activity_data: ActivityDataInput


class CSVUploadRequest(BaseModel):
    """
    Schema for CSV batch upload metadata.
    """
    
    user_id: str = Field(..., min_length=1, description="User identifier")
    user_name: str = Field(..., min_length=1, description="User display name")


class MLPredictionRequest(BaseModel):
    """
    Schema for ML model prediction request.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_hours": 7.0,
                "idle_hours": 1.0,
                "social_media_usage": 1.5,
                "break_frequency": 4,
                "tasks_completed": 10
            }
        }
    )
    
    task_hours: float = Field(..., ge=0, le=24)
    idle_hours: float = Field(..., ge=0, le=24)
    social_media_usage: float = Field(..., ge=0, le=24)
    break_frequency: int = Field(..., ge=0, le=50)
    tasks_completed: int = Field(..., ge=0, le=100)


# ==================== Output Schemas ====================

class ScoreBreakdown(BaseModel):
    """
    Breakdown of productivity score components.
    """
    
    productive: float = Field(..., description="Hours of productive work")
    idle: float = Field(..., description="Hours of idle time")
    social: float = Field(..., description="Hours of social media usage")
    breaks: float = Field(..., description="Break hours equivalent")


class AnalysisResult(BaseModel):
    """
    Schema for productivity analysis result.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = Field(None, description="Analysis record ID")
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    productivity_score: float = Field(..., ge=0, le=100, description="Calculated productivity score")
    category_rule_based: str = Field(..., description="Rule-based category classification")
    category_ml: Optional[str] = Field(None, description="ML model category classification")
    breakdown: ScoreBreakdown
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    created_at: str = Field(..., description="Analysis timestamp")
    
    # Input data echo
    task_hours: float
    idle_hours: float
    social_media_usage: float
    break_frequency: int
    tasks_completed: int


class BatchAnalysisResult(BaseModel):
    """
    Schema for batch CSV analysis result.
    """
    
    total_rows: int = Field(..., description="Total rows processed")
    successful: int = Field(..., description="Successfully processed rows")
    failed: int = Field(..., description="Failed rows")
    results: List[AnalysisResult] = Field(default_factory=list)
    summary: "BatchSummary"
    errors: List[str] = Field(default_factory=list, description="Error messages for failed rows")


class BatchSummary(BaseModel):
    """
    Summary statistics for batch analysis.
    """
    
    average_score: float = Field(..., ge=0, le=100)
    highest_score: float = Field(..., ge=0, le=100)
    lowest_score: float = Field(..., ge=0, le=100)
    category_distribution: Dict[str, int]


class HistoryResponse(BaseModel):
    """
    Schema for user history response.
    """
    
    user_id: str
    total_records: int
    history: List[Dict[str, Any]]


class AnalyticsSummary(BaseModel):
    """
    Schema for analytics summary response.
    """
    
    total_analyses: int
    average_score: float
    highest_score: float
    lowest_score: float
    category_distribution: Dict[str, int]
    trend: float = Field(..., description="Score trend (positive = improving)")
    recent_analyses: List[Dict[str, Any]]


class MLPredictionResponse(BaseModel):
    """
    Schema for ML prediction response.
    """
    
    predicted_category: str
    confidence: float = Field(..., ge=0, le=1)
    probabilities: Dict[str, float]
    model_used: str


class ModelInfoResponse(BaseModel):
    """
    Schema for ML model information.
    """
    
    model_type: str
    accuracy: float
    features: List[str]
    classes: List[str]
    trained_at: Optional[str]
    sample_count: Optional[int]


# ==================== Generic Schemas ====================

class SuccessResponse(BaseModel):
    """Generic success response."""
    
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    
    success: bool = False
    error: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: str
    database: str
    ml_model: str


# Forward reference update
BatchAnalysisResult.model_rebuild()
