"""
Template for creating new biomapper strategy actions.
This template follows all established parameter naming standards.

Copy this file and modify for your specific action implementation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.base import ActionResult
from biomapper.core.standards.parameter_validator import validate_action_params
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class MyActionParams(BaseModel):
    """
    Parameters for MyAction.
    
    IMPORTANT: All parameter names MUST follow the standard naming conventions:
    - Use 'input_key' for primary input dataset
    - Use 'output_key' for primary output dataset
    - Use 'file_path' for input files
    - Use 'output_path' for output files
    - See /home/ubuntu/biomapper/standards/PARAMETER_NAMING_STANDARD.md for full list
    """
    
    # === DATASET KEYS (for accessing context data) ===
    # Standard: input_key, output_key, source_key, target_key
    input_key: str = Field(
        ...,
        description="Key to retrieve input dataset from context"
    )
    
    output_key: str = Field(
        ...,
        description="Key to store output dataset in context"
    )
    
    # Optional secondary inputs (use numbered suffixes)
    input_key_2: Optional[str] = Field(
        None,
        description="Optional secondary input dataset key"
    )
    
    # === FILE PATHS ===
    # Standard: file_path (input), output_path (output)
    file_path: Optional[str] = Field(
        None,
        description="Path to input file (if loading from file)"
    )
    
    output_path: Optional[str] = Field(
        None,
        description="Path to save output file (if exporting)"
    )
    
    # === COLUMN NAMES ===
    # Standard: identifier_column, merge_column, value_column
    identifier_column: str = Field(
        "id",
        description="Column containing unique identifiers"
    )
    
    merge_column: Optional[str] = Field(
        None,
        description="Column to use for merging/joining datasets"
    )
    
    # === PROCESSING PARAMETERS ===
    # Standard: threshold, max_limit, min_limit, batch_size
    threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for matching"
    )
    
    batch_size: int = Field(
        1000,
        gt=0,
        description="Number of records to process per batch"
    )
    
    # === BOOLEAN FLAGS ===
    # Standard: case_sensitive, include_header, overwrite, verbose, strict
    case_sensitive: bool = Field(
        False,
        description="Whether to consider case in string comparisons"
    )
    
    verbose: bool = Field(
        False,
        description="Enable detailed logging output"
    )
    
    strict: bool = Field(
        False,
        description="Fail on warnings (strict validation mode)"
    )
    
    # === API/SERVICE PARAMETERS (if applicable) ===
    # Standard: api_key, api_endpoint, request_timeout, max_retries
    api_endpoint: Optional[str] = Field(
        None,
        description="External API endpoint URL"
    )
    
    request_timeout: int = Field(
        30,
        gt=0,
        description="API request timeout in seconds"
    )
    
    max_retries: int = Field(
        3,
        ge=0,
        description="Maximum number of retry attempts"
    )
    
    # === FORMAT PARAMETERS ===
    # Standard: file_format, delimiter, encoding
    file_format: str = Field(
        "csv",
        description="Output file format (csv, tsv, json, parquet)"
    )
    
    delimiter: str = Field(
        ",",
        description="Field delimiter for CSV/TSV files"
    )
    
    encoding: str = Field(
        "utf-8",
        description="Text encoding for file I/O"
    )
    
    @field_validator('file_format')
    def validate_file_format(cls, v):
        """Validate file format is supported."""
        valid_formats = {'csv', 'tsv', 'json', 'parquet', 'excel'}
        if v.lower() not in valid_formats:
            raise ValueError(f"File format must be one of {valid_formats}")
        return v.lower()
    
    @field_validator('file_path', 'output_path')
    def validate_paths(cls, v):
        """Validate file paths."""
        if v and '..' in v:
            raise ValueError("Path traversal not allowed")
        return v
    
    class Config:
        """Pydantic config."""
        # Allow extra fields for backward compatibility during migration
        extra = "forbid"  # Change to "allow" if migrating from old parameters
        
        # Example of handling deprecated parameters:
        # @root_validator(pre=True)
        # def migrate_old_params(cls, values):
        #     """Migrate old parameter names to new standards."""
        #     if 'dataset_key' in values:
        #         values['input_key'] = values.pop('dataset_key')
        #         logger.warning("Parameter 'dataset_key' is deprecated, use 'input_key'")
        #     return values


@register_action("MY_ACTION")  # Replace with your action name
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    """
    Template action implementation following parameter standards.
    
    This action demonstrates:
    - Standard parameter naming
    - Proper validation
    - Context data access patterns
    - Error handling
    - Performance considerations
    """
    
    def get_params_model(self) -> type[MyActionParams]:
        """Return the Pydantic model for parameters."""
        return MyActionParams
    
    async def execute_typed(
        self, 
        params: MyActionParams, 
        context: Dict[str, Any]
    ) -> ActionResult:
        """
        Execute the action with typed parameters.
        
        Args:
            params: Validated parameters following naming standards
            context: Execution context containing datasets
            
        Returns:
            ActionResult indicating success/failure
        """
        try:
            # Validate parameters against standards (optional but recommended)
            if params.strict:
                validator = validate_action_params(
                    params.dict(), 
                    action_name="MY_ACTION",
                    strict=True
                )
            
            # === STEP 1: Retrieve input data from context ===
            if params.input_key not in context.get('datasets', {}):
                return ActionResult(
                    success=False,
                    message=f"Input dataset '{params.input_key}' not found in context"
                )
            
            input_df = context['datasets'][params.input_key]
            
            # Optionally load from file if specified
            if params.file_path and not input_df:
                input_df = self._load_file(params.file_path, params)
            
            # Get secondary input if specified
            secondary_df = None
            if params.input_key_2:
                secondary_df = context['datasets'].get(params.input_key_2)
            
            # === STEP 2: Process the data ===
            if params.verbose:
                logger.info(f"Processing {len(input_df)} records with threshold {params.threshold}")
            
            # Example processing (replace with your logic)
            result_df = self._process_data(
                input_df,
                secondary_df,
                params
            )
            
            # === STEP 3: Store output in context ===
            context['datasets'][params.output_key] = result_df
            
            # Optionally save to file
            if params.output_path:
                self._save_file(result_df, params.output_path, params)
            
            # === STEP 4: Update statistics ===
            if 'statistics' not in context:
                context['statistics'] = {}
            
            context['statistics'][params.output_key] = {
                'total_records': len(result_df),
                'columns': list(result_df.columns),
                'processing_params': {
                    'threshold': params.threshold,
                    'case_sensitive': params.case_sensitive,
                    'batch_size': params.batch_size
                }
            }
            
            # === STEP 5: Return success ===
            return ActionResult(
                success=True,
                message=f"Successfully processed {len(result_df)} records",
                data={
                    'input_count': len(input_df),
                    'output_count': len(result_df),
                    'columns': list(result_df.columns)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in MY_ACTION: {str(e)}", exc_info=True)
            return ActionResult(
                success=False,
                message=f"Action failed: {str(e)}",
                error=str(e)
            )
    
    def _process_data(
        self, 
        input_df: pd.DataFrame,
        secondary_df: Optional[pd.DataFrame],
        params: MyActionParams
    ) -> pd.DataFrame:
        """
        Process the input data (implement your logic here).
        
        Args:
            input_df: Primary input dataframe
            secondary_df: Optional secondary input
            params: Action parameters
            
        Returns:
            Processed dataframe
        """
        # Example implementation - replace with your logic
        result_df = input_df.copy()
        
        # Apply case sensitivity if needed
        if not params.case_sensitive and params.identifier_column in result_df.columns:
            if result_df[params.identifier_column].dtype == 'object':
                result_df[params.identifier_column] = result_df[params.identifier_column].str.upper()
        
        # Apply threshold filtering (example)
        if 'score' in result_df.columns:
            result_df = result_df[result_df['score'] >= params.threshold]
        
        # Merge with secondary data if provided
        if secondary_df is not None and params.merge_column:
            result_df = pd.merge(
                result_df,
                secondary_df,
                on=params.merge_column,
                how='left'
            )
        
        # Process in batches if large dataset
        if len(result_df) > params.batch_size * 10:
            # Process in chunks for memory efficiency
            chunks = []
            for i in range(0, len(result_df), params.batch_size):
                chunk = result_df.iloc[i:i+params.batch_size]
                # Process chunk
                chunks.append(chunk)
            result_df = pd.concat(chunks, ignore_index=True)
        
        return result_df
    
    def _load_file(self, file_path: str, params: MyActionParams) -> pd.DataFrame:
        """Load data from file based on format."""
        if params.file_format == 'csv':
            return pd.read_csv(
                file_path,
                delimiter=params.delimiter,
                encoding=params.encoding
            )
        elif params.file_format == 'tsv':
            return pd.read_csv(
                file_path,
                delimiter='\t',
                encoding=params.encoding
            )
        elif params.file_format == 'json':
            return pd.read_json(file_path)
        elif params.file_format == 'parquet':
            return pd.read_parquet(file_path)
        elif params.file_format == 'excel':
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {params.file_format}")
    
    def _save_file(self, df: pd.DataFrame, file_path: str, params: MyActionParams):
        """Save dataframe to file based on format."""
        if params.file_format == 'csv':
            df.to_csv(
                file_path,
                sep=params.delimiter,
                encoding=params.encoding,
                index=False
            )
        elif params.file_format == 'tsv':
            df.to_csv(
                file_path,
                sep='\t',
                encoding=params.encoding,
                index=False
            )
        elif params.file_format == 'json':
            df.to_json(file_path, orient='records', indent=2)
        elif params.file_format == 'parquet':
            df.to_parquet(file_path, index=False)
        elif params.file_format == 'excel':
            df.to_excel(file_path, index=False)


# === USAGE EXAMPLE ===
"""
To use this template:

1. Copy this file to your action location:
   cp templates/action_template.py biomapper/core/strategy_actions/my_category/my_action.py

2. Replace:
   - "MY_ACTION" with your action name
   - "MyAction" with your class name
   - "MyActionParams" with your params class name

3. Modify parameters:
   - Remove parameters you don't need
   - Add action-specific parameters (following standards)
   - Update descriptions

4. Implement _process_data() with your business logic

5. Create tests using templates/test_action_template.py

6. Register in YAML strategy:
   steps:
     - name: my_step
       action:
         type: MY_ACTION
         params:
           input_key: source_data
           output_key: processed_data
           threshold: 0.9
           case_sensitive: false
"""