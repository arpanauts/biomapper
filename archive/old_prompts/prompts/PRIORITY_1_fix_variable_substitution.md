# PRIORITY 1: Fix MinimalStrategyService Variable Substitution

**CRITICAL: This must be completed FIRST as it blocks all other work**

## Problem Statement

All 26 strategies in `/home/ubuntu/biomapper/configs/strategies/experimental/` are failing with 0% success rate because `${metadata.source_files[0].path}` references are not being resolved. The root cause is in `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py` at line 50-81 where `_substitute_parameters()` only passes `parameters` to Jinja2, not `metadata`.

## Objective

Fix the variable substitution mechanism to properly resolve both `${parameters.*}` and `${metadata.*}` references in strategy YAML files, enabling strategies to execute successfully.

## Current State Analysis

### Files to Review
1. `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py` - Contains broken `_substitute_parameters` method
2. `/home/ubuntu/biomapper/biomapper/core/infrastructure/parameter_resolver.py` - Contains working `ParameterResolver` class that handles metadata
3. `/home/ubuntu/biomapper/configs/strategies/experimental/chem_arv_to_kg2c_phenotypes_v1_base.yaml` - Example strategy with `${metadata.source_files[0].path}` references

### Current Bug Location
```python
# File: /home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py
# Lines: 50-81
def _substitute_parameters(self, obj: Any, parameters: Dict[str, Any]) -> Any:
    # BUG: Only passes 'parameters' to template.render(), not 'metadata'
    template_str = re.sub(r"\$\{([^}]+)\}", r"{{ \1 }}", obj)
    template = Template(template_str)
    return template.render(parameters=parameters)  # <-- Missing metadata here
```

## Task Requirements

### Option A: Integrate Existing ParameterResolver (PREFERRED)

1. **Import ParameterResolver**
   ```python
   from biomapper.core.infrastructure.parameter_resolver import ParameterResolver
   ```

2. **Initialize in MinimalStrategyService.__init__**
   ```python
   self.parameter_resolver = ParameterResolver()
   ```

3. **Replace manual substitution in execute_strategy method**
   - Find where `_substitute_parameters` is called (around line 354)
   - Replace with `parameter_resolver.resolve_strategy_parameters()`

4. **Handle backward compatibility**
   - Ensure existing strategies still work
   - Test with both `${parameters.*}` and `${metadata.*}` patterns

### Option B: Extend Current Method (FALLBACK)

1. **Modify _substitute_parameters signature**
   ```python
   def _substitute_parameters(self, obj: Any, parameters: Dict[str, Any], 
                            metadata: Optional[Dict[str, Any]] = None) -> Any:
   ```

2. **Update template rendering**
   ```python
   context = {"parameters": parameters}
   if metadata:
       context["metadata"] = metadata
   return template.render(**context)
   ```

3. **Update all call sites**
   - Line ~354: Pass metadata from strategy_config
   - Any other locations calling this method

## Test-Driven Development Requirements

### 1. Write Unit Tests FIRST

Create `/home/ubuntu/biomapper/tests/unit/core/test_minimal_strategy_service_fix.py`:

```python
import pytest
from biomapper.core.minimal_strategy_service import MinimalStrategyService

class TestVariableSubstitution:
    def test_resolves_parameter_references(self):
        """Test that ${parameters.key} references are resolved"""
        service = MinimalStrategyService()
        input_str = "File path: ${parameters.data_file}"
        parameters = {"data_file": "/tmp/test.csv"}
        result = service._substitute_parameters(input_str, parameters)
        assert result == "File path: /tmp/test.csv"
    
    def test_resolves_metadata_references(self):
        """Test that ${metadata.source_files[0].path} references are resolved"""
        service = MinimalStrategyService()
        input_str = "Source: ${metadata.source_files[0].path}"
        parameters = {}
        metadata = {"source_files": [{"path": "/data/real_file.tsv"}]}
        # This test should FAIL initially, then pass after fix
        result = service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Source: /data/real_file.tsv"
    
    def test_resolves_nested_metadata(self):
        """Test nested metadata access like ${metadata.source_files[1].last_updated}"""
        service = MinimalStrategyService()
        input_str = "Updated: ${metadata.source_files[1].last_updated}"
        parameters = {}
        metadata = {
            "source_files": [
                {"path": "/file1.csv", "last_updated": "2024-01-01"},
                {"path": "/file2.csv", "last_updated": "2024-06-15"}
            ]
        }
        result = service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Updated: 2024-06-15"
    
    def test_handles_missing_metadata_gracefully(self):
        """Test that missing metadata doesn't crash"""
        service = MinimalStrategyService()
        input_str = "Path: ${metadata.nonexistent.path}"
        parameters = {}
        metadata = {}
        result = service._substitute_parameters(input_str, parameters, metadata)
        # Should either return original or empty string, not crash
        assert "${metadata.nonexistent.path}" in result or result == "Path: "
    
    def test_mixed_parameter_and_metadata_references(self):
        """Test templates with both parameter and metadata references"""
        service = MinimalStrategyService()
        input_str = "Load ${parameters.dataset} from ${metadata.source_files[0].path}"
        parameters = {"dataset": "proteins"}
        metadata = {"source_files": [{"path": "/data/proteins.csv"}]}
        result = service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Load proteins from /data/proteins.csv"
```

Run tests to confirm they fail:
```bash
cd /home/ubuntu/biomapper
poetry run pytest tests/unit/core/test_minimal_strategy_service_fix.py -xvs
```

### 2. Implement the Fix

Choose Option A or B and implement. Document your choice and reasoning.

### 3. Verify Unit Tests Pass

```bash
poetry run pytest tests/unit/core/test_minimal_strategy_service_fix.py -xvs
```

### 4. Integration Test with Real Strategy

Test with the simplest real strategy that uses metadata references:

```python
# Create integration test script
cat > /tmp/test_strategy_execution.py << 'EOF'
import asyncio
from biomapper.core.minimal_strategy_service import MinimalStrategyService
from pathlib import Path

async def test_real_strategy():
    service = MinimalStrategyService()
    
    # Load a real strategy that uses ${metadata.source_files[0].path}
    strategy_path = Path("/home/ubuntu/biomapper/configs/strategies/experimental/chem_arv_to_kg2c_phenotypes_v1_base.yaml")
    
    # Create minimal test data file
    test_data = Path("/tmp/test_chemistry.tsv")
    test_data.write_text("Name\tLOINC\nGlucose\t2345-7\n")
    
    # Create symlink if needed for expected path
    import subprocess
    subprocess.run("sudo mkdir -p /procedure/data/local_data/MAPPING_ONTOLOGIES/arivale", shell=True)
    subprocess.run(f"sudo ln -sf {test_data} /procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv", shell=True)
    
    try:
        # This should work after the fix
        result = await service.execute_strategy("chem_arv_to_kg2c_phenotypes_v1_base", {})
        print(f"SUCCESS: Strategy executed without variable substitution errors")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        return True
    except Exception as e:
        if "${metadata" in str(e):
            print(f"FAILED: Variable substitution still not working: {e}")
            return False
        else:
            print(f"Different error (progress!): {e}")
            return None

if __name__ == "__main__":
    success = asyncio.run(test_real_strategy())
    exit(0 if success else 1)
EOF

python /tmp/test_strategy_execution.py
```

## Success Criteria

1. ✅ All unit tests pass
2. ✅ At least one real strategy executes without `${metadata.*}` substitution errors
3. ✅ Backward compatibility maintained (existing tests still pass)
4. ✅ Code changes are minimal and well-documented
5. ✅ No performance degradation

## Verification Steps

1. **Run existing tests to ensure no regression**
   ```bash
   poetry run pytest tests/unit/core/ -k strategy
   ```

2. **Test with multiple strategies**
   ```bash
   # Start API server
   cd /home/ubuntu/biomapper/biomapper-api
   poetry run uvicorn app.main:app --reload --port 8001 &
   
   # Test different strategy types
   curl -X POST "http://localhost:8001/api/v1/strategies/execute" \
     -H "Content-Type: application/json" \
     -d '{"strategy_name": "chem_arv_to_kg2c_phenotypes_v1_base"}'
   ```

3. **Check that both old and new patterns work**
   - Test strategy with `${parameters.output_dir}` (should still work)
   - Test strategy with `${metadata.source_files[0].path}` (should now work)

## Documentation Requirements

1. **Update code comments**
   - Document why the change was needed
   - Explain the chosen solution
   - Add examples of supported patterns

2. **Update CLAUDE.md**
   - Add note about variable substitution patterns
   - Document that both `${parameters.*}` and `${metadata.*}` are supported

3. **Create changelog entry**
   ```markdown
   ## Fixed
   - Variable substitution now correctly resolves ${metadata.*} references in strategy YAML files
   - This fixes the 0% success rate issue affecting all 26 experimental strategies
   ```

## Deliverables

1. Modified `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py` with fix
2. New test file `/home/ubuntu/biomapper/tests/unit/core/test_minimal_strategy_service_fix.py`
3. Documentation updates to CLAUDE.md
4. Test execution logs showing at least one strategy working
5. Brief report summarizing:
   - Which solution (A or B) was chosen and why
   - Any challenges encountered
   - Confirmation that backward compatibility is maintained
   - Next steps recommendations

## Time Estimate

- Writing tests: 30 minutes
- Implementing fix: 30-60 minutes (depending on chosen solution)
- Testing and verification: 30 minutes
- Documentation: 15 minutes
- **Total: 2-2.5 hours**

## Notes

- This is THE MOST CRITICAL fix - nothing else can proceed until this is done
- If Option A (ParameterResolver) has issues, fall back to Option B
- Focus on getting it working first, optimization can come later
- Test with real strategies, not just unit tests
- Preserve all existing functionality