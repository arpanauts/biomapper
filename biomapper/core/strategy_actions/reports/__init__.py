"""Report generation actions for biomapper."""

# Import report actions to trigger registration
try:
    from .generate_html_report import GenerateHtmlReportAction
except ImportError:
    pass  # HTML report action not yet implemented

try:
    from .generate_mapping_visualizations import GenerateMappingVisualizationsAction
except ImportError:
    pass  # Mapping visualizations with file generation

try:
    from .generate_visualizations import GenerateMappingVisualizationsAction as LegacyVisualizationAction
except ImportError:
    pass  # Basic visualization action

try:
    from .generate_visualizations_v2 import GenerateMappingVisualizationsAction as GenerateMappingVisualizationsV2Action
except ImportError:
    pass  # Comprehensive visualization action

try:
    from .generate_llm_analysis import GenerateLLMAnalysisAction
except ImportError:
    pass  # LLM analysis action

__all__ = []