"""Progress tracking utilities for Biomapper client."""

from typing import Any, Callable, List, Optional, Tuple


class ProgressTracker:
    """Progress tracking with multiple backends."""

    def __init__(self, total_steps: int, description: str = "Processing"):
        """Initialize progress tracker.

        Args:
            total_steps: Total number of steps
            description: Description of the operation
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.backends: List[Tuple[str, Any]] = []
        self._is_closed = False

    def add_tqdm(self, **kwargs) -> "ProgressTracker":
        """Add tqdm progress bar.

        Args:
            **kwargs: Additional arguments for tqdm

        Returns:
            Self for chaining
        """
        try:
            from tqdm import tqdm

            pbar = tqdm(total=self.total_steps, desc=self.description, **kwargs)
            self.backends.append(("tqdm", pbar))
        except ImportError:
            pass  # Silently skip if tqdm not installed
        return self

    def add_rich(self, **kwargs) -> "ProgressTracker":
        """Add rich progress bar.

        Args:
            **kwargs: Additional arguments for rich Progress

        Returns:
            Self for chaining
        """
        try:
            from rich.progress import Progress, TaskID

            progress = Progress(**kwargs)
            progress.start()
            task_id = progress.add_task(self.description, total=self.total_steps)
            self.backends.append(("rich", (progress, task_id)))
        except ImportError:
            pass  # Silently skip if rich not installed
        return self

    def add_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> "ProgressTracker":
        """Add custom callback.

        Args:
            callback: Function(current_step, total_steps, message)

        Returns:
            Self for chaining
        """
        self.backends.append(("callback", callback))
        return self

    def add_jupyter(self) -> "ProgressTracker":
        """Add Jupyter notebook progress widget.

        Returns:
            Self for chaining
        """
        try:
            from IPython.display import display
            from ipywidgets import HTML, HBox, IntProgress, Label

            progress = IntProgress(
                value=0,
                min=0,
                max=self.total_steps,
                description=self.description,
                bar_style="info",
                orientation="horizontal",
            )
            label = Label(value=f"0/{self.total_steps}")
            status = Label(value="")

            # Create horizontal box layout
            widget = HBox([progress, label, status])
            display(widget)

            self.backends.append(("jupyter", (progress, label, status)))
        except ImportError:
            pass  # Silently skip if not in Jupyter
        return self

    def update(
        self,
        message: Optional[str] = None,
        step: Optional[int] = None,
        increment: int = 1,
    ) -> None:
        """Update progress.

        Args:
            message: Optional message to display
            step: Absolute step number (overrides increment)
            increment: Number of steps to increment (default 1)
        """
        if self._is_closed:
            return

        # Update step count
        if step is not None:
            self.current_step = min(step, self.total_steps)
        else:
            self.current_step = min(self.current_step + increment, self.total_steps)

        # Update each backend
        for backend_type, backend in self.backends:
            try:
                if backend_type == "tqdm":
                    # Update tqdm progress bar
                    backend.n = self.current_step
                    backend.refresh()
                    if message:
                        backend.set_postfix_str(message)

                elif backend_type == "rich":
                    # Update rich progress bar
                    progress, task_id = backend
                    progress.update(
                        task_id,
                        completed=self.current_step,
                        description=f"{self.description}: {message}"
                        if message
                        else self.description,
                    )

                elif backend_type == "callback":
                    # Call custom callback
                    backend(
                        self.current_step,
                        self.total_steps,
                        message or self.description,
                    )

                elif backend_type == "jupyter":
                    # Update Jupyter widgets
                    progress, label, status = backend
                    progress.value = self.current_step
                    label.value = f"{self.current_step}/{self.total_steps}"
                    if message:
                        status.value = message

            except Exception:
                # Silently ignore backend errors
                pass

    def set_description(self, description: str) -> None:
        """Update the description.

        Args:
            description: New description
        """
        self.description = description
        for backend_type, backend in self.backends:
            try:
                if backend_type == "tqdm":
                    backend.set_description(description)
                elif backend_type == "rich":
                    progress, task_id = backend
                    progress.update(task_id, description=description)
            except Exception:
                pass

    def close(self) -> None:
        """Close all progress backends."""
        if self._is_closed:
            return

        for backend_type, backend in self.backends:
            try:
                if backend_type == "tqdm":
                    backend.close()
                elif backend_type == "rich":
                    progress, _ = backend
                    progress.stop()
            except Exception:
                pass

        self._is_closed = True

    def __enter__(self) -> "ProgressTracker":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

    @property
    def percentage(self) -> float:
        """Get current progress percentage."""
        if self.total_steps == 0:
            return 100.0
        return (self.current_step / self.total_steps) * 100


class NoOpProgressTracker:
    """No-operation progress tracker for when progress tracking is disabled."""

    def __init__(self, *args, **kwargs):
        """Initialize no-op tracker."""
        pass

    def add_tqdm(self, **kwargs) -> "NoOpProgressTracker":
        """No-op."""
        return self

    def add_rich(self, **kwargs) -> "NoOpProgressTracker":
        """No-op."""
        return self

    def add_callback(self, callback: Callable) -> "NoOpProgressTracker":
        """No-op."""
        return self

    def add_jupyter(self) -> "NoOpProgressTracker":
        """No-op."""
        return self

    def update(self, *args, **kwargs) -> None:
        """No-op."""
        pass

    def set_description(self, description: str) -> None:
        """No-op."""
        pass

    def close(self) -> None:
        """No-op."""
        pass

    def __enter__(self) -> "NoOpProgressTracker":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        pass

    @property
    def percentage(self) -> float:
        """Always return 0."""
        return 0.0
