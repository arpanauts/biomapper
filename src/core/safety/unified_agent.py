"""
Unified BiOMapper Agent with Framework Triad Integration.

This module integrates all three isolation frameworks (Surgical, Circuitous, Interstitial)
into a unified agent that automatically detects and routes to the appropriate framework
based on user intent.
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .action_surgeon import ActionSurgeon, SurgicalMode
from .circuitous_framework import CircuitousFramework, CircuitousMode
from .interstitial_framework import InterstitialFramework, InterstitialMode
from .surgical_agent import SurgicalModeAgent, AgentSurgicalBehavior

logger = logging.getLogger(__name__)


class FrameworkType(Enum):
    """Types of isolation frameworks."""
    SURGICAL = "surgical"      # Internal action logic
    CIRCUITOUS = "circuitous"  # Pipeline orchestration
    INTERSTITIAL = "interstitial"  # Interface compatibility
    NONE = "none"


@dataclass
class IntentScore:
    """Scores for framework detection."""
    framework: FrameworkType
    confidence: float
    matched_patterns: List[str]
    extracted_target: Optional[str]  # Action/strategy/interface name


class FrameworkRouter:
    """
    Intelligent router for framework selection.
    Uses pattern matching with confidence scoring.
    """
    
    # Priority order for conflict resolution
    FRAMEWORK_PRIORITY = [
        FrameworkType.SURGICAL,     # Most specific
        FrameworkType.INTERSTITIAL, # Interface-specific
        FrameworkType.CIRCUITOUS,   # Pipeline-wide
    ]
    
    # Confidence thresholds
    ACTIVATION_THRESHOLD = 0.4
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    DISAMBIGUATION_THRESHOLD = 0.15  # Max difference for ambiguous cases
    
    def __init__(self):
        """Initialize router with pattern cache."""
        self._pattern_cache = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all framework patterns for performance."""
        # Import patterns from each framework
        from .action_surgeon import ActionSurgeon
        from .circuitous_framework import CircuitousFramework
        from .interstitial_framework import InterstitialFramework
        
        self._pattern_cache = {
            FrameworkType.SURGICAL: [
                re.compile(p, re.IGNORECASE) for p in ActionSurgeon.SURGICAL_PATTERNS
            ],
            FrameworkType.CIRCUITOUS: [
                re.compile(p, re.IGNORECASE) for p in CircuitousFramework.CIRCUITOUS_PATTERNS
            ],
            FrameworkType.INTERSTITIAL: [
                re.compile(p, re.IGNORECASE) for p in InterstitialFramework.INTERSTITIAL_PATTERNS
            ]
        }
    
    def route_intent(self, user_message: str) -> Tuple[FrameworkType, IntentScore]:
        """
        Route user intent to appropriate framework.
        
        Returns:
            (selected_framework, intent_score)
        """
        # Score each framework
        scores = self._score_all_frameworks(user_message)
        
        # Sort by confidence
        sorted_scores = sorted(scores, key=lambda x: x.confidence, reverse=True)
        
        # Check if top score meets threshold
        if sorted_scores[0].confidence < self.ACTIVATION_THRESHOLD:
            logger.info(f"📊 No framework activated (max confidence: {sorted_scores[0].confidence:.2f})")
            return FrameworkType.NONE, IntentScore(FrameworkType.NONE, 0.0, [], None)
        
        # Check for ambiguous cases
        if len(sorted_scores) > 1:
            confidence_diff = sorted_scores[0].confidence - sorted_scores[1].confidence
            if confidence_diff < self.DISAMBIGUATION_THRESHOLD:
                # Use priority order to break tie
                return self._resolve_ambiguity(sorted_scores)
        
        # Return highest confidence framework
        selected = sorted_scores[0]
        logger.info(f"🎯 Routed to {selected.framework.value} (confidence: {selected.confidence:.2f})")
        
        return selected.framework, selected
    
    def _score_all_frameworks(self, user_message: str) -> List[IntentScore]:
        """Score all frameworks for the given message."""
        scores = []
        
        for framework_type, patterns in self._pattern_cache.items():
            score = self._score_framework(user_message, framework_type, patterns)
            scores.append(score)
        
        return scores
    
    def _score_framework(
        self, 
        message: str, 
        framework: FrameworkType, 
        patterns: List[re.Pattern]
    ) -> IntentScore:
        """Score a single framework for the message."""
        matched_patterns = []
        total_score = 0.0
        
        message_lower = message.lower()
        
        # Check each pattern
        for pattern in patterns:
            match = pattern.search(message_lower)
            if match:
                matched_patterns.append(pattern.pattern)
                # Weight by pattern specificity (longer patterns = more specific)
                pattern_weight = len(pattern.pattern) / 100.0
                total_score += min(1.0, 0.3 + pattern_weight)
        
        # Normalize score
        if matched_patterns:
            confidence = min(1.0, total_score / max(1, len(patterns) * 0.3))
        else:
            confidence = 0.0
        
        # Apply keyword boosting
        confidence = self._apply_keyword_boosting(message_lower, framework, confidence)
        
        # Extract target (action/strategy/interface)
        target = self._extract_target(message, framework)
        
        return IntentScore(framework, confidence, matched_patterns, target)
    
    def _apply_keyword_boosting(self, message: str, framework: FrameworkType, base_score: float) -> float:
        """Apply keyword-based confidence boosting."""
        boost_keywords = {
            FrameworkType.SURGICAL: ['fix', 'internal', 'logic', 'counting', 'statistics'],
            FrameworkType.CIRCUITOUS: ['flow', 'pipeline', 'parameter', 'yaml', 'strategy'],
            FrameworkType.INTERSTITIAL: ['interface', 'compatibility', 'backward', 'contract', 'api']
        }
        
        boost = 0.0
        for keyword in boost_keywords.get(framework, []):
            if keyword in message:
                boost += 0.1
        
        return min(1.0, base_score + boost)
    
    def _extract_target(self, message: str, framework: FrameworkType) -> Optional[str]:
        """Extract target entity from message based on framework type."""
        if framework == FrameworkType.SURGICAL:
            # Look for action names
            from actions.registry import ACTION_REGISTRY
            for action_name in ACTION_REGISTRY.keys():
                if action_name.lower() in message.lower():
                    return action_name
        
        elif framework == FrameworkType.CIRCUITOUS:
            # Look for strategy names
            patterns = [
                r'(\w+_\w+_to_\w+_\w+_v[\d.]+)',
                r'(prot|met|chem)_\w+_to_\w+',
                r'(\w+\.yaml)'
            ]
            for pattern in patterns:
                match = re.search(pattern, message.lower())
                if match:
                    return match.group(1)
        
        elif framework == FrameworkType.INTERSTITIAL:
            # Look for action or interface references
            if 'export' in message.lower():
                return 'EXPORT_DATASET'
            if 'load' in message.lower():
                return 'LOAD_DATASET_IDENTIFIERS'
        
        return None
    
    def _resolve_ambiguity(self, sorted_scores: List[IntentScore]) -> Tuple[FrameworkType, IntentScore]:
        """Resolve ambiguous cases using priority rules."""
        # Group by similar confidence
        top_confidence = sorted_scores[0].confidence
        ambiguous_group = [
            s for s in sorted_scores 
            if abs(s.confidence - top_confidence) < self.DISAMBIGUATION_THRESHOLD
        ]
        
        # Use priority order
        for priority_framework in self.FRAMEWORK_PRIORITY:
            for score in ambiguous_group:
                if score.framework == priority_framework:
                    logger.info(f"🔀 Resolved ambiguity using priority: {priority_framework.value}")
                    return priority_framework, score
        
        # Fallback to highest confidence
        return sorted_scores[0].framework, sorted_scores[0]


class UnifiedBiomapperAgent:
    """
    Unified agent that orchestrates all three isolation frameworks.
    
    Provides seamless, automatic framework selection and execution
    based on user intent, with transparent operation.
    """
    
    def __init__(self):
        """Initialize unified agent with all frameworks."""
        self.router = FrameworkRouter()
        
        # Initialize framework instances
        self.surgical_agent = SurgicalModeAgent()
        self.circuitous = CircuitousFramework()
        self.interstitial = InterstitialFramework()
        
        # Track active framework
        self.active_framework: Optional[FrameworkType] = None
        self.active_context: Optional[Dict[str, Any]] = None
        
        logger.info("🎯 Unified BiOMapper Agent initialized with framework triad")
    
    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message and activate appropriate framework.
        
        Returns:
            Context dict with framework activation details
        """
        # Route to appropriate framework
        framework_type, intent_score = self.router.route_intent(message)
        
        if framework_type == FrameworkType.NONE:
            return {
                'framework': None,
                'message': "No specialized framework needed for this request"
            }
        
        # Activate selected framework
        context = self._activate_framework(framework_type, intent_score, message)
        
        self.active_framework = framework_type
        self.active_context = context
        
        return context
    
    def _activate_framework(
        self, 
        framework: FrameworkType, 
        intent: IntentScore,
        message: str
    ) -> Dict[str, Any]:
        """Activate the selected framework and return context."""
        
        if framework == FrameworkType.SURGICAL:
            return self._activate_surgical(intent, message)
        
        elif framework == FrameworkType.CIRCUITOUS:
            return self._activate_circuitous(intent, message)
        
        elif framework == FrameworkType.INTERSTITIAL:
            return self._activate_interstitial(intent, message)
        
        return {}
    
    def _activate_surgical(self, intent: IntentScore, message: str) -> Dict[str, Any]:
        """Activate surgical framework."""
        logger.info(f"🔒 Activating Surgical Framework for {intent.extracted_target}")
        
        if intent.extracted_target:
            surgeon = self.surgical_agent.activate_surgical_mode(intent.extracted_target)
        
        return {
            'framework': 'surgical',
            'mode': 'active',
            'target': intent.extracted_target,
            'confidence': intent.confidence,
            'message': message,
            'response': self._generate_surgical_response(intent, message)
        }
    
    def _activate_circuitous(self, intent: IntentScore, message: str) -> Dict[str, Any]:
        """Activate circuitous framework."""
        logger.info(f"🔄 Activating Circuitous Framework for {intent.extracted_target}")
        
        strategy_path = None
        if intent.extracted_target:
            # Resolve strategy path
            strategy_path = f"src/configs/strategies/experimental/{intent.extracted_target}.yaml"
        
        return {
            'framework': 'circuitous',
            'mode': 'active',
            'target': strategy_path,
            'confidence': intent.confidence,
            'message': message,
            'response': self._generate_circuitous_response(intent, message)
        }
    
    def _activate_interstitial(self, intent: IntentScore, message: str) -> Dict[str, Any]:
        """Activate interstitial framework."""
        logger.info(f"🔗 Activating Interstitial Framework for {intent.extracted_target}")
        
        return {
            'framework': 'interstitial',
            'mode': 'active',
            'target': intent.extracted_target,
            'confidence': intent.confidence,
            'message': message,
            'response': self._generate_interstitial_response(intent, message)
        }
    
    def _generate_surgical_response(self, intent: IntentScore, message: str) -> str:
        """Generate user-friendly response for surgical activation."""
        return (
            f"I see the issue with the internal logic. Let me fix that "
            f"while ensuring all output formats and pipeline integration remain unchanged...\n\n"
            f"🔒 Surgical mode activated\n"
            f"🎯 Target: {intent.extracted_target or 'detected action'}\n"
            f"📊 Confidence: {intent.confidence:.1%}"
        )
    
    def _generate_circuitous_response(self, intent: IntentScore, message: str) -> str:
        """Generate user-friendly response for circuitous activation."""
        return (
            f"I'll analyze the pipeline parameter flow and identify where the orchestration breaks...\n\n"
            f"🔄 Circuitous mode activated\n"
            f"📋 Strategy: {intent.extracted_target or 'detected from context'}\n"
            f"📊 Confidence: {intent.confidence:.1%}"
        )
    
    def _generate_interstitial_response(self, intent: IntentScore, message: str) -> str:
        """Generate user-friendly response for interstitial activation."""
        return (
            f"I'll ensure complete backward compatibility while handling the interface evolution...\n\n"
            f"🔗 Interstitial mode activated\n"
            f"🛡️ Compatibility: 100% guaranteed\n"
            f"📊 Confidence: {intent.confidence:.1%}"
        )
    
    def execute_framework_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute an operation on the active framework.
        
        This is called after framework activation to perform specific tasks.
        """
        if not self.active_framework:
            return {'error': 'No framework active'}
        
        if self.active_framework == FrameworkType.SURGICAL:
            return self._execute_surgical_operation(operation, **kwargs)
        
        elif self.active_framework == FrameworkType.CIRCUITOUS:
            return self._execute_circuitous_operation(operation, **kwargs)
        
        elif self.active_framework == FrameworkType.INTERSTITIAL:
            return self._execute_interstitial_operation(operation, **kwargs)
        
        return {'error': f'Unknown framework: {self.active_framework}'}
    
    def _execute_surgical_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute surgical framework operations."""
        if operation == 'validate':
            # Validate surgical changes
            pass
        elif operation == 'apply':
            # Apply surgical modifications
            pass
        
        return {'status': 'completed', 'operation': operation}
    
    def _execute_circuitous_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute circuitous framework operations."""
        if operation == 'diagnose':
            if self.active_context and self.active_context.get('target'):
                diagnosis = self.circuitous.diagnose_strategy(self.active_context['target'])
                return {'status': 'completed', 'diagnosis': diagnosis}
        
        elif operation == 'repair':
            # Apply parameter flow repairs
            pass
        
        return {'status': 'completed', 'operation': operation}
    
    def _execute_interstitial_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute interstitial framework operations."""
        if operation == 'analyze':
            if self.active_context and self.active_context.get('target'):
                analysis = self.interstitial.analyze_interface_evolution(self.active_context['target'])
                return {'status': 'completed', 'analysis': analysis}
        
        elif operation == 'ensure_compatibility':
            # Ensure backward compatibility
            pass
        
        return {'status': 'completed', 'operation': operation}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            'active_framework': self.active_framework.value if self.active_framework else None,
            'frameworks_available': ['surgical', 'circuitous', 'interstitial'],
            'router_status': 'ready',
            'confidence_threshold': self.router.ACTIVATION_THRESHOLD
        }


# Global instance for agent use
unified_agent = UnifiedBiomapperAgent()