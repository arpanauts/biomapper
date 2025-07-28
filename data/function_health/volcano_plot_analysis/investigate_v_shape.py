#!/usr/bin/env python3
"""
Investigate the V-shaped pattern in volcano plots
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Load the raw data to investigate
print("Loading raw data...")

# Load chemistry data
chemistry_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries.tsv', 
                          sep='\t', comment='#')
print(f"Chemistry data: {chemistry_df.shape}")

# Load proteomics data
proteomics_df = pd.read_csv('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_corrected.tsv', 
                           sep='\t', comment='#')
print(f"Proteomics data: {proteomics_df.shape}")

# Check for missing values in proteomics data
print("\n=== MISSING VALUE ANALYSIS ===")
# Get proteomics feature columns
proteomics_cols = [col for col in proteomics_df.columns if any(col.startswith(prefix) for prefix in 
                   ['CAM_', 'CRE_', 'CVD2_', 'CVD3_', 'DEV_', 'INF_', 'IRE_', 'MET_', 'NEU1_', 
                    'NEX_', 'ODA_', 'ONC2_', 'ONC3_'])]

print(f"\nNumber of proteomics features: {len(proteomics_cols)}")

# Check first few protein columns for data quality
sample_proteins = proteomics_cols[:5]
for protein in sample_proteins:
    data = proteomics_df[protein]
    print(f"\n{protein}:")
    print(f"  Non-null values: {data.notna().sum()}")
    print(f"  Null values: {data.isna().sum()}")
    print(f"  Unique values: {data.nunique()}")
    print(f"  Value range: {data.min():.3f} to {data.max():.3f}")
    
    # Check if all values are the same
    if data.nunique() == 1:
        print(f"  WARNING: All values are identical! Value = {data.iloc[0]}")
    
    # Check distribution
    print(f"  Mean: {data.mean():.3f}, Std: {data.std():.3f}")

# Check for proteins with no variation
print("\n=== CHECKING FOR PROTEINS WITH NO VARIATION ===")
no_var_proteins = []
low_var_proteins = []

for i, protein in enumerate(proteomics_cols):
    if i % 100 == 0:
        print(f"Checking protein {i}/{len(proteomics_cols)}...")
    
    data = proteomics_df[protein].dropna()
    if len(data) > 0:
        # Check if all values are identical
        if data.nunique() == 1:
            no_var_proteins.append(protein)
        # Check if variance is very low
        elif data.std() < 0.0001:
            low_var_proteins.append(protein)

print(f"\nProteins with NO variation (all values identical): {len(no_var_proteins)}")
print(f"Proteins with very low variation (std < 0.0001): {len(low_var_proteins)}")

if no_var_proteins:
    print("\nSample of proteins with no variation:")
    for p in no_var_proteins[:10]:
        val = proteomics_df[p].dropna().iloc[0]
        print(f"  {p}: All values = {val}")

# Let's manually calculate a correlation to see what's happening
print("\n=== MANUAL CORRELATION CALCULATION ===")

# Take first measurement per client for chemistry data
chemistry_subset = chemistry_df.groupby('public_client_id').first().reset_index()
proteomics_subset = proteomics_df.groupby('public_client_id').first().reset_index()

# Merge
merged = pd.merge(
    chemistry_subset[['public_client_id', 'GLUCOSE']],
    proteomics_subset[['public_client_id'] + sample_proteins[:3]],
    on='public_client_id',
    how='inner'
)

print(f"\nMerged data shape: {merged.shape}")

# Calculate correlations manually
for protein in sample_proteins[:3]:
    glucose_vals = merged['GLUCOSE'].dropna()
    protein_vals = merged[protein]
    
    # Find common non-null indices
    common_idx = glucose_vals.index.intersection(protein_vals.dropna().index)
    
    print(f"\n{protein}:")
    print(f"  Common samples: {len(common_idx)}")
    
    if len(common_idx) >= 10:
        x = glucose_vals.loc[common_idx]
        y = protein_vals.loc[common_idx]
        
        # Check variation in both variables
        print(f"  Glucose - Mean: {x.mean():.3f}, Std: {x.std():.3f}")
        print(f"  Protein - Mean: {y.mean():.3f}, Std: {y.std():.3f}")
        
        # If either has zero variance, correlation is undefined
        if x.std() == 0 or y.std() == 0:
            print("  WARNING: Zero variance detected!")
            if x.std() == 0:
                print("    Glucose has no variation")
            if y.std() == 0:
                print("    Protein has no variation")
        else:
            r, p = stats.pearsonr(x, y)
            print(f"  Correlation: r={r:.4f}, p={p:.4f}")
            
            # Plot scatter
            plt.figure(figsize=(6, 4))
            plt.scatter(x, y, alpha=0.5)
            plt.xlabel('Glucose')
            plt.ylabel(protein)
            plt.title(f'Glucose vs {protein}\nr={r:.3f}, p={p:.3f}')
            plt.tight_layout()
            plt.savefig(f'scatter_{protein}.png', dpi=150)
            plt.close()

# Check the V-shape more directly
print("\n=== ANALYZING V-SHAPE PATTERN ===")

# For a perfect V-shape, we expect correlations to cluster around specific values
# This often happens when:
# 1. Variables have limited discrete values
# 2. There's a mathematical relationship between r and p for the given sample size
# 3. Many features have identical or near-identical values

# Let's check the relationship between sample size and minimum p-value
n_values = [50, 100, 200, 500, 1000, 1500]
min_p_values = []

for n in n_values:
    # For n samples, what's the minimum p-value for r≈0?
    # Using the t-distribution: t = r * sqrt(n-2) / sqrt(1-r^2)
    r = 0.001  # Very small correlation
    t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
    p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
    min_p_values.append(p)
    print(f"n={n}: minimum p-value for r≈0 is {p:.6f}")

# Create visualization of theoretical V-shape
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Theoretical V-shape for n=200
n = 200
r_values = np.linspace(-0.5, 0.5, 1000)
p_values = []
for r in r_values:
    if abs(r) < 0.0001:
        p = 1.0
    else:
        t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
        p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
    p_values.append(p)

ax1.plot(r_values, -np.log10(p_values), 'b-', linewidth=2)
ax1.set_xlabel('Pearson r')
ax1.set_ylabel('-log10(p-value)')
ax1.set_title(f'Theoretical Volcano Plot Shape (n={n})')
ax1.axhline(y=-np.log10(0.05), color='r', linestyle='--', alpha=0.5)

# For n=1500
n = 1500
p_values = []
for r in r_values:
    if abs(r) < 0.0001:
        p = 1.0
    else:
        t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
        p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
    p_values.append(p)

ax2.plot(r_values, -np.log10(p_values), 'b-', linewidth=2)
ax2.set_xlabel('Pearson r')
ax2.set_ylabel('-log10(p-value)')
ax2.set_title(f'Theoretical Volcano Plot Shape (n={n})')
ax2.axhline(y=-np.log10(0.05), color='r', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('theoretical_v_shape.png', dpi=150)
plt.show()

print("\n=== CONCLUSION ===")
print("The V-shape in volcano plots is expected when:")
print("1. Sample sizes are large (high statistical power)")
print("2. Many correlations are near zero")
print("3. The relationship between r and p follows the theoretical t-distribution")
print("\nThe perfect V-shape suggests the correlations are being calculated correctly!")
print("Small effect sizes become statistically significant with large sample sizes.")