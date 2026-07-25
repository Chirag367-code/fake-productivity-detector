"""
Machine Learning model service.

This module provides ML classification capabilities for productivity
category prediction using scikit-learn models.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support
)
import joblib

from ..config import settings, ProductivityCategory
from .preprocessing import DataPreprocessor, get_preprocessor

logger = logging.getLogger(__name__)


class MLClassifier:
    """
    Machine Learning classifier for productivity categories.
    
    Supports multiple model types:
    - Logistic Regression
    - Random Forest
    - Decision Tree
    
    Features model training, evaluation, saving/loading, and prediction.
    """
    
    SUPPORTED_MODELS = {
        'logistic_regression': LogisticRegression,
        'random_forest': RandomForestClassifier,
        'decision_tree': DecisionTreeClassifier
    }
    
    CATEGORY_CLASSES = [
        ProductivityCategory.FAKE_PRODUCTIVITY,
        ProductivityCategory.MODERATELY_PRODUCTIVE,
        ProductivityCategory.HIGHLY_PRODUCTIVE
    ]
    
    def __init__(
        self,
        model_type: str = 'random_forest',
        model_path: Optional[str] = None
    ):
        """
        Initialize ML classifier.
        
        Args:
            model_type: Type of model to use
            model_path: Path to saved model file
        """
        self.model_type = model_type
        self.model_path = model_path or settings.ml_model_path
        self.model = None
        self.is_trained = False
        self.training_accuracy = 0.0
        self.preprocessor = get_preprocessor()
        
        # Model parameters
        self.model_params = {
            'logistic_regression': {
                'max_iter': 1000,
                'random_state': 42,
                'multi_class': 'multinomial'
            },
            'random_forest': {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42,
                'n_jobs': -1
            },
            'decision_tree': {
                'max_depth': 10,
                'random_state': 42
            }
        }
        
        # Try to load existing model
        self._try_load_model()
    
    def _try_load_model(self) -> bool:
        """
        Try to load existing trained model.
        
        Returns:
            bool: True if model was loaded successfully
        """
        try:
            model_file = Path(self.model_path)
            logger.info(f"Attempting to load model from: {model_file.resolve()}")
            if model_file.exists():
                saved_data = joblib.load(model_file)
                self.model = saved_data['model']
                self.model_type = saved_data.get('model_type', 'unknown')
                self.training_accuracy = saved_data.get('accuracy', 0.0)
                self.is_trained = True
                logger.info(
                    f"Loaded existing {self.model_type} model "
                    f"(accuracy: {self.training_accuracy:.2%})"
                )
                return True
            else:
                logger.warning(f"Model file does not exist at: {model_file.resolve()}")
        except Exception as e:
            logger.warning(f"Could not load model from {self.model_path}: {e}")
        return False
    
    def _create_model(self, model_type: Optional[str] = None) -> Any:
        """
        Create a new model instance.
        
        Args:
            model_type: Type of model to create
            
        Returns:
            Sklearn model instance
        """
        model_type = model_type or self.model_type
        
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model type: {model_type}. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )
        
        model_class = self.SUPPORTED_MODELS[model_type]
        params = self.model_params.get(model_type, {})
        
        return model_class(**params)
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the model on provided data.
        
        Args:
            X: Feature array (scaled)
            y: Label array
            test_size: Fraction of data for testing
            
        Returns:
            Dict containing training results
        """
        logger.info(f"Training {self.model_type} model on {len(X)} samples...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y
        )
        
        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        self.training_accuracy = accuracy
        self.is_trained = True
        
        # Generate detailed report
        report = classification_report(
            y_test, y_pred,
            target_names=self.CATEGORY_CLASSES,
            output_dict=True
        )
        
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        results = {
            'model_type': self.model_type,
            'accuracy': accuracy,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'classification_report': report,
            'confusion_matrix': conf_matrix.tolist()
        }
        
        logger.info(f"Training complete. Accuracy: {accuracy:.2%}")
        
        return results
    
    def train_and_compare(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Dict[str, Dict[str, Any]]:
        """
        Train all supported models and compare performance.
        
        Args:
            X: Feature array (scaled)
            y: Label array
            test_size: Fraction of data for testing
            
        Returns:
            Dict mapping model names to their results
        """
        results = {}
        best_accuracy = 0.0
        best_model_type = None
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y
        )
        
        for model_name in self.SUPPORTED_MODELS.keys():
            logger.info(f"Training {model_name}...")
            
            model = self._create_model(model_name)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X, y, cv=5)
            
            report = classification_report(
                y_test, y_pred,
                target_names=self.CATEGORY_CLASSES,
                output_dict=True
            )
            
            results[model_name] = {
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'classification_report': report
            }
            
            logger.info(f"{model_name}: Accuracy={accuracy:.2%}, CV={cv_scores.mean():.2%}")
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_model_type = model_name
                self.model = model
        
        # Set best model
        self.model_type = best_model_type
        self.training_accuracy = best_accuracy
        self.is_trained = True
        
        logger.info(f"Best model: {best_model_type} (accuracy: {best_accuracy:.2%})")
        
        return {
            'model_results': results,
            'best_model': best_model_type,
            'best_accuracy': best_accuracy
        }
    
    def predict(
        self,
        X: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on input data.
        
        Args:
            X: Feature array (should be scaled)
            
        Returns:
            Tuple of (predicted categories, probability arrays)
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        predictions = self.model.predict(X)
        
        # Get probabilities if available
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X)
        else:
            # Create dummy probabilities for models without predict_proba
            probabilities = np.zeros((len(predictions), len(self.CATEGORY_CLASSES)))
            for i, pred in enumerate(predictions):
                idx = self.CATEGORY_CLASSES.index(pred) if pred in self.CATEGORY_CLASSES else 0
                probabilities[i, idx] = 1.0
        
        return predictions, probabilities
    
    def predict_single(
        self,
        task_hours: float,
        idle_hours: float,
        social_media_usage: float,
        break_frequency: int,
        tasks_completed: int
    ) -> Dict[str, Any]:
        """
        Make prediction for a single data point.
        
        Args:
            task_hours: Hours on tasks
            idle_hours: Idle hours
            social_media_usage: Social media hours
            break_frequency: Number of breaks
            tasks_completed: Tasks completed
            
        Returns:
            Dict with prediction results
        """
        X = self.preprocessor.prepare_single_input(
            task_hours, idle_hours, social_media_usage,
            break_frequency, tasks_completed
        )
        
        predictions, probabilities = self.predict(X)
        
        prediction = predictions[0]
        probs = probabilities[0]
        
        # Create probability dict
        prob_dict = {}
        for i, category in enumerate(self.CATEGORY_CLASSES):
            prob_dict[category] = float(probs[i]) if i < len(probs) else 0.0
        
        return {
            'predicted_category': prediction,
            'confidence': float(max(probs)),
            'probabilities': prob_dict,
            'model_used': self.model_type
        }
    
    def save_model(self, path: Optional[str] = None) -> None:
        """
        Save trained model to disk.
        
        Args:
            path: Path to save model (uses default if not provided)
        """
        if not self.is_trained or self.model is None:
            raise ValueError("No trained model to save")
        
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        save_data = {
            'model': self.model,
            'model_type': self.model_type,
            'accuracy': self.training_accuracy,
            'classes': self.CATEGORY_CLASSES
        }
        
        joblib.dump(save_data, save_path)
        logger.info(f"Saved model to {save_path}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict with model information
        """
        info = {
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'accuracy': self.training_accuracy,
            'features': self.preprocessor.FEATURE_COLUMNS,
            'classes': self.CATEGORY_CLASSES
        }
        
        if self.is_trained and self.model is not None:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                info['feature_importances'] = dict(
                    zip(self.preprocessor.FEATURE_COLUMNS, importances.tolist())
                )
        
        return info
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance from trained model (if available).
        
        Returns:
            Dict mapping feature names to importance scores
        """
        if not self.is_trained or self.model is None:
            return None
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return dict(zip(self.preprocessor.FEATURE_COLUMNS, importances.tolist()))
        elif hasattr(self.model, 'coef_'):
            # For logistic regression, use absolute coefficient values
            coef = np.abs(self.model.coef_).mean(axis=0)
            return dict(zip(self.preprocessor.FEATURE_COLUMNS, coef.tolist()))
        
        return None


# Singleton instance
_classifier_instance = None


def get_classifier() -> MLClassifier:
    """
    Get singleton MLClassifier instance.
    
    Returns:
        MLClassifier: Classifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = MLClassifier()
    return _classifier_instance
