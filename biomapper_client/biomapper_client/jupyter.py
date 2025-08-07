"""Jupyter notebook integration for Biomapper client."""

from typing import Any, Dict, List, Optional

from .client_v2 import BiomapperClient
from .models import ExecutionContext, StrategyResult


class JupyterExecutor:
    """Enhanced execution for Jupyter notebooks."""

    def __init__(self, client: Optional[BiomapperClient] = None):
        """Initialize Jupyter executor.

        Args:
            client: BiomapperClient instance (creates new if None)
        """
        self.client = client or BiomapperClient()
        self._widget = None
        self._output = None

    def _ensure_widgets(self):
        """Ensure Jupyter widgets are available and initialized."""
        try:
            from IPython.display import clear_output, display
            from ipywidgets import HTML, HBox, IntProgress, Label, Output, VBox

            if self._widget is None:
                self._output = Output()
                self.progress = IntProgress(
                    value=0,
                    min=0,
                    max=100,
                    description="Initializing...",
                    bar_style="info",
                    style={"bar_color": "#00ff00"},
                    orientation="horizontal",
                )
                self.status = Label(value="Ready")
                self.details = Label(value="")
                self._widget = VBox(
                    [
                        self.status,
                        self.progress,
                        self.details,
                        self._output,
                    ]
                )
            return True
        except ImportError:
            return False

    def run(
        self,
        strategy: str,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[ExecutionContext] = None,
        show_logs: bool = True,
        auto_display: bool = True,
    ) -> StrategyResult:
        """Run strategy with interactive display.

        Args:
            strategy: Strategy name or path
            parameters: Strategy parameters
            context: Execution context
            show_logs: Whether to show execution logs
            auto_display: Whether to automatically display results

        Returns:
            StrategyResult

        Example:
            executor = JupyterExecutor(client)
            result = executor.run("metabolomics_harmonization")
            executor.display_results(result)
        """
        if not self._ensure_widgets():
            # Fallback to simple execution if not in Jupyter
            result = self.client.run(strategy, parameters, context)
            # Ensure we return a StrategyResult
            if not isinstance(result, StrategyResult):
                # If it's a Job, wait for it
                import asyncio

                result = asyncio.run(self.client.wait_for_job(result.id))
            return result

        from IPython.display import display

        # Display widget
        display(self._widget)

        async def _run():
            """Async execution with progress updates."""
            self.status.value = "🚀 Starting execution..."
            self.progress.value = 0

            try:
                # Execute strategy
                job = await self.client.execute_strategy(strategy, parameters, context)
                self.status.value = f"⚙️ Job {job.id} running..."

                # Stream progress
                async for event in self.client.stream_progress(job.id):
                    self.progress.value = int(event.percentage)
                    self.details.value = event.message

                    if show_logs and event.type == "log":
                        with self._output:
                            print(f"[{event.timestamp}] {event.message}")

                # Get final result
                result = await self.client.wait_for_job(job.id)

                # Update status
                if result.success:
                    self.status.value = "✅ Execution successful!"
                    self.progress.bar_style = "success"
                else:
                    self.status.value = f"❌ Execution failed: {result.error}"
                    self.progress.bar_style = "danger"

                # Auto-display results
                if auto_display:
                    self.display_results(result)

                return result

            except Exception as e:
                self.status.value = f"❌ Error: {str(e)}"
                self.progress.bar_style = "danger"
                raise

        # Run async function
        return asyncio.run(_run())

    def display_results(self, result: StrategyResult):
        """Display results in notebook-friendly format.

        Args:
            result: StrategyResult to display
        """
        try:
            from IPython.display import HTML, display
            import pandas as pd
        except ImportError:
            print("Results:", result.dict())
            return

        from IPython.display import clear_output

        clear_output()

        # Display status
        if result.success:
            display(
                HTML(
                    f"""
                <div style="padding: 10px; background-color: #d4edda; border-radius: 5px;">
                    <h3>✅ Execution Successful</h3>
                    <p><strong>Job ID:</strong> {result.job_id}</p>
                    <p><strong>Execution Time:</strong> {result.execution_time_seconds:.2f} seconds</p>
                </div>
                """
                )
            )
        else:
            display(
                HTML(
                    f"""
                <div style="padding: 10px; background-color: #f8d7da; border-radius: 5px;">
                    <h3>❌ Execution Failed</h3>
                    <p><strong>Job ID:</strong> {result.job_id}</p>
                    <p><strong>Error:</strong> {result.error}</p>
                </div>
                """
                )
            )

        # Display statistics
        if result.statistics:
            display(HTML("<h4>📊 Statistics</h4>"))
            df = pd.DataFrame([result.statistics])
            display(df)

        # Display output files
        if result.output_files:
            display(HTML("<h4>📁 Output Files</h4>"))
            html_list = "<ul>"
            for file in result.output_files:
                html_list += f'<li><a href="{file}" target="_blank">{file}</a></li>'
            html_list += "</ul>"
            display(HTML(html_list))

        # Display warnings
        if result.warnings:
            display(HTML("<h4>⚠️ Warnings</h4>"))
            html_list = "<ul>"
            for warning in result.warnings:
                html_list += f"<li>{warning}</li>"
            html_list += "</ul>"
            display(HTML(html_list))

        # Display result data
        if result.result_data:
            display(HTML("<h4>📊 Result Data</h4>"))
            # Try to display as DataFrame if possible
            try:
                if isinstance(result.result_data, list):
                    df = pd.DataFrame(result.result_data)
                    display(df.head(20))
                elif isinstance(result.result_data, dict):
                    # Check if it contains a data key
                    if "data" in result.result_data and isinstance(
                        result.result_data["data"], list
                    ):
                        df = pd.DataFrame(result.result_data["data"])
                        display(df.head(20))
                    else:
                        display(HTML(f"<pre>{result.result_data}</pre>"))
                else:
                    display(HTML(f"<pre>{result.result_data}</pre>"))
            except Exception:
                display(HTML(f"<pre>{result.result_data}</pre>"))

    def create_progress_callback(self):
        """Create a progress callback for use with client.run_with_progress.

        Returns:
            Callback function

        Example:
            callback = executor.create_progress_callback()
            result = client.run_with_progress("strategy", progress_callback=callback)
        """
        if not self._ensure_widgets():
            return None

        def callback(current: int, total: int, message: str):
            """Update progress widgets."""
            if total > 0:
                self.progress.value = int((current / total) * 100)
            self.details.value = message

        return callback

    def display_strategy_comparison(
        self,
        results: Dict[str, StrategyResult],
        metrics: Optional[List[str]] = None,
    ):
        """Display comparison of multiple strategy results.

        Args:
            results: Dictionary of strategy name to result
            metrics: List of metrics to compare (uses statistics keys if None)
        """
        try:
            import pandas as pd
            from IPython.display import HTML, display
        except ImportError:
            print("Comparison not available outside Jupyter")
            return

        # Prepare comparison data
        comparison_data = []
        for strategy_name, result in results.items():
            row = {
                "Strategy": strategy_name,
                "Success": "✅" if result.success else "❌",
                "Execution Time": f"{result.execution_time_seconds:.2f}s",
            }

            # Add statistics
            if result.statistics and metrics:
                for metric in metrics:
                    row[metric] = result.statistics.get(metric, "N/A")
            elif result.statistics:
                row.update(result.statistics)

            comparison_data.append(row)

        # Display as table
        display(HTML("<h3>📊 Strategy Comparison</h3>"))
        df = pd.DataFrame(comparison_data)
        display(df)

        # Highlight best performers
        if metrics:
            display(HTML("<h4>🏆 Best Performers</h4>"))
            best_html = "<ul>"
            for metric in metrics:
                if metric in df.columns:
                    try:
                        # Try to find max value
                        best_idx = df[metric].astype(float).idxmax()
                        best_strategy = df.loc[best_idx, "Strategy"]
                        best_value = df.loc[best_idx, metric]
                        best_html += f"<li><strong>{metric}:</strong> {best_strategy} ({best_value})</li>"
                    except Exception:
                        pass
            best_html += "</ul>"
            display(HTML(best_html))


class InteractiveStrategyBuilder:
    """Interactive strategy builder for Jupyter notebooks."""

    def __init__(self):
        """Initialize strategy builder."""
        self.actions = []
        self.parameters = {}

    def add_action(
        self,
        action_type: str,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> "InteractiveStrategyBuilder":
        """Add an action to the strategy.

        Args:
            action_type: Type of action
            name: Action name
            params: Action parameters
            description: Action description

        Returns:
            Self for chaining
        """
        self.actions.append(
            {
                "type": action_type,
                "name": name,
                "params": params or {},
                "description": description,
            }
        )
        return self

    def set_parameter(self, key: str, value: Any) -> "InteractiveStrategyBuilder":
        """Set a strategy parameter.

        Args:
            key: Parameter key
            value: Parameter value

        Returns:
            Self for chaining
        """
        self.parameters[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build the strategy configuration.

        Returns:
            Strategy configuration dictionary
        """
        return {
            "name": "interactive_strategy",
            "description": "Strategy built interactively in Jupyter",
            "parameters": self.parameters,
            "actions": self.actions,
        }

    def visualize(self):
        """Visualize the strategy as a flowchart."""
        try:
            from IPython.display import HTML, display
        except ImportError:
            print("Visualization not available outside Jupyter")
            return

        # Create simple HTML flowchart
        html = """
        <div style="font-family: monospace; padding: 20px;">
            <h3>Strategy Flow</h3>
        """

        for i, action in enumerate(self.actions):
            html += f"""
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">
                <strong>{i + 1}. {action['name']}</strong> ({action['type']})<br>
                {action.get('description', '')}<br>
                <small>Params: {action['params']}</small>
            </div>
            """
            if i < len(self.actions) - 1:
                html += '<div style="text-align: center;">↓</div>'

        html += "</div>"
        display(HTML(html))

    def to_yaml(self) -> str:
        """Convert strategy to YAML format.

        Returns:
            YAML string
        """
        import yaml

        return yaml.dump(self.build(), default_flow_style=False)
