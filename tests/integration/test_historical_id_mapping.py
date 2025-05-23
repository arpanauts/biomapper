#!/usr/bin/env python
"""
Integration tests for the end-to-end UniProt historical ID resolution mapping workflow.

This test validates the complete mapping pipeline from UKBB identifiers to Arivale identifiers,
focusing on the ability to handle both direct mappings and historical ID resolution.
"""

import asyncio
import json
import logging
import os
import sys
import pytest
from typing import Dict, List, Any, Optional, Set, Tuple
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

# Import necessary components
from biomapper.core.mapping_executor import MappingExecutor, PathExecutionStatus
from biomapper.core.exceptions import NoPathFoundError, ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for testing
SOURCE_ENDPOINT = "UKBB_Protein"
TARGET_ENDPOINT = "Arivale_Protein"
SOURCE_ONTOLOGY = "UNIPROTKB_AC"  # Primary source ontology
TARGET_ONTOLOGY = "ARIVALE_PROTEIN_ID"  # Primary target ontology

# Test cases with expected outcomes
TEST_CASES = [
    # Regular direct mappings (should use direct path)
    {"id": "P01023", "description": "Alpha-2-macroglobulin", "expects_mapping": True, "expects_historical": False, "expects_multiple": False},
    {"id": "P04114", "description": "Apolipoprotein B-100", "expects_mapping": True, "expects_historical": False, "expects_multiple": False},
    {"id": "Q15848", "description": "Adiponectin", "expects_mapping": True, "expects_historical": False, "expects_multiple": False},
    
    # Historical ID cases (should use historical resolution path)
    {"id": "P0CG05", "description": "Polyubiquitin-C (historical, demerged to P0DOY2 & P0DOY3)", 
     "expects_mapping": True, "expects_historical": True, "expects_multiple": True},
    {"id": "P0CG47", "description": "Polyubiquitin-B (historical)", 
     "expects_mapping": True, "expects_historical": True, "expects_multiple": False},
    {"id": "P0CG48", "description": "Polyubiquitin-C (historical)", 
     "expects_mapping": True, "expects_historical": True, "expects_multiple": False},
    
    # Edge cases
    {"id": "", "description": "Empty ID", "expects_mapping": False, "expects_historical": False, "expects_multiple": False},
    {"id": "INVALID_ID", "description": "Invalid ID", "expects_mapping": False, "expects_historical": False, "expects_multiple": False},
]


class TestHistoricalIDMapping:
    """Test suite for the end-to-end historical ID mapping workflow."""
    
    @pytest.mark.asyncio
    async def test_mapping_with_historical_resolution(self, mock_mapping_executor, setup_mock_endpoints, setup_mock_paths, monkeypatch):
        """
        Test the complete mapping pipeline with both direct and historical resolution paths.
        
        This test validates:
        1. Direct mapping works for primary IDs
        2. Historical resolution path works for historical/secondary IDs
        3. One-to-many mappings are properly handled for demerged IDs
        4. Error handling works for invalid IDs
        """
        # Unpack the mock executor and sessions
        executor, mock_meta_session, mock_cache_session = mock_mapping_executor
        
        # Configure the mocks for endpoints and paths
        setup_mock_endpoints(SOURCE_ENDPOINT, TARGET_ENDPOINT, SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        setup_mock_paths(SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        
        # Mock the _execute_path method to return expected results based on input IDs
        async def mock_execute_path(session, path, input_identifiers, source_ontology, target_ontology, mapping_session_id=None):
            results = {}
            
            # Determine if this is the direct path or historical path
            is_historical_path = "Historical" in path.name if hasattr(path, "name") else False
            
            for input_id in input_identifiers:
                # Find the test case for this ID
                test_case = next((case for case in TEST_CASES if case["id"] == input_id), None)
                
                # Skip if no test case found
                if not test_case:
                    continue
                
                # For direct path, only map IDs that don't need historical resolution
                if not is_historical_path and not test_case["expects_historical"]:
                    if test_case["expects_mapping"]:
                        results[input_id] = {
                            "source_identifier": input_id,
                            "target_identifiers": [f"ARIVALE_{input_id}"],
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": "Direct mapping successful",
                            "confidence_score": 0.95,
                            "mapping_path_details": json.dumps({
                                "path_id": 1,
                                "path_name": "UKBB_to_Arivale_Protein_via_UniProt",
                                "resolved_historical": False,
                                "steps": [{
                                    "client_name": "ArivaleMetadataLookupClient",
                                    "step_order": 1
                                }]
                            }),
                            "hop_count": 1,
                            "mapping_direction": "forward",
                        }
                
                # For historical path, only map IDs that need historical resolution
                elif is_historical_path and test_case["expects_historical"]:
                    if test_case["expects_mapping"]:
                        # Handle one-to-many for demerged IDs
                        target_ids = [f"ARIVALE_{input_id}_1", f"ARIVALE_{input_id}_2"] if test_case["expects_multiple"] else [f"ARIVALE_{input_id}"] 
                        
                        results[input_id] = {
                            "source_identifier": input_id,
                            "target_identifiers": target_ids,
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": "Historical resolution successful",
                            "confidence_score": 0.85,  # Lower confidence for historical resolution
                            "mapping_path_details": json.dumps({
                                "path_id": 2,
                                "path_name": "UKBB_to_Arivale_Protein_via_Historical_Resolution",
                                "resolved_historical": True,
                                "steps": [{
                                    "client_name": "UniProtHistoricalResolverClient",
                                    "step_order": 1
                                }, {
                                    "client_name": "ArivaleMetadataLookupClient",
                                    "step_order": 2
                                }]
                            }),
                            "hop_count": 2,
                            "mapping_direction": "forward",
                        }
            
            return results
        
        # Apply the mock
        monkeypatch.setattr(executor, "_execute_path", mock_execute_path)
        
        # Extract test IDs
        test_ids = [case["id"] for case in TEST_CASES if case["id"]]
        
        # Execute mapping
        mapping_result = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=test_ids,
            source_property_name=SOURCE_ONTOLOGY,
            target_property_name=TARGET_ONTOLOGY,
            use_cache=False,  # Avoid cache to test the actual mapping
            mapping_direction="forward",
            try_reverse_mapping=False,
        )
        
        # Validate overall result structure
        assert "status" in mapping_result, "Result should include status"
        assert mapping_result["status"] in ["success", "partial_success"], f"Expected success or partial_success, got {mapping_result['status']}"
        assert "results" in mapping_result, "Result should include results dictionary"
        
        # Validate individual results against expected outcomes
        results = mapping_result["results"]
        for case in TEST_CASES:
            test_id = case["id"]
            if not test_id:  # Skip empty ID case
                continue
                
            # Ensure the ID is in the results
            assert test_id in results, f"ID {test_id} not found in results"
            result = results[test_id]
            
            # Check mapping success
            if case["expects_mapping"]:
                assert result["status"] == PathExecutionStatus.SUCCESS.value, \
                    f"Expected successful mapping for {test_id} ({case['description']}), got {result['status']}"
                assert result["target_identifiers"] is not None, \
                    f"Expected non-null target identifiers for {test_id} ({case['description']})"
            else:
                assert result["status"] != PathExecutionStatus.SUCCESS.value, \
                    f"Expected failed mapping for {test_id} ({case['description']}), got {result['status']}"
                
            # Check historical resolution
            if case["expects_historical"]:
                # Check if mapping_path_details contains info about historical resolution
                assert "mapping_path_details" in result, \
                    f"Expected mapping_path_details for historical ID {test_id}"
                
                path_details = result["mapping_path_details"]
                if isinstance(path_details, str):
                    try:
                        path_details = json.loads(path_details)
                    except json.JSONDecodeError:
                        path_details = {}
                
                # Check if this was derived using historical resolution
                # This might be in different locations depending on implementation
                historical_flag_found = False
                
                # Check in several possible locations
                if isinstance(path_details, dict):
                    # Option 1: Direct flag
                    if "resolved_historical" in path_details:
                        historical_flag_found = path_details["resolved_historical"]
                    
                    # Option 2: In path name
                    elif "path_name" in path_details and "Historical" in path_details["path_name"]:
                        historical_flag_found = True
                    
                    # Option 3: In step details
                    elif "steps" in path_details:
                        for step in path_details["steps"]:
                            if "client_name" in step and "Historical" in step["client_name"]:
                                historical_flag_found = True
                                break
                
                assert historical_flag_found, \
                    f"Expected evidence of historical resolution for {test_id} in mapping_path_details"
            
            # Check multiple mappings for demerged IDs
            if case["expects_multiple"]:
                assert result["target_identifiers"] is not None, \
                    f"Expected target identifiers for {test_id} ({case['description']})"
                assert len(result["target_identifiers"]) > 1, \
                    f"Expected multiple target identifiers for demerged ID {test_id}, got {result['target_identifiers']}"
    
    @pytest.mark.asyncio
    async def test_path_selection_order(self, mock_mapping_executor, setup_mock_endpoints, setup_mock_paths, monkeypatch):
        """
        Test that the executor prioritizes the direct path before falling back to historical resolution.
        """
        # Create test cases that should always use direct path
        direct_ids = ["P01023", "P04114"]
        
        # Create test cases that should require historical path
        historical_ids = ["P0CG05"]
        
        # Unpack the mock executor and sessions
        executor, mock_meta_session, mock_cache_session = mock_mapping_executor
        
        # Configure the mocks for endpoints and paths
        setup_mock_endpoints(SOURCE_ENDPOINT, TARGET_ENDPOINT, SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        setup_mock_paths(SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        
        # Track which paths are called
        path_execution_order = []
        
        # Create a patched version of _execute_path that tracks which paths are executed
        async def patched_execute_path(session, path, input_identifiers, source_ontology, target_ontology, mapping_session_id=None):
            path_name = path.name if hasattr(path, "name") else "unknown_path"
            path_execution_order.append({
                "path_name": path_name,
                "input_ids": input_identifiers,
            })
            
            # Return an empty result - we're just tracking execution order
            return {}
        
        # Apply the patch
        monkeypatch.setattr(executor, "_execute_path", patched_execute_path)
        
        # Execute mapping with a mix of direct and historical IDs
        await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=direct_ids + historical_ids,
            source_property_name=SOURCE_ONTOLOGY,
            target_property_name=TARGET_ONTOLOGY,
            use_cache=False,
            mapping_direction="forward",
            try_reverse_mapping=False,
        )
        
        # Validate path execution order
        assert len(path_execution_order) >= 2, "Expected at least two path executions (direct and historical)"
        
        # First path should be the direct path
        assert "Historical" not in path_execution_order[0]["path_name"], \
            "Expected direct path to be executed first"
        
        # Check if the historical resolution path was used
        historical_path_used = any("Historical" in path["path_name"] for path in path_execution_order)
        assert historical_path_used, "Expected historical resolution path to be used"
        
        # Historical ID should not be in the first path execution
        for historical_id in historical_ids:
            if historical_id in path_execution_order[0]["input_ids"]:
                assert False, f"Historical ID {historical_id} should not be in the first (direct) path execution"
    
    @pytest.mark.asyncio
    async def test_cache_usage(self, mock_mapping_executor, setup_mock_endpoints, setup_mock_paths, monkeypatch):
        """Test that caching works correctly for both direct and historical ID resolution."""
        # Use a subset of test cases
        test_ids = [case["id"] for case in TEST_CASES[:4] if case["id"]]
        
        # Unpack the mock executor and sessions
        executor, mock_meta_session, mock_cache_session = mock_mapping_executor
        
        # Configure the mocks for endpoints and paths
        setup_mock_endpoints(SOURCE_ENDPOINT, TARGET_ENDPOINT, SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        setup_mock_paths(SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        
        # Mock _check_cache to return cache hits on second call
        call_count = 0
        original_check_cache = executor._check_cache
        
        async def mock_check_cache(session, input_ids, source_ontology, target_ontology, max_age_days=None):
            nonlocal call_count
            if call_count == 0:
                # First call - return empty (no cache hits)
                call_count += 1
                return {}
            else:
                # Second call - return cache hits for all IDs
                result = {}
                for input_id in input_ids:
                    # Find the test case for this ID
                    test_case = next((case for case in TEST_CASES if case["id"] == input_id), None)
                    if test_case and test_case["expects_mapping"]:
                        # Create a mock cached result
                        target_ids = [f"CACHED_{input_id}_1", f"CACHED_{input_id}_2"] if test_case["expects_multiple"] else [f"CACHED_{input_id}"] 
                        result[input_id] = {
                            "source_identifier": input_id,
                            "target_identifiers": target_ids,
                            "status": PathExecutionStatus.SUCCESS.value,
                            "from_cache": True,
                            "cache_entity_id": 123,
                            "confidence_score": 0.9,
                            "mapping_path_details": json.dumps({"from_cache": True}),
                        }
                return result
        
        # Mock execute_path to track calls
        execute_path_called = False
        
        async def mock_execute_path(*args, **kwargs):
            nonlocal execute_path_called
            execute_path_called = True
            return {}
        
        # Apply the mocks
        monkeypatch.setattr(executor, "_check_cache", mock_check_cache)
        monkeypatch.setattr(executor, "_execute_path", mock_execute_path)
        
        # Use a subset of test cases
        test_ids = [case["id"] for case in TEST_CASES[:4] if case["id"]]
        
        # First mapping (should not use cache)
        first_result = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=test_ids,
            source_property_name=SOURCE_ONTOLOGY,
            target_property_name=TARGET_ONTOLOGY,
            use_cache=True,
            mapping_direction="forward",
            try_reverse_mapping=False,
        )
        
        # Reset execution tracking
        execute_path_called = False
        
        # Second mapping (should use cache)
        second_result = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=test_ids,
            source_property_name=SOURCE_ONTOLOGY,
            target_property_name=TARGET_ONTOLOGY,
            use_cache=True,
            mapping_direction="forward",
            try_reverse_mapping=False,
        )
        
        # Validate that _execute_path was not called (results came from cache)
        assert not execute_path_called, "Expected no calls to _execute_path when using cache"
        
        # Verify second result matches first
        assert second_result["status"] == first_result["status"], "Expected same status in cache hit case"
        assert len(second_result["results"]) == len(first_result["results"]), "Expected same number of results in cache hit case"
        
        # Verify historical resolution info is preserved in cache
        for case in TEST_CASES[:4]:
            test_id = case["id"]
            if not test_id or not case["expects_historical"]:
                continue
                
            # Ensure historical resolution metadata is preserved in cached result
            result = second_result["results"][test_id]
            assert "mapping_path_details" in result, f"Expected mapping_path_details for cached historical ID {test_id}"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mapping_executor, setup_mock_endpoints, setup_mock_paths, monkeypatch):
        """Test that errors are properly handled and reported."""
        # Unpack the mock executor and sessions
        executor, mock_meta_session, mock_cache_session = mock_mapping_executor
        
        # Configure the mocks for endpoints and paths
        setup_mock_endpoints(SOURCE_ENDPOINT, TARGET_ENDPOINT, SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        setup_mock_paths(SOURCE_ONTOLOGY, TARGET_ONTOLOGY)
        
        # Create a patched version of _execute_path that raises an error
        async def failing_execute_path(*args, **kwargs):
            raise ClientError("Test client error", details={"step": "test_step"})
        
        # Apply the patch
        monkeypatch.setattr(executor, "_execute_path", failing_execute_path)
        
        # Execute mapping
        result = await executor.execute_mapping(
            source_endpoint_name=SOURCE_ENDPOINT,
            target_endpoint_name=TARGET_ENDPOINT,
            input_identifiers=["P01023"],
            source_property_name=SOURCE_ONTOLOGY,
            target_property_name=TARGET_ONTOLOGY,
            use_cache=False,
            mapping_direction="forward",
            try_reverse_mapping=False,
        )
        
        # Validate error handling
        assert result["status"] != "success", "Expected non-success status when error occurs"
        assert "P01023" in result["results"], "Expected result entry for input ID even when error occurs"
        assert result["results"]["P01023"]["status"] == PathExecutionStatus.ERROR.value, \
            "Expected ERROR status for result when client error occurs"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
