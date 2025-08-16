"""Tests for gene symbol bridge matching action."""

import pytest
import pandas as pd
import numpy as np
from biomapper.core.strategy_actions.entities.proteins.matching.gene_symbol_bridge import (
    ProteinGeneSymbolBridge,
    ProteinGeneSymbolBridgeParams,
    ActionResult
)


class TestProteinGeneSymbolBridge:
    """Comprehensive tests for gene symbol bridge matching."""
    
    @pytest.fixture
    def source_proteins(self):
        """Source proteins with gene symbols to match."""
        return pd.DataFrame({
            'id': ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'],
            'gene_symbol': ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'MYC', 'NOTCH1'],
            'uniprot_id': ['P04637', 'P38398', 'P00533', 'P01116', 'P01106', 'P46531'],
            'name': ['Tumor protein p53', 'Breast cancer 1', 'EGFR protein', 'KRAS proto-oncogene', 'MYC proto-oncogene', 'Notch 1']
        })
    
    @pytest.fixture
    def reference_proteins(self):
        """Reference dataset with gene symbols."""
        return pd.DataFrame({
            'id': ['KG2_1', 'KG2_2', 'KG2_3', 'KG2_4', 'KG2_5', 'KG2_6', 'KG2_7'],
            'gene_symbol': ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'MYC-1', 'NOTCH-1', 'UNKNOWN'],
            'uniprot_accession': ['P04637', 'P38398', 'P00533', 'P01116', 'P01106_VAR', 'P46531_VAR', None],
            'description': ['p53', 'BRCA1', 'EGFR', 'KRAS', 'MYC variant', 'Notch variant', 'Unknown protein']
        })
    
    @pytest.fixture
    def already_matched(self):
        """Already matched proteins from previous stages."""
        return pd.DataFrame({
            'source_id': ['P1', 'P2'],
            'target_id': ['KG2_1', 'KG2_2'],
            'match_method': ['direct', 'direct'],
            'confidence': [1.0, 1.0]
        })
    
    @pytest.mark.asyncio
    async def test_exact_gene_symbol_matching(self, source_proteins, reference_proteins):
        """Should match proteins with exact gene symbols."""
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],  # No previous matches
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched",
            min_confidence=0.8
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert 'gene_matched' in context['datasets']
        
        matched_df = context['datasets']['gene_matched']
        assert len(matched_df) > 0
        
        # Check exact matches
        exact_matches = matched_df[matched_df['confidence'] == 1.0]
        assert 'P3' in exact_matches['source_id'].values  # EGFR exact match
        assert 'P4' in exact_matches['source_id'].values  # KRAS exact match
    
    @pytest.mark.asyncio
    async def test_fuzzy_gene_symbol_matching(self, source_proteins, reference_proteins):
        """Should match proteins with similar gene symbols using fuzzy matching."""
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched",
            min_confidence=0.7,
            use_fuzzy=True,
            fuzzy_threshold=70  # Lower threshold to catch MYC vs MYC-1 (75 score)
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['gene_matched']
        
        # Check fuzzy matches
        myc_match = matched_df[matched_df['source_id'] == 'P5']
        assert len(myc_match) > 0  # MYC should match MYC-1
        assert myc_match.iloc[0]['confidence'] < 1.0  # Fuzzy match confidence
        
        notch_match = matched_df[matched_df['source_id'] == 'P6']
        assert len(notch_match) > 0  # NOTCH1 should match NOTCH-1
    
    @pytest.mark.asyncio
    async def test_excludes_already_matched(self, source_proteins, reference_proteins, already_matched):
        """Should exclude proteins that were already matched in previous stages."""
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=["previous_matches"],
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched",
            min_confidence=0.8
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins,
                'previous_matches': already_matched
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['gene_matched']
        
        # P1 and P2 should not be in results (already matched)
        assert 'P1' not in matched_df['source_id'].values
        assert 'P2' not in matched_df['source_id'].values
        
        # P3 and P4 should still be matched
        assert 'P3' in matched_df['source_id'].values
        assert 'P4' in matched_df['source_id'].values
    
    @pytest.mark.asyncio
    async def test_handles_missing_gene_symbols(self):
        """Should handle missing or null gene symbols gracefully."""
        source_with_missing = pd.DataFrame({
            'id': ['P1', 'P2', 'P3'],
            'gene_symbol': ['TP53', None, np.nan],
            'uniprot_id': ['P04637', 'P38398', 'P00533']
        })
        
        reference_with_missing = pd.DataFrame({
            'id': ['KG2_1', 'KG2_2', 'KG2_3'],
            'gene_symbol': ['TP53', None, ''],
            'uniprot_accession': ['P04637', 'P38398', 'P00533']
        })
        
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched"
        )
        
        context = {
            'datasets': {
                'source': source_with_missing,
                'reference': reference_with_missing
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['gene_matched']
        
        # Only P1 with TP53 should match
        assert len(matched_df) == 1
        assert matched_df.iloc[0]['source_id'] == 'P1'
    
    @pytest.mark.asyncio
    async def test_tracks_statistics(self, source_proteins, reference_proteins):
        """Should track matching statistics in context."""
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched"
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            },
            'statistics': {}
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert 'gene_symbol_bridge' in context['statistics']
        
        stats = context['statistics']['gene_symbol_bridge']
        assert 'total_processed' in stats
        assert 'exact_matches' in stats
        assert 'fuzzy_matches' in stats
        assert 'unmatched' in stats
        assert stats['total_processed'] == len(source_proteins)
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, source_proteins, reference_proteins):
        """Should filter matches below confidence threshold."""
        action = ProteinGeneSymbolBridge()
        params = ProteinGeneSymbolBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_gene_column="gene_symbol",
            reference_gene_column="gene_symbol",
            output_key="gene_matched",
            min_confidence=0.95,  # High threshold
            use_fuzzy=True
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['gene_matched']
        
        # All matches should have confidence >= 0.95
        assert all(matched_df['confidence'] >= 0.95)
        
        # Fuzzy matches with lower confidence should be excluded
        assert 'P5' not in matched_df['source_id'].values  # MYC vs MYC-1
        assert 'P6' not in matched_df['source_id'].values  # NOTCH1 vs NOTCH-1