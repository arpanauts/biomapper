"""Type stubs for dspy."""
from typing import Any, Dict, List, Tuple

class teleprompt:
    """DSPy teleprompt module."""
    class BootstrapFewShot:
        """DSPy bootstrap few-shot learner."""
        def __init__(self) -> None: ...
        def compile(
            self, train_data: List[Tuple[str, str]], metric: str
        ) -> "CompileResult": ...

class CompileResult:
    """DSPy compile result."""

    metrics: Dict[str, Any]
