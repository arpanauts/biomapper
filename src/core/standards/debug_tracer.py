from typing import Set, Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path

class DebugTracer:
    """Trace specific identifiers through the pipeline"""
    
    def __init__(self, trace_identifiers: Optional[Set[str]] = None):
        self.trace_identifiers = trace_identifiers or set()
        self.trace_log = []
        self.enabled = bool(trace_identifiers)
        
    def add_identifier(self, identifier: str):
        """Add identifier to trace list"""
        self.trace_identifiers.add(identifier)
        self.enabled = True
        
    def should_trace(self, value: Any) -> bool:
        """Check if value should be traced"""
        if not self.enabled:
            return False
            
        str_value = str(value)
        return any(tid in str_value for tid in self.trace_identifiers)
    
    def trace(self, 
              identifier: str,
              action: str,
              phase: str,
              details: Dict[str, Any]):
        """Log trace information for identifier"""
        if identifier not in self.trace_identifiers:
            return
            
        entry = {
            'timestamp': datetime.now().isoformat(),
            'identifier': identifier,
            'action': action,
            'phase': phase,
            'details': details
        }
        self.trace_log.append(entry)
        
        # Also log to console
        print(f"🔍 TRACE [{identifier}] {action}.{phase}: {details}")
    
    def save_trace(self, filepath: str):
        """Save trace log to file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.trace_log, f, indent=2, default=str)
            
    def get_identifier_journey(self, identifier: str) -> List[Dict]:
        """Get all trace entries for specific identifier"""
        return [e for e in self.trace_log if e['identifier'] == identifier]

class ActionDebugMixin:
    """Mixin for actions to add debug tracing"""
    
    def __init__(self):
        self.tracer: Optional[DebugTracer] = None
        super().__init__()
        
    def setup_tracing(self, identifiers: Set[str]):
        """Setup tracing for specific identifiers"""
        self.tracer = DebugTracer(identifiers)
        
    def trace_if_relevant(self, 
                         value: Any,
                         action: str,
                         phase: str,
                         **details):
        """Trace if value contains tracked identifier"""
        if self.tracer and self.tracer.should_trace(value):
            # Find which identifier is relevant
            for tid in self.tracer.trace_identifiers:
                if tid in str(value):
                    self.tracer.trace(tid, action, phase, details)