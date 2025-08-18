# UniProt Historical ID Resolution

This document explains how BioMapper handles historical, secondary, and demerged UniProt identifiers through the `MERGE_WITH_UNIPROT_RESOLUTION` action and related protein normalization actions.

## Background

UniProt protein identifiers can change over time as protein entries are:

1. **Merged**: Multiple entries are merged into a single entry, causing some accessions to become secondary IDs
2. **Split/Demerged**: One entry is split into multiple entries, where the original ID becomes a secondary ID to multiple primary IDs
3. **Obsoleted**: Entries are removed from the database when they are no longer considered valid proteins
4. **Updated**: Primary accessions can become secondary accessions when entries are reorganized

When mapping protein identifiers from one system to another, these historical changes must be handled to ensure accurate and complete mapping.

## Types of UniProt IDs

The Biomapper framework handles these types of UniProt identifiers:

1. **Primary Accessions**: Current, active UniProt identifiers (e.g., P01308 for human insulin)
2. **Secondary Accessions**: Former primary IDs that now point to a current primary ID (e.g., Q99895 → P01308)
3. **Demerged Accessions**: IDs that now point to multiple primary IDs after being split (e.g., P0CG05 → P0DOY2, P0DOY3)
4. **Obsolete Accessions**: IDs that no longer exist in UniProt

## Implementation in BioMapper Actions

BioMapper provides several actions for UniProt ID handling:

### PROTEIN_NORMALIZE_ACCESSIONS
Standardizes UniProt accessions by removing isoform suffixes and validating format:

```python
- name: normalize_proteins
  action:
    type: PROTEIN_NORMALIZE_ACCESSIONS
    params:
      input_key: "raw_proteins"
      output_key: "normalized_proteins"
      remove_isoforms: true  # P01308-1 → P01308
      validate_format: true   # Validates UniProt regex pattern
```

### MERGE_WITH_UNIPROT_RESOLUTION
Merges datasets with historical UniProt ID resolution via API:

```python
- name: merge_with_resolution
  action:
    type: MERGE_WITH_UNIPROT_RESOLUTION
    params:
      source_dataset_key: "dataset1"
      target_dataset_key: "dataset2"
      enable_api_resolution: true  # Enable UniProt API for unmatched IDs
      confidence_threshold: 0.5
```

### How It Works

1. The client submits queries to the UniProt REST API to search for both primary and secondary accessions
2. It searches in both the primary accession and secondary accession fields
3. For each match, it processes the response to determine the correct resolution:
   - If the ID is found as a primary accession, it returns it unchanged
   - If the ID is found as a secondary accession, it returns the matching primary accession(s)
   - If the ID appears as a secondary accession in multiple entries, it returns all primary accessions (demerged case)
   - If no match is found, it marks the ID as obsolete
4. The client includes rich metadata in the return value to indicate the resolution type

### Resolution Results in Context

The actions store resolution results in the shared execution context:

```python
context["datasets"]["merged_dataset"] = [
    {
        "source_id": "P01308",
        "target_id": "P01308",
        "match_type": "primary",
        "match_confidence": 1.0
    },
    {
        "source_id": "Q99895",
        "target_id": "P01308",
        "match_type": "secondary",
        "match_confidence": 0.9
    },
    {
        "source_id": "P0CG05",
        "target_id": "P0DOY2,P0DOY3",
        "match_type": "demerged",
        "match_confidence": 0.8
    }
]
```

## YAML Strategy Configuration

A complete protein harmonization strategy with UniProt resolution:

```yaml
name: PROTEIN_HARMONIZATION_WITH_RESOLUTION
description: Harmonize protein datasets with historical ID resolution

parameters:
  source_file: "${SOURCE_FILE}"
  target_file: "${TARGET_FILE}"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"

steps:
  # Step 1: Load source proteins
  - name: load_source
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.source_file}"
        identifier_column: "uniprot_id"
        output_key: "source_proteins_raw"

  # Step 2: Normalize source proteins
  - name: normalize_source
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "source_proteins_raw"
        output_key: "source_proteins"
        remove_isoforms: true
        validate_format: true

  # Step 3: Load target proteins
  - name: load_target
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.target_file}"
        identifier_column: "protein_accession"
        output_key: "target_proteins"

  # Step 4: Merge with UniProt resolution
  - name: merge_with_resolution
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "source_proteins"
        target_dataset_key: "target_proteins"
        source_id_column: "identifier"
        target_id_column: "identifier"
        output_key: "merged_proteins"
        enable_api_resolution: true
        confidence_threshold: 0.5

  # Step 5: Calculate overlap statistics
  - name: analyze_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        merged_dataset_key: "merged_proteins"
        source_name: "Source"
        target_name: "Target"
        output_key: "overlap_stats"
        output_directory: "${parameters.output_dir}"
```

## Python Client Usage

Execute the strategy using BiomapperClient:

```python
from biomapper.client.client_v2 import BiomapperClient

client = BiomapperClient(base_url="http://localhost:8000")

# Execute protein harmonization with UniProt resolution
result = client.run(
    strategy_name="PROTEIN_HARMONIZATION_WITH_RESOLUTION",
    parameters={
        "source_file": "/data/ukbb_proteins.tsv",
        "target_file": "/data/hpa_proteins.csv",
        "output_dir": "/results/protein_harmonization"
    }
)

print(f"Job completed: {result['status']}")
print(f"Merged proteins: {result['results']['merged_proteins_count']}")
print(f"Resolution stats: {result['results']['resolution_stats']}")
```

## Testing Historical Resolution

Test the MERGE_WITH_UNIPROT_RESOLUTION action:

```python
# tests/unit/core/strategy_actions/test_merge_with_uniprot_resolution.py

class TestMergeWithUniprotResolution:
    @pytest.mark.asyncio
    async def test_secondary_id_resolution(self, mock_context):
        """Test resolution of secondary UniProt IDs."""
        # Setup test data with known secondary IDs
        mock_context["datasets"]["source"] = [
            {"identifier": "Q99895"},  # Secondary ID
            {"identifier": "P01308"}   # Primary ID
        ]
        mock_context["datasets"]["target"] = [
            {"identifier": "P01308"}   # Primary ID
        ]
        
        action = MergeWithUniprotResolutionAction()
        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="identifier",
            target_id_column="identifier",
            output_key="merged",
            enable_api_resolution=True
        )
        
        result = await action.execute_typed(params, mock_context)
        
        assert result.success
        merged = mock_context["datasets"]["merged"]
        # Both Q99895 and P01308 should map to P01308
        assert len([m for m in merged if m["target_id"] == "P01308"]) == 2
```

## Performance Considerations

### Batch Processing
The MERGE_WITH_UNIPROT_RESOLUTION action automatically batches API requests:
- Default batch size: 250 IDs
- Configurable via `batch_size` parameter
- Automatic retry on API failures

### Caching
- Results cached in execution context
- SQLite persistence for job recovery
- Consider using CHUNK_PROCESSOR for very large datasets

### API Rate Limits
- UniProt API has rate limits
- Action implements exponential backoff
- Large datasets may take time to process

## Best Practices

1. **Always normalize first**: Use PROTEIN_NORMALIZE_ACCESSIONS before merging
2. **Set appropriate confidence thresholds**: Use 0.5-0.7 for historical matches
3. **Monitor API resolution**: Check statistics for resolution success rates
4. **Use chunking for large datasets**: Combine with CHUNK_PROCESSOR action
5. **Validate results**: Use CALCULATE_SET_OVERLAP to verify mappings

## Related Actions

- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`: Extract UniProt IDs from compound fields
- `PROTEIN_MULTI_BRIDGE`: Multi-source protein identifier resolution
- `CALCULATE_MAPPING_QUALITY`: Assess quality of UniProt mappings
- `GENERATE_ENHANCEMENT_REPORT`: Detailed report on resolution statistics

---

---

## Verification Sources
*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- `/biomapper/src/biomapper/actions/merge_with_uniprot_resolution.py` (Main resolution action with API integration)
- `/biomapper/src/biomapper/actions/entities/proteins/annotation/` (Protein normalization actions)
- `/biomapper/tests/unit/core/strategy_actions/test_merge_with_uniprot_resolution.py` (Unit tests with secondary ID scenarios)
- `/biomapper/src/biomapper/configs/strategies/templates/protein_mapping_template.yaml` (Template with UniProt resolution)
- `/biomapper/src/biomapper/client/client_v2.py` (BiomapperClient with strategy execution)
- `/biomapper/CLAUDE.md` (Protein action documentation and historical ID handling patterns)