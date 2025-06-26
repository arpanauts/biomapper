"""
ResultsSaver: Generic strategy action to save data from context to files.

This action:
- Reads data from a specified context key
- Supports multiple data structures (list of dicts, pandas DataFrame)
- Saves to CSV or JSON format
- Handles file system errors gracefully
- Provides detailed logging and error messages
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Union
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import MappingExecutionError
from biomapper.db.models import Endpoint

logger = logging.getLogger(__name__)


@register_action("SAVE_RESULTS")
class ResultsSaver(BaseStrategyAction):
    """
    Generic action to save data from context to files in various formats.
    
    This action takes data from a specified context key and saves it to a file
    in either CSV or JSON format. It handles various data structures including
    lists of dictionaries and pandas DataFrames.
    
    Required parameters:
    - input_context_key: Key in context containing the data to save
    - output_directory: Directory path to save the file (supports env vars)
    - filename: Name of the output file
    - format: Output format ('csv' or 'json')
    
    Optional parameters:
    - create_summary: For CSV, also create a JSON summary file (default: False)
    - include_timestamp: Add timestamp to filename (default: False)
    - ensure_unique: Add suffix to prevent overwriting (default: False)
    
    Example usage in YAML:
    ```yaml
    - action_type: SAVE_RESULTS
      params:
        input_context_key: "mapping_results"
        output_directory: "${OUTPUT_DIR}/results"
        filename: "protein_mappings"
        format: "csv"
        create_summary: true
        include_timestamp: true
    ```
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session
        self.logger = logger
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the save results action.
        
        Args:
            current_identifiers: Current list of identifiers (passed through)
            current_ontology_type: Current ontology type (passed through)
            action_params: Action parameters including file settings
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Execution context containing data to save
            
        Returns:
            Result dictionary with file paths and statistics
        """
        # Validate required parameters
        input_key = action_params.get('input_context_key')
        if not input_key:
            raise ValueError("input_context_key is required for ResultsSaver")
        
        output_dir = action_params.get('output_directory')
        if not output_dir:
            raise ValueError("output_directory is required for ResultsSaver")
        
        filename = action_params.get('filename')
        if not filename:
            raise ValueError("filename is required for ResultsSaver")
        
        file_format = action_params.get('format', 'csv').lower()
        if file_format not in ['csv', 'json']:
            raise ValueError(f"Unsupported format: {file_format}. Must be 'csv' or 'json'")
        
        # Get optional parameters
        create_summary = action_params.get('create_summary', False)
        include_timestamp = action_params.get('include_timestamp', False)
        ensure_unique = action_params.get('ensure_unique', False)
        
        self.logger.info(f"Saving data from context key '{input_key}' as {file_format}")
        
        # Get data from context
        data = context.get(input_key)
        if data is None:
            self.logger.warning(f"No data found at context key '{input_key}'")
            return {
                'output_identifiers': current_identifiers,
                'output_ontology_type': current_ontology_type,
                'details': {
                    'status': 'no_data',
                    'message': f'No data found at context key {input_key}'
                }
            }
        
        try:
            # Resolve output directory (handle environment variables)
            resolved_dir = os.path.expandvars(output_dir)
            Path(resolved_dir).mkdir(parents=True, exist_ok=True)
            
            # Build filename with optional timestamp
            base_name = filename
            if include_timestamp:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_name = f"{filename}_{timestamp}"
            
            # Determine file extension
            extension = '.csv' if file_format == 'csv' else '.json'
            full_filename = f"{base_name}{extension}"
            
            # Handle unique filename requirement
            if ensure_unique:
                counter = 1
                while os.path.exists(os.path.join(resolved_dir, full_filename)):
                    full_filename = f"{base_name}_{counter}{extension}"
                    counter += 1
            
            file_path = os.path.join(resolved_dir, full_filename)
            
            # Save based on format
            if file_format == 'csv':
                saved_path, row_count = await self._save_as_csv(data, file_path)
                
                # Optionally create summary
                summary_path = None
                if create_summary:
                    summary_filename = f"{base_name}_summary.json"
                    summary_path = os.path.join(resolved_dir, summary_filename)
                    await self._create_summary(data, summary_path, saved_path, row_count)
                
                result_details = {
                    'status': 'success',
                    'format': 'csv',
                    'file_path': saved_path,
                    'rows_saved': row_count,
                    'summary_path': summary_path
                }
            else:  # JSON format
                saved_path, item_count = await self._save_as_json(data, file_path)
                result_details = {
                    'status': 'success',
                    'format': 'json',
                    'file_path': saved_path,
                    'items_saved': item_count
                }
            
            # Add saved file paths to context for downstream use
            context[f"{input_key}_saved_path"] = saved_path
            if file_format == 'csv' and create_summary and summary_path:
                context[f"{input_key}_summary_path"] = summary_path
            
            self.logger.info(f"Successfully saved data to: {saved_path}")
            
            return {
                'output_identifiers': current_identifiers,
                'output_ontology_type': current_ontology_type,
                'details': result_details
            }
            
        except PermissionError as e:
            error_msg = f"Permission denied writing to {output_dir}: {str(e)}"
            self.logger.error(error_msg)
            raise MappingExecutionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to save results: {str(e)}"
            self.logger.error(error_msg)
            raise MappingExecutionError(error_msg)
    
    async def _save_as_csv(self, data: Any, file_path: str) -> tuple[str, int]:
        """
        Save data as CSV file.
        
        Args:
            data: Data to save (DataFrame, list of dicts, or dict)
            file_path: Path to save the CSV file
            
        Returns:
            Tuple of (saved file path, number of rows)
        """
        # Convert to DataFrame if needed
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to convert dict to DataFrame
            try:
                df = pd.DataFrame([data])
            except ValueError:
                # If dict has lists as values, assume it's column-oriented
                df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type for CSV: {type(data)}")
        
        # Save to CSV
        df.to_csv(file_path, index=False)
        self.logger.debug(f"Saved {len(df)} rows to CSV: {file_path}")
        
        return file_path, len(df)
    
    async def _save_as_json(self, data: Any, file_path: str) -> tuple[str, int]:
        """
        Save data as JSON file.
        
        Args:
            data: Data to save
            file_path: Path to save the JSON file
            
        Returns:
            Tuple of (saved file path, number of items)
        """
        # Convert DataFrame to dict if needed
        if isinstance(data, pd.DataFrame):
            data_to_save = data.to_dict(orient='records')
            item_count = len(data)
        elif isinstance(data, list):
            data_to_save = data
            item_count = len(data)
        elif isinstance(data, dict):
            data_to_save = data
            # Count items based on structure
            if all(isinstance(v, list) for v in data.values()):
                # Column-oriented dict
                item_count = len(next(iter(data.values())))
            else:
                # Single item
                item_count = 1
        else:
            # Try to serialize as-is
            data_to_save = data
            item_count = 1 if not hasattr(data, '__len__') else len(data)
        
        # Save to JSON with pretty formatting
        with open(file_path, 'w') as f:
            json.dump(data_to_save, f, indent=2, default=str)
        
        self.logger.debug(f"Saved {item_count} items to JSON: {file_path}")
        
        return file_path, item_count
    
    async def _create_summary(self, data: Any, summary_path: str, data_path: str, row_count: int):
        """
        Create a JSON summary file for CSV data.
        
        Args:
            data: Original data
            summary_path: Path to save the summary
            data_path: Path where data was saved
            row_count: Number of rows saved
        """
        summary = {
            'created_at': datetime.now().isoformat(),
            'data_file': data_path,
            'format': 'csv',
            'statistics': {
                'total_rows': row_count
            }
        }
        
        # Add column information if data is DataFrame-like
        if isinstance(data, pd.DataFrame) or (isinstance(data, list) and data and isinstance(data[0], dict)):
            if isinstance(data, pd.DataFrame):
                df = data
            else:
                df = pd.DataFrame(data)
            
            summary['columns'] = list(df.columns)
            summary['statistics']['columns_count'] = len(df.columns)
            
            # Add basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary['numeric_statistics'] = {}
                for col in numeric_cols:
                    summary['numeric_statistics'][col] = {
                        'mean': float(df[col].mean()),
                        'min': float(df[col].min()),
                        'max': float(df[col].max()),
                        'null_count': int(df[col].isna().sum())
                    }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.debug(f"Created summary file: {summary_path}")