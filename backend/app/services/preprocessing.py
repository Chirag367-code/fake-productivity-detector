"""
Data preprocessing service.

This module handles data cleaning, validation, and transformation
for the Fake Productivity Detector ML pipeline.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from pathlib import Path
import joblib

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Data preprocessing pipeline for productivity data.
    
    Handles:
    - Missing value imputation
    - Feature normalization/scaling
    - Label encoding
    - Data validation
    - Train/test splitting
    """
    
    FEATURE_COLUMNS = [
        'task_hours',
        'idle_hours',
        'social_media_usage',
        'break_frequency',
        'tasks_completed'
    ]
    
    TARGET_COLUMN = 'productivity_category'
    
    def __init__(self, scaler_path: Optional[str] = None):
        """
        Initialize preprocessor.
        
        Args:
            scaler_path: Path to saved scaler (if loading existing)
        """
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_fitted = False
        self.scaler_path = scaler_path or "app/ml/scaler.pkl"
        
        # Try to load existing scaler
        self._try_load_scaler()
    
    def _try_load_scaler(self) -> bool:
        """
        Try to load existing fitted scaler.
        
        Returns:
            bool: True if scaler was loaded successfully
        """
        try:
            scaler_file = Path(self.scaler_path)
            if scaler_file.exists():
                self.scaler = joblib.load(scaler_file)
                self.is_fitted = True
                logger.info(f"Loaded existing scaler from {self.scaler_path}")
                return True
        except Exception as e:
            logger.warning(f"Could not load scaler: {e}")
        return False
    
    def save_scaler(self, path: Optional[str] = None) -> None:
        """
        Save fitted scaler to disk.
        
        Args:
            path: Path to save scaler (uses default if not provided)
        """
        save_path = path or self.scaler_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.scaler, save_path)
        logger.info(f"Saved scaler to {save_path}")
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate DataFrame has required columns and valid data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required columns
        missing_cols = set(self.FEATURE_COLUMNS) - set(df.columns)
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
        
        # Check for empty DataFrame
        if df.empty:
            errors.append("DataFrame is empty")
        
        # Check for valid numeric data
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    errors.append(f"Column '{col}' must be numeric")
        
        return len(errors) == 0, errors
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare data for processing.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        
        # Standardize column names
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        # Handle column name variations
        column_mapping = {
            'task_hours': ['task_hours', 'taskhours', 'productive_hours'],
            'idle_hours': ['idle_hours', 'idlehours', 'idle_time'],
            'social_media_usage': ['social_media_usage', 'social_media_hours', 'social_media', 'socialmedia'],
            'break_frequency': ['break_frequency', 'breakfrequency', 'breaks', 'break_count'],
            'tasks_completed': ['tasks_completed', 'taskscompleted', 'completed_tasks', 'task_count']
        }
        
        for standard_name, variations in column_mapping.items():
            for var in variations:
                if var in df.columns and standard_name not in df.columns:
                    df.rename(columns={var: standard_name}, inplace=True)
                    break
        
        # Convert to numeric, coercing errors
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Handle missing values
        df = self.handle_missing_values(df)
        
        # Clip values to valid ranges
        df = self.clip_values(df)
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        logger.info(f"Cleaned data: {len(df)} rows")
        return df
    
    def handle_missing_values(
        self,
        df: pd.DataFrame,
        strategy: str = 'median'
    ) -> pd.DataFrame:
        """
        Handle missing values in DataFrame.
        
        Args:
            df: DataFrame with potential missing values
            strategy: Imputation strategy ('mean', 'median', 'zero')
            
        Returns:
            DataFrame with imputed values
        """
        df = df.copy()
        
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                if df[col].isna().any():
                    if strategy == 'mean':
                        fill_value = df[col].mean()
                    elif strategy == 'median':
                        fill_value = df[col].median()
                    else:
                        fill_value = 0
                    
                    df[col].fillna(fill_value, inplace=True)
                    logger.debug(f"Imputed {col} with {strategy}: {fill_value}")
        
        return df
    
    def clip_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clip feature values to valid ranges.
        
        Args:
            df: DataFrame to clip
            
        Returns:
            DataFrame with clipped values
        """
        df = df.copy()
        
        # Define valid ranges
        ranges = {
            'task_hours': (0, 24),
            'idle_hours': (0, 24),
            'social_media_usage': (0, 24),
            'break_frequency': (0, 50),
            'tasks_completed': (0, 100)
        }
        
        for col, (min_val, max_val) in ranges.items():
            if col in df.columns:
                df[col] = df[col].clip(min_val, max_val)
        
        return df
    
    def fit_transform(
        self,
        df: pd.DataFrame,
        fit: bool = True
    ) -> np.ndarray:
        """
        Fit scaler and transform features.
        
        Args:
            df: DataFrame with features
            fit: Whether to fit the scaler (True for training)
            
        Returns:
            Scaled feature array
        """
        # Ensure all feature columns exist
        for col in self.FEATURE_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        X = df[self.FEATURE_COLUMNS].values
        
        if fit:
            X_scaled = self.scaler.fit_transform(X)
            self.is_fitted = True
            logger.info("Fitted and transformed features")
        else:
            if not self.is_fitted:
                raise ValueError("Scaler not fitted. Call fit_transform first with fit=True")
            X_scaled = self.scaler.transform(X)
            logger.info("Transformed features using existing scaler")
        
        return X_scaled
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform features using fitted scaler.
        
        Args:
            df: DataFrame with features
            
        Returns:
            Scaled feature array
        """
        return self.fit_transform(df, fit=False)
    
    def prepare_single_input(
        self,
        task_hours: float,
        idle_hours: float,
        social_media_usage: float,
        break_frequency: int,
        tasks_completed: int
    ) -> np.ndarray:
        """
        Prepare a single data point for prediction.
        
        Args:
            task_hours: Hours on tasks
            idle_hours: Idle hours
            social_media_usage: Social media hours
            break_frequency: Number of breaks
            tasks_completed: Tasks completed
            
        Returns:
            Scaled feature array for prediction
        """
        data = {
            'task_hours': [task_hours],
            'idle_hours': [idle_hours],
            'social_media_usage': [social_media_usage],
            'break_frequency': [break_frequency],
            'tasks_completed': [tasks_completed]
        }
        
        df = pd.DataFrame(data)
        df = self.clip_values(df)
        
        if self.is_fitted:
            return self.scaler.transform(df[self.FEATURE_COLUMNS].values)
        else:
            # If not fitted, return unscaled (model should handle)
            logger.warning("Scaler not fitted, returning unscaled features")
            return df[self.FEATURE_COLUMNS].values
    
    def encode_labels(
        self,
        labels: pd.Series,
        fit: bool = True
    ) -> np.ndarray:
        """
        Encode categorical labels to integers.
        
        Args:
            labels: Series of category labels
            fit: Whether to fit the encoder
            
        Returns:
            Encoded label array
        """
        if fit:
            return self.label_encoder.fit_transform(labels)
        return self.label_encoder.transform(labels)
    
    def decode_labels(self, encoded: np.ndarray) -> np.ndarray:
        """
        Decode integer labels back to categories.
        
        Args:
            encoded: Array of encoded labels
            
        Returns:
            Array of category strings
        """
        return self.label_encoder.inverse_transform(encoded)
    
    def get_feature_statistics(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        Get descriptive statistics for features.
        
        Args:
            df: DataFrame with features
            
        Returns:
            Dict of statistics per feature
        """
        stats = {}
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                stats[col] = {
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'median': float(df[col].median()),
                    'missing': int(df[col].isna().sum())
                }
        return stats


# Singleton instance
_preprocessor_instance = None


def get_preprocessor() -> DataPreprocessor:
    """
    Get singleton DataPreprocessor instance.
    
    Returns:
        DataPreprocessor: Preprocessor instance
    """
    global _preprocessor_instance
    if _preprocessor_instance is None:
        _preprocessor_instance = DataPreprocessor()
    return _preprocessor_instance
