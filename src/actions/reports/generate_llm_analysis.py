"""
Generate LLM-powered analysis for progressive mapping results.
Uses Claude API to provide intelligent insights, pattern recognition, and recommendations.
Falls back to template-based report if API fails.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Literal
from pathlib import Path
from datetime import datetime
from collections import Counter
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, validator
import warnings

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext
from actions.utils.llm_providers import AnthropicProvider, LLMResponse, LLMUsageMetrics

logger = logging.getLogger(__name__)

# Cache for LLM responses during development
CACHE_DIR = Path("/tmp/biomapper_llm_cache")
CACHE_DIR.mkdir(exist_ok=True)


class ActionResult(BaseModel):
    """Standard action result for LLM analysis."""
    
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class GenerateLLMAnalysisParams(BaseModel):
    """Parameters for LLM analysis generation.
    
    Supports backward compatibility for parameter naming transitions.
    Standard parameter name: directory_path
    Legacy parameter name: output_directory (deprecated)
    """
    
    # Required parameters
    provider: Literal["anthropic", "openai", "template"] = Field(
        "anthropic",
        description="LLM provider to use"
    )
    model: str = Field(
        "claude-3-sonnet-20240229",
        description="Model to use for analysis"
    )
    
    # Standard compliant parameter (PARAMETER_NAMING_STANDARD.md)
    directory_path: Optional[str] = Field(
        None,
        description="Directory for saving analysis files (standard name)"
    )
    
    # Backward compatibility alias (deprecated)
    output_directory: Optional[str] = Field(
        None,
        description="DEPRECATED: Use 'directory_path' instead. Directory for saving analysis files"
    )
    
    @validator('directory_path', always=True)
    def handle_backward_compatibility(cls, v, values):
        """Handle backward compatibility for output_directory -> directory_path migration."""
        if v is None and 'output_directory' in values and values['output_directory'] is not None:
            warnings.warn(
                "Parameter 'output_directory' is deprecated and will be removed in v3.0. "
                "Please use 'directory_path' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            logger.warning(
                "Using deprecated parameter 'output_directory'. Please update to 'directory_path'."
            )
            return values['output_directory']
        elif v is None and ('output_directory' not in values or values['output_directory'] is None):
            raise ValueError("Either 'directory_path' or 'output_directory' must be provided")
        return v
    
    # Data keys
    progressive_stats_key: str = Field(
        "progressive_stats",
        description="Context key containing progressive statistics"
    )
    mapping_results_key: str = Field(
        "final_merged",
        description="Context key containing final mapping results dataframe"
    )
    
    # Metadata
    strategy_name: str = Field(
        ...,
        description="Name of the strategy being analyzed"
    )
    entity_type: Literal["protein", "metabolite", "chemistry"] = Field(
        "protein",
        description="Type of biological entity being mapped"
    )
    
    # Output configuration
    output_format: List[str] = Field(
        default=["summary", "flowchart", "recommendations"],
        description="Sections to include in analysis"
    )
    include_recommendations: bool = Field(
        True,
        description="Include improvement recommendations"
    )
    
    # Analysis focus areas
    analysis_focus: List[str] = Field(
        default=["coverage_analysis", "confidence_distribution", "unmapped_patterns", "progressive_improvement"],
        description="Key areas to analyze"
    )
    
    # Optional prefix for output files
    prefix: str = Field(
        "",
        description="Prefix for output files"
    )
    
    # Caching for development
    use_cache: bool = Field(
        True,
        description="Use cached LLM responses during development"
    )


@register_action("GENERATE_LLM_ANALYSIS")
class GenerateLLMAnalysis(TypedStrategyAction[GenerateLLMAnalysisParams, ActionResult]):
    """Generate comprehensive LLM-powered analysis of mapping results."""
    
    def get_params_model(self) -> type[GenerateLLMAnalysisParams]:
        return GenerateLLMAnalysisParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self, params: GenerateLLMAnalysisParams, context: Any, **kwargs
    ) -> ActionResult:
        """Execute LLM analysis generation."""
        try:
            # Wrap context for standardized access
            ctx = UniversalContext(context)
            
            # Get progressive stats
            progressive_stats = ctx.get(params.progressive_stats_key, {})
            if not progressive_stats:
                logger.warning(f"No progressive stats found at key '{params.progressive_stats_key}'")
            
            # Get mapping results dataframe
            datasets = ctx.get('datasets', {})
            mapping_data = datasets.get(params.mapping_results_key)
            
            if mapping_data is None:
                logger.warning(f"No mapping results found at key '{params.mapping_results_key}'")
                mapping_df = pd.DataFrame()
            elif isinstance(mapping_data, list):
                # Convert list of dicts to DataFrame
                mapping_df = pd.DataFrame(mapping_data) if mapping_data else pd.DataFrame()
                logger.info(f"Converted list of {len(mapping_data)} records to DataFrame for LLM analysis")
            elif isinstance(mapping_data, pd.DataFrame):
                mapping_df = mapping_data
            else:
                logger.warning(f"Unsupported mapping data type: {type(mapping_data)}, using empty DataFrame")
                mapping_df = pd.DataFrame()
            
            # Create output directory
            # Use the standard parameter name internally
            output_path = Path(params.directory_path)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Extract analysis data
            analysis_data = self._prepare_analysis_data(
                progressive_stats, mapping_df, params
            )
            
            # Generate LLM analysis or use fallback
            if params.provider == "template":
                analysis_result = self._generate_template_analysis(analysis_data, params)
            else:
                analysis_result = await self._generate_llm_analysis(
                    analysis_data, params
                )
            
            # Generate output files
            files_created = []
            
            # Generate markdown report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            markdown_file = output_path / f"{params.prefix}llm_analysis_{timestamp}.md"
            markdown_file.write_text(analysis_result.content)
            files_created.append(str(markdown_file))
            logger.info(f"Generated markdown analysis: {markdown_file}")
            
            # Generate JSON metadata
            json_file = output_path / f"{params.prefix}llm_metadata_{timestamp}.json"
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "strategy_name": params.strategy_name,
                "entity_type": params.entity_type,
                "provider": params.provider,
                "model": params.model if params.provider != "template" else "template",
                "analysis_data": analysis_data,
                "llm_usage": analysis_result.usage.dict() if hasattr(analysis_result, 'usage') else None,
                "success": analysis_result.success if hasattr(analysis_result, 'success') else True
            }
            json_file.write_text(json.dumps(metadata, indent=2, default=str))
            files_created.append(str(json_file))
            logger.info(f"Generated JSON metadata: {json_file}")
            
            # Export unmapped proteins to TSV for biological review
            if analysis_data.get('unmapped_details'):
                unmapped_df = pd.DataFrame(analysis_data['unmapped_details'])
                unmapped_file = output_path / f"{params.prefix}unmapped_proteins_audit_{timestamp}.tsv"
                unmapped_df.to_csv(unmapped_file, sep='\t', index=False)
                files_created.append(str(unmapped_file))
                logger.info(f"Exported {len(unmapped_df)} unmapped proteins to {unmapped_file}")
            
            # Update context with output files using UniversalContext
            output_files = ctx.get('output_files', [])
            if not isinstance(output_files, list):
                output_files = []
            output_files.extend(files_created)
            ctx.set('output_files', output_files)
            
            return ActionResult(
                success=True,
                message=f"Generated LLM analysis in {params.directory_path}",
                data={
                    'files_created': files_created,
                    'provider_used': params.provider,
                    'analysis_sections': params.output_format
                }
            )
            
        except Exception as e:
            error_msg = f"LLM analysis generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Try fallback to template
            try:
                logger.info("Falling back to template-based analysis...")
                return await self._fallback_to_template(params, context)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return ActionResult(success=False, message=error_msg)
    
    def _prepare_analysis_data(
        self, progressive_stats: Dict, mapping_df: pd.DataFrame, params: GenerateLLMAnalysisParams
    ) -> Dict[str, Any]:
        """Prepare data for LLM analysis."""
        
        # Calculate summary statistics - FIX: Use unique protein counts, not row counts
        if not mapping_df.empty and 'confidence_score' in mapping_df.columns:
            # Use unique protein counting logic (same as corrected statistics)
            id_col = 'uniprot' if 'uniprot' in mapping_df.columns else params.entity_type
            unique_total = mapping_df[id_col].nunique()
            unique_matched = mapping_df[mapping_df['confidence_score'] > 0][id_col].nunique()
            unique_unmapped = mapping_df[mapping_df['confidence_score'] == 0][id_col].nunique()
            
            # Use corrected counts instead of progressive_stats which has row counts
            total_processed = unique_total
            final_match_rate = unique_matched / unique_total if unique_total > 0 else 0
            logger.info(f"LLM Analysis: Using corrected unique protein counts - {unique_total} total, {unique_matched} matched, {unique_unmapped} unmapped")
        else:
            # Fallback to progressive_stats if no mapping data available
            total_processed = progressive_stats.get('total_processed', len(mapping_df))
            final_match_rate = progressive_stats.get('final_match_rate', 0)
            logger.warning("LLM Analysis: Using raw progressive_stats (may be inflated row counts)")
        
        # Extract stage performance
        stage_summary = []
        if 'stages' in progressive_stats:
            for stage_id, stage_data in progressive_stats['stages'].items():
                stage_summary.append({
                    'stage': stage_id,
                    'name': stage_data.get('name', f'stage_{stage_id}'),
                    'method': stage_data.get('method', 'Unknown'),
                    'new_matches': stage_data.get('new_matches', 0),
                    'cumulative_matched': stage_data.get('cumulative_matched', 0),
                    'confidence': stage_data.get('confidence_avg', 0),
                    'time': stage_data.get('computation_time', 'N/A')
                })
        
        # Analyze unmapped patterns (top 50)
        unmapped_patterns = []
        if not mapping_df.empty and 'confidence_score' in mapping_df.columns:
            unmapped_df = mapping_df[mapping_df['confidence_score'] == 0]
            
            if not unmapped_df.empty and params.entity_type in unmapped_df.columns:
                # Get unmapped identifiers
                unmapped_ids = unmapped_df[params.entity_type].dropna().tolist()
                
                # Group by patterns
                patterns = self._extract_patterns(unmapped_ids, params.entity_type)
                
                # Get top 50 patterns
                pattern_counter = Counter(patterns)
                unmapped_patterns = [
                    {'pattern': pattern, 'count': count, 'examples': self._get_examples(unmapped_ids, pattern, 3)}
                    for pattern, count in pattern_counter.most_common(50)
                ]
        
        # Extract detailed unmapped protein information for biological review
        unmapped_details = []
        if not mapping_df.empty and 'confidence_score' in mapping_df.columns:
            unmapped_df = mapping_df[mapping_df['confidence_score'] == 0]
            if not unmapped_df.empty:
                # Get key columns, using 'uniprot' as primary ID column
                id_col = 'uniprot' if 'uniprot' in unmapped_df.columns else params.entity_type
                
                # Filter out composite artifacts - only include unique original identifiers
                if '_original_uniprot' in unmapped_df.columns:
                    # Use original identifiers to avoid composite parsing artifacts
                    unique_original_ids = unmapped_df['_original_uniprot'].dropna().unique()
                    for original_id in unique_original_ids:
                        # Get representative row for this original ID
                        row = unmapped_df[unmapped_df['_original_uniprot'] == original_id].iloc[0]
                        unmapped_details.append({
                            'id': original_id,  # Use original ID
                            'name': row.get('name', ''),
                            'gene_name': row.get('gene_name', ''),
                            'description': row.get('gene_description', ''),
                            'panel': row.get('panel', ''),
                            'failure_type': self._classify_failure_type(original_id)  # Classify original ID
                        })
                else:
                    # Fallback to current behavior if _original_uniprot not available
                    for _, row in unmapped_df.iterrows():
                        unmapped_details.append({
                            'id': row.get(id_col, ''),
                            'name': row.get('name', ''),
                            'gene_name': row.get('gene_name', ''),
                            'description': row.get('gene_description', ''),
                            'panel': row.get('panel', ''),
                            'failure_type': self._classify_failure_type(row.get(id_col, ''))
                        })
        
        # Confidence distribution
        confidence_dist = {}
        if not mapping_df.empty and 'confidence_score' in mapping_df.columns:
            bins = [0, 0.5, 0.7, 0.85, 0.95, 1.0]
            counts, _ = np.histogram(mapping_df['confidence_score'], bins=bins)
            confidence_dist = {
                f"{bins[i]:.1f}-{bins[i+1]:.1f}": int(counts[i])
                for i in range(len(counts))
            }
        
        return {
            'summary': {
                'total_processed': total_processed,
                'final_match_rate': final_match_rate,
                'total_matched': int(total_processed * final_match_rate),
                'total_unmapped': unique_unmapped if 'unique_unmapped' in locals() else int(total_processed * (1 - final_match_rate)),
                'entity_type': params.entity_type,
                'strategy_name': params.strategy_name
            },
            'stages': stage_summary,
            'unmapped_patterns': unmapped_patterns[:50],  # Top 50
            'unmapped_details': unmapped_details[:20],  # Limit to 20 for LLM context
            'confidence_distribution': confidence_dist,
            'match_type_distribution': progressive_stats.get('match_type_distribution', {})
        }
    
    def _extract_patterns(self, identifiers: List[str], entity_type: str) -> List[str]:
        """Extract patterns from unmapped identifiers."""
        patterns = []
        
        for id_str in identifiers:
            if not id_str or pd.isna(id_str):
                patterns.append("empty_or_null")
                continue
            
            id_str = str(id_str).strip()
            
            # Entity-specific pattern recognition
            if entity_type == "protein":
                if len(id_str) == 6 and id_str[0] in 'OPQABCDEFGHIJKLMNRSTUVWXYZ':
                    patterns.append("standard_uniprot")
                elif '-' in id_str:
                    patterns.append("isoform_variant")
                elif '.' in id_str:
                    patterns.append("versioned_id")
                elif len(id_str) < 6:
                    patterns.append("short_identifier")
                elif len(id_str) > 10:
                    patterns.append("long_identifier")
                else:
                    patterns.append("non_standard_format")
                    
            elif entity_type == "metabolite":
                if id_str.startswith("HMDB"):
                    patterns.append("hmdb_format")
                elif id_str.startswith("CHEBI:"):
                    patterns.append("chebi_format")
                elif "-" in id_str and len(id_str) > 20:
                    patterns.append("inchikey_format")
                else:
                    patterns.append("unknown_metabolite_format")
                    
            else:
                patterns.append("unrecognized_pattern")
        
        return patterns
    
    def _get_examples(self, identifiers: List[str], pattern: str, n: int = 3) -> List[str]:
        """Get example identifiers matching a pattern."""
        examples = []
        pattern_funcs = {
            "empty_or_null": lambda x: not x or pd.isna(x),
            "standard_uniprot": lambda x: len(str(x)) == 6 and str(x)[0] in 'OPQABCDEFGHIJKLMNRSTUVWXYZ',
            "isoform_variant": lambda x: '-' in str(x),
            "versioned_id": lambda x: '.' in str(x),
            "short_identifier": lambda x: len(str(x)) < 6,
            "long_identifier": lambda x: len(str(x)) > 10,
        }
        
        check_func = pattern_funcs.get(pattern, lambda x: True)
        
        for id_str in identifiers:
            if check_func(id_str):
                examples.append(str(id_str))
                if len(examples) >= n:
                    break
        
        return examples
    
    def _classify_failure_type(self, protein_id: str) -> str:
        """Classify why a protein failed to map for biological review."""
        if not protein_id or pd.isna(protein_id):
            return 'missing_identifier'
        
        id_str = str(protein_id).strip().upper()
        
        # Check for composite IDs (multiple proteins in one field)
        if ',' in id_str:
            return 'composite_id'
        
        # Check for clinical markers
        if id_str.startswith('NT-') or id_str in ['NT-PROBNP', 'BNP', 'TROPONIN']:
            return 'clinical_marker'
        
        # Check for standard UniProt format that should have matched
        if len(id_str) == 6 and id_str[0] in 'OPQABCDEFGHIJKLMNRSTUVWXYZ' and id_str[1:].replace('0','').isdigit():
            return 'database_gap'  # Valid UniProt but not in reference
        
        # Check for isoforms
        if '-' in id_str and len(id_str.split('-')[0]) == 6:
            return 'isoform_variant'
        
        # Everything else
        return 'non_standard_format'
    
    async def _generate_llm_analysis(
        self, analysis_data: Dict[str, Any], params: GenerateLLMAnalysisParams
    ) -> LLMResponse:
        """Generate analysis using LLM provider."""
        
        # Check cache first
        if params.use_cache:
            cache_key = self._get_cache_key(analysis_data, params)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.info("Using cached LLM response")
                return cached_response
        
        # Prepare focused prompt
        prompt = self._build_analysis_prompt(analysis_data, params)
        
        # Initialize provider
        provider = AnthropicProvider(model=params.model)
        
        # Generate analysis
        logger.info(f"Generating LLM analysis using {params.provider}/{params.model}")
        response = await provider.generate_analysis(prompt, analysis_data)
        
        # Handle API failure
        if not response.success:
            logger.error(f"LLM API failed: {response.error_message}")
            # Return template fallback
            return self._generate_template_analysis(analysis_data, params)
        
        # Cache successful response
        if params.use_cache and response.success:
            self._cache_response(cache_key, response)
        
        return response
    
    def _build_analysis_prompt(self, data: Dict[str, Any], params: GenerateLLMAnalysisParams) -> str:
        """Build enhanced prompt for LLM analysis with biological context."""
        
        # Extract key metrics
        summary = data['summary']
        stages = data['stages']
        unmapped = data['unmapped_patterns'][:20]  # Focus on top 20
        confidence_dist = data.get('confidence_distribution', {})
        
        # Calculate biological impact metrics
        high_confidence = sum(v for k, v in confidence_dist.items() if '0.9' in k or '1.0' in k)
        total_matches = sum(confidence_dist.values()) if confidence_dist else summary['total_matched']
        
        prompt = f"""You are analyzing progressive {params.entity_type} mapping results for biological research. Provide a comprehensive analysis that helps biological researchers understand data quality, coverage gaps, and actionable improvements.

# Dataset Context
**Strategy**: {params.strategy_name}
**Entity Type**: {params.entity_type} identifiers
**Total Processed**: {summary['total_processed']:,} unique {params.entity_type}s
**Success Rate**: {summary['final_match_rate']:.1%} ({summary['total_matched']:,} mapped, {summary['total_unmapped']:,} unmapped)
**High-Confidence Matches**: {high_confidence:,} ({(high_confidence/total_matches*100) if total_matches > 0 else 0:.1f}% of mapped)

# Progressive Mapping Stages"""
        
        for stage in stages:
            efficiency = f"{stage['new_matches']/summary['total_processed']*100:.1f}%" if summary['total_processed'] > 0 else "0%"
            prompt += f"""
**Stage {stage['stage']}: {stage['name']}**
- Method: {stage['method']}
- New matches: {stage['new_matches']:,} ({efficiency} of total dataset)
- Cumulative coverage: {stage['cumulative_matched']:,} matches
- Processing time: {stage['time']}
- Average confidence: {stage['confidence']:.3f}"""
        
        prompt += f"""

# Unmapped Pattern Analysis
Top failure patterns with examples:
{json.dumps(unmapped, indent=2)}

# Confidence Score Distribution
{json.dumps(confidence_dist, indent=2)}

# ANALYSIS REQUIREMENTS

## 1. Report Structure (Enhanced for Biological Research)

Generate a comprehensive markdown report following this structure:

### **Introduction**
Start with a clear problem statement explaining:
- What biological dataset was processed
- Why {params.entity_type} mapping is critical for downstream analysis
- Brief overview of the progressive mapping approach

### **Methods and Technical Details**
For each stage, provide:
- **Algorithm Description**: Specific method used (not just "exact match")
- **Reference Database**: Which database/version was queried
- **Match Criteria**: Exact parameters for accepting/rejecting matches
- **Quality Metrics**: How confidence scores are calculated
- **Error Handling**: How edge cases and failures are managed

### **Results with Biological Context**
Present results in structured tables:
- **Stage Performance Table**: Stage | Method | New Matches | Cumulative | Processing Time | Biological Impact
- **Confidence Distribution Table**: Range | Count | Percentage | Biological Interpretation
- **Failure Analysis Table**: Pattern | Count | Examples | Root Cause | Biological Impact

### **Unmapped {params.entity_type.title()}s: Biological Review and Audit**
Provide detailed biological context for failures:
- **Summary Table** with biological annotations
- **Failure Type Classification** with biological explanations
- **Biological Impact Assessment**: Which pathways/functions are affected
- **Priority Ranking** for remediation based on biological importance

### **Actionable Recommendations**
Provide 3-5 prioritized, specific recommendations:
1. **Technical Improvements**: Specific code/algorithm changes
2. **Database Enhancements**: Additional reference sources to integrate
3. **Quality Control**: Validation steps to implement
4. **Biological Validation**: Manual curation priorities
5. **Pipeline Optimization**: Performance improvements

Each recommendation must include:
- Specific implementation steps
- Expected coverage improvement
- Resource requirements
- Timeline estimate

## 2. Biological Research Focus

**Critical Analysis Points**:
- What biological processes/pathways are represented in mapped vs unmapped {params.entity_type}s?
- Are there systematic biases (e.g., well-studied vs novel {params.entity_type}s)?
- Which unmapped {params.entity_type}s are most critical for biological interpretation?
- How does mapping quality affect downstream functional analysis?

## 3. Technical Specificity Requirements

**Method Descriptions Must Include**:
- Exact string matching algorithms used
- Database API versions and endpoints
- Confidence scoring formulas
- Normalization procedures applied
- Error handling and retry logic

**Performance Metrics Must Include**:
- Processing time per {params.entity_type} (milliseconds/item)
- Memory usage patterns
- API rate limiting considerations
- Scalability characteristics

## 4. Visualization Requirements

Include these Mermaid diagrams:
1. **Process Flow**: Detailed pipeline with decision points
2. **Results Waterfall**: Cumulative mapping improvements
3. **Failure Analysis**: Classification tree for unmapped patterns
4. **Quality Distribution**: Confidence score histogram

## 5. Reproducibility

Include enough technical detail to allow:
- Reproduction of the analysis
- Comparison with other datasets
- Validation of results
- Extension to related {params.entity_type} types

Focus on practical, implementable insights that immediately improve biological data quality and research outcomes."""
        
        # Add enhanced biological review section
        if data.get('unmapped_details'):
            failure_types = {}
            for item in data['unmapped_details']:
                failure_type = item.get('failure_type', 'unknown')
                if failure_type not in failure_types:
                    failure_types[failure_type] = []
                failure_types[failure_type].append(item)
            
            prompt += f"""

## Detailed Unmapped {params.entity_type.title()} Information

### Failure Type Distribution:
"""
            for failure_type, items in failure_types.items():
                prompt += f"- **{failure_type}**: {len(items)} {params.entity_type}s\n"
            
            prompt += f"""

### Representative Examples by Failure Type:
{json.dumps(failure_types, indent=2, default=str)}

### REQUIRED: Enhanced Biological Review Section

You MUST include a comprehensive section titled "## Unmapped {params.entity_type.title()}s: Biological Review and Audit" with:

1. **Detailed Summary Table** (markdown format):
   | {params.entity_type.title()} ID | Gene Name | Description | Panel/Source | Failure Type | Biological Context | Priority | Suggested Action |
   |---|---|---|---|---|---|---|---|
   [Complete table for all unmapped {params.entity_type}s]

2. **Failure Type Analysis with Biological Context**:
   - **Database Gaps**: Valid {params.entity_type}s missing from reference - highest priority
   - **Composite IDs**: Multi-{params.entity_type} entries needing parsing
   - **Clinical Markers**: Non-standard identifiers from clinical panels
   - **Format Issues**: Versioned/isoform variants needing normalization
   - **Unknown Patterns**: Novel formats requiring investigation

3. **Biological Impact Assessment**:
   - Which biological pathways/functions are affected by missing {params.entity_type}s
   - Disease relevance and clinical importance
   - Research impact of coverage gaps
   - Cross-dataset integration implications

4. **Prioritized Remediation Plan**:
   - Immediate actions (database updates, format fixes)
   - Short-term improvements (additional parsers, fuzzy matching)
   - Long-term strategy (reference database expansion)
   - Manual curation priorities

5. **Quality Control Recommendations**:
   - Validation steps for corrected mappings
   - Monitoring for similar issues in future datasets
   - Upstream data quality improvements

This biological review section is critical for researchers to understand the real-world impact of mapping failures and prioritize remediation efforts."""
        
        return prompt
    
    def _generate_template_analysis(self, data: Dict[str, Any], params: GenerateLLMAnalysisParams) -> LLMResponse:
        """Generate enhanced template-based analysis as fallback."""
        
        summary = data['summary']
        stages = data['stages']
        unmapped = data['unmapped_patterns'][:10]  # Top 10 for template
        confidence_dist = data.get('confidence_distribution', {})
        unmapped_details = data.get('unmapped_details', [])
        
        # Calculate biological impact metrics
        high_confidence = sum(v for k, v in confidence_dist.items() if '0.9' in k or '1.0' in k)
        total_matches = sum(confidence_dist.values()) if confidence_dist else summary['total_matched']
        
        # Build report sections
        header = f"""# {params.entity_type.title()} Mapping Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Strategy**: {params.strategy_name}  
**Entity Type**: {params.entity_type} identifiers  
**Analysis Mode**: Template-based (LLM unavailable)

## Introduction

This report analyzes the mapping of {summary['total_processed']:,} {params.entity_type} identifiers using a progressive multi-stage approach. {params.entity_type.title()} mapping is critical for biological data integration, enabling cross-dataset analysis and functional annotation. The progressive strategy applies increasingly sophisticated matching techniques to maximize coverage while maintaining high confidence.

## Methods and Technical Details

### Progressive Mapping Pipeline

The mapping process employs a waterfall approach with {len(stages)} stages:

"""
        
        # Add stage details
        stages_content = ""
        for i, stage in enumerate(stages, 1):
            improvement = stage['new_matches'] / summary['total_processed'] * 100 if summary['total_processed'] > 0 else 0
            stages_content += f"""#### Stage {stage['stage']}: {stage['name']}
- **Algorithm**: {stage['method']}
- **Match Criteria**: High-confidence exact matching with normalization
- **Quality Control**: Confidence scoring with {stage['confidence']:.3f} average
- **Performance**: {stage['time']} processing time
- **Yield**: {stage['new_matches']:,} new matches ({improvement:.1f}% of dataset)

"""
        
        # Results section
        results_section = f"""### Reference Database Integration
- **Primary Source**: UniProt/KG2c cross-references
- **Normalization**: Standardized identifier formats
- **Validation**: Confidence-based quality scoring
- **Error Handling**: Graceful degradation for invalid formats

## Results with Biological Context

### Overall Performance Summary

| Metric | Value | Biological Significance |
|--------|-------|------------------------|
| Total Processed | {summary['total_processed']:,} | Complete dataset coverage |
| Successfully Mapped | {summary['total_matched']:,} ({summary['final_match_rate']:.1%}) | High biological coverage achieved |
| High-Confidence Matches | {high_confidence:,} ({(high_confidence/total_matches*100) if total_matches > 0 else 0:.1f}%) | Reliable for downstream analysis |
| Unmapped | {summary['total_unmapped']:,} ({100-summary['final_match_rate']*100:.1f}%) | Requires targeted investigation |

### Stage Performance Analysis

| Stage | Method | New Matches | Cumulative Coverage | Processing Time | Biological Impact |
|-------|--------|-------------|-------------------|-----------------|------------------|"""

        # Add stage performance table rows
        stage_table_rows = ""
        for stage in stages:
            coverage = f"{stage['cumulative_matched']/summary['total_processed']*100:.1f}%" if summary['total_processed'] > 0 else "0%"
            impact = "High" if stage['new_matches'] > summary['total_processed'] * 0.1 else "Moderate" if stage['new_matches'] > 10 else "Low"
            stage_table_rows += f"\n| {stage['stage']} | {stage['name']} | {stage['new_matches']:,} | {coverage} | {stage['time']} | {impact} |"

        # Confidence distribution section
        confidence_section = "\n\n### Confidence Score Distribution\n\n"
        if confidence_dist:
            confidence_section += "| Confidence Range | Count | Percentage | Biological Interpretation |\n"
            confidence_section += "|------------------|--------|------------|--------------------------|\\n"
            total_conf = sum(confidence_dist.values())
            for range_str, count in confidence_dist.items():
                pct = f"{count/total_conf*100:.1f}%" if total_conf > 0 else "0%"
                if '0.9' in range_str or '1.0' in range_str:
                    interp = "Excellent - suitable for all analyses"
                elif '0.8' in range_str:
                    interp = "Good - validate for critical applications"
                elif '0.7' in range_str:
                    interp = "Moderate - manual review recommended"
                else:
                    interp = "Low - requires manual curation"
                confidence_section += f"| {range_str} | {count:,} | {pct} | {interp} |\\n"

        # Unmapped patterns section
        patterns_section = f"""

## Unmapped Pattern Analysis

### Failure Classification

The following patterns represent the most common mapping failures:

| Pattern | Count | Examples | Root Cause | Priority |
|---------|-------|----------|------------|----------|"""

        for pattern in unmapped[:10]:
            examples = ', '.join(pattern.get('examples', [])[:2]) if pattern.get('examples') else 'N/A'
            if pattern['pattern'] == 'standard_uniprot':
                cause = 'Reference database gap'
                priority = 'High'
            elif pattern['pattern'] == 'isoform_variant':
                cause = 'Isoform parsing needed'
                priority = 'Medium'
            elif pattern['pattern'] == 'non_standard_format':
                cause = 'Format standardization required'
                priority = 'Medium'
            else:
                cause = 'Investigation required'
                priority = 'Low'
            patterns_section += f"\\n| {pattern['pattern']} | {pattern['count']} | {examples} | {cause} | {priority} |"

        # Add biological review section if unmapped details available
        biological_review_section = ""
        if unmapped_details:
            biological_review_section = self._generate_biological_review_section(unmapped_details, params.entity_type)

        # Combine all sections (simplified for testing)
        content = (header + stages_content + results_section + stage_table_rows + 
                   confidence_section + patterns_section + biological_review_section)
        
        return LLMResponse(
            content=content,
            usage=LLMUsageMetrics(
                provider="template",
                model="template",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
            success=True,
            error_message=None
        )
    
    def _generate_biological_review_section(self, unmapped_details: List[Dict], entity_type: str) -> str:
        """Generate detailed biological review section for unmapped entities."""
        
        if not unmapped_details:
            return ""
        
        content = f"""

## Unmapped {entity_type.title()}s: Biological Review and Audit

### Executive Summary

{len(unmapped_details)} {entity_type}s failed to map and require biological investigation. This section provides detailed analysis to enable targeted remediation and assess biological impact.

### Detailed Unmapped {entity_type.title()} Inventory

| {entity_type.title()} ID | Gene Name | Description | Panel/Source | Failure Type | Biological Context | Priority | Suggested Action |
|{"―" * 12}|{"―" * 10}|{"―" * 12}|{"―" * 12}|{"―" * 12}|{"―" * 18}|{"―" * 8}|{"―" * 16}|
"""
        
        # Group by failure type for analysis
        failure_groups = {}
        for item in unmapped_details:
            failure_type = item.get('failure_type', 'unknown')
            if failure_type not in failure_groups:
                failure_groups[failure_type] = []
            failure_groups[failure_type].append(item)
            
            # Add table row
            protein_id = item.get('id', 'N/A')
            gene_name = item.get('gene_name', 'N/A')[:15]  # Truncate for table
            description = item.get('description', 'N/A')[:20]  # Truncate for table
            panel = item.get('panel', 'N/A')[:10]
            
            # Determine biological context and priority
            bio_context, priority, action = self._get_biological_assessment(item, entity_type)
            
            content += f"| {protein_id} | {gene_name} | {description} | {panel} | {failure_type} | {bio_context} | {priority} | {action} |\\n"
        
        return content
    
    def _get_biological_assessment(self, item: Dict, entity_type: str) -> tuple:
        """Get biological context, priority, and suggested action for unmapped entity."""
        
        failure_type = item.get('failure_type', 'unknown')
        gene_name = item.get('gene_name', '')
        description = item.get('description', '')
        
        # Determine biological context
        if failure_type == 'database_gap':
            bio_context = "Valid but missing"
            priority = "High"
            action = "Database query"
        elif failure_type == 'composite_id':
            bio_context = "Multi-entity field"
            priority = "High"
            action = "Parse composite"
        elif failure_type == 'clinical_marker':
            bio_context = "Clinical biomarker"
            priority = "Medium"
            action = "Clinical mapping"
        elif failure_type == 'isoform_variant':
            bio_context = "Protein isoform"
            priority = "Medium"
            action = "Isoform resolution"
        elif 'TP53' in gene_name.upper() or 'BRCA' in gene_name.upper():
            bio_context = "Cancer-related"
            priority = "High"
            action = "Manual curation"
        elif 'cytokine' in description.lower() or 'interleukin' in description.lower():
            bio_context = "Immune function"
            priority = "Medium"
            action = "Immune DB check"
        else:
            bio_context = "Unknown function"
            priority = "Low"
            action = "Literature search"
        
        return bio_context[:15], priority, action[:15]  # Truncate for table
    
    def _get_cache_key(self, data: Dict, params: GenerateLLMAnalysisParams) -> str:
        """Generate cache key for LLM response."""
        # Create a deterministic hash of the data and params
        cache_data = {
            'summary': data.get('summary'),
            'stages': data.get('stages'),
            'pattern_count': len(data.get('unmapped_patterns', [])),
            'provider': params.provider,
            'model': params.model,
            'entity_type': params.entity_type
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Retrieve cached LLM response."""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                return LLMResponse(**cached)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _cache_response(self, cache_key: str, response: LLMResponse) -> None:
        """Cache LLM response for development."""
        cache_file = CACHE_DIR / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(response.dict(), f, indent=2, default=str)
            logger.info(f"Cached response to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    async def _fallback_to_template(self, params: GenerateLLMAnalysisParams, context: Any) -> ActionResult:
        """Fallback to template-based analysis."""
        # Create a modified params with template provider
        fallback_params = params.copy(update={"provider": "template"})
        
        # Re-execute with template - but avoid infinite recursion
        try:
            # Wrap context for standardized access
            ctx = UniversalContext(context)
            
            # Get data
            progressive_stats = ctx.get(params.progressive_stats_key, {})
            datasets = ctx.get('datasets', {})
            mapping_data = datasets.get(params.mapping_results_key)
            
            # Convert to DataFrame if needed
            if mapping_data is None:
                mapping_df = pd.DataFrame()
            elif isinstance(mapping_data, list):
                mapping_df = pd.DataFrame(mapping_data) if mapping_data else pd.DataFrame()
            elif isinstance(mapping_data, pd.DataFrame):
                mapping_df = mapping_data
            else:
                mapping_df = pd.DataFrame()
            
            # Prepare analysis data
            analysis_data = self._prepare_analysis_data(progressive_stats, mapping_df, fallback_params)
            
            # Generate template report
            analysis_result = self._generate_template_analysis(analysis_data, fallback_params)
            
            # Create output directory
            output_path = Path(fallback_params.directory_path)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate output files
            files_created = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save markdown
            markdown_file = output_path / f"{fallback_params.prefix}llm_analysis_{timestamp}.md"
            markdown_file.write_text(analysis_result.content)
            files_created.append(str(markdown_file))
            
            # Save JSON metadata
            json_file = output_path / f"{fallback_params.prefix}llm_metadata_{timestamp}.json"
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "strategy_name": fallback_params.strategy_name,
                "entity_type": fallback_params.entity_type,
                "provider": "template",
                "model": "template",
                "analysis_data": analysis_data,
                "success": True
            }
            json_file.write_text(json.dumps(metadata, indent=2, default=str))
            files_created.append(str(json_file))
            
            # Update context using UniversalContext
            output_files = ctx.get('output_files', [])
            if not isinstance(output_files, list):
                output_files = []
            output_files.extend(files_created)
            ctx.set('output_files', output_files)
            
            return ActionResult(
                success=True,
                message=f"Generated template analysis in {fallback_params.directory_path}",
                data={'files_created': files_created, 'provider_used': 'template'}
            )
        except Exception as e:
            return ActionResult(success=False, message=f"Template fallback failed: {str(e)}")
    
