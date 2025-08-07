"""Data validation utilities for pipeline."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates input data files for the pipeline."""

    def validate_file(
        self, file_path: Path, required_columns: List[str], min_records: int = 10
    ) -> Dict[str, Any]:
        """Validate a single data file."""
        results: Dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {},
        }

        try:
            # Load file
            if file_path.suffix == ".csv":
                df = pd.read_csv(file_path)
            elif file_path.suffix == ".tsv":
                df = pd.read_csv(file_path, sep="\t")
            else:
                results["valid"] = False
                results["errors"].append(f"Unsupported file type: {file_path.suffix}")
                return results

            # Check required columns
            missing_cols = set(required_columns) - set(df.columns)
            if missing_cols:
                results["valid"] = False
                results["errors"].append(f"Missing required columns: {missing_cols}")

            # Check minimum records
            if len(df) < min_records:
                results["warnings"].append(
                    f"File has only {len(df)} records (minimum: {min_records})"
                )

            # Collect statistics
            results["stats"] = {
                "rows": len(df),
                "columns": len(df.columns),
                "missing_values": df.isnull().sum().to_dict(),
            }

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Error reading file: {str(e)}")

        return results
