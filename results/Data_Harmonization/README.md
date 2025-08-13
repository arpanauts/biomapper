# BioMapper Results - Data Harmonization

This directory mirrors the structure of the Google Drive "Data Harmonization" folder.

## Directory Structure

```
Data_Harmonization/
├── strategy_name/                  # Base strategy name (without version suffix)
│   ├── v1_0_0/                     # Version folder
│   │   ├── run_20250812_123456/   # Timestamped run folder
│   │   │   ├── results.tsv        # Output files
│   │   │   ├── results_summary.txt
│   │   │   └── ...
│   │   └── run_20250812_234567/   # Another run
│   └── v2_0_0/                     # New version
│       └── run_20250813_012345/
└── another_strategy/
    └── v1_0_0/
        └── run_20250813_123456/
```

## Organization Rules

1. **Strategy Names**: Base name without version suffixes
   - `metabolite_protein_integration_v2_enhanced` → `metabolite_protein_integration/`
   - `custom_strategy_v1_base` → `custom_strategy/`

2. **Version Folders**: Formatted as `v{major}_{minor}_{patch}`
   - `1.0.0` → `v1_0_0/`
   - `2.1.3-beta` → `v2_1_3-beta/`

3. **Run Folders**: Timestamped for each execution
   - Format: `run_YYYYMMDD_HHMMSS`
   - Example: `run_20250812_143022`

## Synchronization

This local structure is automatically synchronized with Google Drive when using:
- `EXPORT_DATASET_V2` action for local organized exports
- `SYNC_TO_GOOGLE_DRIVE_V2` action for cloud synchronization

Both actions use the same organization pattern to ensure consistency.

## Usage Examples

### In YAML Strategies

```yaml
steps:
  - name: export_organized
    action:
      type: EXPORT_DATASET_V2
      params:
        input_key: my_data
        output_filename: results.tsv
        use_organized_structure: true  # Automatic organization
        
  - name: sync_to_cloud
    action:
      type: SYNC_TO_GOOGLE_DRIVE_V2
      params:
        drive_folder_id: "folder_id_here"
        auto_organize: true  # Matching organization
```

### Programmatically

```python
from biomapper.core.results_manager import LocalResultsOrganizer

organizer = LocalResultsOrganizer()

# Prepare output directory for a strategy
output_path = organizer.prepare_strategy_output(
    strategy_name="my_strategy_v2_enhanced",
    version="2.0.0",
    include_timestamp=True
)

# Get latest run for a strategy
latest = organizer.get_latest_run("my_strategy", "2.0.0")

# List all runs
runs = organizer.list_strategy_runs("my_strategy")

# Clean old runs (keep latest 5)
deleted = organizer.clean_old_runs("my_strategy", "2.0.0", keep_latest=5)
```

## Environment Variables

You can override the base directory using:
- In `.env`: `BIOMAPPER_RESULTS_DIR=/custom/path`
- In YAML: `base_output_dir` parameter

## Notes

- This structure is created automatically when using organized exports
- Old runs can be cleaned up using the `clean_old_runs` utility
- The structure matches exactly with Google Drive for easy comparison
- All paths are logged in the execution context for traceability
