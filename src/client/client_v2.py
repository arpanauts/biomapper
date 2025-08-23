"""Enhanced Biomapper API client for strategy execution."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

import httpx
from httpx import AsyncClient

from .exceptions import (
    ApiError,
    FileUploadError,
    JobNotFoundError,
    NetworkError,
    StrategyNotFoundError,
    TimeoutError,
    ValidationError,
)
from .models import (
    CSVPreviewResponse,
    Checkpoint,
    ColumnsResponse,
    EndpointResponse,
    ExecutionContext,
    ExecutionOptions,
    FileUploadResponse,
    Job,
    JobStatus,
    JobStatusEnum,
    LogEntry,
    ProgressEvent,
    ProgressEventType,
    StrategyExecutionRequest,
    StrategyInfo,
    StrategyResult,
    ValidationResult,
)
from .progress import ProgressTracker


class BiomapperClient:
    """Enhanced Biomapper API client for strategy execution.

    Example usage:
        # Synchronous usage (for scripts)
        client = BiomapperClient()
        result = client.run("metabolomics_harmonization")

        # Async usage (for advanced users)
        async with BiomapperClient() as client:
            job = await client.execute_strategy("my_strategy")
            result = await client.wait_for_job(job.id)

        # Jupyter notebook usage
        client = BiomapperClient()
        result = client.run_with_progress("my_strategy", watch=True)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 300,
        auto_retry: bool = True,
        max_retries: int = 3,
    ):
        """Initialize client with configuration.

        Args:
            base_url: Base URL of the Biomapper API
            api_key: API key for authentication
            timeout: Default timeout in seconds
            auto_retry: Whether to automatically retry failed requests
            max_retries: Maximum number of retries
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("BIOMAPPER_API_KEY")
        self.timeout = timeout
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        self._client: Optional[AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    # === Context Manager Support ===

    async def __aenter__(self):
        """Enter async context."""
        self._client = AsyncClient(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def __enter__(self):
        """Enter sync context."""
        self._sync_client = httpx.Client(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    # === Synchronous Methods (for simple usage) ===

    def run(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        wait: bool = True,
        watch: bool = False,
    ) -> Union[Job, StrategyResult]:
        """Simple synchronous method to run a strategy.

        Args:
            strategy: Strategy name, path to YAML, or dict
            parameters: Parameter overrides
            context: Execution context
            wait: If True, wait for completion (default)
            watch: If True, print progress to stdout

        Returns:
            Job if wait=False, StrategyResult if wait=True

        Example:
            result = client.run("metabolomics_baseline",
                              parameters={"threshold": 0.9})
        """
        return asyncio.run(self._async_run(strategy, parameters, context, wait, watch))

    def run_with_progress(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        use_tqdm: bool = True,
    ) -> StrategyResult:
        """Run strategy with progress bar.

        Args:
            strategy: Strategy name, path to YAML, or dict
            parameters: Parameter overrides
            context: Execution context
            progress_callback: Optional callback for progress updates
            use_tqdm: Whether to use tqdm progress bar

        Returns:
            StrategyResult

        Example:
            result = client.run_with_progress("my_strategy")
        """
        return asyncio.run(
            self._async_run_with_progress(
                strategy, parameters, context, progress_callback, use_tqdm
            )
        )

    # === Async Methods (for advanced usage) ===

    async def execute_strategy(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        options: Optional[ExecutionOptions] = None,
    ) -> Job:
        """Execute a strategy asynchronously.

        Args:
            strategy: Strategy name, path to YAML, or dict
            parameters: Parameter overrides
            context: Execution context
            options: Execution options

        Returns:
            Job object with execution details

        Raises:
            StrategyNotFoundError: If strategy not found
            ValidationError: If strategy validation fails
            ExecutionError: If execution fails
        """
        # Prepare request
        request = self._prepare_strategy_request(strategy, parameters, context, options)

        # Determine endpoint - use v2 endpoint for modern strategies
        if isinstance(strategy, str) and not Path(strategy).exists():
            # Strategy name - use v2 endpoint which handles modern YAML strategies
            endpoint = "/api/strategies/v2/execute"
        else:
            # Strategy YAML (dict or file) - also use v2 endpoint
            endpoint = "/api/strategies/v2/execute"

        # Execute request
        client = self._get_client()
        try:
            # Convert request to v2 API format
            request_dict = request.dict()

            # For v2 API, map fields correctly
            if endpoint.endswith("/v2/execute"):
                v2_request = {
                    "strategy": request_dict.get("strategy_name")
                    or request_dict.get("strategy_yaml"),
                    "parameters": request_dict.get("parameters", {}),
                    "options": request_dict.get("options", {}),
                }
                # Remove context field for v2 API (not needed)
                response = await client.post(endpoint, json=v2_request)
            else:
                # Use original format for old API
                response = await client.post(endpoint, json=request_dict)

            response.raise_for_status()
            data = response.json()

            # Convert to Job object
            from datetime import datetime

            return Job(
                id=data["job_id"],
                status=JobStatusEnum.RUNNING,
                strategy_name=request.strategy_name or "custom",
                created_at=data.get("created_at", datetime.utcnow()),
                updated_at=data.get("updated_at", datetime.utcnow()),
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise StrategyNotFoundError(f"Strategy not found: {strategy}")
            elif e.response.status_code == 400:
                raise ValidationError(f"Invalid strategy: {e.response.text}")
            else:
                raise ApiError(e.response.status_code, e.response.text)
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}")

    async def wait_for_job(
        self,
        job_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 2,
    ) -> StrategyResult:
        """Wait for job completion.

        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait (seconds)
            poll_interval: Polling interval (seconds)

        Returns:
            StrategyResult

        Raises:
            JobNotFoundError: If job not found
            TimeoutError: If timeout exceeded
        """
        start_time = asyncio.get_event_loop().time()
        timeout = timeout or self.timeout

        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} timed out after {timeout} seconds")

            # Get job status
            status = await self.get_job_status(job_id)

            if status.status == JobStatusEnum.COMPLETED:
                # Get results
                results = await self.get_job_results(job_id)
                return StrategyResult(
                    success=True,
                    job_id=job_id,
                    execution_time_seconds=asyncio.get_event_loop().time() - start_time,
                    result_data=results,
                )
            elif status.status == JobStatusEnum.FAILED:
                return StrategyResult(
                    success=False,
                    job_id=job_id,
                    execution_time_seconds=asyncio.get_event_loop().time() - start_time,
                    error=status.message,
                )
            elif status.status == JobStatusEnum.CANCELLED:
                return StrategyResult(
                    success=False,
                    job_id=job_id,
                    execution_time_seconds=asyncio.get_event_loop().time() - start_time,
                    error="Job was cancelled",
                )

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def stream_progress(self, job_id: str) -> AsyncIterator[ProgressEvent]:
        """Stream progress events via WebSocket.

        Args:
            job_id: Job ID to stream progress for

        Yields:
            ProgressEvent objects

        Example:
            async for event in client.stream_progress(job.id):
                print(f"{event.step}/{event.total}: {event.message}")
        """
        # Note: WebSocket implementation would go here
        # For now, using polling as fallback
        last_progress = 0.0

        while True:
            status = await self.get_job_status(job_id)

            # Yield progress event if changed
            if status.progress > last_progress:
                yield ProgressEvent(
                    type=ProgressEventType.PROGRESS,
                    timestamp=status.updated_at,
                    job_id=job_id,
                    percentage=status.progress,
                    message=status.message or "",
                )
                last_progress = status.progress

            # Check if completed
            if status.status in [
                JobStatusEnum.COMPLETED,
                JobStatusEnum.FAILED,
                JobStatusEnum.CANCELLED,
            ]:
                break

            await asyncio.sleep(1)

    # === Job Management ===

    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get current job status.

        Args:
            job_id: Job ID

        Returns:
            JobStatus object

        Raises:
            JobNotFoundError: If job not found
        """
        client = self._get_client()
        try:
            # Try v2 endpoint first (for modern strategies)
            response = await client.get(f"/api/strategies/v2/jobs/{job_id}/status")
            response.raise_for_status()
            data = response.json()
            
            # Convert v2 response to JobStatus format
            from datetime import datetime
            return JobStatus(
                job_id=data.get("job_id"),
                status=data.get("status"),
                progress=100.0 if data.get("status") == "completed" else 0.0,
                current_action=None,
                message=data.get("error"),
                updated_at=datetime.utcnow()
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Fallback to old endpoint
                try:
                    response = await client.get(f"/api/mapping/jobs/{job_id}/status")
                    response.raise_for_status()
                    return JobStatus(**response.json())
                except httpx.HTTPStatusError:
                    raise JobNotFoundError(f"Job not found: {job_id}")
            else:
                raise ApiError(e.response.status_code, e.response.text)

    async def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Get job results.

        Args:
            job_id: Job ID

        Returns:
            Results dictionary

        Raises:
            JobNotFoundError: If job not found
        """
        client = self._get_client()
        
        # Try v2 endpoint first (for modern strategies)
        try:
            response = await client.get(f"/api/strategies/v2/jobs/{job_id}/results")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try v1 endpoint as fallback
                try:
                    response = await client.get(f"/api/mapping/jobs/{job_id}/results")
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError:
                    raise JobNotFoundError(f"Job not found: {job_id}")
            else:
                raise ApiError(e.response.status_code, e.response.text)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled successfully
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Job cancellation not yet implemented in API")

    async def pause_job(self, job_id: str) -> bool:
        """Pause a running job.

        Args:
            job_id: Job ID

        Returns:
            True if paused successfully
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Job pausing not yet implemented in API")

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: Job ID

        Returns:
            True if resumed successfully
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Job resuming not yet implemented in API")

    async def list_jobs(
        self,
        status: Optional[JobStatusEnum] = None,
        limit: int = 100,
    ) -> List[Job]:
        """List recent jobs.

        Args:
            status: Filter by status
            limit: Maximum number of jobs to return

        Returns:
            List of Job objects
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Job listing not yet implemented in API")

    async def get_job_logs(
        self,
        job_id: str,
        tail: int = 100,
    ) -> List[LogEntry]:
        """Get job execution logs.

        Args:
            job_id: Job ID
            tail: Number of most recent log entries to return

        Returns:
            List of LogEntry objects
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Job logs not yet implemented in API")

    # === File Operations ===

    async def upload_file(
        self,
        file_path: Union[str, Path],
        session_id: Optional[str] = None,
    ) -> FileUploadResponse:
        """Upload a file to the API.

        Args:
            file_path: Path to the file
            session_id: Optional session ID

        Returns:
            FileUploadResponse

        Raises:
            FileUploadError: If upload fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileUploadError(f"File not found: {file_path}")

        client = self._get_client()
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "text/csv")}
            data = {"session_id": session_id} if session_id else {}

            response = await client.post("/api/files/upload", files=files, data=data)
            response.raise_for_status()
            return FileUploadResponse(**response.json())

    async def get_file_columns(self, session_id: str) -> ColumnsResponse:
        """Get column information for uploaded file.

        Args:
            session_id: Session ID

        Returns:
            ColumnsResponse
        """
        client = self._get_client()
        response = await client.get(f"/api/files/{session_id}/columns")
        response.raise_for_status()
        return ColumnsResponse(**response.json())

    async def preview_file(
        self,
        session_id: str,
        rows: int = 10,
    ) -> CSVPreviewResponse:
        """Preview uploaded file.

        Args:
            session_id: Session ID
            rows: Number of rows to preview

        Returns:
            CSVPreviewResponse
        """
        client = self._get_client()
        response = await client.get(
            f"/api/files/{session_id}/preview",
            params={"rows": rows},
        )
        response.raise_for_status()
        return CSVPreviewResponse(**response.json())

    # === Checkpoint Management ===

    async def list_checkpoints(self, job_id: str) -> List[Checkpoint]:
        """List available checkpoints for a job.

        Args:
            job_id: Job ID

        Returns:
            List of Checkpoint objects
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Checkpoint listing not yet implemented in API")

    async def restore_from_checkpoint(
        self,
        job_id: str,
        checkpoint_id: str,
    ) -> Job:
        """Restore and continue execution from checkpoint.

        Args:
            job_id: Job ID
            checkpoint_id: Checkpoint ID

        Returns:
            New Job object for resumed execution
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Checkpoint restoration not yet implemented in API")

    # === Strategy Management ===

    async def list_strategies(self) -> List[str]:
        """List available strategies.

        Returns:
            List of strategy names
        """
        # Note: This endpoint would need to be added to the API
        # For now, we can list YAML files in configs directory
        raise NotImplementedError("Strategy listing not yet implemented in API")

    async def get_strategy_info(self, strategy_name: str) -> StrategyInfo:
        """Get strategy metadata and parameters.

        Args:
            strategy_name: Strategy name

        Returns:
            StrategyInfo object
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Strategy info not yet implemented in API")

    async def validate_strategy(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
    ) -> ValidationResult:
        """Validate a strategy without executing.

        Args:
            strategy: Strategy name, path to YAML, or dict

        Returns:
            ValidationResult
        """
        # Note: This endpoint would need to be added to the API
        raise NotImplementedError("Strategy validation not yet implemented in API")

    # === API Information ===

    async def health_check(self) -> Dict[str, Any]:
        """Check API health.

        Returns:
            Health status dictionary
        """
        client = self._get_client()
        response = await client.get("/")
        response.raise_for_status()
        return response.json()

    async def list_endpoints(self) -> List[EndpointResponse]:
        """List available API endpoints.

        Returns:
            List of EndpointResponse objects
        """
        client = self._get_client()
        response = await client.get("/api/endpoints")
        response.raise_for_status()
        return [EndpointResponse(**e) for e in response.json()]

    # === Private Helper Methods ===

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_client(self) -> AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def _prepare_strategy_request(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        options: Optional[ExecutionOptions] = None,
    ) -> StrategyExecutionRequest:
        """Prepare strategy execution request."""
        # Handle ExecutionContext
        if isinstance(context, ExecutionContext):
            request = context.to_request(
                strategy if isinstance(strategy, str) else "custom"
            )
            if parameters:
                request.parameters.update(parameters)
            if options:
                request.options = options
            return request

        # Handle strategy input - prepare for v2 API format
        if isinstance(strategy, Path):
            # Load YAML file
            with open(strategy) as f:
                if strategy.suffix in [".yaml", ".yml"]:
                    import yaml

                    strategy_dict = yaml.safe_load(f)
                else:
                    strategy_dict = json.load(f)
            # For v2 API, pass dict as 'strategy' field (handled in dict conversion)
            return StrategyExecutionRequest(
                strategy_yaml=strategy_dict,  # Will be mapped to 'strategy' in dict()
                parameters=parameters or {},
                options=options or ExecutionOptions(),
                context=context or {},
            )
        elif isinstance(strategy, dict):
            # For v2 API, pass dict as 'strategy' field (handled in dict conversion)
            return StrategyExecutionRequest(
                strategy_yaml=strategy,  # Will be mapped to 'strategy' in dict()
                parameters=parameters or {},
                options=options or ExecutionOptions(),
                context=context or {},
            )
        else:
            # For v2 API, pass name as 'strategy' field (handled in dict conversion)
            return StrategyExecutionRequest(
                strategy_name=strategy,  # Will be mapped to 'strategy' in dict()
                parameters=parameters or {},
                options=options or ExecutionOptions(),
                context=context or {},
            )

    async def _async_run(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        wait: bool = True,
        watch: bool = False,
    ) -> Union[Job, StrategyResult]:
        """Internal async run method."""
        job = await self.execute_strategy(strategy, parameters, context)

        if not wait:
            return job

        if watch:
            # Stream progress to stdout
            async for event in self.stream_progress(job.id):
                print(f"[{event.percentage:.1f}%] {event.message}")

        return await self.wait_for_job(job.id)

    async def _async_run_with_progress(
        self,
        strategy: Union[str, Path, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Union[Dict[str, Any], ExecutionContext]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        use_tqdm: bool = True,
    ) -> StrategyResult:
        """Internal async run with progress tracking."""
        job = await self.execute_strategy(strategy, parameters, context)

        # Create progress tracker
        tracker = ProgressTracker(100, f"Executing {job.strategy_name}")
        if use_tqdm:
            tracker.add_tqdm()
        if progress_callback:
            tracker.add_callback(progress_callback)

        try:
            # Stream progress
            async for event in self.stream_progress(job.id):
                tracker.update(event.message, step=int(event.percentage))

            # Get final result
            return await self.wait_for_job(job.id)
        finally:
            tracker.close()
