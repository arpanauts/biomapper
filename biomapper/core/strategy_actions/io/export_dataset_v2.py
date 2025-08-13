"""
Enhanced export dataset action with organized output structure.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.results_manager import ResultsPathManager, get_organized_output_path


class ExportResult(BaseModel):
    """Result of export dataset action."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ExportDatasetV2Params(BaseModel):
    """Enhanced parameters for EXPORT_DATASET_V2 action."""
    
    input_key: str = Field(..., description="Key in context containing data to export")
    
    # Output configuration
    output_filename: str = Field(
        ..., 
        description="Output filename (path will be auto-organized)"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Full output path (overrides organized structure if provided)"
    )
    
    # Organization settings
    use_organized_structure: bool = Field(
        default=True,
        description="Use organized folder structure (strategy/version/run)"
    )
    base_output_dir: Optional[str] = Field(
        default=None,
        description="Base directory for organized outputs (default: results/Data_Harmonization)"
    )
    
    # Export settings
    format: str = Field(
        default="tsv", 
        description="Export format: tsv, csv, json, xlsx, parquet"
    )
    columns: Optional[list[str]] = Field(
        default=None, 
        description="Specific columns to export"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata comment in file (if format supports)"
    )
    compression: Optional[str] = Field(
        default=None,
        description="Compression type: gzip, bz2, xz, zip"
    )
    
    # Additional options
    append_timestamp: bool = Field(
        default=False,
        description="Append timestamp to filename"
    )
    create_summary: bool = Field(
        default=True,
        description="Create summary statistics file alongside export"
    )


@register_action("EXPORT_DATASET_V2")
class ExportDatasetV2Action(TypedStrategyAction[ExportDatasetV2Params, ExportResult]):
    """Enhanced export with organized output structure matching Google Drive."""
    
    def get_params_model(self) -> type[ExportDatasetV2Params]:
        return ExportDatasetV2Params
    
    def get_result_model(self) -> type[ExportResult]:
        return ExportResult
    
    async def execute_typed(
        self, params: ExportDatasetV2Params, context: Dict[str, Any]
    ) -> ExportResult:
        """Export dataset with organized structure."""
        try:
            # Get data from context
            if params.input_key not in context.get("datasets", {}):
                return ExportResult(
                    success=False,
                    error=f"Dataset '{params.input_key}' not found in context"
                )
            
            data = context["datasets"][params.input_key]
            
            # Convert to DataFrame if needed
            if not isinstance(data, pd.DataFrame):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Filter columns if specified
            if params.columns:
                df = df[params.columns]
            
            # Determine output path
            output_path = self._get_output_path(params, context)
            
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata as comment if supported
            if params.include_metadata:
                metadata = self._generate_metadata(context, df)
            else:
                metadata = None
            
            # Export based on format
            self._export_dataframe(df, output_path, params.format, params.compression, metadata)
            
            # Create summary if requested
            summary_path = None
            if params.create_summary:
                summary_path = self._create_summary(df, output_path)
            
            # Update context with output file info
            if "output_files" not in context:
                context["output_files"] = {}
            context["output_files"][params.input_key] = str(output_path)
            
            if summary_path:
                context["output_files"][f"{params.input_key}_summary"] = str(summary_path)
            
            # Add organized structure info to context
            if params.use_organized_structure and "organized_output_path" in context:
                result_data = {
                    "exported_path": str(output_path),
                    "organized_structure": context.get("organized_structure"),
                    "row_count": len(df),
                    "column_count": len(df.columns),
                }
            else:
                result_data = {
                    "exported_path": str(output_path),
                    "row_count": len(df),
                    "column_count": len(df.columns),
                }
            
            if summary_path:
                result_data["summary_path"] = str(summary_path)
            
            return ExportResult(success=True, data=result_data)
            
        except Exception as e:
            return ExportResult(success=False, error=f"Export failed: {str(e)}")
    
    def _get_output_path(self, params: ExportDatasetV2Params, context: Dict[str, Any]) -> Path:
        """Determine the output path based on parameters and context."""
        
        # If explicit path provided, use it
        if params.output_path:
            return Path(params.output_path)
        
        # Build filename
        filename = params.output_filename
        if params.append_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = filename.rsplit(".", 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{filename}_{timestamp}"
        
        # Use organized structure
        if params.use_organized_structure:
            # Check if context already has organized path
            if "organized_output_path" in context:
                base_path = Path(context["organized_output_path"])
            else:
                # Create organized path
                strategy_name = context.get("strategy_name", "unknown_strategy")
                strategy_metadata = context.get("strategy_metadata", {})
                version = strategy_metadata.get("version", "1.0.0")
                
                base_dir = params.base_output_dir or ResultsPathManager.LOCAL_RESULTS_BASE
                
                base_path = ResultsPathManager.get_organized_path(
                    strategy_name=strategy_name,
                    version=version,
                    base_dir=base_dir,
                    include_timestamp=True  # Use timestamped run folder
                )
                
                # Ensure directory exists
                ResultsPathManager.ensure_directory(base_path)
                
                # Update context for other actions to use
                context["organized_output_path"] = str(base_path)
            
            return base_path / filename
        
        # Fallback to simple output
        base_dir = params.base_output_dir or "/tmp/biomapper/output"
        return Path(base_dir) / filename
    
    def _export_dataframe(
        self, 
        df: pd.DataFrame, 
        output_path: Path, 
        format: str,
        compression: Optional[str],
        metadata: Optional[str]
    ):
        """Export DataFrame to specified format."""
        
        # Add compression suffix if needed
        if compression:
            compression_suffixes = {
                "gzip": ".gz",
                "bz2": ".bz2", 
                "xz": ".xz",
                "zip": ".zip"
            }
            if not str(output_path).endswith(compression_suffixes.get(compression, "")):
                output_path = Path(str(output_path) + compression_suffixes[compression])
        
        # Export based on format
        if format == "tsv":
            # Write with metadata comment if provided
            if metadata:
                with open(output_path, 'w') as f:
                    for line in metadata.split('\n'):
                        f.write(f"# {line}\n")
                    df.to_csv(f, sep="\t", index=False)
            else:
                df.to_csv(output_path, sep="\t", index=False, compression=compression)
                
        elif format == "csv":
            if metadata:
                with open(output_path, 'w') as f:
                    for line in metadata.split('\n'):
                        f.write(f"# {line}\n")
                    df.to_csv(f, index=False)
            else:
                df.to_csv(output_path, index=False, compression=compression)
                
        elif format == "json":
            df.to_json(output_path, orient="records", indent=2, compression=compression)
            
        elif format == "xlsx":
            df.to_excel(output_path, index=False)
            
        elif format == "parquet":
            df.to_parquet(output_path, compression=compression)
            
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_metadata(self, context: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate metadata comment for the file."""
        metadata_lines = []
        
        # Add strategy info
        strategy_name = context.get("strategy_name", "unknown")
        strategy_metadata = context.get("strategy_metadata", {})
        version = strategy_metadata.get("version", "1.0.0")
        
        metadata_lines.append(f"Strategy: {strategy_name} v{version}")
        metadata_lines.append(f"Generated: {datetime.now().isoformat()}")
        metadata_lines.append(f"Rows: {len(df)}")
        metadata_lines.append(f"Columns: {', '.join(df.columns)}")
        
        # Add organized structure info if available
        if "organized_structure" in context:
            structure = context["organized_structure"]
            metadata_lines.append(f"Organization: {structure.get('strategy')}/{structure.get('version')}")
        
        return "\n".join(metadata_lines)
    
    def _create_summary(self, df: pd.DataFrame, output_path: Path) -> Path:
        """Create summary statistics file."""
        summary_path = output_path.parent / f"{output_path.stem}_summary.txt"
        
        with open(summary_path, 'w') as f:
            f.write(f"Dataset Summary\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"File: {output_path.name}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n\n")
            
            f.write("Columns:\n")
            for col in df.columns:
                dtype = str(df[col].dtype)
                null_count = df[col].isna().sum()
                unique_count = df[col].nunique()
                f.write(f"  - {col}: {dtype}, {unique_count} unique, {null_count} nulls\n")
            
            f.write("\n")
            
            # Add numeric column statistics
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                f.write("Numeric Column Statistics:\n")
                for col in numeric_cols:
                    f.write(f"\n{col}:\n")
                    f.write(f"  Mean: {df[col].mean():.4f}\n")
                    f.write(f"  Std:  {df[col].std():.4f}\n")
                    f.write(f"  Min:  {df[col].min():.4f}\n")
                    f.write(f"  Max:  {df[col].max():.4f}\n")
        
        return summary_path