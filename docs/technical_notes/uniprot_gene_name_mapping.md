# UniProt Gene Name Mapping Approach

## Problem Statement

When mapping UKBB entries to Arivale protein IDs using a fallback strategy through gene names, we encountered a consistent 0% success rate despite successfully mapping gene names to UniProt accessions. This document explains the root cause and solution for this issue.

## Root Cause Analysis

After detailed investigation, we identified the following issues:

1. **Species/Taxonomy Filtering Issue**: When mapping gene names to UniProt accessions using the UniProt ID Mapping API, the service returns accessions from all species despite the `taxon_id="9606"` parameter. This results in a high proportion of non-human or TrEMBL entries that are unlikely to match with Arivale data.

2. **Database Coverage Mismatch**: The Arivale dataset contains a limited set of 1,162 unique proteins, which is a small subset of all human proteins. The likelihood of randomly finding matches between the returned UniProt accessions and the Arivale dataset is low.

3. **Entry Type Mismatch**: The UniProt API returns many unreviewed TrEMBL entries (A0A* pattern), while Arivale primarily uses reviewed Swiss-Prot entries (P/Q/O pattern).

## Solution Strategy

We implemented an enhanced approach with the following key improvements:

1. **Pre-filtering and Prioritization**:
   - Parse and store all UniProt IDs from the Arivale dataset for fast lookup
   - Prioritize Swiss-Prot entries (P/Q/O followed by digits) as they're more likely to be in Arivale
   - Filter returned UniProt accessions to only those present in the Arivale dataset

2. **Enhanced Metadata**:
   - Track both filtered (Arivale-compatible) and all UniProt accessions for reporting
   - Provide more detailed mapping statistics and failure reasons

3. **Improved Error Handling**:
   - Distinguish between different types of mapping failures:
     - `UniProt_Gene_Name_API_Failed`: No UniProt ACs found for gene name
     - `UniProt_Gene_Name_API_No_Arivale_Compatible_ACs`: Found UniProt ACs, but none are in Arivale's format
     - `UniProt_Gene_Name_API_No_Arivale_Match`: Found Arivale-compatible UniProt ACs, but no matching Arivale protein ID

## Implementation Details

The enhanced implementation is structured into three key components:

1. **Arivale Metadata Loading with Cache**:
   ```python
   async def load_arivale_metadata() -> pd.DataFrame:
       # ...
       # Extract and store all UniProt IDs for fast lookup
       arivale_uniprot_ids = set(arivale_df['uniprot'].dropna().astype(str).str.strip().unique())
       # ...
   ```

2. **UniProt AC Filtering and Prioritization**:
   ```python
   def filter_and_prioritize_uniprot_acs(uniprot_acs: List[str]) -> List[str]:
       # Find the intersection with Arivale dataset
       arivale_matches = [ac for ac in uniprot_acs if ac in arivale_uniprot_ids]
       
       # Sort by SwissProt pattern (P/Q entries first)
       return sorted(arivale_matches, 
                    key=lambda ac: (0 if SWISSPROT_PATTERN.match(ac) else 1, ac))
   ```

3. **Enhanced Mapping with Detailed Reporting**:
   ```python
   # Track both filtered and all results
   filtered_results: Dict[str, Tuple[List[str], List[str]]] = {}
   
   for gene_name, uniprot_acs in results.items():
       if uniprot_acs:
           # Filter and prioritize the UniProt ACs
           filtered_acs = filter_and_prioritize_uniprot_acs(uniprot_acs)
           filtered_results[gene_name] = (filtered_acs, uniprot_acs)
   ```

## Expected Outcomes

This enhanced approach should significantly improve the success rate of the UniProt gene name fallback mapping by:

1. Focusing only on UniProt accessions that have a realistic chance of matching Arivale data
2. Providing clearer diagnostics to understand remaining mapping failures
3. Reducing processing time by filtering out irrelevant results early

## Usage

To use this enhanced approach:

1. Run the original process:
   ```
   python scripts/process_uniprot_gene_fallback.py
   ```

2. Run the enhanced process:
   ```
   python scripts/enhanced_process_uniprot_gene_fallback.py
   ```

3. Compare the results:
   ```
   python scripts/run_enhanced_uniprot_fallback.py
   ```

## Extensibility

This approach can be extended for other UniProt-based mapping tasks by:

1. Applying the same pre-filtering strategy to other mapping endpoints
2. Expanding the pattern recognition for other database formats (e.g., NCBI, Ensembl)
3. Adding additional priority tiers for cases where Arivale data might include both Swiss-Prot and TrEMBL entries