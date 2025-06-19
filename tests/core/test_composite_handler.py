"""Unit tests for the composite identifier handler."""

import pytest
import asyncio
from unittest.mock import MagicMock

from biomapper.core.composite_handler import CompositeIdentifierHandler, CompositeMiddleware
from biomapper.db.models import CompositePatternConfig, CompositeProcessingStep


class TestCompositeIdentifierHandler:
    """Test cases for the CompositeIdentifierHandler class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        session = MagicMock()
        
        # Create mock pattern configurations
        gene_pattern = MagicMock(spec=CompositePatternConfig)
        gene_pattern.id = 1
        gene_pattern.name = "Underscore Separated Genes"
        gene_pattern.ontology_type = "GENE_NAME"
        gene_pattern.pattern = r"[A-Za-z0-9]+_[A-Za-z0-9]+"
        gene_pattern.delimiters = "_"
        gene_pattern.mapping_strategy = "first_match"
        gene_pattern.keep_component_type = True
        gene_pattern.priority = 1
        
        uniprot_pattern = MagicMock(spec=CompositePatternConfig)
        uniprot_pattern.id = 2
        uniprot_pattern.name = "Comma Separated UniProt IDs"
        uniprot_pattern.ontology_type = "UNIPROTKB_AC"
        uniprot_pattern.pattern = r"[A-Z][0-9][A-Z0-9]{3}[0-9],([A-Z][0-9][A-Z0-9]{3}[0-9],?)+"
        uniprot_pattern.delimiters = ","
        uniprot_pattern.mapping_strategy = "all_matches"
        uniprot_pattern.keep_component_type = True
        uniprot_pattern.priority = 1
        
        # Configure mock query results
        session.query.return_value.order_by.return_value.all.return_value = [
            gene_pattern, uniprot_pattern
        ]
        
        # Configure mock steps query
        def filter_side_effect(*args, **kwargs):
            query = MagicMock()
            if args[0].left == CompositeProcessingStep.pattern_id:
                if args[0].right == 1:  # Gene pattern steps
                    query.order_by.return_value.all.return_value = [
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=1,
                            step_type="split",
                            parameters='{"delimiter": "_"}',
                            order=1
                        ),
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=1,
                            step_type="clean",
                            parameters='{"strip": true}',
                            order=2
                        )
                    ]
                elif args[0].right == 2:  # UniProt pattern steps
                    query.order_by.return_value.all.return_value = [
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=2,
                            step_type="split",
                            parameters='{"delimiter": ","}',
                            order=1
                        ),
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=2,
                            step_type="clean",
                            parameters='{"strip": true}',
                            order=2
                        )
                    ]
                else:
                    query.order_by.return_value.all.return_value = []
            return query
        
        session.query.return_value.filter.side_effect = filter_side_effect
        
        return session
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_session):
        """Test initialization of the handler with patterns from the database."""
        handler = CompositeIdentifierHandler()
        await handler.initialize(mock_session)
        
        assert handler._initialized
        assert "GENE_NAME" in handler._patterns
        assert "UNIPROTKB_AC" in handler._patterns
        assert len(handler._patterns["GENE_NAME"]) == 1
        assert len(handler._patterns["UNIPROTKB_AC"]) == 1
    
    @pytest.mark.asyncio
    async def test_has_patterns_for_ontology(self, mock_session):
        """Test checking if patterns exist for a specific ontology type."""
        handler = CompositeIdentifierHandler()
        await handler.initialize(mock_session)
        
        assert handler.has_patterns_for_ontology("GENE_NAME")
        assert handler.has_patterns_for_ontology("UNIPROTKB_AC")
        assert not handler.has_patterns_for_ontology("PUBCHEM_ID")
        
        # Test case insensitivity
        assert handler.has_patterns_for_ontology("gene_name")
    
    @pytest.mark.asyncio
    async def test_is_composite(self, mock_session):
        """Test detection of composite identifiers."""
        handler = CompositeIdentifierHandler()
        await handler.initialize(mock_session)
        
        # Test gene name patterns
        assert handler.is_composite("GENE1_GENE2", "GENE_NAME")
        assert handler.is_composite("ABC_DEF", "GENE_NAME")
        assert not handler.is_composite("SINGLEGENE", "GENE_NAME")
        
        # Test UniProt ID patterns
        assert handler.is_composite("P12345,Q67890", "UNIPROTKB_AC")
        assert not handler.is_composite("P12345", "UNIPROTKB_AC")
        
        # Test non-existent ontology type
        assert not handler.is_composite("COMPOUND1,COMPOUND2", "PUBCHEM_ID")
    
    @pytest.mark.asyncio
    async def test_split_composite(self, mock_session):
        """Test splitting composite identifiers into components."""
        handler = CompositeIdentifierHandler()
        await handler.initialize(mock_session)
        
        # Test gene name splitting
        is_composite, components, pattern = handler.split_composite("GENE1_GENE2", "GENE_NAME")
        assert is_composite
        assert components == ["GENE1", "GENE2"]
        assert pattern is not None
        assert pattern.name == "Underscore Separated Genes"
        
        # Test multi-part gene name
        is_composite, components, pattern = handler.split_composite("GENE1_GENE2_GENE3", "GENE_NAME")
        assert is_composite
        assert components == ["GENE1", "GENE2", "GENE3"]
        
        # Test UniProt ID splitting
        is_composite, components, pattern = handler.split_composite("P12345,Q67890", "UNIPROTKB_AC")
        assert is_composite
        assert components == ["P12345", "Q67890"]
        assert pattern is not None
        assert pattern.name == "Comma Separated UniProt IDs"
        
        # Test non-composite
        is_composite, components, pattern = handler.split_composite("SINGLEGENE", "GENE_NAME")
        assert not is_composite
        assert components == ["SINGLEGENE"]
        assert pattern is None


class TestCompositeMiddleware:
    """Test cases for the CompositeMiddleware class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        session = MagicMock()
        
        # Create mock pattern configurations
        gene_pattern = MagicMock(spec=CompositePatternConfig)
        gene_pattern.id = 1
        gene_pattern.name = "Underscore Separated Genes"
        gene_pattern.ontology_type = "GENE_NAME"
        gene_pattern.pattern = r"[A-Za-z0-9]+_[A-Za-z0-9]+"
        gene_pattern.delimiters = "_"
        gene_pattern.mapping_strategy = "first_match"
        gene_pattern.keep_component_type = True
        gene_pattern.priority = 1
        
        uniprot_pattern = MagicMock(spec=CompositePatternConfig)
        uniprot_pattern.id = 2
        uniprot_pattern.name = "Comma Separated UniProt IDs"
        uniprot_pattern.ontology_type = "UNIPROTKB_AC"
        uniprot_pattern.pattern = r"[A-Z][0-9][A-Z0-9]{3}[0-9],([A-Z][0-9][A-Z0-9]{3}[0-9],?)+"
        uniprot_pattern.delimiters = ","
        uniprot_pattern.mapping_strategy = "all_matches"
        uniprot_pattern.keep_component_type = True
        uniprot_pattern.priority = 1
        
        # Configure mock query results
        session.query.return_value.order_by.return_value.all.return_value = [
            gene_pattern, uniprot_pattern
        ]
        
        # Configure mock steps query
        def filter_side_effect(*args, **kwargs):
            query = MagicMock()
            if args[0].left == CompositeProcessingStep.pattern_id:
                if args[0].right == 1:  # Gene pattern steps
                    query.order_by.return_value.all.return_value = [
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=1,
                            step_type="split",
                            parameters='{"delimiter": "_"}',
                            order=1
                        ),
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=1,
                            step_type="clean",
                            parameters='{"strip": true}',
                            order=2
                        )
                    ]
                elif args[0].right == 2:  # UniProt pattern steps
                    query.order_by.return_value.all.return_value = [
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=2,
                            step_type="split",
                            parameters='{"delimiter": ","}',
                            order=1
                        ),
                        MagicMock(
                            spec=CompositeProcessingStep,
                            pattern_id=2,
                            step_type="clean",
                            parameters='{"strip": true}',
                            order=2
                        )
                    ]
                else:
                    query.order_by.return_value.all.return_value = []
            return query
        
        session.query.return_value.filter.side_effect = filter_side_effect
        
        return session
    
    @pytest.fixture
    def handler_and_middleware(self, mock_session):
        """Create and initialize a handler and middleware for testing."""
        handler = CompositeIdentifierHandler()
        asyncio.run(handler.initialize(mock_session))
        middleware = CompositeMiddleware(handler)
        return handler, middleware
    
    @pytest.mark.asyncio
    async def test_preprocess_identifiers(self, handler_and_middleware):
        """Test preprocessing of identifiers to identify and split composites."""
        handler, middleware = handler_and_middleware
        
        # Test with gene names
        identifiers = ["GENE1_GENE2", "SINGLEGENE", "GENE3_GENE4_GENE5"]
        result = await middleware.preprocess_identifiers(identifiers, "GENE_NAME")
        
        assert len(result) == 3
        assert result["GENE1_GENE2"] == [("GENE1", "GENE_NAME"), ("GENE2", "GENE_NAME")]
        assert result["SINGLEGENE"] == [("SINGLEGENE", "GENE_NAME")]
        assert result["GENE3_GENE4_GENE5"] == [
            ("GENE3", "GENE_NAME"), 
            ("GENE4", "GENE_NAME"), 
            ("GENE5", "GENE_NAME")
        ]
        
        # Test with UniProt IDs
        identifiers = ["P12345,Q67890", "P54321"]
        result = await middleware.preprocess_identifiers(identifiers, "UNIPROTKB_AC")
        
        assert len(result) == 2
        assert result["P12345,Q67890"] == [("P12345", "UNIPROTKB_AC"), ("Q67890", "UNIPROTKB_AC")]
        assert result["P54321"] == [("P54321", "UNIPROTKB_AC")]
    
    @pytest.mark.asyncio
    async def test_aggregate_results_first_match(self, handler_and_middleware):
        """Test aggregation of component results with 'first_match' strategy."""
        handler, middleware = handler_and_middleware
        
        # Original identifiers and preprocessed map
        original_ids = ["GENE1_GENE2", "SINGLEGENE"]
        preprocessed_map = {
            "GENE1_GENE2": [("GENE1", "GENE_NAME"), ("GENE2", "GENE_NAME")],
            "SINGLEGENE": [("SINGLEGENE", "GENE_NAME")]
        }
        
        # Component mapping results
        component_results = {
            "GENE1": (["UNIPROT1"], "GENE1"),  # First component has a result
            "GENE2": (["UNIPROT2"], "GENE2"),  # Second component also has a result
            "SINGLEGENE": (["UNIPROT3"], "SINGLEGENE")
        }
        
        # Aggregate the results
        aggregated = await middleware.aggregate_results(
            original_ids, component_results, preprocessed_map, "GENE_NAME"
        )
        
        assert len(aggregated) == 2
        # For GENE1_GENE2, should use the result from GENE1 (first match)
        assert aggregated["GENE1_GENE2"] == (["UNIPROT1"], "GENE1")
        # For SINGLEGENE, should use its direct result
        assert aggregated["SINGLEGENE"] == (["UNIPROT3"], "SINGLEGENE")
    
    @pytest.mark.asyncio
    async def test_aggregate_results_all_matches(self, handler_and_middleware):
        """Test aggregation of component results with 'all_matches' strategy."""
        handler, middleware = handler_and_middleware
        
        # Original identifiers and preprocessed map
        original_ids = ["P12345,Q67890"]
        preprocessed_map = {
            "P12345,Q67890": [("P12345", "UNIPROTKB_AC"), ("Q67890", "UNIPROTKB_AC")]
        }
        
        # Component mapping results
        component_results = {
            "P12345": (["TARGET1", "TARGET2"], "P12345"),
            "Q67890": (["TARGET3"], "Q67890")
        }
        
        # Aggregate the results
        aggregated = await middleware.aggregate_results(
            original_ids, component_results, preprocessed_map, "UNIPROTKB_AC"
        )
        
        assert len(aggregated) == 1
        # For P12345,Q67890, should combine results from both components
        assert set(aggregated["P12345,Q67890"][0]) == {"TARGET1", "TARGET2", "TARGET3"}
        # Should use the first successful component as the source
        assert aggregated["P12345,Q67890"][1] == "P12345"
    
    @pytest.mark.asyncio
    async def test_aggregate_results_no_matches(self, handler_and_middleware):
        """Test aggregation when no components have results."""
        handler, middleware = handler_and_middleware
        
        # Original identifiers and preprocessed map
        original_ids = ["GENE1_GENE2"]
        preprocessed_map = {
            "GENE1_GENE2": [("GENE1", "GENE_NAME"), ("GENE2", "GENE_NAME")]
        }
        
        # Component mapping results - no matches
        component_results = {
            "GENE1": None,
            "GENE2": None
        }
        
        # Aggregate the results
        aggregated = await middleware.aggregate_results(
            original_ids, component_results, preprocessed_map, "GENE_NAME"
        )
        
        assert len(aggregated) == 1
        # For GENE1_GENE2, should be None since no components had results
        assert aggregated["GENE1_GENE2"] is None
