"""Tests for biological identifier parsing functionality."""

import pytest
from unittest.mock import Mock

from actions.utils.data_processing.parse_composite_identifiers_v2 import (
    ParseCompositeIdentifiersAction,
    ParseCompositeIdentifiersParams,
    CompositePattern,
    parse_composite_string,
    expand_dataset_rows
)


class TestCompositePattern:
    """Test CompositePattern model."""
    
    def test_composite_pattern_creation(self):
        """Test CompositePattern creation and defaults."""
        
        pattern = CompositePattern(
            separator="|",
            trim_whitespace=True,
            column="protein_ids",
            validation_pattern=r'^[A-Z][0-9][A-Z0-9]{3,8}$'
        )
        
        assert pattern.separator == "|"
        assert pattern.trim_whitespace is True
        assert pattern.column == "protein_ids"
        assert pattern.validation_pattern == r'^[A-Z][0-9][A-Z0-9]{3,8}$'
    
    def test_composite_pattern_defaults(self):
        """Test CompositePattern default values."""
        
        minimal_pattern = CompositePattern()
        
        assert minimal_pattern.separator == ","
        assert minimal_pattern.trim_whitespace is True
        assert minimal_pattern.column is None
        assert minimal_pattern.validation_pattern is None


class TestParseCompositeString:
    """Test standalone composite string parsing function."""
    
    def test_parse_simple_comma_separated(self):
        """Test parsing simple comma-separated identifiers."""
        
        result = parse_composite_string("P12345,Q9Y6R4,O00533")
        
        assert result == ["P12345", "Q9Y6R4", "O00533"]
    
    def test_parse_pipe_separated(self):
        """Test parsing pipe-separated identifiers."""
        
        result = parse_composite_string("P12345|Q9Y6R4|O00533", ["|"])
        
        assert result == ["P12345", "Q9Y6R4", "O00533"]
    
    def test_parse_with_whitespace(self):
        """Test parsing with whitespace trimming."""
        
        result = parse_composite_string("P12345 , Q9Y6R4 , O00533")
        
        assert result == ["P12345", "Q9Y6R4", "O00533"]
    
    def test_parse_single_identifier(self):
        """Test parsing single identifier (no separator)."""
        
        result = parse_composite_string("P12345")
        
        assert result == ["P12345"]
    
    def test_parse_empty_values(self):
        """Test parsing empty and None values."""
        
        assert parse_composite_string("") == []
        assert parse_composite_string(None) == []
        assert parse_composite_string("   ") == []
    
    def test_parse_multiple_separators(self):
        """Test parsing with multiple possible separators."""
        
        # Should use first matching separator
        result = parse_composite_string("P12345,Q9Y6R4", [";", ",", "|"])
        
        assert result == ["P12345", "Q9Y6R4"]
    
    def test_parse_with_empty_components(self):
        """Test parsing with empty components."""
        
        result = parse_composite_string("P12345,,Q9Y6R4,")
        
        # Should filter out empty components
        assert result == ["P12345", "Q9Y6R4"]
    
    def test_parse_problematic_identifiers(self):
        """Test parsing with problematic identifiers like Q6EMK4."""
        
        result = parse_composite_string("P12345,Q6EMK4,O00533")
        
        # Should preserve Q6EMK4 even though it's problematic
        assert result == ["P12345", "Q6EMK4", "O00533"]
        assert "Q6EMK4" in result


class TestExpandDatasetRows:
    """Test dataset row expansion functionality."""
    
    def test_expand_simple_composite_ids(self):
        """Test expanding simple composite identifiers."""
        
        data = [
            {"protein_id": "P12345,Q9Y6R4", "gene": "TP53"},
            {"protein_id": "O00533", "gene": "CD4"}
        ]
        
        result = expand_dataset_rows(data, "protein_id", ",")
        
        assert len(result) == 3  # 2 from first row + 1 from second
        assert result[0]["protein_id"] == "P12345"
        assert result[1]["protein_id"] == "Q9Y6R4"
        assert result[2]["protein_id"] == "O00533"
        
        # Verify other fields are preserved
        assert result[0]["gene"] == "TP53"
        assert result[1]["gene"] == "TP53"
        assert result[2]["gene"] == "CD4"
    
    def test_expand_with_original_tracking(self):
        """Test expansion with original value tracking."""
        
        data = [
            {"protein_id": "P12345,Q9Y6R4", "description": "Test protein"}
        ]
        
        result = expand_dataset_rows(data, "protein_id", ",")
        
        # Should track original values
        assert result[0]["_original_protein_id"] == "P12345,Q9Y6R4"
        assert result[1]["_original_protein_id"] == "P12345,Q9Y6R4"
        
        # Should track parsed IDs
        assert result[0]["_parsed_ids"] == ["P12345", "Q9Y6R4"]
        assert result[1]["_parsed_ids"] == ["P12345", "Q9Y6R4"]
    
    def test_expand_empty_dataset(self):
        """Test expansion with empty dataset."""
        
        result = expand_dataset_rows([], "protein_id", ",")
        
        assert result == []
    
    def test_expand_with_null_values(self):
        """Test expansion handling null/empty values."""
        
        data = [
            {"protein_id": "P12345,Q9Y6R4", "gene": "TP53"},
            {"protein_id": None, "gene": "UNKNOWN"},
            {"protein_id": "", "gene": "EMPTY"}
        ]
        
        result = expand_dataset_rows(data, "protein_id", ",")
        
        # Should have 4 rows: 2 from first + 1 null + 1 empty
        assert len(result) == 4
        assert result[0]["protein_id"] == "P12345"
        assert result[1]["protein_id"] == "Q9Y6R4"
        assert result[2]["protein_id"] is None
        assert result[3]["protein_id"] == ""
    
    def test_expand_edge_case_identifiers(self):
        """Test expansion with edge case identifiers."""
        
        data = [
            {"protein_id": "P12345,Q6EMK4,INVALID", "confidence": "high"}
        ]
        
        result = expand_dataset_rows(data, "protein_id", ",")
        
        assert len(result) == 3
        assert result[0]["protein_id"] == "P12345"
        assert result[1]["protein_id"] == "Q6EMK4"  # Edge case preserved
        assert result[2]["protein_id"] == "INVALID"
        
        # All should have same metadata
        for row in result:
            assert row["confidence"] == "high"
            assert row["_original_protein_id"] == "P12345,Q6EMK4,INVALID"


class TestParseCompositeIdentifiersParams:
    """Test parameter model validation."""
    
    def test_params_with_standard_names(self):
        """Test parameters with standardized naming."""
        
        params = ParseCompositeIdentifiersParams(
            input_key="source_proteins",
            id_field="protein_ids",
            output_key="expanded_proteins",
            separators=[",", ";", "|"],
            preserve_original=True
        )
        
        assert params.input_key == "source_proteins"
        assert params.id_field == "protein_ids"
        assert params.output_key == "expanded_proteins"
        assert params.separators == [",", ";", "|"]
        assert params.preserve_original is True
    
    def test_params_with_legacy_names(self):
        """Test parameters with legacy naming support."""
        
        params = ParseCompositeIdentifiersParams(
            dataset_key="source_proteins",  # Legacy name
            id_field="protein_ids",
            output_context_key="expanded_proteins",  # Legacy name
        )
        
        assert params.dataset_key == "source_proteins"
        assert params.output_context_key == "expanded_proteins"
        assert params.input_key is None  # Should be None when using legacy
    
    def test_params_validation_options(self):
        """Test validation and processing options."""
        
        params = ParseCompositeIdentifiersParams(
            input_key="test",
            id_field="ids",
            output_key="output",
            validate_format=True,
            entity_type="uniprot",
            skip_empty=True,
            trim_whitespace=False,
            preserve_order=True
        )
        
        assert params.validate_format is True
        assert params.entity_type == "uniprot"
        assert params.skip_empty is True
        assert params.trim_whitespace is False
        assert params.preserve_order is True


class TestParseCompositeIdentifiersAction:
    """Test ParseCompositeIdentifiersAction functionality."""
    
    @pytest.fixture
    def biological_datasets(self):
        """Create biological datasets for testing."""
        return {
            "proteins": [
                {"protein_id": "P12345,Q9Y6R4", "gene_symbol": "TP53", "confidence": 0.95},
                {"protein_id": "O00533", "gene_symbol": "CD4", "confidence": 0.88},
                {"protein_id": "P38398;P04626", "gene_symbol": "BRCA1", "confidence": 0.92}
            ],
            "metabolites": [
                {"compound_id": "HMDB0000001|HMDB0000002", "name": "Compound A", "mass": 180.0},
                {"compound_id": "HMDB0000003", "name": "Compound B", "mass": 220.0}
            ],
            "edge_cases": [
                {"mixed_id": "P12345,Q6EMK4,INVALID", "notes": "Contains edge case"},
                {"mixed_id": "", "notes": "Empty identifier"},
                {"mixed_id": "P04637", "notes": "Single identifier"}
            ]
        }
    
    @pytest.fixture
    def action_context(self, biological_datasets):
        """Create test action context."""
        return {
            "datasets": biological_datasets,
            "statistics": {}
        }
    
    @pytest.mark.asyncio
    async def test_basic_composite_parsing(self, action_context):
        """Test basic composite identifier parsing."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="protein_id",
            output_key="expanded_proteins",
            separators=[","]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        assert result.rows_processed == 3
        assert result.rows_expanded == 4  # P12345,Q9Y6R4 -> 2, O00533 -> 1, P38398;P04626 -> 1
        assert result.composite_count == 1  # Only first row has comma separator
        
        # Verify expanded data
        expanded_data = action_context["datasets"]["expanded_proteins"]
        assert len(expanded_data) == 4
        
        # Check that composite ID was split
        protein_ids = [row["protein_id"] for row in expanded_data]
        assert "P12345" in protein_ids
        assert "Q9Y6R4" in protein_ids
        assert "O00533" in protein_ids
        assert "P38398;P04626" in protein_ids  # Not split because separator is comma, not semicolon
    
    @pytest.mark.asyncio
    async def test_multiple_separators(self, action_context):
        """Test parsing with multiple separators."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="protein_id",
            output_key="multi_sep_proteins",
            separators=[",", ";"],  # Both comma and semicolon
            preserve_original=True
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        assert result.rows_expanded == 5  # Should now split both comma and semicolon
        
        # Verify both separators were handled
        expanded_data = action_context["datasets"]["multi_sep_proteins"]
        protein_ids = [row["protein_id"] for row in expanded_data]
        assert "P12345" in protein_ids
        assert "Q9Y6R4" in protein_ids
        assert "P38398" in protein_ids  # Should be split from P38398;P04626
        assert "P04626" in protein_ids
    
    @pytest.mark.asyncio
    async def test_preserve_original_and_order(self, action_context):
        """Test preserving original values and order."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="protein_id",
            output_key="preserved_proteins",
            separators=[","],
            preserve_original=True,
            preserve_order=True
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        expanded_data = action_context["datasets"]["preserved_proteins"]
        
        # Check original value preservation
        p12345_row = next(row for row in expanded_data if row["protein_id"] == "P12345")
        assert p12345_row["_original_protein_id"] == "P12345,Q9Y6R4"
        assert p12345_row["_expansion_count"] == 2
        
        # Check order preservation
        assert "_original_index" in p12345_row
        assert p12345_row["_original_index"] == 0  # First row in original data
    
    @pytest.mark.asyncio
    async def test_uniprot_validation(self, action_context):
        """Test UniProt identifier validation."""
        
        # Add dataset with invalid UniProt IDs
        action_context["datasets"]["mixed_proteins"] = [
            {"protein_id": "P12345,INVALID123,Q9Y6R4", "source": "test"}
        ]
        
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="mixed_proteins",
            id_field="protein_id",
            output_key="validated_proteins",
            separators=[","],
            validate_format=True,
            entity_type="uniprot"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Should only include valid UniProt IDs
        expanded_data = action_context["datasets"]["validated_proteins"]
        protein_ids = [row["protein_id"] for row in expanded_data]
        assert "P12345" in protein_ids
        assert "Q9Y6R4" in protein_ids
        assert "INVALID123" not in protein_ids  # Should be filtered out
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self, action_context):
        """Test handling of edge cases including Q6EMK4."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="edge_cases",
            id_field="mixed_id",
            output_key="edge_case_results",
            separators=[","],
            skip_empty=False  # Don't skip empty values
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        expanded_data = action_context["datasets"]["edge_case_results"]
        
        # Verify Q6EMK4 is preserved
        q6emk4_rows = [row for row in expanded_data if row["mixed_id"] == "Q6EMK4"]
        assert len(q6emk4_rows) == 1
        assert q6emk4_rows[0]["notes"] == "Contains edge case"
        
        # Verify empty values are handled
        empty_rows = [row for row in expanded_data if row["mixed_id"] == ""]
        assert len(empty_rows) == 1
        assert empty_rows[0]["notes"] == "Empty identifier"
    
    @pytest.mark.asyncio
    async def test_skip_empty_values(self, action_context):
        """Test skipping empty values."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="edge_cases",
            id_field="mixed_id",
            output_key="no_empty_results",
            separators=[","],
            skip_empty=True  # Skip empty values
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        expanded_data = action_context["datasets"]["no_empty_results"]
        
        # Should not include empty identifier
        mixed_ids = [row["mixed_id"] for row in expanded_data]
        assert "" not in mixed_ids
        assert "P12345" in mixed_ids  # Should include valid ones
        assert "Q6EMK4" in mixed_ids  # Should include edge case
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, action_context):
        """Test statistics tracking functionality."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="protein_id",
            output_key="stats_proteins",
            separators=[",", ";"],
            track_expansion=True
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify statistics are tracked
        stats = action_context["statistics"]
        assert "composite_tracking" in stats
        assert "composite_expansion" in stats
        
        composite_stats = stats["composite_tracking"]
        assert composite_stats["total_input"] == 3
        assert composite_stats["individual_count"] == result.rows_expanded
        assert composite_stats["expansion_factor"] == result.expansion_factor
        
        expansion_stats = stats["composite_expansion"]
        assert expansion_stats["dataset_key"] == "proteins"
        assert expansion_stats["field"] == "protein_id"
        assert expansion_stats["total_input_rows"] == 3
        assert expansion_stats["separators_used"] == [",", ";"]
    
    @pytest.mark.asyncio
    async def test_error_handling_missing_dataset(self, action_context):
        """Test error handling for missing dataset."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="nonexistent_dataset",
            id_field="protein_id",
            output_key="error_test"
        )
        
        # Should raise KeyError for backward compatibility
        with pytest.raises(KeyError, match="Dataset 'nonexistent_dataset' not found"):
            await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context=action_context
            )
    
    @pytest.mark.asyncio
    async def test_error_handling_missing_field(self, action_context):
        """Test error handling for missing field."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="nonexistent_field",
            output_key="error_test"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is False
        assert "not found in dataset" in result.message
    
    @pytest.mark.asyncio
    async def test_error_handling_missing_output_key(self, action_context):
        """Test error handling for missing output key."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            input_key="proteins",
            id_field="protein_id"
            # No output_key specified
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is False
        assert "No output dataset key specified" in result.message
    
    @pytest.mark.asyncio
    async def test_legacy_parameter_support(self, action_context):
        """Test support for legacy parameter names."""
        action = ParseCompositeIdentifiersAction()
        
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",  # Legacy name
            id_field="protein_id",
            output_context_key="legacy_output",  # Legacy name
            separators=[","]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        assert "legacy_output" in action_context["datasets"]
        assert len(action_context["datasets"]["legacy_output"]) > 0


class TestBiologicalIdentifierPatterns:
    """Test parsing of realistic biological identifier patterns."""
    
    def test_uniprot_composite_patterns(self):
        """Test UniProt composite identifier patterns."""
        
        # Common UniProt composite patterns
        test_cases = [
            "UniProtKB:P12345|RefSeq:NP_000546|KEGG:hsa:7157",
            "P12345;Q9Y6R4;O00533",
            "P12345,P38398,P01730",
            "P12345|P38398|P01730"
        ]
        
        for composite_id in test_cases:
            # Determine appropriate separator
            if "|" in composite_id:
                separators = ["|"]
            elif ";" in composite_id:
                separators = [";"]
            else:
                separators = [","]
            
            result = parse_composite_string(composite_id, separators)
            
            # Should have multiple components
            assert len(result) > 1
            
            # Should contain UniProt-like identifiers (either direct or with prefix)
            uniprot_ids = []
            for id in result:
                # Handle both direct UniProt IDs and prefixed ones
                if id.startswith(('P', 'Q', 'O')) and len(id) >= 6:
                    uniprot_ids.append(id)
                elif ':' in id:
                    # Check if it's a prefixed UniProt ID
                    prefix, actual_id = id.split(':', 1)
                    if actual_id.startswith(('P', 'Q', 'O')) and len(actual_id) >= 6:
                        uniprot_ids.append(actual_id)
            
            assert len(uniprot_ids) > 0, f"No UniProt IDs found in {result} from {composite_id}"
    
    def test_metabolite_composite_patterns(self):
        """Test metabolite composite identifier patterns."""
        
        test_cases = [
            "HMDB0000001,HMDB0000002,HMDB0000003",
            "HMDB0000001|CHEBI:28001|KEGG:C00001",
            "BQJCRHHNABKAKU-KBQPJGBKSA-N;WSFSSNUMVMOOMR-UHFFFAOYSA-N"  # InChIKeys
        ]
        
        for composite_id in test_cases:
            # Determine appropriate separator
            if "," in composite_id:
                separators = [","]
            elif "|" in composite_id:
                separators = ["|"]
            else:
                separators = [";"]
            
            result = parse_composite_string(composite_id, separators)
            
            # Should have multiple components
            assert len(result) > 1
            
            # Should preserve metabolite identifier formats
            if "HMDB" in composite_id:
                hmdb_ids = [id for id in result if "HMDB" in id]
                assert len(hmdb_ids) > 0
    
    def test_problematic_identifier_edge_cases(self):
        """Test problematic biological identifiers."""
        
        edge_cases = [
            "Q6EMK4",  # Known problematic UniProt ID
            "Q6EMK4,P12345",  # Composite with problematic ID
            "P12345-1,P12345-2",  # Isoform identifiers
            "P12345.1,P12345.2",  # Version identifiers
            "",  # Empty string
            "INVALID_ID_FORMAT",  # Invalid format
            "123456",  # Numeric only
        ]
        
        for edge_case in edge_cases:
            if not edge_case:  # Skip empty string for this test
                continue
                
            result = parse_composite_string(edge_case, [","])
            
            # Should handle gracefully without crashing
            assert isinstance(result, list)
            
            if edge_case == "Q6EMK4":
                assert result == ["Q6EMK4"]  # Should preserve as-is
            elif "Q6EMK4" in edge_case:
                assert "Q6EMK4" in result  # Should be in parsed components


class TestPerformanceAndScalability:
    """Test performance characteristics with large datasets."""
    
    @pytest.mark.asyncio
    async def test_large_dataset_parsing(self):
        """Test parsing performance with large biological datasets."""
        action = ParseCompositeIdentifiersAction()
        
        # Generate large dataset with composite identifiers
        large_size = 10000
        large_dataset = []
        for i in range(large_size):
            composite_id = f"P{i:05d},Q{i:05d}" if i % 3 == 0 else f"O{i:05d}"
            large_dataset.append({
                "protein_id": composite_id,
                "index": i
            })
        
        context = {
            "datasets": {"large_proteins": large_dataset},
            "statistics": {}
        }
        
        params = ParseCompositeIdentifiersParams(
            input_key="large_proteins",
            id_field="protein_id",
            output_key="expanded_large_proteins",
            separators=[","]
        )
        
        import time
        start_time = time.time()
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=context
        )
        
        execution_time = time.time() - start_time
        
        assert result.success is True
        assert result.rows_processed == large_size
        
        # Should process reasonably quickly
        assert execution_time < 30.0  # Generous bound for CI
        
        # Verify expansion worked correctly
        # Count actual composite IDs (includes index 0, so it's 3334, not 3333)
        actual_composite_count = sum(1 for i in range(large_size) if i % 3 == 0)
        expected_expansion = large_size + actual_composite_count
        assert result.rows_expanded == expected_expansion
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency with large datasets."""
        action = ParseCompositeIdentifiersAction()
        
        # Create dataset with moderate size
        dataset_size = 50000
        test_dataset = []
        for i in range(dataset_size):
            test_dataset.append({
                "id": f"P{i:05d},Q{i:05d},O{i:05d}",  # 3 components each
                "data": f"protein_{i}"
            })
        
        context = {
            "datasets": {"memory_test": test_dataset},
            "statistics": {}
        }
        
        params = ParseCompositeIdentifiersParams(
            input_key="memory_test",
            id_field="id",
            output_key="memory_test_output",
            separators=[","]
        )
        
        # Monitor memory usage
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=context
        )
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        assert result.success is True
        assert result.rows_processed == dataset_size
        assert result.rows_expanded == dataset_size * 3  # Each ID has 3 components
        
        # Memory increase should be reasonable (very generous bound)
        assert memory_increase < 500 * 1024 * 1024  # < 500MB increase
    
    def test_delimiter_detection_performance(self):
        """Test performance of delimiter detection with various patterns."""
        
        # Test various delimiter patterns
        test_patterns = [
            ("P12345,Q9Y6R4,O00533", ","),
            ("P12345;Q9Y6R4;O00533", ";"),
            ("P12345|Q9Y6R4|O00533", "|"),
            ("P12345 Q9Y6R4 O00533", " "),
            ("P12345\tQ9Y6R4\tO00533", "\t")
        ]
        
        # Test many times to check performance
        import time
        start_time = time.time()
        
        for _ in range(1000):
            for pattern, expected_delimiter in test_patterns:
                result = parse_composite_string(pattern, [",", ";", "|", " ", "\t"])
                assert len(result) == 3  # Should split into 3 components
        
        execution_time = time.time() - start_time
        
        # Should be fast even with many iterations
        assert execution_time < 1.0  # Should complete in < 1 second