"""
Reports API routes.

This module provides endpoints for generating productivity reports and analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from ..models.schemas import ErrorResponse
from ..models.database import ProductivityAnalysisDB, get_db
from ..services.suggestions import SuggestionEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/{user_id}",
    summary="Get user analytics report",
    description="Generate comprehensive analytics report for a user."
)
async def get_user_report(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Days to analyze"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Generate comprehensive user analytics report.
    
    Args:
        user_id: User identifier
        days: Number of days to include in report
        db: Database dependency
        
    Returns:
        Dict with comprehensive analytics
    """
    try:
        # Get analytics summary from database
        analytics = await db.get_analytics_summary(user_id)
        
        # Get recent history for additional analysis
        history = await db.get_user_history(user_id=user_id, limit=days)
        
        if not history:
            return {
                "user_id": user_id,
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_analyses": 0,
                    "message": "No productivity data found for this user"
                }
            }
        
        # Extract scores and categories
        scores = []
        categories = []
        daily_metrics = {}
        
        for record in history:
            score = record.get('productivity_score') or record.get('score', 0)
            scores.append(score)
            
            category = record.get('category_rule_based') or record.get('category', 'Unknown')
            categories.append(category)
            
            # Aggregate by date
            timestamp = record.get('created_at') or record.get('timestamp', '')
            if timestamp:
                date_key = timestamp[:10] if isinstance(timestamp, str) else str(timestamp)[:10]
                if date_key not in daily_metrics:
                    daily_metrics[date_key] = {'scores': [], 'count': 0}
                daily_metrics[date_key]['scores'].append(score)
                daily_metrics[date_key]['count'] += 1
        
        # Calculate statistics
        import statistics as st
        
        avg_score = round(st.mean(scores), 2) if scores else 0
        median_score = round(st.median(scores), 2) if scores else 0
        score_stdev = round(st.stdev(scores), 2) if len(scores) > 1 else 0
        
        # Category distribution
        category_distribution = {}
        for cat in set(categories):
            count = categories.count(cat)
            category_distribution[cat] = {
                "count": count,
                "percentage": round((count / len(categories)) * 100, 1)
            }
        
        # Daily averages for trend
        daily_averages = []
        for date_key in sorted(daily_metrics.keys()):
            data = daily_metrics[date_key]
            daily_averages.append({
                "date": date_key,
                "average_score": round(st.mean(data['scores']), 2),
                "analyses_count": data['count']
            })
        
        # Generate overall suggestions
        suggestion_engine = SuggestionEngine()
        
        # Use average metrics for suggestions
        avg_metrics = {
            'task_hours': analytics.get('avg_task_hours', 0),
            'tasks_completed': analytics.get('avg_tasks_completed', 0),
            'idle_hours': analytics.get('avg_idle_hours', 0),
            'social_media_usage': analytics.get('avg_social_media_hours', 0),
            'break_frequency': analytics.get('avg_break_frequency', 0),
            'score': avg_score
        }
        
        suggestions = suggestion_engine.generate_suggestions(
            task_hours=avg_metrics['task_hours'],
            idle_hours=avg_metrics['idle_hours'],
            social_media_usage=avg_metrics['social_media_usage'],
            break_frequency=avg_metrics['break_frequency'],
            tasks_completed=avg_metrics['tasks_completed'],
            score=avg_metrics['score'],
            max_suggestions=5
        )
        
        # Determine trend
        if len(daily_averages) >= 2:
            first_half = daily_averages[:len(daily_averages)//2]
            second_half = daily_averages[len(daily_averages)//2:]
            
            first_avg = st.mean([d['average_score'] for d in first_half]) if first_half else 0
            second_avg = st.mean([d['average_score'] for d in second_half]) if second_half else 0
            
            trend_change = round(second_avg - first_avg, 2)
            
            if trend_change > 5:
                trend_direction = "improving"
            elif trend_change < -5:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_change = 0
            trend_direction = "insufficient_data"
        
        return {
            "user_id": user_id,
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_analyses": len(history),
                "average_score": avg_score,
                "median_score": median_score,
                "score_std_deviation": score_stdev,
                "min_score": round(min(scores), 2) if scores else 0,
                "max_score": round(max(scores), 2) if scores else 0
            },
            "category_distribution": category_distribution,
            "trend": {
                "direction": trend_direction,
                "change": trend_change,
                "daily_data": daily_averages[-14:]  # Last 2 weeks
            },
            "suggestions": suggestions,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error generating report for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get(
    "/{user_id}/weekly",
    summary="Get weekly report",
    description="Generate weekly productivity report with day-by-day breakdown."
)
async def get_weekly_report(
    user_id: str,
    weeks_ago: int = Query(default=0, ge=0, le=52, description="Weeks back from current"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Generate weekly productivity report.
    
    Args:
        user_id: User identifier
        weeks_ago: Number of weeks back
        db: Database dependency
        
    Returns:
        Dict with weekly report data
    """
    try:
        # Calculate date range
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday() + (weeks_ago * 7))
        week_end = week_start + timedelta(days=6)
        
        history = await db.get_user_history(user_id=user_id, limit=500)
        
        # Filter to the specified week
        week_data = []
        for record in history:
            timestamp = record.get('created_at') or record.get('timestamp', '')
            if timestamp:
                try:
                    record_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    if week_start <= record_date <= week_end:
                        week_data.append(record)
                except:
                    continue
        
        # Group by day of week
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_breakdown = {day: {'scores': [], 'count': 0} for day in days_of_week}
        
        for record in week_data:
            timestamp = record.get('created_at') or record.get('timestamp', '')
            score = record.get('productivity_score') or record.get('score', 0)
            
            try:
                record_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                day_name = days_of_week[record_date.weekday()]
                daily_breakdown[day_name]['scores'].append(score)
                daily_breakdown[day_name]['count'] += 1
            except:
                continue
        
        # Calculate daily averages
        import statistics as st
        
        daily_summary = []
        for day in days_of_week:
            data = daily_breakdown[day]
            if data['scores']:
                daily_summary.append({
                    "day": day,
                    "average_score": round(st.mean(data['scores']), 2),
                    "analyses_count": data['count'],
                    "min_score": round(min(data['scores']), 2),
                    "max_score": round(max(data['scores']), 2)
                })
            else:
                daily_summary.append({
                    "day": day,
                    "average_score": None,
                    "analyses_count": 0,
                    "min_score": None,
                    "max_score": None
                })
        
        # Weekly totals
        all_scores = [s for data in daily_breakdown.values() for s in data['scores']]
        
        return {
            "user_id": user_id,
            "week_start": str(week_start),
            "week_end": str(week_end),
            "weeks_ago": weeks_ago,
            "total_analyses": len(week_data),
            "weekly_average": round(st.mean(all_scores), 2) if all_scores else None,
            "daily_breakdown": daily_summary,
            "best_day": max(daily_summary, key=lambda x: x['average_score'] or 0)['day'] if all_scores else None,
            "worst_day": min(daily_summary, key=lambda x: x['average_score'] or float('inf'))['day'] if all_scores else None
        }
        
    except Exception as e:
        logger.error(f"Error generating weekly report for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{user_id}/comparison",
    summary="Compare productivity periods",
    description="Compare productivity between two time periods."
)
async def compare_periods(
    user_id: str,
    period1_days: int = Query(default=7, ge=1, le=30, description="First period days back"),
    period2_days: int = Query(default=14, ge=1, le=60, description="Second period days back"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Compare productivity between two periods.
    
    Args:
        user_id: User identifier
        period1_days: Recent period length
        period2_days: Comparison period start
        db: Database dependency
        
    Returns:
        Dict with comparison data
    """
    import statistics as st
    
    try:
        history = await db.get_user_history(user_id=user_id, limit=1000)
        
        today = datetime.utcnow().date()
        
        # Period 1: Last N days
        period1_start = today - timedelta(days=period1_days)
        period1_scores = []
        
        # Period 2: Previous N days before period 1
        period2_start = today - timedelta(days=period2_days)
        period2_end = period1_start - timedelta(days=1)
        period2_scores = []
        
        for record in history:
            timestamp = record.get('created_at') or record.get('timestamp', '')
            score = record.get('productivity_score') or record.get('score', 0)
            
            if timestamp:
                try:
                    record_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    
                    if record_date >= period1_start:
                        period1_scores.append(score)
                    elif period2_start <= record_date <= period2_end:
                        period2_scores.append(score)
                except:
                    continue
        
        # Calculate comparison metrics
        period1_avg = round(st.mean(period1_scores), 2) if period1_scores else None
        period2_avg = round(st.mean(period2_scores), 2) if period2_scores else None
        
        if period1_avg is not None and period2_avg is not None:
            change = round(period1_avg - period2_avg, 2)
            change_percent = round((change / period2_avg) * 100, 1) if period2_avg != 0 else 0
            
            if change > 0:
                status_text = "improved"
            elif change < 0:
                status_text = "declined"
            else:
                status_text = "unchanged"
        else:
            change = None
            change_percent = None
            status_text = "insufficient_data"
        
        return {
            "user_id": user_id,
            "period1": {
                "start": str(period1_start),
                "end": str(today),
                "days": period1_days,
                "analyses_count": len(period1_scores),
                "average_score": period1_avg
            },
            "period2": {
                "start": str(period2_start),
                "end": str(period2_end),
                "days": period2_days - period1_days,
                "analyses_count": len(period2_scores),
                "average_score": period2_avg
            },
            "comparison": {
                "status": status_text,
                "absolute_change": change,
                "percent_change": change_percent
            }
        }
        
    except Exception as e:
        logger.error(f"Error comparing periods for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{user_id}/export/csv",
    summary="Export report as CSV",
    description="Export productivity data as CSV file."
)
async def export_csv(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Days to export"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> StreamingResponse:
    """
    Export user data as CSV.
    
    Args:
        user_id: User identifier
        days: Days of data to export
        db: Database dependency
        
    Returns:
        StreamingResponse with CSV data
    """
    import io
    import csv
    
    try:
        history = await db.get_user_history(user_id=user_id, limit=days)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Date',
            'Productivity Score',
            'Category (Rule-based)',
            'Category (ML)',
            'Task Hours',
            'Tasks Completed',
            'Idle Hours',
            'Social Media Hours',
            'Break Frequency'
        ])
        
        # Data rows
        for record in history:
            writer.writerow([
                record.get('created_at', record.get('timestamp', ''))[:10],
                record.get('productivity_score', record.get('score', '')),
                record.get('category_rule_based', record.get('category', '')),
                record.get('category_ml', ''),
                record.get('task_hours', ''),
                record.get('tasks_completed', ''),
                record.get('idle_hours', ''),
                record.get('social_media_usage', record.get('social_media_hours', '')),
                record.get('break_frequency', '')
            ])
        
        output.seek(0)
        
        filename = f"productivity_report_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting CSV for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/global/leaderboard",
    summary="Get productivity leaderboard",
    description="Get anonymized leaderboard of top productive users."
)
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100, description="Top N users"),
    db: ProductivityAnalysisDB = Depends(get_db)
) -> dict:
    """
    Get anonymized productivity leaderboard.
    
    Note: This returns anonymized user identifiers.
    
    Args:
        limit: Number of top users
        db: Database dependency
        
    Returns:
        Dict with leaderboard data
    """
    try:
        # This would require a more complex query in production
        # For now, return a placeholder structure
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "leaderboard": [],
            "message": "Leaderboard feature requires aggregation queries on user data"
        }
        
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
