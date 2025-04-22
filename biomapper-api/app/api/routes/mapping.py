"""
API routes for mapping operations.
"""
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse

from app.api.deps import get_mapper_service, get_session
from app.core.session import Session
from app.models.mapping import (
    MappingJobCreate, 
    MappingJobResponse, 
    JobStatus, 
    MappingResults,
    MappingResultSummary,
    RelationshipMappingRequest,
    RelationshipMappingResponse,
    MappingResult
)
from app.services.mapper_service import MapperService

router = APIRouter()


@router.post("/jobs", response_model=MappingJobResponse)
async def create_mapping_job(
    job_config: MappingJobCreate,
    mapper_service: MapperService = Depends(get_mapper_service),
    session: Session = Depends(get_session),
) -> MappingJobResponse:
    """
    Create a new mapping job.
    
    Args:
        job_config: Mapping job configuration
        mapper_service: Mapper service dependency
        session: Session dependency
        
    Returns:
        Created job response
    """
    # Validate session ID matches
    if job_config.session_id != session.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID in request does not match session ID in path",
        )
    
    job = await mapper_service.create_job(
        session=session,
        id_columns=job_config.id_columns,
        target_ontologies=job_config.target_ontologies,
        options=job_config.options,
    )
    
    return MappingJobResponse(
        job_id=job.job_id,
        session_id=job.session_id,
        created_at=job.created_at,
        status=job.status,
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    mapper_service: MapperService = Depends(get_mapper_service),
) -> JobStatus:
    """
    Get the status of a mapping job.
    
    Args:
        job_id: ID of the job to check
        mapper_service: Mapper service dependency
        
    Returns:
        Job status
    """
    job = mapper_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    
    return JobStatus(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/{job_id}/results", response_model=MappingResults)
async def get_job_results(
    job_id: str,
    mapper_service: MapperService = Depends(get_mapper_service),
) -> MappingResults:
    """
    Get the results of a completed mapping job.
    
    Args:
        job_id: ID of the job to retrieve results for
        mapper_service: Mapper service dependency
        
    Returns:
        Mapping results
    """
    job = mapper_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status}",
        )
    
    # Get results preview
    preview_data = mapper_service.get_job_results_preview(job_id)
    
    # Extract stats from job result
    stats = job.result.get("stats", {})
    
    # Create summary object
    summary = MappingResultSummary(
        total_records=stats.get("total_records", 0),
        mapped_records=stats.get("mapped_records", 0),
        mapping_rate=stats.get("mapping_rate", 0.0),
        ontologies_used=stats.get("ontologies_used", []),
        column_stats=stats.get("column_stats", {}),
    )
    
    return MappingResults(
        job_id=job.job_id,
        summary=summary,
        preview=preview_data["preview"],
        download_url=f"/api/mapping/jobs/{job_id}/download",
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/download")
async def download_results(
    job_id: str,
    mapper_service: MapperService = Depends(get_mapper_service),
) -> StreamingResponse:
    """
    Download the mapped CSV file.
    
    Args:
        job_id: ID of the job to download results for
        mapper_service: Mapper service dependency
        
    Returns:
        StreamingResponse with CSV file
    """
    job = mapper_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status}",
        )
    
    output_path = job.result.get("output_path")
    if not output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job result file not found",
        )
    
    def iterfile():
        with open(output_path, "rb") as f:
            yield from f
    
    # Get original filename
    original_file_path = job.result.get("file_path", "")
    original_filename = original_file_path.split("/")[-1] if original_file_path else "data.csv"
    download_filename = f"mapped_{original_filename}"
    
    return StreamingResponse(
        iterfile(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={download_filename}"},
    )


@router.post("/relationship", response_model=RelationshipMappingResponse)
async def map_with_relationship(
    request: RelationshipMappingRequest,
    mapper_service: MapperService = Depends(get_mapper_service),
) -> RelationshipMappingResponse:
    """
    Map data using a relationship and the endpoint adapter extraction mechanism.
    
    This endpoint uses the newly integrated CSVAdapter and RelationshipMappingExecutor
    to map values from one endpoint to another using defined relationships.
    
    Args:
        request: The relationship mapping request
        mapper_service: Mapper service dependency
        
    Returns:
        Mapping results
    """
    results = await mapper_service.map_relationship(
        relationship_id=request.relationship_id,
        source_data=request.source_data
    )
    
    return RelationshipMappingResponse(
        relationship_id=request.relationship_id,
        source_data=request.source_data,
        results=results
    )
