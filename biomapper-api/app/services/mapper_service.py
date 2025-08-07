"""
Service for mapping operations with Biomapper.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError
from biomapper.utils.io_utils import load_tabular_file
from biomapper.core.models.strategy import Strategy
from biomapper.core.minimal_strategy_service import MinimalStrategyService

# BiomapperContext import removed - using dict directly
from app.core.config import settings
from app.core.session import Session
from app.models.persistence import Job
from app.models.mapping import MappingStatus
# Removed database and legacy imports

logger = logging.getLogger(__name__)


class MapperService:
    """Service for mapping operations with Biomapper."""

    def __init__(self):
        logger.info("Initializing MapperService...")

        # Store jobs in memory (in production would use a persistent store)
        self.jobs: Dict[str, Job] = {}

        # Initialize the mock mapper instance
        try:
            self.mapper_service = MapperServiceForStrategies()
        except Exception as e:
            logger.error(
                f"Failed to create MapperServiceForStrategies: {e}", exc_info=True
            )
            raise

        # No longer using relationship executor
        logger.info("MapperService initialized.")

    async def create_job(
        self,
        session: Session,
        id_columns: List[str],
        target_ontologies: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """
        Create a new mapping job.

        Args:
            session: The user session
            id_columns: Columns containing identifiers to map
            target_ontologies: Target ontologies to map to
            options: Additional mapping options

        Returns:
            Created job

        Raises:
            HTTPException: If session has no file or columns are invalid
        """
        if not session.file_path or not session.file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No CSV file found for this session",
            )

        # Validate columns exist in the file
        try:
            # Use load_tabular_file to properly handle comments
            df = load_tabular_file(session.file_path, nrows=0, comment="#")
            file_columns = df.columns.tolist()

            invalid_columns = [col for col in id_columns if col not in file_columns]
            if invalid_columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Columns not found in CSV: {', '.join(invalid_columns)}",
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading CSV file: {str(e)}",
            )

        # Create job
        job = Job(
            session_id=session.session_id,
            result={
                "id_columns": id_columns,
                "target_ontologies": target_ontologies,
                "options": options or {},
                "file_path": str(session.file_path),
                "output_path": None,
            },
        )

        # Store job
        self.jobs[job.job_id] = job

        # Start background processing
        asyncio.create_task(self.process_mapping_job(job.job_id))

        return job

    async def process_mapping_job(self, job_id: str) -> None:
        """
        Process a mapping job (runs asynchronously).

        Args:
            job_id: ID of the job to process
        """
        job = self.jobs.get(job_id)
        if not job:
            return

        # Update status to processing
        job.update_status(MappingStatus.PROCESSING, progress=0.0)

        try:
            # Retrieve job parameters
            file_path = Path(job.result["file_path"])
            id_columns = job.result["id_columns"]
            target_ontologies = job.result["target_ontologies"]
            options = job.result["options"]

            # Read CSV with comment handling
            df = load_tabular_file(file_path, comment="#")
            total_rows = len(df)

            # Process each column
            results_by_column = {}

            for idx, column in enumerate(id_columns):
                # Update progress
                progress = (idx / len(id_columns)) * 100
                job.update_status(MappingStatus.PROCESSING, progress=progress)

                # Get unique values to map
                unique_values = df[column].dropna().unique().tolist()

                # Map values using Biomapper
                mapped_values = {}
                for i, value in enumerate(unique_values):
                    # Update sub-progress
                    sub_progress = progress + (
                        (i / len(unique_values)) * (100 / len(id_columns))
                    )
                    job.update_status(MappingStatus.PROCESSING, progress=sub_progress)

                    # Map the value
                    try:
                        # For each target ontology, generate a mapping
                        result = {}
                        for ontology in target_ontologies:
                            mapping_result = await self.mapper_service.execute_strategy(
                                "composite_id_split",
                                {"value": value, "ontology": ontology},
                            )
                            if mapping_result:
                                result[ontology] = mapping_result

                        mapped_values[value] = result
                    except Exception as e:
                        # Log error but continue with next value
                        print(f"Error mapping value '{value}': {str(e)}")
                        mapped_values[value] = {"error": str(e)}

                # Store results for this column
                results_by_column[column] = mapped_values

            # Generate output file
            # Create a copy of the original dataframe
            result_df = df.copy()

            # Add mapped columns
            for column in id_columns:
                for ontology in target_ontologies:
                    new_column_name = f"{column}_{ontology}"

                    # Apply mapping to create new column
                    def get_mapping(value):
                        if pd.isna(value):
                            return None
                        result = (
                            results_by_column[column].get(value, {}).get(ontology, None)
                        )
                        return result

                    result_df[new_column_name] = df[column].apply(get_mapping)

            # Save result
            output_filename = f"mapping_result_{job_id}.csv"
            output_path = settings.MAPPING_RESULTS_DIR / output_filename
            result_df.to_csv(output_path, index=False)

            # Calculate stats
            mapping_stats = self._calculate_mapping_stats(
                df, result_df, id_columns, target_ontologies
            )

            # Update job with result
            job.update_status(
                MappingStatus.COMPLETED,
                progress=100.0,
                result={
                    **job.result,
                    "output_path": str(output_path),
                    "stats": mapping_stats,
                },
            )

        except Exception as e:
            # Update job with error
            job.update_status(MappingStatus.FAILED, error=str(e))

    def _calculate_mapping_stats(
        self,
        original_df: pd.DataFrame,
        result_df: pd.DataFrame,
        id_columns: List[str],
        target_ontologies: List[str],
    ) -> Dict[str, Any]:
        """
        Calculate mapping statistics.

        Args:
            original_df: Original dataframe
            result_df: Mapped dataframe
            id_columns: Columns containing identifiers
            target_ontologies: Target ontologies mapped to

        Returns:
            Mapping statistics
        """
        total_records = len(original_df)
        mapped_count = 0
        column_stats = {}

        for column in id_columns:
            column_stats[column] = {
                "total_values": original_df[column].count(),
                "unique_values": original_df[column].nunique(),
                "by_ontology": {},
            }

            for ontology in target_ontologies:
                mapped_column = f"{column}_{ontology}"
                mapped_count_in_column = result_df[mapped_column].notna().sum()

                column_stats[column]["by_ontology"][ontology] = {
                    "mapped_count": mapped_count_in_column,
                    "mapping_rate": mapped_count_in_column / original_df[column].count()
                    if original_df[column].count() > 0
                    else 0,
                }

                mapped_count += mapped_count_in_column

        # Avoid division by zero
        denominator = sum(original_df[column].count() for column in id_columns) * len(
            target_ontologies
        )
        mapping_rate = mapped_count / denominator if denominator > 0 else 0

        return {
            "total_records": total_records,
            "mapped_records": mapped_count,
            "mapping_rate": mapping_rate,
            "ontologies_used": target_ontologies,
            "column_stats": column_stats,
        }

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job if found, None otherwise
        """
        return self.jobs.get(job_id)

    def get_job_results_preview(self, job_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a preview of the job results.

        Args:
            job_id: Job ID
            limit: Maximum number of rows to return

        Returns:
            Preview data

        Raises:
            HTTPException: If job not found or not completed
        """
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found",
            )

        if job.status != MappingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not completed yet. Current status: {job.status}",
            )

        output_path = job.result.get("output_path")
        if not output_path or not os.path.exists(output_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job result file not found",
            )

        try:
            # Read preview rows with comment handling
            df = load_tabular_file(output_path, nrows=limit, comment="#")

            # Convert to list of dicts
            rows = df.replace({pd.NA: None}).to_dict(orient="records")

            return {
                "preview": rows,
                "columns": df.columns.tolist(),
                "stats": job.result.get("stats", {}),
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading result file: {str(e)}",
            )

    async def get_endpoints(self) -> List[Any]:
        """Return empty list since we're not using database endpoints anymore."""
        return []

    async def execute_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a mapping strategy by name.

        Args:
            strategy_name: Name of the strategy to execute.
            source_endpoint_name: The name of the source data endpoint.
            target_endpoint_name: The name of the target data endpoint.
            input_identifiers: A list of identifiers to be mapped.
            context: Optional execution context for the strategy.

        Returns:
            Dictionary containing the strategy execution results.

        Raises:
            KeyError: If the strategy is not found.
            Exception: If the strategy execution fails.
        """
        return await self.mapper_service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            context=context,
        )


class MapperServiceForStrategies:
    """Service for loading and executing mapping strategies."""

    def __init__(self):
        """
        Initializes the service by loading strategies using MinimalStrategyService.
        """
        print("DEBUG: MapperServiceForStrategies.__init__ starting", flush=True)
        logger.info("Initializing MapperServiceForStrategies...")

        try:
            print("DEBUG: About to initialize MinimalStrategyService", flush=True)
            self.strategy_service = MinimalStrategyService(settings.STRATEGIES_DIR)
            self.strategies = self.strategy_service.strategies
            print(f"DEBUG: Loaded {len(self.strategies)} strategies", flush=True)

            logger.info("MinimalStrategyService initialized successfully.")

        except Exception as e:
            print(
                f"DEBUG: Failed to initialize MapperServiceForStrategies: {type(e).__name__}: {str(e)}",
                flush=True,
            )
            logger.exception(f"Failed to initialize MapperServiceForStrategies: {e}")
            raise
        print("DEBUG: MapperServiceForStrategies.__init__ completed", flush=True)

    def _load_strategies(self) -> Dict[str, Strategy]:
        """
        Scans the strategies directory, loads each YAML file, and validates it against the Strategy model.

        Returns:
            A dictionary mapping strategy names to Strategy objects.
        """
        strategies = {}
        strategies_dir = settings.STRATEGIES_DIR

        if not strategies_dir.exists():
            logger.warning(f"Strategies directory not found: {strategies_dir}")
            return strategies

        logger.info(f"Loading strategies from: {strategies_dir}")

        for file_path in strategies_dir.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    strategy_data = yaml.safe_load(f)
                    if not strategy_data:
                        logger.warning(f"Skipping empty YAML file: {file_path.name}")
                        continue

                    strategy = Strategy(**strategy_data)
                    if strategy.name in strategies:
                        logger.warning(
                            f"Duplicate strategy name '{strategy.name}' found in {file_path.name}. Overwriting."
                        )
                    strategies[strategy.name] = strategy
                    logger.info(
                        f"Successfully loaded strategy: '{strategy.name}' from {file_path.name}"
                    )
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML file {file_path.name}: {e}")
            except ValidationError as e:
                logger.error(f"Invalid strategy format in {file_path.name}: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error loading strategy from {file_path.name}: {e}",
                    exc_info=True,
                )

        if not strategies:
            logger.warning("No strategies were loaded.")

        return strategies

    async def execute_strategy(
        self,
        strategy_name: str,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a named strategy with the given context using MinimalStrategyService.
        """
        if not self.strategies.get(strategy_name):
            raise HTTPException(
                status_code=404, detail=f"Strategy '{strategy_name}' not found."
            )

        try:
            logger.info(f"Executing strategy '{strategy_name}' with minimal service...")

            # Execute the strategy using MinimalStrategyService
            final_context = await self.strategy_service.execute_strategy(
                strategy_name=strategy_name,
                source_endpoint_name=source_endpoint_name,
                target_endpoint_name=target_endpoint_name,
                input_identifiers=input_identifiers,
                context=context,
            )

            logger.info(f"Successfully executed strategy '{strategy_name}'.")
            return final_context

        except Exception as e:
            logger.exception(
                f"An error occurred during execution of strategy '{strategy_name}': {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"An internal error occurred while executing the strategy: {e}",
            )

    async def get_endpoints(self) -> List[Any]:
        """Return empty list since we're not using database endpoints anymore."""
        logger.info("Returning empty endpoints list (database-free mode)")
        return []
