"""
BiOMapper Safety Framework Triad.

Provides automatic, transparent safety mechanisms for three types of isolation:
1. Surgical - Internal action logic modifications
2. Circuitous - Pipeline orchestration and parameter flow
3. Interstitial - Interface compatibility and backward compatibility

All frameworks maintain user-transparent operation with automatic activation.
"""

# Surgical Framework - Action internals
from .action_surgeon import (
    ActionSurgeon,
    ActionSnapshot,
    SurgicalValidator,
    SurgicalMode,
    ContextTracker
)

from .surgical_agent import (
    SurgicalModeAgent,
    surgical_safety_wrapper,
    AgentSurgicalBehavior,
    AutoSurgicalFramework,
    surgical_framework
)

# Circuitous Framework - Pipeline orchestration
from .circuitous_framework import (
    CircuitousFramework,
    CircuitousMode,
    StrategyFlowAnalyzer,
    FlowNode,
    FlowBreakpoint
)

# Interstitial Framework - Interface compatibility
from .interstitial_framework import (
    InterstitialFramework,
    InterstitialMode,
    ContractAnalyzer,
    CompatibilityLayer,
    ActionContract,
    CompatibilityIssue
)

# Unified Agent - Intelligent routing
from .unified_agent import (
    UnifiedBiomapperAgent,
    FrameworkRouter,
    FrameworkType,
    IntentScore,
    unified_agent
)

__all__ = [
    # Surgical components
    'ActionSurgeon',
    'ActionSnapshot',
    'SurgicalValidator',
    'SurgicalMode',
    'ContextTracker',
    'SurgicalModeAgent',
    'surgical_safety_wrapper',
    'AgentSurgicalBehavior',
    'AutoSurgicalFramework',
    'surgical_framework',
    
    # Circuitous components
    'CircuitousFramework',
    'CircuitousMode',
    'StrategyFlowAnalyzer',
    'FlowNode',
    'FlowBreakpoint',
    
    # Interstitial components
    'InterstitialFramework',
    'InterstitialMode',
    'ContractAnalyzer',
    'CompatibilityLayer',
    'ActionContract',
    'CompatibilityIssue',
    
    # Unified agent
    'UnifiedBiomapperAgent',
    'FrameworkRouter',
    'FrameworkType',
    'IntentScore',
    'unified_agent'
]