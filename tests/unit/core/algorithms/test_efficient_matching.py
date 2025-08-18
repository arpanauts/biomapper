"""Tests for efficient_matching.py."""

import pytest
import pandas as pd
import numpy as np
import time

from core.algorithms.efficient_matching import (
    MatchResult,
    EfficientMatcher
)


class TestMatchResult:
    """Test MatchResult dataclass."""
    
    def test_match_result_basic_instantiation(self):
        """Test basic MatchResult instantiation."""
        result = MatchResult(
            source_item="P12345",
            target_item="UniProt:P12345",
            match_score=1.0,
            match_type="exact"
        )
        
        assert result.source_item == "P12345"
        assert result.target_item == "UniProt:P12345"
        assert result.match_score == 1.0
        assert result.match_type == "exact"
    
    def test_match_result_default_values(self):
        """Test MatchResult default values."""
        result = MatchResult(
            source_item="HMDB0000001",
            target_item="KEGG:C00001"
        )
        
        assert result.match_score == 1.0
        assert result.match_type == "exact"
    
    def test_match_result_biological_data(self):
        """Test MatchResult with biological data."""
        protein_match = MatchResult(
            source_item={"id": "P12345", "gene": "TP53"},
            target_item={"id": "ENSP00000269305", "gene": "TP53"},
            match_score=0.95,
            match_type="fuzzy"
        )
        
        assert protein_match.source_item["gene"] == "TP53"
        assert protein_match.target_item["gene"] == "TP53"
        assert protein_match.match_score == 0.95
        assert protein_match.match_type == "fuzzy"


class TestEfficientMatcherBasicOperations:
    """Test basic EfficientMatcher operations."""
    
    def test_build_index_simple(self):
        """Test building simple index."""
        items = ["P12345", "Q9Y6R4", "O15552"]
        key_func = lambda x: x
        
        index = EfficientMatcher.build_index(items, key_func)
        
        assert index["P12345"] == ["P12345"]
        assert index["Q9Y6R4"] == ["Q9Y6R4"]
        assert index["O15552"] == ["O15552"]
        assert len(index) == 3
    
    def test_build_index_with_duplicates(self):
        """Test building index with duplicate keys."""
        items = [
            {"id": "P12345", "type": "protein"},
            {"id": "P12345", "type": "isoform"},
            {"id": "Q9Y6R4", "type": "protein"}
        ]
        key_func = lambda x: x["id"]
        
        index = EfficientMatcher.build_index(items, key_func)
        
        assert len(index["P12345"]) == 2
        assert len(index["Q9Y6R4"]) == 1
        assert index["P12345"][0]["type"] == "protein"
        assert index["P12345"][1]["type"] == "isoform"
    
    def test_build_index_ignores_empty_keys(self):
        """Test index building ignores empty keys."""
        items = ["P12345", "", None, "Q9Y6R4"]
        key_func = lambda x: x if x else ""
        
        index = EfficientMatcher.build_index(items, key_func)
        
        assert "P12345" in index
        assert "Q9Y6R4" in index
        assert "" not in index
        assert len(index) == 2
    
    def test_build_index_biological_patterns(self):
        """Test index with biological identifier patterns."""
        proteins = [
            {"uniprot_id": "P12345", "gene_name": "TP53"},
            {"uniprot_id": "Q9Y6R4", "gene_name": "BRCA1"},
            {"uniprot_id": "O15552", "gene_name": "TEKT4"}
        ]
        
        # Index by UniProt ID
        uniprot_index = EfficientMatcher.build_index(proteins, lambda x: x["uniprot_id"])
        assert "P12345" in uniprot_index
        assert uniprot_index["P12345"][0]["gene_name"] == "TP53"
        
        # Index by gene name
        gene_index = EfficientMatcher.build_index(proteins, lambda x: x["gene_name"])
        assert "BRCA1" in gene_index
        assert gene_index["BRCA1"][0]["uniprot_id"] == "Q9Y6R4"
    
    def test_match_with_index_basic(self):
        """Test basic matching with index."""
        source = ["P12345", "Q9Y6R4", "NOTFOUND"]
        target = ["P12345", "O15552", "Q9Y6R4"]
        
        target_index = EfficientMatcher.build_index(target, lambda x: x)
        matches = EfficientMatcher.match_with_index(source, target_index, lambda x: x)
        
        match_pairs = [(m.source_item, m.target_item) for m in matches]
        
        assert ("P12345", "P12345") in match_pairs
        assert ("Q9Y6R4", "Q9Y6R4") in match_pairs
        assert len(matches) == 2
        
        # Check all matches are exact type
        for match in matches:
            assert match.match_score == 1.0
            assert match.match_type == "exact"
    
    def test_match_with_index_complex_objects(self):
        """Test matching with complex objects."""
        source_proteins = [
            {"id": "P12345", "source": "uniprot"},
            {"id": "Q9Y6R4", "source": "uniprot"}
        ]
        
        target_proteins = [
            {"identifier": "P12345", "database": "ensembl"},
            {"identifier": "O15552", "database": "ensembl"}
        ]
        
        target_index = EfficientMatcher.build_index(target_proteins, lambda x: x["identifier"])
        matches = EfficientMatcher.match_with_index(
            source_proteins, 
            target_index, 
            lambda x: x["id"]
        )
        
        assert len(matches) == 1
        match = matches[0]
        assert match.source_item["id"] == "P12345"
        assert match.target_item["identifier"] == "P12345"
    
    def test_multi_key_index(self):
        """Test multi-key indexing."""
        proteins = [
            {"uniprot": "P12345", "gene": "TP53", "ensembl": "ENSP00000269305"},
            {"uniprot": "Q9Y6R4", "gene": "BRCA1", "ensembl": "ENSP00000350283"}
        ]
        
        key_funcs = [
            lambda x: x.get("uniprot"),
            lambda x: x.get("gene"),
            lambda x: x.get("ensembl")
        ]
        
        index = EfficientMatcher.multi_key_index(proteins, key_funcs)
        
        # Check UniProt key (priority 0)
        assert "P12345" in index
        assert index["P12345"][0][0] == 0  # Priority
        assert index["P12345"][0][1]["gene"] == "TP53"
        
        # Check gene key (priority 1)
        assert "BRCA1" in index
        assert index["BRCA1"][0][0] == 1  # Priority
        assert index["BRCA1"][0][1]["uniprot"] == "Q9Y6R4"
        
        # Check Ensembl key (priority 2)
        assert "ENSP00000269305" in index
        assert index["ENSP00000269305"][0][0] == 2  # Priority
    
    def test_multi_key_index_handles_exceptions(self):
        """Test multi-key index handles key extraction exceptions."""
        items = [
            {"id": "P12345", "name": "protein1"},
            {"id": "Q9Y6R4"},  # Missing 'name' key
            {"different_structure": True}  # Missing 'id' key
        ]
        
        key_funcs = [
            lambda x: x["id"],  # Will fail for third item
            lambda x: x["name"]  # Will fail for second and third items
        ]
        
        index = EfficientMatcher.multi_key_index(items, key_funcs)
        
        # Should only index items where keys could be extracted
        assert "P12345" in index
        assert "protein1" in index
        assert "Q9Y6R4" in index
        assert len(index) == 3  # P12345, protein1, Q9Y6R4


class TestEfficientMatcherDataFrameOperations:
    """Test DataFrame-based operations."""
    
    def test_dataframe_index_merge_basic(self):
        """Test basic DataFrame merge."""
        df1 = pd.DataFrame({
            "uniprot_id": ["P12345", "Q9Y6R4", "O15552"],
            "gene_name": ["TP53", "BRCA1", "TEKT4"]
        })
        
        df2 = pd.DataFrame({
            "protein_id": ["P12345", "Q9Y6R4", "UNKNOWN"],
            "pathway": ["p53_pathway", "dna_repair", "unknown_pathway"]
        })
        
        result = EfficientMatcher.dataframe_index_merge(
            df1, df2, "uniprot_id", "protein_id", how="inner"
        )
        
        assert len(result) == 2
        assert "P12345" in result["uniprot_id"].values
        assert "Q9Y6R4" in result["uniprot_id"].values
        assert "dna_repair" in result["pathway"].values
    
    def test_dataframe_index_merge_different_joins(self):
        """Test different join types."""
        df1 = pd.DataFrame({
            "id": ["A", "B", "C"],
            "value1": [1, 2, 3]
        })
        
        df2 = pd.DataFrame({
            "id": ["B", "C", "D"],
            "value2": [20, 30, 40]
        })
        
        # Inner join
        inner_result = EfficientMatcher.dataframe_index_merge(df1, df2, "id", "id", how="inner")
        assert len(inner_result) == 2
        
        # Left join
        left_result = EfficientMatcher.dataframe_index_merge(df1, df2, "id", "id", how="left")
        assert len(left_result) == 3
        
        # Outer join
        outer_result = EfficientMatcher.dataframe_index_merge(df1, df2, "id", "id", how="outer")
        assert len(outer_result) == 4
    
    def test_dataframe_vectorized_match(self):
        """Test vectorized DataFrame matching."""
        df1 = pd.DataFrame({
            "uniprot": ["P12345", "Q9Y6R4"],
            "gene": ["TP53", "BRCA1"],
            "type": ["tumor_suppressor", "tumor_suppressor"]
        })
        
        df2 = pd.DataFrame({
            "uniprot": ["P12345", "O15552"],
            "gene": ["TP53", "TEKT4"],
            "function": ["transcription_factor", "structural"]
        })
        
        result = EfficientMatcher.dataframe_vectorized_match(
            df1, df2, ["uniprot", "gene"]
        )
        
        assert len(result) == 1
        assert result.iloc[0]["uniprot_source"] == "P12345"
        assert result.iloc[0]["gene_source"] == "TP53"
        assert result.iloc[0]["function"] == "transcription_factor"
    
    def test_dataframe_vectorized_match_biological_data(self):
        """Test vectorized matching with biological data patterns."""
        metabolites_df1 = pd.DataFrame({
            "hmdb_id": ["HMDB0000001", "HMDB0000123", "HMDB0006456"],
            "compound_name": ["1-Methylhistidine", "Acetylcarnitine", "Unknown"],
            "molecular_weight": [169.18, 203.24, 150.0]
        })
        
        metabolites_df2 = pd.DataFrame({
            "hmdb_id": ["HMDB0000001", "HMDB0000123", "HMDB0009999"],
            "kegg_id": ["C02178", "C02990", "C99999"],
            "pathway_class": ["amino_acid", "lipid", "unknown"]
        })
        
        result = EfficientMatcher.dataframe_vectorized_match(
            metabolites_df1, metabolites_df2, ["hmdb_id"]
        )
        
        assert len(result) == 2
        assert "C02178" in result["kegg_id"].values
        assert "amino_acid" in result["pathway_class"].values
        assert 169.18 in result["molecular_weight"].values


class TestEfficientMatcherAdvancedAlgorithms:
    """Test advanced matching algorithms."""
    
    def test_batch_lookup(self):
        """Test batch lookup operation."""
        lookup_dict = {
            "P12345": "TP53",
            "Q9Y6R4": "BRCA1", 
            "O15552": "TEKT4"
        }
        
        keys = ["P12345", "UNKNOWN", "Q9Y6R4", "MISSING"]
        default_value = "NOT_FOUND"
        
        results = EfficientMatcher.batch_lookup(keys, lookup_dict, default_value)
        
        expected = ["TP53", "NOT_FOUND", "BRCA1", "NOT_FOUND"]
        assert results == expected
    
    def test_batch_lookup_biological_mapping(self):
        """Test batch lookup with biological mappings."""
        uniprot_to_gene = {
            "P12345": "TP53",
            "Q9Y6R4": "BRCA1",
            "O15552": "TEKT4",
            "P04637": "TP53"  # Another isoform
        }
        
        protein_ids = ["P12345", "Q9Y6R4", "UNKNOWN_PROTEIN", "P04637"]
        
        gene_names = EfficientMatcher.batch_lookup(protein_ids, uniprot_to_gene, "UNKNOWN_GENE")
        
        assert gene_names == ["TP53", "BRCA1", "UNKNOWN_GENE", "TP53"]
    
    def test_set_intersection_match(self):
        """Test set intersection matching."""
        source_proteins = ["P12345", "Q9Y6R4", "O15552", "P04637"]
        target_proteins = ["P12345", "Q9Y6R4", "UNKNOWN1", "UNKNOWN2"]
        
        matched, source_only, target_only = EfficientMatcher.set_intersection_match(
            source_proteins, target_proteins
        )
        
        assert set(matched) == {"P12345", "Q9Y6R4"}
        assert set(source_only) == {"O15552", "P04637"}
        assert set(target_only) == {"UNKNOWN1", "UNKNOWN2"}
    
    def test_set_intersection_match_metabolites(self):
        """Test set intersection with metabolite identifiers."""
        hmdb_ids = ["HMDB0000001", "HMDB0000123", "HMDB0006456", "HMDB0000789"]
        kegg_mapped = ["HMDB0000001", "HMDB0006456", "HMDB0009999", "HMDB0001234"]
        
        matched, hmdb_only, kegg_only = EfficientMatcher.set_intersection_match(
            hmdb_ids, kegg_mapped
        )
        
        assert set(matched) == {"HMDB0000001", "HMDB0006456"}
        assert set(hmdb_only) == {"HMDB0000123", "HMDB0000789"}
        assert set(kegg_only) == {"HMDB0009999", "HMDB0001234"}
    
    def test_sorted_merge_join(self):
        """Test sorted merge join algorithm."""
        source = [("A", "source_A"), ("C", "source_C"), ("E", "source_E")]
        target = [("A", "target_A"), ("B", "target_B"), ("C", "target_C")]
        
        matches = EfficientMatcher.sorted_merge_join(source, target)
        
        expected_matches = [("source_A", "target_A"), ("source_C", "target_C")]
        assert matches == expected_matches
    
    def test_sorted_merge_join_with_duplicates(self):
        """Test sorted merge join with duplicate keys."""
        source = [("A", "source_A1"), ("A", "source_A2"), ("B", "source_B")]
        target = [("A", "target_A1"), ("A", "target_A2"), ("C", "target_C")]
        
        matches = EfficientMatcher.sorted_merge_join(source, target)
        
        # Should create cartesian product for matching keys
        expected_matches = [
            ("source_A1", "target_A1"),
            ("source_A1", "target_A2"),
            ("source_A2", "target_A1"),
            ("source_A2", "target_A2")
        ]
        assert set(matches) == set(expected_matches)
    
    def test_sorted_merge_join_biological_data(self):
        """Test sorted merge join with biological identifiers."""
        # Sorted protein data
        uniprot_data = [
            ("BRCA1", {"uniprot": "Q9Y6R4", "chr": "17"}),
            ("TP53", {"uniprot": "P12345", "chr": "17"}),
            ("TEKT4", {"uniprot": "O15552", "chr": "2"})
        ]
        
        ensembl_data = [
            ("BRCA1", {"ensembl": "ENSP00000350283", "length": 1863}),
            ("TP53", {"ensembl": "ENSP00000269305", "length": 393})
        ]
        
        matches = EfficientMatcher.sorted_merge_join(uniprot_data, ensembl_data)
        
        assert len(matches) == 2
        
        # Find TP53 match
        tp53_match = next(m for m in matches if m[0]["uniprot"] == "P12345")
        assert tp53_match[1]["ensembl"] == "ENSP00000269305"
        assert tp53_match[1]["length"] == 393
    
    def test_hash_partition_match(self):
        """Test hash partition matching."""
        source = [f"protein_{i}" for i in range(100)]
        target = [f"protein_{i}" for i in range(50, 150)]  # 50% overlap
        
        key_func = lambda x: x
        
        matches = EfficientMatcher.hash_partition_match(
            source, target, key_func, num_partitions=5
        )
        
        # Should find 50 matches (protein_50 to protein_99)
        assert len(matches) == 50
        
        match_sources = {m.source_item for m in matches}
        expected_sources = {f"protein_{i}" for i in range(50, 100)}
        assert match_sources == expected_sources
    
    def test_hash_partition_match_biological_objects(self):
        """Test hash partition matching with biological objects."""
        source_proteins = [
            {"id": "P12345", "gene": "TP53"},
            {"id": "Q9Y6R4", "gene": "BRCA1"},
            {"id": "O15552", "gene": "TEKT4"}
        ]
        
        target_proteins = [
            {"id": "P12345", "pathway": "p53_signaling"},
            {"id": "Q9Y6R4", "pathway": "dna_repair"},
            {"id": "UNKNOWN", "pathway": "unknown"}
        ]
        
        matches = EfficientMatcher.hash_partition_match(
            source_proteins, target_proteins, 
            lambda x: x["id"], 
            num_partitions=3
        )
        
        assert len(matches) == 2
        
        # Check that correct proteins matched
        match_ids = {m.source_item["id"] for m in matches}
        assert match_ids == {"P12345", "Q9Y6R4"}


class TestEfficientMatcherPerformance:
    """Test performance-related functionality."""
    
    def test_chunked_processing(self):
        """Test chunked processing for memory efficiency."""
        large_dataset = list(range(10000))
        
        def process_chunk(chunk):
            return [x * 2 for x in chunk]
        
        results = EfficientMatcher.chunked_processing(
            large_dataset, process_chunk, chunk_size=1000
        )
        
        assert len(results) == 10000
        assert results[0] == 0
        assert results[100] == 200
        assert results[9999] == 19998
    
    def test_chunked_processing_biological_data(self):
        """Test chunked processing with biological data."""
        protein_ids = [f"P{str(i).zfill(5)}" for i in range(5000)]
        
        def normalize_proteins(chunk):
            return [{"original": pid, "normalized": pid.upper()} for pid in chunk]
        
        results = EfficientMatcher.chunked_processing(
            protein_ids, normalize_proteins, chunk_size=500
        )
        
        assert len(results) == 5000
        assert results[0]["original"] == "P00000"
        assert results[0]["normalized"] == "P00000"
        assert results[4999]["original"] == "P04999"
    
    def test_estimate_performance_nested_loop(self):
        """Test performance estimation for nested loop."""
        estimate = EfficientMatcher.estimate_performance(
            n_source=1000, n_target=1000, algorithm="nested_loop"
        )
        
        assert estimate["algorithm"] == "nested_loop"
        assert estimate["complexity"] == "O(n*m)"
        assert estimate["operations"] == 1000 * 1000
        assert estimate["recommended"] == False  # Too many operations
    
    def test_estimate_performance_hash_index(self):
        """Test performance estimation for hash index."""
        estimate = EfficientMatcher.estimate_performance(
            n_source=10000, n_target=10000, algorithm="hash_index"
        )
        
        assert estimate["algorithm"] == "hash_index"
        assert estimate["complexity"] == "O(n+m)"
        assert estimate["operations"] == 20000
        assert estimate["recommended"] == True
    
    def test_estimate_performance_sorted_merge(self):
        """Test performance estimation for sorted merge."""
        estimate = EfficientMatcher.estimate_performance(
            n_source=100000, n_target=100000, algorithm="sorted_merge"
        )
        
        assert estimate["algorithm"] == "sorted_merge"
        assert estimate["complexity"] == "O(n log n + m log m)"
        assert estimate["recommended"] == True
    
    def test_estimate_performance_set_intersection(self):
        """Test performance estimation for set intersection."""
        estimate = EfficientMatcher.estimate_performance(
            n_source=50000, n_target=50000, algorithm="set_intersection"
        )
        
        assert estimate["algorithm"] == "set_intersection"
        assert estimate["complexity"] == "O(n+m)"
        assert estimate["memory"] == "O(n+m)"
        assert estimate["recommended"] == True
    
    def test_estimate_performance_unknown_algorithm(self):
        """Test performance estimation for unknown algorithm."""
        estimate = EfficientMatcher.estimate_performance(
            n_source=1000, n_target=1000, algorithm="unknown_algo"
        )
        
        assert "error" in estimate
        assert "Unknown algorithm" in estimate["error"]
    
    @pytest.mark.performance
    def test_large_dataset_matching_performance(self):
        """Test performance with large biological datasets."""
        # Create large protein dataset
        large_source = [f"P{str(i).zfill(5)}" for i in range(10000)]
        large_target = [f"P{str(i).zfill(5)}" for i in range(5000, 15000)]  # 50% overlap
        
        # Test hash index approach
        start_time = time.time()
        target_index = EfficientMatcher.build_index(large_target, lambda x: x)
        matches = EfficientMatcher.match_with_index(large_source, target_index, lambda x: x)
        end_time = time.time()
        
        # Should complete quickly (< 1 second for this size)
        assert end_time - start_time < 1.0
        assert len(matches) == 5000  # P05000 to P09999
    
    @pytest.mark.performance
    def test_dataframe_merge_performance(self):
        """Test DataFrame merge performance with biological data."""
        # Create large DataFrames
        df1 = pd.DataFrame({
            "uniprot_id": [f"P{str(i).zfill(5)}" for i in range(10000)],
            "gene_name": [f"GENE_{i}" for i in range(10000)],
            "score": np.random.rand(10000)
        })
        
        df2 = pd.DataFrame({
            "protein_id": [f"P{str(i).zfill(5)}" for i in range(5000, 15000)],
            "pathway": [f"PATHWAY_{i}" for i in range(5000, 15000)],
            "confidence": np.random.rand(10000)
        })
        
        start_time = time.time()
        result = EfficientMatcher.dataframe_index_merge(
            df1, df2, "uniprot_id", "protein_id", how="inner"
        )
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 2.0
        assert len(result) == 5000
    
    @pytest.mark.performance
    def test_set_operations_performance(self):
        """Test set operations performance."""
        # Large sets of biological identifiers
        uniprot_ids = {f"P{str(i).zfill(5)}" for i in range(50000)}
        ensembl_ids = {f"P{str(i).zfill(5)}" for i in range(25000, 75000)}
        
        start_time = time.time()
        matched, uniprot_only, ensembl_only = EfficientMatcher.set_intersection_match(
            list(uniprot_ids), list(ensembl_ids)
        )
        end_time = time.time()
        
        # Set operations should be very fast
        assert end_time - start_time < 0.5
        assert len(matched) == 25000  # P25000 to P49999
        assert len(uniprot_only) == 25000  # P00000 to P24999
        assert len(ensembl_only) == 25000  # P50000 to P74999


class TestEfficientMatcherEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_datasets(self):
        """Test matching with empty datasets."""
        # Empty source
        target_index = EfficientMatcher.build_index(["P12345"], lambda x: x)
        matches = EfficientMatcher.match_with_index([], target_index, lambda x: x)
        assert matches == []
        
        # Empty target
        source_index = EfficientMatcher.build_index([], lambda x: x)
        matches = EfficientMatcher.match_with_index(["P12345"], source_index, lambda x: x)
        assert matches == []
        
        # Both empty
        empty_index = EfficientMatcher.build_index([], lambda x: x)
        matches = EfficientMatcher.match_with_index([], empty_index, lambda x: x)
        assert matches == []
    
    def test_none_values_in_data(self):
        """Test handling of None values."""
        source = ["P12345", None, "Q9Y6R4"]
        target = [None, "P12345", "UNKNOWN"]
        
        # Key function that handles None
        key_func = lambda x: x if x is not None else ""
        
        target_index = EfficientMatcher.build_index(target, key_func)
        matches = EfficientMatcher.match_with_index(source, target_index, key_func)
        
        # Should only match non-None values
        assert len(matches) == 1
        assert matches[0].source_item == "P12345"
        assert matches[0].target_item == "P12345"
    
    def test_complex_key_extraction_failures(self):
        """Test handling of key extraction failures."""
        mixed_data = [
            {"id": "P12345"},
            {"different_key": "value"},
            "string_item",
            None,
            {"id": "Q9Y6R4"}
        ]
        
        def safe_key_func(item):
            try:
                if isinstance(item, dict):
                    return item.get("id", "")
                elif isinstance(item, str):
                    return item
                else:
                    return ""
            except:
                return ""
        
        index = EfficientMatcher.build_index(mixed_data, safe_key_func)
        
        # Should only index items with valid keys
        assert "P12345" in index
        assert "Q9Y6R4" in index
        assert "string_item" in index
        assert len(index) == 3
    
    def test_very_large_objects(self):
        """Test handling of very large objects."""
        # Create objects with large metadata
        large_objects = []
        for i in range(100):
            obj = {
                "id": f"P{str(i).zfill(5)}",
                "metadata": {
                    "interactions": [f"interaction_{j}" for j in range(1000)],
                    "pathways": [f"pathway_{j}" for j in range(100)],
                    "publications": [f"PMID:{j}" for j in range(500)]
                }
            }
            large_objects.append(obj)
        
        # Should handle large objects efficiently
        index = EfficientMatcher.build_index(large_objects, lambda x: x["id"])
        
        assert len(index) == 100
        assert "P00000" in index
        assert len(index["P00000"][0]["metadata"]["interactions"]) == 1000
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        biological_names = [
            {"id": "α-synuclein", "type": "protein"},
            {"id": "β-alanine", "type": "metabolite"},
            {"id": "γ-aminobutyric acid", "type": "metabolite"},
            {"id": "protein/complex-1", "type": "complex"},
            {"id": "metabolite [isomer]", "type": "metabolite"}
        ]
        
        index = EfficientMatcher.build_index(biological_names, lambda x: x["id"])
        
        assert "α-synuclein" in index
        assert "β-alanine" in index
        assert "γ-aminobutyric acid" in index
        assert "protein/complex-1" in index
        assert "metabolite [isomer]" in index
    
    def test_case_sensitivity_handling(self):
        """Test case sensitivity in matching."""
        source = ["P12345", "Q9Y6R4", "O15552"]
        target = ["p12345", "Q9Y6R4", "o15552"]
        
        # Case-sensitive matching
        target_index = EfficientMatcher.build_index(target, lambda x: x)
        matches_case_sensitive = EfficientMatcher.match_with_index(source, target_index, lambda x: x)
        assert len(matches_case_sensitive) == 1  # Only Q9Y6R4 matches
        
        # Case-insensitive matching
        target_index_lower = EfficientMatcher.build_index(target, lambda x: x.lower())
        matches_case_insensitive = EfficientMatcher.match_with_index(
            source, target_index_lower, lambda x: x.lower()
        )
        assert len(matches_case_insensitive) == 3  # All should match


class TestBiologicalDataIntegration:
    """Test integration with realistic biological data patterns."""
    
    def test_protein_identifier_mapping(self):
        """Test protein identifier cross-referencing."""
        uniprot_proteins = [
            {"uniprot_id": "P12345", "gene_name": "TP53", "organism": "human"},
            {"uniprot_id": "Q9Y6R4", "gene_name": "BRCA1", "organism": "human"},
            {"uniprot_id": "O15552", "gene_name": "TEKT4", "organism": "human"}
        ]
        
        ensembl_proteins = [
            {"ensembl_id": "ENSP00000269305", "gene_name": "TP53", "chromosome": "17"},
            {"ensembl_id": "ENSP00000350283", "gene_name": "BRCA1", "chromosome": "17"},
            {"ensembl_id": "ENSP00000123456", "gene_name": "UNKNOWN", "chromosome": "X"}
        ]
        
        # Match by gene name
        ensembl_index = EfficientMatcher.build_index(ensembl_proteins, lambda x: x["gene_name"])
        matches = EfficientMatcher.match_with_index(
            uniprot_proteins, ensembl_index, lambda x: x["gene_name"]
        )
        
        assert len(matches) == 2  # TP53 and BRCA1
        
        # Verify correct matches
        tp53_match = next(m for m in matches if m.source_item["gene_name"] == "TP53")
        assert tp53_match.source_item["uniprot_id"] == "P12345"
        assert tp53_match.target_item["ensembl_id"] == "ENSP00000269305"
        assert tp53_match.target_item["chromosome"] == "17"
    
    def test_metabolite_pathway_mapping(self):
        """Test metabolite to pathway mapping."""
        metabolites = [
            {"hmdb_id": "HMDB0000001", "name": "1-Methylhistidine", "class": "amino_acid"},
            {"hmdb_id": "HMDB0000123", "name": "Acetylcarnitine", "class": "lipid"},
            {"hmdb_id": "HMDB0006456", "name": "Unknown_compound", "class": "unknown"}
        ]
        
        pathways = [
            {"compound_name": "1-Methylhistidine", "pathway": "histidine_metabolism", "kegg_id": "C02178"},
            {"compound_name": "Acetylcarnitine", "pathway": "fatty_acid_oxidation", "kegg_id": "C02990"},
            {"compound_name": "L-Alanine", "pathway": "alanine_metabolism", "kegg_id": "C00041"}
        ]
        
        # Match by compound name
        pathway_index = EfficientMatcher.build_index(pathways, lambda x: x["compound_name"])
        matches = EfficientMatcher.match_with_index(
            metabolites, pathway_index, lambda x: x["name"]
        )
        
        assert len(matches) == 2
        
        # Check histidine match
        histidine_match = next(m for m in matches if m.source_item["hmdb_id"] == "HMDB0000001")
        assert histidine_match.target_item["pathway"] == "histidine_metabolism"
        assert histidine_match.target_item["kegg_id"] == "C02178"
    
    def test_multi_omics_integration_workflow(self):
        """Test comprehensive multi-omics data integration."""
        # Protein data
        proteins = [
            {"uniprot_id": "P12345", "gene_symbol": "TP53", "expression": 2.5},
            {"uniprot_id": "Q9Y6R4", "gene_symbol": "BRCA1", "expression": 1.8}
        ]
        
        # Metabolite data
        metabolites = [
            {"hmdb_id": "HMDB0000001", "compound": "1-Methylhistidine", "concentration": 0.5},
            {"hmdb_id": "HMDB0000123", "compound": "Acetylcarnitine", "concentration": 1.2}
        ]
        
        # Pathway connections
        protein_pathways = [
            {"gene_symbol": "TP53", "pathway": "p53_signaling", "role": "regulator"},
            {"gene_symbol": "BRCA1", "pathway": "dna_repair", "role": "enzyme"}
        ]
        
        metabolite_pathways = [
            {"compound": "1-Methylhistidine", "pathway": "amino_acid_metabolism", "flux": "high"},
            {"compound": "Acetylcarnitine", "pathway": "lipid_metabolism", "flux": "medium"}
        ]
        
        # Build integrated network
        protein_pathway_index = EfficientMatcher.build_index(protein_pathways, lambda x: x["gene_symbol"])
        metabolite_pathway_index = EfficientMatcher.build_index(metabolite_pathways, lambda x: x["compound"])
        
        # Map proteins to pathways
        protein_matches = EfficientMatcher.match_with_index(
            proteins, protein_pathway_index, lambda x: x["gene_symbol"]
        )
        
        # Map metabolites to pathways
        metabolite_matches = EfficientMatcher.match_with_index(
            metabolites, metabolite_pathway_index, lambda x: x["compound"]
        )
        
        assert len(protein_matches) == 2
        assert len(metabolite_matches) == 2
        
        # Verify integrated data
        tp53_match = next(m for m in protein_matches if m.source_item["uniprot_id"] == "P12345")
        assert tp53_match.target_item["pathway"] == "p53_signaling"
        assert tp53_match.source_item["expression"] == 2.5
        
        histidine_match = next(m for m in metabolite_matches if m.source_item["hmdb_id"] == "HMDB0000001")
        assert histidine_match.target_item["pathway"] == "amino_acid_metabolism"
        assert histidine_match.source_item["concentration"] == 0.5
    
    def test_cross_species_ortholog_mapping(self):
        """Test cross-species protein ortholog mapping."""
        human_proteins = [
            {"uniprot_id": "P12345", "gene": "TP53", "species": "human"},
            {"uniprot_id": "Q9Y6R4", "gene": "BRCA1", "species": "human"}
        ]
        
        mouse_proteins = [
            {"uniprot_id": "P02340", "gene": "Tp53", "species": "mouse", "ortholog_human": "TP53"},
            {"uniprot_id": "P97929", "gene": "Brca1", "species": "mouse", "ortholog_human": "BRCA1"},
            {"uniprot_id": "Q61735", "gene": "Mstn", "species": "mouse", "ortholog_human": "MSTN"}
        ]
        
        # Map by ortholog relationship
        mouse_index = EfficientMatcher.build_index(mouse_proteins, lambda x: x["ortholog_human"])
        matches = EfficientMatcher.match_with_index(
            human_proteins, mouse_index, lambda x: x["gene"]
        )
        
        assert len(matches) == 2
        
        # Verify TP53 ortholog mapping
        tp53_match = next(m for m in matches if m.source_item["gene"] == "TP53")
        assert tp53_match.target_item["gene"] == "Tp53"
        assert tp53_match.target_item["species"] == "mouse"
        assert tp53_match.target_item["uniprot_id"] == "P02340"