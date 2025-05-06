# UniProt Historical ID Resolution

This document explains how the Biomapper framework handles historical, secondary, and demerged UniProt identifiers.

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

## Implementation Details

The `UniProtHistoricalResolverClient` provides functionality to handle historical ID resolution:

```python
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Initialize the client
client = UniProtHistoricalResolverClient()

# Resolve a list of potentially historical/secondary IDs
results = await client.map_identifiers(["P01308", "Q99895", "P0CG05"])
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

### Return Format

The client returns results in the standard Biomapper tuple format:

```python
results = {
    "P01308": (["P01308"], "primary"),  # Primary ID (unchanged)
    "Q99895": (["P01308"], "secondary:P01308"),  # Secondary ID with resolution
    "P0CG05": (["P0DOY2", "P0DOY3"], "demerged"),  # Demerged ID with multiple targets
    "FAKEID": (None, "obsolete")  # Obsolete/non-existent ID
}
```

- The first element of the tuple is the list of resolved primary IDs (or None)
- The second element is metadata about the resolution type

## Mapping Configuration

The Biomapper framework includes a two-step process for UKBB to Arivale protein mapping:

1. **Direct Path** (Primary): Try to map the UniProt ID directly to Arivale
   ```
   UKBB UniProt ID → Arivale Protein ID
   ```

2. **Fallback Path** (with Historical Resolution): If direct mapping fails, try historical resolution first
   ```
   UKBB UniProt ID → Historical Resolution → Arivale Protein ID
   ```

### Configuration in the Database

The metamapper database includes these configurations in the `MappingPath` table:

1. Direct path (priority 1):
   ```
   UKBB_to_Arivale_Protein_via_UniProt
   ```

2. Historical resolution path (priority 2):
   ```
   UKBB_to_Arivale_Protein_via_Historical_Resolution
   ```

## Example Usage

Here's how to execute a mapping that utilizes historical ID resolution:

```python
from biomapper.core.mapping_executor import MappingExecutor

# Initialize the executor
executor = MappingExecutor()

# Execute mapping with fallback to historical resolution
result = await executor.execute_mapping(
    source_endpoint_name="UKBB_Protein",
    target_endpoint_name="Arivale_Protein",
    source_identifiers=["P01308", "Q99895", "P0CG05"],
    source_ontology_type="UNIPROTKB_AC",
    target_ontology_type="ARIVALE_PROTEIN_ID",
)
```

The MappingExecutor will:
1. Try the direct path first (for performance)
2. For any IDs that fail direct mapping, try the fallback path with historical resolution
3. Combine and return the results

## Testing

A test dataset is provided to verify historical ID resolution functionality:

```
/home/ubuntu/biomapper/data/ukbb_test_data_with_historical_ids.tsv
```

This dataset contains various test cases:
- Primary IDs that should map directly
- Secondary IDs that require resolution
- Demerged IDs that map to multiple entries
- Obsolete/non-existent IDs that should fail to map

To run a test of the historical resolution functionality:

```bash
python /home/ubuntu/biomapper/test_ukbb_historical_mapping.py
```

## Limitations

1. The UniProt REST API may have rate limits, so large batches of IDs should be processed in smaller chunks.
2. Some very old or specific accessions might not resolve correctly through the API.
3. Performance can be impacted when large numbers of IDs require resolution through the API.
4. The UniProt API's treatment of secondary and demerged IDs can change over time as the database is updated.
5. Reference data used in tests may become outdated as UniProt updates its database.

### API Compatibility Notes

Our tests have shown that:

1. **Primary IDs**: The API correctly identifies current primary accessions.
2. **Secondary IDs**: Some IDs that were historically secondary may now appear as primary in the API.
3. **Demerged IDs**: Some demerged IDs might be reused or become primary IDs in later releases.

For the most accurate historical ID resolution, consider using the UniProt ID Mapping Service's
batch job endpoint or maintaining a local mapping of secondary-to-primary IDs.