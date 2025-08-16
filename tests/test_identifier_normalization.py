"""Comprehensive tests for the biological identifier normalization system."""

import pytest
import time
from typing import List, Tuple, Dict

# Import the actual implementation
from biomapper.core.standards.identifier_normalizer import (
    UniProtNormalizer,
    HMDBNormalizer,
    EnsemblNormalizer,
    NCBIGeneNormalizer,
    CHEBINormalizer,
    KEGGNormalizer
)
from biomapper.core.standards.identifier_registry import (
    IdentifierRegistry,
    get_registry,
    normalize_identifier,
    detect_identifier_type
)
from biomapper.core.standards.xrefs_parser import XrefsParser


class TestUniProtNormalizer:
    """Test UniProt identifier normalization."""
    
    @pytest.fixture
    def normalizer(self):
        return UniProtNormalizer()
    
    @pytest.mark.parametrize("input_id,expected_base,expected_full,source_format", [
        # Standard formats
        ("P12345", "P12345", "P12345", "standard"),
        ("Q6EMK4", "Q6EMK4", "Q6EMK4", "standard"),
        ("O15143", "O15143", "O15143", "standard"),
        
        # With isoform
        ("P12345-1", "P12345", "P12345-1", "with_isoform"),
        ("Q6EMK4-2", "Q6EMK4", "Q6EMK4-2", "with_isoform"),
        
        # Prefixed
        ("UniProtKB:P12345", "P12345", "P12345", "prefixed"),
        ("PR:Q6EMK4", "Q6EMK4", "Q6EMK4", "prefixed"),
        ("uniprot:P12345", "P12345", "P12345", "prefixed"),
        ("sp:P12345", "P12345", "P12345", "prefixed"),
        ("tr:Q6EMK4", "Q6EMK4", "Q6EMK4", "prefixed"),
        
        # With version
        ("P12345.2", "P12345", "P12345", "with_version"),
        
        # Complex combinations
        ("UniProtKB:P12345-1", "P12345", "P12345-1", "prefixed"),
        ("PR:Q6EMK4-2", "Q6EMK4", "Q6EMK4-2", "prefixed"),
        
        # Case insensitive prefixes
        ("uniprotkb:P12345", "P12345", "P12345", "prefixed"),
        ("UNIPROTKB:Q6EMK4", "Q6EMK4", "Q6EMK4", "prefixed"),
    ])
    def test_normalize(self, normalizer, input_id, expected_base, expected_full, source_format):
        """Test normalization of various UniProt formats."""
        result = normalizer.normalize(input_id)
        assert result is not None
        assert result.base_id == expected_base
        assert result.full_id == expected_full
        assert result.source_format == source_format
        assert result.confidence == 1.0
    
    @pytest.mark.parametrize("invalid_id", [
        "",
        None,
        "12345",
        "INVALID",
        "X12345",
        "P1234",  # Too short
        "P123456789",  # Too long
        "ENSG00000168140",  # Wrong type
    ])
    def test_invalid_identifiers(self, normalizer, invalid_id):
        """Test that invalid identifiers return None."""
        result = normalizer.normalize(invalid_id)
        assert result is None
    
    def test_extract_from_text(self, normalizer):
        """Test extraction of UniProt IDs from free text."""
        text = """
        The protein P12345 interacts with Q6EMK4-1.
        UniProtKB:O15143 is also involved.
        PR:Q6EMK4 shows similar behavior.
        """
        extracted = normalizer.extract_from_text(text)
        assert set(extracted) == {"P12345", "Q6EMK4-1", "O15143", "Q6EMK4"}
    
    def test_strip_isoform(self, normalizer):
        """Test isoform stripping."""
        assert normalizer.strip_isoform("P12345-1") == "P12345"
        assert normalizer.strip_isoform("Q6EMK4-2") == "Q6EMK4"
        assert normalizer.strip_isoform("P12345") == "P12345"
    
    def test_strip_version(self, normalizer):
        """Test version stripping."""
        assert normalizer.strip_version("P12345.2") == "P12345"
        assert normalizer.strip_version("Q6EMK4.1") == "Q6EMK4"
        assert normalizer.strip_version("P12345") == "P12345"


class TestHMDBNormalizer:
    """Test HMDB identifier normalization."""
    
    @pytest.fixture
    def normalizer(self):
        return HMDBNormalizer()
    
    @pytest.mark.parametrize("input_id,expected,confidence,source_format", [
        # Standard format (7 digits)
        ("HMDB0001234", "HMDB0001234", 1.0, "standard"),
        
        # Wrong case
        ("hmdb0001234", "HMDB0001234", 1.0, "wrong_case"),
        ("HmDb0001234", "HMDB0001234", 1.0, "wrong_case"),
        
        # Wrong padding
        ("HMDB00001234", "HMDB0001234", 1.0, "wrong_padding"),
        ("HMDB001234", "HMDB0001234", 1.0, "wrong_padding"),
        ("HMDB1234", "HMDB0001234", 1.0, "wrong_padding"),
        
        # Old format (5 digits)
        ("HMDB00001", "HMDB00001", 0.9, "standard"),
        ("HMDB12345", "HMDB12345", 0.9, "standard"),
        
        # Digits only
        ("0001234", "HMDB0001234", 1.0, "digits_only"),
    ])
    def test_normalize(self, normalizer, input_id, expected, confidence, source_format):
        """Test normalization of various HMDB formats."""
        result = normalizer.normalize(input_id)
        assert result is not None
        assert result.base_id == expected
        assert result.full_id == expected
        assert result.confidence == confidence
        assert result.source_format == source_format
    
    def test_extract_from_text(self, normalizer):
        """Test extraction of HMDB IDs from text."""
        text = "Metabolites HMDB0001234 and hmdb00005678 were analyzed."
        extracted = normalizer.extract_from_text(text)
        assert set(extracted) == {"HMDB0001234", "HMDB0005678"}


class TestEnsemblNormalizer:
    """Test Ensembl identifier normalization."""
    
    @pytest.fixture
    def normalizer(self):
        return EnsemblNormalizer()
    
    @pytest.mark.parametrize("input_id,expected_base,expected_full,id_type", [
        # Gene IDs
        ("ENSG00000168140", "ENSG00000168140", "ENSG00000168140", "gene"),
        ("ENSEMBL:ENSG00000168140", "ENSG00000168140", "ENSG00000168140", "gene"),
        ("ENSG00000168140.5", "ENSG00000168140", "ENSG00000168140.5", "gene"),
        
        # Transcript IDs
        ("ENST00000306864", "ENST00000306864", "ENST00000306864", "transcript"),
        
        # Protein IDs
        ("ENSP00000306864", "ENSP00000306864", "ENSP00000306864", "protein"),
    ])
    def test_normalize(self, normalizer, input_id, expected_base, expected_full, id_type):
        """Test normalization of Ensembl identifiers."""
        result = normalizer.normalize(input_id)
        assert result is not None
        assert result.base_id == expected_base
        assert result.full_id == expected_full
        assert normalizer.get_type(input_id) == id_type
    
    def test_extract_from_text(self, normalizer):
        """Test extraction of Ensembl IDs from text."""
        text = "Gene ENSG00000168140 produces transcript ENST00000306864 and protein ENSP00000306864."
        extracted = normalizer.extract_from_text(text)
        assert set(extracted) == {"ENSG00000168140", "ENST00000306864", "ENSP00000306864"}


class TestXrefsParser:
    """Test xrefs field parsing."""
    
    @pytest.fixture
    def parser(self):
        return XrefsParser()
    
    def test_parse_double_pipe_separated(self, parser):
        """Test parsing of double-pipe separated xrefs."""
        xrefs = "ENSEMBL:ENSG00000168140||ENSEMBL:ENSP00000306864||UniProtKB:Q6EMK4||PR:Q6EMK4"
        result = parser.parse(xrefs)
        
        assert "ensembl" in result
        assert set(result["ensembl"]) == {"ENSG00000168140", "ENSP00000306864"}
        assert "uniprot" in result
        assert "Q6EMK4" in result["uniprot"]
    
    def test_parse_semicolon_separated(self, parser):
        """Test parsing of semicolon-separated xrefs."""
        xrefs = "UniProtKB:P12345;RefSeq:NP_001234;KEGG:K12345"
        result = parser.parse(xrefs)
        
        assert result["uniprot"] == ["P12345"]
        assert result["refseq"] == ["NP_001234"]
        assert result["kegg"] == ["KEGG:K12345"]
    
    def test_extract_uniprot(self, parser):
        """Test extraction of UniProt IDs from complex xrefs."""
        xrefs = "UniProtKB:P12345||PR:Q6EMK4||ENSEMBL:ENSG00000168140"
        uniprot_ids = parser.extract_uniprot(xrefs)
        assert set(uniprot_ids) == {"P12345", "Q6EMK4"}
    
    def test_handle_duplicates(self, parser):
        """Test that duplicates are properly handled."""
        xrefs = "UniProtKB:P12345||PR:P12345||UniProtKB:P12345"
        result = parser.parse(xrefs)
        assert len(result["uniprot"]) == 1
        assert result["uniprot"][0] == "P12345"
    
    def test_handle_malformed_entries(self, parser):
        """Test parsing with malformed entries."""
        xrefs = "UniProtKB:P12345||malformed||RefSeq:NP_001234||:empty||noprefix"
        result = parser.parse(xrefs)
        
        assert "uniprot" in result
        assert "refseq" in result
        # Malformed entries should be ignored
        assert "malformed" not in result
    
    def test_get_primary_identifier(self, parser):
        """Test getting the primary identifier."""
        xrefs = "ENSEMBL:ENSG00000168140||UniProtKB:Q6EMK4||HMDB0001234"
        primary = parser.get_primary_identifier(xrefs)
        assert primary == "Q6EMK4"  # UniProt has highest priority
    
    def test_merge_xrefs(self, parser):
        """Test merging multiple xrefs strings."""
        xrefs_list = [
            "UniProtKB:P12345||ENSEMBL:ENSG00000168140",
            "PR:Q6EMK4||ENSEMBL:ENSG00000168140",  # Duplicate Ensembl
            "UniProtKB:P12345||HMDB0001234"  # Duplicate UniProt
        ]
        merged = parser.merge_xrefs(xrefs_list)
        
        # Should contain unique identifiers
        assert "P12345" in merged
        assert "Q6EMK4" in merged
        assert "ENSG00000168140" in merged
        assert "HMDB0001234" in merged
        # Check no duplicates
        assert merged.count("ENSG00000168140") == 1
        assert merged.count("P12345") == 1
    
    def test_standardize_xrefs(self, parser):
        """Test standardization of xrefs format."""
        xrefs = "uniprot:P12345;ensembl:ENSG00000168140,HMDB0001234"
        standardized = parser.standardize_xrefs(xrefs)
        
        # Should have consistent prefixes and delimiter
        assert "UniProtKB:" in standardized
        assert "ENSEMBL:" in standardized
        assert "HMDB:" in standardized
        assert "||" in standardized
        assert ";" not in standardized
        assert "," not in standardized


class TestIdentifierRegistry:
    """Test the central identifier registry."""
    
    @pytest.fixture
    def registry(self):
        return IdentifierRegistry()
    
    def test_detect_type(self, registry):
        """Test automatic type detection."""
        # UniProt
        detections = registry.detect_type("P12345")
        assert detections[0][0] == "uniprot"
        assert detections[0][1] == 1.0
        
        # HMDB
        detections = registry.detect_type("HMDB0001234")
        assert detections[0][0] == "hmdb"
        
        # Ensembl
        detections = registry.detect_type("ENSG00000168140")
        assert detections[0][0] == "ensembl"
        
        # Ambiguous (plain number could be NCBI Gene or ChEBI)
        detections = registry.detect_type("12345")
        assert len(detections) > 0
        # NCBI Gene should have lower confidence for plain numbers
        for id_type, confidence in detections:
            if id_type == "ncbi_gene":
                assert confidence < 1.0
    
    def test_normalize_any(self, registry):
        """Test normalization with auto-detection."""
        # UniProt
        match = registry.normalize_any("UniProtKB:P12345-1")
        assert match.identifier_type == "uniprot"
        assert match.base_id == "P12345"
        assert match.full_id == "P12345-1"
        
        # HMDB
        match = registry.normalize_any("hmdb0001234")
        assert match.identifier_type == "hmdb"
        assert match.full_id == "HMDB0001234"
        
        # With preferred type
        match = registry.normalize_any("12345", preferred_type="ncbi_gene")
        assert match.identifier_type == "ncbi_gene"
        assert match.full_id == "NCBIGene:12345"
    
    def test_batch_normalize(self, registry):
        """Test batch normalization."""
        identifiers = [
            "P12345",
            "HMDB0001234",
            "ENSG00000168140",
            "NCBIGene:12345",
            "invalid_id"
        ]
        results = registry.normalize_batch(identifiers)
        
        assert len(results) == 5
        assert results[0].identifier_type == "uniprot"
        assert results[1].identifier_type == "hmdb"
        assert results[2].identifier_type == "ensembl"
        assert results[3].identifier_type == "ncbi_gene"
        assert results[4] is None
    
    def test_extract_all_identifiers(self, registry):
        """Test extraction of all identifier types from text."""
        text = """
        The protein P12345 (UniProtKB:Q6EMK4) is encoded by ENSG00000168140.
        Related metabolite: HMDB0001234. See also NCBIGene:12345.
        """
        extracted = registry.extract_all_identifiers(text)
        
        assert "uniprot" in extracted
        assert set(extracted["uniprot"]) == {"P12345", "Q6EMK4"}
        assert "ensembl" in extracted
        assert "ENSG00000168140" in extracted["ensembl"]
        assert "hmdb" in extracted
        assert "HMDB0001234" in extracted["hmdb"]
    
    def test_get_statistics(self, registry):
        """Test statistical analysis of identifiers."""
        identifiers = [
            "P12345", "Q6EMK4", "P12345-1",  # UniProt
            "HMDB0001234", "hmdb00005678",    # HMDB
            "ENSG00000168140",                # Ensembl
            "invalid_id", "another_invalid"   # Invalid
        ]
        stats = registry.get_statistics(identifiers)
        
        assert stats["total"] == 8
        assert stats["valid"] == 6
        assert stats["invalid"] == 2
        assert stats["by_type"]["uniprot"] == 3
        assert stats["by_type"]["hmdb"] == 2
        assert stats["by_type"]["ensembl"] == 1


class TestPerformance:
    """Test performance requirements."""
    
    def test_uniprot_performance(self):
        """Test UniProt normalization performance."""
        normalizer = UniProtNormalizer()
        identifiers = ["P12345", "Q6EMK4-1", "UniProtKB:O15143"] * 33334
        
        start_time = time.time()
        for identifier in identifiers:
            normalizer.normalize(identifier)
        elapsed = time.time() - start_time
        
        rate = len(identifiers) / elapsed
        print(f"UniProt normalization rate: {rate:.0f} identifiers/second")
        # Target: > 100k identifiers/second
        assert rate > 100000, f"Performance too slow: {rate:.0f} ids/sec"
    
    def test_registry_batch_performance(self):
        """Test batch normalization performance."""
        registry = IdentifierRegistry()
        identifiers = ["P12345", "HMDB0001234", "ENSG00000168140"] * 10000
        
        start_time = time.time()
        registry.normalize_batch(identifiers)
        elapsed = time.time() - start_time
        
        rate = len(identifiers) / elapsed
        print(f"Batch normalization rate: {rate:.0f} identifiers/second")
        assert rate > 50000, f"Batch performance too slow: {rate:.0f} ids/sec"
    
    def test_xrefs_parsing_performance(self):
        """Test xrefs parsing performance."""
        parser = XrefsParser()
        xrefs = "ENSEMBL:ENSG00000168140||UniProtKB:Q6EMK4||HMDB0001234||NCBIGene:12345"
        
        start_time = time.time()
        for _ in range(10000):
            parser.parse(xrefs)
        elapsed = time.time() - start_time
        
        rate = 10000 / elapsed
        print(f"Xrefs parsing rate: {rate:.0f} xrefs/second")
        assert rate > 5000, f"Xrefs parsing too slow: {rate:.0f} xrefs/sec"


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_real_world_example_kg2c(self):
        """Test with real KG2c xrefs data."""
        parser = XrefsParser()
        xrefs = "ENSEMBL:ENSG00000168140||ENSEMBL:ENSP00000306864||UniProtKB:Q6EMK4||PR:Q6EMK4"
        
        # Parse and extract UniProt
        uniprot_ids = parser.extract_uniprot(xrefs)
        assert "Q6EMK4" in uniprot_ids
        
        # Verify normalization
        registry = get_registry()
        for uid in uniprot_ids:
            match = registry.normalize_any(uid)
            assert match.identifier_type == "uniprot"
            assert match.base_id == "Q6EMK4"
    
    def test_real_world_example_mixed(self):
        """Test with mixed identifier types."""
        text = """
        Analysis of protein UniProtKB:P12345-1 (gene ENSG00000168140)
        revealed interaction with metabolite HMDB0001234.
        See also NCBIGene:114990 for more information.
        """
        
        registry = get_registry()
        matches = registry.extract_and_normalize(text)
        
        # Check we found all types
        types_found = {m.identifier_type for m in matches}
        assert "uniprot" in types_found
        assert "ensembl" in types_found
        assert "hmdb" in types_found
        
        # Verify specific normalizations
        uniprot_matches = [m for m in matches if m.identifier_type == "uniprot"]
        assert any(m.base_id == "P12345" for m in uniprot_matches)
        assert any(m.full_id == "P12345-1" for m in uniprot_matches)
    
    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        # Test normalize_identifier
        match = normalize_identifier("UniProtKB:P12345")
        assert match.base_id == "P12345"
        
        # Test detect_identifier_type
        id_type = detect_identifier_type("HMDB0001234")
        assert id_type == "hmdb"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])