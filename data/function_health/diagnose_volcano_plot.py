#!/usr/bin/env python3
"""
Diagnostic script to investigate V-shaped patterns in volcano plots
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Set display options
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 100)

# Load the correlation results
print("Loading correlation results...")
correlation_results = pd.read_csv('omics_clinical_correlations_all.csv')
print(f"Loaded {len(correlation_results)} correlations")

# Focus on proteomics data
proteomics_data = correlation_results[correlation_results['omics_type'] == 'proteomics']
metabolomics_data = correlation_results[correlation_results['omics_type'] == 'metabolomics']

print(f"\nProteomics correlations: {len(proteomics_data)}")
print(f"Metabolomics correlations: {len(metabolomics_data)}")

# 1. Check distribution of correlation coefficients
print("\n=== CORRELATION COEFFICIENT DISTRIBUTION ===")
print("\nProteomics pearson_r statistics:")
print(proteomics_data['pearson_r'].describe())

# Count correlations exactly at 0
zero_corr_prot = proteomics_data[proteomics_data['pearson_r'] == 0]
print(f"\nProteomics correlations with r=0: {len(zero_corr_prot)} ({len(zero_corr_prot)/len(proteomics_data)*100:.1f}%)")

near_zero_prot = proteomics_data[np.abs(proteomics_data['pearson_r']) < 0.001]
print(f"Proteomics correlations with |r|<0.001: {len(near_zero_prot)} ({len(near_zero_prot)/len(proteomics_data)*100:.1f}%)")

print("\nMetabolomics pearson_r statistics:")
print(metabolomics_data['pearson_r'].describe())

# Count correlations exactly at 0
zero_corr_metab = metabolomics_data[metabolomics_data['pearson_r'] == 0]
print(f"\nMetabolomics correlations with r=0: {len(zero_corr_metab)} ({len(zero_corr_metab)/len(metabolomics_data)*100:.1f}%)")

# 2. Create diagnostic plots
fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# Proteomics plots
ax = axes[0, 0]
ax.hist(proteomics_data['pearson_r'], bins=100, alpha=0.7, edgecolor='black')
ax.set_title('Proteomics: Distribution of Pearson r')
ax.set_xlabel('Pearson r')
ax.set_ylabel('Count')

ax = axes[0, 1]
# Zoom in on the center
center_data = proteomics_data[(proteomics_data['pearson_r'] > -0.1) & (proteomics_data['pearson_r'] < 0.1)]
ax.hist(center_data['pearson_r'], bins=50, alpha=0.7, edgecolor='black')
ax.set_title('Proteomics: Zoomed Distribution (-0.1 < r < 0.1)')
ax.set_xlabel('Pearson r')
ax.set_ylabel('Count')

ax = axes[0, 2]
# Volcano plot
ax.scatter(proteomics_data['pearson_r'], -np.log10(proteomics_data['pearson_p']), 
           alpha=0.3, s=10)
ax.set_title('Proteomics: Volcano Plot')
ax.set_xlabel('Pearson r')
ax.set_ylabel('-log10(p-value)')
ax.axhline(y=-np.log10(0.05), color='r', linestyle='--', alpha=0.5)

# Metabolomics plots
ax = axes[1, 0]
ax.hist(metabolomics_data['pearson_r'], bins=100, alpha=0.7, edgecolor='black', color='orange')
ax.set_title('Metabolomics: Distribution of Pearson r')
ax.set_xlabel('Pearson r')
ax.set_ylabel('Count')

ax = axes[1, 1]
# Zoom in on the center
center_data = metabolomics_data[(metabolomics_data['pearson_r'] > -0.1) & (metabolomics_data['pearson_r'] < 0.1)]
ax.hist(center_data['pearson_r'], bins=50, alpha=0.7, edgecolor='black', color='orange')
ax.set_title('Metabolomics: Zoomed Distribution (-0.1 < r < 0.1)')
ax.set_xlabel('Pearson r')
ax.set_ylabel('Count')

ax = axes[1, 2]
# Volcano plot
ax.scatter(metabolomics_data['pearson_r'], -np.log10(metabolomics_data['pearson_p']), 
           alpha=0.3, s=10, color='orange')
ax.set_title('Metabolomics: Volcano Plot')
ax.set_xlabel('Pearson r')
ax.set_ylabel('-log10(p-value)')
ax.axhline(y=-np.log10(0.05), color='r', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('diagnostic_plots.png', dpi=150)
plt.show()

# 3. Check sample sizes
print("\n=== SAMPLE SIZE ANALYSIS ===")
print("\nProteomics sample sizes:")
print(proteomics_data['n_samples'].describe())

print("\nMetabolomics sample sizes:")
print(metabolomics_data['n_samples'].describe())

# 4. Investigate zero correlations
if len(zero_corr_prot) > 0:
    print("\n=== INVESTIGATING ZERO CORRELATIONS (PROTEOMICS) ===")
    print("\nSample of features with r=0:")
    print(zero_corr_prot[['clinical_test', 'omics_feature', 'omics_feature_name', 'n_samples', 'pearson_p']].head(10))
    
    # Check which clinical tests have many zero correlations
    zero_by_test = zero_corr_prot.groupby('clinical_test').size().sort_values(ascending=False)
    print("\n\nClinical tests with most r=0 correlations:")
    print(zero_by_test.head(10))
    
    # Check which omics features have many zero correlations
    zero_by_feature = zero_corr_prot.groupby('omics_feature').size().sort_values(ascending=False)
    print("\n\nOmics features with most r=0 correlations:")
    print(zero_by_feature.head(10))

# 5. Check p-value distribution for zero correlations
print("\n=== P-VALUE ANALYSIS FOR ZERO CORRELATIONS ===")
if len(zero_corr_prot) > 0:
    print("\nP-values for proteomics r=0 correlations:")
    print(zero_corr_prot['pearson_p'].describe())
    
    # Plot p-value distribution for r=0
    plt.figure(figsize=(10, 6))
    plt.hist(zero_corr_prot['pearson_p'], bins=50, alpha=0.7, edgecolor='black')
    plt.title('Distribution of p-values for Proteomics Correlations with r=0')
    plt.xlabel('p-value')
    plt.ylabel('Count')
    plt.savefig('pvalue_distribution_r0.png', dpi=150)
    plt.show()

# 6. Look at the relationship between r and p
# For correlations with p < 0.05
sig_prot = proteomics_data[proteomics_data['pearson_p'] < 0.05]
print(f"\nProteomics correlations with p < 0.05: {len(sig_prot)}")
print(f"Of these, how many have r=0? {len(sig_prot[sig_prot['pearson_r'] == 0])}")

# 7. Sample raw data investigation
print("\n=== LOOKING FOR PATTERNS IN SPECIFIC TESTS ===")
# Pick a test with many zero correlations
if len(zero_by_test) > 0:
    test_to_check = zero_by_test.index[0]
    print(f"\nInvestigating test: {test_to_check}")
    test_zeros = zero_corr_prot[zero_corr_prot['clinical_test'] == test_to_check]
    print(f"Number of r=0 correlations: {len(test_zeros)}")
    print("\nSample of these correlations:")
    print(test_zeros[['omics_feature', 'omics_feature_name', 'n_samples', 'pearson_p']].head(10))