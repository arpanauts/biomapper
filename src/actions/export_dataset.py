"""Export dataset action for saving results to various formats."""
from typing import Any
from pathlib import Path
import pandas as pd
from pydantic import Field
from core.standards import ActionParamsBase, FlexibleBaseModel

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext
# Don't use the complex ActionResult from models
# from core.models.action_results import ActionResult


class ExportDatasetParams(ActionParamsBase):
    """Parameters for EXPORT_DATASET action."""

    input_key: str = Field(..., description="Key in context containing data to export")
    output_path: str = Field(..., description="Path where to save the exported file")
    format: str = Field(
        default="tsv", description="Export format: tsv, csv, json, xlsx"
    )
    columns: list[str] | None = Field(
        default=None, description="Specific columns to export"
    )


class ActionResult(FlexibleBaseModel):
    """Simple action result for export operations."""
    
    success: bool = Field(..., description="Whether the action succeeded")
    message: str | None = Field(default=None, description="Optional message")
    error: str | None = Field(default=None, description="Error message if failed")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional data")


@register_action("EXPORT_DATASET")
class ExportDatasetAction(TypedStrategyAction[ExportDatasetParams, ActionResult]):
    """Export dataset to file in specified format."""

    def get_params_model(self) -> type[ExportDatasetParams]:
        return ExportDatasetParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    async def execute_typed(
        self, params: ExportDatasetParams, context: Any, **kwargs
    ) -> ActionResult:
        """Export dataset from context to file."""
        try:
            # Wrap context for uniform access
            ctx = UniversalContext.wrap(context)
            
            # Get data from context
            datasets = ctx.get_datasets()
            if params.input_key not in datasets:
                return ActionResult(
                    success=False,
                    error=f"Dataset '{params.input_key}' not found in context",
                )

            data = datasets[params.input_key]

            # Convert to DataFrame if needed
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, list):
                # List of dicts from other actions
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame(data)

            # Filter columns if specified
            if params.columns:
                df = df[params.columns]

            # Export based on format
            output_path = Path(params.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if params.format == "tsv":
                df.to_csv(output_path, sep="\t", index=False)
            elif params.format == "csv":
                df.to_csv(output_path, index=False)
            elif params.format == "json":
                df.to_json(output_path, orient="records", indent=2)
            elif params.format == "xlsx":
                df.to_excel(output_path, index=False)
            else:
                return ActionResult(
                    success=False, error=f"Unsupported format: {params.format}"
                )

            # Update context with output file info
            output_files = ctx.get("output_files", {})
            if not isinstance(output_files, dict):
                output_files = {}
            output_files[params.input_key] = str(output_path)
            ctx.set("output_files", output_files)

            return ActionResult(
                success=True,
                data={"exported_path": str(output_path), "row_count": len(df)},
            )

        except Exception as e:
            return ActionResult(success=False, error=f"Export failed: {str(e)}")
