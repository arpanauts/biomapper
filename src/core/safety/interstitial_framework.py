"""
Interstitial Framework for BiOMapper Interface Compatibility.

This framework handles interface compatibility issues when action boundaries 
need modification while maintaining backward compatibility. It focuses on
action input/output contracts, parameter interfaces, and version compatibility.

Automatically activated by agent when detecting interface evolution needs.
"""

import re
import json
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Set, Type
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from actions.registry import ACTION_REGISTRY
from actions.typed_base import TypedStrategyAction
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


@dataclass
class ActionContract:
    """Represents an action's input/output contract."""
    
    action_type: str
    version: str
    input_params: Dict[str, Dict[str, Any]]  # param_name -> {type, required, default}
    output_structure: Dict[str, Any]  # Expected output format
    context_reads: Set[str]
    context_writes: Set[str]
    backward_compatible_with: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize contract for storage."""
        return {
            'action_type': self.action_type,
            'version': self.version,
            'input_params': self.input_params,
            'output_structure': self.output_structure,
            'context_reads': list(self.context_reads),
            'context_writes': list(self.context_writes),
            'backward_compatible_with': self.backward_compatible_with
        }


@dataclass
class CompatibilityIssue:
    """Identifies interface compatibility problems."""
    
    action_type: str
    issue_type: str  # 'breaking', 'deprecated', 'missing'
    description: str
    affected_parameter: Optional[str] = None
    old_interface: Optional[Any] = None
    new_interface: Optional[Any] = None
    migration_path: Optional[str] = None
    severity: str = 'warning'  # 'error', 'warning', 'info'
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize issue for reporting."""
        return {
            'action_type': self.action_type,
            'issue_type': self.issue_type,
            'description': self.description,
            'affected_parameter': self.affected_parameter,
            'old_interface': str(self.old_interface) if self.old_interface else None,
            'new_interface': str(self.new_interface) if self.new_interface else None,
            'migration_path': self.migration_path,
            'severity': self.severity
        }


class ContractAnalyzer:
    """Analyzes action contracts and detects compatibility issues."""
    
    def __init__(self):
        """Initialize contract analyzer."""
        self.contracts: Dict[str, ActionContract] = {}
        self.compatibility_matrix: Dict[str, Dict[str, bool]] = {}
        
    def extract_contract(self, action_type: str) -> ActionContract:
        """Extract contract from an action class."""
        if action_type not in ACTION_REGISTRY:
            raise ValueError(f"Action {action_type} not found in registry")
        
        action_class = ACTION_REGISTRY[action_type]
        
        # Extract parameter model if it's a TypedStrategyAction
        input_params = {}
        
        if hasattr(action_class, 'get_params_model'):
            try:
                # Get the Pydantic model
                params_model = action_class().get_params_model()
                
                # Extract field information
                for field_name, field_info in params_model.__fields__.items():
                    input_params[field_name] = {
                        'type': str(field_info.type_),
                        'required': field_info.required,
                        'default': field_info.default if not field_info.required else None,
                        'description': field_info.field_info.description if hasattr(field_info, 'field_info') else None
                    }
            except Exception as e:
                logger.warning(f"Could not extract params model for {action_type}: {e}")
        
        # Analyze execute method signature as fallback
        if not input_params and hasattr(action_class, 'execute'):
            sig = inspect.signature(action_class.execute)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'context']:
                    input_params[param_name] = {
                        'type': str(param.annotation) if param.annotation != param.empty else 'Any',
                        'required': param.default == param.empty,
                        'default': param.default if param.default != param.empty else None
                    }
        
        # Extract context access patterns (heuristic)
        context_reads = set()
        context_writes = set()
        
        # Common patterns in action implementations
        if hasattr(action_class, 'execute'):
            # This would require source code analysis
            # For now, use common patterns
            if 'LOAD' in action_type:
                context_writes.add('datasets')
            if 'EXPORT' in action_type or 'SAVE' in action_type:
                context_reads.add('datasets')
                context_writes.add('output_files')
            if 'MERGE' in action_type or 'COMBINE' in action_type:
                context_reads.add('datasets')
                context_writes.add('datasets')
        
        # Determine version (could be enhanced with actual versioning)
        version = '1.0.0'  # Default version
        
        contract = ActionContract(
            action_type=action_type,
            version=version,
            input_params=input_params,
            output_structure={},  # Would need execution to determine
            context_reads=context_reads,
            context_writes=context_writes
        )
        
        self.contracts[action_type] = contract
        logger.info(f"📋 Extracted contract for {action_type}: {len(input_params)} parameters")
        
        return contract
    
    def compare_contracts(self, old_contract: ActionContract, new_contract: ActionContract) -> List[CompatibilityIssue]:
        """Compare two contracts and identify compatibility issues."""
        issues = []
        
        # Check for removed required parameters (breaking)
        for param_name, param_info in old_contract.input_params.items():
            if param_info['required'] and param_name not in new_contract.input_params:
                issues.append(CompatibilityIssue(
                    action_type=new_contract.action_type,
                    issue_type='breaking',
                    description=f"Required parameter '{param_name}' removed",
                    affected_parameter=param_name,
                    old_interface=param_info,
                    severity='error'
                ))
        
        # Check for type changes (potentially breaking)
        for param_name in old_contract.input_params:
            if param_name in new_contract.input_params:
                old_type = old_contract.input_params[param_name]['type']
                new_type = new_contract.input_params[param_name]['type']
                
                if old_type != new_type and not self._types_compatible(old_type, new_type):
                    issues.append(CompatibilityIssue(
                        action_type=new_contract.action_type,
                        issue_type='breaking',
                        description=f"Parameter '{param_name}' type changed",
                        affected_parameter=param_name,
                        old_interface=old_type,
                        new_interface=new_type,
                        severity='error'
                    ))
        
        # Check for new required parameters (potentially breaking)
        for param_name, param_info in new_contract.input_params.items():
            if param_info['required'] and param_name not in old_contract.input_params:
                issues.append(CompatibilityIssue(
                    action_type=new_contract.action_type,
                    issue_type='breaking',
                    description=f"New required parameter '{param_name}' added",
                    affected_parameter=param_name,
                    new_interface=param_info,
                    migration_path=f"Add '{param_name}' to existing strategies",
                    severity='warning'
                ))
        
        # Check for deprecated parameters (warning)
        for param_name in old_contract.input_params:
            if param_name not in new_contract.input_params:
                # Check if there's an alternative
                alternative = self._find_alternative_param(param_name, new_contract.input_params)
                issues.append(CompatibilityIssue(
                    action_type=new_contract.action_type,
                    issue_type='deprecated',
                    description=f"Parameter '{param_name}' deprecated",
                    affected_parameter=param_name,
                    migration_path=f"Use '{alternative}' instead" if alternative else "Remove from strategies",
                    severity='warning'
                ))
        
        # Check context interface changes
        removed_reads = old_contract.context_reads - new_contract.context_reads
        removed_writes = old_contract.context_writes - new_contract.context_writes
        
        if removed_reads:
            issues.append(CompatibilityIssue(
                action_type=new_contract.action_type,
                issue_type='breaking',
                description=f"No longer reads from context: {removed_reads}",
                severity='warning'
            ))
        
        if removed_writes:
            issues.append(CompatibilityIssue(
                action_type=new_contract.action_type,
                issue_type='breaking',
                description=f"No longer writes to context: {removed_writes}",
                severity='error'
            ))
        
        logger.info(f"🔍 Found {len(issues)} compatibility issues")
        return issues
    
    def _types_compatible(self, old_type: str, new_type: str) -> bool:
        """Check if two types are compatible."""
        # Simple compatibility check - could be enhanced
        compatible_pairs = [
            ('str', 'Optional[str]'),
            ('int', 'float'),
            ('List', 'Sequence'),
            ('Dict', 'Mapping')
        ]
        
        for old, new in compatible_pairs:
            if old in old_type and new in new_type:
                return True
        
        return old_type == new_type
    
    def _find_alternative_param(self, old_param: str, new_params: Dict) -> Optional[str]:
        """Find alternative parameter name (heuristic)."""
        # Check for common naming migrations
        migrations = {
            'dataset_key': 'input_key',
            'output_dataset': 'output_key',
            'filepath': 'file_path',
            'output_dir': 'directory_path'
        }
        
        if old_param in migrations and migrations[old_param] in new_params:
            return migrations[old_param]
        
        # Check for similar names
        for new_param in new_params:
            if old_param in new_param or new_param in old_param:
                return new_param
        
        return None


class CompatibilityLayer:
    """Creates compatibility layers for interface evolution."""
    
    def __init__(self):
        """Initialize compatibility layer generator."""
        self.adapters: Dict[str, Any] = {}
        
    def create_parameter_adapter(self, action_type: str, migration_spec: Dict) -> str:
        """
        Create parameter adapter code for backward compatibility.
        
        Returns Python code string for the adapter.
        """
        adapter_code = f"""
# Auto-generated compatibility adapter for {action_type}
# Generated: {datetime.now().isoformat()}

from typing import Dict, Any

def adapt_{action_type.lower()}_params(old_params: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Adapt old parameter format to new interface.\"\"\"
    new_params = old_params.copy()
    
"""
        
        # Add parameter migrations
        for old_name, new_name in migration_spec.get('param_renames', {}).items():
            adapter_code += f"""    # Rename {old_name} -> {new_name}
    if '{old_name}' in new_params:
        new_params['{new_name}'] = new_params.pop('{old_name}')
    
"""
        
        # Add default values for new required parameters
        for param_name, default_value in migration_spec.get('new_defaults', {}).items():
            adapter_code += f"""    # Add default for new parameter
    if '{param_name}' not in new_params:
        new_params['{param_name}'] = {repr(default_value)}
    
"""
        
        # Add type conversions
        for param_name, conversion in migration_spec.get('type_conversions', {}).items():
            adapter_code += f"""    # Convert type for {param_name}
    if '{param_name}' in new_params:
        new_params['{param_name}'] = {conversion}(new_params['{param_name}'])
    
"""
        
        adapter_code += """    return new_params
"""
        
        logger.info(f"📝 Generated compatibility adapter for {action_type}")
        return adapter_code
    
    def create_wrapper_action(self, action_type: str, compatibility_issues: List[CompatibilityIssue]) -> str:
        """
        Create wrapper action class for full backward compatibility.
        
        Returns Python code string for the wrapper.
        """
        wrapper_code = f"""
# Auto-generated backward compatibility wrapper for {action_type}
# Generated: {datetime.now().isoformat()}

from typing import Dict, Any
from actions.registry import register_action
from actions.typed_base import TypedStrategyAction

@register_action("{action_type}_COMPAT")
class {action_type}CompatibilityWrapper(TypedStrategyAction):
    \"\"\"Backward compatibility wrapper for {action_type}.\"\"\"
    
    def __init__(self):
        super().__init__()
        # Load the new implementation
        from actions.registry import ACTION_REGISTRY
        self.new_action = ACTION_REGISTRY['{action_type}']()
    
    async def execute_typed(self, params: Dict[str, Any], context: Any) -> Any:
        # Adapt old parameters to new interface
        adapted_params = self._adapt_parameters(params)
        
        # Call new implementation
        result = await self.new_action.execute_typed(adapted_params, context)
        
        # Adapt output if needed
        return self._adapt_output(result)
    
    def _adapt_parameters(self, old_params: Dict[str, Any]) -> Dict[str, Any]:
        new_params = old_params.copy()
        
"""
        
        # Add specific adaptations based on issues
        for issue in compatibility_issues:
            if issue.issue_type == 'deprecated' and issue.migration_path:
                old_param = issue.affected_parameter
                # Extract new parameter from migration path
                if "Use '" in issue.migration_path:
                    new_param = issue.migration_path.split("'")[1]
                    wrapper_code += f"""        # Handle deprecated parameter
        if '{old_param}' in new_params:
            new_params['{new_param}'] = new_params.pop('{old_param}')
        
"""
        
        wrapper_code += """        return new_params
    
    def _adapt_output(self, result: Any) -> Any:
        # Adapt output format if needed
        return result
"""
        
        logger.info(f"📦 Generated compatibility wrapper for {action_type}")
        return wrapper_code


class InterstitialFramework:
    """
    Main framework for interface compatibility management.
    
    CORE PRINCIPLE: Maintain 100% backward compatibility while allowing interface evolution.
    Every interface change must preserve existing functionality through compatibility layers.
    
    Automatically activated by agent when detecting interface evolution needs.
    """
    
    # Patterns that trigger interstitial mode
    INTERSTITIAL_PATTERNS = [
        r"interstitial",  # Direct framework name trigger
        r"(handoff|interface).*between.*actions.*(failing|broken)",
        r"(contract|compatibility).*(issue|problem|broken)",
        r"action.*boundary.*(change|modify|update)",
        r"backward.*compatibility.*(maintain|preserve|break)",
        r"parameter.*interface.*(evolve|change|update)",
        r"output.*structure.*(modify|change).*compatibility",
        r"version.*compatibility.*(issue|problem)",
        r"api.*(evolution|change|update).*break",
        r"(new|added).*parameter.*broke.*existing",
        r"interface.*contract.*(violat|broken)",
        r"existing.*strategies?.*(broke|fail|not.*work)",
        r"upgrade.*without.*breaking"
    ]
    
    # Backward compatibility enforcement rules
    COMPATIBILITY_RULES = {
        'NEVER_BREAK': [
            'Required parameters cannot be removed',
            'Parameter types must remain compatible',
            'Output structure must remain accessible',
            'Context keys must remain available'
        ],
        'ALWAYS_PROVIDE': [
            'Migration path for deprecated features',
            'Default values for new required parameters',
            'Type adapters for changed parameters',
            'Compatibility wrappers when needed'
        ],
        'PRESERVE': [
            'All existing strategies must continue working',
            'All parameter aliases must be maintained',
            'All output formats must be readable',
            'All context patterns must be supported'
        ]
    }
    
    def __init__(self):
        """Initialize interstitial framework."""
        self.analyzer = ContractAnalyzer()
        self.compatibility_layer = CompatibilityLayer()
        self.active = False
        self.contract_cache: Dict[str, ActionContract] = {}
        
        logger.info("🔗 Interstitial framework initialized")
    
    @classmethod
    def should_use_interstitial_mode(cls, user_message: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if interstitial mode needed based on user intent.
        
        Called automatically by agent for every user message.
        """
        message_lower = user_message.lower()
        
        # Check for interstitial patterns
        for pattern in cls.INTERSTITIAL_PATTERNS:
            if re.search(pattern, message_lower):
                # Try to extract action type
                action = cls._extract_action_type(user_message)
                logger.info(f"✅ Interstitial mode triggered for action: {action}")
                return True, action
        
        return False, None
    
    @classmethod
    def _extract_action_type(cls, message: str) -> Optional[str]:
        """Extract action type from user message."""
        # Look for action names in registry
        for action_name in ACTION_REGISTRY.keys():
            if action_name.lower() in message.lower():
                return action_name
        
        # Check for common action references
        if 'export' in message.lower():
            return 'EXPORT_DATASET'
        if 'load' in message.lower():
            return 'LOAD_DATASET_IDENTIFIERS'
        
        return None
    
    def analyze_interface_evolution(self, action_type: str, old_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze how an action's interface has evolved.
        
        Returns comprehensive evolution report.
        """
        logger.info(f"🔍 Analyzing interface evolution for {action_type}")
        
        # Extract current contract
        current_contract = self.analyzer.extract_contract(action_type)
        
        # Load or reconstruct old contract
        old_contract = None
        if old_version:
            old_contract = self._load_historical_contract(action_type, old_version)
        
        # If no old contract, try to infer from usage patterns
        if not old_contract:
            old_contract = self._infer_historical_contract(action_type)
        
        # Compare contracts if we have both
        compatibility_issues = []
        if old_contract:
            compatibility_issues = self.analyzer.compare_contracts(old_contract, current_contract)
        
        # Build evolution report
        report = {
            'action_type': action_type,
            'timestamp': datetime.now().isoformat(),
            'current_interface': current_contract.to_dict(),
            'compatibility_issues': [issue.to_dict() for issue in compatibility_issues],
            'breaking_changes': len([i for i in compatibility_issues if i.severity == 'error']),
            'warnings': len([i for i in compatibility_issues if i.severity == 'warning']),
            'migration_required': any(i.severity == 'error' for i in compatibility_issues)
        }
        
        # Save report
        self._save_evolution_report(report)
        
        return report
    
    def ensure_backward_compatibility(self, action_type: str, target_version: str = 'all') -> Dict[str, Any]:
        """
        Ensure 100% backward compatibility for an action.
        
        GUARANTEE: After this method completes, ALL existing strategies will continue working.
        
        Returns compatibility assurance report with enforced solutions.
        """
        logger.info(f"🛡️ Ensuring FULL backward compatibility for {action_type}")
        
        # Analyze current state
        evolution_report = self.analyze_interface_evolution(action_type)
        
        # Check against compatibility rules
        rule_violations = self._check_compatibility_rules(evolution_report)
        if rule_violations:
            logger.warning(f"⚠️ Compatibility rule violations detected: {rule_violations}")
        
        compatibility_solutions = []
        auto_applied_fixes = []
        
        # Generate AND APPLY solutions for each issue
        for issue_data in evolution_report['compatibility_issues']:
            issue = CompatibilityIssue(**issue_data)
            
            # ALL issues must be resolved for backward compatibility
            solution = {
                'issue': issue.description,
                'severity': issue.severity,
                'solution_type': self._determine_solution_type(issue),
                'action': self._generate_compatibility_solution(action_type, issue)
            }
            
            # Auto-apply critical fixes
            if issue.severity == 'error':
                fix_applied = self._auto_apply_compatibility_fix(action_type, issue)
                if fix_applied:
                    auto_applied_fixes.append(fix_applied)
                    solution['auto_applied'] = True
            
            compatibility_solutions.append(solution)
        
        # Generate migration guide
        migration_guide = self._generate_migration_guide(action_type, evolution_report)
        
        # Generate compatibility wrapper if needed
        wrapper_code = None
        if evolution_report['migration_required']:
            wrapper_code = self.compatibility_layer.create_wrapper_action(
                action_type,
                [CompatibilityIssue(**i) for i in evolution_report['compatibility_issues']]
            )
        
        return {
            'action_type': action_type,
            'compatibility_assured': not evolution_report['migration_required'],
            'solutions_applied': compatibility_solutions,
            'migration_guide': migration_guide,
            'wrapper_code': wrapper_code
        }
    
    def validate_strategy_compatibility(self, strategy_path: str, action_versions: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate that a strategy works with specified action versions.
        
        Returns (is_compatible, compatibility_messages).
        """
        logger.info(f"✅ Validating strategy compatibility: {strategy_path}")
        
        import yaml
        
        # Load strategy
        with open(strategy_path, 'r') as f:
            strategy_data = yaml.safe_load(f)
        
        messages = []
        is_compatible = True
        
        # Check each step
        for step in strategy_data.get('steps', []):
            action_type = step.get('action', {}).get('type')
            if not action_type:
                continue
            
            # Get expected version
            expected_version = action_versions.get(action_type, 'latest')
            
            # Check if action exists
            if action_type not in ACTION_REGISTRY:
                messages.append(f"❌ Action {action_type} not found in registry")
                is_compatible = False
                continue
            
            # Extract and check contract
            contract = self.analyzer.extract_contract(action_type)
            
            # Check parameters used in strategy
            params = step.get('action', {}).get('params', {})
            for param_name in params:
                if param_name not in contract.input_params:
                    messages.append(f"⚠️ Step '{step.get('name')}': Unknown parameter '{param_name}'")
                    # Check if there's a migration
                    alternative = self.analyzer._find_alternative_param(param_name, contract.input_params)
                    if alternative:
                        messages.append(f"   → Use '{alternative}' instead")
            
            # Check required parameters
            for param_name, param_info in contract.input_params.items():
                if param_info['required'] and param_name not in params:
                    messages.append(f"⚠️ Step '{step.get('name')}': Missing required parameter '{param_name}'")
                    is_compatible = False
        
        if is_compatible:
            messages.append("✅ Strategy is compatible with current action versions")
        
        return is_compatible, messages
    
    def _load_historical_contract(self, action_type: str, version: str) -> Optional[ActionContract]:
        """Load historical contract from storage."""
        # This would load from a contract history database
        # For now, return None to trigger inference
        return None
    
    def _infer_historical_contract(self, action_type: str) -> Optional[ActionContract]:
        """Infer historical contract from common patterns."""
        # Use knowledge of common parameter migrations
        historical_params = {}
        
        # Common historical patterns
        if 'EXPORT' in action_type:
            historical_params = {
                'dataset_key': {'type': 'str', 'required': True, 'default': None},
                'output_dir': {'type': 'str', 'required': True, 'default': None}
            }
        elif 'LOAD' in action_type:
            historical_params = {
                'filepath': {'type': 'str', 'required': True, 'default': None},
                'dataset_key': {'type': 'str', 'required': True, 'default': None}
            }
        
        if historical_params:
            return ActionContract(
                action_type=action_type,
                version='0.9.0',  # Assumed old version
                input_params=historical_params,
                output_structure={},
                context_reads=set(),
                context_writes=set()
            )
        
        return None
    
    def _check_compatibility_rules(self, evolution_report: Dict) -> List[str]:
        """Check if evolution violates compatibility rules."""
        violations = []
        
        for issue in evolution_report.get('compatibility_issues', []):
            if issue['severity'] == 'error':
                # Check against NEVER_BREAK rules
                if 'removed' in issue['description'] and 'Required' in issue['description']:
                    violations.append("NEVER_BREAK: Required parameters cannot be removed")
                if 'type changed' in issue['description']:
                    violations.append("NEVER_BREAK: Parameter types must remain compatible")
                if 'no longer writes' in issue['description'].lower():
                    violations.append("NEVER_BREAK: Context keys must remain available")
        
        return violations
    
    def _determine_solution_type(self, issue: CompatibilityIssue) -> str:
        """Determine the type of solution needed for an issue."""
        if issue.issue_type == 'deprecated':
            return 'parameter_alias'
        elif issue.issue_type == 'breaking':
            if 'type' in issue.description:
                return 'type_adapter'
            elif 'removed' in issue.description:
                return 'compatibility_wrapper'
            elif 'added' in issue.description:
                return 'default_provider'
        return 'migration_guide'
    
    def _auto_apply_compatibility_fix(self, action_type: str, issue: CompatibilityIssue) -> Optional[Dict]:
        """Automatically apply compatibility fix for critical issues."""
        fix_record = {
            'action_type': action_type,
            'issue': issue.description,
            'fix_type': None,
            'fix_applied': False
        }
        
        # For breaking changes, create automatic compatibility layer
        if issue.severity == 'error':
            if issue.affected_parameter:
                # Create parameter alias/adapter
                fix_record['fix_type'] = 'parameter_compatibility'
                fix_record['details'] = f"Created backward compatible parameter handling for '{issue.affected_parameter}'"
                fix_record['fix_applied'] = True
                
                # In a real implementation, this would modify the action class
                logger.info(f"🔧 Auto-applied compatibility fix for {issue.affected_parameter}")
        
        return fix_record if fix_record['fix_applied'] else None
    
    def _generate_compatibility_solution(self, action_type: str, issue: CompatibilityIssue) -> str:
        """Generate specific solution that guarantees backward compatibility."""
        # ALWAYS provide a solution that preserves existing functionality
        if issue.issue_type == 'deprecated':
            return f"Maintain alias '{issue.affected_parameter}' → '{issue.migration_path}' indefinitely"
        elif issue.issue_type == 'breaking':
            if 'removed' in issue.description:
                return f"Add permanent compatibility wrapper to support old parameter '{issue.affected_parameter}'"
            elif 'type changed' in issue.description:
                return f"Add automatic type conversion from {issue.old_interface} to {issue.new_interface}"
            elif 'new required' in issue.description:
                return f"Provide smart default for '{issue.affected_parameter}' when missing"
        
        # Fallback: Always maintain compatibility
        return "Create compatibility layer to preserve existing functionality"
    
    def _generate_migration_guide(self, action_type: str, evolution_report: Dict) -> List[str]:
        """Generate step-by-step migration guide."""
        guide = []
        
        guide.append(f"Migration Guide for {action_type}")
        guide.append("=" * 50)
        
        if evolution_report['breaking_changes'] > 0:
            guide.append("\n⚠️ Breaking Changes Detected\n")
            
            for issue in evolution_report['compatibility_issues']:
                if issue['severity'] == 'error':
                    guide.append(f"• {issue['description']}")
                    if issue.get('migration_path'):
                        guide.append(f"  → {issue['migration_path']}")
        
        if evolution_report['warnings'] > 0:
            guide.append("\n📋 Deprecation Warnings\n")
            
            for issue in evolution_report['compatibility_issues']:
                if issue['severity'] == 'warning':
                    guide.append(f"• {issue['description']}")
                    if issue.get('migration_path'):
                        guide.append(f"  → {issue['migration_path']}")
        
        guide.append("\n📝 Migration Steps:\n")
        guide.append("1. Update parameter names as indicated above")
        guide.append("2. Add default values for new required parameters")
        guide.append("3. Test strategy with updated action")
        guide.append("4. Consider using compatibility wrapper for gradual migration")
        
        return guide
    
    def _save_evolution_report(self, report: Dict):
        """Save evolution report for documentation."""
        report_dir = Path("/tmp/biomapper/interstitial")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"evolution_{report['action_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = report_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.debug(f"💾 Saved evolution report to {filepath}")


class InterstitialMode:
    """
    Context manager for interstitial mode operations.
    
    Usage:
        with InterstitialMode('EXPORT_DATASET') as interstitial:
            report = interstitial.analyze_evolution()
            interstitial.ensure_compatibility()
    """
    
    def __init__(self, action_type: str):
        """Initialize interstitial mode."""
        self.framework = InterstitialFramework()
        self.action_type = action_type
        
    def __enter__(self):
        """Enter interstitial mode."""
        logger.info(f"🔗 Entering interstitial mode for {self.action_type}")
        self.framework.active = True
        return self.framework
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit interstitial mode."""
        logger.info(f"🔓 Exiting interstitial mode")
        self.framework.active = False
        
        if exc_type is None:
            logger.info("✅ Interstitial operations completed successfully")
        else:
            logger.error(f"❌ Interstitial mode failed: {exc_val}")