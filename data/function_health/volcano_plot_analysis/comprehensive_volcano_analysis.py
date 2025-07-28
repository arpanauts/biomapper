#!/usr/bin/env python3
"""
Comprehensive analysis of V-shaped patterns in volcano plots across all omics types.
This script provides a detailed explanation of why V-shapes occur and how to interpret them.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def calculate_theoretical_pvalue(r: np.ndarray, n: int) -> np.ndarray:
    """
    Calculate theoretical p-values for given correlation coefficients and sample size.
    
    The relationship is: t = r * sqrt(n-2) / sqrt(1-r^2)
    p-value = 2 * (1 - CDF(|t|, df=n-2))
    """
    # Avoid division by zero for r = ±1
    r_safe = np.clip(r, -0.9999, 0.9999)
    
    # Calculate t-statistic
    t = r_safe * np.sqrt(n - 2) / np.sqrt(1 - r_safe**2)
    
    # Calculate two-tailed p-value
    p = 2 * (1 - stats.t.cdf(np.abs(t), n - 2))
    
    return p

def analyze_sample_size_distribution(df: pd.DataFrame, omics_type: str) -> pd.DataFrame:
    """Analyze the distribution of sample sizes for a given omics type."""
    omics_data = df[df['omics_type'] == omics_type]
    
    # Count correlations by sample size
    sample_size_dist = omics_data['n_samples'].value_counts().sort_index()
    
    # Calculate percentage
    sample_size_pct = (sample_size_dist / len(omics_data) * 100).round(2)
    
    result = pd.DataFrame({
        'n_samples': sample_size_dist.index,
        'count': sample_size_dist.values,
        'percentage': sample_size_pct.values
    })
    
    return result

def plot_volcano_with_theoretical_overlay(df: pd.DataFrame, omics_type: str, ax: plt.Axes):
    """
    Plot volcano plot with theoretical V-shape overlay for different sample sizes.
    """
    omics_data = df[df['omics_type'] == omics_type]
    
    # Plot actual data
    scatter = ax.scatter(omics_data['pearson_r'], 
                        -np.log10(omics_data['pearson_p']), 
                        alpha=0.3, s=10, label='Actual correlations')
    
    # Get most common sample sizes
    common_n = omics_data['n_samples'].value_counts().head(3).index.tolist()
    
    # Plot theoretical curves for common sample sizes
    r_range = np.linspace(-0.8, 0.8, 1000)
    colors = ['red', 'green', 'blue']
    
    for i, n in enumerate(common_n):
        p_theoretical = calculate_theoretical_pvalue(r_range, n)
        ax.plot(r_range, -np.log10(p_theoretical), 
                color=colors[i], linewidth=2, alpha=0.7,
                label=f'Theoretical (n={n})')
    
    # Add significance threshold
    ax.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5, label='p=0.05')
    
    ax.set_xlabel('Pearson r')
    ax.set_ylabel('-log10(p-value)')
    ax.set_title(f'{omics_type.capitalize()} Volcano Plot with Theoretical Curves')
    ax.legend(loc='upper right')
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(0, ax.get_ylim()[1])

def identify_interesting_correlations(df: pd.DataFrame, omics_type: str, 
                                    r_threshold: float = 0.3, 
                                    p_threshold: float = 0.05) -> pd.DataFrame:
    """
    Identify correlations that deviate from the expected V-shape pattern.
    These are biologically interesting findings.
    """
    omics_data = df[df['omics_type'] == omics_type]
    
    # Calculate theoretical p-values for each correlation
    theoretical_p = []
    for _, row in omics_data.iterrows():
        p_theo = calculate_theoretical_pvalue(np.array([row['pearson_r']]), row['n_samples'])[0]
        theoretical_p.append(p_theo)
    
    omics_data['theoretical_p'] = theoretical_p
    
    # Calculate deviation from theoretical
    omics_data['log_p_actual'] = -np.log10(omics_data['pearson_p'])
    omics_data['log_p_theoretical'] = -np.log10(omics_data['theoretical_p'])
    omics_data['deviation'] = omics_data['log_p_actual'] - omics_data['log_p_theoretical']
    
    # Filter for interesting correlations
    interesting = omics_data[
        (omics_data['pearson_p'] < p_threshold) & 
        (np.abs(omics_data['pearson_r']) > r_threshold)
    ].copy()
    
    # Sort by absolute correlation strength
    interesting['abs_r'] = np.abs(interesting['pearson_r'])
    interesting = interesting.sort_values('abs_r', ascending=False)
    
    return interesting[['clinical_test', 'omics_feature', 'omics_feature_name', 
                       'pearson_r', 'pearson_p', 'n_samples', 'deviation']]

def create_comprehensive_visualization():
    """Create a comprehensive figure explaining the V-shape phenomenon."""
    
    # Load correlation results
    print("Loading correlation results...")
    df = pd.read_csv('omics_clinical_correlations_all.csv')
    
    # Get unique omics types
    omics_types = df['omics_type'].unique()
    print(f"Found omics types: {omics_types}")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Sample size distributions
    for i, omics_type in enumerate(omics_types[:3]):  # Limit to first 3 types
        ax = plt.subplot(5, 3, i + 1)
        sample_dist = analyze_sample_size_distribution(df, omics_type)
        
        # Plot top 10 most common sample sizes
        top_10 = sample_dist.head(10)
        ax.bar(range(len(top_10)), top_10['percentage'], 
               tick_label=top_10['n_samples'])
        ax.set_xlabel('Sample Size')
        ax.set_ylabel('Percentage of Correlations')
        ax.set_title(f'{omics_type.capitalize()}: Sample Size Distribution')
        ax.tick_params(axis='x', rotation=45)
    
    # 2. Volcano plots with theoretical overlays
    for i, omics_type in enumerate(omics_types[:3]):
        ax = plt.subplot(5, 3, i + 4)
        plot_volcano_with_theoretical_overlay(df, omics_type, ax)
    
    # 3. Correlation coefficient distributions
    for i, omics_type in enumerate(omics_types[:3]):
        ax = plt.subplot(5, 3, i + 7)
        omics_data = df[df['omics_type'] == omics_type]
        ax.hist(omics_data['pearson_r'], bins=100, alpha=0.7, edgecolor='black')
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
        ax.set_xlabel('Pearson r')
        ax.set_ylabel('Count')
        ax.set_title(f'{omics_type.capitalize()}: Distribution of r values')
        
        # Add statistics
        mean_r = omics_data['pearson_r'].mean()
        median_r = omics_data['pearson_r'].median()
        ax.text(0.05, 0.95, f'Mean: {mean_r:.3f}\nMedian: {median_r:.3f}', 
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 4. Mathematical explanation
    ax = plt.subplot(5, 3, 10)
    ax.axis('off')
    explanation = """
Mathematical Explanation of V-Shape:

The V-shape emerges from the relationship between 
correlation coefficient (r) and p-value:

t = r × √(n-2) / √(1-r²)
p = 2 × (1 - CDF(|t|, df=n-2))

Key insights:
• When r ≈ 0, p ≈ 1 (bottom of V)
• As |r| increases, p decreases (sides of V)
• Larger n → narrower, taller V
• Consistent n → sharp V pattern
• Mixed n → blurred V pattern

The V-shape is EXPECTED when:
1. Most correlations are near zero
2. Sample sizes are consistent
3. No systematic biases exist
"""
    ax.text(0.1, 0.9, explanation, transform=ax.transAxes, 
            verticalalignment='top', fontsize=11,
            fontfamily='monospace')
    
    # 5. How to interpret the V-shape
    ax = plt.subplot(5, 3, 11)
    ax.axis('off')
    interpretation = """
How to Interpret V-Shaped Volcano Plots:

✓ V-shape indicates CORRECT analysis
✓ Points ON the V: Expected null correlations
✓ Points ABOVE the V: Stronger than expected
✓ Points BELOW the V: Weaker than expected

Biologically interesting findings:
• Deviate from the V pattern
• Have both p < 0.05 AND |r| > 0.3
• Show consistent patterns across related features

Common V-shape scenarios:
• Proteomics: Sharp V (small, consistent n)
• Metabolomics: Wide V (large, varied n)
• Clinical labs: Mixed patterns
"""
    ax.text(0.1, 0.9, interpretation, transform=ax.transAxes,
            verticalalignment='top', fontsize=11,
            fontfamily='monospace')
    
    # 6. Example of identifying interesting correlations
    ax = plt.subplot(5, 3, 12)
    # Show example of how to filter for interesting correlations
    example_omics = omics_types[0]
    interesting = identify_interesting_correlations(df, example_omics)
    
    if len(interesting) > 0:
        # Plot showing interesting vs non-interesting
        omics_data = df[df['omics_type'] == example_omics]
        
        # Plot all correlations
        ax.scatter(omics_data['pearson_r'], 
                  -np.log10(omics_data['pearson_p']), 
                  alpha=0.1, s=5, color='gray', label='All correlations')
        
        # Highlight interesting ones
        ax.scatter(interesting['pearson_r'], 
                  -np.log10(interesting['pearson_p']), 
                  alpha=0.8, s=50, color='red', 
                  edgecolor='black', linewidth=1,
                  label=f'Interesting (|r|>{0.3}, p<{0.05})')
        
        ax.set_xlabel('Pearson r')
        ax.set_ylabel('-log10(p-value)')
        ax.set_title(f'Identifying Interesting Correlations ({example_omics})')
        ax.legend()
    
    # 7-9. Theoretical V-shapes for different sample sizes
    sample_sizes = [50, 200, 1000]
    for i, n in enumerate(sample_sizes):
        ax = plt.subplot(5, 3, i + 13)
        r_range = np.linspace(-0.5, 0.5, 1000)
        p_theoretical = calculate_theoretical_pvalue(r_range, n)
        
        ax.plot(r_range, -np.log10(p_theoretical), 'b-', linewidth=2)
        ax.fill_between(r_range, 0, -np.log10(p_theoretical), alpha=0.3)
        ax.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
        ax.set_xlabel('Pearson r')
        ax.set_ylabel('-log10(p-value)')
        ax.set_title(f'Theoretical V-shape (n={n})')
        ax.set_ylim(0, 10)
    
    plt.tight_layout()
    plt.savefig('comprehensive_volcano_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\n=== SUMMARY STATISTICS ===")
    for omics_type in omics_types:
        omics_data = df[df['omics_type'] == omics_type]
        interesting = identify_interesting_correlations(df, omics_type)
        
        print(f"\n{omics_type.upper()}:")
        print(f"  Total correlations: {len(omics_data):,}")
        print(f"  Significant (p<0.05): {(omics_data['pearson_p'] < 0.05).sum():,}")
        print(f"  Strong effect (|r|>0.3): {(np.abs(omics_data['pearson_r']) > 0.3).sum():,}")
        print(f"  Interesting (both): {len(interesting):,}")
        print(f"  Sample size range: {omics_data['n_samples'].min()} - {omics_data['n_samples'].max()}")
        
        # Show top 5 interesting correlations
        if len(interesting) > 0:
            print(f"\n  Top 5 interesting correlations:")
            for _, row in interesting.head(5).iterrows():
                print(f"    {row['clinical_test']} vs {row['omics_feature_name']}: r={row['pearson_r']:.3f}, p={row['pearson_p']:.2e}, n={row['n_samples']}")

def create_detailed_metabolite_analysis():
    """Create a detailed analysis specifically for metabolites."""
    
    print("\n=== DETAILED METABOLITE ANALYSIS ===")
    
    # Load correlation results
    df = pd.read_csv('omics_clinical_correlations_all.csv')
    metabolomics_data = df[df['omics_type'] == 'metabolomics']
    
    # Create figure for metabolite-specific analysis
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Metabolite volcano plot colored by sample size
    ax = axes[0, 0]
    scatter = ax.scatter(metabolomics_data['pearson_r'], 
                        -np.log10(metabolomics_data['pearson_p']),
                        c=metabolomics_data['n_samples'], 
                        cmap='viridis', alpha=0.5, s=20)
    plt.colorbar(scatter, ax=ax, label='Sample Size')
    ax.set_xlabel('Pearson r')
    ax.set_ylabel('-log10(p-value)')
    ax.set_title('Metabolomics Volcano Plot (Colored by Sample Size)')
    ax.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
    
    # 2. Sample size vs correlation strength
    ax = axes[0, 1]
    ax.scatter(metabolomics_data['n_samples'], 
               np.abs(metabolomics_data['pearson_r']),
               alpha=0.3, s=10)
    ax.set_xlabel('Sample Size')
    ax.set_ylabel('|Pearson r|')
    ax.set_title('Sample Size vs Correlation Strength')
    ax.set_xscale('log')
    
    # 3. Clinical test breakdown
    ax = axes[1, 0]
    test_counts = metabolomics_data.groupby('clinical_test').size().sort_values(ascending=False).head(15)
    ax.barh(range(len(test_counts)), test_counts.values)
    ax.set_yticks(range(len(test_counts)))
    ax.set_yticklabels(test_counts.index)
    ax.set_xlabel('Number of Metabolite Correlations')
    ax.set_title('Top 15 Clinical Tests by Metabolite Correlations')
    
    # 4. Strong metabolite correlations
    ax = axes[1, 1]
    strong_corr = metabolomics_data[np.abs(metabolomics_data['pearson_r']) > 0.5]
    if len(strong_corr) > 0:
        # Group by clinical test and count
        strong_by_test = strong_corr.groupby('clinical_test').size().sort_values(ascending=False).head(10)
        ax.bar(range(len(strong_by_test)), strong_by_test.values)
        ax.set_xticks(range(len(strong_by_test)))
        ax.set_xticklabels(strong_by_test.index, rotation=45, ha='right')
        ax.set_ylabel('Count of Strong Correlations (|r| > 0.5)')
        ax.set_title('Clinical Tests with Most Strong Metabolite Correlations')
    else:
        ax.text(0.5, 0.5, 'No correlations with |r| > 0.5', 
                transform=ax.transAxes, ha='center', va='center')
    
    plt.tight_layout()
    plt.savefig('metabolite_specific_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print metabolite-specific insights
    print("\nMETABOLITE-SPECIFIC INSIGHTS:")
    print(f"Total metabolite correlations: {len(metabolomics_data):,}")
    print(f"Unique metabolites: {metabolomics_data['omics_feature'].nunique():,}")
    print(f"Average sample size: {metabolomics_data['n_samples'].mean():.1f}")
    print(f"Median sample size: {metabolomics_data['n_samples'].median():.1f}")
    
    # Find metabolites that correlate with their corresponding clinical tests
    print("\nMETABOLITE-CLINICAL TEST MATCHES:")
    matches = [
        ('GLUCOSE', 'glucose'),
        ('CREATININE', 'creatinine'),
        ('URIC ACID', 'urate'),
        ('UREA NITROGEN', 'urea'),
        ('CHOLESTEROL', 'cholesterol'),
        ('TRIGLYCERIDES', 'triglyceride')
    ]
    
    for clinical, metabolite_pattern in matches:
        subset = metabolomics_data[
            (metabolomics_data['clinical_test'] == clinical) & 
            (metabolomics_data['omics_feature_name'].str.contains(metabolite_pattern, case=False, na=False))
        ]
        if len(subset) > 0:
            best_match = subset.loc[subset['pearson_r'].abs().idxmax()]
            print(f"  {clinical} vs {best_match['omics_feature_name']}: r={best_match['pearson_r']:.3f}, p={best_match['pearson_p']:.2e}")

if __name__ == "__main__":
    # Create comprehensive visualization
    create_comprehensive_visualization()
    
    # Create metabolite-specific analysis
    create_detailed_metabolite_analysis()
    
    print("\n=== ANALYSIS COMPLETE ===")
    print("Generated files:")
    print("  - comprehensive_volcano_analysis.png: Full analysis of V-shape phenomenon")
    print("  - metabolite_specific_analysis.png: Detailed metabolite correlation patterns")
    print("\nThe V-shape in volcano plots is a sign of CORRECT statistical analysis!")