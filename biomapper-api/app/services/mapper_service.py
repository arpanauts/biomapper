"""
Service for mapping operations with Biomapper.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

import pandas as pd
from fastapi import HTTPException, status

# Mock implementation for testing
# from biomapper import MetaboliteNameMapper

# This is a placeholder for testing the UI without the full biomapper package
class MockMetaboliteNameMapper:
    """Mock mapper for testing the UI without the biomapper package."""
    
    def __init__(self):
        pass
        
    def map_single_name(self, name, **kwargs):
        """Return mock mapping results for testing."""
        return {
            "query": name,
            "matches": [
                {"id": "CHEBI:12345", "name": name, "score": 0.95},
                {"id": "HMDB:54321", "name": f"{name} derivative", "score": 0.85},
            ],
            "source": "mock_mapper"
        }
    
    def map_dataframe(self, df, id_col, **kwargs):
        """Return mock dataframe mapping results."""
        results = []
        for name in df[id_col]:
            results.append(self.map_single_name(name))
        return results

from app.core.config import settings
from app.core.session import Session
from app.models.job import Job
from app.models.mapping import MappingStatus


class MapperService:
    """Service for mapping operations with Biomapper."""
    
    def __init__(self):
        # Store jobs in memory (in production would use a persistent store)
        self.jobs: Dict[str, Job] = {}
        # Initialize the mock mapper instance
        self.mapper = MockMetaboliteNameMapper()
        
    async def create_job(
        self, 
        session: Session, 
        id_columns: List[str], 
        target_ontologies: List[str],
        options: Optional[Dict[str, Any]] = None
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
            df = pd.read_csv(session.file_path, nrows=0)
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
            }
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
            
            # Read CSV
            df = pd.read_csv(file_path)
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
                    sub_progress = progress + ((i / len(unique_values)) * (100 / len(id_columns)))
                    job.update_status(MappingStatus.PROCESSING, progress=sub_progress)
                    
                    # Map the value
                    try:
                        # For each target ontology, generate a mapping
                        result = {}
                        for ontology in target_ontologies:
                            mapping_result = self.mapper.map_single_name(
                                value, target_type=ontology
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
                        result = results_by_column[column].get(value, {}).get(ontology, None)
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
                }
            )
            
        except Exception as e:
            # Update job with error
            job.update_status(
                MappingStatus.FAILED,
                error=str(e)
            )
    
    def _calculate_mapping_stats(
        self, 
        original_df: pd.DataFrame, 
        result_df: pd.DataFrame,
        id_columns: List[str],
        target_ontologies: List[str]
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
                "by_ontology": {}
            }
            
            for ontology in target_ontologies:
                mapped_column = f"{column}_{ontology}"
                mapped_count_in_column = result_df[mapped_column].notna().sum()
                
                column_stats[column]["by_ontology"][ontology] = {
                    "mapped_count": mapped_count_in_column,
                    "mapping_rate": mapped_count_in_column / original_df[column].count() if original_df[column].count() > 0 else 0
                }
                
                mapped_count += mapped_count_in_column
        
        # Avoid division by zero
        denominator = sum(original_df[column].count() for column in id_columns) * len(target_ontologies)
        mapping_rate = mapped_count / denominator if denominator > 0 else 0
        
        return {
            "total_records": total_records,
            "mapped_records": mapped_count,
            "mapping_rate": mapping_rate,
            "ontologies_used": target_ontologies,
            "column_stats": column_stats
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
            # Read preview rows
            df = pd.read_csv(output_path, nrows=limit)
            
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
