"""
Agent integration for automatic surgical mode activation.

This module provides the agent-side logic for detecting when surgical
modifications are needed and transparently activating the framework.
"""

import logging
from typing import Optional, Tuple, Dict, Any, Callable
from functools import wraps

from .action_surgeon import ActionSurgeon, SurgicalMode

logger = logging.getLogger(__name__)


class SurgicalModeAgent:
    """
    Agent-side surgical mode manager.
    
    Automatically detects when surgical refinement is needed
    and transparently activates safety framework.
    """
    
    def __init__(self):
        """Initialize surgical mode agent."""
        self.active_surgeon: Optional[ActionSurgeon] = None
        self.mode_active = False
        
    def process_user_intent(self, user_message: str) -> Tuple[bool, Optional[str]]:
        """
        Process user message to detect surgical intent.
        
        Returns:
            (should_use_surgical, action_type)
        """
        # Check if surgical mode needed
        needs_surgical, action_type = ActionSurgeon.should_use_surgical_mode(user_message)
        
        if needs_surgical:
            logger.info(f"🎯 Surgical intent detected for {action_type}")
            logger.info(f"📝 User message: {user_message[:100]}...")
            
        return needs_surgical, action_type
    
    def activate_surgical_mode(self, action_type: str) -> ActionSurgeon:
        """
        Activate surgical mode for specified action.
        
        This is transparent to the user.
        """
        if self.mode_active:
            logger.warning("Surgical mode already active")
            return self.active_surgeon
        
        logger.info(f"🔒 Activating surgical mode for {action_type}")
        
        self.active_surgeon = ActionSurgeon(action_type)
        self.mode_active = True
        
        # Capture baseline automatically
        self.active_surgeon.capture_baseline()
        
        return self.active_surgeon
    
    def deactivate_surgical_mode(self):
        """Deactivate surgical mode."""
        if not self.mode_active:
            return
        
        logger.info("🔓 Deactivating surgical mode")
        self.active_surgeon = None
        self.mode_active = False
    
    def validate_changes(self, modified_action_class) -> Tuple[bool, list]:
        """
        Validate that changes are safe.
        
        Returns:
            (is_safe, validation_messages)
        """
        if not self.active_surgeon:
            return False, ["No active surgical session"]
        
        return self.active_surgeon.validate_surgical_changes(modified_action_class)
    
    def get_user_friendly_status(self) -> str:
        """
        Get user-friendly status message.
        
        This is what the user sees, hiding complexity.
        """
        if not self.mode_active:
            return ""
        
        return (
            f"I'm working on refining {self.active_surgeon.action_type} "
            f"while preserving all output structures and pipeline integration..."
        )


def surgical_safety_wrapper(action_class):
    """
    Decorator that automatically wraps action modifications with surgical safety.
    
    Applied transparently by the agent when modifying actions.
    """
    class SurgicalSafeWrapper(action_class):
        """Wrapped version with surgical safety checks."""
        
        def execute(self, params, context):
            """Execute with automatic safety validation."""
            # Check if we're in surgical mode
            if hasattr(self, '_surgical_mode') and self._surgical_mode:
                logger.info(f"🛡️ Executing {self.__class__.__name__} in surgical mode")
                
                # Track context access
                from .action_surgeon import ContextTracker
                tracker = ContextTracker(context)
                
                # Execute with tracking
                result = super().execute(params, tracker.tracked_context)
                
                # Log access patterns for validation
                logger.debug(f"Context reads: {tracker.keys_read}")
                logger.debug(f"Context writes: {tracker.keys_written}")
                
                return result
            else:
                # Normal execution
                return super().execute(params, context)
    
    return SurgicalSafeWrapper


class AgentSurgicalBehavior:
    """
    Defines agent behavioral patterns for surgical mode.
    
    This encapsulates the decision logic for when and how
    the agent uses surgical mode.
    """
    
    # User phrases that trigger surgical mode
    TRIGGER_PHRASES = {
        'fix_internal': [
            'fix the counting',
            'statistics are wrong',
            'numbers are inflated',
            'counting expanded records',
            'should show unique'
        ],
        'preserve_structure': [
            'without breaking',
            'keep the same format',
            'preserve the output',
            'dont change the structure',
            'maintain compatibility'
        ],
        'surgical_explicit': [
            'surgical change',
            'careful modification',
            'internal fix only',
            'refine the logic'
        ]
    }
    
    # Agent response templates
    RESPONSES = {
        'activation': (
            "I see the issue with {issue_description}. Let me fix that "
            "while ensuring all output formats and pipeline integration remain unchanged..."
        ),
        'validation_success': (
            "✅ Fixed! The {change_description} has been corrected. "
            "All output files maintain their original structure and the pipeline continues to work as expected."
        ),
        'validation_failure': (
            "I attempted to fix {issue_description}, but the changes would affect "
            "{affected_component}. Let me try a different approach..."
        ),
        'completion': (
            "The refinement is complete. {summary_of_changes} "
            "The pipeline integration and output structures are preserved."
        )
    }
    
    @classmethod
    def should_activate(cls, user_message: str) -> bool:
        """Determine if surgical mode should activate."""
        message_lower = user_message.lower()
        
        # Check trigger phrases
        for category, phrases in cls.TRIGGER_PHRASES.items():
            if any(phrase in message_lower for phrase in phrases):
                return True
        
        # Check for action-specific issues
        if 'visualization' in message_lower and any(
            word in message_lower for word in ['count', 'statistic', 'number', 'total']
        ):
            return True
        
        return False
    
    @classmethod
    def generate_response(cls, stage: str, **kwargs) -> str:
        """Generate appropriate user response for surgical operation stage."""
        template = cls.RESPONSES.get(stage, "Processing your request...")
        return template.format(**kwargs)


class AutoSurgicalFramework:
    """
    Main framework class that orchestrates automatic surgical operations.
    
    This is the top-level interface used by the BiOMapper agent.
    """
    
    def __init__(self):
        """Initialize the automatic surgical framework."""
        self.agent = SurgicalModeAgent()
        self.behavior = AgentSurgicalBehavior()
        
    def process_user_message(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Process user message and return surgical context if needed.
        
        Returns:
            None if no surgical mode needed, or dict with surgical context
        """
        # Check if surgical mode needed
        needs_surgical, action_type = self.agent.process_user_intent(message)
        
        if not needs_surgical:
            return None
        
        # Prepare surgical context for agent
        return {
            'mode': 'surgical',
            'action_type': action_type,
            'user_message': message,
            'framework': self,
            'initial_response': self.behavior.generate_response(
                'activation',
                issue_description=self._extract_issue_description(message)
            )
        }
    
    def execute_surgical_modification(
        self, 
        action_type: str, 
        modification_func: Callable,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Execute a surgical modification with full safety checks.
        
        Args:
            action_type: The action to modify
            modification_func: Function that performs the modification
            user_message: Original user message for context
            
        Returns:
            Result dictionary with status and details
        """
        # Activate surgical mode
        surgeon = self.agent.activate_surgical_mode(action_type)
        
        try:
            # Apply modification (this would be the actual code change)
            modified_action = modification_func(action_type)
            
            # Validate changes
            is_safe, validation_messages = self.agent.validate_changes(modified_action)
            
            if is_safe:
                # Generate success response
                response = self.behavior.generate_response(
                    'validation_success',
                    change_description=self._extract_change_description(user_message)
                )
                
                return {
                    'success': True,
                    'response': response,
                    'validation': validation_messages,
                    'modified_action': modified_action
                }
            else:
                # Generate failure response
                response = self.behavior.generate_response(
                    'validation_failure',
                    issue_description=self._extract_issue_description(user_message),
                    affected_component=self._identify_affected_component(validation_messages)
                )
                
                return {
                    'success': False,
                    'response': response,
                    'validation': validation_messages,
                    'retry_possible': True
                }
                
        finally:
            # Always deactivate surgical mode
            self.agent.deactivate_surgical_mode()
    
    def _extract_issue_description(self, message: str) -> str:
        """Extract issue description from user message."""
        # Simple extraction logic - could be enhanced with NLP
        if 'counting' in message.lower():
            return "incorrect counting logic"
        elif 'statistics' in message.lower():
            return "statistics calculation"
        elif 'format' in message.lower():
            return "output formatting"
        return "the identified issue"
    
    def _extract_change_description(self, message: str) -> str:
        """Extract change description from user message."""
        if 'entity' in message.lower() or 'unique' in message.lower():
            return "entity counting logic"
        elif 'statistics' in message.lower():
            return "statistics calculation"
        return "internal logic"
    
    def _identify_affected_component(self, validation_messages: list) -> str:
        """Identify what component would be affected by failed changes."""
        for msg in validation_messages:
            if 'Context' in msg:
                return "the context interface"
            elif 'Output' in msg:
                return "the output structure"
            elif 'Type' in msg:
                return "data types"
        return "pipeline integration"


# Global instance for agent use
surgical_framework = AutoSurgicalFramework()