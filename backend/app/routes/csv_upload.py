"""
CSV Upload API routes.

This module provides endpoints for batch CSV processing.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import io

from ..models.schemas import (
    BatchAnalysisResult,
    BatchSummary,
    AnalysisResult,
    ScoreBreakdown,
    ErrorResponse
)
from ..models.database import ProductivityAnalysisDB, get_db
from ..services.scoring import ProductivityScorer, get_scorer
from ..services.ml_model import MLClassifier, get_classifier
from ..services.suggestions import SuggestionEngine, get_suggestion_engine
from ..utils.csv_parser import CSVParser, get_csv_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload-csv", tags=["CSV Upload"])


@router.post(
    "",
    response_model=BatchAnalysisResult,
    summary="Upload and analyze CSV",
    description="Upload a CSV file for batch productivity analysis."
)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to upload"),
    user_id: str = Form(..., description="User identifier"),
    user_name: str = Form(..., description="User display name"),
    db: ProductivityAnalysisDB = Depends(get_db),
    scorer: ProductivityScorer = Depends(get_scorer),
    classifier: MLClassifier = Depends(get_classifier),
    suggestion_engine: SuggestionEngine = Depends(get_suggestion_engine),
    csv_parser: CSVParser = Depends(get_csv_parser)
) -> BatchAnalysisResult:
    """
    Process CSV file for batch productivity analysis.
    
    Workflow:
    1. Parse and validate CSV content
    2. Process each row through scoring algorithm
    3. Apply ML classification (if available)
    4. Generate suggestions
    5. Store all results in database
    6. Return batch summary
    
    Args:
        file: Uploaded CSV file
        user_id: User identifier
        user_name: User display name
        db: Database dependency
        scorer: Scoring service
        classifier: ML classifier
        suggestion_engine: Suggestion engine
        csv_parser: CSV parser utility
        
    Returns:
        BatchAnalysisResult with all processed rows and summary
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse CSV
        df, errors = csv_parser.parse_csv_bytes(content)
        
        if errors:
            logger.warning(f"CSV parsing errors: {errors}")
            return BatchAnalysisResult(
                total_rows=0,
                successful=0,
                failed=0,
                results=[],
                summary=BatchSummary(
                    average_score=0,
                    highest_score=0,
                    lowest_score=0,
                    category_distribution={}
                ),
                errors=errors
            )
        
        # Process each row
        results: List[AnalysisResult] = []
        row_errors: List[str] = []
        scores: List[float] = []
        categories: List[str] = []
        
        rows = csv_parser.get_all_rows(df)
        
        for i, row_data in enumerate(rows, start=1):
            try:
                # Only allow expected keys for ML and suggestions
                allowed_keys = [
                    'task_hours', 'idle_hours', 'social_media_usage', 'break_frequency', 'tasks_completed'
                ]
                filtered_row_data = {k: row_data[k] for k in allowed_keys if k in row_data}

                # Calculate score
                scoring_result = scorer.calculate_score(
                    task_hours=filtered_row_data['task_hours'],
                    idle_hours=filtered_row_data['idle_hours'],
                    social_media_hours=filtered_row_data['social_media_usage'],
                    break_frequency=filtered_row_data['break_frequency'],
                    tasks_completed=filtered_row_data['tasks_completed']
                )

                # ML prediction
                ml_category = None
                if classifier.is_trained:
                    try:
                        ml_result = classifier.predict_single(**filtered_row_data)
                        ml_category = ml_result['predicted_category']
                    except Exception:
                        pass

                # Prepare only allowed arguments for suggestions
                suggestion_args = {
                    'task_hours': filtered_row_data.get('task_hours', 0),
                    'idle_hours': filtered_row_data.get('idle_hours', 0),
                    'social_media_usage': filtered_row_data.get('social_media_usage', 0),
                    'break_frequency': filtered_row_data.get('break_frequency', 0),
                    'tasks_completed': filtered_row_data.get('tasks_completed', 0),
                    'score': scoring_result.score,
                    'max_suggestions': 3
                }
                suggestions = suggestion_engine.generate_suggestions(**suggestion_args)
                
                timestamp = datetime.utcnow().isoformat()
                
                # Save to database
                record = await db.create_analysis(
                    user_id=user_id,
                    user_name=user_name,
                    task_hours=row_data['task_hours'],
                    idle_hours=row_data['idle_hours'],
                    social_media_usage=row_data['social_media_usage'],
                    break_frequency=row_data['break_frequency'],
                    tasks_completed=row_data['tasks_completed'],
                    productivity_score=scoring_result.score,
                    category_rule_based=scoring_result.category,
                    category_ml=ml_category,
                    suggestions=suggestions
                )
                
                # Create result
                result = AnalysisResult(
                    id=record.get('id'),
                    user_id=user_id,
                    user_name=user_name,
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
                    task_hours=row_data['task_hours'],
                    idle_hours=row_data['idle_hours'],
                    social_media_usage=row_data['social_media_usage'],
                    break_frequency=row_data['break_frequency'],
                    tasks_completed=row_data['tasks_completed']
                )
                
                results.append(result)
                scores.append(scoring_result.score)
                categories.append(scoring_result.category)
                
            except Exception as e:
                error_msg = f"Row {i}: {str(e)}"
                row_errors.append(error_msg)
                logger.warning(f"Error processing row {i}: {e}")
        
        # Calculate summary
        if scores:
            summary = BatchSummary(
                average_score=round(sum(scores) / len(scores), 2),
                highest_score=round(max(scores), 2),
                lowest_score=round(min(scores), 2),
                category_distribution={
                    "Highly Productive": categories.count("Highly Productive"),
                    "Moderately Productive": categories.count("Moderately Productive"),
                    "Fake Productivity": categories.count("Fake Productivity")
                }
            )
        else:
            summary = BatchSummary(
                average_score=0,
                highest_score=0,
                lowest_score=0,
                category_distribution={
                    "Highly Productive": 0,
                    "Moderately Productive": 0,
                    "Fake Productivity": 0
                }
            )
        return BatchAnalysisResult(
            total_rows=len(rows),
            successful=len(results),
            failed=len(row_errors),
            results=results,
            summary=summary,
            errors=row_errors
        )
        
    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV processing failed: {str(e)}"
        )


@router.get(
    "/template",
    summary="Download CSV template",
    description="Download a sample CSV template for productivity data."
)
async def download_template(
    csv_parser: CSVParser = Depends(get_csv_parser)
) -> StreamingResponse:
    """
    Download CSV template file.
    
    Returns:
        Streaming response with CSV template
    """
    template = csv_parser.generate_template()
    
    return StreamingResponse(
        io.BytesIO(template.encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=productivity_template.csv"
        }
    )


@router.post(
    "/validate",
    summary="Validate CSV without processing",
    description="Validate a CSV file structure without performing analysis."
)
async def validate_csv(
    file: UploadFile = File(...),
    csv_parser: CSVParser = Depends(get_csv_parser)
) -> dict:
    """
    Validate CSV file structure without processing.
    
    Args:
        file: CSV file to validate
        csv_parser: Parser utility
        
    Returns:
        Validation result with column info and statistics
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted"
        )
    
    try:
        content = await file.read()
        df, errors = csv_parser.parse_csv_bytes(content)
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "rows": 0,
                "columns": [],
                "statistics": {}
            }
        
        stats = csv_parser.get_summary_stats(df)
        
        return {
            "valid": True,
            "errors": [],
            "rows": stats['total_rows'],
            "columns": stats['columns_found'],
            "statistics": stats['column_stats']
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "rows": 0,
            "columns": [],
            "statistics": {}
        }


@router.post(
    "/preview",
    summary="Preview CSV analysis",
    description="Analyze first 5 rows without saving to database."
)
async def preview_csv(
    file: UploadFile = File(...),
    csv_parser: CSVParser = Depends(get_csv_parser),
    scorer: ProductivityScorer = Depends(get_scorer)
) -> dict:
    """
    Preview analysis of first few rows.
    
    Args:
        file: CSV file to preview
        csv_parser: Parser utility
        scorer: Scoring service
        
    Returns:
        Preview results for first 5 rows
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted"
        )
    
    try:
        content = await file.read()
        df, errors = csv_parser.parse_csv_bytes(content)
        
        if errors:
            return {"valid": False, "errors": errors, "preview": []}
        
        # Get first 5 rows
        rows = csv_parser.get_all_rows(df)[:5]
        preview_results = []
        
        for i, row_data in enumerate(rows, start=1):
            scoring_result = scorer.calculate_score(
                task_hours=row_data['task_hours'],
                idle_hours=row_data['idle_hours'],
                social_media_hours=row_data['social_media_usage'],
                break_frequency=row_data['break_frequency'],
                tasks_completed=row_data['tasks_completed']
            )
            
            preview_results.append({
                "row": i,
                "input": row_data,
                "score": scoring_result.score,
                "category": scoring_result.category
            })
        
        return {
            "valid": True,
            "total_rows": len(csv_parser.get_all_rows(df)),
            "preview": preview_results
        }
        
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "preview": []}
