"""
Suggestion engine service.

This module generates personalized improvement suggestions
based on productivity analysis results.
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from ..config import ProductivityCategory

logger = logging.getLogger(__name__)


@dataclass
class SuggestionRule:
    """
    Rule for generating suggestions.
    
    Attributes:
        condition: Condition description
        threshold: Value threshold for triggering
        comparison: Comparison operator ('gt', 'lt', 'gte', 'lte', 'eq')
        suggestion: Suggestion text
        priority: Priority level (1=highest)
        category: Suggestion category
    """
    condition: str
    threshold: float
    comparison: str
    suggestion: str
    priority: int = 5
    category: str = "general"


class SuggestionEngine:
    """
    Engine for generating productivity improvement suggestions.
    
    Analyzes activity data and generates context-aware recommendations
    based on predefined rules and thresholds.
    """
    
    def __init__(self):
        """Initialize suggestion engine with rules."""
        self.rules = self._create_rules()
    
    def _create_rules(self) -> List[SuggestionRule]:
        """
        Create suggestion rules.
        
        Returns:
            List of SuggestionRule objects
        """
        return [
            # High idle time suggestions
            SuggestionRule(
                condition="idle_hours",
                threshold=2.0,
                comparison="gt",
                suggestion="Your idle time is quite high. Try using focus techniques like the Pomodoro method to maintain consistent productivity throughout the day.",
                priority=1,
                category="focus"
            ),
            SuggestionRule(
                condition="idle_hours",
                threshold=1.0,
                comparison="gt",
                suggestion="Consider minimizing idle time with better task planning. Break large tasks into smaller, manageable chunks.",
                priority=2,
                category="focus"
            ),
            
            # Social media suggestions
            SuggestionRule(
                condition="social_media_usage",
                threshold=3.0,
                comparison="gt",
                suggestion="Your social media usage is significantly impacting productivity. Consider using app blockers like Freedom, Cold Turkey, or built-in screen time limits.",
                priority=1,
                category="distraction"
            ),
            SuggestionRule(
                condition="social_media_usage",
                threshold=2.0,
                comparison="gt",
                suggestion="Reduce social media usage to improve focus. Try scheduling specific times for social media instead of checking continuously.",
                priority=2,
                category="distraction"
            ),
            SuggestionRule(
                condition="social_media_usage",
                threshold=1.5,
                comparison="gt",
                suggestion="Consider using website blockers during work hours to minimize social media distractions.",
                priority=3,
                category="distraction"
            ),
            
            # Break frequency suggestions
            SuggestionRule(
                condition="break_frequency",
                threshold=10,
                comparison="gt",
                suggestion="Too many breaks can disrupt your workflow. Try the Pomodoro technique: 25 minutes work, 5 minutes break.",
                priority=1,
                category="breaks"
            ),
            SuggestionRule(
                condition="break_frequency",
                threshold=8,
                comparison="gt",
                suggestion="Consolidate your breaks to maintain workflow momentum. Longer, less frequent breaks are more effective than many short ones.",
                priority=2,
                category="breaks"
            ),
            SuggestionRule(
                condition="break_frequency",
                threshold=2,
                comparison="lt",
                suggestion="Taking regular breaks actually improves productivity. Consider adding short breaks every 45-60 minutes.",
                priority=3,
                category="breaks"
            ),
            
            # Low task hours suggestions
            SuggestionRule(
                condition="task_hours",
                threshold=4.0,
                comparison="lt",
                suggestion="Increase focused work hours for better productivity. Start with time-blocking specific tasks in your calendar.",
                priority=2,
                category="focus"
            ),
            SuggestionRule(
                condition="task_hours",
                threshold=2.0,
                comparison="lt",
                suggestion="Your productive hours are very low. Try identifying your peak productivity hours and scheduling important tasks during those times.",
                priority=1,
                category="focus"
            ),
            
            # Low tasks completed suggestions
            SuggestionRule(
                condition="tasks_completed",
                threshold=3,
                comparison="lt",
                suggestion="Set clear, achievable task goals for each day. Try breaking larger projects into smaller, completable tasks.",
                priority=2,
                category="planning"
            ),
            SuggestionRule(
                condition="tasks_completed",
                threshold=5,
                comparison="lt",
                suggestion="Consider using a task management system like Todoist, Trello, or simple to-do lists to track and complete more tasks.",
                priority=3,
                category="planning"
            ),
            
            # High task hours but low completion
            SuggestionRule(
                condition="efficiency_ratio",
                threshold=0.5,
                comparison="lt",
                suggestion="You're spending time on tasks but completion rate is low. Focus on finishing tasks before starting new ones.",
                priority=2,
                category="efficiency"
            ),
            
            # Positive reinforcement
            SuggestionRule(
                condition="score",
                threshold=80,
                comparison="gte",
                suggestion="Excellent work! Maintain your current productivity habits. Consider sharing your strategies with peers.",
                priority=5,
                category="positive"
            ),
            SuggestionRule(
                condition="score",
                threshold=90,
                comparison="gte",
                suggestion="Outstanding productivity! You're in the top tier. Keep up the great work!",
                priority=5,
                category="positive"
            )
        ]
    
    def generate_suggestions(
        self,
        task_hours: float,
        idle_hours: float,
        social_media_usage: float,
        break_frequency: int,
        tasks_completed: int,
        score: float,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Generate personalized improvement suggestions.
        
        Args:
            task_hours: Hours spent on tasks
            idle_hours: Hours spent idle
            social_media_usage: Hours on social media
            break_frequency: Number of breaks
            tasks_completed: Number of tasks completed
            score: Calculated productivity score
            max_suggestions: Maximum number of suggestions to return
        
        Returns:
            List of suggestion strings
        """
        triggered_suggestions: List[Tuple[int, str, str]] = []  # (priority, category, suggestion)
        
        # Calculate efficiency ratio
        efficiency_ratio = tasks_completed / max(task_hours, 1) if task_hours > 0 else 0
        
        # Check each rule
        metrics = {
            "idle_hours": idle_hours,
            "social_media_usage": social_media_usage,
            "break_frequency": break_frequency,
            "task_hours": task_hours,
            "tasks_completed": tasks_completed,
            "efficiency_ratio": efficiency_ratio,
            "score": score
        }
        
        for rule in self.rules:
            if self._check_rule(rule, metrics):
                triggered_suggestions.append(
                    (rule.priority, rule.category, rule.suggestion)
                )
        
        # Sort by priority (lower = higher priority)
        triggered_suggestions.sort(key=lambda x: x[0])
        
        # Remove duplicates from same category, keeping highest priority
        seen_categories = set()
        unique_suggestions = []
        
        for priority, category, suggestion in triggered_suggestions:
            if category not in seen_categories or category == "positive":
                unique_suggestions.append(suggestion)
                seen_categories.add(category)
        
        # Add default suggestions if none triggered
        if not unique_suggestions:
            unique_suggestions = self._get_default_suggestions(score)
        
        # Limit number of suggestions
        return unique_suggestions[:max_suggestions]
    
    def _check_rule(
        self,
        rule: SuggestionRule,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Check if a rule condition is met.
        
        Args:
            rule: Rule to check
            metrics: Dict of metric values
            
        Returns:
            True if condition is met
        """
        if rule.condition not in metrics:
            return False
        
        value = metrics[rule.condition]
        threshold = rule.threshold
        
        comparisons = {
            "gt": value > threshold,
            "lt": value < threshold,
            "gte": value >= threshold,
            "lte": value <= threshold,
            "eq": value == threshold
        }
        
        return comparisons.get(rule.comparison, False)
    
    def _get_default_suggestions(self, score: float) -> List[str]:
        """
        Get default suggestions when no specific rules triggered.
        
        Args:
            score: Productivity score
            
        Returns:
            List of default suggestions
        """
        if score >= 80:
            return [
                "Excellent work! Maintain your current productivity habits.",
                "Consider mentoring others with your productivity strategies.",
                "Challenge yourself with more ambitious goals."
            ]
        elif score >= 50:
            return [
                "Good progress! Focus on consistency to improve further.",
                "Try identifying your peak productivity hours.",
                "Set specific goals for each work session."
            ]
        else:
            return [
                "Start with small improvements - even 10% better is progress.",
                "Identify your biggest time wasters and address them first.",
                "Consider using productivity apps to track your time.",
                "Set realistic daily goals and celebrate small wins."
            ]
    
    def get_category_specific_tips(self, category: str) -> List[str]:
        """
        Get tips specific to a productivity category.
        
        Args:
            category: Productivity category
            
        Returns:
            List of category-specific tips
        """
        tips = {
            ProductivityCategory.HIGHLY_PRODUCTIVE: [
                "Share your productivity strategies with colleagues",
                "Consider taking on leadership roles in team projects",
                "Mentor others who are struggling with productivity",
                "Document your workflow for future reference"
            ],
            ProductivityCategory.MODERATELY_PRODUCTIVE: [
                "You're on the right track - focus on consistency",
                "Identify your top 3 time wasters and address them",
                "Try time-blocking your most important tasks",
                "Review your productivity weekly and adjust"
            ],
            ProductivityCategory.FAKE_PRODUCTIVITY: [
                "Start fresh with a simple daily planning routine",
                "Focus on completing one task before starting another",
                "Use the 2-minute rule: if it takes 2 minutes, do it now",
                "Set up your environment to minimize distractions",
                "Consider an accountability partner or productivity coach"
            ]
        }
        
        return tips.get(category, tips[ProductivityCategory.MODERATELY_PRODUCTIVE])
    
    def get_quick_wins(
        self,
        idle_hours: float,
        social_media_hours: float,
        break_frequency: int
    ) -> List[str]:
        """
        Get quick actionable improvements.
        
        Args:
            idle_hours: Current idle hours
            social_media_hours: Current social media usage
            break_frequency: Current break frequency
            
        Returns:
            List of quick win suggestions
        """
        quick_wins = []
        
        if social_media_hours > 1:
            potential_gain = min(social_media_hours * 7, 20)
            quick_wins.append(
                f"Reducing social media by 1 hour could boost your score by ~{potential_gain:.0f} points"
            )
        
        if idle_hours > 1:
            potential_gain = min(idle_hours * 6, 18)
            quick_wins.append(
                f"Converting 1 idle hour to productive work could add ~{potential_gain:.0f} points"
            )
        
        if break_frequency > 8:
            potential_gain = (break_frequency - 5) * 2
            quick_wins.append(
                f"Optimizing break frequency could add ~{potential_gain:.0f} points"
            )
        
        if not quick_wins:
            quick_wins.append("Your metrics look good! Focus on maintaining consistency.")
        
        return quick_wins


# Singleton instance
_suggestion_engine = None


def get_suggestion_engine() -> SuggestionEngine:
    """
    Get singleton SuggestionEngine instance.
    
    Returns:
        SuggestionEngine: Engine instance
    """
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine()
    return _suggestion_engine
