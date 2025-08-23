"""
Automated Surgical Framework for BiOMapper Action Refinement.

This framework enables safe, surgical modifications to action internals
without affecting pipeline integration or output structures.

Designed to be agent-driven and transparent to users.
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import logging
from copy import deepcopy

from actions.registry import ACTION_REGISTRY
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


@dataclass
class ActionSnapshot:
    """Captures baseline behavior of an action for comparison."""
    
    action_type: str
    timestamp: str
    context_inputs: Dict[str, Any]
    context_outputs: Dict[str, Any]
    output_structure: Dict[str, str]  # file -> structure hash
    context_keys_read: List[str]
    context_keys_written: List[str]
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot for storage."""
        return {
            'action_type': self.action_type,
            'timestamp': self.timestamp,
            'context_inputs': self._serialize_context(self.context_inputs),
            'context_outputs': self._serialize_context(self.context_outputs),
            'output_structure': self.output_structure,
            'context_keys_read': self.context_keys_read,
            'context_keys_written': self.context_keys_written,
            'execution_metadata': self.execution_metadata
        }
    
    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Safely serialize context data."""
        serialized = {}
        for key, value in context.items():
            if isinstance(value, pd.DataFrame):
                serialized[key] = {
                    'type': 'DataFrame',
                    'shape': value.shape,
                    'columns': list(value.columns),
                    'dtypes': {col: str(dtype) for col, dtype in value.dtypes.items()}
                }
            elif isinstance(value, list):
                serialized[key] = {
                    'type': 'list',
                    'length': len(value),
                    'sample': value[:3] if len(value) > 3 else value
                }
            else:
                serialized[key] = {'type': type(value).__name__, 'value': str(value)[:100]}
        return serialized


class SurgicalValidator:
    """Validates that changes are truly surgical (internal only)."""
    
    @staticmethod
    def validate_context_interface(before: ActionSnapshot, after: ActionSnapshot) -> Tuple[bool, str]:
        """Ensure context read/write patterns unchanged."""
        # Check read keys
        if set(before.context_keys_read) != set(after.context_keys_read):
            return False, f"Context read keys changed: {before.context_keys_read} -> {after.context_keys_read}"
        
        # Check write keys
        if set(before.context_keys_written) != set(after.context_keys_written):
            return False, f"Context write keys changed: {before.context_keys_written} -> {after.context_keys_written}"
        
        return True, "Context interface preserved"
    
    @staticmethod
    def validate_output_structure(before: ActionSnapshot, after: ActionSnapshot) -> Tuple[bool, str]:
        """Ensure output file structures unchanged."""
        for file_key, before_hash in before.output_structure.items():
            if file_key not in after.output_structure:
                return False, f"Output file missing: {file_key}"
            
            if before_hash != after.output_structure[file_key]:
                return False, f"Output structure changed for: {file_key}"
        
        return True, "Output structures preserved"
    
    @staticmethod
    def validate_data_types(before: ActionSnapshot, after: ActionSnapshot) -> Tuple[bool, str]:
        """Ensure data types in context unchanged."""
        for key in before.context_outputs:
            if key not in after.context_outputs:
                return False, f"Missing output key: {key}"
            
            before_type = before.context_outputs[key].get('type')
            after_type = after.context_outputs[key].get('type')
            
            if before_type != after_type:
                return False, f"Type changed for {key}: {before_type} -> {after_type}"
        
        return True, "Data types preserved"


class ActionSurgeon:
    """
    Main surgical framework for safe action refinement.
    
    Automatically activated by agent when detecting surgical intent.
    """
    
    # Patterns that trigger surgical mode
    SURGICAL_PATTERNS = [
        r"surgical",  # Direct framework name trigger
        r"fix.*(counting|calculation|logic|statistics).*in.*(action|visualization)",
        r"(update|refine|correct|adjust).*without.*(breaking|affecting|changing).*pipeline",
        r"(internal|surgical|careful).*change",
        r"preserve.*structure.*while.*(fixing|updating|correcting)",
        r"entity.*counting.*(wrong|incorrect|inflated)",
        r"statistics.*(show|display|count).*(wrong|incorrect|inflated|expanded)",
        r"output.*correct.*but.*numbers.*wrong",
        r"counting.*expanded.*records.*instead.*unique",
        r"should.*show.*unique.*(entities|proteins|metabolites)",
        r"\d+.*but.*should.*(be|show).*\d+"  # "3675 but should be 1200"
    ]
    
    def __init__(self, action_type: str):
        """Initialize surgeon for specific action type."""
        self.action_type = action_type
        self.action_class = self._load_action_class()
        self.isolation_dir = Path(f"/tmp/biomapper/surgical/{action_type}")
        self.isolation_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_snapshot: Optional[ActionSnapshot] = None
        self.modified_snapshot: Optional[ActionSnapshot] = None
        
        logger.info(f"🔒 Surgical framework initialized for {action_type}")
    
    def _load_action_class(self):
        """Load the action class from registry."""
        if self.action_type not in ACTION_REGISTRY:
            raise ValueError(f"Action {self.action_type} not found in registry")
        return ACTION_REGISTRY[self.action_type]
    
    @classmethod
    def should_use_surgical_mode(cls, user_message: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if surgical mode needed based on user intent.
        
        Called automatically by agent for every user message.
        """
        message_lower = user_message.lower()
        
        # Check for surgical patterns
        for pattern in cls.SURGICAL_PATTERNS:
            if re.search(pattern, message_lower):
                # Try to extract action type from message
                action_type = cls._extract_action_type(user_message)
                if action_type:
                    logger.info(f"✅ Surgical mode triggered for {action_type}")
                    return True, action_type
        
        return False, None
    
    @classmethod
    def _extract_action_type(cls, message: str) -> Optional[str]:
        """Extract action type from user message."""
        # Look for explicit action names
        for action_name in ACTION_REGISTRY.keys():
            if action_name.lower() in message.lower():
                return action_name
        
        # Look for common references
        if any(word in message.lower() for word in ['visualization', 'visualize', 'chart', 'statistics']):
            return 'GENERATE_MAPPING_VISUALIZATIONS'
        if any(word in message.lower() for word in ['export', 'save', 'output']):
            return 'EXPORT_DATASET'
        
        return None
    
    def capture_baseline(self, test_context: Optional[Dict[str, Any]] = None) -> ActionSnapshot:
        """
        Capture baseline behavior with real or test context.
        
        This establishes the 'before' state for comparison.
        """
        logger.info(f"📸 Capturing baseline for {self.action_type}")
        
        # Use test context or load from real pipeline
        if test_context is None:
            test_context = self._load_test_context()
        
        # Track context access
        context_tracker = ContextTracker(test_context)
        
        # Run action with tracking
        action_instance = self.action_class()
        params = self._get_test_params()
        
        # Execute and track - handle different action signatures
        try:
            # Try TypedStrategyAction signature first
            result = action_instance.execute(
                action_params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context_tracker.tracked_context
            )
        except TypeError:
            # Fall back to simpler signature
            result = action_instance.execute(params, context_tracker.tracked_context)
        
        # Capture snapshot
        self.baseline_snapshot = ActionSnapshot(
            action_type=self.action_type,
            timestamp=datetime.now().isoformat(),
            context_inputs=context_tracker.get_reads(),
            context_outputs=context_tracker.get_writes(),
            output_structure=self._hash_output_structures(context_tracker.tracked_context),
            context_keys_read=list(context_tracker.keys_read),
            context_keys_written=list(context_tracker.keys_written),
            execution_metadata={'result': str(result)}
        )
        
        # Save snapshot
        self._save_snapshot(self.baseline_snapshot, 'baseline')
        
        logger.info(f"✅ Baseline captured: {len(self.baseline_snapshot.context_keys_read)} reads, "
                   f"{len(self.baseline_snapshot.context_keys_written)} writes")
        
        return self.baseline_snapshot
    
    def validate_surgical_changes(self, modified_action_class) -> Tuple[bool, List[str]]:
        """
        Validate that changes are truly surgical.
        
        Returns (is_safe, validation_messages)
        """
        logger.info(f"🔍 Validating surgical changes for {self.action_type}")
        
        if not self.baseline_snapshot:
            return False, ["No baseline snapshot available"]
        
        # Run modified action with same test context
        test_context = self._load_test_context()
        context_tracker = ContextTracker(test_context)
        
        # Execute modified version
        modified_instance = modified_action_class()
        params = self._get_test_params()
        
        # Handle different action signatures
        try:
            # Try TypedStrategyAction signature first
            result = modified_instance.execute(
                action_params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context_tracker.tracked_context
            )
        except TypeError:
            # Fall back to simpler signature
            result = modified_instance.execute(params, context_tracker.tracked_context)
        
        # Capture modified snapshot
        self.modified_snapshot = ActionSnapshot(
            action_type=self.action_type,
            timestamp=datetime.now().isoformat(),
            context_inputs=context_tracker.get_reads(),
            context_outputs=context_tracker.get_writes(),
            output_structure=self._hash_output_structures(context_tracker.tracked_context),
            context_keys_read=list(context_tracker.keys_read),
            context_keys_written=list(context_tracker.keys_written),
            execution_metadata={'result': str(result)}
        )
        
        # Run validation checks
        validator = SurgicalValidator()
        validation_results = []
        all_valid = True
        
        # Check context interface
        valid, msg = validator.validate_context_interface(self.baseline_snapshot, self.modified_snapshot)
        validation_results.append(f"{'✅' if valid else '❌'} Context Interface: {msg}")
        all_valid = all_valid and valid
        
        # Check output structure
        valid, msg = validator.validate_output_structure(self.baseline_snapshot, self.modified_snapshot)
        validation_results.append(f"{'✅' if valid else '❌'} Output Structure: {msg}")
        all_valid = all_valid and valid
        
        # Check data types
        valid, msg = validator.validate_data_types(self.baseline_snapshot, self.modified_snapshot)
        validation_results.append(f"{'✅' if valid else '❌'} Data Types: {msg}")
        all_valid = all_valid and valid
        
        # Save comparison
        self._save_comparison()
        
        return all_valid, validation_results
    
    def _load_test_context(self) -> Dict[str, Any]:
        """Load realistic test context from saved pipeline run."""
        # Try to load from saved context
        context_file = self.isolation_dir / "test_context.json"
        if context_file.exists():
            with open(context_file, 'r') as f:
                return json.load(f)
        
        # Create minimal test context
        return self._create_minimal_test_context()
    
    def _create_minimal_test_context(self) -> Dict[str, Any]:
        """Create minimal test context for action."""
        # This would be customized per action type
        # For now, create generic context
        return {
            'datasets': {},
            'output_files': [],
            'statistics': {},
            'progressive_stats': {}
        }
    
    def _get_test_params(self) -> Dict[str, Any]:
        """Get test parameters for action."""
        # This would be customized per action type
        # For now, return minimal params
        if self.action_type == 'GENERATE_MAPPING_VISUALIZATIONS':
            return {
                'input_key': 'test_data',
                'directory_path': str(self.isolation_dir),
                'generate_statistics': True,
                'generate_summary': True,
                'generate_json_report': True
            }
        return {}
    
    def _hash_output_structures(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Create structural hashes of output files."""
        hashes = {}
        
        # Hash output files if present
        output_files = context.get('output_files', [])
        if isinstance(output_files, list):
            for file_path in output_files:
                if Path(file_path).exists():
                    # Hash file structure (not content)
                    structure_hash = self._hash_file_structure(file_path)
                    hashes[file_path] = structure_hash
        
        return hashes
    
    def _hash_file_structure(self, file_path: str) -> str:
        """Hash the structure of a file (not its content)."""
        path = Path(file_path)
        if not path.exists():
            return "missing"
        
        # For JSON files, hash keys
        if path.suffix == '.json':
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    keys = self._extract_keys_recursive(data)
                    return hashlib.md5(str(sorted(keys)).encode()).hexdigest()
            except:
                pass
        
        # For other files, hash format indicators
        return hashlib.md5(f"{path.suffix}:{path.stat().st_size}".encode()).hexdigest()
    
    def _extract_keys_recursive(self, obj: Any, prefix: str = "") -> List[str]:
        """Extract all keys from nested structure."""
        keys = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.append(full_key)
                keys.extend(self._extract_keys_recursive(v, full_key))
        elif isinstance(obj, list) and obj:
            keys.extend(self._extract_keys_recursive(obj[0], f"{prefix}[0]"))
        return keys
    
    def _save_snapshot(self, snapshot: ActionSnapshot, label: str):
        """Save snapshot to disk for debugging."""
        snapshot_file = self.isolation_dir / f"{label}_snapshot.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)
        logger.debug(f"Saved {label} snapshot to {snapshot_file}")
    
    def _save_comparison(self):
        """Save before/after comparison."""
        if not self.baseline_snapshot or not self.modified_snapshot:
            return
        
        comparison = {
            'action_type': self.action_type,
            'timestamp': datetime.now().isoformat(),
            'baseline': self.baseline_snapshot.to_dict(),
            'modified': self.modified_snapshot.to_dict(),
            'changes': {
                'context_reads_changed': 
                    set(self.modified_snapshot.context_keys_read) != set(self.baseline_snapshot.context_keys_read),
                'context_writes_changed': 
                    set(self.modified_snapshot.context_keys_written) != set(self.baseline_snapshot.context_keys_written),
                'output_structure_changed': 
                    self.modified_snapshot.output_structure != self.baseline_snapshot.output_structure
            }
        }
        
        comparison_file = self.isolation_dir / "surgical_comparison.json"
        with open(comparison_file, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        logger.info(f"💾 Comparison saved to {comparison_file}")


class ContextTracker:
    """Tracks context access patterns during action execution."""
    
    def __init__(self, base_context: Dict[str, Any]):
        """Initialize tracker with base context."""
        self.base_context = deepcopy(base_context)
        self.tracked_context = UniversalContext.wrap(base_context)
        self.keys_read = set()
        self.keys_written = set()
        self.reads = {}
        self.writes = {}
        
        # Monkey-patch context methods to track access
        self._patch_context_methods()
    
    def _patch_context_methods(self):
        """Patch context methods to track access."""
        original_get = self.tracked_context.get
        original_set = self.tracked_context.set
        
        def tracked_get(key, default=None):
            self.keys_read.add(key)
            value = original_get(key, default)
            self.reads[key] = value
            return value
        
        def tracked_set(key, value):
            self.keys_written.add(key)
            self.writes[key] = value
            return original_set(key, value)
        
        self.tracked_context.get = tracked_get
        self.tracked_context.set = tracked_set
    
    def get_reads(self) -> Dict[str, Any]:
        """Get all context reads."""
        return self.reads
    
    def get_writes(self) -> Dict[str, Any]:
        """Get all context writes."""
        return self.writes


class SurgicalMode:
    """
    Context manager for surgical mode operations.
    
    Usage:
        with SurgicalMode('GENERATE_MAPPING_VISUALIZATIONS') as surgeon:
            # Make surgical changes
            surgeon.validate()
    """
    
    def __init__(self, action_type: str):
        """Initialize surgical mode."""
        self.surgeon = ActionSurgeon(action_type)
        
    def __enter__(self):
        """Enter surgical mode."""
        logger.info(f"🔒 Entering surgical mode for {self.surgeon.action_type}")
        self.surgeon.capture_baseline()
        return self.surgeon
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit surgical mode."""
        logger.info(f"🔓 Exiting surgical mode for {self.surgeon.action_type}")
        if exc_type is None:
            logger.info("✅ Surgical mode completed successfully")
        else:
            logger.error(f"❌ Surgical mode failed: {exc_val}")