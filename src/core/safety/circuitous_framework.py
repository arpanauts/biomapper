"""
Circuitous Framework for BiOMapper Pipeline Orchestration.

This framework handles pipeline flow issues where individual actions work
but data flow between steps fails. It focuses on YAML strategy definitions,
parameter substitution, and context key flow without modifying action internals.

Automatically activated by agent when detecting orchestration issues.
"""

import re
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Set
from dataclasses import dataclass, field
from datetime import datetime
import os

from core.standards.context_handler import UniversalContext
from core.infrastructure.parameter_resolver import ParameterResolver

logger = logging.getLogger(__name__)


@dataclass
class FlowNode:
    """Represents a step in the strategy flow."""
    
    step_name: str
    action_type: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    context_reads: Set[str] = field(default_factory=set)
    context_writes: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node for analysis."""
        return {
            'step_name': self.step_name,
            'action_type': self.action_type,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'parameters': self.parameters,
            'dependencies': self.dependencies,
            'context_reads': list(self.context_reads),
            'context_writes': list(self.context_writes)
        }


@dataclass
class FlowBreakpoint:
    """Identifies where pipeline flow breaks."""
    
    location: str  # Step where break occurs
    type: str  # 'parameter', 'context', 'sequencing'
    description: str
    from_step: Optional[str] = None
    to_step: Optional[str] = None
    missing_key: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize breakpoint for reporting."""
        return {
            'location': self.location,
            'type': self.type,
            'description': self.description,
            'from_step': self.from_step,
            'to_step': self.to_step,
            'missing_key': self.missing_key,
            'expected_value': str(self.expected_value) if self.expected_value else None,
            'actual_value': str(self.actual_value) if self.actual_value else None
        }


class StrategyFlowAnalyzer:
    """Analyzes YAML strategy flow and identifies issues."""
    
    def __init__(self, strategy_path: Optional[str] = None):
        """Initialize flow analyzer."""
        self.strategy_path = strategy_path
        self.strategy_data: Optional[Dict] = None
        self.flow_graph: List[FlowNode] = []
        self.breakpoints: List[FlowBreakpoint] = []
        
    def load_strategy(self, strategy_path: str) -> Dict[str, Any]:
        """Load and parse YAML strategy."""
        try:
            with open(strategy_path, 'r') as f:
                self.strategy_data = yaml.safe_load(f)
            self.strategy_path = strategy_path
            logger.info(f"📋 Loaded strategy: {Path(strategy_path).name}")
            return self.strategy_data
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
            raise
    
    def build_flow_graph(self) -> List[FlowNode]:
        """Build directed graph of strategy flow."""
        if not self.strategy_data:
            raise ValueError("No strategy loaded")
        
        self.flow_graph = []
        steps = self.strategy_data.get('steps', [])
        
        for i, step in enumerate(steps):
            node = self._create_flow_node(step, i)
            self.flow_graph.append(node)
        
        # Analyze dependencies
        self._analyze_dependencies()
        
        logger.info(f"📊 Built flow graph with {len(self.flow_graph)} nodes")
        return self.flow_graph
    
    def _create_flow_node(self, step: Dict, index: int) -> FlowNode:
        """Create a flow node from a strategy step."""
        action = step.get('action', {})
        params = action.get('params', {})
        
        # Extract inputs and outputs
        inputs = {}
        outputs = {}
        
        # Common input patterns
        for key in ['input_key', 'dataset_key', 'source_key', 'file_path']:
            if key in params:
                inputs[key] = params[key]
        
        # Common output patterns
        for key in ['output_key', 'target_key', 'result_key']:
            if key in params:
                outputs[key] = params[key]
        
        # Detect context access patterns
        context_reads = set()
        context_writes = set()
        
        # Analyze parameter references
        for param_value in params.values():
            if isinstance(param_value, str):
                # Find context references
                if 'datasets.' in param_value or 'context.' in param_value:
                    context_reads.add(param_value)
                # Find parameter substitutions
                param_refs = re.findall(r'\$\{([^}]+)\}', param_value)
                for ref in param_refs:
                    context_reads.add(ref)
        
        # Output keys are written to context
        for output_value in outputs.values():
            context_writes.add(output_value)
        
        return FlowNode(
            step_name=step.get('name', f'step_{index}'),
            action_type=action.get('type', 'UNKNOWN'),
            inputs=inputs,
            outputs=outputs,
            parameters=params,
            context_reads=context_reads,
            context_writes=context_writes
        )
    
    def _analyze_dependencies(self):
        """Analyze dependencies between flow nodes."""
        for i, node in enumerate(self.flow_graph):
            # Check what this node needs from previous nodes
            for j in range(i):
                prev_node = self.flow_graph[j]
                
                # Check if this node uses outputs from previous node
                for input_key, input_value in node.inputs.items():
                    if input_value in prev_node.outputs.values():
                        node.dependencies.append(prev_node.step_name)
                        break
    
    def trace_parameter_flow(self) -> List[FlowBreakpoint]:
        """Trace parameter flow through the pipeline."""
        self.breakpoints = []
        
        if not self.flow_graph:
            self.build_flow_graph()
        
        # Check parameter substitutions
        parameters = self.strategy_data.get('parameters', {})
        
        for node in self.flow_graph:
            for param_key, param_value in node.parameters.items():
                if isinstance(param_value, str) and '${' in param_value:
                    # Extract parameter references
                    refs = re.findall(r'\$\{parameters\.([^}]+)\}', param_value)
                    for ref in refs:
                        if ref not in parameters:
                            self.breakpoints.append(FlowBreakpoint(
                                location=node.step_name,
                                type='parameter',
                                description=f"Undefined parameter: ${{{ref}}}",
                                missing_key=ref
                            ))
        
        # Check context handoffs
        available_keys = set()
        
        for i, node in enumerate(self.flow_graph):
            # Check if node can access what it needs
            for read_key in node.context_reads:
                if read_key.startswith('parameters.'):
                    continue  # Already checked above
                    
                clean_key = read_key.replace('datasets.', '').replace('context.', '')
                if clean_key not in available_keys and i > 0:
                    # Find which step should have provided this
                    provider = None
                    for prev_node in self.flow_graph[:i]:
                        if clean_key in prev_node.context_writes:
                            provider = prev_node.step_name
                            break
                    
                    if not provider:
                        self.breakpoints.append(FlowBreakpoint(
                            location=node.step_name,
                            type='context',
                            description=f"Missing context key: {clean_key}",
                            missing_key=clean_key,
                            to_step=node.step_name
                        ))
            
            # Add this node's outputs to available keys
            available_keys.update(node.context_writes)
        
        logger.info(f"🔍 Found {len(self.breakpoints)} flow breakpoints")
        return self.breakpoints
    
    def suggest_repairs(self) -> List[Dict[str, Any]]:
        """Suggest repairs for identified breakpoints."""
        repairs = []
        
        for breakpoint in self.breakpoints:
            if breakpoint.type == 'parameter':
                repairs.append({
                    'type': 'add_parameter',
                    'location': 'parameters',
                    'action': f"Add missing parameter '{breakpoint.missing_key}' to parameters section",
                    'suggested_value': f"${{ENV_VAR:-/default/path}}"
                })
            
            elif breakpoint.type == 'context':
                # Find where the key should come from
                potential_sources = []
                for node in self.flow_graph:
                    if node.action_type in ['LOAD_DATASET_IDENTIFIERS', 'MERGE_DATASETS']:
                        potential_sources.append(node.step_name)
                
                repairs.append({
                    'type': 'fix_context_flow',
                    'location': breakpoint.location,
                    'action': f"Ensure key '{breakpoint.missing_key}' is available in context",
                    'suggestion': f"Check output_key from previous steps or add intermediate step"
                })
        
        return repairs


class CircuitousFramework:
    """
    Main framework for pipeline orchestration issues.
    
    Automatically activated by agent when detecting flow problems.
    """
    
    # Patterns that trigger circuitous mode
    CIRCUITOUS_PATTERNS = [
        r"circuitous",  # Direct framework name trigger
        r"parameters?.*not.*(flow|pass|work).*between",
        r"(strategy|pipeline).*orchestration.*(broken|failing|issue)",
        r"(step|action).*sequence.*(wrong|incorrect|broken)",
        r"parameter.*substitution.*(failing|broken|not.*work)",
        r"context.*(not.*pass|broken|missing).*between",
        r"\$\{.*\}.*not.*(resolv|work|substitut)",
        r"data.*not.*(flow|pass).*from.*to",
        r"output.*not.*(reach|available).*next.*step",
        r"(handoff|transfer).*between.*steps.*(fail|broken)",
        r"yaml.*strategy.*(broken|issue|problem)"
    ]
    
    def __init__(self):
        """Initialize circuitous framework."""
        self.analyzer = StrategyFlowAnalyzer()
        self.active = False
        self.current_strategy = None
        self.repair_log = []
        
        logger.info("🔄 Circuitous framework initialized")
    
    @classmethod
    def should_use_circuitous_mode(cls, user_message: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if circuitous mode needed based on user intent.
        
        Called automatically by agent for every user message.
        """
        message_lower = user_message.lower()
        
        # Check for circuitous patterns
        for pattern in cls.CIRCUITOUS_PATTERNS:
            if re.search(pattern, message_lower):
                # Try to extract strategy name
                strategy = cls._extract_strategy_name(user_message)
                logger.info(f"✅ Circuitous mode triggered for strategy: {strategy}")
                return True, strategy
        
        return False, None
    
    @classmethod
    def _extract_strategy_name(cls, message: str) -> Optional[str]:
        """Extract strategy name from user message."""
        # Look for strategy file patterns
        patterns = [
            r'(\w+_\w+_to_\w+_\w+_v[\d.]+)',  # Full strategy name
            r'(prot|met|chem)_\w+_to_\w+',     # Partial strategy name
            r'(\w+\.yaml)',                     # YAML file reference
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        
        # Check for common strategy references
        if 'visualization' in message.lower() and 'export' in message.lower():
            return 'detected_from_context'
        
        return None
    
    def diagnose_strategy(self, strategy_path: str) -> Dict[str, Any]:
        """
        Diagnose strategy flow issues.
        
        Returns comprehensive diagnosis report.
        """
        logger.info(f"🔍 Diagnosing strategy: {strategy_path}")
        
        # Load and analyze strategy
        self.analyzer.load_strategy(strategy_path)
        flow_graph = self.analyzer.build_flow_graph()
        breakpoints = self.analyzer.trace_parameter_flow()
        repairs = self.analyzer.suggest_repairs()
        
        # Build diagnosis report
        diagnosis = {
            'strategy': Path(strategy_path).name,
            'timestamp': datetime.now().isoformat(),
            'flow_analysis': {
                'total_steps': len(flow_graph),
                'dependencies_found': sum(len(n.dependencies) for n in flow_graph),
                'context_keys_tracked': len(set().union(*[n.context_writes for n in flow_graph]))
            },
            'issues_found': len(breakpoints),
            'breakpoints': [bp.to_dict() for bp in breakpoints],
            'suggested_repairs': repairs,
            'flow_graph': [node.to_dict() for node in flow_graph]
        }
        
        # Save diagnosis
        self._save_diagnosis(diagnosis)
        
        return diagnosis
    
    def repair_parameter_flow(self, strategy_path: str, repair_spec: Dict) -> bool:
        """
        Apply repairs to fix parameter flow.
        
        Returns True if repairs successful.
        """
        logger.info(f"🔧 Applying repairs to {strategy_path}")
        
        try:
            # Load strategy
            with open(strategy_path, 'r') as f:
                strategy_data = yaml.safe_load(f)
            
            # Apply repairs based on spec
            if repair_spec['type'] == 'add_parameter':
                if 'parameters' not in strategy_data:
                    strategy_data['parameters'] = {}
                
                # Add missing parameter with suggested default
                param_name = repair_spec.get('parameter_name')
                default_value = repair_spec.get('default_value', '/tmp/default')
                strategy_data['parameters'][param_name] = default_value
                
                logger.info(f"✅ Added parameter: {param_name} = {default_value}")
            
            elif repair_spec['type'] == 'fix_context_key':
                # Fix context key reference in step
                step_name = repair_spec.get('step_name')
                old_key = repair_spec.get('old_key')
                new_key = repair_spec.get('new_key')
                
                for step in strategy_data.get('steps', []):
                    if step.get('name') == step_name:
                        params = step.get('action', {}).get('params', {})
                        for key, value in params.items():
                            if value == old_key:
                                params[key] = new_key
                                logger.info(f"✅ Fixed context key: {old_key} → {new_key}")
            
            # Save repaired strategy
            backup_path = strategy_path + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.rename(strategy_path, backup_path)
            
            with open(strategy_path, 'w') as f:
                yaml.dump(strategy_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"💾 Saved repaired strategy (backup: {backup_path})")
            
            # Log repair
            self.repair_log.append({
                'timestamp': datetime.now().isoformat(),
                'strategy': strategy_path,
                'repair': repair_spec,
                'backup': backup_path
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Repair failed: {e}")
            return False
    
    def validate_orchestration(self, strategy_path: str) -> Tuple[bool, List[str]]:
        """
        Validate that orchestration is working correctly.
        
        Returns (is_valid, validation_messages).
        """
        logger.info(f"✅ Validating orchestration for {strategy_path}")
        
        # Diagnose current state
        diagnosis = self.diagnose_strategy(strategy_path)
        
        validation_messages = []
        is_valid = True
        
        # Check for breakpoints
        if diagnosis['issues_found'] > 0:
            is_valid = False
            for breakpoint in diagnosis['breakpoints']:
                validation_messages.append(
                    f"❌ {breakpoint['type'].title()} issue at {breakpoint['location']}: "
                    f"{breakpoint['description']}"
                )
        else:
            validation_messages.append("✅ No flow breakpoints detected")
        
        # Check parameter resolution
        parameters = self.analyzer.strategy_data.get('parameters', {})
        unresolved = []
        
        for key, value in parameters.items():
            if isinstance(value, str) and '${' in value:
                # Check if environment variable exists
                env_var = re.search(r'\$\{([^:-}]+)', value)
                if env_var and not os.getenv(env_var.group(1)):
                    unresolved.append(f"{key}: {value}")
        
        if unresolved:
            is_valid = False
            validation_messages.append(f"⚠️ Unresolved parameters: {', '.join(unresolved)}")
        else:
            validation_messages.append("✅ All parameters resolvable")
        
        # Check step sequencing
        flow_graph = diagnosis['flow_graph']
        for i, node in enumerate(flow_graph):
            if i > 0 and not node['dependencies'] and node['context_reads']:
                validation_messages.append(
                    f"⚠️ Step '{node['step_name']}' reads context but has no dependencies"
                )
        
        return is_valid, validation_messages
    
    def _save_diagnosis(self, diagnosis: Dict):
        """Save diagnosis report for debugging."""
        diagnosis_dir = Path("/tmp/biomapper/circuitous")
        diagnosis_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"diagnosis_{diagnosis['strategy']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = diagnosis_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(diagnosis, f, indent=2, default=str)
        
        logger.debug(f"💾 Saved diagnosis to {filepath}")


class CircuitousMode:
    """
    Context manager for circuitous mode operations.
    
    Usage:
        with CircuitousMode('strategy.yaml') as circuitous:
            diagnosis = circuitous.diagnose()
            circuitous.repair()
    """
    
    def __init__(self, strategy_path: str):
        """Initialize circuitous mode."""
        self.framework = CircuitousFramework()
        self.strategy_path = strategy_path
        
    def __enter__(self):
        """Enter circuitous mode."""
        logger.info(f"🔄 Entering circuitous mode for {self.strategy_path}")
        self.framework.active = True
        self.framework.current_strategy = self.strategy_path
        return self.framework
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit circuitous mode."""
        logger.info(f"🔓 Exiting circuitous mode")
        self.framework.active = False
        
        if exc_type is None:
            logger.info("✅ Circuitous operations completed successfully")
        else:
            logger.error(f"❌ Circuitous mode failed: {exc_val}")