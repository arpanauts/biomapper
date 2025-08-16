"""System prompts for LLM analysis generation."""

from typing import Dict, Any


class BiomapperAnalysisPrompts:
    """System prompts for biomapper analysis tasks."""
    
    UNIVERSAL_ANALYST_PROMPT = """You are a biomapper results analyst specializing in biological identifier mapping strategies.

Given progressive mapping statistics and results, provide:

1. EXECUTIVE SUMMARY (2-3 sentences)
   - Overall mapping performance and key achievements
   - Primary methodology and success rate

2. STAGE-BY-STAGE ANALYSIS 
   - Performance of each mapping stage
   - Improvement contributions by stage
   - Efficiency metrics (time, API calls, match rate gains)
   - Cost-benefit assessment

3. SCIENTIFIC ASSESSMENT
   - Overall mapping quality and reliability
   - Confidence score distribution analysis
   - Data coverage and completeness
   - Potential limitations and biases

4. OPTIMIZATION RECOMMENDATIONS
   - Strategy improvements for better performance
   - Performance enhancements for efficiency
   - Quality considerations for reliability
   - Future methodological directions

Focus on scientific rigor, reproducibility, and actionable insights.
Use precise biological terminology and quantitative metrics.
Consider the biological significance of mapping outcomes."""
    
    COMPREHENSIVE_STRATEGY_ANALYST_PROMPT = """You are a biomapper strategy analyzer specializing in biological identifier mapping pipelines.

Given a progressive mapping strategy configuration and execution results, provide a COMPREHENSIVE analysis:

## 1. STRATEGY OVERVIEW
- Brief description of the strategy's purpose
- Key innovations and features (progressive filtering, match type tracking, etc.)
- Expected vs actual performance metrics

## 2. STAGE-BY-STAGE BREAKDOWN
Organize the complete pipeline by progressive stages:

### Stage 0: Data Loading
- List each action (e.g., LOAD_DATASET_IDENTIFIERS) with its specific purpose
- Note data sources and formats
- Identify any data quality issues

### Stage 1: Direct Matching (Expected ~65%)
- Explain the direct matching approach
- List each action in sequence:
  - Action name and type
  - Purpose in the pipeline
  - Key parameters used
  - Output produced
- Actual match rate achieved
- Performance timing

### Stage 2: Composite/Advanced Parsing (if applicable)
- Describe composite identifier handling
- Show how original values are preserved while parsing
- List actions and their roles
- Expected vs actual additional matches

### Stage 3: Historical/Fallback Resolution
- Explain API-based or advanced matching strategies
- List actions used
- Number of API calls made
- Expected vs actual improvement

### Result Consolidation
- How results from all stages are merged
- Tagging and confidence scoring approach
- Final statistics calculation

### Analysis & Visualization
- Report generation steps
- Visualization types produced (waterfall charts, TSV exports, etc.)
- LLM analysis configuration

### Export & Sync
- Output file formats
- Cloud synchronization setup

## 3. ACTION TYPE ANALYSIS
For each unique action type used in the strategy, provide:

**ACTION_TYPE_NAME**
- Purpose: What it does in the pipeline
- Occurrences: How many times used
- Key parameters: Important configuration options
- Output format: What it produces
- Known issues: Any problems or limitations
- Optimization opportunities: How it could be improved

## 4. PROGRESSIVE METRICS BREAKDOWN
- Stage 1: X% matched (direct)
- Stage 2: +Y% additional (composite) → Z% cumulative
- Stage 3: +A% additional (historical) → B% cumulative
- Final: C% unmapped
- Confidence distribution: High/Medium/Low percentages
- Performance: Total time, API calls, memory usage

## 5. KEY INNOVATIONS
- **Progressive Filtering**: Each stage only processes unmatched from previous
- **Match Type Tracking**: Every protein tagged with match method
- **Composite Preservation**: Original multi-value identifiers preserved
- **Standardized Output**: Consistent format across all actions
- **Waterfall Visualization**: Cumulative improvement tracking

## 6. RECOMMENDATIONS
### Immediate Optimizations
- Quick wins for performance
- Parameter tuning suggestions

### Coverage Improvements
- Additional matching strategies
- New data sources to consider

### Quality Enhancements
- Validation steps to add
- Confidence score refinements

Format as clear markdown with headers, bullet points, and code blocks where appropriate.
Be specific and quantitative wherever possible."""

    MERMAID_FLOWCHART_PROMPT = """Create a mermaid flowchart representing the progressive mapping strategy execution.

Include:
- Input dataset size and composition
- Each processing stage with match counts and success rates
- Decision points and filtering criteria
- API calls and external resource usage
- Final results breakdown (mapped/unmapped identifiers)
- Performance metrics (execution time, efficiency)

Requirements:
- Use clear, descriptive labels
- Follow proper mermaid syntax
- Include quantitative metrics in nodes
- Show data flow direction clearly
- Use appropriate node shapes for different operation types
- Include conditional paths where applicable

Output only the mermaid code, starting with ```mermaid and ending with ```."""

    SCIENTIFIC_SUMMARY_PROMPT = """Generate a scientific summary of biomapper mapping results.

Provide:
1. METHODOLOGY OVERVIEW
   - Mapping approach and algorithms used
   - Data sources and validation methods
   - Quality control measures

2. QUANTITATIVE RESULTS
   - Mapping statistics with confidence intervals
   - Performance benchmarks
   - Coverage analysis

3. BIOLOGICAL INTERPRETATION
   - Functional relevance of mapped identifiers
   - Biological pathway coverage
   - Potential research applications

4. QUALITY ASSESSMENT
   - Validation against known standards
   - Error analysis and limitations
   - Reproducibility considerations

Write in scientific journal style with appropriate citations where relevant."""

    TROUBLESHOOTING_ANALYSIS_PROMPT = """Analyze biomapper mapping results for potential issues and optimization opportunities.

Focus on:
1. PERFORMANCE BOTTLENECKS
   - Identify slow or inefficient stages
   - Resource utilization analysis
   - Scalability concerns

2. QUALITY ISSUES
   - Low confidence mappings
   - Inconsistent results
   - Missing or incorrect mappings

3. DATA PROBLEMS
   - Input data quality issues
   - Format inconsistencies
   - Missing required fields

4. RECOMMENDATIONS
   - Immediate fixes for critical issues
   - Performance optimization strategies
   - Data quality improvements
   - Alternative methodologies

Provide specific, actionable recommendations with priority levels."""

    @classmethod
    def get_analysis_prompt(cls, analysis_type: str = "universal") -> str:
        """Get the appropriate analysis prompt."""
        prompts = {
            "universal": cls.UNIVERSAL_ANALYST_PROMPT,
            "mermaid": cls.MERMAID_FLOWCHART_PROMPT,
            "scientific": cls.SCIENTIFIC_SUMMARY_PROMPT,
            "troubleshooting": cls.TROUBLESHOOTING_ANALYSIS_PROMPT
        }
        return prompts.get(analysis_type, cls.UNIVERSAL_ANALYST_PROMPT)

    @classmethod
    def customize_prompt(cls, base_prompt: str, customizations: Dict[str, Any]) -> str:
        """Customize a base prompt with specific requirements."""
        custom_prompt = base_prompt
        
        # Add entity-specific focus
        if "entity_type" in customizations:
            entity_type = customizations["entity_type"]
            entity_guidance = {
                "protein": "Focus on protein identifier mappings (UniProt, Ensembl, gene symbols). Consider isoforms, variants, and ortholog relationships.",
                "metabolite": "Focus on metabolite identifier mappings (HMDB, KEGG, ChEBI, InChIKey). Consider stereochemistry and structural variants.", 
                "chemistry": "Focus on clinical chemistry mappings (LOINC, test names). Consider method variations and unit standardization.",
                "gene": "Focus on gene identifier mappings (HGNC, Ensembl, Entrez). Consider synonyms and nomenclature changes."
            }
            if entity_type in entity_guidance:
                custom_prompt += f"\n\nENTITY-SPECIFIC GUIDANCE:\n{entity_guidance[entity_type]}"
        
        # Add specific analysis focus
        if "focus_areas" in customizations:
            focus_areas = customizations["focus_areas"]
            if isinstance(focus_areas, list):
                custom_prompt += f"\n\nSPECIFIC FOCUS AREAS:\n" + "\n".join(f"- {area}" for area in focus_areas)
        
        # Add output format requirements
        if "output_format" in customizations:
            format_req = customizations["output_format"]
            custom_prompt += f"\n\nOUTPUT FORMAT REQUIREMENTS:\n{format_req}"
        
        # Add biological context
        if "biological_context" in customizations:
            context = customizations["biological_context"]
            custom_prompt += f"\n\nBIOLOGICAL CONTEXT:\n{context}"
        
        return custom_prompt


class ProgressiveAnalysisTemplates:
    """Templates for analyzing progressive mapping results."""
    
    @staticmethod
    def format_progressive_stats(stats: Dict[str, Any]) -> str:
        """Format progressive statistics for LLM analysis."""
        formatted = "PROGRESSIVE MAPPING STATISTICS:\n\n"
        
        # Overall summary
        total_processed = stats.get("total_processed", 0)
        final_match_rate = stats.get("final_match_rate", 0.0)
        total_time = stats.get("total_time", "Unknown")
        
        formatted += f"Total Identifiers: {total_processed}\n"
        formatted += f"Final Match Rate: {final_match_rate:.1%}\n"
        formatted += f"Total Execution Time: {total_time}\n\n"
        
        # Stage-by-stage breakdown
        stages = stats.get("stages", {})
        if stages:
            formatted += "STAGE BREAKDOWN:\n"
            for stage_num, stage_data in stages.items():
                name = stage_data.get("name", f"Stage {stage_num}")
                method = stage_data.get("method", "Unknown")
                time_taken = stage_data.get("time", "Unknown")
                
                if "matched" in stage_data:
                    # Initial stage with matched/unmatched counts
                    matched = stage_data.get("matched", 0)
                    unmatched = stage_data.get("unmatched", 0) 
                    match_rate = matched / (matched + unmatched) if (matched + unmatched) > 0 else 0
                    formatted += f"\nStage {stage_num}: {name}\n"
                    formatted += f"  Method: {method}\n"
                    formatted += f"  Matched: {matched:,} ({match_rate:.1%})\n"
                    formatted += f"  Unmatched: {unmatched:,}\n"
                    formatted += f"  Time: {time_taken}\n"
                elif "new_matches" in stage_data:
                    # Subsequent stages with new matches
                    new_matches = stage_data.get("new_matches", 0)
                    cumulative = stage_data.get("cumulative_matched", 0)
                    improvement = new_matches / total_processed if total_processed > 0 else 0
                    formatted += f"\nStage {stage_num}: {name}\n"
                    formatted += f"  Method: {method}\n"
                    formatted += f"  New Matches: {new_matches:,} (+{improvement:.1%})\n"
                    formatted += f"  Cumulative: {cumulative:,}\n"
                    formatted += f"  Time: {time_taken}\n"
        
        return formatted
    
    @staticmethod
    def format_mapping_results(results: list) -> str:
        """Format mapping results for LLM analysis."""
        if not results:
            return "No mapping results available."
        
        formatted = "MAPPING RESULTS SAMPLE:\n\n"
        
        # Analyze confidence distribution
        confidences = [r.confidence for r in results if hasattr(r, 'confidence')]
        if confidences:
            high_conf = sum(1 for c in confidences if c >= 0.9)
            med_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
            low_conf = sum(1 for c in confidences if c < 0.7)
            
            formatted += f"Confidence Distribution:\n"
            formatted += f"  High (≥0.9): {high_conf:,} ({high_conf/len(confidences):.1%})\n"
            formatted += f"  Medium (0.7-0.9): {med_conf:,} ({med_conf/len(confidences):.1%})\n"
            formatted += f"  Low (<0.7): {low_conf:,} ({low_conf/len(confidences):.1%})\n\n"
        
        # Method distribution
        methods = [r.match_method for r in results if hasattr(r, 'match_method')]
        if methods:
            method_counts = {}
            for method in methods:
                method_counts[method] = method_counts.get(method, 0) + 1
            
            formatted += "Methods Used:\n"
            for method, count in method_counts.items():
                percentage = count / len(methods)
                formatted += f"  {method}: {count:,} ({percentage:.1%})\n"
            formatted += "\n"
        
        # Stage distribution
        stages = [r.stage for r in results if hasattr(r, 'stage')]
        if stages:
            stage_counts = {}
            for stage in stages:
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            formatted += "Stage Distribution:\n"
            for stage, count in sorted(stage_counts.items()):
                percentage = count / len(stages)
                formatted += f"  Stage {stage}: {count:,} ({percentage:.1%})\n"
        
        return formatted
    
    @staticmethod
    def create_analysis_context(
        progressive_stats: Dict[str, Any],
        mapping_results: list,
        strategy_name: str,
        entity_type: str = "protein"
    ) -> Dict[str, Any]:
        """Create comprehensive context for LLM analysis."""
        return {
            "strategy_name": strategy_name,
            "entity_type": entity_type,
            "timestamp": str(progressive_stats.get("timestamp", "Unknown")),
            "progressive_statistics": progressive_stats,
            "mapping_results_summary": ProgressiveAnalysisTemplates.format_mapping_results(mapping_results),
            "total_results": len(mapping_results),
            "execution_metadata": {
                "total_time": progressive_stats.get("total_time"),
                "stages_executed": len(progressive_stats.get("stages", {})),
                "final_match_rate": progressive_stats.get("final_match_rate"),
                "total_processed": progressive_stats.get("total_processed")
            }
        }