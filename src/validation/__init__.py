"""
Biological Validation Framework for Biomapper

This module provides simplified column-based expert review flagging and validation
infrastructure for the progressive metabolomics mapping pipeline.

Key Components:
- Gold standard dataset curation with stratified sampling
- Column-based expert review flagging (no complex web dashboard)
- Simple review tracking and documentation
- ROC-based confidence threshold optimization
- Performance and cost validation

Strategic Approach:
- Phase 1: Simplified flagging system for rapid production deployment
- Phase 2: Enhanced web dashboard (future enhancement)
"""

# Core validation components
from .pipeline_modes import PipelineMode, ValidationConfig, PipelineModeFactory
from .flagging_logic import ExpertReviewFlagger, FlaggingCategory, FlaggingDecision
from .gold_standard_curator import GoldStandardCurator, MetaboliteClass, GoldStandardDataset
from .threshold_optimizer import ConfidenceThresholdOptimizer, ThresholdResult

__all__ = [
    # Pipeline configuration
    'PipelineMode',
    'ValidationConfig', 
    'PipelineModeFactory',
    
    # Expert review flagging
    'ExpertReviewFlagger',
    'FlaggingCategory',
    'FlaggingDecision',
    
    # Gold standard curation
    'GoldStandardCurator',
    'MetaboliteClass',
    'GoldStandardDataset',
    
    # Threshold optimization
    'ConfidenceThresholdOptimizer',
    'ThresholdResult'
]