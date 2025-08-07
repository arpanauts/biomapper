# Mapping Strategy Action Sequences

## Entity-Specific Action Types Summary

### Protein-Specific Actions
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from compound xrefs
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize UniProt formats
- `PROTEIN_MULTI_BRIDGE` - Try UniProt → Gene → Ensembl bridges

### Metabolite-Specific Actions
- `METABOLITE_EXTRACT_IDENTIFIERS` - Extract HMDB, InChIKey, CHEBI, etc.
- `METABOLITE_NORMALIZE_HMDB` - Pad HMDB IDs, handle versions
- `METABOLITE_CTS_BRIDGE` - Chemical Translation Service lookup
- `METABOLITE_MULTI_BRIDGE` - Try multiple metabolite ID bridges
- `NIGHTINGALE_NMR_MATCH` - Specialized NMR biomarker matching

### Chemistry-Specific Actions
- `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes from various formats
- `CHEMISTRY_VENDOR_HARMONIZATION` - Handle LabCorp vs Quest differences
- `CHEMISTRY_FUZZY_TEST_MATCH` - Primary matching via test names

### Shared Actions (Generic)
- `LOAD_DATASET` - Load source/target files
- `FILTER_DATASET` - Quality filtering
- `MERGE_DATASETS` - Combine multiple sources
- `CALCULATE_SET_OVERLAP` - Analyze mapping success
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset analysis
- `EXPORT_DATASET` - Save results

---

## Typical Action Sequences by Entity Type

### Protein Mappings (6 strategies)
**Standard Sequence:**
```
1. LOAD_DATASET (source)
2. LOAD_DATASET (target with xrefs)
3. PROTEIN_EXTRACT_UNIPROT_FROM_XREFS (from target xrefs)
4. PROTEIN_NORMALIZE_ACCESSIONS (both datasets)
5. FILTER_DATASET (quality control)
6. PROTEIN_MULTI_BRIDGE (match)
7. CALCULATE_SET_OVERLAP
8. EXPORT_DATASET
```

### Metabolite Mappings (10 strategies)
**Standard Sequence:**
```
1. LOAD_DATASET (source)
2. LOAD_DATASET (target)
3. METABOLITE_EXTRACT_IDENTIFIERS (both)
4. METABOLITE_NORMALIZE_HMDB
5. METABOLITE_CTS_BRIDGE or METABOLITE_MULTI_BRIDGE
6. CALCULATE_SET_OVERLAP
7. EXPORT_DATASET
```

**NMR Variant (for UKBB):**
```
1. LOAD_DATASET (source NMR)
2. LOAD_DATASET (target)
3. METABOLITE_EXTRACT_IDENTIFIERS
4. NIGHTINGALE_NMR_MATCH (specialized)
5. METABOLITE_NORMALIZE_HMDB
6. METABOLITE_CTS_BRIDGE (if needed)
7. CALCULATE_SET_OVERLAP
8. EXPORT_DATASET
```

### Chemistry Mappings (5 strategies)
**Standard Sequence:**
```
1. LOAD_DATASET (source)
2. LOAD_DATASET (target)
3. CHEMISTRY_EXTRACT_LOINC (both)
4. CHEMISTRY_VENDOR_HARMONIZATION
5. CHEMISTRY_FUZZY_TEST_MATCH (primary matching)
6. CALCULATE_SET_OVERLAP
7. EXPORT_DATASET
```

---

## Key Observations

1. **Extract Step is Critical**: Every mapping needs extraction from compound fields
   - Proteins: Extract from xrefs (UniProtKB:P12345|RefSeq:...)
   - Metabolites: Extract from xrefs and synonyms
   - Chemistry: Extract LOINC from various formats

2. **Normalization is Universal**: All entities need format standardization
   - Proteins: Case, versions, isoforms
   - Metabolites: HMDB padding, InChIKey format
   - Chemistry: LOINC variations, vendor differences

3. **Matching Strategies Differ**:
   - Proteins: Multi-bridge with UniProt primary
   - Metabolites: CTS or multi-bridge depending on source
   - Chemistry: Fuzzy matching is PRIMARY (not fallback)

4. **Special Cases**:
   - UKBB NMR needs `NIGHTINGALE_NMR_MATCH`
   - Multi-source needs `MERGE_DATASETS` and `CALCULATE_THREE_WAY_OVERLAP`
   - Semantic bridging for metabolomics→clinical chemistry

5. **Common Pattern**:
   ```
   Load → Extract → Normalize → Match → Analyze → Export
   ```
   But implementation details vary significantly by entity type

---

## Implementation Priority

Based on frequency and blocking status:

### Week 1 (Proteins - 6 strategies)
1. `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Blocks all 6
2. `PROTEIN_NORMALIZE_ACCESSIONS` - Needed by all 6
3. `PROTEIN_MULTI_BRIDGE` - Core matching for all 6

### Week 2 (Metabolites - 10 strategies)
1. `METABOLITE_EXTRACT_IDENTIFIERS` - Blocks all 10
2. `METABOLITE_NORMALIZE_HMDB` - Needed by all 10
3. `METABOLITE_CTS_BRIDGE` - Used by 7/10
4. `NIGHTINGALE_NMR_MATCH` - Needed for UKBB (2/10)

### Week 3 (Chemistry - 5 strategies)
1. `CHEMISTRY_EXTRACT_LOINC` - Blocks all 5
2. `CHEMISTRY_FUZZY_TEST_MATCH` - Primary for all 5
3. `CHEMISTRY_VENDOR_HARMONIZATION` - Needed by 3/5

### Week 4 (Optimization)
1. `CHUNK_PROCESSOR` - Wrap expensive operations
2. Performance testing
3. Pattern extraction (if any emerge)

---

*This breakdown shows clear entity-specific needs that justify the revised implementation approach*