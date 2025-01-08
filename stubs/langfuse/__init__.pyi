"""Type stubs for langfuse."""
from typing import Any, Dict, Optional

class Langfuse:
    """Langfuse client."""
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None: ...
    def trace(
        self,
        name: str = "",
        id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> "Trace": ...
    def traces(self) -> Any: ...

class Trace:
    """Langfuse trace."""

    id: str
    def span(
        self, name: str, input: Dict[str, Any], output: Optional[Dict[str, Any]] = None
    ) -> "Span": ...
    def error(self, message: str) -> None: ...
    def score(self, name: str, value: float, comment: str) -> None: ...
    def metrics(self) -> None: ...

class Span:
    """Langfuse span."""
    def __init__(self, name: str, input: Dict[str, Any]) -> None: ...
