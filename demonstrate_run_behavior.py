#!/usr/bin/env python3
"""
Demonstrate how multiple runs of the same strategy are handled.
"""
import time
from pathlib import Path
from biomapper.core.results_manager import LocalResultsOrganizer

def demonstrate_multiple_runs():
    """Show what happens when running the same strategy multiple times."""
    
    print("🔄 Demonstrating Multiple Runs of Same Strategy")
    print("=" * 60)
    
    organizer = LocalResultsOrganizer()
    strategy_name = "demo_multiple_runs_v2_enhanced"
    version = "2.0.0"
    
    print(f"\nStrategy: {strategy_name}")
    print(f"Version: {version}")
    print(f"Base name extracted: {organizer.path_manager.extract_strategy_base(strategy_name)}")
    
    # Create 3 runs with slight delays
    print("\n📂 Creating 3 runs of the same strategy:")
    print("-" * 40)
    
    run_paths = []
    for i in range(1, 4):
        print(f"\nRun {i}:")
        
        # Create a new run
        run_path = organizer.prepare_strategy_output(
            strategy_name=strategy_name,
            version=version,
            include_timestamp=True  # Each run gets unique timestamp
        )
        run_paths.append(run_path)
        
        # Create some dummy files
        (run_path / f"results_run{i}.tsv").write_text(f"id,value\n1,run_{i}\n")
        (run_path / f"summary_run{i}.txt").write_text(f"Summary for run {i}")
        
        print(f"  ✅ Created: {run_path.name}")
        print(f"  📁 Full path: {run_path}")
        
        # Small delay to ensure different timestamps
        time.sleep(1)
    
    # Show the directory structure
    print("\n🌳 Directory Structure After 3 Runs:")
    print("-" * 40)
    
    base_strategy = organizer.path_manager.extract_strategy_base(strategy_name)
    strategy_dir = Path(organizer.base_dir) / base_strategy / f"v{version.replace('.', '_')}"
    
    if strategy_dir.exists():
        runs = sorted([d for d in strategy_dir.iterdir() if d.is_dir()])
        print(f"\n📁 {base_strategy}/")
        print(f"└── v{version.replace('.', '_')}/")
        for run in runs:
            print(f"    ├── {run.name}/")
            files = sorted(run.glob("*"))
            for f in files[:3]:  # Show first 3 files
                print(f"    │   ├── {f.name}")
    
    # Show how to get the latest run
    print("\n🔍 Accessing Runs:")
    print("-" * 40)
    
    latest = organizer.get_latest_run(base_strategy, f"v{version.replace('.', '_')}")
    if latest:
        print(f"Latest run: {latest.name}")
        print(f"  Files: {', '.join(f.name for f in latest.glob('*'))}")
    
    # List all runs
    all_runs = organizer.list_strategy_runs(base_strategy)
    for ver, run_list in all_runs.items():
        print(f"\nVersion {ver}: {len(run_list)} total runs")
        for run in run_list:
            print(f"  - {run}")
    
    print("\n" + "=" * 60)
    print("💡 Key Points:")
    print("-" * 40)
    print("✅ Each run creates a NEW timestamped folder")
    print("✅ NO overwrites - all runs are preserved")
    print("✅ Easy to find latest run with get_latest_run()")
    print("✅ Can list all historical runs")
    print("✅ Same behavior for Google Drive sync")
    
    print("\n🧹 Cleanup Options:")
    print("-" * 40)
    print("• Keep all runs for full history")
    print("• Use clean_old_runs() to keep only N latest")
    print("• Manually delete old runs as needed")
    print("• Archive old runs to cold storage")
    
    # Demonstrate cleanup
    print("\n🗑️  Demonstrating Cleanup (keeping latest 2):")
    deleted = organizer.clean_old_runs(base_strategy, f"v{version.replace('.', '_')}", keep_latest=2)
    print(f"Deleted {deleted} old run(s)")
    
    # Show structure after cleanup
    remaining = organizer.list_strategy_runs(base_strategy)
    for ver, run_list in remaining.items():
        print(f"Remaining in {ver}: {len(run_list)} runs")
    
    return run_paths


if __name__ == "__main__":
    demonstrate_multiple_runs()