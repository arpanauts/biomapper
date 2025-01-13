import pandas as pd
from biomapper.core.protein_metadata_comparison import ProteinMetadataComparison
from biomapper.mapping.clients.uniprot_focused_mapper import UniprotFocusedMapper

# Load datasets
arivale_proteins_df = pd.read_csv(
    "arivale_proteins.csv", sep=","
)
ukbb_proteins_df = pd.read_csv(
    "UKBB_Protein_Meta.tsv", sep="\t"
)

# Extract UniProt IDs into Series
arivale_proteins = pd.Series(arivale_proteins_df["uniprot"].unique())
ukbb_proteins = pd.Series(ukbb_proteins_df["UniProt"].unique())

print("Number of unique proteins in Arivale:", len(arivale_proteins))
print("Number of unique proteins in UKBB:", len(ukbb_proteins))

# Initialize comparison tools
mapper = UniprotFocusedMapper()
comparer = ProteinMetadataComparison(mapper=mapper)

# Validate protein IDs
print("\nValidating protein IDs...")
validation_arivale = comparer.validate_protein_ids(arivale_proteins, "Arivale")
validation_ukbb = comparer.validate_protein_ids(ukbb_proteins, "UKBB")

print("\nValid proteins in Arivale:", len(validation_arivale.valid_ids))
print("Valid proteins in UKBB:", len(validation_ukbb.valid_ids))
print("Invalid proteins in Arivale:", len(validation_arivale.invalid_records["id"]))
print("Invalid proteins in UKBB:", len(validation_ukbb.invalid_records["id"]))

# Compare datasets with both Protein/Gene and Pathway mappings
print("\nComparing datasets...")
comparison_result = comparer.compare_datasets(
    validation_arivale.valid_ids,
    validation_ukbb.valid_ids,
    map_categories=["Protein/Gene", "Pathways"],
)

# Create detailed report dataframes
results_df, invalid_df = comparer.create_comparison_dataframe(
    comparison_result,
    validation_arivale.invalid_records,
    validation_ukbb.invalid_records,
)

# Save all results
output_dir = "arivale_ukbb_comparison"
comparer.generate_report(comparison_result, results_df, invalid_df, output_dir)
results_path, invalid_path = comparer.save_results(results_df, invalid_df, output_dir)

print(f"\nResults saved to: {results_path}")
print(f"Invalid IDs saved to: {invalid_path}")

# Summary statistics
print("\nComparison Summary:")
print(f"Shared proteins: {len(comparison_result.shared_proteins)}")
print(f"Unique to Arivale: {len(comparison_result.unique_to_first)}")
print(f"Unique to UKBB: {len(comparison_result.unique_to_second)}")

# Show sample of mapped results
print("\nSample of mapping results (first 5 shared proteins):")
sample_proteins = list(comparison_result.shared_proteins)[:5]
for protein in sample_proteins:
    print(f"\n{protein}:")
    mappings = comparison_result.mappings_first.get(protein, {})
    for db, ids in mappings.items():
        print(f"  {db}: {', '.join(ids)}")
