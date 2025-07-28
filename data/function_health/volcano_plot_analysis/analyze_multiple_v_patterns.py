#!/usr/bin/env python3
"""
Analyze and explain the multiple V-shaped patterns in volcano plots.
The key insight: different sample sizes create distinct V-curves that overlay each other.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from collections import Counter

# Set style
plt.style.use('seaborn-v0_8-whitegrid')

def calculate_theoretical_curves(sample_sizes, r_range):
    """Calculate theoretical p-value curves for different sample sizes."""
    curves = {}
    for n in sample_sizes:
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        curves[n] = p_values
    return curves

def simulate_multiple_v_patterns():
    """Simulate data that creates multiple V patterns like in the real data."""
    
    # Common sample sizes in proteomics data (from the analysis)
    # These create the distinct layers
    sample_size_groups = [
        (72, 500),    # Sparse test + rare chip
        (193, 300),   # Well-measured test + rare chip  
        (464, 800),   # Sparse test + common chip
        (1582, 400),  # Well-measured test + common chip
    ]
    
    all_r = []
    all_p = []
    all_n = []
    
    for n_samples, n_correlations in sample_size_groups:
        # Generate mostly null correlations
        r_values = np.random.normal(0, 0.1, n_correlations)
        
        # Add a few true correlations
        n_true = int(n_correlations * 0.02)
        true_indices = np.random.choice(n_correlations, n_true, replace=False)
        r_values[true_indices] = np.random.choice([-1, 1]) * np.random.uniform(0.3, 0.8, n_true)
        
        # Calculate p-values
        t_values = r_values * np.sqrt(n_samples - 2) / np.sqrt(1 - r_values**2)
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_values), n_samples - 2))
        
        all_r.extend(r_values)
        all_p.extend(p_values)
        all_n.extend([n_samples] * n_correlations)
    
    return np.array(all_r), np.array(all_p), np.array(all_n)

def create_diagnostic_figure():
    """Create a comprehensive figure explaining multiple V patterns."""
    
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Simulated data showing multiple V patterns
    ax1 = plt.subplot(2, 3, 1)
    r_sim, p_sim, n_sim = simulate_multiple_v_patterns()
    
    # Color by sample size
    scatter = ax1.scatter(r_sim, -np.log10(p_sim), c=n_sim, cmap='viridis', 
                         alpha=0.6, s=20, edgecolor='none')
    plt.colorbar(scatter, ax=ax1, label='Sample Size (n)')
    
    ax1.set_xlabel('Correlation (r)')
    ax1.set_ylabel('-log10(p-value)')
    ax1.set_title('Multiple V-Patterns from Different Sample Sizes\n(Simulated Data)')
    ax1.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
    ax1.set_xlim(-0.8, 0.8)
    
    # 2. Theoretical curves showing how sample size creates different Vs
    ax2 = plt.subplot(2, 3, 2)
    r_range = np.linspace(-0.8, 0.8, 1000)
    sample_sizes = [72, 193, 464, 1582]
    colors = plt.cm.viridis(np.linspace(0, 1, len(sample_sizes)))
    
    for n, color in zip(sample_sizes, colors):
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        ax2.plot(r_range, -np.log10(p_theoretical), color=color, linewidth=2.5, 
                label=f'n={n}', alpha=0.8)
    
    ax2.set_xlabel('Correlation (r)')
    ax2.set_ylabel('-log10(p-value)')
    ax2.set_title('Theoretical V-Curves for Different Sample Sizes')
    ax2.legend()
    ax2.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
    ax2.set_xlim(-0.8, 0.8)
    ax2.set_ylim(0, 10)
    
    # 3. Explanation of sample size groups
    ax3 = plt.subplot(2, 3, 3)
    ax3.axis('off')
    
    explanation = """
Why Multiple V-Patterns Appear:

In proteomics/metabolomics studies, different 
combinations create distinct sample sizes:

1. Clinical Test Coverage × Omics Panel Coverage
   
   Well-measured test + Common chip → n ≈ 1,582
   Well-measured test + Rare chip → n ≈ 193
   Sparse test + Common chip → n ≈ 464
   Sparse test + Rare chip → n ≈ 72

2. Each Sample Size Creates Its Own V-Curve
   
   Larger n → Taller, narrower V (top layer)
   Smaller n → Shorter, wider V (bottom layer)

3. Result: Layered/Banded Appearance
   
   The "multiple U shapes" are mathematical
   artifacts of having discrete sample size
   groups rather than continuous variation.
"""
    
    ax3.text(0.1, 0.9, explanation, transform=ax3.transAxes, 
             fontsize=12, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # 4. Sample size distribution histogram
    ax4 = plt.subplot(2, 3, 4)
    
    # Create example sample size distribution
    sample_sizes = []
    # Add clusters of sample sizes
    sample_sizes.extend([72] * 300)
    sample_sizes.extend([193] * 200)
    sample_sizes.extend([464] * 400)
    sample_sizes.extend([1582] * 300)
    # Add some intermediate values
    sample_sizes.extend(np.random.randint(100, 1500, 100))
    
    ax4.hist(sample_sizes, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
    ax4.set_xlabel('Sample Size (n)')
    ax4.set_ylabel('Number of Correlations')
    ax4.set_title('Typical Sample Size Distribution\n(Discrete Groups, Not Continuous)')
    ax4.axvline(x=72, color='red', linestyle='--', alpha=0.5, label='Common n values')
    ax4.axvline(x=193, color='red', linestyle='--', alpha=0.5)
    ax4.axvline(x=464, color='red', linestyle='--', alpha=0.5)
    ax4.axvline(x=1582, color='red', linestyle='--', alpha=0.5)
    
    # 5. Visual explanation of the layers
    ax5 = plt.subplot(2, 3, 5)
    
    # Create stylized version showing layers
    r_range_small = np.linspace(-0.6, 0.6, 100)
    
    # Plot layers with fill
    alphas = [0.3, 0.3, 0.3, 0.3]
    labels = ['n=72 (bottom layer)', 'n=193', 'n=464', 'n=1582 (top layer)']
    
    for i, (n, alpha, label) in enumerate(zip([72, 193, 464, 1582], alphas, labels)):
        t_values = r_range_small * np.sqrt(n - 2) / np.sqrt(1 - r_range_small**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        log_p = -np.log10(p_theoretical)
        
        # Fill under curve
        ax5.fill_between(r_range_small, 0, log_p, alpha=alpha, 
                        label=label, color=colors[i])
        # Draw curve
        ax5.plot(r_range_small, log_p, color=colors[i], linewidth=2)
    
    ax5.set_xlabel('Correlation (r)')
    ax5.set_ylabel('-log10(p-value)')
    ax5.set_title('Layered V-Patterns Create "Banded" Appearance')
    ax5.legend(loc='upper right')
    ax5.set_xlim(-0.6, 0.6)
    ax5.set_ylim(0, 8)
    ax5.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
    
    # 6. Real-world implications
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    implications = """
Implications for Analysis:

1. Multiple V-patterns are EXPECTED when:
   • Different test/panel combinations exist
   • Batch effects create sample groups
   • Time-based cohorts are analyzed together

2. This is NOT a problem, but shows:
   • Heterogeneous data structure
   • Need to account for sample size
   • Importance of stratified analysis

3. Best Practices:
   • Report sample sizes with correlations
   • Consider stratified FDR correction
   • Weight by sample size if combining
   • Check which "layer" significant 
     correlations come from

4. Biological Interpretation:
   • High-n findings are most reliable
   • Low-n findings need validation
   • Cross-layer consistency is valuable
"""
    
    ax6.text(0.1, 0.9, implications, transform=ax6.transAxes,
             fontsize=11, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('multiple_v_patterns_explained.png', dpi=300, bbox_inches='tight')
    plt.show()

def analyze_sample_size_clustering():
    """Analyze how sample sizes cluster to create multiple V patterns."""
    
    # Example: Common sample size combinations in proteomics/metabolomics
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Create example data showing clustering
    # Clinical test availability (% of samples)
    clinical_tests = {
        'GLUCOSE': 0.95,
        'CHOLESTEROL': 0.95,
        'ALBUMIN': 0.95,
        'BILIRUBIN_DIRECT': 0.30,
        'COPPER_RBC': 0.30,
        'SELENIUM': 0.30,
        'LEPTIN': 0.10
    }
    
    # Omics panel coverage (% of samples)
    omics_panels = {
        'CVD2/CVD3/INF (common)': 0.92,
        'CAM/CRE/DEV (rare)': 0.09,
        'Metabolomics (variable)': 'varies'
    }
    
    # Show matrix of expected sample sizes
    ax1.axis('off')
    matrix_text = """
    Sample Size Matrix (Proteomics Example):
    
    Clinical Test    ×    Omics Panel    →    Expected n    →    V-layer
    ─────────────────────────────────────────────────────────────────────
    Well-measured   ×    Common chip    →    n ≈ 1,580    →    Top layer
    Well-measured   ×    Rare chip      →    n ≈ 193      →    Layer 3
    Sparse test     ×    Common chip    →    n ≈ 464      →    Layer 2  
    Sparse test     ×    Rare chip      →    n ≈ 72       →    Bottom layer
    Very sparse     ×    Rare chip      →    n ≈ 32       →    Lowest points
    
    Each combination creates its own V-curve!
    """
    
    ax1.text(0.1, 0.5, matrix_text, transform=ax1.transAxes,
             fontsize=12, fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
             verticalalignment='center')
    
    # Visualize the effect
    ax2.set_xlabel('Correlation (r)')
    ax2.set_ylabel('-log10(p-value)')
    ax2.set_title('How Sample Size Groups Create Multiple V-Patterns')
    
    r_range = np.linspace(-0.5, 0.5, 500)
    
    # Plot with annotations
    sample_groups = [
        (1580, 'Well-measured test\n+ Common chip', 'green'),
        (464, 'Sparse test\n+ Common chip', 'orange'),
        (193, 'Well-measured test\n+ Rare chip', 'blue'),
        (72, 'Sparse test\n+ Rare chip', 'red'),
    ]
    
    for n, label, color in sample_groups:
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        ax2.plot(r_range, -np.log10(p_theoretical), color=color, 
                linewidth=2.5, label=f'{label}\n(n={n})', alpha=0.7)
    
    # Add example data points
    np.random.seed(42)
    for n, _, color in sample_groups:
        # Add some example points
        n_points = 50
        r_vals = np.random.normal(0, 0.05, n_points)
        t_vals = r_vals * np.sqrt(n - 2) / np.sqrt(1 - r_vals**2)
        p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), n - 2))
        ax2.scatter(r_vals, -np.log10(p_vals), color=color, alpha=0.3, s=20)
    
    ax2.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.set_xlim(-0.5, 0.5)
    ax2.set_ylim(0, 6)
    
    plt.tight_layout()
    plt.savefig('sample_size_clustering_effect.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    print("Creating visualizations to explain multiple V-patterns...")
    
    # Create main diagnostic figure
    create_diagnostic_figure()
    
    # Create sample size clustering analysis
    analyze_sample_size_clustering()
    
    print("\n=== ANALYSIS COMPLETE ===")
    print("\nKey Insight: Multiple V-patterns occur because:")
    print("1. Different test/panel combinations have different sample sizes")
    print("2. Each unique sample size creates its own V-curve")
    print("3. These curves overlay to create a 'banded' or 'layered' appearance")
    print("\nThis is EXPECTED behavior in studies with:")
    print("- Multiple measurement platforms")
    print("- Variable test availability")
    print("- Different panel coverage")
    print("\nGenerated files:")
    print("  - multiple_v_patterns_explained.png")
    print("  - sample_size_clustering_effect.png")