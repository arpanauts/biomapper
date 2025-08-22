# Test Scripts Directory

This directory contains standalone test scripts used for validating specific biomapper functionality. These are separate from the main test suite in `/tests/`.

## ⚠️ Important Note

These scripts were originally in the project root and have been moved here for better organization. They are primarily used for:
- Quick validation of specific features
- Debugging pipeline issues
- Testing integrations
- Reproducing reported problems

## Test Scripts

### Pipeline Testing
- `test_full_pipeline.py` - Complete pipeline execution test
- `test_complete_metabolomics_workflow.py` - Metabolomics workflow validation
- `test_complete_workflow_with_timing.py` - Performance benchmarking
- `test_metabolomics_execution.py` - Metabolomics-specific tests
- `test_metabolomics_simple.py` - Simplified metabolomics tests
- `test_minimal_metabolomics.py` - Minimal test case
- `real_metabolomics_execution_test.py` - Real data validation

### API and Client Testing
- `test_api_direct.py` - Direct API calls
- `test_api_port_8001.py` - API on specific port
- `test_fixed_pipeline_api.py` - Fixed pipeline via API
- `test_fixed_pipeline_direct.py` - Direct pipeline execution

### Integration Testing
- `test_google_drive_auth.py` - Google Drive authentication
- `test_ukbb_pipeline.py` - UK Biobank pipeline
- `test_progressive_pipeline.py` - Progressive mapping strategy

### Framework Testing
- `test_circuitous_context.py` - Circuitous framework context
- `test_circuitous_pipeline.py` - Circuitous pipeline execution
- `test_validation_framework_demo.py` - Validation framework

### Component Testing
- `test_action_interface.py` - Action interface validation
- `test_individual_actions.py` - Individual action tests
- `test_fix_base_class.py` - Base class fixes
- `test_import_error.py` - Import error handling
- `test_backward_compatibility.py` - Backward compatibility checks

### Staging Tests
- `test_simple_stage1.py` - Stage 1 tests
- `test_stage1_direct.py` - Direct stage 1 execution
- `test_stage1_simple.py` - Simplified stage 1
- `test_stages_1_to_3.py` - Multi-stage testing
- `test_stages_1_to_3_fixed.py` - Fixed multi-stage tests

### Other Tests
- `test_condition_evaluation.py` - Condition evaluation logic
- `test_fixed_pipeline.py` - Fixed pipeline tests
- `test_minimal_repro.py` - Minimal reproduction cases
- `test_param_compatibility_simple.py` - Parameter compatibility
- `test_progressive_fix_simple.py` - Progressive fix validation
- `test_real_coverage.py` - Real coverage analysis
- `test_simple_existing.py` - Simple existing functionality
- `test_simple_fix.py` - Simple fix validation
- `test_simple_strategy.py` - Simple strategy tests
- `test_trace_error.py` - Error tracing

## Usage

To run a specific test script:
```bash
cd /home/ubuntu/biomapper
python scripts/test_scripts/test_full_pipeline.py
```

## Note

These scripts may have dependencies on:
- Local file paths
- Environment variables
- API server running on specific ports
- Database connections
- External services (Google Drive, etc.)

Check individual scripts for specific requirements.

## Maintenance

These scripts should be considered temporary validation tools. Well-tested functionality should be moved to the main test suite in `/tests/` with proper pytest integration.