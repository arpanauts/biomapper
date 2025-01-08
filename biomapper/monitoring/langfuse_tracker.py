"""Langfuse integration for tracking RAG operations."""
import os
from typing import Optional, Dict, Any, cast
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context


def create_langfuse_client(
    public_key: Optional[str], secret_key: Optional[str], host: Optional[str] = None
) -> Optional[Langfuse]:
    """Create a Langfuse client with the given credentials.

    Args:
        public_key: The Langfuse public key
        secret_key: The Langfuse secret key
        host: Optional host URL, defaults to cloud.langfuse.com

    Returns:
        Optional[Langfuse]: A Langfuse client if credentials are valid, None otherwise
    """
    if not public_key or not secret_key:
        return None

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host or "https://cloud.langfuse.com",
    )


class LangfuseTracker:
    """Central Langfuse integration using environment variables for configuration."""

    def __init__(self, load_env: bool = True) -> None:
        """Initialize LangfuseTracker using environment variables.

        Args:
            load_env: If True, load environment variables from .env file. Defaults to True.
                     Set to False in testing environments where env vars are set manually.
        """
        if load_env:
            load_dotenv()

        # Get environment variables
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")

        print(
            f"[DEBUG] LangfuseTracker.__init__: public_key={public_key}, secret_key={'set' if secret_key else 'not set'}, host={host}"
        )

        self.enabled = bool(public_key and secret_key)
        print(f"[DEBUG] LangfuseTracker.__init__: enabled={self.enabled}")

        if self.enabled:
            print("[DEBUG] LangfuseTracker.__init__: Creating Langfuse client...")
            self.client = create_langfuse_client(
                public_key=public_key, secret_key=secret_key, host=host
            )
            print("[DEBUG] LangfuseTracker.__init__: Langfuse client created")
        else:
            print("[DEBUG] LangfuseTracker.__init__: Skipping Langfuse client creation")
            self.client = None

    @observe(name="compound_mapping")  # type: ignore[misc]
    def trace_mapping(
        self, query: str, trace_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a trace for a mapping operation.

        Args:
            query: The query being mapped
            trace_id: Optional trace ID to use for the trace. If not provided,
                     a new trace ID will be generated.

        Returns:
            Optional[str]: The trace ID if tracking is enabled, None otherwise
        """
        if not self.enabled:
            return None

        metadata = {"query": query, "type": "rag"}
        if trace_id:
            metadata["trace_id"] = trace_id

        langfuse_context.update_current_observation(metadata=metadata)
        result_trace_id = langfuse_context.get_current_trace_id()
        # Help mypy understand the type
        return cast(Optional[str], result_trace_id)

    @observe(name="record_error")  # type: ignore[misc]
    def record_error(self, trace_id: str, error: str) -> None:
        """Record an error in the current trace.

        Args:
            trace_id: The trace ID to record the error for
            error: The error message to record
        """
        if not self.enabled or not self.client:
            return

        # Update observation with error information
        langfuse_context.update_current_observation(
            metadata={"error": error, "trace_id": trace_id}
        )

        try:
            # Update the current trace with error information
            langfuse_context.update_current_trace(
                metadata={"error": error, "trace_id": trace_id}
            )
        except Exception as e:
            print(f"[ERROR] Failed to record error in Langfuse: {e}")

    @observe(name="record_span")  # type: ignore[misc]
    def record_span(
        self,
        trace_id: str,
        span_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
    ) -> None:
        """Record a span in the current trace.

        Args:
            trace_id: The trace ID to record the span for
            span_name: The name of the span
            input_data: Input data for the span
            output_data: Output data for the span
        """
        if not self.enabled:
            return

        langfuse_context.update_current_observation(
            input=input_data, output=output_data, metadata={"span_name": span_name}
        )
