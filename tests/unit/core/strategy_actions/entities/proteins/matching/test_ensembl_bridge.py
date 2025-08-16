"""Tests for Ensembl bridge matching action."""

import pytest
import pandas as pd
import numpy as np
from biomapper.core.strategy_actions.entities.proteins.matching.ensembl_bridge import (
    ProteinEnsemblBridge,
    ProteinEnsemblBridgeParams,
    ActionResult
)


class TestProteinEnsemblBridge:
    """Comprehensive tests for Ensembl bridge matching."""
    
    @pytest.fixture
    def source_proteins(self):
        """Source proteins with Ensembl IDs to match."""
        return pd.DataFrame({
            'id': ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'],
            'ensembl_id': ['ENSP00000269305', 'ENSP00000350283', 'ENSP00000275493', 'ENSP00000308067', 'ENSP00000367207', 'ENSP00000277541'],
            'uniprot_id': ['P04637', 'P38398', 'P00533', 'P01116', 'P01106', 'P46531'],
            'gene_symbol': ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'MYC', 'NOTCH1']
        })
    
    @pytest.fixture
    def reference_proteins(self):
        """Reference dataset with Ensembl IDs."""
        return pd.DataFrame({
            'id': ['KG2_1', 'KG2_2', 'KG2_3', 'KG2_4', 'KG2_5', 'KG2_6', 'KG2_7'],
            'ensembl_protein_id': ['ENSP00000269305', 'ENSP00000350283', 'ENSP00000275493', 'ENSP00000308067', 'ENSP00000367207.1', 'ENSP00000277541.2', 'ENSP99999999'],
            'uniprot_accession': ['P04637', 'P38398', 'P00533', 'P01116', 'P01106', 'P46531', None],
            'description': ['p53', 'BRCA1', 'EGFR', 'KRAS', 'MYC', 'Notch 1', 'Unknown protein']
        })
    
    @pytest.fixture
    def already_matched(self):
        """Already matched proteins from previous stages."""
        return pd.DataFrame({
            'source_id': ['P1', 'P2', 'P3'],
            'target_id': ['KG2_1', 'KG2_2', 'KG2_3'],
            'match_method': ['direct', 'direct', 'gene_symbol'],
            'confidence': [1.0, 1.0, 0.95]
        })
    
    @pytest.mark.asyncio
    async def test_exact_ensembl_matching(self, source_proteins, reference_proteins):
        """Should match proteins with exact Ensembl IDs."""
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],  # No previous matches
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched"
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert 'ensembl_matched' in context['datasets']
        
        matched_df = context['datasets']['ensembl_matched']
        assert len(matched_df) > 0
        
        # Check exact matches (first 4 should match exactly)
        exact_matches = matched_df[matched_df['confidence'] == 1.0]
        assert len(exact_matches) >= 4
        assert 'P4' in exact_matches['source_id'].values  # KRAS
    
    @pytest.mark.asyncio
    async def test_version_stripped_matching(self, source_proteins, reference_proteins):
        """Should match Ensembl IDs with version suffixes stripped."""
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched",
            strip_versions=True
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['ensembl_matched']
        
        # P5 should match despite .1 version suffix in reference
        p5_match = matched_df[matched_df['source_id'] == 'P5']
        assert len(p5_match) > 0
        assert p5_match.iloc[0]['confidence'] >= 0.9  # High confidence for version match
        
        # P6 should match despite .2 version suffix
        p6_match = matched_df[matched_df['source_id'] == 'P6']
        assert len(p6_match) > 0
        assert p6_match.iloc[0]['confidence'] >= 0.9
    
    @pytest.mark.asyncio
    async def test_excludes_already_matched(self, source_proteins, reference_proteins, already_matched):
        """Should exclude proteins that were already matched in previous stages."""
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=["previous_matches"],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched"
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
        matched_df = context['datasets']['ensembl_matched']
        
        # P1, P2, P3 should not be in results (already matched)
        assert 'P1' not in matched_df['source_id'].values
        assert 'P2' not in matched_df['source_id'].values
        assert 'P3' not in matched_df['source_id'].values
        
        # P4, P5, P6 should still be matched
        assert 'P4' in matched_df['source_id'].values
        assert 'P5' in matched_df['source_id'].values
        assert 'P6' in matched_df['source_id'].values
    
    @pytest.mark.asyncio
    async def test_handles_missing_ensembl_ids(self):
        """Should handle missing or null Ensembl IDs gracefully."""
        source_with_missing = pd.DataFrame({
            'id': ['P1', 'P2', 'P3', 'P4'],
            'ensembl_id': ['ENSP00000269305', None, np.nan, ''],
            'uniprot_id': ['P04637', 'P38398', 'P00533', 'P01116']
        })
        
        reference_with_missing = pd.DataFrame({
            'id': ['KG2_1', 'KG2_2', 'KG2_3', 'KG2_4'],
            'ensembl_protein_id': ['ENSP00000269305', None, '', 'ENSP00000308067'],
            'uniprot_accession': ['P04637', 'P38398', 'P00533', 'P01116']
        })
        
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched"
        )
        
        context = {
            'datasets': {
                'source': source_with_missing,
                'reference': reference_with_missing
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['ensembl_matched']
        
        # Only P1 with valid Ensembl ID should match
        assert len(matched_df) == 1
        assert matched_df.iloc[0]['source_id'] == 'P1'
    
    @pytest.mark.asyncio
    async def test_tracks_statistics(self, source_proteins, reference_proteins):
        """Should track matching statistics in context."""
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched"
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
        assert 'ensembl_bridge' in context['statistics']
        
        stats = context['statistics']['ensembl_bridge']
        assert 'total_processed' in stats
        assert 'exact_matches' in stats
        assert 'version_matches' in stats
        assert 'unmatched' in stats
        assert stats['total_processed'] == len(source_proteins)
    
    @pytest.mark.asyncio
    async def test_invalid_ensembl_format_filtering(self):
        """Should filter out invalid Ensembl ID formats."""
        source_with_invalid = pd.DataFrame({
            'id': ['P1', 'P2', 'P3', 'P4'],
            'ensembl_id': ['ENSP00000269305', 'INVALID_ID', 'ENSG00000141510', 'ENSP00000350283'],
            'uniprot_id': ['P04637', 'P38398', 'P00533', 'P01116']
        })
        
        reference_proteins = pd.DataFrame({
            'id': ['KG2_1', 'KG2_2', 'KG2_3', 'KG2_4'],
            'ensembl_protein_id': ['ENSP00000269305', 'INVALID_REF', 'ENSP00000275493', 'ENSP00000350283'],
            'uniprot_accession': ['P04637', 'P38398', 'P00533', 'P01116']
        })
        
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=[],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched",
            validate_format=True
        )
        
        context = {
            'datasets': {
                'source': source_with_invalid,
                'reference': reference_proteins
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['ensembl_matched']
        
        # Only P1 and P4 should match (valid ENSP formats)
        assert len(matched_df) <= 2
        assert all(matched_df['source_id'].isin(['P1', 'P4']))
    
    @pytest.mark.asyncio
    async def test_multiple_unmatched_datasets(self, source_proteins, reference_proteins):
        """Should handle multiple datasets to exclude from matching."""
        direct_matches = pd.DataFrame({
            'source_id': ['P1'],
            'target_id': ['KG2_1'],
            'match_method': ['direct'],
            'confidence': [1.0]
        })
        
        gene_matches = pd.DataFrame({
            'source_id': ['P2', 'P3'],
            'target_id': ['KG2_2', 'KG2_3'],
            'match_method': ['gene_symbol', 'gene_symbol'],
            'confidence': [0.95, 0.90]
        })
        
        action = ProteinEnsemblBridge()
        params = ProteinEnsemblBridgeParams(
            dataset_key="source",
            reference_dataset="reference",
            unmatched_from=["direct_matches", "gene_matches"],
            source_ensembl_column="ensembl_id",
            reference_ensembl_column="ensembl_protein_id",
            output_key="ensembl_matched"
        )
        
        context = {
            'datasets': {
                'source': source_proteins,
                'reference': reference_proteins,
                'direct_matches': direct_matches,
                'gene_matches': gene_matches
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is True
        matched_df = context['datasets']['ensembl_matched']
        
        # P1, P2, P3 should be excluded
        excluded_ids = ['P1', 'P2', 'P3']
        assert all(excluded_id not in matched_df['source_id'].values for excluded_id in excluded_ids)
        
        # P4, P5, P6 should still be available for matching
        remaining_ids = ['P4', 'P5', 'P6']
        assert any(remaining_id in matched_df['source_id'].values for remaining_id in remaining_ids)