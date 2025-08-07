"""Core services for biomapper."""

# Import only the new control flow modules we created
from .expression_evaluator import (
    SafeExpressionEvaluator,
    ConditionEvaluator,
    ExpressionError,
)
from .control_flow_executor import ControlFlowExecutor, StepExecutionError

# Try to import existing services if they exist
try:
    from .bidirectional_validation_service import BidirectionalValidationService
except ImportError:
    BidirectionalValidationService = None

try:
    from .database_setup_service import DatabaseSetupService
except ImportError:
    DatabaseSetupService = None

try:
    from .direct_mapping_service import DirectMappingService
except ImportError:
    DirectMappingService = None

try:
    from .execution_lifecycle_service import ExecutionLifecycleService
except ImportError:
    ExecutionLifecycleService = None

try:
    from .execution_services import (
        IterativeExecutionService,
        DbStrategyExecutionService,
        YamlStrategyExecutionService,
    )
except ImportError:
    IterativeExecutionService = None
    DbStrategyExecutionService = None
    YamlStrategyExecutionService = None

try:
    from .execution_trace_logger import ExecutionTraceLogger
except ImportError:
    ExecutionTraceLogger = None

try:
    from .iterative_mapping_service import IterativeMappingService
except ImportError:
    IterativeMappingService = None

try:
    from .mapping_handler_service import MappingHandlerService
except ImportError:
    MappingHandlerService = None

try:
    from .mapping_path_execution_service import MappingPathExecutionService
except ImportError:
    MappingPathExecutionService = None

try:
    from .mapping_step_execution_service import MappingStepExecutionService
except ImportError:
    MappingStepExecutionService = None

try:
    from .metadata_query_service import MetadataQueryService
except ImportError:
    MetadataQueryService = None

try:
    from .result_aggregation_service import ResultAggregationService
except ImportError:
    ResultAggregationService = None

try:
    from .strategy_execution_service import StrategyExecutionService
except ImportError:
    StrategyExecutionService = None

__all__ = [
    "SafeExpressionEvaluator",
    "ConditionEvaluator",
    "ExpressionError",
    "ControlFlowExecutor",
    "StepExecutionError",
]

# Add existing services to __all__ if they were imported successfully
if BidirectionalValidationService:
    __all__.append("BidirectionalValidationService")
if DatabaseSetupService:
    __all__.append("DatabaseSetupService")
if DbStrategyExecutionService:
    __all__.append("DbStrategyExecutionService")
if DirectMappingService:
    __all__.append("DirectMappingService")
if ExecutionLifecycleService:
    __all__.append("ExecutionLifecycleService")
if ExecutionTraceLogger:
    __all__.append("ExecutionTraceLogger")
if IterativeExecutionService:
    __all__.append("IterativeExecutionService")
if IterativeMappingService:
    __all__.append("IterativeMappingService")
if MappingHandlerService:
    __all__.append("MappingHandlerService")
if MappingPathExecutionService:
    __all__.append("MappingPathExecutionService")
if MappingStepExecutionService:
    __all__.append("MappingStepExecutionService")
if MetadataQueryService:
    __all__.append("MetadataQueryService")
if ResultAggregationService:
    __all__.append("ResultAggregationService")
if StrategyExecutionService:
    __all__.append("StrategyExecutionService")
if YamlStrategyExecutionService:
    __all__.append("YamlStrategyExecutionService")
