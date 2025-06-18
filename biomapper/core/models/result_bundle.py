from datetime import datetime
from typing import List, Dict, Any, Optional

from biomapper.core.utils.time_utils import get_current_utc_time


class MappingResultBundle:
    """Comprehensive result object for strategy execution tracking."""

    def __init__(self, strategy_name: str, initial_identifiers: List[str], source_ontology_type: Optional[str] = None, target_ontology_type: Optional[str] = None):
        """Initialize the result bundle for a strategy execution.

        Args:
            strategy_name: Name of the strategy being executed
            initial_identifiers: List of starting identifiers
            source_ontology_type: Source ontology type
            target_ontology_type: Target ontology type
        """
        self.strategy_name = strategy_name
        self.initial_identifiers = initial_identifiers.copy()
        self.source_ontology_type = source_ontology_type
        self.target_ontology_type = target_ontology_type

        # Current state
        self.current_identifiers = initial_identifiers.copy()
        self.current_ontology_type = source_ontology_type

        # Execution tracking
        self.start_time = get_current_utc_time()
        self.end_time: Optional[datetime] = None
        self.execution_status = "in_progress"  # in_progress, completed, failed
        self.error: Optional[str] = None

        # Step-by-step tracking
        self.step_results: List[Dict[str, Any]] = []
        self.provenance: List[Dict[str, Any]] = []

        # Summary statistics
        self.total_steps = 0
        self.completed_steps = 0
        self.failed_steps = 0

    def add_step_result(self, step_id: str, step_description: str, action_type: str,
                        input_identifiers: List[str], output_identifiers: List[str],
                        status: str, details: Dict[str, Any], error: Optional[str] = None,
                        output_ontology_type: Optional[str] = None):
        """Add the result of a step execution.

        Args:
            step_id: Unique identifier for the step
            step_description: Human-readable description
            action_type: Type of action performed
            input_identifiers: Identifiers before step
            output_identifiers: Identifiers after step
            status: Status of step execution (success, failed, not_implemented)
            details: Additional details about the step execution
            error: Error message if step failed
            output_ontology_type: Updated ontology type after step
        """
        step_result = {
            "step_id": step_id,
            "description": step_description,
            "action_type": action_type,
            "input_count": len(input_identifiers),
            "output_count": len(output_identifiers),
            "status": status,
            "details": details,
            "timestamp": get_current_utc_time(),
            "error": error
        }

        # Add provenance information
        provenance_entry = {
            "step_id": step_id,
            "action_type": action_type,
            "input_identifiers": input_identifiers[:10],  # Sample for provenance
            "output_identifiers": output_identifiers[:10],  # Sample for provenance
            "input_ontology_type": self.current_ontology_type,
            "output_ontology_type": output_ontology_type or self.current_ontology_type,
            "resources_used": details.get("resources_used", []),
            "timestamp": get_current_utc_time()
        }

        self.step_results.append(step_result)
        self.provenance.append(provenance_entry)

        # Update current state
        self.current_identifiers = output_identifiers
        if output_ontology_type:
            self.current_ontology_type = output_ontology_type

        # Update statistics
        if status == "success":
            self.completed_steps += 1
        elif status in ["failed", "error"]:
            self.failed_steps += 1

    def finalize(self, status: str = "completed", error: Optional[str] = None):
        """Finalize the result bundle.

        Args:
            status: Final execution status
            error: Error message if execution failed
        """
        self.end_time = get_current_utc_time()
        self.execution_status = status
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result bundle to a dictionary.

        Returns:
            Dictionary representation of the result bundle
        """
        return {
            "strategy_name": self.strategy_name,
            "execution_status": self.execution_status,
            "error": self.error,
            "initial_identifiers_count": len(self.initial_identifiers),
            "final_identifiers_count": len(self.current_identifiers),
            "source_ontology_type": self.source_ontology_type,
            "target_ontology_type": self.target_ontology_type,
            "current_ontology_type": self.current_ontology_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "step_results": self.step_results,
            "provenance": self.provenance,
            "final_identifiers": self.current_identifiers[:100]  # Sample of final identifiers
        }
