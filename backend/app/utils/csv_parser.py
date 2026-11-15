"""
CSV parsing utility.

This module handles CSV file parsing and validation
for batch productivity analysis uploads.
Works with pandas if installed, or falls back to Python's built-in csv module.
"""

import csv
import io
import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CSVData:
    """Lightweight tabular container when pandas is not installed."""
    def __init__(self, rows: List[Dict[str, Any]], columns: List[str]):
        self.rows = rows
        self.columns = columns

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def empty(self) -> bool:
        return len(self.rows) == 0


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
    ) -> Tuple[Optional[Any], List[str]]:
        """
        Parse CSV content string into a tabular container.
        
        Args:
            content: CSV file content as string
            delimiter: Column delimiter
            
        Returns:
            Tuple of (Data container or None, list of errors)
        """
        self.validation_errors = []
        
        try:
            # Check empty content
            if not content or not content.strip():
                self.validation_errors.append("CSV file is empty")
                return None, self.validation_errors

            # Try parsing with standard csv module
            f = io.StringIO(content.strip())
            reader = csv.reader(f, delimiter=delimiter)
            
            raw_headers = next(reader, None)
            if not raw_headers:
                self.validation_errors.append("CSV file is empty")
                return None, self.validation_errors

            # Clean and map headers
            clean_headers = [h.lower().strip().replace(' ', '_') for h in raw_headers]
            mapped_headers: Dict[int, str] = {}
            self.column_mapping = {}

            for idx, h in enumerate(clean_headers):
                for standard_name, variations in self.REQUIRED_COLUMNS.items():
                    if h in variations or any(var in h for var in variations):
                        if standard_name not in self.column_mapping.values():
                            mapped_headers[idx] = standard_name
                            self.column_mapping[h] = standard_name
                            break

            # Validate minimum required columns
            found_standard_cols = set(mapped_headers.values())
            for col in self.MINIMUM_REQUIRED:
                if col not in found_standard_cols:
                    self.validation_errors.append(
                        f"Missing required column: '{col}'. "
                        f"Accepted variations: {self.REQUIRED_COLUMNS[col]}"
                    )

            if self.validation_errors:
                return None, self.validation_errors

            ranges = {
                'task_hours': (0.0, 24.0),
                'idle_hours': (0.0, 24.0),
                'social_media_usage': (0.0, 24.0),
                'break_frequency': (0, 50),
                'tasks_completed': (0, 100)
            }

            parsed_rows: List[Dict[str, Any]] = []
            for row in reader:
                if not row or not any(field.strip() for field in row):
                    continue  # skip blank lines

                row_dict: Dict[str, Any] = {
                    'task_hours': 0.0,
                    'idle_hours': 0.0,
                    'social_media_usage': 0.0,
                    'break_frequency': 0,
                    'tasks_completed': 0
                }

                for idx, val in enumerate(row):
                    if idx in mapped_headers:
                        col_name = mapped_headers[idx]
                        # Sanitize string against formula injection
                        clean_val = val.lstrip("=+-@\t\r").strip()
                        try:
                            if col_name in ('break_frequency', 'tasks_completed'):
                                num_val = int(float(clean_val))
                            else:
                                num_val = float(clean_val)
                        except (ValueError, TypeError):
                            num_val = row_dict[col_name]

                        # Clip to valid range
                        min_v, max_v = ranges[col_name]
                        if num_val < min_v:
                            num_val = min_v
                        elif num_val > max_v:
                            num_val = max_v

                        row_dict[col_name] = num_val

                parsed_rows.append(row_dict)

            if not parsed_rows:
                self.validation_errors.append("CSV file contains no valid data rows")
                return None, self.validation_errors

            columns = list(ranges.keys())
            container = CSVData(rows=parsed_rows, columns=columns)
            logger.info(f"Successfully parsed CSV: {len(container)} rows")
            return container, []

        except UnicodeDecodeError:
            self.validation_errors.append("CSV encoding error. Please use UTF-8 encoding.")
        except Exception as e:
            self.validation_errors.append(f"CSV parsing error: {str(e)}")
            logger.error(f"CSV parsing error: {e}")
        
        return None, self.validation_errors
    
    def parse_csv_bytes(
        self,
        content: bytes,
        delimiter: str = ','
    ) -> Tuple[Optional[Any], List[str]]:
        """
        Parse CSV content from bytes.
        
        Args:
            content: CSV file content as bytes
            delimiter: Column delimiter
            
        Returns:
            Tuple of (Data container or None, list of errors)
        """
        try:
            try:
                decoded = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                decoded = content.decode('latin-1')
            
            return self.parse_csv_content(decoded, delimiter)
            
        except Exception as e:
            return None, [f"Failed to decode CSV content: {str(e)}"]
    
    def get_row_data(
        self,
        df: Any,
        row_index: int
    ) -> Dict[str, Any]:
        """
        Extract data for a specific row.
        
        Args:
            df: Source tabular container
            row_index: Row index to extract
            
        Returns:
            Dict containing row data
        """
        if isinstance(df, CSVData):
            row = df.rows[row_index]
        elif hasattr(df, 'iloc'):
            row = df.iloc[row_index]
        else:
            row = df[row_index]
            
        return {
            'task_hours': float(row.get('task_hours', 0)),
            'idle_hours': float(row.get('idle_hours', 0)),
            'social_media_usage': float(row.get('social_media_usage', 0)),
            'break_frequency': int(row.get('break_frequency', 0)),
            'tasks_completed': int(row.get('tasks_completed', 0))
        }
    
    def get_all_rows(self, df: Any) -> List[Dict[str, Any]]:
        """
        Extract all rows as list of dicts.
        
        Args:
            df: Source tabular container
            
        Returns:
            List of row data dicts
        """
        if isinstance(df, CSVData):
            return df.rows
        if isinstance(df, list):
            return df
        rows = []
        for i in range(len(df)):
            rows.append(self.get_row_data(df, i))
        return rows
    
    def get_summary_stats(self, df: Any) -> Dict[str, Any]:
        """
        Calculate summary statistics for CSV data.
        
        Args:
            df: Tabular container to summarize
            
        Returns:
            Dict of summary statistics
        """
        rows = self.get_all_rows(df)
        numeric_cols = ['task_hours', 'idle_hours', 'social_media_usage', 
                       'break_frequency', 'tasks_completed']
        
        columns_found = list(df.columns) if hasattr(df, 'columns') else numeric_cols
        
        stats = {
            'total_rows': len(rows),
            'columns_found': columns_found,
            'column_stats': {}
        }
        
        for col in numeric_cols:
            values = [float(r.get(col, 0)) for r in rows if col in r]
            if values:
                mean_val = statistics.mean(values)
                std_val = statistics.stdev(values) if len(values) > 1 else 0.0
                stats['column_stats'][col] = {
                    'mean': round(mean_val, 2),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2),
                    'std': round(std_val, 2)
                }
            else:
                stats['column_stats'][col] = {
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'std': 0.0
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
