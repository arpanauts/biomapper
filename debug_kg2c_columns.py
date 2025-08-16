#!/usr/bin/env python3
"""Debug script to check what columns are created by extract_uniprot_from_xrefs"""

import pandas as pd
import asyncio
from biomapper.core.strategy_actions.entities.proteins.annotation.extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction,
    ExtractUniProtFromXrefsParams
)

async def main():
    # Load sample kg2c data
    kg2c_df = pd.read_csv(
        "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv",
        nrows=10
    )
    
    print("KG2C columns:", kg2c_df.columns.tolist())
    print("\nSample xrefs values:")
    print(kg2c_df['xrefs'].head(3))
    
    # Create a test context
    context = {
        "datasets": {
            "kg2c_raw": kg2c_df.to_dict("records")
        },
        "statistics": {}
    }
    
    # Create and execute the action with default params
    action = ProteinExtractUniProtFromXrefsAction()
    params = ExtractUniProtFromXrefsParams(
        input_key="kg2c_raw",
        xrefs_column="xrefs",
        output_key="kg2c_with_uniprot"
        # Note: NOT specifying output_column, so it uses default "uniprot_id"
    )
    
    result = await action.execute_typed(params, context)
    
    print(f"\nAction result: {result.success}")
    print(f"Message: {result.message}")
    
    # Check what columns are in the output
    if "kg2c_with_uniprot" in context["datasets"]:
        output_df = pd.DataFrame(context["datasets"]["kg2c_with_uniprot"])
        print(f"\nOutput columns: {output_df.columns.tolist()}")
        print(f"\nColumn 'uniprot_id' exists: {'uniprot_id' in output_df.columns}")
        print(f"Column 'extracted_uniprot' exists: {'extracted_uniprot' in output_df.columns}")
        
        if 'uniprot_id' in output_df.columns:
            print(f"\nSample uniprot_id values:")
            print(output_df['uniprot_id'].head(3))

if __name__ == "__main__":
    asyncio.run(main())