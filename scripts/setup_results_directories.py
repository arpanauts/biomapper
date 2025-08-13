#!/usr/bin/env python3
"""
Setup script to create organized results directory structure.
Mirrors the Google Drive "Data Harmonization" folder structure locally.
"""
import os
import sys
from pathlib import Path

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')

from biomapper.core.results_manager import ResultsPathManager, LocalResultsOrganizer


def setup_results_structure():
    """Create the base results directory structure."""
    
    print("🏗️  Setting up organized results directory structure")
    print("=" * 60)
    
    # Create base directories
    base_dir = Path(ResultsPathManager.LOCAL_RESULTS_BASE)
    
    print(f"\n📁 Creating base directory structure:")
    print(f"   {base_dir}")
    
    # Create main directories
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create README to explain the structure
    readme_path = base_dir / "README.md"
    readme_content = """# BioMapper Results - Data Harmonization

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
"""
    
    if not readme_path.exists():
        readme_path.write_text(readme_content)
        print(f"   ✅ Created README.md")
    else:
        print(f"   ℹ️  README.md already exists")
    
    # Create example structure for demonstration
    print(f"\n📂 Creating example directory structure:")
    
    organizer = LocalResultsOrganizer(base_dir=str(base_dir))
    
    # Example 1: Metabolite strategy
    example_path1 = organizer.prepare_strategy_output(
        strategy_name="metabolite_harmonization_example",
        version="1.0.0",
        include_timestamp=False  # Just create version folder
    )
    print(f"   ✅ {example_path1.relative_to(base_dir.parent.parent)}")
    
    # Example 2: Protein strategy with multiple versions
    for version in ["1.0.0", "1.1.0", "2.0.0"]:
        example_path2 = organizer.prepare_strategy_output(
            strategy_name="protein_mapping_example",
            version=version,
            include_timestamp=False
        )
        print(f"   ✅ {example_path2.relative_to(base_dir.parent.parent)}")
    
    # Create .gitignore to exclude results but keep structure
    gitignore_path = base_dir / ".gitignore"
    gitignore_content = """# Ignore all result files but keep directory structure
*
!.gitignore
!README.md
!*/
"""
    gitignore_path.write_text(gitignore_content)
    print(f"   ✅ Created .gitignore")
    
    print(f"\n✨ Results directory structure setup complete!")
    print(f"\n📍 Location: {base_dir}")
    print(f"📊 This structure will be used by:")
    print(f"   - EXPORT_DATASET_V2 action (local organized exports)")
    print(f"   - SYNC_TO_GOOGLE_DRIVE_V2 action (cloud synchronization)")
    
    # Show current structure
    print(f"\n🌳 Current structure:")
    for item in sorted(base_dir.rglob("*")):
        if item.is_dir():
            level = len(item.relative_to(base_dir).parts)
            indent = "   " * level
            print(f"   {indent}📁 {item.name}/")
    
    return base_dir


def demonstrate_usage():
    """Demonstrate how to use the organized structure."""
    
    print("\n" + "=" * 60)
    print("📚 Usage Examples")
    print("=" * 60)
    
    organizer = LocalResultsOrganizer()
    
    # Example: Create a run directory
    print("\n1️⃣ Creating a new run directory:")
    run_path = organizer.prepare_strategy_output(
        strategy_name="demo_strategy_v1_base",  # Will extract "demo_strategy"
        version="1.0.0",
        include_timestamp=True
    )
    print(f"   Created: {run_path}")
    
    # Create a dummy file
    dummy_file = run_path / "demo_results.tsv"
    dummy_file.write_text("id\tname\tvalue\n1\ttest\t100\n")
    print(f"   Added file: {dummy_file.name}")
    
    # Example: Get latest run
    print("\n2️⃣ Getting latest run:")
    latest = organizer.get_latest_run("demo_strategy", "1.0.0")
    if latest:
        print(f"   Latest run: {latest}")
        files = list(latest.glob("*"))
        if files:
            print(f"   Contains: {', '.join(f.name for f in files)}")
    
    # Example: List all runs
    print("\n3️⃣ Listing all runs for a strategy:")
    runs = organizer.list_strategy_runs("demo_strategy")
    for version, run_list in runs.items():
        print(f"   Version {version}: {len(run_list)} run(s)")
        for run in run_list[:3]:  # Show first 3
            print(f"      - {run}")
    
    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    # Setup the structure
    base_dir = setup_results_structure()
    
    # Demonstrate usage
    demonstrate_usage()
    
    print("\n🎉 Setup complete! The organized results structure is ready to use.")
    print("\n💡 Next steps:")
    print("   1. Use EXPORT_DATASET_V2 in your strategies for organized local exports")
    print("   2. Use SYNC_TO_GOOGLE_DRIVE_V2 for matching cloud synchronization")
    print("   3. Both will automatically use the same structure")
    print(f"\n📁 Results will be stored in: {base_dir}")