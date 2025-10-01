#!/usr/bin/env python3
"""
Compare PubChem vs HMDB mapping for Arivale metabolites
"""
import pandas as pd

# Load the data
arivale = pd.read_csv('data/arivale_metabolites_clean.tsv', sep='\t')
pubchem_df = pd.read_csv('data/kraken_pubchem_1m.tsv', sep='\t')

# Fix data types - ensure both are strings
arivale['pubchem_str'] = arivale['pubchem_normalized'].astype(str).str.replace('.0', '', regex=False)
pubchem_df['pubchem_cid'] = pubchem_df['pubchem_cid'].astype(str)

# Filter out 'nan' values
arivale_with_pubchem = arivale[arivale['pubchem_str'] != 'nan'].copy()

print(f'Arivale metabolites with valid PubChem: {len(arivale_with_pubchem)}')
print(f'Kraken PubChem mappings available: {len(pubchem_df)}')
print(f'Unique PubChem CIDs in Kraken: {pubchem_df["pubchem_cid"].nunique()}')

# Perform mapping
merged_pubchem = arivale_with_pubchem.merge(pubchem_df,
                                            left_on='pubchem_str',
                                            right_on='pubchem_cid',
                                            how='inner')

unique_pubchem_matches = merged_pubchem['arivale_metabolite_id'].nunique()

print(f'\nPubChem mapping results:')
print(f'Matched metabolites: {unique_pubchem_matches}')
print(f'Match rate: {100*unique_pubchem_matches/len(arivale_with_pubchem):.1f}%')

# Load HMDB results for comparison
hmdb_mapped = pd.read_csv('data/arivale_kraken_mapped.tsv', sep='\t')
unique_hmdb_matches = hmdb_mapped['arivale_metabolite_id'].nunique()

print(f'\nComparison:')
print(f'HMDB matches: {unique_hmdb_matches} metabolites')
print(f'PubChem matches: {unique_pubchem_matches} metabolites')

# Check what PubChem adds beyond HMDB
hmdb_ids = set(hmdb_mapped['arivale_metabolite_id'].unique())
pubchem_ids = set(merged_pubchem['arivale_metabolite_id'].unique())

both = hmdb_ids & pubchem_ids
hmdb_only = hmdb_ids - pubchem_ids
pubchem_only = pubchem_ids - hmdb_ids
total_unique = hmdb_ids | pubchem_ids

print(f'\nCoverage analysis:')
print(f'Matched by both HMDB and PubChem: {len(both)}')
print(f'HMDB only: {len(hmdb_only)}')
print(f'PubChem only: {len(pubchem_only)}')
print(f'Total unique metabolites mapped: {len(total_unique)}')

# Calculate combined coverage
arivale_with_any = arivale[(arivale['hmdb_normalized'].notna()) | (arivale['pubchem_str'] != 'nan')]
combined_rate = 100 * len(total_unique) / len(arivale_with_any)
print(f'\nCombined mapping rate: {combined_rate:.1f}%')

# Show examples of PubChem-only matches
if len(pubchem_only) > 0:
    print('\nExamples of metabolites matched ONLY via PubChem:')
    pubchem_only_df = merged_pubchem[merged_pubchem['arivale_metabolite_id'].isin(pubchem_only)]
    for _, row in pubchem_only_df[['metabolite_name', 'pubchem_cid', 'kraken_name']].head(5).iterrows():
        name_short = row["kraken_name"][:50] + "..." if len(row["kraken_name"]) > 50 else row["kraken_name"]
        print(f'  {row["metabolite_name"]} (PubChem:{row["pubchem_cid"]}) -> {name_short}')

# Check if PubChem gets us closer to primary IDs (ChEBI)
print('\nKraken ID type analysis:')
print('HMDB mappings by Kraken ID type:')
hmdb_id_types = hmdb_mapped['kraken_id'].str.split(':').str[0].value_counts()
print(hmdb_id_types.head())

print('\nPubChem mappings by Kraken ID type:')
pubchem_id_types = merged_pubchem['kraken_id'].str.split(':').str[0].value_counts()
print(pubchem_id_types.head())

# Count how many map to ChEBI (primary) vs other IDs
hmdb_to_chebi = (hmdb_mapped['kraken_id'].str.startswith('CHEBI:')).sum()
pubchem_to_chebi = (merged_pubchem['kraken_id'].str.startswith('CHEBI:')).sum()

print(f'\nMapping to ChEBI (primary ID):')
print(f'HMDB -> ChEBI: {hmdb_to_chebi}/{len(hmdb_mapped)} ({100*hmdb_to_chebi/len(hmdb_mapped):.1f}%)')
print(f'PubChem -> ChEBI: {pubchem_to_chebi}/{len(merged_pubchem)} ({100*pubchem_to_chebi/len(merged_pubchem):.1f}%)')