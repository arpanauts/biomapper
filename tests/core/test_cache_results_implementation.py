#!/usr/bin/env python3
"""
Test script for validating the _cache_results method implementation 
with metadata field population in MappingExecutor.
"""

import json
import asyncio
import datetime
from typing import Dict, Any, List, Optional, Union
from unittest.mock import MagicMock, AsyncMock, patch
from enum import Enum

# Mock classes to simulate the required objects
class MockMappingResource:
    def __init__(self, id=None, name=None, resource_type=None, client_class_path=None, 
                 input_ontology_term=None, output_ontology_term=None):
        self.id = id
        self.name = name
        self.resource_type = resource_type
        self.client_class_path = client_class_path
        self.input_ontology_term = input_ontology_term
        self.output_ontology_term = output_ontology_term

class MockMappingPathStep:
    def __init__(self, step_order=None, mapping_resource=None):
        self.step_order = step_order
        self.mapping_resource = mapping_resource

class MockMappingPath:
    def __init__(self, id=None, name=None, steps=None):
        self.id = id
        self.name = name
        self.steps = steps or []

class MockReversiblePath:
    def __init__(self, original_path, is_reverse=False):
        self.original_path = original_path
        self.is_reverse = is_reverse
        self.id = original_path.id
        self.name = f"{original_path.name} (Reverse)" if is_reverse else original_path.name
        self.steps = original_path.steps

class MockEntityMapping:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class PathExecutionStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    NO_MAPPING_FOUND = "no_mapping_found"

class MockAsyncSession:
    def __init__(self):
        self.add_all_calls = []
        self.commit_calls = 0
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        pass
    
    async def add_all(self, mappings):
        self.add_all_calls.append(mappings)
        
    async def commit(self):
        self.commit_calls += 1
        
class MockMappingExecutor:
    def __init__(self):
        self.session = MockAsyncSession()
        
    def get_cache_session(self):
        return self.session

# Custom JSON encoder for testing
class PydanticEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle special types."""
    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Handle Enum values
        if isinstance(obj, Enum):
            return obj.value
        # Let the base class handle anything else
        return super().default(obj)

async def test_cache_results():
    """Test the _cache_results method."""
    # Create mock resources
    resource1 = MockMappingResource(
        id=1, 
        name="TestResource1", 
        resource_type="API", 
        client_class_path="biomapper.test.TestClient",
        input_ontology_term="ChEBI",
        output_ontology_term="HMDB"
    )
    
    resource2 = MockMappingResource(
        id=2, 
        name="TestResource2", 
        resource_type="Database", 
        client_class_path="biomapper.test.DatabaseClient",
        input_ontology_term="HMDB",
        output_ontology_term="PubChem"
    )
    
    # Create mock steps
    step1 = MockMappingPathStep(step_order=1, mapping_resource=resource1)
    step2 = MockMappingPathStep(step_order=2, mapping_resource=resource2)
    
    # Create a mock path with steps
    path = MockMappingPath(id=101, name="Test Mapping Path", steps=[step1, step2])
    
    # Implementation of _cache_results
    async def _cache_results(
        self,
        results_to_cache: Dict[str, Dict[str, Any]],
        path: Union[MockMappingPath, MockReversiblePath],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None
    ):
        """Store successful mapping results in the cache with metadata fields."""
        # Skip if no results to cache
        if not results_to_cache:
            print("No results to cache")
            return None
        
        # Get basic path information
        path_id = getattr(path, 'id', None)
        path_name = getattr(path, 'name', "Unknown")
        
        # Determine if this is a reverse path
        is_reversed = getattr(path, "is_reverse", False)
        mapping_direction = "reverse" if is_reversed else "forward"
        
        # Calculate hop count from path steps if available
        if hasattr(path, 'original_path') and path.original_path:
            # This is a ReversiblePath, so get its wrapped path for the steps
            path_obj = path.original_path
        else:
            # This is a regular MappingPath
            path_obj = path
        
        # Now extract the hop count from the steps
        hop_count = len(path_obj.steps) if hasattr(path_obj, "steps") and path_obj.steps else None
        
        # Prepare the rich path details JSON structure
        path_details = {}
        
        # Add step information if available
        if hasattr(path_obj, "steps") and path_obj.steps:
            # Sort steps for consistent ordering
            steps = sorted(path_obj.steps, key=lambda s: getattr(s, 'step_order', 0))
            
            for idx, step in enumerate(steps):
                step_order = getattr(step, 'step_order', idx + 1)
                resource = getattr(step, 'mapping_resource', None)
                
                # Create a step entry with relevant details
                step_key = f"step_{step_order}"
                path_details[step_key] = {
                    "resource_id": getattr(resource, 'id', None) if resource else None,
                    "resource_name": getattr(resource, 'name', "Unknown") if resource else "Unknown",
                    "resource_type": getattr(resource, 'resource_type', "Unknown") if resource else "Unknown",
                    "client_class": getattr(resource, 'client_class_path', "Unknown") if resource else "Unknown",
                    "input_ontology": getattr(resource, 'input_ontology_term', "Unknown") if resource else "Unknown",
                    "output_ontology": getattr(resource, 'output_ontology_term', "Unknown") if resource else "Unknown",
                }
        
        # Construct the final mapping_path_info to be serialized
        mapping_path_info = {
            "path_id": path_id,
            "path_name": path_name,
            "mapping_direction": mapping_direction,
            "hop_count": hop_count,
            "steps": path_details
        }
        
        # Serialize to JSON
        try:
            path_details_json = json.dumps(mapping_path_info, cls=PydanticEncoder)
        except Exception as e:
            print(f"Failed to serialize path details: {e}")
            path_details_json = json.dumps({"error": "Failed to serialize path details", "path_id": path_id})
        
        # Create entity mappings
        mappings_to_add = []
        current_time = datetime.datetime.now().replace(microsecond=0)
        
        for source_id, result in results_to_cache.items():
            target_identifiers = result.get("target_identifiers", [])
            # Ensure target_identifiers is always a list
            if not isinstance(target_identifiers, list):
                target_identifiers = [target_identifiers] if target_identifiers is not None else []
            
            # Filter out None values from target identifiers
            valid_target_ids = [tid for tid in target_identifiers if tid is not None]
            
            if not valid_target_ids:
                print(f"No valid target identifiers found for source {source_id}")
                continue
            
            # Calculate confidence score
            confidence_score = result.get("confidence_score")
            if confidence_score is None:
                if hop_count is not None:
                    if hop_count <= 1:
                        confidence_score = 0.9  # Direct mapping
                    elif hop_count == 2:
                        confidence_score = 0.8  # 2-hop mapping
                    else:
                        # Decrease confidence for longer paths
                        confidence_score = max(0.1, 0.9 - ((hop_count - 1) * 0.1))
                    
                    # Apply penalty for reverse paths
                    if is_reversed:
                        confidence_score = max(0.1, confidence_score - 0.05)
                else:
                    confidence_score = 0.7  # Default if hop_count is somehow None
            
            # Create entity mapping for each valid target identifier
            for target_id in valid_target_ids:
                # For testing, use a dictionary to represent our entity mapping
                entity_mapping = MockEntityMapping(
                    source_id=str(source_id),
                    source_type=source_ontology,
                    target_id=str(target_id),
                    target_type=target_ontology,
                    confidence_score=confidence_score,
                    hop_count=hop_count,
                    mapping_direction=mapping_direction,
                    mapping_path_details=path_details_json,
                    last_updated=current_time
                )
                mappings_to_add.append(entity_mapping)
        
        if not mappings_to_add:
            print(f"No valid entity mappings generated despite having results to cache.")
            return None
        
        # Use database session
        session = self.get_cache_session()
        async with session:
            # Add all entity mappings
            await session.add_all(mappings_to_add)
            await session.commit()
            
            print(f"Successfully cached {len(mappings_to_add)} mappings for path {path_id}.")
            return mappings_to_add
    
    # Test both regular path and reversible path
    for is_reversed in [False, True]:
        print(f"\n=== Testing {'Reverse' if is_reversed else 'Forward'} Path ===")
        
        if is_reversed:
            test_path = MockReversiblePath(path, is_reverse=True)
        else:
            test_path = path
            
        # Sample results to cache
        results_to_cache = {
            "source1": {
                "target_identifiers": ["target1", "target2"],
                "confidence_score": None  # Test auto-calculation
            },
            "source2": {
                "target_identifiers": ["target3"],
                "confidence_score": 0.95  # Test provided score
            },
            "source3": {
                "target_identifiers": [],  # Test empty targets (should be skipped)
            }
        }
        
        # Create executor instance
        executor = MockMappingExecutor()
        
        # Call the _cache_results method
        result = await _cache_results(
            executor,
            results_to_cache,
            test_path,
            "ChEBI",
            "PubChem",
            mapping_session_id=1001
        )
        
        # Verify results
        assert executor.session.add_all_calls, "session.add_all was not called"
        assert executor.session.commit_calls > 0, "session.commit was not called"
        
        # Check the mappings that were added
        mappings = executor.session.add_all_calls[0]
        print(f"Mappings count: {len(mappings)}")
        
        # Check that we have 3 mappings (source1->target1, source1->target2, source2->target3)
        assert len(mappings) == 3, f"Expected 3 mappings, got {len(mappings)}"
        
        # Verify metadata for each mapping
        for idx, mapping in enumerate(mappings):
            # Extract path details from JSON for validation
            path_details = json.loads(mapping.mapping_path_details)
            
            print(f"\nMapping {idx+1}:")
            print(f"  Source ID: {mapping.source_id}")
            print(f"  Target ID: {mapping.target_id}")
            print(f"  Confidence Score: {mapping.confidence_score}")
            print(f"  Hop Count: {mapping.hop_count}")
            print(f"  Mapping Direction: {mapping.mapping_direction}")
            print(f"  Path ID from details: {path_details.get('path_id')}")
            
            # Check if metadata fields were populated correctly
            assert mapping.mapping_direction == ("reverse" if is_reversed else "forward"), "Mapping direction incorrect"
            assert mapping.hop_count == 2, "Hop count incorrect"
            assert mapping.confidence_score is not None, "Confidence score not populated"
            assert path_details.get("path_id") == 101, "Path ID incorrect in path details"
            assert path_details.get("hop_count") == 2, "Hop count incorrect in path details"
            assert len(path_details.get("steps", {})) == 2, "Step details missing or incorrect"
        
        print("\n✅ Verification passed!")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_cache_results())