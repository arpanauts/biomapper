"""Stub for visualization functions that don't exist in v2."""

from typing import Any, Dict, List
import pandas as pd


class VisualizationParams:
    """Stub for VisualizationParams."""
    pass


def create_coverage_pie(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for coverage pie chart."""
    return {"type": "pie", "data": []}


def create_confidence_histogram(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for confidence histogram."""
    return {"type": "histogram", "data": []}


def create_mapping_flow_sankey(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for mapping flow sankey."""
    return {"type": "sankey", "data": []}


def create_one_to_many_chart(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for one-to-many chart."""
    return {"type": "chart", "data": []}


def create_interactive_scatter(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for interactive scatter plot."""
    return {"type": "scatter", "data": []}


def create_statistics_dashboard(data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """Stub for statistics dashboard."""
    return {"type": "dashboard", "data": []}