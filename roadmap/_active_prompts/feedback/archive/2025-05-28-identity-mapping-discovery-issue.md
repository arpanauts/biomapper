# Identity Mapping Discovery Issue in Biomapper Framework

**Date**: 2025-05-28  
**Issue Type**: Bug Report / Framework Limitation  
**Affected Components**: MappingExecutor, Path Discovery  
**Severity**: High - Prevents basic protein dataset comparisons  

## Executive Summary

The Biomapper framework successfully handles ontology transformations (e.g., UNIPROTKB_AC → ARIVALE_PROTEIN_ID) but fails to discover identity mapping paths (e.g., UNIPROTKB_AC → UNIPROTKB_AC). This prevents using the framework for comparing protein datasets that use the same identifier system, such as UKBB, HPA, and QIN, which all use UniProtKB accessions.

## Detailed Analysis

### Working Case: UKBB to Arivale Mapping

When mapping from UKBB_Protein to Arivale_Protein:
- **Source ontology**: UNIPROTKB_AC
- **Target ontology**: ARIVALE_PROTEIN_ID  
- **Result**: Successfully finds path ID 6: `UKBB_to_Arivale_Protein_via_UniProt`
- **Success rate**: 78.9% (15/19 in test sample)

```
2025-05-28 18:28:59,792 - biomapper.core.mapping_executor - INFO - Mapping execution completed in 5.609s: 15/19 successful (78.9%), 4 unmapped
```

### Failing Case: UKBB to HPA/QIN Mapping

When mapping from UKBB_Protein to HPA_Protein or Qin_Protein:
- **Source ontology**: UNIPROTKB_AC
- **Target ontology**: UNIPROTKB_AC
- **Result**: "No mapping paths found from 'UNIPROTKB_AC' to 'UNIPROTKB_AC'"
- **Success rate**: 0%

```
2025-05-28 17:29:01,504 - biomapper.core.mapping_executor - WARNING - No mapping paths found from 'UNIPROTKB_AC' to 'UNIPROTKB_AC' (bidirectional=False)
```

## Database Configuration Analysis

### Verified Database State

1. **Mapping paths exist** in the `mapping_paths` table:
   ```sql
   16|UNIPROTKB_AC|UNIPROTKB_AC|UKBB_Protein_to_HPA_Protein_UniProt_Identity|Maps UKBB UniProtKB AC to HPA UniProtKB AC if present in HPA data.|1|1||||
   18|UNIPROTKB_AC|UNIPROTKB_AC|UKBB_Protein_to_Qin_Protein_UniProt_Identity|Maps UKBB UniProtKB AC to Qin UniProtKB AC if present in Qin data.|1|1||||
   ```

2. **Mapping path steps are configured**:
   ```sql
   18|16|16|1||HPA Protein Lookup: UKBB UniProtKB AC -> HPA UniProtKB AC|HPA_Protein_UniProt_Lookup
   20|18|17|1||Qin Protein Lookup: UKBB UniProtKB AC -> Qin UniProtKB AC|Qin_Protein_UniProt_Lookup
   ```

3. **Endpoint relationships exist**:
   ```sql
   3|5|2|UKBB to QIN protein mapping
   4|5|1|UKBB to HPA protein mapping
   ```

4. **Relationship mapping paths are linked**:
   ```sql
   1|3|UNIPROTKB_AC|UNIPROTKB_AC|18||||||  # UKBB to QIN
   2|4|UNIPROTKB_AC|UNIPROTKB_AC|16||||||  # UKBB to HPA
   ```

### Property Configuration Differences

1. **UKBB_Protein and Arivale_Protein**: Both use "PrimaryIdentifier"
   ```
   UKBB_Protein|PrimaryIdentifier|UNIPROTKB_AC|1
   Arivale_Protein|PrimaryIdentifier|ARIVALE_PROTEIN_ID|1
   ```

2. **HPA_Protein and Qin_Protein**: Use "UniProtAccession"
   ```
   HPA_Protein|UniProtAccession|UNIPROTKB_AC|1
   Qin_Protein|UniProtAccession|UNIPROTKB_AC|1
   ```

## Root Cause Hypothesis

The MappingExecutor's path discovery mechanism appears to have a specific issue with identity mappings where:
1. Source ontology type == Target ontology type (UNIPROTKB_AC → UNIPROTKB_AC)
2. The path discovery query may be filtering out or not properly handling identity transformations

This is evidenced by:
- The warning specifically states no paths found for UNIPROTKB_AC to UNIPROTKB_AC
- The same infrastructure works when ontologies differ (UNIPROTKB_AC to ARIVALE_PROTEIN_ID)
- All database configurations appear correct

## Impact

This bug prevents using the Biomapper framework's advanced features for:
- Comparing protein datasets that use the same identifier system
- Leveraging historical UniProt ID resolution for dataset comparisons
- Using secondary ontology fallbacks for improved mapping coverage

## Workaround

Simple direct lookups were implemented that bypass the framework:
- Successfully mapped 472/2923 UKBB proteins to QIN (16.15%)
- Successfully mapped 485/2923 UKBB proteins to HPA (16.59%)

These workarounds lose the framework benefits of:
- Historical ID resolution (deprecated, merged, demerged UniProt IDs)
- Secondary identifier fallbacks (gene names, Ensembl IDs)
- Confidence scoring and validation
- Caching for performance

## Recommended Actions

1. **Investigate MappingExecutor path discovery**:
   - Review the `_get_mapping_paths` method
   - Check if identity mappings are explicitly filtered out
   - Verify the SQL query used for path discovery

2. **Add test cases** for identity mappings:
   - Test UNIPROTKB_AC → UNIPROTKB_AC paths
   - Ensure path discovery works for same-ontology transformations

3. **Consider design enhancement**:
   - Should identity mappings be handled as a special case?
   - Could a "direct lookup" path type simplify these scenarios?

4. **Update documentation** to clarify:
   - Current limitations with identity mappings
   - When to use framework vs. simple lookups
   - Property name requirements for different endpoints

## Code References

- Path discovery warning: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` (search for "No mapping paths found from")
- Working example: `/home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py`
- Failed attempts: 
  - `/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py` 
  - `/home/ubuntu/biomapper/scripts/map_endpoints_flexible.py`

## Conclusion

The Biomapper framework has a specific limitation with identity ontology mappings that prevents it from being used for comparing datasets using the same identifier system. While the database is correctly configured with the necessary paths and relationships, the MappingExecutor's path discovery mechanism fails to find these paths. This forces users to implement simple workarounds that lose the framework's sophisticated mapping capabilities.