"""
Productivity scoring service.

This module implements the rule-based productivity scoring algorithm
for the Fake Productivity Detector.
"""

import logging
from typing import Dict, Tuple
from dataclasses import dataclass

from ..config import ScoringConfig, ProductivityCategory

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """
    Result of productivity score calculation.
    
    Attributes:
        score: Normalized productivity score (0-100)
        category: Productivity category classification
        breakdown: Score contribution breakdown
        raw_score: Raw score before normalization
    """
    score: float
    category: str
    breakdown: Dict[str, float]
    raw_score: float


class ProductivityScorer:
    """
    Rule-based productivity scoring engine.
    
    Implements the formula:
    score = (task_hours × 8) + (tasks_completed × 5)
            - (idle_hours × 6) - (social_media × 7)
            - (break_frequency × 2)
    
    Normalized to 0-100 range.
    """
    
    def __init__(self):
        """Initialize scorer with configuration."""
        self.config = ScoringConfig()
    
    def calculate_score(
        self,
        task_hours: float,
        idle_hours: float,
        social_media_hours: float,
        break_frequency: int,
        tasks_completed: int
    ) -> ScoringResult:
        """
        Calculate productivity score from activity data.
        
        Args:
            task_hours: Hours spent on productive tasks
            idle_hours: Hours spent idle
            social_media_hours: Hours spent on social media
            break_frequency: Number of breaks taken
            tasks_completed: Number of tasks completed
            
        Returns:
            ScoringResult: Complete scoring result with breakdown
        """
        # Calculate score components
        task_contribution = task_hours * self.config.TASK_WEIGHT
        tasks_completed_contribution = tasks_completed * self.config.TASKS_COMPLETED_WEIGHT
        
        idle_penalty = idle_hours * self.config.IDLE_WEIGHT
        social_media_penalty = social_media_hours * self.config.SOCIAL_MEDIA_WEIGHT
        break_penalty = break_frequency * self.config.BREAK_WEIGHT
        
        # Calculate raw score
        raw_score = (
            task_contribution 
            + tasks_completed_contribution
            - idle_penalty
            - social_media_penalty
            - break_penalty
        )
        
        # Normalize to 0-100
        normalized_score = self._normalize_score(raw_score)
        
        # Determine category
        category = self._classify_category(normalized_score)
        
        # Create breakdown
        breakdown = {
            "productive": round(task_hours, 2),
            "idle": round(idle_hours, 2),
            "social": round(social_media_hours, 2),
            "breaks": round(break_frequency / 2, 2),  # Convert to hours equivalent
            "task_contribution": round(task_contribution, 2),
            "tasks_completed_contribution": round(tasks_completed_contribution, 2),
            "idle_penalty": round(-idle_penalty, 2),
            "social_media_penalty": round(-social_media_penalty, 2),
            "break_penalty": round(-break_penalty, 2)
        }
        
        logger.debug(
            f"Calculated score: {normalized_score:.2f} "
            f"(raw: {raw_score:.2f}) - {category}"
        )
        
        return ScoringResult(
            score=round(normalized_score, 2),
            category=category,
            breakdown=breakdown,
            raw_score=round(raw_score, 2)
        )
    
    def _normalize_score(self, raw_score: float) -> float:
        """
        Normalize raw score to 0-100 range.
        
        Args:
            raw_score: Raw calculated score
            
        Returns:
            float: Normalized score between 0 and 100
        """
        return max(
            self.config.MIN_SCORE,
            min(self.config.MAX_SCORE, raw_score)
        )
    
    def _classify_category(self, score: float) -> str:
        """
        Classify productivity category based on score.
        
        Args:
            score: Normalized productivity score
            
        Returns:
            str: Productivity category label
        """
        if score >= self.config.HIGHLY_PRODUCTIVE_MIN:
            return ProductivityCategory.HIGHLY_PRODUCTIVE
        elif score >= self.config.MODERATELY_PRODUCTIVE_MIN:
            return ProductivityCategory.MODERATELY_PRODUCTIVE
        else:
            return ProductivityCategory.FAKE_PRODUCTIVITY
    
    def get_category_thresholds(self) -> Dict[str, Tuple[float, float]]:
        """
        Get category score thresholds.
        
        Returns:
            Dict mapping category names to (min, max) score tuples
        """
        return {
            ProductivityCategory.HIGHLY_PRODUCTIVE: (
                self.config.HIGHLY_PRODUCTIVE_MIN,
                self.config.MAX_SCORE
            ),
            ProductivityCategory.MODERATELY_PRODUCTIVE: (
                self.config.MODERATELY_PRODUCTIVE_MIN,
                self.config.HIGHLY_PRODUCTIVE_MIN - 0.01
            ),
            ProductivityCategory.FAKE_PRODUCTIVITY: (
                self.config.MIN_SCORE,
                self.config.MODERATELY_PRODUCTIVE_MIN - 0.01
            )
        }
    
    def explain_score(
        self,
        task_hours: float,
        idle_hours: float,
        social_media_hours: float,
        break_frequency: int,
        tasks_completed: int
    ) -> str:
        """
        Generate human-readable explanation of score calculation.
        
        Args:
            task_hours: Hours spent on productive tasks
            idle_hours: Hours spent idle
            social_media_hours: Hours spent on social media
            break_frequency: Number of breaks taken
            tasks_completed: Number of tasks completed
            
        Returns:
            str: Detailed explanation of score calculation
        """
        result = self.calculate_score(
            task_hours, idle_hours, social_media_hours,
            break_frequency, tasks_completed
        )
        
        explanation = f"""
Productivity Score Calculation
==============================

Input Data:
- Task Hours: {task_hours}
- Idle Hours: {idle_hours}
- Social Media Hours: {social_media_hours}
- Break Frequency: {break_frequency}
- Tasks Completed: {tasks_completed}

Formula:
score = (task_hours × {self.config.TASK_WEIGHT}) + (tasks_completed × {self.config.TASKS_COMPLETED_WEIGHT})
        - (idle_hours × {self.config.IDLE_WEIGHT})
        - (social_media × {self.config.SOCIAL_MEDIA_WEIGHT})
        - (break_frequency × {self.config.BREAK_WEIGHT})

Calculation:
+ Task contribution: {task_hours} × {self.config.TASK_WEIGHT} = {result.breakdown['task_contribution']}
+ Tasks completed:   {tasks_completed} × {self.config.TASKS_COMPLETED_WEIGHT} = {result.breakdown['tasks_completed_contribution']}
- Idle penalty:      {idle_hours} × {self.config.IDLE_WEIGHT} = {result.breakdown['idle_penalty']}
- Social media:      {social_media_hours} × {self.config.SOCIAL_MEDIA_WEIGHT} = {result.breakdown['social_media_penalty']}
- Break penalty:     {break_frequency} × {self.config.BREAK_WEIGHT} = {result.breakdown['break_penalty']}

Raw Score: {result.raw_score}
Normalized Score (0-100): {result.score}

Category: {result.category}
"""
        return explanation.strip()


# Singleton instance
_scorer_instance = None


def get_scorer() -> ProductivityScorer:
    """
    Get singleton ProductivityScorer instance.
    
    Returns:
        ProductivityScorer: Scorer instance
    """
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = ProductivityScorer()
    return _scorer_instance
