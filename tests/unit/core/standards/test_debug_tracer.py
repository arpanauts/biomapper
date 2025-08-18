"""Tests for debug tracer standards component."""

import pytest
import tempfile
import threading
import time
import json
from pathlib import Path

from src.core.standards.debug_tracer import DebugTracer, ActionDebugMixin


class TestDebugTracer:
    """Test DebugTracer functionality."""
    
    @pytest.fixture
    def sample_biological_identifiers(self):
        """Create sample biological identifiers for testing."""
        return {
            "uniprot_ids": ["P12345", "Q9Y6R4", "O00533", "Q6EMK4"],
            "hmdb_ids": ["HMDB0000001", "HMDB0123456"],
            "gene_symbols": ["TP53", "BRCA1", "CD4"],
            "edge_case_ids": ["Q6EMK4"],  # Known problematic identifier
            "invalid_ids": ["", None, "INVALID_FORMAT"]
        }
    
    @pytest.fixture
    def tracer_with_identifiers(self, sample_biological_identifiers):
        """Create tracer with sample biological identifiers."""
        return DebugTracer(trace_identifiers={"Q6EMK4", "P12345"})
    
    @pytest.fixture
    def empty_tracer(self):
        """Create empty tracer for testing."""
        return DebugTracer()

    def test_debug_tracer_initialization(self, sample_biological_identifiers):
        """Test DebugTracer initialization."""
        # Test with identifiers
        tracer = DebugTracer(trace_identifiers={"P12345", "Q9Y6R4"})
        assert tracer.trace_identifiers == {"P12345", "Q9Y6R4"}
        assert tracer.enabled is True
        assert len(tracer.trace_log) == 0
        
        # Test without identifiers
        empty_tracer = DebugTracer()
        assert len(empty_tracer.trace_identifiers) == 0
        assert empty_tracer.enabled is False
        
        # Test with None
        none_tracer = DebugTracer(None)
        assert len(none_tracer.trace_identifiers) == 0
        assert none_tracer.enabled is False

    def test_add_identifier_functionality(self, empty_tracer):
        """Test adding identifiers to tracer."""
        assert empty_tracer.enabled is False
        
        # Add identifier
        empty_tracer.add_identifier("Q6EMK4")
        assert "Q6EMK4" in empty_tracer.trace_identifiers
        assert empty_tracer.enabled is True
        
        # Add another identifier
        empty_tracer.add_identifier("P12345")
        assert "P12345" in empty_tracer.trace_identifiers
        assert len(empty_tracer.trace_identifiers) == 2

    def test_should_trace_functionality(self, tracer_with_identifiers):
        """Test should_trace method."""
        # Test with exact match
        assert tracer_with_identifiers.should_trace("Q6EMK4") is True
        assert tracer_with_identifiers.should_trace("P12345") is True
        
        # Test with substring match
        assert tracer_with_identifiers.should_trace("UniProt:Q6EMK4") is True
        assert tracer_with_identifiers.should_trace("protein_P12345_data") is True
        
        # Test with no match
        assert tracer_with_identifiers.should_trace("Q9Y6R4") is False
        assert tracer_with_identifiers.should_trace("unrelated_data") is False
        
        # Test with disabled tracer
        disabled_tracer = DebugTracer()
        assert disabled_tracer.should_trace("Q6EMK4") is False

    def test_trace_functionality(self, tracer_with_identifiers):
        """Test trace method."""
        # Add trace entry
        tracer_with_identifiers.trace(
            identifier="Q6EMK4",
            action="PROTEIN_MAPPING",
            phase="input_validation",
            details={"status": "found", "dataset": "arivale_proteins"}
        )
        
        assert len(tracer_with_identifiers.trace_log) == 1
        
        entry = tracer_with_identifiers.trace_log[0]
        assert entry["identifier"] == "Q6EMK4"
        assert entry["action"] == "PROTEIN_MAPPING"
        assert entry["phase"] == "input_validation"
        assert entry["details"]["status"] == "found"
        assert "timestamp" in entry
        
        # Add another trace entry
        tracer_with_identifiers.trace(
            identifier="Q6EMK4",
            action="PROTEIN_MAPPING",
            phase="cross_reference_lookup",
            details={"xrefs_found": 3, "kg2c_match": False}
        )
        
        assert len(tracer_with_identifiers.trace_log) == 2

    def test_trace_non_tracked_identifier(self, tracer_with_identifiers):
        """Test tracing non-tracked identifier (should be ignored)."""
        initial_log_size = len(tracer_with_identifiers.trace_log)
        
        # Try to trace non-tracked identifier
        tracer_with_identifiers.trace(
            identifier="Q9Y6R4",  # Not in trace_identifiers
            action="PROTEIN_MAPPING",
            phase="test_phase",
            details={"test": "data"}
        )
        
        # Log should not increase
        assert len(tracer_with_identifiers.trace_log) == initial_log_size

    def test_save_trace_functionality(self, tracer_with_identifiers):
        """Test saving trace log to file."""
        # Add some trace entries
        tracer_with_identifiers.trace(
            "Q6EMK4", "ACTION1", "phase1", {"detail1": "value1"}
        )
        tracer_with_identifiers.trace(
            "P12345", "ACTION2", "phase2", {"detail2": "value2"}
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Save trace
            tracer_with_identifiers.save_trace(tmp_path)
            
            # Verify file exists and contains correct data
            assert Path(tmp_path).exists()
            
            with open(tmp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert len(saved_data) == 2
            assert saved_data[0]["identifier"] == "Q6EMK4"
            assert saved_data[1]["identifier"] == "P12345"
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_save_trace_creates_directories(self, tracer_with_identifiers):
        """Test that save_trace creates parent directories."""
        tracer_with_identifiers.trace(
            "Q6EMK4", "TEST_ACTION", "test_phase", {"test": "data"}
        )
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_path = Path(tmp_dir) / "subdir" / "trace.json"
            
            # Directory doesn't exist yet
            assert not nested_path.parent.exists()
            
            # Save trace (should create directory)
            tracer_with_identifiers.save_trace(str(nested_path))
            
            # Verify directory was created and file exists
            assert nested_path.parent.exists()
            assert nested_path.exists()

    def test_get_identifier_journey_functionality(self, tracer_with_identifiers):
        """Test getting identifier journey."""
        # Add traces for different identifiers
        tracer_with_identifiers.trace("Q6EMK4", "ACTION1", "phase1", {"step": 1})
        tracer_with_identifiers.trace("P12345", "ACTION1", "phase1", {"step": 1})
        tracer_with_identifiers.trace("Q6EMK4", "ACTION1", "phase2", {"step": 2})
        tracer_with_identifiers.trace("Q6EMK4", "ACTION2", "phase1", {"step": 3})
        
        # Get journey for Q6EMK4
        q6emk4_journey = tracer_with_identifiers.get_identifier_journey("Q6EMK4")
        assert len(q6emk4_journey) == 3
        assert all(entry["identifier"] == "Q6EMK4" for entry in q6emk4_journey)
        
        # Verify chronological order
        assert q6emk4_journey[0]["details"]["step"] == 1
        assert q6emk4_journey[1]["details"]["step"] == 2
        assert q6emk4_journey[2]["details"]["step"] == 3
        
        # Get journey for P12345
        p12345_journey = tracer_with_identifiers.get_identifier_journey("P12345")
        assert len(p12345_journey) == 1
        assert p12345_journey[0]["identifier"] == "P12345"
        
        # Get journey for non-existent identifier
        empty_journey = tracer_with_identifiers.get_identifier_journey("NONEXISTENT")
        assert len(empty_journey) == 0

    def test_debug_tracer_performance(self):
        """Test DebugTracer performance with large datasets."""
        # Create tracer with many identifiers
        large_identifier_set = {f"P{i:05d}" for i in range(1000)}
        tracer = DebugTracer(trace_identifiers=large_identifier_set)
        
        start_time = time.time()
        
        # Test should_trace performance
        for i in range(1000):
            tracer.should_trace(f"P{i:05d}")
            tracer.should_trace(f"Q{i:05d}")  # Non-matching
        
        # Add many trace entries
        for i in range(100):
            tracer.trace(
                f"P{i:05d}",
                "PERFORMANCE_TEST",
                "trace_phase",
                {"iteration": i, "data": f"test_data_{i}"}
            )
        
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete quickly
        assert len(tracer.trace_log) == 100

    def test_debug_tracer_thread_safety(self, tracer_with_identifiers):
        """Test DebugTracer thread safety."""
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(50):
                    # Each thread traces with thread-specific data
                    tracer_with_identifiers.trace(
                        "Q6EMK4",
                        f"THREAD_ACTION_{thread_id}",
                        f"phase_{i}",
                        {"thread_id": thread_id, "iteration": i}
                    )
                results.append(thread_id)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 5
        
        # Verify all traces were recorded
        q6emk4_journey = tracer_with_identifiers.get_identifier_journey("Q6EMK4")
        assert len(q6emk4_journey) == 250  # 5 threads * 50 iterations


class TestActionDebugMixin:
    """Test ActionDebugMixin functionality."""
    
    @pytest.fixture
    def action_with_debug(self):
        """Create action class with debug mixin."""
        class TestAction(ActionDebugMixin):
            def __init__(self):
                super().__init__()
                self.action_name = "TEST_ACTION"
        
        return TestAction()

    def test_action_debug_mixin_initialization(self, action_with_debug):
        """Test ActionDebugMixin initialization."""
        assert hasattr(action_with_debug, "tracer")
        assert action_with_debug.tracer is None
        assert hasattr(action_with_debug, "action_name")

    def test_setup_tracing_functionality(self, action_with_debug):
        """Test setup_tracing method."""
        identifiers = {"Q6EMK4", "P12345"}
        action_with_debug.setup_tracing(identifiers)
        
        assert action_with_debug.tracer is not None
        assert isinstance(action_with_debug.tracer, DebugTracer)
        assert action_with_debug.tracer.trace_identifiers == identifiers
        assert action_with_debug.tracer.enabled is True

    def test_trace_if_relevant_functionality(self, action_with_debug):
        """Test trace_if_relevant method."""
        # Setup tracing
        action_with_debug.setup_tracing({"Q6EMK4", "P12345"})
        
        # Test with relevant value
        action_with_debug.trace_if_relevant(
            value="Processing Q6EMK4 from dataset",
            action="TEST_ACTION",
            phase="processing",
            dataset="arivale_proteins",
            status="in_progress"
        )
        
        # Should have created trace entry
        journey = action_with_debug.tracer.get_identifier_journey("Q6EMK4")
        assert len(journey) == 1
        assert journey[0]["action"] == "TEST_ACTION"
        assert journey[0]["phase"] == "processing"
        assert journey[0]["details"]["dataset"] == "arivale_proteins"
        
        # Test with non-relevant value
        action_with_debug.trace_if_relevant(
            value="Processing Q9Y6R4 from dataset",  # Not tracked
            action="TEST_ACTION",
            phase="processing"
        )
        
        # Should not have added new trace entry
        all_traces = action_with_debug.tracer.trace_log
        assert len(all_traces) == 1

    def test_trace_if_relevant_no_tracer(self, action_with_debug):
        """Test trace_if_relevant with no tracer (should not crash)."""
        # Don't setup tracing
        assert action_with_debug.tracer is None
        
        # Should not crash
        action_with_debug.trace_if_relevant(
            value="Q6EMK4",
            action="TEST_ACTION",
            phase="test"
        )

    def test_multiple_identifier_detection(self, action_with_debug):
        """Test tracing when value contains multiple identifiers."""
        action_with_debug.setup_tracing({"Q6EMK4", "P12345", "O00533"})
        
        # Value contains multiple tracked identifiers
        complex_value = "Processing proteins: Q6EMK4, P12345, and Q9Y6R4 from Arivale dataset"
        
        action_with_debug.trace_if_relevant(
            value=complex_value,
            action="MULTI_PROTEIN_PROCESSING",
            phase="batch_processing",
            protein_count=3
        )
        
        # Should trace for each relevant identifier found
        q6emk4_journey = action_with_debug.tracer.get_identifier_journey("Q6EMK4")
        p12345_journey = action_with_debug.tracer.get_identifier_journey("P12345")
        
        assert len(q6emk4_journey) >= 1
        assert len(p12345_journey) >= 1


class TestPerformanceDebugTracer:
    """Performance tests for DebugTracer."""
    
    @pytest.mark.performance
    def test_large_scale_tracing_performance(self):
        """Test performance with large-scale tracing."""
        # Create tracer with many biological identifiers
        large_protein_set = {f"P{i:05d}" for i in range(5000)}
        large_metabolite_set = {f"HMDB{i:07d}" for i in range(2000)}
        all_identifiers = large_protein_set | large_metabolite_set
        
        tracer = DebugTracer(trace_identifiers=all_identifiers)
        
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        # Simulate realistic tracing scenario
        actions = ["LOAD_DATA", "VALIDATE_IDS", "MAP_IDENTIFIERS", "EXPORT_RESULTS"]
        phases = ["start", "processing", "validation", "completion"]
        
        trace_count = 0
        for action in actions:
            for phase in phases:
                for i in range(100):  # 100 identifiers per phase
                    identifier = f"P{i:05d}"
                    tracer.trace(
                        identifier=identifier,
                        action=action,
                        phase=phase,
                        details={
                            "iteration": i,
                            "dataset_size": 10000,
                            "memory_usage": f"{50 + i}MB"
                        }
                    )
                    trace_count += 1
        
        memory_after = self._get_memory_usage()
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 5.0  # Should complete in reasonable time
        assert (memory_after - memory_before) < 100 * 1024 * 1024  # < 100MB memory increase
        assert len(tracer.trace_log) == trace_count
        
        # Test journey retrieval performance
        start_time = time.time()
        journey = tracer.get_identifier_journey("P00010")
        journey_time = time.time() - start_time
        
        assert journey_time < 0.1  # Journey retrieval should be fast
        assert len(journey) == len(actions) * len(phases)  # Should find all traces

    def _get_memory_usage(self):
        """Get current memory usage."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0  # Skip memory check if psutil not available


class TestBiologicalTracingPatterns:
    """Test with realistic biological tracing patterns."""
    
    @pytest.fixture
    def protein_mapping_tracer(self):
        """Tracer configured for protein mapping scenarios."""
        # Include known edge cases
        edge_case_proteins = {"Q6EMK4", "P12345", "Q9Y6R4"}
        return DebugTracer(trace_identifiers=edge_case_proteins)
    
    @pytest.fixture
    def metabolite_analysis_tracer(self):
        """Tracer configured for metabolite analysis scenarios."""
        problematic_metabolites = {"HMDB0000001", "HMDB0123456"}
        return DebugTracer(trace_identifiers=problematic_metabolites)

    def test_protein_mapping_tracing_scenario(self, protein_mapping_tracer):
        """Test realistic protein mapping tracing scenario."""
        # Simulate Q6EMK4 edge case journey
        tracer = protein_mapping_tracer
        
        # Step 1: Input validation
        tracer.trace(
            "Q6EMK4",
            "LOAD_DATASET_IDENTIFIERS",
            "input_validation",
            {
                "source_dataset": "arivale_proteins",
                "format": "tsv",
                "total_proteins": 1247,
                "status": "found"
            }
        )
        
        # Step 2: Cross-reference lookup
        tracer.trace(
            "Q6EMK4",
            "MERGE_WITH_UNIPROT_RESOLUTION",
            "xref_lookup",
            {
                "xrefs_found": ["NCBIGene:114990", "HGNC:OTUD5"],
                "kg2c_match": False,
                "manual_mapping_required": True
            }
        )
        
        # Step 3: Manual resolution attempt
        tracer.trace(
            "Q6EMK4",
            "MERGE_WITH_UNIPROT_RESOLUTION",
            "manual_resolution",
            {
                "manual_mapping": "Q6EMK4 -> NCBIGene:114990 (OTUD5)",
                "confidence": 0.95,
                "verification_needed": True
            }
        )
        
        # Step 4: Final classification
        tracer.trace(
            "Q6EMK4",
            "CALCULATE_SET_OVERLAP",
            "final_classification",
            {
                "classification": "source_only",
                "reason": "no_direct_kg2c_match",
                "edge_case": True
            }
        )
        
        # Verify complete journey
        journey = tracer.get_identifier_journey("Q6EMK4")
        assert len(journey) == 4
        
        # Verify journey progression
        phases = [entry["phase"] for entry in journey]
        expected_phases = ["input_validation", "xref_lookup", "manual_resolution", "final_classification"]
        assert phases == expected_phases
        
        # Verify edge case information captured
        final_entry = journey[-1]
        assert final_entry["details"]["edge_case"] is True
        assert final_entry["details"]["classification"] == "source_only"

    def test_metabolite_semantic_matching_tracing(self, metabolite_analysis_tracer):
        """Test metabolite semantic matching tracing scenario."""
        tracer = metabolite_analysis_tracer
        
        # Step 1: Input processing
        tracer.trace(
            "HMDB0000001",
            "SEMANTIC_METABOLITE_MATCH",
            "input_processing",
            {
                "input_name": "1-Methylhistidine",
                "hmdb_canonical": "HMDB0000001",
                "synonyms_found": 3
            }
        )
        
        # Step 2: Vector embedding
        tracer.trace(
            "HMDB0000001",
            "SEMANTIC_METABOLITE_MATCH",
            "vector_embedding",
            {
                "embedding_model": "sentence-transformers",
                "vector_dim": 384,
                "embedding_time_ms": 45
            }
        )
        
        # Step 3: Similarity search
        tracer.trace(
            "HMDB0000001",
            "SEMANTIC_METABOLITE_MATCH",
            "similarity_search",
            {
                "top_matches": 5,
                "best_score": 0.98,
                "search_time_ms": 120,
                "qdrant_collection": "hmdb_metabolites"
            }
        )
        
        # Step 4: Confidence calculation
        tracer.trace(
            "HMDB0000001",
            "SEMANTIC_METABOLITE_MATCH",
            "confidence_calculation",
            {
                "final_confidence": 0.95,
                "factors": {
                    "name_similarity": 0.98,
                    "chemical_similarity": 0.92,
                    "pathway_consistency": 0.95
                }
            }
        )
        
        # Verify complete metabolite journey
        journey = tracer.get_identifier_journey("HMDB0000001")
        assert len(journey) == 4
        
        # Verify semantic matching progression
        actions = [entry["action"] for entry in journey]
        assert all(action == "SEMANTIC_METABOLITE_MATCH" for action in actions)
        
        # Verify confidence progression
        final_confidence = journey[-1]["details"]["final_confidence"]
        assert final_confidence == 0.95

    def test_multi_action_biological_pipeline_tracing(self):
        """Test tracing across multiple actions in biological pipeline."""
        # Create tracer for comprehensive pipeline
        pipeline_identifiers = {"P12345", "HMDB0000001", "ENSG00000141510"}
        tracer = DebugTracer(trace_identifiers=pipeline_identifiers)
        
        # Action 1: Data loading
        tracer.trace("P12345", "LOAD_DATASET_IDENTIFIERS", "protein_loading", 
                    {"dataset": "arivale", "count": 1247})
        tracer.trace("HMDB0000001", "LOAD_DATASET_IDENTIFIERS", "metabolite_loading", 
                    {"dataset": "user_metabolites", "count": 89})
        
        # Action 2: ID normalization
        tracer.trace("P12345", "PROTEIN_NORMALIZE_ACCESSIONS", "normalization", 
                    {"input": "UniProtKB:P12345", "output": "P12345"})
        
        # Action 3: Cross-mapping
        tracer.trace("P12345", "MULTI_BRIDGE_MAPPING", "protein_gene_mapping", 
                    {"gene_id": "ENSG00000141510", "confidence": 0.99})
        tracer.trace("ENSG00000141510", "MULTI_BRIDGE_MAPPING", "gene_protein_mapping", 
                    {"protein_id": "P12345", "confidence": 0.99})
        
        # Action 4: Pathway integration
        tracer.trace("P12345", "PATHWAY_INTEGRATION", "protein_pathway_mapping", 
                    {"pathways": ["glycolysis", "gluconeogenesis"]})
        tracer.trace("HMDB0000001", "PATHWAY_INTEGRATION", "metabolite_pathway_mapping", 
                    {"pathways": ["amino_acid_metabolism"]})
        
        # Verify cross-omics integration
        protein_journey = tracer.get_identifier_journey("P12345")
        metabolite_journey = tracer.get_identifier_journey("HMDB0000001")
        gene_journey = tracer.get_identifier_journey("ENSG00000141510")
        
        assert len(protein_journey) == 4
        assert len(metabolite_journey) == 2
        assert len(gene_journey) == 1
        
        # Verify pathway integration captured
        protein_pathway_entry = next(
            entry for entry in protein_journey 
            if entry["action"] == "PATHWAY_INTEGRATION"
        )
        assert "glycolysis" in protein_pathway_entry["details"]["pathways"]

    def test_edge_case_investigation_tracing(self):
        """Test tracing for edge case investigation scenarios."""
        # Focus on Q6EMK4 edge case
        edge_case_tracer = DebugTracer(trace_identifiers={"Q6EMK4"})
        
        # Investigation step 1: Initial detection
        edge_case_tracer.trace(
            "Q6EMK4",
            "EDGE_CASE_INVESTIGATION",
            "initial_detection",
            {
                "issue": "shows_as_source_only_despite_kg2c_xrefs",
                "datasets": ["arivale_proteins", "kg2c_proteins"],
                "expected_outcome": "matched",
                "actual_outcome": "source_only"
            }
        )
        
        # Investigation step 2: Cross-reference analysis
        edge_case_tracer.trace(
            "Q6EMK4",
            "EDGE_CASE_INVESTIGATION",
            "xref_analysis",
            {
                "kg2c_xrefs": ["NCBIGene:114990"],
                "gene_symbol": "OTUD5",
                "uniprot_status": "reviewed",
                "mapping_algorithm": "direct_accession_lookup"
            }
        )
        
        # Investigation step 3: Algorithm debugging
        edge_case_tracer.trace(
            "Q6EMK4",
            "EDGE_CASE_INVESTIGATION",
            "algorithm_debugging",
            {
                "lookup_method": "exact_string_match",
                "kg2c_format": "different_from_uniprot",
                "normalization_issue": True,
                "potential_fix": "add_normalization_step"
            }
        )
        
        # Investigation step 4: Resolution proposal
        edge_case_tracer.trace(
            "Q6EMK4",
            "EDGE_CASE_INVESTIGATION",
            "resolution_proposal",
            {
                "proposed_fix": "manual_mapping_Q6EMK4_to_NCBIGene_114990",
                "confidence": 0.95,
                "verification_methods": ["literature_review", "uniprot_cross_check"],
                "implementation_priority": "high"
            }
        )
        
        # Verify investigation journey
        investigation_journey = edge_case_tracer.get_identifier_journey("Q6EMK4")
        assert len(investigation_journey) == 4
        
        # Verify investigation phases
        phases = [entry["phase"] for entry in investigation_journey]
        expected_phases = ["initial_detection", "xref_analysis", "algorithm_debugging", "resolution_proposal"]
        assert phases == expected_phases
        
        # Verify resolution information
        resolution_entry = investigation_journey[-1]
        assert resolution_entry["details"]["confidence"] == 0.95
        assert "manual_mapping" in resolution_entry["details"]["proposed_fix"]