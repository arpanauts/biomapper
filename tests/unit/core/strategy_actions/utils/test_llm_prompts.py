"""Tests for LLM prompt utilities and template handling.

STATUS: LLM analysis utilities not fully implemented
FUNCTIONALITY: LLM prompt generation and template management
TIMELINE: TBD based on product priorities  
ALTERNATIVE: Use direct analysis tools or manual reporting

These tests are skipped as LLM prompt utilities are not currently implemented.
"""

import pytest

# Skip entire module - LLM analysis utilities not fully implemented
pytestmark = pytest.mark.skip("LLM analysis utilities not fully implemented - use direct analysis tools")

from actions.utils.llm_prompts import (
    BiomapperAnalysisPrompts,
    ProgressiveAnalysisTemplates
)


class TestBiomapperAnalysisPrompts:
    """Test LLM prompt generation and management."""
    
    def test_universal_analyst_prompt_structure(self):
        """Test universal analyst prompt structure and content."""
        prompt = BiomapperAnalysisPrompts.UNIVERSAL_ANALYST_PROMPT
        
        # Verify prompt contains required sections
        assert "EXECUTIVE SUMMARY" in prompt
        assert "STAGE-BY-STAGE ANALYSIS" in prompt
        assert "SCIENTIFIC ASSESSMENT" in prompt
        assert "OPTIMIZATION RECOMMENDATIONS" in prompt
        
        # Verify biological terminology
        assert "biomapper" in prompt.lower()
        assert "biological identifier" in prompt.lower()
        assert "mapping" in prompt.lower()
        
        # Verify scientific rigor emphasis
        assert "scientific rigor" in prompt.lower()
        assert "reproducibility" in prompt.lower()
        assert "quantitative metrics" in prompt.lower()
    
    def test_comprehensive_strategy_analyst_prompt(self):
        """Test comprehensive strategy analysis prompt."""
        prompt = BiomapperAnalysisPrompts.COMPREHENSIVE_STRATEGY_ANALYST_PROMPT
        
        # Verify comprehensive analysis sections
        assert "STRATEGY OVERVIEW" in prompt
        assert "STAGE-BY-STAGE BREAKDOWN" in prompt
        assert "ACTION TYPE ANALYSIS" in prompt
        assert "PROGRESSIVE METRICS BREAKDOWN" in prompt
        assert "KEY INNOVATIONS" in prompt
        assert "RECOMMENDATIONS" in prompt
        
        # Verify progressive methodology references
        assert "Progressive Filtering" in prompt
        assert "Match Type Tracking" in prompt
        assert "Composite Preservation" in prompt
        assert "Waterfall Visualization" in prompt
        
        # Verify expected performance metrics
        assert "Stage 1: X% matched (direct)" in prompt
        assert "Stage 2: +Y% additional (composite)" in prompt
        assert "Stage 3: +A% additional (historical)" in prompt
    
    def test_mermaid_flowchart_prompt(self):
        """Test mermaid flowchart generation prompt."""
        prompt = BiomapperAnalysisPrompts.MERMAID_FLOWCHART_PROMPT
        
        # Verify mermaid-specific requirements
        assert "mermaid flowchart" in prompt.lower()
        assert "mermaid syntax" in prompt.lower()
        assert "```mermaid" in prompt
        assert "```" in prompt
        
        # Verify flowchart components
        assert "Input dataset size" in prompt
        assert "processing stage" in prompt
        assert "Decision points" in prompt
        assert "API calls" in prompt
        assert "Performance metrics" in prompt
        
        # Verify formatting requirements
        assert "descriptive labels" in prompt
        assert "quantitative metrics" in prompt
        assert "data flow direction" in prompt
    
    def test_scientific_summary_prompt(self):
        """Test scientific summary generation prompt."""
        prompt = BiomapperAnalysisPrompts.SCIENTIFIC_SUMMARY_PROMPT
        
        # Verify scientific sections
        assert "METHODOLOGY OVERVIEW" in prompt
        assert "QUANTITATIVE RESULTS" in prompt
        assert "BIOLOGICAL INTERPRETATION" in prompt
        assert "QUALITY ASSESSMENT" in prompt
        
        # Verify scientific terminology
        assert "algorithms" in prompt.lower()
        assert "validation methods" in prompt.lower()
        assert "confidence intervals" in prompt.lower()
        assert "reproducibility" in prompt.lower()
        
        # Verify journal-style requirement
        assert "scientific journal style" in prompt.lower()
    
    def test_troubleshooting_analysis_prompt(self):
        """Test troubleshooting analysis prompt."""
        prompt = BiomapperAnalysisPrompts.TROUBLESHOOTING_ANALYSIS_PROMPT
        
        # Verify troubleshooting sections
        assert "PERFORMANCE BOTTLENECKS" in prompt
        assert "QUALITY ISSUES" in prompt
        assert "DATA PROBLEMS" in prompt
        assert "RECOMMENDATIONS" in prompt
        
        # Verify specific issue types
        assert "Low confidence mappings" in prompt
        assert "Inconsistent results" in prompt
        assert "Format inconsistencies" in prompt
        assert "priority levels" in prompt.lower()
    
    def test_get_analysis_prompt_method(self):
        """Test get_analysis_prompt method with different types."""
        
        # Test default (universal)
        universal_prompt = BiomapperAnalysisPrompts.get_analysis_prompt()
        assert universal_prompt == BiomapperAnalysisPrompts.UNIVERSAL_ANALYST_PROMPT
        
        # Test specific types
        universal_prompt = BiomapperAnalysisPrompts.get_analysis_prompt("universal")
        assert universal_prompt == BiomapperAnalysisPrompts.UNIVERSAL_ANALYST_PROMPT
        
        mermaid_prompt = BiomapperAnalysisPrompts.get_analysis_prompt("mermaid")
        assert mermaid_prompt == BiomapperAnalysisPrompts.MERMAID_FLOWCHART_PROMPT
        
        scientific_prompt = BiomapperAnalysisPrompts.get_analysis_prompt("scientific")
        assert scientific_prompt == BiomapperAnalysisPrompts.SCIENTIFIC_SUMMARY_PROMPT
        
        troubleshooting_prompt = BiomapperAnalysisPrompts.get_analysis_prompt("troubleshooting")
        assert troubleshooting_prompt == BiomapperAnalysisPrompts.TROUBLESHOOTING_ANALYSIS_PROMPT
        
        # Test unknown type falls back to universal
        unknown_prompt = BiomapperAnalysisPrompts.get_analysis_prompt("unknown_type")
        assert unknown_prompt == BiomapperAnalysisPrompts.UNIVERSAL_ANALYST_PROMPT
    
    def test_customize_prompt_entity_types(self):
        """Test prompt customization with different entity types."""
        base_prompt = "Analyze the following data:"
        
        # Test protein customization
        protein_customizations = {"entity_type": "protein"}
        protein_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, protein_customizations)
        
        assert "ENTITY-SPECIFIC GUIDANCE:" in protein_prompt
        assert "protein identifier mappings" in protein_prompt.lower()
        assert "UniProt" in protein_prompt
        assert "Ensembl" in protein_prompt
        assert "isoforms" in protein_prompt.lower()
        
        # Test metabolite customization
        metabolite_customizations = {"entity_type": "metabolite"}
        metabolite_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, metabolite_customizations)
        
        assert "metabolite identifier mappings" in metabolite_prompt.lower()
        assert "HMDB" in metabolite_prompt
        assert "KEGG" in metabolite_prompt
        assert "ChEBI" in metabolite_prompt
        assert "stereochemistry" in metabolite_prompt.lower()
        
        # Test chemistry customization
        chemistry_customizations = {"entity_type": "chemistry"}
        chemistry_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, chemistry_customizations)
        
        assert "clinical chemistry mappings" in chemistry_prompt.lower()
        assert "LOINC" in chemistry_prompt
        assert "method variations" in chemistry_prompt.lower()
        
        # Test gene customization
        gene_customizations = {"entity_type": "gene"}
        gene_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, gene_customizations)
        
        assert "gene identifier mappings" in gene_prompt.lower()
        assert "HGNC" in gene_prompt
        assert "nomenclature changes" in gene_prompt.lower()
    
    def test_customize_prompt_focus_areas(self):
        """Test prompt customization with specific focus areas."""
        base_prompt = "Analyze the data:"
        
        focus_customizations = {
            "focus_areas": [
                "Performance optimization",
                "Quality validation", 
                "Edge case handling"
            ]
        }
        
        customized_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, focus_customizations)
        
        assert "SPECIFIC FOCUS AREAS:" in customized_prompt
        assert "Performance optimization" in customized_prompt
        assert "Quality validation" in customized_prompt
        assert "Edge case handling" in customized_prompt
    
    def test_customize_prompt_output_format(self):
        """Test prompt customization with output format requirements."""
        base_prompt = "Analyze the data:"
        
        format_customizations = {
            "output_format": "Provide results as a structured JSON with sections for summary, details, and recommendations."
        }
        
        customized_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, format_customizations)
        
        assert "OUTPUT FORMAT REQUIREMENTS:" in customized_prompt
        assert "structured JSON" in customized_prompt
        assert "sections for summary" in customized_prompt
    
    def test_customize_prompt_biological_context(self):
        """Test prompt customization with biological context."""
        base_prompt = "Analyze the data:"
        
        context_customizations = {
            "biological_context": "This analysis focuses on protein-protein interactions in cancer research, specifically looking at p53 pathway proteins."
        }
        
        customized_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, context_customizations)
        
        assert "BIOLOGICAL CONTEXT:" in customized_prompt
        assert "protein-protein interactions" in customized_prompt
        assert "cancer research" in customized_prompt
        assert "p53 pathway" in customized_prompt
    
    def test_customize_prompt_multiple_customizations(self):
        """Test prompt customization with multiple customization types."""
        base_prompt = "Analyze the mapping results:"
        
        multiple_customizations = {
            "entity_type": "protein",
            "focus_areas": ["Q6EMK4 edge case", "Performance metrics"],
            "output_format": "Markdown with code blocks",
            "biological_context": "Human proteome mapping with emphasis on cancer biomarkers"
        }
        
        customized_prompt = BiomapperAnalysisPrompts.customize_prompt(base_prompt, multiple_customizations)
        
        # Verify all customizations are included
        assert "ENTITY-SPECIFIC GUIDANCE:" in customized_prompt
        assert "protein identifier mappings" in customized_prompt.lower()
        assert "SPECIFIC FOCUS AREAS:" in customized_prompt
        assert "Q6EMK4 edge case" in customized_prompt
        assert "OUTPUT FORMAT REQUIREMENTS:" in customized_prompt
        assert "Markdown with code blocks" in customized_prompt
        assert "BIOLOGICAL CONTEXT:" in customized_prompt
        assert "cancer biomarkers" in customized_prompt


class TestProgressiveAnalysisTemplates:
    """Test progressive analysis template functionality."""
    
    def test_format_progressive_stats_basic(self):
        """Test basic progressive statistics formatting."""
        stats = {
            "total_processed": 1000,
            "final_match_rate": 0.85,
            "total_time": "45.2 seconds",
            "stages": {
                "1": {
                    "name": "Direct Matching",
                    "method": "Exact match",
                    "matched": 650,
                    "unmatched": 350,
                    "time": "12.1 seconds"
                },
                "2": {
                    "name": "Composite Parsing",
                    "method": "Multi-separator parsing",
                    "new_matches": 150,
                    "cumulative_matched": 800,
                    "time": "18.3 seconds"
                }
            }
        }
        
        formatted = ProgressiveAnalysisTemplates.format_progressive_stats(stats)
        
        # Verify overall summary
        assert "Total Identifiers: 1,000" in formatted
        assert "Final Match Rate: 85.0%" in formatted
        assert "Total Execution Time: 45.2 seconds" in formatted
        
        # Verify stage breakdown
        assert "STAGE BREAKDOWN:" in formatted
        assert "Stage 1: Direct Matching" in formatted
        assert "Method: Exact match" in formatted
        assert "Matched: 650 (65.0%)" in formatted
        assert "Unmatched: 350" in formatted
        assert "Time: 12.1 seconds" in formatted
        
        assert "Stage 2: Composite Parsing" in formatted
        assert "Method: Multi-separator parsing" in formatted
        assert "New Matches: 150 (+15.0%)" in formatted
        assert "Cumulative: 800" in formatted
        assert "Time: 18.3 seconds" in formatted
    
    def test_format_progressive_stats_empty(self):
        """Test progressive statistics formatting with empty data."""
        empty_stats = {}
        
        formatted = ProgressiveAnalysisTemplates.format_progressive_stats(empty_stats)
        
        assert "PROGRESSIVE MAPPING STATISTICS:" in formatted
        assert "Total Identifiers: 0" in formatted
        assert "Final Match Rate: 0.0%" in formatted
        assert "Total Execution Time: Unknown" in formatted
    
    def test_format_mapping_results_with_data(self):
        """Test mapping results formatting with sample data."""
        
        # Create mock mapping results
        class MockResult:
            def __init__(self, confidence, method, stage):
                self.confidence = confidence
                self.match_method = method
                self.stage = stage
        
        results = [
            MockResult(0.95, "exact_match", 1),
            MockResult(0.85, "fuzzy_match", 1),
            MockResult(0.75, "composite_parse", 2),
            MockResult(0.65, "historical_api", 3),
            MockResult(0.90, "exact_match", 1)
        ]
        
        formatted = ProgressiveAnalysisTemplates.format_mapping_results(results)
        
        # Verify confidence distribution
        assert "Confidence Distribution:" in formatted
        assert "High (≥0.9): 2 (40.0%)" in formatted
        assert "Medium (0.7-0.9): 2 (40.0%)" in formatted
        assert "Low (<0.7): 1 (20.0%)" in formatted
        
        # Verify method distribution
        assert "Methods Used:" in formatted
        assert "exact_match: 2 (40.0%)" in formatted
        assert "fuzzy_match: 1 (20.0%)" in formatted
        
        # Verify stage distribution
        assert "Stage Distribution:" in formatted
        assert "Stage 1: 3 (60.0%)" in formatted
        assert "Stage 2: 1 (20.0%)" in formatted
        assert "Stage 3: 1 (20.0%)" in formatted
    
    def test_format_mapping_results_empty(self):
        """Test mapping results formatting with empty data."""
        empty_results = []
        
        formatted = ProgressiveAnalysisTemplates.format_mapping_results(empty_results)
        
        assert "No mapping results available." in formatted
    
    def test_format_mapping_results_no_attributes(self):
        """Test mapping results formatting with objects lacking expected attributes."""
        
        # Create results without expected attributes
        class MinimalResult:
            pass
        
        minimal_results = [MinimalResult(), MinimalResult()]
        
        formatted = ProgressiveAnalysisTemplates.format_mapping_results(minimal_results)
        
        # Should handle gracefully
        assert "MAPPING RESULTS SAMPLE:" in formatted
        # Should not crash even without expected attributes
    
    def test_create_analysis_context(self):
        """Test creation of comprehensive analysis context."""
        
        progressive_stats = {
            "total_processed": 500,
            "final_match_rate": 0.78,
            "total_time": "30.5 seconds",
            "timestamp": "2025-01-18T10:30:00",
            "stages": {
                "1": {"name": "Direct", "matched": 300, "unmatched": 200}
            }
        }
        
        # Mock mapping results
        class MockResult:
            def __init__(self, confidence, method):
                self.confidence = confidence
                self.match_method = method
                self.stage = 1
        
        mapping_results = [
            MockResult(0.95, "exact"),
            MockResult(0.85, "fuzzy")
        ]
        
        context = ProgressiveAnalysisTemplates.create_analysis_context(
            progressive_stats=progressive_stats,
            mapping_results=mapping_results,
            strategy_name="test_protein_strategy",
            entity_type="protein"
        )
        
        # Verify context structure
        assert context["strategy_name"] == "test_protein_strategy"
        assert context["entity_type"] == "protein"
        assert context["timestamp"] == "2025-01-18T10:30:00"
        assert context["total_results"] == 2
        
        # Verify progressive statistics
        assert context["progressive_statistics"] == progressive_stats
        
        # Verify mapping results summary is included
        assert "MAPPING RESULTS SAMPLE:" in context["mapping_results_summary"]
        
        # Verify execution metadata
        metadata = context["execution_metadata"]
        assert metadata["total_time"] == "30.5 seconds"
        assert metadata["stages_executed"] == 1
        assert metadata["final_match_rate"] == 0.78
        assert metadata["total_processed"] == 500
    
    def test_biological_data_patterns_in_formatting(self):
        """Test that biological data patterns are properly handled in formatting."""
        
        # Test with biological-specific statistics
        bio_stats = {
            "total_processed": 2500,
            "final_match_rate": 0.92,
            "total_time": "3 minutes 45 seconds",
            "stages": {
                "1": {
                    "name": "UniProt Direct Match",
                    "method": "Accession lookup",
                    "matched": 1800,
                    "unmatched": 700,
                    "time": "45 seconds"
                },
                "2": {
                    "name": "Gene Symbol Bridge",
                    "method": "Symbol-to-UniProt mapping",
                    "new_matches": 400,
                    "cumulative_matched": 2200,
                    "time": "2 minutes"
                },
                "3": {
                    "name": "Historical Resolution",
                    "method": "UniProt API historical lookup",
                    "new_matches": 100,
                    "cumulative_matched": 2300,
                    "time": "1 minute"
                }
            }
        }
        
        formatted = ProgressiveAnalysisTemplates.format_progressive_stats(bio_stats)
        
        # Verify biological terminology is preserved
        assert "UniProt Direct Match" in formatted
        assert "Gene Symbol Bridge" in formatted
        assert "Historical Resolution" in formatted
        assert "Accession lookup" in formatted
        assert "UniProt API" in formatted
        
        # Verify calculations are correct for biological data
        assert "Matched: 1,800 (72.0%)" in formatted  # 1800/2500
        assert "New Matches: 400 (+16.0%)" in formatted  # 400/2500
        assert "New Matches: 100 (+4.0%)" in formatted  # 100/2500
    
    def test_edge_case_identifiers_in_context(self):
        """Test handling of edge case identifiers like Q6EMK4 in context."""
        
        # Mock results with edge case identifier
        class EdgeCaseResult:
            def __init__(self, identifier, confidence, method, notes):
                self.identifier = identifier
                self.confidence = confidence
                self.match_method = method
                self.stage = 1
                self.notes = notes
        
        edge_case_results = [
            EdgeCaseResult("P12345", 0.95, "exact_match", "Standard protein"),
            EdgeCaseResult("Q6EMK4", 0.45, "problematic_id", "Known edge case"),
            EdgeCaseResult("O00533", 0.85, "exact_match", "Standard protein")
        ]
        
        formatted = ProgressiveAnalysisTemplates.format_mapping_results(edge_case_results)
        
        # Should handle edge cases gracefully in formatting
        assert "MAPPING RESULTS SAMPLE:" in formatted
        # The formatting should not crash on edge case identifiers