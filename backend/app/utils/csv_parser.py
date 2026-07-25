"""
CSV parsing utility.

This module handles CSV file parsing and validation
for batch productivity analysis uploads.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from io import StringIO
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class CSVParser:
    """
    CSV parser for productivity data files.
    
    Handles file parsing, column mapping, validation,
    and data extraction for batch analysis.
    """
    
    # Required columns (will try to match variations)
    REQUIRED_COLUMNS = {
        'task_hours': ['task_hours', 'taskhours', 'productive_hours', 'work_hours'],
        'idle_hours': ['idle_hours', 'idlehours', 'idle_time', 'unproductive_hours'],
        'social_media_usage': ['social_media_usage', 'social_media_hours', 'social_media', 'socialmedia', 'social'],
        'break_frequency': ['break_frequency', 'breakfrequency', 'breaks', 'break_count', 'num_breaks'],
        'tasks_completed': ['tasks_completed', 'taskscompleted', 'completed_tasks', 'task_count', 'tasks']
    }
    
    # Minimum required columns
    MINIMUM_REQUIRED = ['task_hours', 'idle_hours']
    
    def __init__(self):
        """Initialize CSV parser."""
        self.column_mapping: Dict[str, str] = {}
        self.validation_errors: List[str] = []
    
    def parse_csv_content(
        self,
        content: str,
        delimiter: str = ','
    ) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse CSV content string into DataFrame.
        
        Args:
            content: CSV file content as string
            delimiter: Column delimiter
            
        Returns:
            Tuple of (DataFrame or None, list of errors)
        """
        self.validation_errors = []
        
        try:
            # Read CSV content
            df = pd.read_csv(
                StringIO(content),
                delimiter=delimiter,
                encoding='utf-8'
            )
            
            if df.empty:
                self.validation_errors.append("CSV file is empty")
                return None, self.validation_errors
            
            # Standardize column names
            df = self._standardize_columns(df)
            
            # Validate required columns
            if not self._validate_columns(df):
                return None, self.validation_errors
            
            # Clean and validate data
            df = self._clean_data(df)
            
            logger.info(f"Successfully parsed CSV: {len(df)} rows")
            return df, []
            
        except pd.errors.EmptyDataError:
            self.validation_errors.append("CSV file is empty")
        except pd.errors.ParserError as e:
            self.validation_errors.append(f"CSV parsing error: {str(e)}")
        except UnicodeDecodeError:
            self.validation_errors.append("CSV encoding error. Please use UTF-8 encoding.")
        except Exception as e:
            self.validation_errors.append(f"Unexpected error: {str(e)}")
            logger.error(f"CSV parsing error: {e}")
        
        return None, self.validation_errors
    
    def parse_csv_bytes(
        self,
        content: bytes,
        delimiter: str = ','
    ) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Parse CSV content from bytes.
        
        Args:
            content: CSV file content as bytes
            delimiter: Column delimiter
            
        Returns:
            Tuple of (DataFrame or None, list of errors)
        """
        try:
            # Try UTF-8 first, then fall back to latin-1
            try:
                decoded = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                decoded = content.decode('latin-1')
            
            return self.parse_csv_content(decoded, delimiter)
            
        except Exception as e:
            return None, [f"Failed to decode CSV content: {str(e)}"]
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to match expected format.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with standardized column names
        """
        # Clean column names
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
        
        # Map columns to standard names
        self.column_mapping = {}
        
        for standard_name, variations in self.REQUIRED_COLUMNS.items():
            for col in df.columns:
                if col in variations or any(var in col for var in variations):
                    if standard_name not in self.column_mapping:
                        self.column_mapping[col] = standard_name
                        break
        
        # Rename columns
        df = df.rename(columns=self.column_mapping)
        
        return df
    
    def _validate_columns(self, df: pd.DataFrame) -> bool:
        """
        Validate that required columns are present.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        present_columns = set(df.columns)
        standard_columns = set(self.REQUIRED_COLUMNS.keys())
        
        # Check minimum required
        for col in self.MINIMUM_REQUIRED:
            if col not in present_columns:
                self.validation_errors.append(
                    f"Missing required column: '{col}'. "
                    f"Accepted variations: {self.REQUIRED_COLUMNS[col]}"
                )
        
        if self.validation_errors:
            return False
        
        # Warn about missing optional columns
        missing_optional = standard_columns - set(self.MINIMUM_REQUIRED) - present_columns
        if missing_optional:
            logger.warning(f"Missing optional columns (will use defaults): {missing_optional}")
        
        return True
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate data values.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        
        # Sanitize string columns against CSV injection
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(
                lambda x: x.lstrip("=+-@\t\r") if isinstance(x, str) else x
            )
        
        # Define default values for missing columns
        defaults = {
            'task_hours': 0.0,
            'idle_hours': 0.0,
            'social_media_usage': 0.0,
            'break_frequency': 0,
            'tasks_completed': 0
        }
        
        # Add missing columns with defaults
        for col, default_val in defaults.items():
            if col not in df.columns:
                df[col] = default_val
        
        # Convert to numeric
        numeric_columns = list(defaults.keys())
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Handle NaN values
        for col, default_val in defaults.items():
            df[col] = df[col].fillna(default_val)
        
        # Clip values to valid ranges
        ranges = {
            'task_hours': (0, 24),
            'idle_hours': (0, 24),
            'social_media_usage': (0, 24),
            'break_frequency': (0, 50),
            'tasks_completed': (0, 100)
        }
        
        for col, (min_val, max_val) in ranges.items():
            df[col] = df[col].clip(min_val, max_val)
        
        # Convert integer columns
        df['break_frequency'] = df['break_frequency'].astype(int)
        df['tasks_completed'] = df['tasks_completed'].astype(int)
        
        return df
    
    def get_row_data(
        self,
        df: pd.DataFrame,
        row_index: int
    ) -> Dict[str, Any]:
        """
        Extract data for a specific row.
        
        Args:
            df: Source DataFrame
            row_index: Row index to extract
            
        Returns:
            Dict containing row data
        """
        row = df.iloc[row_index]
        
        return {
            'task_hours': float(row.get('task_hours', 0)),
            'idle_hours': float(row.get('idle_hours', 0)),
            'social_media_usage': float(row.get('social_media_usage', 0)),
            'break_frequency': int(row.get('break_frequency', 0)),
            'tasks_completed': int(row.get('tasks_completed', 0))
        }
    
    def get_all_rows(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract all rows as list of dicts.
        
        Args:
            df: Source DataFrame
            
        Returns:
            List of row data dicts
        """
        rows = []
        for i in range(len(df)):
            rows.append(self.get_row_data(df, i))
        return rows
    
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate summary statistics for CSV data.
        
        Args:
            df: DataFrame to summarize
            
        Returns:
            Dict of summary statistics
        """
        numeric_cols = ['task_hours', 'idle_hours', 'social_media_usage', 
                       'break_frequency', 'tasks_completed']
        
        stats = {
            'total_rows': len(df),
            'columns_found': list(df.columns),
            'column_stats': {}
        }
        
        for col in numeric_cols:
            if col in df.columns:
                stats['column_stats'][col] = {
                    'mean': round(df[col].mean(), 2),
                    'min': round(df[col].min(), 2),
                    'max': round(df[col].max(), 2),
                    'std': round(df[col].std(), 2)
                }
        
        return stats
    
    def generate_template(self) -> str:
        """
        Generate CSV template content.
        
        Returns:
            CSV template string
        """
        template = """Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
6,1,0.5,4,8
8,0.5,1,3,12
4,3,2,8,3
7,1,1.5,5,10
5,2,3,6,5
3,4,4,10,2
9,0,0.5,2,15"""
        return template


# Singleton instance
_parser_instance = None


def get_csv_parser() -> CSVParser:
    """
    Get singleton CSVParser instance.
    
    Returns:
        CSVParser: Parser instance
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = CSVParser()
    return _parser_instance
