"""
Analysis API routes.

This module provides endpoints for single productivity analysis.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status

from ..models.schemas import (
    AnalysisRequest,
    AnalysisResult,
    ScoreBreakdown,
    MLPredictionRequest,
    MLPredictionResponse,
    ErrorResponse
)
from ..models.database import ProductivityAnalysisDB, get_db
from ..services.scoring import ProductivityScorer, get_scorer
from ..services.ml_model import MLClassifier, get_classifier
from ..services.suggestions import SuggestionEngine, get_suggestion_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analysis"])


async def verify_auth(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify authorization header and extract user info.
    
    Args:
        authorization: Bearer token from header
        
    Returns:
        User ID extracted from token
        
    Raises:
        HTTPException: If authorization is invalid
    """
    # For now, allow requests with any token (including anon key)
    # In production, verify JWT token properly
    if not authorization:
        logger.warning("No authorization header provided")
        # For development, allow unauthenticated requests
        return "anonymous"
    
    # Extract bearer token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        # In production, decode and verify JWT here
        # For now, just return a placeholder
        return "authenticated_user"
    
    return "anonymous"


@router.post(
    "",
    response_model=AnalysisResult,
    summary="Analyze productivity data",
    description="Submit activity data for productivity analysis including rule-based and ML classification."
)
async def analyze_productivity(
    request: AnalysisRequest,
    db: ProductivityAnalysisDB = Depends(get_db),
    scorer: ProductivityScorer = Depends(get_scorer),
    classifier: MLClassifier = Depends(get_classifier),
    suggestion_engine: SuggestionEngine = Depends(get_suggestion_engine),
    user_id: str = Depends(verify_auth)
) -> AnalysisResult:
    """
    Analyze single productivity data entry.
    
    Performs:
    1. Rule-based score calculation
    2. ML classification (if model available)
    3. Suggestion generation
    4. Database storage
    
    Args:
        request: Analysis request with user and activity data
        db: Database dependency
        scorer: Scoring service dependency
        classifier: ML classifier dependency
        suggestion_engine: Suggestion engine dependency
        user_id: Authenticated user ID
        
    Returns:
        AnalysisResult with scores, categories, and suggestions
    """
    try:
        activity = request.activity_data
        
        # Calculate rule-based score
        scoring_result = scorer.calculate_score(
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_hours=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed
        )
        
        # Get ML prediction if model is trained
        ml_category = None
        if classifier.is_trained:
            try:
                ml_result = classifier.predict_single(
                    task_hours=activity.task_hours,
                    idle_hours=activity.idle_hours,
                    social_media_usage=activity.social_media_usage,
                    break_frequency=activity.break_frequency,
                    tasks_completed=activity.tasks_completed
                )
                ml_category = ml_result['predicted_category']
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        # Generate suggestions
        suggestions = suggestion_engine.generate_suggestions(
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_usage=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed,
            score=scoring_result.score
        )
        
        # Create timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Save to database
        record = await db.create_analysis(
            user_id=request.user_id,
            user_name=request.user_name,
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_usage=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed,
            productivity_score=scoring_result.score,
            category_rule_based=scoring_result.category,
            category_ml=ml_category,
            suggestions=suggestions
        )
        
        logger.info(
            f"Analysis complete for user {request.user_id}: "
            f"score={scoring_result.score}, category={scoring_result.category}"
        )
        
        return AnalysisResult(
            id=record.get('id'),
            user_id=request.user_id,
            user_name=request.user_name,
            productivity_score=scoring_result.score,
            category_rule_based=scoring_result.category,
            category_ml=ml_category,
            breakdown=ScoreBreakdown(
                productive=scoring_result.breakdown['productive'],
                idle=scoring_result.breakdown['idle'],
                social=scoring_result.breakdown['social'],
                breaks=scoring_result.breakdown['breaks']
            ),
            suggestions=suggestions,
            created_at=timestamp,
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_usage=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed
        )
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post(
    "/quick",
    response_model=AnalysisResult,
    summary="Quick analysis without storage",
    description="Perform analysis without saving to database."
)
async def quick_analyze(
    activity: MLPredictionRequest,
    scorer: ProductivityScorer = Depends(get_scorer),
    classifier: MLClassifier = Depends(get_classifier),
    suggestion_engine: SuggestionEngine = Depends(get_suggestion_engine)
) -> AnalysisResult:
    """
    Quick productivity analysis without database storage.
    
    Useful for preview/testing purposes.
    
    Args:
        activity: Activity data
        scorer: Scoring service
        classifier: ML classifier
        suggestion_engine: Suggestion engine
        
    Returns:
        AnalysisResult (not stored in database)
    """
    try:
        # Calculate score
        scoring_result = scorer.calculate_score(
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_hours=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed
        )
        
        # ML prediction
        ml_category = None
        if classifier.is_trained:
            try:
                ml_result = classifier.predict_single(
                    task_hours=activity.task_hours,
                    idle_hours=activity.idle_hours,
                    social_media_usage=activity.social_media_usage,
                    break_frequency=activity.break_frequency,
                    tasks_completed=activity.tasks_completed
                )
                ml_category = ml_result['predicted_category']
            except Exception:
                pass
        
        # Generate suggestions
        suggestions = suggestion_engine.generate_suggestions(
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_usage=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed,
            score=scoring_result.score
        )
        
        return AnalysisResult(
            id=None,
            user_id="anonymous",
            user_name="Anonymous User",
            productivity_score=scoring_result.score,
            category_rule_based=scoring_result.category,
            category_ml=ml_category,
            breakdown=ScoreBreakdown(
                productive=scoring_result.breakdown['productive'],
                idle=scoring_result.breakdown['idle'],
                social=scoring_result.breakdown['social'],
                breaks=scoring_result.breakdown['breaks']
            ),
            suggestions=suggestions,
            created_at=datetime.utcnow().isoformat(),
            task_hours=activity.task_hours,
            idle_hours=activity.idle_hours,
            social_media_usage=activity.social_media_usage,
            break_frequency=activity.break_frequency,
            tasks_completed=activity.tasks_completed
        )
        
    except Exception as e:
        logger.error(f"Quick analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/explain",
    summary="Explain scoring",
    description="Get detailed explanation of how scoring works."
)
async def explain_scoring(
    task_hours: float = 6.0,
    idle_hours: float = 1.5,
    social_media_usage: float = 2.0,
    break_frequency: int = 5,
    tasks_completed: int = 8,
    scorer: ProductivityScorer = Depends(get_scorer)
) -> dict:
    """
    Get detailed explanation of score calculation.
    
    Args:
        task_hours: Hours on productive tasks
        idle_hours: Idle hours
        social_media_usage: Social media hours
        break_frequency: Number of breaks
        tasks_completed: Tasks completed
        scorer: Scoring service
        
    Returns:
        Dict with explanation text
    """
    explanation = scorer.explain_score(
        task_hours=task_hours,
        idle_hours=idle_hours,
        social_media_hours=social_media_usage,
        break_frequency=break_frequency,
        tasks_completed=tasks_completed
    )
    
    return {
        "explanation": explanation,
        "thresholds": scorer.get_category_thresholds()
    }
