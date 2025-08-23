#!/usr/bin/env python3
"""
Tests for LIPID MAPS Static Matcher.

Tests the fast, reliable static matching approach that replaces SPARQL.

STATUS: External service integration not implemented
FUNCTIONALITY: LIPID MAPS static data matching via local indices  
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use core metabolite matching actions (fuzzy, vector, etc.)
"""

import pytest
import pandas as pd
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import asyncio

# Skip entire module - external service integrations not implemented  
pytestmark = pytest.mark.skip("External service integrations not implemented - use core metabolite matching actions instead")

from src.actions.entities.metabolites.external.lipid_maps_static_match import (
    LipidMapsStaticMatch,
    LipidMapsStaticParams,
    LipidMapsStaticResult
)


class TestLipidMapsStaticMatch:
    """Test suite for LIPID MAPS static matcher."""
    
    @pytest.fixture
    def sample_indices(self):
        """Create sample LIPID MAPS indices for testing."""
        return {
            "exact_names": {
                "Cholesterol": "LMST01010001",
                "Palmitic acid": "LMFA01010001",
                "DHA": "LMFA01030185",
                "Oleic acid": "LMFA01030002"
            },
            "normalized_names": {
                "cholesterol": "LMST01010001",
                "palmitic acid": "LMFA01010001",
                "dha": "LMFA01030185",
                "oleic acid": "LMFA01030002",
                "docosahexaenoic acid": "LMFA01030185"
            },
            "synonyms": {
                "18:2n6": "LMFA01030120",
                "22:6n3": "LMFA01030185",
                "Docosahexaenoic acid": "LMFA01030185",
                "C16:0": "LMFA01010001"
            },
            "lipid_data": {
                "LMST01010001": {
                    "COMMON_NAME": "Cholesterol",
                    "SYSTEMATIC_NAME": "cholest-5-en-3β-ol",
                    "FORMULA": "C27H46O",
                    "CATEGORY": "Sterol Lipids"
                },
                "LMFA01010001": {
                    "COMMON_NAME": "Palmitic acid",
                    "SYSTEMATIC_NAME": "hexadecanoic acid",
                    "FORMULA": "C16H32O2",
                    "CATEGORY": "Fatty Acyls"
                },
                "LMFA01030185": {
                    "COMMON_NAME": "DHA",
                    "SYSTEMATIC_NAME": "(4Z,7Z,10Z,13Z,16Z,19Z)-docosahexaenoic acid",
                    "FORMULA": "C22H32O2",
                    "CATEGORY": "Fatty Acyls"
                },
                "LMFA01030002": {
                    "COMMON_NAME": "Oleic acid",
                    "SYSTEMATIC_NAME": "(9Z)-octadecenoic acid",
                    "FORMULA": "C18H34O2",
                    "CATEGORY": "Fatty Acyls"
                },
                "LMFA01030120": {
                    "COMMON_NAME": "Linoleic acid",
                    "SYSTEMATIC_NAME": "(9Z,12Z)-octadecadienoic acid",
                    "FORMULA": "C18H32O2",
                    "CATEGORY": "Fatty Acyls"
                }
            }
        }
    
    @pytest.fixture
    def temp_data_dir(self, sample_indices):
        """Create temporary directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save sample indices
            data_file = Path(tmpdir) / "lipidmaps_static_202501.json"
            with open(data_file, 'w') as f:
                json.dump(sample_indices, f)
            yield tmpdir
    
    @pytest.fixture
    def test_metabolites(self):
        """Create test metabolite dataset."""
        return pd.DataFrame([
            {"identifier": "Cholesterol", "SUPER_PATHWAY": "Lipid"},
            {"identifier": "glucose", "SUPER_PATHWAY": "Carbohydrate"},
            {"identifier": "palmitic acid", "SUPER_PATHWAY": "Lipid"},  # Lowercase
            {"identifier": "22:6n3", "SUPER_PATHWAY": "Lipid"},  # Synonym
            {"identifier": "alanine", "SUPER_PATHWAY": "Amino Acid"},
            {"identifier": "DHA", "SUPER_PATHWAY": "Lipid"},
            {"identifier": "unknown_lipid", "SUPER_PATHWAY": "Lipid"}
        ])
    
    @pytest.mark.asyncio
    async def test_basic_matching(self, temp_data_dir, test_metabolites):
        """Test basic metabolite matching."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            data_version="202501"
        )
        
        context = {
            "datasets": {
                "unmapped": test_metabolites,
                "original_metabolites": test_metabolites
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 4  # Cholesterol, palmitic acid, 22:6n3, DHA
        assert result.total_processed == 7
        
        matched = context["datasets"]["matched"]
        unmatched = context["datasets"]["still_unmapped"]
        
        assert len(matched) == 4
        assert len(unmatched) == 3
        
        # Check specific matches
        cholesterol = matched[matched["identifier"] == "Cholesterol"].iloc[0]
        assert cholesterol["lipid_maps_id"] == "LMST01010001"
        assert cholesterol["match_type"] == "exact"
        assert cholesterol["confidence_score"] == 1.0
    
    @pytest.mark.asyncio
    async def test_normalized_matching(self, temp_data_dir):
        """Test case-insensitive normalized matching."""
        
        test_data = pd.DataFrame([
            {"identifier": "CHOLESTEROL"},  # Uppercase
            {"identifier": "Palmitic Acid"},  # Different case
            {"identifier": "docosahexaenoic acid"}  # Lowercase full name
        ])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            use_normalized_matching=True
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 3
        assert result.normalized_matches == 3
    
    @pytest.mark.asyncio
    async def test_synonym_matching(self, temp_data_dir):
        """Test synonym and alternative name matching."""
        
        test_data = pd.DataFrame([
            {"identifier": "18:2n6"},  # Fatty acid notation
            {"identifier": "22:6n3"},  # DHA notation
            {"identifier": "C16:0"},  # Palmitic acid notation
            {"identifier": "Docosahexaenoic acid"}  # Full name
        ])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            use_synonym_matching=True
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 4
        assert result.synonym_matches >= 3  # At least 3 are synonyms
    
    @pytest.mark.asyncio
    async def test_disabled_action(self, temp_data_dir, test_metabolites):
        """Test that action can be disabled."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            enabled=False
        )
        
        context = {"datasets": {"unmapped": test_metabolites}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 0
        assert "disabled" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_missing_data_file(self):
        """Test handling of missing data file."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir="/nonexistent/directory"
        )
        
        context = {"datasets": {"unmapped": pd.DataFrame([{"identifier": "test"}])}}
        result = await action.execute_typed(params, context)
        
        assert not result.success
        assert "failed to load" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_confidence_threshold(self, temp_data_dir):
        """Test confidence score filtering."""
        
        test_data = pd.DataFrame([
            {"identifier": "Cholesterol"},  # Exact match, confidence 1.0
            {"identifier": "cholesterol"},  # Normalized match, confidence 0.95
            {"identifier": "22:6n3"}  # Synonym match, confidence 0.9
        ])
        
        action = LipidMapsStaticMatch()
        
        # High threshold - only exact matches
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            confidence_threshold=0.98
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.matches_found == 1  # Only exact match passes
        
        # Lower threshold - all matches
        params.confidence_threshold = 0.8
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.matches_found == 3  # All matches pass
    
    @pytest.mark.asyncio
    async def test_coverage_calculation(self, temp_data_dir):
        """Test coverage statistics calculation."""
        
        original = pd.DataFrame([{"id": i} for i in range(100)])
        unmapped = pd.DataFrame([{"identifier": f"metabolite_{i}"} for i in range(20)])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir
        )
        
        context = {
            "datasets": {
                "unmapped": unmapped,
                "original_metabolites": original
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.coverage_before == 0.8  # 80% already matched
        # Coverage after depends on how many we match
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, temp_data_dir):
        """Test that performance metrics are tracked."""
        
        test_data = pd.DataFrame([
            {"identifier": f"metabolite_{i}"} for i in range(100)
        ])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 1000  # Should be fast
        
        # Check per-metabolite time
        per_metabolite = result.processing_time_ms / result.total_processed
        assert per_metabolite < 10  # Should be < 10ms per metabolite
    
    @pytest.mark.asyncio
    async def test_max_metabolites_limit(self, temp_data_dir):
        """Test limiting number of metabolites processed."""
        
        test_data = pd.DataFrame([
            {"identifier": f"metabolite_{i}"} for i in range(100)
        ])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            max_metabolites=10
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.total_processed == 10  # Limited to 10
    
    @pytest.mark.asyncio
    async def test_statistics_update(self, temp_data_dir, test_metabolites):
        """Test that context statistics are updated."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir
        )
        
        context = {"datasets": {"unmapped": test_metabolites}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert "statistics" in context
        assert "lipid_maps_static" in context["statistics"]
        
        stats = context["statistics"]["lipid_maps_static"]
        assert stats["matches_found"] == result.matches_found
        assert stats["exact_matches"] == result.exact_matches
        assert stats["normalized_matches"] == result.normalized_matches
        assert stats["synonym_matches"] == result.synonym_matches
        assert stats["processing_time_ms"] == result.processing_time_ms
    
    @pytest.mark.asyncio
    async def test_empty_input(self, temp_data_dir):
        """Test handling of empty input data."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir
        )
        
        context = {"datasets": {"unmapped": pd.DataFrame()}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 0
        assert "no input data" in result.message.lower()
    
    @pytest.mark.asyncio  
    async def test_missing_identifier_column(self, temp_data_dir):
        """Test handling of missing identifier column."""
        
        test_data = pd.DataFrame([
            {"metabolite": "Cholesterol"},  # Wrong column name
            {"metabolite": "DHA"}
        ])
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir,
            identifier_column="identifier"  # Column doesn't exist
        )
        
        context = {"datasets": {"unmapped": test_data}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        assert result.matches_found == 0  # No matches due to missing column
    
    @pytest.mark.asyncio
    async def test_data_version_fallback(self, sample_indices):
        """Test fallback to available data version."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save with different version
            data_file = Path(tmpdir) / "lipidmaps_static_202412.json"
            with open(data_file, 'w') as f:
                json.dump(sample_indices, f)
            
            action = LipidMapsStaticMatch()
            params = LipidMapsStaticParams(
                input_key="unmapped",
                output_key="matched",
                unmatched_key="still_unmapped",
                data_dir=tmpdir,
                data_version="202501"  # Request non-existent version
            )
            
            test_data = pd.DataFrame([{"identifier": "Cholesterol"}])
            context = {"datasets": {"unmapped": test_data}}
            
            result = await action.execute_typed(params, context)
            
            assert result.success
            assert result.matches_found == 1  # Still works with fallback
    
    @pytest.mark.asyncio
    async def test_match_details_in_output(self, temp_data_dir, test_metabolites):
        """Test that match details are included in output."""
        
        action = LipidMapsStaticMatch()
        params = LipidMapsStaticParams(
            input_key="unmapped",
            output_key="matched",
            unmatched_key="still_unmapped",
            data_dir=temp_data_dir
        )
        
        context = {"datasets": {"unmapped": test_metabolites}}
        result = await action.execute_typed(params, context)
        
        assert result.success
        
        matched = context["datasets"]["matched"]
        
        # Check that all required columns are present
        required_columns = [
            "lipid_maps_id", "match_type", "confidence_score",
            "common_name", "systematic_name", "formula", "category"
        ]
        
        for col in required_columns:
            assert col in matched.columns
        
        # Check specific match details
        dha_matches = matched[matched["identifier"] == "DHA"]
        assert len(dha_matches) == 1
        dha = dha_matches.iloc[0]
        assert dha["common_name"] == "DHA"
        assert dha["formula"] == "C22H32O2"
        assert dha["category"] == "Fatty Acyls"