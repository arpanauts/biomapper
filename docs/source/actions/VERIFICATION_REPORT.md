# Documentation Verification Report

## Summary
- **Date**: 2025-08-13
- **Location**: `/home/ubuntu/biomapper/docs/source/actions/`
- **Status**: ❌ Critical issues found

## Issues Found

### 1. Missing Documentation Files (19 files)
The following actions are referenced in `index.rst` but have no corresponding `.rst` files:

- `calculate_mapping_quality.rst`
- `calculate_three_way_overlap.rst`
- `chemistry_extract_loinc.rst`
- `chemistry_fuzzy_test_match.rst`
- `chemistry_vendor_harmonization.rst`
- `custom_transform.rst`
- `export_dataset.rst`
- `filter_dataset.rst`
- `generate_metabolomics_report.rst`
- `merge_datasets.rst`
- `metabolite_cts_bridge.rst`
- `metabolite_extract_identifiers.rst`
- `metabolite_normalize_hmdb.rst`
- `nightingale_nmr_match.rst`
- `protein_extract_uniprot.rst`
- `protein_multi_bridge.rst`
- `protein_normalize_accessions.rst`
- `semantic_metabolite_match.rst`
- `vector_enhanced_match.rst`

### 2. Incorrect Documentation
**File**: `calculate_set_overlap.rst`
- **Issue**: Documentation shows incorrect parameters
- **Documented params**: `dataset_a_key`, `dataset_b_key`, `output_key`
- **Actual params**: `input_key`, `source_name`, `target_name`, `mapping_combo_id`, `confidence_threshold`, `output_dir`, `output_key`

### 3. Undocumented Actions in Code (13 actions)
The following actions exist in the codebase but are not documented:

- `BASELINE_FUZZY_MATCH`
- `BUILD_NIGHTINGALE_REFERENCE`
- `CHEMISTRY_TO_PHENOTYPE_BRIDGE`
- `CHUNK_PROCESSOR`
- `COMBINE_METABOLITE_MATCHES`
- `CTS_ENRICHED_MATCH`
- `CUSTOM_TRANSFORM_EXPRESSION`
- `GENERATE_ENHANCEMENT_REPORT`
- `METABOLITE_API_ENRICHMENT`
- `METABOLITE_MULTI_BRIDGE`
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`
- `SYNC_TO_GOOGLE_DRIVE`
- `SYNC_TO_GOOGLE_DRIVE_V2`

### 4. Action Name Mismatches
Several actions have inconsistent naming between code and documentation:
- Code: `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` → Doc: `protein_extract_uniprot`
- Code: `EXPORT_DATASET_V2` → Doc: `export_dataset`
- Code: `CUSTOM_TRANSFORM_EXPRESSION` → Doc: `custom_transform`

## Statistics
- **Total registered actions in code**: 35
- **Total referenced in index.rst**: 22
- **Documentation files exist**: 3
- **Documentation coverage**: 8.6% (3/35)

## Recommendations

### Immediate Actions Required
1. ✅ Create the 19 missing documentation files
2. ✅ Update `calculate_set_overlap.rst` with correct parameters
3. ✅ Add documentation for the 13 undocumented actions
4. ✅ Fix action name inconsistencies in `index.rst`

### Documentation Standards
Each `.rst` file should include:
- Purpose section
- Complete parameter documentation (required and optional)
- Example usage with YAML
- Output format description
- Error handling guidance
- Integration examples
- Performance notes (if applicable)

### Cross-Reference Issues
The following cross-references in existing docs may be broken:
- `calculate_set_overlap.rst` references `:doc:merge_with_uniprot_resolution` (file exists)
- `calculate_set_overlap.rst` references `:doc:load_dataset_identifiers` (file exists)

## Valid Documentation Files
Only 3 documentation files currently exist and are properly formatted:
1. ✅ `load_dataset_identifiers.rst` - Well documented
2. ✅ `merge_with_uniprot_resolution.rst` - Needs verification
3. ❌ `calculate_set_overlap.rst` - Has incorrect parameters

## Next Steps
1. Generate missing documentation files based on code implementation
2. Update existing documentation to match current code
3. Ensure all action names are consistent across code and docs
4. Add all new actions to `index.rst`
5. Validate all examples work correctly