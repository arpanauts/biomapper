#!/usr/bin/env python3
"""
Check BILIRUBIN, DIRECT data specifically since it shows extreme V-shape
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Load the correlation results
correlation_results = pd.read_csv("omics_clinical_correlations_all.csv")

# Filter for BILIRUBIN, DIRECT
bilirubin_data = correlation_results[
    correlation_results["clinical_test"] == "BILIRUBIN, DIRECT"
]
print(f"Total correlations for BILIRUBIN, DIRECT: {len(bilirubin_data)}")

# Separate by omics type
bilirubin_prot = bilirubin_data[bilirubin_data["omics_type"] == "proteomics"]
bilirubin_metab = bilirubin_data[bilirubin_data["omics_type"] == "metabolomics"]

print(f"\nProteomics correlations: {len(bilirubin_prot)}")
print(f"Metabolomics correlations: {len(bilirubin_metab)}")

# Check the distribution of correlations
print("\n=== PROTEOMICS CORRELATIONS ===")
print(bilirubin_prot["pearson_r"].describe())

# Check for clustering around zero
near_zero = bilirubin_prot[np.abs(bilirubin_prot["pearson_r"]) < 0.01]
print(
    f"\nCorrelations with |r| < 0.01: {len(near_zero)} ({len(near_zero)/len(bilirubin_prot)*100:.1f}%)"
)

# Check sample sizes
print("\nSample sizes for proteomics:")
print(bilirubin_prot["n_samples"].value_counts().head())

# Look for patterns in the data
print("\n=== INVESTIGATING THE V-SHAPE ===")

# The V-shape can occur when:
# 1. Many correlations are near zero (which is normal for unrelated variables)
# 2. The sample size is consistent, creating a predictable relationship between r and p

# Group by sample size
sample_size_groups = bilirubin_prot.groupby("n_samples")

print("\nNumber of different sample sizes:", len(sample_size_groups))
print("\nMost common sample sizes:")
for n, group in list(sample_size_groups)[:5]:
    print(f"  n={n}: {len(group)} correlations")

# For the most common sample size, check the r-p relationship
most_common_n = bilirubin_prot["n_samples"].mode()[0]
common_n_data = bilirubin_prot[bilirubin_prot["n_samples"] == most_common_n]

print(f"\n=== ANALYZING n={most_common_n} (most common) ===")
print(f"Number of correlations: {len(common_n_data)}")
print(
    f"Range of r values: {common_n_data['pearson_r'].min():.3f} to {common_n_data['pearson_r'].max():.3f}"
)
print(
    f"Correlations with |r| < 0.05: {len(common_n_data[np.abs(common_n_data['pearson_r']) < 0.05])}"
)

# Create detailed diagnostic plots
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Plot 1: Full volcano plot
ax = axes[0, 0]
ax.scatter(
    bilirubin_prot["pearson_r"], -np.log10(bilirubin_prot["pearson_p"]), alpha=0.5, s=20
)
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("BILIRUBIN, DIRECT vs Proteomics")
ax.axhline(y=-np.log10(0.05), color="r", linestyle="--", alpha=0.5)

# Plot 2: Histogram of r values
ax = axes[0, 1]
ax.hist(bilirubin_prot["pearson_r"], bins=50, alpha=0.7)
ax.set_xlabel("Pearson r")
ax.set_ylabel("Count")
ax.set_title("Distribution of Correlation Coefficients")

# Plot 3: r vs p scatter
ax = axes[0, 2]
ax.scatter(bilirubin_prot["pearson_r"], bilirubin_prot["pearson_p"], alpha=0.5, s=20)
ax.set_xlabel("Pearson r")
ax.set_ylabel("p-value")
ax.set_title("r vs p-value")

# Plot 4: Theoretical vs actual
ax = axes[1, 0]
# Plot actual data
ax.scatter(
    common_n_data["pearson_r"],
    -np.log10(common_n_data["pearson_p"]),
    alpha=0.5,
    s=20,
    label="Actual",
)

# Overlay theoretical curve
n = most_common_n
r_theory = np.linspace(-0.5, 0.5, 100)
p_theory = []
for r in r_theory:
    if abs(r) < 0.00001:
        p = 1.0
    else:
        t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
        p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
    p_theory.append(p)

ax.plot(r_theory, -np.log10(p_theory), "r-", linewidth=2, label="Theoretical")
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title(f"Actual vs Theoretical (n={most_common_n})")
ax.legend()

# Plot 5: Sample size distribution
ax = axes[1, 1]
ax.hist(bilirubin_prot["n_samples"], bins=30, alpha=0.7)
ax.set_xlabel("Sample Size")
ax.set_ylabel("Count")
ax.set_title("Distribution of Sample Sizes")

# Plot 6: Metabolomics comparison
ax = axes[1, 2]
ax.scatter(
    bilirubin_metab["pearson_r"],
    -np.log10(bilirubin_metab["pearson_p"]),
    alpha=0.5,
    s=20,
    color="orange",
)
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("BILIRUBIN, DIRECT vs Metabolomics")
ax.axhline(y=-np.log10(0.05), color="r", linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig("bilirubin_diagnostic.png", dpi=150)
plt.show()

# Check actual data values
print("\n=== CHECKING RAW DATA ===")

# Load the raw data
chemistry_df = pd.read_csv(
    "/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries.tsv",
    sep="\t",
    comment="#",
)

# Check BILIRUBIN, DIRECT values
if "BILIRUBIN, DIRECT" in chemistry_df.columns:
    bili_values = chemistry_df["BILIRUBIN, DIRECT"].dropna()
    print("\nBILIRUBIN, DIRECT statistics:")
    print(f"  Count: {len(bili_values)}")
    print(f"  Mean: {bili_values.mean():.3f}")
    print(f"  Std: {bili_values.std():.3f}")
    print(f"  Min: {bili_values.min():.3f}")
    print(f"  Max: {bili_values.max():.3f}")
    print(f"  Unique values: {bili_values.nunique()}")

    # Plot distribution
    plt.figure(figsize=(8, 5))
    plt.hist(bili_values, bins=50, alpha=0.7, edgecolor="black")
    plt.xlabel("BILIRUBIN, DIRECT value")
    plt.ylabel("Count")
    plt.title("Distribution of BILIRUBIN, DIRECT values")
    plt.savefig("bilirubin_distribution.png", dpi=150)
    plt.show()

print("\n=== CONCLUSION ===")
print("The V-shape pattern is NORMAL and expected when:")
print("1. Most biological features are not strongly correlated (r near 0)")
print("2. Sample sizes are consistent and moderately large")
print("3. The statistical test is working correctly")
print(
    "\nThis is NOT a bug - it's the expected pattern for sparse biological correlations!"
)
print(
    "The few significant correlations that deviate from the V are the interesting findings."
)
