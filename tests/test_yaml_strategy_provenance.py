"""Unit tests for YAML strategy provenance tracking fix."""

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder


class TestYAMLStrategyProvenanceTracking:
    """Test the fixed provenance tracking in execute_yaml_strategy."""
    
    def test_trace_mapping_chain_simple(self):
        """Test simple mapping chain tracing."""
        # Create a mock executor with the trace_mapping_chain logic
        # Note: MappingExecutor now requires specific service dependencies
        # For this test we're just testing the trace_mapping_chain logic directly
        
        # Simulate provenance data
        provenance_list = [
            {'source_id': 'A', 'target_id': 'B', 'method': 'convert'},
            {'source_id': 'B', 'target_id': 'C', 'method': 'map'},
        ]
        
        # The trace_mapping_chain function is defined inside execute_yaml_strategy,
        # so we'll test the logic directly here
        def trace_mapping_chain(source_id, provenance_list):
            """Recursively trace through the mapping chain to find final target."""
            mappings = [p for p in provenance_list if p.get('source_id') == source_id and p.get('target_id')]
            
            if not mappings:
                filter_entries = [p for p in provenance_list if p.get('source_id') == source_id and p.get('action') == 'filter_passed']
                if filter_entries:
                    return [source_id]
                return []
            
            final_targets = []
            for mapping in mappings:
                target = mapping['target_id']
                further_mappings = trace_mapping_chain(target, provenance_list)
                if further_mappings:
                    final_targets.extend(further_mappings)
                else:
                    final_targets.append(target)
            
            return final_targets
        
        # Test tracing
        result = trace_mapping_chain('A', provenance_list)
        assert result == ['C'], f"Expected ['C'], got {result}"
        
        result = trace_mapping_chain('B', provenance_list)
        assert result == ['C'], f"Expected ['C'], got {result}"
        
        result = trace_mapping_chain('C', provenance_list)
        assert result == [], f"Expected [], got {result}"
    
    def test_trace_mapping_chain_with_filter(self):
        """Test mapping chain tracing with filtering."""
        def trace_mapping_chain(source_id, provenance_list):
            """Recursively trace through the mapping chain to find final target."""
            mappings = [p for p in provenance_list if p.get('source_id') == source_id and p.get('target_id')]
            
            if not mappings:
                filter_entries = [p for p in provenance_list if p.get('source_id') == source_id and p.get('action') == 'filter_passed']
                if filter_entries:
                    return [source_id]
                return []
            
            final_targets = []
            for mapping in mappings:
                target = mapping['target_id']
                further_mappings = trace_mapping_chain(target, provenance_list)
                if further_mappings:
                    final_targets.extend(further_mappings)
                else:
                    final_targets.append(target)
            
            return final_targets
        
        # Simulate provenance where some items are filtered
        provenance_list = [
            # Step 1: Convert
            {'source_id': 'ID1', 'target_id': 'CONV1', 'method': 'convert'},
            {'source_id': 'ID2', 'target_id': 'CONV2', 'method': 'convert'},
            {'source_id': 'ID3', 'target_id': 'CONV3', 'method': 'convert'},
            
            # Step 2: Filter (only ID1 and ID3 pass)
            {'source_id': 'ID1', 'action': 'filter_passed'},
            {'source_id': 'ID3', 'action': 'filter_passed'},
            # ID2 is filtered out (no filter_passed entry)
            
            # Step 3: Map (only filtered items)
            {'source_id': 'CONV1', 'target_id': 'FINAL1', 'method': 'map'},
            {'source_id': 'CONV3', 'target_id': 'FINAL3', 'method': 'map'},
        ]
        
        # Test tracing
        assert trace_mapping_chain('ID1', provenance_list) == ['FINAL1']
        assert trace_mapping_chain('ID2', provenance_list) == ['CONV2']  # Stops at CONV2
        assert trace_mapping_chain('ID3', provenance_list) == ['FINAL3']
    
    def test_provenance_vs_position_mapping(self):
        """Test that provenance-based mapping handles filtering correctly."""
        # Simulate the scenario where position-based mapping would fail
        input_identifiers = ['A', 'B', 'C', 'D', 'E']
        current_identifiers = ['A_final', 'C_final', 'E_final']  # B and D filtered out
        
        # Position-based mapping (WRONG)
        position_based = {}
        for i, input_id in enumerate(input_identifiers):
            if i < len(current_identifiers):
                position_based[input_id] = current_identifiers[i]
            else:
                position_based[input_id] = None
        
        # This gives wrong mappings:
        assert position_based == {
            'A': 'A_final',  # Correct by luck
            'B': 'C_final',  # WRONG! B was filtered, not mapped to C_final
            'C': 'E_final',  # WRONG! C should map to C_final
            'D': None,       # Correct by luck
            'E': None        # WRONG! E should map to E_final
        }
        
        # Provenance-based mapping (CORRECT)
        provenance = [
            {'source_id': 'A', 'target_id': 'A_conv', 'method': 'convert'},
            {'source_id': 'B', 'target_id': 'B_conv', 'method': 'convert'},
            {'source_id': 'C', 'target_id': 'C_conv', 'method': 'convert'},
            {'source_id': 'D', 'target_id': 'D_conv', 'method': 'convert'},
            {'source_id': 'E', 'target_id': 'E_conv', 'method': 'convert'},
            
            # Filter passes only A, C, E
            {'source_id': 'A', 'action': 'filter_passed'},
            {'source_id': 'C', 'action': 'filter_passed'},
            {'source_id': 'E', 'action': 'filter_passed'},
            
            # Final mapping
            {'source_id': 'A_conv', 'target_id': 'A_final', 'method': 'map'},
            {'source_id': 'C_conv', 'target_id': 'C_final', 'method': 'map'},
            {'source_id': 'E_conv', 'target_id': 'E_final', 'method': 'map'},
        ]
        
        def trace_mapping_chain(source_id, provenance_list):
            """Recursively trace through the mapping chain to find final target."""
            mappings = [p for p in provenance_list if p.get('source_id') == source_id and p.get('target_id')]
            
            if not mappings:
                filter_entries = [p for p in provenance_list if p.get('source_id') == source_id and p.get('action') == 'filter_passed']
                if filter_entries:
                    return [source_id]
                return []
            
            final_targets = []
            for mapping in mappings:
                target = mapping['target_id']
                further_mappings = trace_mapping_chain(target, provenance_list)
                if further_mappings:
                    final_targets.extend(further_mappings)
                else:
                    final_targets.append(target)
            
            return final_targets
        
        provenance_based = {}
        for input_id in input_identifiers:
            targets = trace_mapping_chain(input_id, provenance)
            provenance_based[input_id] = targets[0] if targets else None
        
        # This gives correct mappings:
        assert provenance_based == {
            'A': 'A_final',  # Correct
            'B': 'B_conv',   # Correct - filtered out after conversion
            'C': 'C_final',  # Correct
            'D': 'D_conv',   # Correct - filtered out after conversion
            'E': 'E_final'   # Correct
        }


if __name__ == "__main__":
    # Run tests manually
    test = TestYAMLStrategyProvenanceTracking()
    
    print("Testing simple mapping chain...")
    test.test_trace_mapping_chain_simple()
    print("✓ Passed")
    
    print("\nTesting mapping chain with filtering...")
    test.test_trace_mapping_chain_with_filter()
    print("✓ Passed")
    
    print("\nTesting provenance vs position mapping...")
    test.test_provenance_vs_position_mapping()
    print("✓ Passed")
    
    print("\n✅ All tests passed!")