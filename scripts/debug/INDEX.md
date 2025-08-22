# Debug Scripts Directory

This directory contains debugging and diagnostic scripts used during development and troubleshooting.

## ⚠️ Important Note

These scripts were originally in the project root and have been moved here for better organization. They are temporary debugging tools and should not be considered part of the production codebase.

## Debug Scripts

### Client and API Debugging
- `debug_client_execution.py` - Debug biomapper client execution issues
- `debug_job_results.py` - Analyze job execution results

### Direct Execution Scripts
- `direct_metabolomics_execution.py` - Direct metabolomics pipeline execution for debugging

### Demo Scripts
- `demo_oauth2_drive_sync.py` - Demonstrate OAuth2 Google Drive synchronization

### Validation Tools
- `validation_report.py` - Generate validation reports for debugging

## Usage

These scripts are intended for debugging specific issues:

```bash
cd /home/ubuntu/biomapper
python scripts/debug/debug_client_execution.py
```

## Common Use Cases

1. **Client Issues**: Use `debug_client_execution.py` to trace client-server communication
2. **Job Failures**: Use `debug_job_results.py` to analyze why jobs are failing
3. **Direct Testing**: Use `direct_metabolomics_execution.py` to bypass the API layer
4. **OAuth Issues**: Use `demo_oauth2_drive_sync.py` to test Google Drive integration

## Dependencies

These scripts may require:
- Running API server
- Database access
- Environment variables configured
- Google credentials (for OAuth scripts)

## Maintenance

These are temporary debugging tools. Once issues are resolved:
1. Document the findings
2. Add proper tests to the test suite
3. Consider removing or archiving the debug script

## Note

Debug scripts often contain:
- Hard-coded paths
- Verbose logging
- Experimental code
- Direct database access

They should never be used in production environments.