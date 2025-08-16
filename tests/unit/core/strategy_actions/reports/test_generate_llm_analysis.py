"""Comprehensive tests for GENERATE_LLM_ANALYSIS action using three-level framework."""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from biomapper.core.strategy_actions.reports.generate_llm_analysis import (
    GenerateLLMAnalysisAction,
    LLMAnalysisParams,
    LLMAnalysisResult
)
from biomapper.core.strategy_actions.utils.llm_providers import LLMResponse, LLMUsageMetrics
# from biomapper.testing.base_test_class import ActionTestBase  # Not available yet


class TestGenerateLLMAnalysisAction:
    """Test suite for LLM analysis action using three-level testing framework."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.action = GenerateLLMAnalysisAction()
        self.temp_dir = tempfile.mkdtemp()
        
    def create_sample_progressive_stats(self, scale: str = "minimal") -> Dict[str, Any]:
        """Create sample progressive statistics for testing."""
        if scale == "minimal":
            return {
                "stages": {
                    1: {
                        "name": "direct_match", 
                        "matched": 8, 
                        "unmatched": 2, 
                        "method": "Direct UniProt", 
                        "time": "0.1s"
                    }
                },
                "total_processed": 10,
                "final_match_rate": 0.80,
                "total_time": "0.1s"
            }
        elif scale == "sample":
            return {
                "stages": {
                    1: {
                        "name": "direct_match", 
                        "matched": 650, 
                        "unmatched": 350, 
                        "method": "Direct UniProt", 
                        "time": "0.5s"
                    },
                    2: {
                        "name": "composite_expansion", 
                        "new_matches": 0, 
                        "cumulative_matched": 650, 
                        "method": "Composite parsing", 
                        "time": "0.2s"
                    },
                    3: {
                        "name": "historical_resolution", 
                        "new_matches": 150, 
                        "cumulative_matched": 800, 
                        "method": "Historical API", 
                        "time": "12.3s"
                    }
                },
                "total_processed": 1000,
                "final_match_rate": 0.80,
                "total_time": "13.0s"
            }
        else:  # production scale
            return {
                "stages": {
                    1: {
                        "name": "direct_match", 
                        "matched": 6500, 
                        "unmatched": 3500, 
                        "method": "Direct UniProt", 
                        "time": "2.5s"
                    },
                    2: {
                        "name": "composite_expansion", 
                        "new_matches": 500, 
                        "cumulative_matched": 7000, 
                        "method": "Composite parsing", 
                        "time": "1.2s"
                    },
                    3: {
                        "name": "historical_resolution", 
                        "new_matches": 1500, 
                        "cumulative_matched": 8500, 
                        "method": "Historical API", 
                        "time": "45.3s"
                    },
                    4: {
                        "name": "gene_symbol_bridge", 
                        "new_matches": 800, 
                        "cumulative_matched": 9300, 
                        "method": "Gene Symbol API", 
                        "time": "23.1s"
                    }
                },
                "total_processed": 10000,
                "final_match_rate": 0.93,
                "total_time": "72.1s"
            }
    
    def create_sample_mapping_results(self, count: int = 10) -> List[Any]:
        """Create sample mapping results for testing."""
        results = []
        for i in range(count):
            # Mock mapping result object
            result = MagicMock()
            result.source_id = f"P{12345 + i:05d}"
            result.target_id = f"P{12345 + i:05d}"
            result.match_method = "direct" if i % 2 == 0 else "historical"
            result.confidence = 1.0 if i % 2 == 0 else 0.85
            result.stage = 1 if i % 2 == 0 else 3
            results.append(result)
        return results
    
    def create_mock_llm_response(self, content: str, provider: str = "openai") -> LLMResponse:
        """Create mock LLM response for testing."""
        return LLMResponse(
            content=content,
            usage=LLMUsageMetrics(
                provider=provider,
                model="gpt-4",
                prompt_tokens=1000,
                completion_tokens=500,
                total_tokens=1500
            ),
            success=True
        )
    
    @pytest.mark.asyncio
    async def test_level_1_minimal_data(self):
        """Level 1: Fast unit test with minimal data (<1s execution)."""
        # Setup minimal test data
        progressive_stats = self.create_sample_progressive_stats("minimal")
        mapping_results = self.create_sample_mapping_results(5)
        
        params = LLMAnalysisParams(
            provider="openai",
            model="gpt-4",
            output_format=["summary"],
            output_directory=self.temp_dir,
            strategy_name="test_strategy"
        )
        
        # Mock LLM provider to avoid API calls
        mock_summary = "# Test Analysis\n\nThis is a test analysis report."
        mock_response = self.create_mock_llm_response(mock_summary)
        
        with patch('biomapper.core.strategy_actions.reports.generate_llm_analysis.LLMProviderManager') as mock_manager:
            mock_manager.return_value.generate_analysis_with_fallback = AsyncMock(return_value=mock_response)
            
            # Setup context
            context = {
                "progressive_stats": progressive_stats,
                "mapping_results": mapping_results
            }
            
            # Execute action
            result = await self.action.execute_typed(
                current_identifiers=["P12345", "P12346"],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context
            )
            
            # Assertions
            assert isinstance(result, LLMAnalysisResult)
            assert len(result.generated_files) >= 1  # At least summary and metadata
            assert result.summary_content is not None
            assert "test_strategy" in result.analysis_metadata.get("strategy_name", "")
            
            # Verify files were created
            summary_file = Path(self.temp_dir) / "mapping_summary.md"
            metadata_file = Path(self.temp_dir) / "analysis_metadata.json"
            assert summary_file.exists()
            assert metadata_file.exists()
    
    @pytest.mark.asyncio
    async def test_level_2_sample_data(self):
        """Level 2: Integration test with sample data (<10s execution)."""
        # Setup sample dataset
        progressive_stats = self.create_sample_progressive_stats("sample")
        mapping_results = self.create_sample_mapping_results(1000)
        
        params = LLMAnalysisParams(
            provider="gemini",
            model="gemini-1.5-flash",
            output_format=["summary", "flowchart"],
            include_recommendations=True,
            output_directory=self.temp_dir,
            strategy_name="sample_protein_strategy",
            entity_type="protein",
            analysis_focus=["performance", "quality"],
            fallback_providers=["openai"]
        )
        
        # Mock comprehensive LLM responses
        mock_summary = """# Protein Mapping Analysis Report

## Executive Summary
Achieved 80% protein mapping rate through 3-stage progressive enhancement.

## Stage Performance Analysis
### Stage 1: Direct UniProt Matching
- **Matched:** 650/1000 (65%)
- **Performance:** 0.5s execution
- **Assessment:** Strong baseline performance

### Stage 3: Historical Resolution  
- **New Matches:** 150 (+15%)
- **Cumulative Rate:** 80%
- **Performance:** 12.3s, 35 API calls
- **Assessment:** Significant improvement, moderate cost

## Recommendations
1. Consider caching historical resolutions
2. Investigate unmapped proteins for patterns
"""
        
        mock_flowchart = """graph TD
    A[Input: 1000 proteins] --> B[Stage 1: Direct Match]
    B --> C{650 matched}
    C -->|Matched| D[Direct Results: 65%]
    C -->|350 unmatched| E[Stage 3: Historical API]
    E --> F{150 more matched}
    F -->|Matched| G[Historical Results: +15%]
    F -->|200 unmatched| H[Final: 80% mapped]"""
        
        with patch('biomapper.core.strategy_actions.reports.generate_llm_analysis.LLMProviderManager') as mock_manager:
            # Setup different responses for summary and flowchart
            responses = [
                self.create_mock_llm_response(mock_summary, "gemini"),
                self.create_mock_llm_response(mock_flowchart, "gemini")
            ]
            mock_manager.return_value.generate_analysis_with_fallback = AsyncMock(side_effect=responses)
            
            context = {
                "progressive_stats": progressive_stats,
                "mapping_results": mapping_results
            }
            
            # Execute with performance monitoring
            import time
            start_time = time.time()
            
            result = await self.action.execute_typed(
                current_identifiers=[f"P{i:05d}" for i in range(1000)],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context
            )
            
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert execution_time < 10.0  # Should complete within 10 seconds
            
            # Functionality assertions
            assert len(result.generated_files) >= 3  # summary, flowchart, metadata
            assert result.summary_content is not None
            assert result.flowchart_content is not None
            assert "graph TD" in result.flowchart_content or "flowchart" in result.flowchart_content
            
            # Quality assertions
            assert len(result.analysis_metadata["llm_usage"]) == 2  # Two LLM calls
            assert all(usage.get("provider") == "gemini" for usage in result.analysis_metadata["llm_usage"])
            
            # File content validation
            summary_file = Path(self.temp_dir) / "mapping_summary.md"
            flowchart_file = Path(self.temp_dir) / "strategy_flowchart.mermaid"
            
            assert summary_file.exists()
            assert flowchart_file.exists()
            
            summary_content = summary_file.read_text()
            flowchart_content = flowchart_file.read_text()
            
            assert "Executive Summary" in summary_content
            assert "Recommendations" in summary_content
            assert "graph TD" in flowchart_content or "flowchart" in flowchart_content
    
    @pytest.mark.asyncio
    async def test_level_3_production_subset(self):
        """Level 3: Production subset test with realistic data patterns (<60s)."""
        # Setup production-scale subset
        progressive_stats = self.create_sample_progressive_stats("production")
        mapping_results = self.create_sample_mapping_results(5000)
        
        params = LLMAnalysisParams(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            output_format=["summary", "flowchart"],
            include_recommendations=True,
            output_directory=self.temp_dir,
            strategy_name="production_protein_mapping_v2.3",
            entity_type="protein",
            analysis_focus=["scalability", "edge_cases", "cost_optimization"],
            biological_context="Arivale proteomics dataset with known Q6EMK4-style edge cases",
            fallback_providers=["openai", "gemini"]
        )
        
        # Mock realistic production-quality analysis
        mock_analysis = """# Biomapper Analysis Report - Production Protein Mapping v2.3

## Executive Summary
Achieved exceptional 93% protein mapping rate through 4-stage progressive enhancement across 10,000 protein identifiers. The strategy demonstrates production-ready performance with robust edge case handling and cost-effective API utilization.

## Stage Performance Analysis

### Stage 1: Direct UniProt Matching
- **Matched:** 6,500/10,000 (65%)
- **Performance:** 2.5s execution (2,600 IDs/second)
- **Assessment:** Excellent baseline with optimal performance

### Stage 2: Composite Expansion  
- **New Matches:** 500 (+5%)
- **Cumulative Rate:** 70%
- **Performance:** 1.2s (8,333 IDs/second)
- **Assessment:** Efficient parsing of compound identifiers

### Stage 3: Historical Resolution
- **New Matches:** 1,500 (+15%)
- **Cumulative Rate:** 85%
- **Performance:** 45.3s, ~150 API calls
- **Assessment:** High-value improvement with reasonable API cost

### Stage 4: Gene Symbol Bridge
- **New Matches:** 800 (+8%)
- **Cumulative Rate:** 93%
- **Performance:** 23.1s, ~80 API calls
- **Assessment:** Excellent final stage optimization

## Scientific Assessment
- **Confidence Distribution:** 78% high confidence (≥0.9), 15% medium (0.7-0.9), 7% low (<0.7)
- **Coverage Analysis:** Comprehensive across major protein families
- **Edge Case Handling:** Successfully processed Q6EMK4-style problematic identifiers
- **Reproducibility:** High with deterministic mapping algorithms

## Optimization Recommendations

### Performance Enhancements
1. **Implement staged caching** for historical and gene symbol APIs to reduce redundant calls
2. **Parallel processing** for stages 3-4 could reduce total time by ~40%
3. **Batch API requests** for improved throughput efficiency

### Quality Improvements  
1. **Confidence weighting** for composite results from multiple stages
2. **Cross-validation** against UniProt review status
3. **Isoform handling** refinement for specialized datasets

### Scalability Considerations
1. **Memory optimization** for datasets >50K identifiers
2. **Rate limiting** configuration for production API endpoints
3. **Checkpoint persistence** for very large batch processing

## Cost Analysis
- **Total API Calls:** ~230 across stages 3-4
- **Cost Estimate:** $0.12 per 10K identifiers at current rates
- **Efficiency Ratio:** 430 identifiers mapped per API call
"""
        
        with patch('biomapper.core.strategy_actions.reports.generate_llm_analysis.LLMProviderManager') as mock_manager:
            mock_manager.return_value.generate_analysis_with_fallback = AsyncMock(
                return_value=self.create_mock_llm_response(mock_analysis, "anthropic")
            )
            
            context = {
                "progressive_stats": progressive_stats,
                "mapping_results": mapping_results
            }
            
            # Execute with comprehensive monitoring
            import time
            start_time = time.time()
            
            result = await self.action.execute_typed(
                current_identifiers=[f"P{i:05d}" for i in range(5000)],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context
            )
            
            execution_time = time.time() - start_time
            
            # Production-level assertions
            assert execution_time < 60.0  # Must complete within 1 minute
            assert len(result.generated_files) >= 3
            
            # Quality and content validation
            summary_file = Path(self.temp_dir) / "mapping_summary.md"
            metadata_file = Path(self.temp_dir) / "analysis_metadata.json"
            
            assert summary_file.exists()
            assert metadata_file.exists()
            
            # Content quality checks
            summary_content = summary_file.read_text()
            assert "10,000" in summary_content  # Production scale mentioned
            assert "Q6EMK4" in summary_content  # Edge case handling
            assert "Cost Analysis" in summary_content  # Production considerations
            assert "API Calls" in summary_content  # Resource utilization
            
            # Metadata validation
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            assert metadata["strategy_name"] == "production_protein_mapping_v2.3"
            assert metadata["entity_type"] == "protein"
            assert len(metadata["llm_usage"]) > 0
            assert metadata["provider"] == "anthropic"
    
    @pytest.mark.asyncio
    async def test_error_handling_api_failures(self):
        """Test robust error handling for API failures."""
        params = LLMAnalysisParams(
            provider="openai",
            output_format=["summary"],
            output_directory=self.temp_dir,
            fallback_providers=["anthropic", "gemini"]
        )
        
        # Mock API failure
        with patch('biomapper.core.strategy_actions.reports.generate_llm_analysis.LLMProviderManager') as mock_manager:
            mock_error_response = LLMResponse(
                content="",
                usage=LLMUsageMetrics(provider="openai", model="gpt-4"),
                success=False,
                error_message="API rate limit exceeded"
            )
            mock_manager.return_value.generate_analysis_with_fallback = AsyncMock(return_value=mock_error_response)
            
            context = {
                "progressive_stats": self.create_sample_progressive_stats("minimal"),
                "mapping_results": self.create_sample_mapping_results(5)
            }
            
            result = await self.action.execute_typed(
                current_identifiers=["P12345"],
                current_ontology_type="protein", 
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context
            )
            
            # Should still complete but with error metadata
            assert isinstance(result, LLMAnalysisResult)
            # Metadata file should still be created with error info
            metadata_file = Path(self.temp_dir) / "analysis_metadata.json"
            assert metadata_file.exists()
    
    @pytest.mark.asyncio
    async def test_entity_specific_analysis(self):
        """Test entity-specific analysis customization."""
        test_cases = [
            ("protein", ["UniProt", "Ensembl", "gene symbols"]),
            ("metabolite", ["HMDB", "KEGG", "InChIKey"]),
            ("chemistry", ["LOINC", "test names"])
        ]
        
        for entity_type, expected_terms in test_cases:
            params = LLMAnalysisParams(
                provider="gemini",
                output_format=["summary"],
                output_directory=self.temp_dir,
                entity_type=entity_type,
                strategy_name=f"test_{entity_type}_strategy"
            )
            
            # Mock entity-specific response
            mock_content = f"Analysis for {entity_type} identifiers including {', '.join(expected_terms)}"
            
            with patch('biomapper.core.strategy_actions.reports.generate_llm_analysis.LLMProviderManager') as mock_manager:
                mock_manager.return_value.generate_analysis_with_fallback = AsyncMock(
                    return_value=self.create_mock_llm_response(mock_content, "gemini")
                )
                
                context = {
                    "progressive_stats": self.create_sample_progressive_stats("minimal"),
                    "mapping_results": self.create_sample_mapping_results(3)
                }
                
                result = await self.action.execute_typed(
                    current_identifiers=["TEST001"],
                    current_ontology_type=entity_type,
                    params=params,
                    source_endpoint=None,
                    target_endpoint=None,
                    context=context
                )
                
                assert result.summary_content is not None
                assert entity_type in result.summary_content
                
                # Verify entity type is recorded in metadata
                assert result.analysis_metadata["entity_type"] == entity_type
    
    def test_parameter_validation(self):
        """Test parameter validation and standardization compliance."""
        # Test required parameters
        with pytest.raises(Exception):  # Should fail without output_directory
            LLMAnalysisParams(provider="openai")
        
        # Test valid parameters (2025 standards compliance)
        params = LLMAnalysisParams(
            provider="openai",
            model="gpt-4",
            output_directory="/tmp/test",
            output_format=["summary", "flowchart"],
            entity_type="protein"
        )
        
        assert params.provider == "openai"
        assert params.model == "gpt-4"
        assert "summary" in params.output_format
        assert "flowchart" in params.output_format
    
    def test_results_model_validation(self):
        """Test results model validation."""
        result = LLMAnalysisResult(
            input_identifiers=["P12345"],
            output_identifiers=["P12345"],
            output_ontology_type="protein",
            generated_files=["/tmp/summary.md", "/tmp/flowchart.mermaid"],
            analysis_metadata={"provider": "openai", "model": "gpt-4"}
        )
        
        assert len(result.generated_files) == 2
        assert result.analysis_metadata["provider"] == "openai"
        assert result.input_identifiers == ["P12345"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])