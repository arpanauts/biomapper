#!/usr/bin/env python3
"""
Test the Google Drive sync action directly
"""
import asyncio
from biomapper.core.strategy_actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action, 
    SyncToGoogleDriveV2Params
)

async def test_sync():
    print("Testing Google Drive sync action...")
    
    # Create action
    action = SyncToGoogleDriveV2Action()
    
    # Create params
    params = SyncToGoogleDriveV2Params(
        drive_folder_id="1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D",
        local_directory="/tmp/biomapper_results",
        include_patterns=["*.csv"],
        strategy_name="test_sync",
        auto_organize=True
    )
    
    # Create mock context
    context = {
        "output_files": {
            "protein_mapping": "/tmp/biomapper_results/protein_mapping_results.csv"
        }
    }
    
    # Execute
    result = await action.execute_typed(
        current_identifiers=[],
        current_ontology_type="protein",
        params=params,
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    print(f"\nResult: {result.success}")
    if result.success:
        print(f"Data: {result.data}")
    else:
        print(f"Error: {result.error}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_sync())