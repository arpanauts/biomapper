# AI-Native Development Workflow with Claude Code

## Overview

This document guides developers in using Claude Code to extend BioMapper with new strategies and action types, demonstrating the AI-native development experience that sets BioMapper apart.

## AI-Native Development Philosophy

### Traditional Workflow
1. Read documentation
2. Study existing code
3. Write new code
4. Debug errors
5. Test manually
6. Iterate slowly

### BioMapper AI-Native Workflow
1. Describe biological goal to Claude
2. Claude generates strategy/action with tests
3. Claude validates against benchmarks
4. Claude optimizes based on results
5. Claude documents for reproducibility

## Creating New Strategies with Claude

### Example 1: Metabolomics Harmonization

**Developer Input:**
```
I need to harmonize metabolite data from three different platforms:
- UKBB NMR data with Nightingale nomenclature
- Arivale LC-MS data with HMDB IDs
- Israeli10K with mixed nomenclature

Goal: Create unified dataset with >70% overlap
```

**Claude Response Process:**
```yaml
# Claude analyzes the requirements and generates:
name: THREE_PLATFORM_METABOLOMICS_HARMONIZATION
description: AI-generated strategy for harmonizing metabolomics data

actions:
  # Stage 1: Load and standardize
  - action_type: LOAD_DATASET_IDENTIFIERS
    params:
      dataset_files:
        ukbb: "${DATA_DIR}/ukbb_nmr.csv"
        arivale: "${DATA_DIR}/arivale_lcms.csv"
        israeli: "${DATA_DIR}/israeli10k.csv"
      
  # Stage 2: Build reference
  - action_type: BUILD_NIGHTINGALE_REFERENCE
    params:
      reference_source: "ukbb"
      
  # Stage 3: Progressive matching
  - action_type: BASELINE_FUZZY_MATCH
    params:
      fuzzy_threshold: 0.8
      
  - action_type: CTS_ENRICHED_MATCH
    params:
      api_timeout: 30
      cache_results: true
      
  - action_type: VECTOR_ENHANCED_MATCH
    params:
      model: "biochemical-bert"
      similarity_threshold: 0.85
      
  # Stage 4: Validation
  - action_type: VALIDATE_AGAINST_REFERENCE
    params:
      reference_tool: "manual_curation"
      metrics: ["overlap_rate", "accuracy", "completeness"]
```

### Example 2: Creating Domain-Specific Action

**Developer Input:**
```
Create an action that performs pathway enrichment analysis on metabolomics data
```

**Claude Generates:**
```python
# File: biomapper/core/strategy_actions/pathway_enrichment.py

from typing import Dict, List, Any
from pydantic import BaseModel, Field
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

class PathwayEnrichmentParams(BaseModel):
    """Parameters for pathway enrichment analysis."""
    metabolite_list: List[str] = Field(..., description="List of metabolite identifiers")
    database: str = Field(default="KEGG", description="Pathway database to use")
    p_value_cutoff: float = Field(default=0.05, description="Significance threshold")
    correction_method: str = Field(default="fdr", description="Multiple testing correction")

class PathwayEnrichmentResult(BaseModel):
    """Results from pathway enrichment analysis."""
    enriched_pathways: List[Dict[str, Any]]
    significant_count: int
    visualization_data: Dict[str, Any]

@register_action("PATHWAY_ENRICHMENT")
class PathwayEnrichment(TypedStrategyAction[PathwayEnrichmentParams, PathwayEnrichmentResult]):
    """
    Performs pathway enrichment analysis on metabolite lists.
    
    This action:
    - Maps metabolites to pathways
    - Calculates enrichment statistics
    - Applies multiple testing correction
    - Generates visualization data
    """
    
    def get_params_model(self) -> type[PathwayEnrichmentParams]:
        return PathwayEnrichmentParams
    
    async def execute_typed(
        self, 
        params: PathwayEnrichmentParams,
        context: Dict[str, Any]
    ) -> PathwayEnrichmentResult:
        # Implementation with biological awareness
        metabolites = params.metabolite_list
        
        # Map to pathway database IDs
        mapped_metabolites = await self.map_to_database(
            metabolites, 
            params.database
        )
        
        # Get pathway associations
        pathway_associations = await self.get_pathway_associations(
            mapped_metabolites,
            params.database
        )
        
        # Calculate enrichment
        enrichment_results = self.calculate_enrichment(
            pathway_associations,
            background_size=self.get_background_size(params.database)
        )
        
        # Apply multiple testing correction
        corrected_results = self.apply_correction(
            enrichment_results,
            method=params.correction_method
        )
        
        # Filter by significance
        significant = [
            p for p in corrected_results 
            if p['adjusted_p_value'] < params.p_value_cutoff
        ]
        
        # Generate visualization data
        viz_data = self.prepare_visualization(significant)
        
        return PathwayEnrichmentResult(
            enriched_pathways=significant,
            significant_count=len(significant),
            visualization_data=viz_data
        )
```

**Claude Also Generates Tests:**
```python
# File: tests/unit/strategy_actions/test_pathway_enrichment.py

import pytest
from biomapper.core.strategy_actions.pathway_enrichment import (
    PathwayEnrichment, 
    PathwayEnrichmentParams
)

class TestPathwayEnrichment:
    @pytest.fixture
    def action(self):
        return PathwayEnrichment({}, None)
    
    @pytest.fixture
    def test_metabolites(self):
        return ["glucose", "lactate", "pyruvate", "citrate"]
    
    async def test_basic_enrichment(self, action, test_metabolites):
        """Test basic pathway enrichment functionality."""
        params = PathwayEnrichmentParams(
            metabolite_list=test_metabolites,
            database="KEGG",
            p_value_cutoff=0.05
        )
        
        result = await action.execute_typed(params, {})
        
        assert result.significant_count >= 0
        assert isinstance(result.enriched_pathways, list)
        assert 'visualization_data' in result.dict()
    
    async def test_multiple_testing_correction(self, action, test_metabolites):
        """Test that multiple testing correction is applied."""
        params = PathwayEnrichmentParams(
            metabolite_list=test_metabolites,
            correction_method="bonferroni"
        )
        
        result = await action.execute_typed(params, {})
        
        for pathway in result.enriched_pathways:
            assert pathway['adjusted_p_value'] >= pathway['raw_p_value']
```

## AI-Assisted Debugging Workflow

### Scenario: Action Failing with Type Error

**Developer:**
```
The NIGHTINGALE_NMR_MATCH action is failing with:
AttributeError: 'float' object has no attribute 'lower'
```

**Claude's Diagnostic Process:**
1. Analyzes error context
2. Identifies data type mismatch
3. Suggests fix with validation

**Claude's Solution:**
```python
# Add type checking and conversion
def process_metabolite_name(self, name: Any) -> str:
    """Safely process metabolite names handling various input types."""
    if pd.isna(name) or name is None:
        return ""
    
    # Convert to string if numeric
    if isinstance(name, (int, float)):
        return str(name)
    
    # Ensure string type and normalize
    return str(name).lower().strip()
```

## AI-Powered Strategy Optimization

### Initial Strategy Performance
```yaml
# Human-written strategy
- action_type: BASELINE_FUZZY_MATCH
  params:
    fuzzy_threshold: 0.7  # Arbitrary choice
```

### Claude Optimization Process

**Step 1: Analyze Current Performance**
```python
# Claude suggests validation action
- action_type: VALIDATE_AGAINST_REFERENCE
  params:
    parameter_sweep:
      fuzzy_threshold: [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
```

**Step 2: Identify Optimal Parameters**
```yaml
# Claude analyzes results and updates
- action_type: BASELINE_FUZZY_MATCH
  params:
    fuzzy_threshold: 0.82  # Optimized based on validation
    # Claude adds comment explaining optimization
    # Threshold of 0.82 achieved best F1 score (0.89) 
    # on validation set with 15% improvement over default
```

## Natural Language to Strategy Translation

### Example: Complex Multi-Omics Analysis

**Researcher Input:**
```
I want to integrate metabolomics and proteomics data to identify 
biomarkers for diabetes. The metabolomics data is from NMR and 
the proteomics from mass spec. I need to:
1. Harmonize both datasets
2. Find correlated features
3. Validate against known diabetes markers
4. Generate a report with visualizations
```

**Claude Generates Complete Strategy:**
```yaml
name: DIABETES_BIOMARKER_DISCOVERY
description: |
  AI-generated multi-omics integration strategy for diabetes biomarker discovery
  combining NMR metabolomics with MS proteomics data

metadata:
  generated_by: "Claude Code"
  version: "1.0"
  validation_status: "pending"

parameters:
  metabolomics_file: "${DATA_DIR}/diabetes_nmr_metabolomics.csv"
  proteomics_file: "${DATA_DIR}/diabetes_ms_proteomics.csv"
  known_markers_file: "${DATA_DIR}/diabetes_known_markers.csv"
  output_dir: "${OUTPUT_DIR}/diabetes_biomarkers"

actions:
  # Data Loading
  - action_type: LOAD_DATASET_IDENTIFIERS
    params:
      dataset_files:
        metabolomics: "${metabolomics_file}"
        proteomics: "${proteomics_file}"
      
  # Harmonization
  - action_type: HARMONIZE_METABOLOMICS
    params:
      platform: "NMR"
      standardize_to: "HMDB"
      
  - action_type: HARMONIZE_PROTEOMICS
    params:
      platform: "MS"
      standardize_to: "UniProt"
      
  # Integration Analysis
  - action_type: CALCULATE_CORRELATIONS
    params:
      method: "spearman"
      threshold: 0.7
      correction: "fdr"
      
  - action_type: IDENTIFY_CLUSTERS
    params:
      algorithm: "hierarchical"
      distance_metric: "euclidean"
      
  # Validation
  - action_type: VALIDATE_AGAINST_KNOWN_MARKERS
    params:
      reference_file: "${known_markers_file}"
      metrics: ["sensitivity", "specificity", "auc"]
      
  # Reporting
  - action_type: GENERATE_BIOMARKER_REPORT
    params:
      include_visualizations: true
      formats: ["html", "pdf"]
      output_path: "${output_dir}/report"
```

## Best Practices for AI-Native Development

### 1. Describe Biology, Not Code
```
# Good prompt:
"Harmonize metabolite names accounting for stereoisomers and salt forms"

# Less effective:
"Write a function that uses string matching on metabolite names"
```

### 2. Provide Context and Constraints
```
# Good prompt:
"Create a validation action that compares our results to DESeq2 output,
focusing on fold change correlation and FDR agreement. Must handle 
missing genes gracefully."

# Less effective:
"Create a validation action"
```

### 3. Iterate with Validation
```yaml
# Claude suggests incremental validation
- action_type: QUICK_VALIDATION
  params:
    sample_size: 100  # Start small
    
# Then full validation
- action_type: FULL_VALIDATION
  params:
    use_all_data: true
```

### 4. Request Documentation
```
"Also generate comprehensive documentation including:
- Biological assumptions
- Parameter sensitivity
- Validation results
- Usage examples"
```

## Claude Commands for BioMapper Development

### Strategy Development
```
@claude create a strategy for [biological goal]
@claude optimize this strategy for [metric]
@claude add validation to this workflow
@claude generate test data for this strategy
```

### Action Development
```
@claude create an action for [biological operation]
@claude add error handling to this action
@claude make this action handle composite identifiers
@claude generate unit tests for this action
```

### Debugging
```
@claude debug this error: [error message]
@claude why might this action produce empty results?
@claude suggest parameter values for this action
@claude validate this output against expected biology
```

### Documentation
```
@claude document this strategy for scientists
@claude explain the biological assumptions
@claude create a validation report template
@claude generate usage examples
```

## Continuous Learning Loop

### 1. Claude Monitors Execution
- Tracks success rates
- Identifies failure patterns
- Suggests improvements

### 2. Claude Updates Strategies
- Adjusts parameters based on outcomes
- Adds error recovery for common failures
- Optimizes action ordering

### 3. Claude Shares Knowledge
- Documents successful patterns
- Warns about common pitfalls
- Suggests best practices

## Integration with Development Tools

### VS Code Integration
```json
// .vscode/settings.json
{
  "biomapper.claude.enabled": true,
  "biomapper.claude.autoSuggest": true,
  "biomapper.claude.validateOnSave": true
}
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: claude-validate-strategy
      name: Validate Strategy with Claude
      entry: claude validate-strategy
      language: system
      files: \.yaml$
```

### CI/CD Integration
```yaml
# .github/workflows/claude-validation.yml
- name: Claude Strategy Validation
  run: |
    claude validate-all-strategies
    claude generate-validation-report
    claude check-biological-consistency
```

## Future AI-Native Capabilities

### Coming Soon
1. **Auto-completion in YAML**: Claude suggests next action while typing
2. **Real-time validation**: Claude validates biological correctness as you write
3. **Automatic benchmarking**: Claude runs benchmarks on every commit
4. **Smart error recovery**: Claude automatically fixes common errors

### On the Roadmap
1. **Visual strategy builder**: Drag-drop with Claude suggestions
2. **Natural language debugging**: "Why didn't this work?"
3. **Automatic optimization**: Claude tunes parameters overnight
4. **Knowledge synthesis**: Claude learns from all users' strategies

## Conclusion

BioMapper's AI-native development experience transforms bioinformatics workflow creation from a manual, error-prone process to an intelligent, validated, and efficient collaboration between human expertise and AI capabilities. This is not just automation - it's augmentation that maintains scientific rigor while accelerating discovery.