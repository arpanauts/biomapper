"""LLM prompt templates and generation."""
from typing import Dict, Any, List


class PromptTemplates:
    """Collection of prompt templates for different analysis types."""

    def get_pathway_analysis_prompts(self, data: Dict[str, Any]) -> List[str]:
        """Generate prompts for pathway analysis.
        
        Args:
            data: Dictionary containing:
                - mapping: Metabolite mapping results
                - spoke: SPOKE pathway analysis results
                - context: Additional context
                
        Returns:
            List of prompts for pathway analysis
        """
        prompts = []
        
        # System context prompt
        prompts.append(self._get_system_context())
        
        # Pathway analysis prompt
        prompts.append(self._format_pathway_prompt(data))
        
        # Follow-up analysis prompts
        if data.get("spoke"):
            prompts.extend(self._get_spoke_analysis_prompts(data))
            
        return prompts

    def get_interaction_analysis_prompts(self, data: Dict[str, Any]) -> List[str]:
        """Generate prompts for metabolite interaction analysis.
        
        Args:
            data: Dictionary containing:
                - mapping: Metabolite mapping results
                - spoke: Optional SPOKE analysis results
                - context: Additional context
                
        Returns:
            List of prompts for interaction analysis
        """
        prompts = []
        
        # System context
        prompts.append(self._get_system_context())
        
        # Interaction analysis
        prompts.append(self._format_interaction_prompt(data))
        
        return prompts

    def _get_system_context(self) -> str:
        """Get system context prompt."""
        return """You are an expert biochemist analyzing metabolomics data.
        Your task is to identify meaningful patterns, relationships, and insights
        from the provided metabolite data and pathway analysis results.
        Focus on biochemically relevant relationships and provide confidence
        scores for your insights."""

    def _format_pathway_prompt(self, data: Dict[str, Any]) -> str:
        """Format pathway analysis prompt."""
        # Implementation details
        pass

    def _format_interaction_prompt(self, data: Dict[str, Any]) -> str:
        """Format metabolite interaction prompt."""
        # Implementation details
        pass

    def _get_spoke_analysis_prompts(self, data: Dict[str, Any]) -> List[str]:
        """Generate SPOKE-specific analysis prompts."""
        # Implementation details
        pass
