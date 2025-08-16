#!/usr/bin/env python3
"""Check if target_xref_column is actually being used"""

from pydantic import BaseModel, Field
from typing import Optional

# Simulate the params class
class MergeWithUniprotResolutionParams(BaseModel):
    source_dataset_key: str
    target_dataset_key: str
    source_id_column: str
    target_id_column: str
    output_key: str
    composite_separator: str = "||"
    confidence_threshold: float = 0.6
    use_api: bool = False
    # Is target_xref_column actually defined?
    target_xref_column: Optional[str] = None

# Test what production would pass
test_params = {
    "source_dataset_key": "source_proteins",
    "target_dataset_key": "target_proteins",
    "source_id_column": "uniprot",
    "target_id_column": "id",
    "target_xref_column": "xrefs",  # This should be set
    "output_key": "merged_proteins",
    "composite_separator": "||",
    "confidence_threshold": 0.6,
    "use_api": False
}

# Create params object
params = MergeWithUniprotResolutionParams(**test_params)

print("PARAMS CHECK:")
print("=" * 80)

# Check if hasattr works
print(f"hasattr(params, 'target_xref_column'): {hasattr(params, 'target_xref_column')}")
print(f"params.target_xref_column: {params.target_xref_column}")
print(f"bool(params.target_xref_column): {bool(params.target_xref_column)}")

# This is the exact check from production
if hasattr(params, 'target_xref_column') and params.target_xref_column:
    print("\n✅ Would extract from xrefs!")
else:
    print("\n❌ Would NOT extract from xrefs!")

# Check what happens if target_xref_column is not in the params
print("\n" + "=" * 80)
print("WITHOUT target_xref_column:")

test_params_no_xref = {
    "source_dataset_key": "source_proteins",
    "target_dataset_key": "target_proteins",
    "source_id_column": "uniprot",
    "target_id_column": "id",
    # NO target_xref_column!
    "output_key": "merged_proteins",
    "composite_separator": "||",
    "confidence_threshold": 0.6,
    "use_api": False
}

params_no_xref = MergeWithUniprotResolutionParams(**test_params_no_xref)

print(f"hasattr(params_no_xref, 'target_xref_column'): {hasattr(params_no_xref, 'target_xref_column')}")
print(f"params_no_xref.target_xref_column: {params_no_xref.target_xref_column}")

if hasattr(params_no_xref, 'target_xref_column') and params_no_xref.target_xref_column:
    print("\n✅ Would extract from xrefs!")
else:
    print("\n❌ Would NOT extract from xrefs!")