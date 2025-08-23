"""
Phased Rollout Configuration for Metabolomics Pipeline

Implements conservative phased deployment strategy based on Gemini's expert recommendations.
Start ultra-conservative, then gradually relax based on real-world feedback.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class RolloutPhase(Enum):
    """Pipeline rollout phases."""
    
    PHASE_1A_ULTRA_CONSERVATIVE = "phase_1a_ultra_conservative"  # Week 1
    PHASE_1B_STANDARD_CONSERVATIVE = "phase_1b_standard_conservative"  # Weeks 2-4
    PHASE_2_STAGE_4_CONSIDERATION = "phase_2_stage_4_consideration"  # Month 2+
    PHASE_3_OPTIMIZED = "phase_3_optimized"  # After validation


@dataclass
class PhaseConfiguration:
    """Configuration for a specific rollout phase."""
    
    phase: RolloutPhase
    name: str
    description: str
    
    # Stage configurations
    enabled_stages: List[int]
    stage_thresholds: Dict[int, float]
    
    # Expert review settings
    auto_accept_threshold: float
    auto_reject_threshold: float
    max_flagging_rate: float
    
    # Cost and performance limits
    max_cost: float
    max_execution_time: int  # seconds
    
    # Validation requirements
    min_coverage_target: float
    max_false_positive_rate: float
    
    # Adjustment triggers
    success_criteria: Dict[str, Any]
    escalation_triggers: Dict[str, Any]


class PhasedRolloutManager:
    """Manages phased rollout of metabolomics pipeline."""
    
    def __init__(self):
        self.phases = self._initialize_phases()
        self.current_phase = RolloutPhase.PHASE_1A_ULTRA_CONSERVATIVE
        self.phase_history = []
        
    def _initialize_phases(self) -> Dict[RolloutPhase, PhaseConfiguration]:
        """Initialize all rollout phases with configurations."""
        
        phases = {}
        
        # Phase 1A: Ultra-Conservative (Week 1)
        phases[RolloutPhase.PHASE_1A_ULTRA_CONSERVATIVE] = PhaseConfiguration(
            phase=RolloutPhase.PHASE_1A_ULTRA_CONSERVATIVE,
            name="Ultra-Conservative Initial Deployment",
            description="Maximum safety with minimal flagging for initial validation",
            
            # Only Stages 1-3, no LLM
            enabled_stages=[1, 2, 3],
            stage_thresholds={
                1: 0.95,  # Direct matching - very high
                2: 0.85,  # Fuzzy matching - high
                3: 0.75,  # RampDB - moderate-high
                4: None   # Disabled
            },
            
            # Conservative review settings (10% target)
            auto_accept_threshold=0.88,  # Very high
            auto_reject_threshold=0.65,  # Moderate
            max_flagging_rate=0.10,      # Only 10% (25 metabolites)
            
            # Tight constraints
            max_cost=2.00,
            max_execution_time=45,
            
            # Conservative targets
            min_coverage_target=0.50,     # 50% minimum
            max_false_positive_rate=0.02, # 2% maximum
            
            # Success criteria for moving to next phase
            success_criteria={
                "min_runs_completed": 5,
                "avg_coverage": 0.55,
                "false_positive_rate": 0.03,
                "user_satisfaction": 0.70
            },
            
            # Triggers to stay in this phase or investigate
            escalation_triggers={
                "false_positive_rate_exceeds": 0.05,
                "coverage_below": 0.45,
                "cost_exceeds": 2.50,
                "review_workload_exceeds": 0.15
            }
        )
        
        # Phase 1B: Standard Conservative (Weeks 2-4)
        phases[RolloutPhase.PHASE_1B_STANDARD_CONSERVATIVE] = PhaseConfiguration(
            phase=RolloutPhase.PHASE_1B_STANDARD_CONSERVATIVE,
            name="Standard Conservative Deployment",
            description="Gemini-recommended production settings",
            
            # Still Stages 1-3 only
            enabled_stages=[1, 2, 3],
            stage_thresholds={
                1: 0.95,  # Keep direct matching very high
                2: 0.85,  # Keep fuzzy matching high
                3: 0.70,  # Slightly lower for RampDB
                4: None   # Still disabled
            },
            
            # Target 15% review rate
            auto_accept_threshold=0.85,  # Gemini recommendation
            auto_reject_threshold=0.60,  # Gemini recommendation
            max_flagging_rate=0.15,      # 15% (38 metabolites)
            
            # Moderate constraints
            max_cost=3.00,
            max_execution_time=60,
            
            # Realistic targets
            min_coverage_target=0.60,     # 60% target
            max_false_positive_rate=0.03, # 3% acceptable
            
            success_criteria={
                "min_runs_completed": 20,
                "avg_coverage": 0.65,
                "false_positive_rate": 0.025,
                "user_satisfaction": 0.75,
                "validation_dataset_ready": True
            },
            
            escalation_triggers={
                "false_positive_rate_exceeds": 0.05,
                "coverage_below": 0.50,
                "cost_exceeds": 3.50,
                "review_workload_exceeds": 0.20
            }
        )
        
        # Phase 2: Consider Stage 4 (Month 2+)
        phases[RolloutPhase.PHASE_2_STAGE_4_CONSIDERATION] = PhaseConfiguration(
            phase=RolloutPhase.PHASE_2_STAGE_4_CONSIDERATION,
            name="Stage 4 LLM Consideration",
            description="Carefully introduce LLM matching after validation",
            
            # Test Stage 4 with very high threshold
            enabled_stages=[1, 2, 3, 4],
            stage_thresholds={
                1: 0.95,  # Keep high
                2: 0.85,  # Keep high
                3: 0.70,  # Moderate
                4: 0.90   # Very high for LLM (Gemini recommendation)
            },
            
            # Keep conservative review
            auto_accept_threshold=0.85,
            auto_reject_threshold=0.60,
            max_flagging_rate=0.20,  # Slightly higher with Stage 4
            
            # Higher cost with LLM
            max_cost=4.00,
            max_execution_time=90,
            
            # Higher coverage target with Stage 4
            min_coverage_target=0.75,     # 75% with all stages
            max_false_positive_rate=0.03, # Keep low
            
            success_criteria={
                "min_runs_completed": 50,
                "avg_coverage": 0.80,
                "false_positive_rate": 0.02,
                "user_satisfaction": 0.80,
                "gold_standard_validated": True,
                "stage_4_accuracy": 0.85
            },
            
            escalation_triggers={
                "stage_4_hallucination_rate": 0.10,
                "false_positive_rate_exceeds": 0.05,
                "cost_exceeds": 5.00,
                "llm_errors": 3
            }
        )
        
        # Phase 3: Optimized (After full validation)
        phases[RolloutPhase.PHASE_3_OPTIMIZED] = PhaseConfiguration(
            phase=RolloutPhase.PHASE_3_OPTIMIZED,
            name="Optimized Production",
            description="Data-driven optimized thresholds after validation",
            
            # All stages with optimized thresholds
            enabled_stages=[1, 2, 3, 4],
            stage_thresholds={
                1: 0.93,  # Slightly relaxed
                2: 0.82,  # Slightly relaxed
                3: 0.68,  # Slightly relaxed
                4: 0.85   # More permissive but still high
            },
            
            # Optimized review settings
            auto_accept_threshold=0.82,
            auto_reject_threshold=0.58,
            max_flagging_rate=0.12,
            
            # Production limits
            max_cost=4.50,
            max_execution_time=90,
            
            # Production targets
            min_coverage_target=0.85,     # 85% target
            max_false_positive_rate=0.02, # 2% target achieved
            
            success_criteria={
                "stable_performance": True,
                "avg_coverage": 0.85,
                "false_positive_rate": 0.015,
                "user_satisfaction": 0.90
            },
            
            escalation_triggers={
                "performance_degradation": 0.10,
                "false_positive_spike": 0.05,
                "user_complaints": 5
            }
        )
        
        return phases
    
    def get_current_configuration(self) -> PhaseConfiguration:
        """Get configuration for current phase."""
        return self.phases[self.current_phase]
    
    def should_advance_phase(self, metrics: Dict[str, Any]) -> bool:
        """Check if metrics indicate readiness to advance to next phase."""
        
        current_config = self.get_current_configuration()
        
        # Check all success criteria
        for criterion, target in current_config.success_criteria.items():
            if criterion not in metrics:
                return False
            
            if isinstance(target, bool):
                if metrics[criterion] != target:
                    return False
            elif isinstance(target, (int, float)):
                if metrics[criterion] < target:
                    return False
        
        return True
    
    def check_escalation_triggers(self, metrics: Dict[str, Any]) -> List[str]:
        """Check if any escalation triggers are activated."""
        
        current_config = self.get_current_configuration()
        triggered = []
        
        for trigger, threshold in current_config.escalation_triggers.items():
            if trigger in metrics:
                if "exceeds" in trigger or "above" in trigger:
                    if metrics[trigger.replace("_exceeds", "").replace("_above", "")] > threshold:
                        triggered.append(f"{trigger}: {metrics[trigger]} > {threshold}")
                elif "below" in trigger:
                    if metrics[trigger.replace("_below", "")] < threshold:
                        triggered.append(f"{trigger}: {metrics[trigger]} < {threshold}")
        
        return triggered
    
    def advance_to_next_phase(self) -> bool:
        """Advance to next phase if available."""
        
        phase_order = [
            RolloutPhase.PHASE_1A_ULTRA_CONSERVATIVE,
            RolloutPhase.PHASE_1B_STANDARD_CONSERVATIVE,
            RolloutPhase.PHASE_2_STAGE_4_CONSIDERATION,
            RolloutPhase.PHASE_3_OPTIMIZED
        ]
        
        current_index = phase_order.index(self.current_phase)
        
        if current_index < len(phase_order) - 1:
            self.phase_history.append(self.current_phase)
            self.current_phase = phase_order[current_index + 1]
            return True
        
        return False
    
    def generate_phase_report(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report on current phase performance."""
        
        current_config = self.get_current_configuration()
        
        report = {
            "current_phase": self.current_phase.value,
            "phase_name": current_config.name,
            "enabled_stages": current_config.enabled_stages,
            "current_metrics": metrics,
            "success_criteria_met": self.should_advance_phase(metrics),
            "escalation_triggers": self.check_escalation_triggers(metrics),
            "recommendations": []
        }
        
        # Add recommendations
        if report["success_criteria_met"]:
            report["recommendations"].append("Ready to advance to next phase")
        
        if report["escalation_triggers"]:
            report["recommendations"].append("Review escalation triggers before proceeding")
        
        if metrics.get("false_positive_rate", 0) > current_config.max_false_positive_rate:
            report["recommendations"].append("Consider raising confidence thresholds")
        
        if metrics.get("coverage", 0) < current_config.min_coverage_target:
            report["recommendations"].append("Coverage below target - investigate unmapped metabolites")
        
        return report


# Example usage
if __name__ == "__main__":
    # Initialize rollout manager
    manager = PhasedRolloutManager()
    
    # Get current phase configuration
    current_config = manager.get_current_configuration()
    print(f"Current Phase: {current_config.name}")
    print(f"Enabled Stages: {current_config.enabled_stages}")
    print(f"Max Flagging Rate: {current_config.max_flagging_rate * 100}%")
    print(f"Auto-Accept Threshold: {current_config.auto_accept_threshold}")
    
    # Simulate metrics after Week 1
    week_1_metrics = {
        "min_runs_completed": 6,
        "avg_coverage": 0.58,
        "false_positive_rate": 0.025,
        "user_satisfaction": 0.72
    }
    
    # Check if ready to advance
    if manager.should_advance_phase(week_1_metrics):
        print("\n✓ Ready to advance to Phase 1B")
        manager.advance_to_next_phase()
    else:
        print("\n✗ Not ready to advance - continue with current phase")
    
    # Generate phase report
    report = manager.generate_phase_report(week_1_metrics)
    print(f"\nPhase Report:")
    print(f"- Success Criteria Met: {report['success_criteria_met']}")
    print(f"- Escalation Triggers: {report['escalation_triggers']}")
    print(f"- Recommendations: {report['recommendations']}")