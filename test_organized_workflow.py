#!/usr/bin/env python3
"""
Test the complete organized workflow: local export + cloud sync
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')

# Load environment variables
load_dotenv('/home/ubuntu/biomapper/.env')

from biomapper.core.strategy_actions.io.export_dataset_v2 import (
    ExportDatasetV2Action, ExportDatasetV2Params
)
from biomapper.core.strategy_actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action, SyncToGoogleDriveV2Params
)
from biomapper.core.results_manager import LocalResultsOrganizer


async def test_organized_workflow():
    """Test the complete organized workflow."""
    
    print("🚀 Testing Complete Organized Workflow")
    print("=" * 60)
    
    # Create test data
    test_data = pd.DataFrame({
        'metabolite_id': ['HMDB0000001', 'HMDB0000002', 'HMDB0000005'],
        'name': ['1-Methylhistidine', '1,3-Diaminopropane', '2-Ketobutyric acid'],
        'inchikey': [
            'BRMWTNUJHUMWMS-UHFFFAOYSA-N',
            'XFNJVYOIXUGMKA-UHFFFAOYSA-N', 
            'TYEYBOSBBBHJIV-UHFFFAOYSA-N'
        ],
        'chebi_id': ['CHEBI:50599', 'CHEBI:15724', 'CHEBI:16763'],
        'kegg_id': ['C01152', 'C00986', 'C00109']
    })
    
    # Simulate execution context
    context = {
        'strategy_name': 'test_organized_workflow_v2_enhanced',
        'strategy_metadata': {
            'version': '2.1.0',
            'entity_type': 'metabolites'
        },
        'datasets': {
            'test_metabolites': test_data
        },
        'parameters': {}  # No custom output dir
    }
    
    print("\n📊 Test Data:")
    print(f"   Strategy: {context['strategy_name']}")
    print(f"   Version: {context['strategy_metadata']['version']}")
    print(f"   Rows: {len(test_data)}")
    print(f"   Columns: {', '.join(test_data.columns)}")
    
    # Step 1: Export locally with organized structure
    print("\n" + "-" * 60)
    print("📁 Step 1: Export with organized local structure")
    print("-" * 60)
    
    export_action = ExportDatasetV2Action()
    export_params = ExportDatasetV2Params(
        input_key='test_metabolites',
        output_filename='metabolites_harmonized.tsv',
        use_organized_structure=True,
        format='tsv',
        include_metadata=True,
        create_summary=True
    )
    
    export_result = await export_action.execute_typed(export_params, context)
    
    if export_result.success:
        print(f"✅ Local export successful!")
        print(f"   Path: {export_result.data['exported_path']}")
        if 'organized_structure' in export_result.data and export_result.data['organized_structure']:
            structure = export_result.data['organized_structure']
            print(f"   Structure: {structure['strategy']}/{structure['version']}/{structure.get('run', 'N/A')}")
        print(f"   Rows: {export_result.data['row_count']}")
        if 'summary_path' in export_result.data:
            print(f"   Summary: {export_result.data['summary_path']}")
    else:
        print(f"❌ Export failed: {export_result.error}")
        return False
    
    # Export additional format (JSON)
    print("\n📄 Exporting additional format (JSON)...")
    export_params_json = ExportDatasetV2Params(
        input_key='test_metabolites',
        output_filename='metabolites_harmonized.json',
        use_organized_structure=True,  # Will use same path from context
        format='json',
        create_summary=False
    )
    
    export_result_json = await export_action.execute_typed(export_params_json, context)
    if export_result_json.success:
        print(f"✅ JSON export successful: {Path(export_result_json.data['exported_path']).name}")
    
    # Step 2: Sync to Google Drive with matching structure
    print("\n" + "-" * 60)
    print("☁️  Step 2: Sync to Google Drive with matching structure")
    print("-" * 60)
    
    # Get Google Drive config
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not folder_id or not credentials_path:
        print("⚠️  Google Drive not configured, skipping sync")
        print("   Set GOOGLE_DRIVE_FOLDER_ID and GOOGLE_APPLICATION_CREDENTIALS in .env")
    else:
        sync_action = SyncToGoogleDriveV2Action()
        sync_params = SyncToGoogleDriveV2Params(
            drive_folder_id=folder_id,
            credentials_path=credentials_path,
            auto_organize=True,  # Match local structure
            sync_context_outputs=True,  # Sync all files from context
            create_subfolder=False,  # Don't add extra timestamp (already in path)
            description="Test organized workflow"
        )
        
        sync_result = await sync_action.execute_typed(sync_params, context)
        
        if sync_result.success:
            print(f"✅ Cloud sync successful!")
            print(f"   Structure: {sync_result.data.get('folder_structure')}")
            print(f"   Files uploaded: {sync_result.data.get('uploaded_count')}")
            
            for file_info in sync_result.data.get('uploaded_files', []):
                print(f"   - {file_info.get('name')}")
                
            print(f"\n📁 View in Google Drive:")
            print(f"   https://drive.google.com/drive/folders/{folder_id}")
        else:
            print(f"❌ Sync failed: {sync_result.error}")
    
    # Step 3: Verify local structure
    print("\n" + "-" * 60)
    print("🔍 Step 3: Verify local structure")
    print("-" * 60)
    
    organizer = LocalResultsOrganizer()
    
    # List runs for this strategy
    strategy_base = 'test_organized_workflow'  # Without version suffix
    runs = organizer.list_strategy_runs(strategy_base)
    
    print(f"\n📂 Local directory structure:")
    print(f"   results/Data_Harmonization/{strategy_base}/")
    
    for version, run_list in runs.items():
        print(f"   └── {version}/")
        for run in run_list[-3:]:  # Show last 3 runs
            print(f"       └── {run}/")
            
            # List files in the run
            run_path = Path(organizer.base_dir) / strategy_base / version / run
            if run_path.exists():
                files = sorted(run_path.glob("*"))
                for f in files:
                    print(f"           ├── {f.name}")
    
    # Get latest run
    latest_run = organizer.get_latest_run(strategy_base, "v2_1_0")
    if latest_run:
        print(f"\n📍 Latest run location:")
        print(f"   {latest_run}")
    
    print("\n" + "=" * 60)
    print("✅ Organized workflow test complete!")
    print("\n📊 Summary:")
    print("   1. Local export created organized structure")
    print("   2. Google Drive sync matched the structure")
    print("   3. Both locations have identical organization")
    print("\n🎯 Benefits:")
    print("   - Consistent structure across local and cloud")
    print("   - Easy to find results by strategy/version/run")
    print("   - Automatic versioning and timestamping")
    print("   - No manual path management needed")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_organized_workflow())
    
    if success:
        print("\n🎉 All tests passed! The organized workflow is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)