"""
History API routes.

This module provides endpoints for user productivity history management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.schemas import HistoryResponse, SuccessResponse, ErrorResponse
from ..models.database import ProductivityAnalysisDB, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "/{user_id}",
    response_model=HistoryResponse,
    summary="Get user history",
    description="Retrieve productivity analysis history for a specific user."
)
async def get_user_history(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> HistoryResponse:
    """
    Get productivity history for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of records
        offset: Records to skip (for pagination)
        db: Database dependency
        
    Returns:
        HistoryResponse with user's analysis history
    """
    try:
        history = await db.get_user_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Retrieved {len(history)} history records for user {user_id}")
        
        return HistoryResponse(
            user_id=user_id,
            total_records=len(history),
            history=history
        )
        
    except Exception as e:
        logger.error(f"Error retrieving history for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.delete(
    "/{user_id}",
    response_model=SuccessResponse,
    summary="Delete user history",
    description="Delete all productivity history for a specific user."
)
async def delete_user_history(
    user_id: str,
    db: ProductivityAnalysisDB = Depends(get_db)
) -> SuccessResponse:
    """
    Delete all productivity history for a user.
    
    Args:
        user_id: User identifier
        db: Database dependency
        
    Returns:
        Success response with deletion count
    """
    try:
        deleted_count = await db.delete_user_history(user_id)
        
        logger.info(f"Deleted {deleted_count} records for user {user_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Deleted {deleted_count} analysis records"
        )
        
    except Exception as e:
        logger.error(f"Error deleting history for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete history: {str(e)}"
        )


@router.get(
    "/{user_id}/recent",
    summary="Get recent analyses",
    description="Get the most recent productivity analyses for a user."
)
async def get_recent_history(
    user_id: str,
    count: int = Query(default=5, ge=1, le=20, description="Number of recent records"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Get most recent productivity analyses.
    
    Args:
        user_id: User identifier
        count: Number of recent records to fetch
        db: Database dependency
        
    Returns:
        Dict with recent analyses
    """
    try:
        history = await db.get_user_history(user_id=user_id, limit=count)
        
        return {
            "user_id": user_id,
            "count": len(history),
            "recent": history
        }
        
    except Exception as e:
        logger.error(f"Error retrieving recent history for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{user_id}/stats",
    summary="Get history statistics",
    description="Get statistical summary of user's productivity history."
)
async def get_history_stats(
    user_id: str,
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Get statistical summary of user's history.
    
    Args:
        user_id: User identifier
        db: Database dependency
        
    Returns:
        Dict with statistics
    """
    try:
        history = await db.get_user_history(user_id=user_id, limit=1000)
        
        if not history:
            return {
                "user_id": user_id,
                "total_records": 0,
                "statistics": None
            }
        
        # Extract scores
        scores = []
        for record in history:
            score = record.get('productivity_score') or record.get('score', 0)
            scores.append(score)
        
        # Calculate statistics
        import statistics as st
        
        stats = {
            "count": len(scores),
            "mean": round(st.mean(scores), 2) if scores else 0,
            "median": round(st.median(scores), 2) if scores else 0,
            "stdev": round(st.stdev(scores), 2) if len(scores) > 1 else 0,
            "min": round(min(scores), 2) if scores else 0,
            "max": round(max(scores), 2) if scores else 0
        }
        
        # Category breakdown
        categories = [
            record.get('category_rule_based') or record.get('category', 'Unknown')
            for record in history
        ]
        
        category_counts = {}
        for cat in set(categories):
            category_counts[cat] = categories.count(cat)
        
        return {
            "user_id": user_id,
            "total_records": len(history),
            "statistics": stats,
            "category_breakdown": category_counts
        }
        
    except Exception as e:
        logger.error(f"Error calculating stats for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{user_id}/trend",
    summary="Get productivity trend",
    description="Get productivity score trend over time."
)
async def get_productivity_trend(
    user_id: str,
    period: str = Query(default="week", description="Trend period: day, week, month"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Get productivity trend data for charting.
    
    Args:
        user_id: User identifier
        period: Time period for trend
        db: Database dependency
        
    Returns:
        Dict with trend data points
    """
    from datetime import datetime, timedelta
    
    try:
        history = await db.get_user_history(user_id=user_id, limit=100)
        
        if not history:
            return {
                "user_id": user_id,
                "period": period,
                "trend": [],
                "direction": "neutral"
            }
        
        # Extract date-score pairs
        trend_data = []
        for record in history:
            timestamp = record.get('created_at') or record.get('timestamp', '')
            score = record.get('productivity_score') or record.get('score', 0)
            
            if timestamp:
                trend_data.append({
                    "date": timestamp[:10] if isinstance(timestamp, str) else str(timestamp)[:10],
                    "score": round(score, 2)
                })
        
        # Reverse to chronological order
        trend_data.reverse()
        
        # Take last N based on period
        if period == "day":
            trend_data = trend_data[-7:]
        elif period == "week":
            trend_data = trend_data[-28:]
        else:  # month
            trend_data = trend_data[-90:]
        
        # Calculate trend direction
        if len(trend_data) >= 2:
            first_half = trend_data[:len(trend_data)//2]
            second_half = trend_data[len(trend_data)//2:]
            
            first_avg = sum(d['score'] for d in first_half) / len(first_half) if first_half else 0
            second_avg = sum(d['score'] for d in second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg + 5:
                direction = "improving"
            elif second_avg < first_avg - 5:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"
        
        return {
            "user_id": user_id,
            "period": period,
            "trend": trend_data,
            "direction": direction
        }
        
    except Exception as e:
        logger.error(f"Error calculating trend for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
