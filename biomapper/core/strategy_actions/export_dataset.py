"""Export dataset action for saving results to various formats."""
from typing import Dict, Any
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.action_results import ActionResult


class ExportDatasetParams(BaseModel):
    """Parameters for EXPORT_DATASET action."""

    input_key: str = Field(..., description="Key in context containing data to export")
    output_path: str = Field(..., description="Path where to save the exported file")
    format: str = Field(
        default="tsv", description="Export format: tsv, csv, json, xlsx"
    )
    columns: list[str] | None = Field(
        default=None, description="Specific columns to export"
    )


@register_action("EXPORT_DATASET")
class ExportDatasetAction(TypedStrategyAction[ExportDatasetParams, ActionResult]):
    """Export dataset to file in specified format."""

    def get_params_model(self) -> type[ExportDatasetParams]:
        return ExportDatasetParams

    async def execute_typed(
        self, params: ExportDatasetParams, context: Dict[str, Any]
    ) -> ActionResult:
        """Export dataset from context to file."""
        try:
            # Get data from context
            if params.input_key not in context.get("datasets", {}):
                return ActionResult(
                    success=False,
                    error=f"Dataset '{params.input_key}' not found in context",
                )

            data = context["datasets"][params.input_key]

            # Convert to DataFrame if needed
            if not isinstance(data, pd.DataFrame):
                df = pd.DataFrame(data)
            else:
                df = data

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
            if "output_files" not in context:
                context["output_files"] = {}
            context["output_files"][params.input_key] = str(output_path)

            return ActionResult(
                success=True,
                data={"exported_path": str(output_path), "row_count": len(df)},
            )

        except Exception as e:
            return ActionResult(success=False, error=f"Export failed: {str(e)}")
