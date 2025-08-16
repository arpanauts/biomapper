#!/usr/bin/env python3
"""Debug script to find rows with UniProt IDs and test extraction"""

import pandas as pd
import asyncio
from biomapper.core.strategy_actions.entities.proteins.annotation.extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction,
    ExtractUniProtFromXrefsParams
)

async def main():
    # Load kg2c data and find rows with UniProtKB references
    kg2c_df = pd.read_csv(
        "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv"
    )
    
    # Find rows with UniProtKB in xrefs
    uniprot_mask = kg2c_df['xrefs'].str.contains('UniProtKB:', na=False)
    rows_with_uniprot = kg2c_df[uniprot_mask].head(5)
    
    print(f"Total rows in kg2c: {len(kg2c_df)}")
    print(f"Rows with UniProtKB: {uniprot_mask.sum()}")
    print(f"\nSample rows with UniProtKB:")
    for idx, row in rows_with_uniprot.iterrows():
        print(f"  ID: {row['id']}, xrefs: {row['xrefs'][:100]}...")
    
    # Create a test context with rows that have UniProt IDs
    context = {
        "datasets": {
            "kg2c_test": rows_with_uniprot.to_dict("records")
        },
        "statistics": {}
    }
    
    # Test extraction with default parameters (creates 'uniprot_id' column)
    action = ProteinExtractUniProtFromXrefsAction()
    params_default = ExtractUniProtFromXrefsParams(
        input_key="kg2c_test",
        xrefs_column="xrefs",
        output_key="kg2c_extracted_default",
        drop_na=False  # Keep all rows to see what happens
    )
    
    result_default = await action.execute_typed(params_default, context)
    print(f"\n=== Test 1: Default output_column ===")
    print(f"Result: {result_default.success}")
    print(f"Message: {result_default.message}")
    
    if "kg2c_extracted_default" in context["datasets"]:
        df_default = pd.DataFrame(context["datasets"]["kg2c_extracted_default"])
        print(f"Columns: {df_default.columns.tolist()}")
        if 'uniprot_id' in df_default.columns:
            print(f"Sample uniprot_id values:")
            for val in df_default['uniprot_id'].head(3):
                print(f"  {val}")
    
    # Test extraction with custom output_column='extracted_uniprot'
    params_custom = ExtractUniProtFromXrefsParams(
        input_key="kg2c_test",
        xrefs_column="xrefs",
        output_key="kg2c_extracted_custom",
        output_column="extracted_uniprot",  # Custom column name
        drop_na=False
    )
    
    result_custom = await action.execute_typed(params_custom, context)
    print(f"\n=== Test 2: Custom output_column='extracted_uniprot' ===")
    print(f"Result: {result_custom.success}")
    print(f"Message: {result_custom.message}")
    
    if "kg2c_extracted_custom" in context["datasets"]:
        df_custom = pd.DataFrame(context["datasets"]["kg2c_extracted_custom"])
        print(f"Columns: {df_custom.columns.tolist()}")
        if 'extracted_uniprot' in df_custom.columns:
            print(f"Sample extracted_uniprot values:")
            for val in df_custom['extracted_uniprot'].head(3):
                print(f"  {val}")

if __name__ == "__main__":
    asyncio.run(main())