"""
Pipeline Mode Configuration for Biological Validation

Provides simple mode configuration for the progressive metabolomics pipeline
with validation-aware settings and confidence thresholds.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pydantic import BaseModel, Field


class PipelineMode(Enum):
    """Pipeline execution modes with validation integration."""
    
    PRODUCTION = "production"           # Full pipeline with expert review flagging
    VALIDATION = "validation"           # Gold standard validation mode
    RESEARCH = "research"              # Research mode with detailed logging
    COST_OPTIMIZED = "cost_optimized"  # Skip expensive LLM calls
    

@dataclass
class StageConfig:
    """Configuration for individual pipeline stages."""
    
    enabled: bool = True
    confidence_threshold: float = 0.75  # Minimum confidence to proceed
    max_cost_per_batch: float = 5.0     # Maximum cost in USD
    timeout_seconds: int = 300          # Stage timeout
    retry_attempts: int = 2             # Retry failed operations
    

class ValidationConfig(BaseModel):
    """
    Complete validation configuration for pipeline modes.
    
    Supports the simplified column-based expert review approach with
    automatic confidence-based flagging logic.
    """
    
    # Pipeline mode settings
    mode: PipelineMode = Field(default=PipelineMode.PRODUCTION, description="Pipeline execution mode")
    
    # Stage configurations  
    nightingale_bridge: StageConfig = Field(default_factory=lambda: StageConfig(
        enabled=True, 
        confidence_threshold=0.85,
        max_cost_per_batch=0.0,  # No cost
        timeout_seconds=60
    ))
    
    fuzzy_string_match: StageConfig = Field(default_factory=lambda: StageConfig(
        enabled=True,
        confidence_threshold=0.75, 
        max_cost_per_batch=0.0,  # No cost
        timeout_seconds=120
    ))
    
    rampdb_bridge: StageConfig = Field(default_factory=lambda: StageConfig(
        enabled=True,
        confidence_threshold=0.70,
        max_cost_per_batch=1.0,  # API calls
        timeout_seconds=300
    ))
    
    llm_semantic_match: StageConfig = Field(default_factory=lambda: StageConfig(
        enabled=True,
        confidence_threshold=0.60,
        max_cost_per_batch=10.0,  # LLM calls expensive
        timeout_seconds=600
    ))
    
    # Expert review flagging settings
    enable_expert_flagging: bool = Field(default=True, description="Enable column-based expert review flagging")
    auto_accept_threshold: float = Field(default=0.85, description="Auto-accept confidence threshold")
    auto_reject_threshold: float = Field(default=0.75, description="Auto-reject confidence threshold") 
    flagging_rate_limit: float = Field(default=0.15, description="Maximum proportion to flag for review")
    
    # Validation dataset settings
    gold_standard_enabled: bool = Field(default=False, description="Use gold standard validation")
    gold_standard_path: Optional[str] = Field(default=None, description="Path to gold standard dataset")
    validation_sample_size: int = Field(default=250, description="Sample size for validation")
    
    # Performance monitoring
    enable_performance_tracking: bool = Field(default=True, description="Track performance metrics")
    cost_monitoring_enabled: bool = Field(default=True, description="Monitor API costs")
    max_total_cost: float = Field(default=50.0, description="Maximum total cost per run")
    
    # Output settings
    output_format: str = Field(default="csv", description="Output format (csv, json, both)")
    include_confidence_scores: bool = Field(default=True, description="Include confidence scores in output")
    include_stage_metadata: bool = Field(default=True, description="Include stage execution metadata")
    
    class Config:
        extra = "allow"  # Allow additional configuration fields


class PipelineModeFactory:
    """Factory for creating pre-configured pipeline modes."""
    
    @staticmethod
    def create_production_config() -> ValidationConfig:
        """Production mode: Full pipeline with expert review flagging."""
        return ValidationConfig(
            mode=PipelineMode.PRODUCTION,
            enable_expert_flagging=True,
            auto_accept_threshold=0.85,
            auto_reject_threshold=0.75,
            flagging_rate_limit=0.15,
            max_total_cost=25.0,
            llm_semantic_match=StageConfig(
                enabled=True,
                confidence_threshold=0.65,
                max_cost_per_batch=5.0,
                timeout_seconds=300
            )
        )
    
    @staticmethod 
    def create_validation_config(gold_standard_path: str) -> ValidationConfig:
        """Validation mode: Gold standard dataset validation."""
        return ValidationConfig(
            mode=PipelineMode.VALIDATION,
            gold_standard_enabled=True,
            gold_standard_path=gold_standard_path,
            validation_sample_size=250,
            enable_expert_flagging=False,  # Not needed for validation
            enable_performance_tracking=True,
            max_total_cost=10.0,
            llm_semantic_match=StageConfig(
                enabled=True,
                confidence_threshold=0.60,
                max_cost_per_batch=2.0,
                timeout_seconds=180
            )
        )
    
    @staticmethod
    def create_research_config() -> ValidationConfig:
        """Research mode: Detailed logging and analysis."""
        return ValidationConfig(
            mode=PipelineMode.RESEARCH,
            enable_expert_flagging=True,
            auto_accept_threshold=0.80,  # More conservative
            auto_reject_threshold=0.70,  # More conservative
            flagging_rate_limit=0.25,    # Higher flagging rate
            include_stage_metadata=True,
            enable_performance_tracking=True,
            max_total_cost=100.0,  # Higher cost allowance
            llm_semantic_match=StageConfig(
                enabled=True,
                confidence_threshold=0.55,  # Lower threshold for research
                max_cost_per_batch=15.0,
                timeout_seconds=900
            )
        )
    
    @staticmethod
    def create_cost_optimized_config() -> ValidationConfig:
        """Cost-optimized mode: Skip expensive LLM calls."""
        return ValidationConfig(
            mode=PipelineMode.COST_OPTIMIZED,
            enable_expert_flagging=True,
            auto_accept_threshold=0.90,  # Very high threshold
            auto_reject_threshold=0.80,
            flagging_rate_limit=0.10,    # Low flagging rate
            max_total_cost=5.0,          # Very low cost limit
            llm_semantic_match=StageConfig(
                enabled=False,           # Disable expensive LLM stage
                confidence_threshold=0.70,
                max_cost_per_batch=0.0,
                timeout_seconds=60
            )
        )
    
    @staticmethod
    def create_custom_config(**kwargs) -> ValidationConfig:
        """Create custom configuration with specified overrides."""
        base_config = PipelineModeFactory.create_production_config()
        
        # Update with custom parameters
        for key, value in kwargs.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)
        
        return base_config


class ConfigValidator:
    """Validates pipeline configuration for consistency and safety."""
    
    @staticmethod
    def validate_config(config: ValidationConfig) -> List[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        # Validate threshold relationships
        if config.auto_accept_threshold <= config.auto_reject_threshold:
            issues.append(
                f"auto_accept_threshold ({config.auto_accept_threshold}) must be > "
                f"auto_reject_threshold ({config.auto_reject_threshold})"
            )
        
        # Validate flagging rate
        if not 0.0 <= config.flagging_rate_limit <= 1.0:
            issues.append(f"flagging_rate_limit must be between 0.0 and 1.0, got {config.flagging_rate_limit}")
        
        # Validate cost limits
        if config.max_total_cost <= 0:
            issues.append(f"max_total_cost must be positive, got {config.max_total_cost}")
        
        # Validate stage configurations
        stages = [
            ("nightingale_bridge", config.nightingale_bridge),
            ("fuzzy_string_match", config.fuzzy_string_match), 
            ("rampdb_bridge", config.rampdb_bridge),
            ("llm_semantic_match", config.llm_semantic_match)
        ]
        
        for stage_name, stage_config in stages:
            if stage_config.confidence_threshold < 0 or stage_config.confidence_threshold > 1:
                issues.append(
                    f"{stage_name}.confidence_threshold must be between 0 and 1, "
                    f"got {stage_config.confidence_threshold}"
                )
            
            if stage_config.timeout_seconds <= 0:
                issues.append(
                    f"{stage_name}.timeout_seconds must be positive, "
                    f"got {stage_config.timeout_seconds}"
                )
        
        # Validate gold standard settings
        if config.gold_standard_enabled and not config.gold_standard_path:
            issues.append("gold_standard_path required when gold_standard_enabled=True")
        
        return issues
    
    @staticmethod
    def validate_and_raise(config: ValidationConfig) -> None:
        """Validate configuration and raise ValueError if invalid."""
        issues = ConfigValidator.validate_config(config)
        if issues:
            raise ValueError(f"Invalid configuration: {'; '.join(issues)}")


# Pre-configured pipeline modes for common use cases
PRODUCTION_MODE = PipelineModeFactory.create_production_config()
VALIDATION_MODE_TEMPLATE = lambda path: PipelineModeFactory.create_validation_config(path)
RESEARCH_MODE = PipelineModeFactory.create_research_config()
COST_OPTIMIZED_MODE = PipelineModeFactory.create_cost_optimized_config()