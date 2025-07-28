#!/usr/bin/env python3
"""
Create clear, separated visualizations showing how sample size groups create multiple V-patterns.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import matplotlib.patches as patches

def create_sample_size_table():
    """Create a clear table showing sample size matrix."""
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.axis('off')
    
    # Title
    ax.text(0.5, 0.95, 'Sample Size Matrix: How Different Combinations Create Distinct V-Curves', 
            fontsize=18, fontweight='bold', ha='center', transform=ax.transAxes)
    
    # Create table data
    table_data = [
        ['Clinical Test', 'Coverage', '×', 'Omics Panel', 'Coverage', '→', 'Expected n', '→', 'V-layer Position'],
        ['─' * 15, '─' * 8, ' ', '─' * 15, '─' * 8, ' ', '─' * 10, ' ', '─' * 15],
        ['Well-measured', '95%', '×', 'Common chip', '92%', '→', 'n ≈ 1,580', '→', 'Top layer (tall V)'],
        ['Well-measured', '95%', '×', 'Rare chip', '9%', '→', 'n ≈ 193', '→', 'Middle layer'],
        ['Sparse test', '30%', '×', 'Common chip', '92%', '→', 'n ≈ 464', '→', 'Upper-middle layer'],
        ['Sparse test', '30%', '×', 'Rare chip', '9%', '→', 'n ≈ 72', '→', 'Bottom layer (wide V)'],
        ['Very sparse', '10%', '×', 'Rare chip', '9%', '→', 'n ≈ 32', '→', 'Lowest points'],
    ]
    
    # Position for table
    y_start = 0.75
    row_height = 0.08
    
    # Column positions
    col_positions = [0.05, 0.20, 0.28, 0.35, 0.50, 0.58, 0.65, 0.75, 0.82]
    
    # Draw table
    for i, row in enumerate(table_data):
        y_pos = y_start - i * row_height
        
        # Header row styling
        if i == 0:
            # Add background for header
            rect = patches.Rectangle((0.02, y_pos - 0.02), 0.96, row_height, 
                                   facecolor='lightblue', alpha=0.3, transform=ax.transAxes)
            ax.add_patch(rect)
            fontweight = 'bold'
            fontsize = 12
        elif i == 1:
            fontweight = 'normal'
            fontsize = 10
        else:
            fontweight = 'normal'
            fontsize = 11
            
            # Alternate row coloring
            if (i - 2) % 2 == 1:
                rect = patches.Rectangle((0.02, y_pos - 0.02), 0.96, row_height, 
                                       facecolor='gray', alpha=0.1, transform=ax.transAxes)
                ax.add_patch(rect)
        
        # Draw each cell
        for j, (text, x_pos) in enumerate(zip(row, col_positions)):
            # Color coding for sample sizes
            if j == 6 and i > 1:  # Sample size column
                if '1,580' in text:
                    color = 'darkgreen'
                elif '464' in text:
                    color = 'darkorange'
                elif '193' in text:
                    color = 'darkblue'
                elif '72' in text:
                    color = 'darkred'
                else:
                    color = 'purple'
            else:
                color = 'black'
                
            ax.text(x_pos, y_pos, text, fontsize=fontsize, fontweight=fontweight,
                   transform=ax.transAxes, color=color)
    
    # Add explanation box
    explanation_y = 0.15
    ax.text(0.5, explanation_y, 
            'Key Insight: Each unique combination of clinical test coverage and omics panel coverage\n' +
            'creates a specific sample size, which in turn creates its own V-shaped curve in the volcano plot.\n' +
            'These curves overlay to create the "multiple V-pattern" or "banded" appearance.',
            fontsize=12, ha='center', transform=ax.transAxes,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
    
    plt.savefig('sample_size_matrix_table.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_v_curves_visualization():
    """Create visualization showing how different sample sizes create different V-curves."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Left plot: Individual V-curves
    r_range = np.linspace(-0.6, 0.6, 1000)
    
    # Define sample groups with colors matching the table
    sample_groups = [
        (1580, 'n=1,580 (Well-measured + Common)', 'darkgreen'),
        (464, 'n=464 (Sparse + Common)', 'darkorange'),
        (193, 'n=193 (Well-measured + Rare)', 'darkblue'),
        (72, 'n=72 (Sparse + Rare)', 'darkred'),
    ]
    
    for n, label, color in sample_groups:
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        ax1.plot(r_range, -np.log10(p_theoretical), color=color, 
                linewidth=3, label=label, alpha=0.8)
    
    ax1.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5, label='p=0.05 threshold')
    ax1.set_xlabel('Correlation (r)', fontsize=14)
    ax1.set_ylabel('-log10(p-value)', fontsize=14)
    ax1.set_title('Individual V-Curves for Each Sample Size Group', fontsize=16, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(-0.6, 0.6)
    ax1.set_ylim(0, 8)
    
    # Add annotations
    ax1.annotate('Tall, narrow V\n(high power)', xy=(0.15, 6), xytext=(0.3, 6.5),
                arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2),
                fontsize=11, color='darkgreen', fontweight='bold')
    
    ax1.annotate('Short, wide V\n(low power)', xy=(0.3, 2), xytext=(0.4, 1),
                arrowprops=dict(arrowstyle='->', color='darkred', lw=2),
                fontsize=11, color='darkred', fontweight='bold')
    
    # Right plot: Overlapped pattern (what you see in real data)
    # First, draw filled regions to show layering
    for n, label, color in reversed(sample_groups):  # Draw in reverse order so larger n is on top
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
        log_p = -np.log10(p_theoretical)
        
        # Fill under curve with transparency
        ax2.fill_between(r_range, 0, log_p, alpha=0.2, color=color)
        
        # Draw the curve
        ax2.plot(r_range, log_p, color=color, linewidth=2, alpha=0.8)
    
    # Add simulated data points
    np.random.seed(42)
    for n, _, color in sample_groups:
        # Generate random correlations
        n_points = 100
        r_vals = np.random.normal(0, 0.08, n_points)
        
        # Add a few outliers
        n_outliers = 5
        outlier_indices = np.random.choice(n_points, n_outliers, replace=False)
        r_vals[outlier_indices] = np.random.choice([-1, 1]) * np.random.uniform(0.3, 0.5, n_outliers)
        
        # Calculate p-values
        t_vals = r_vals * np.sqrt(n - 2) / np.sqrt(1 - r_vals**2)
        p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), n - 2))
        
        # Plot points
        ax2.scatter(r_vals, -np.log10(p_vals), color=color, alpha=0.4, s=30, edgecolor='none')
    
    ax2.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Correlation (r)', fontsize=14)
    ax2.set_ylabel('-log10(p-value)', fontsize=14)
    ax2.set_title('Overlapped V-Patterns (As Seen in Real Data)', fontsize=16, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-0.6, 0.6)
    ax2.set_ylim(0, 8)
    
    # Add text annotations for the bands
    band_annotations = [
        (0.45, 6.5, 'Top band\n(n≈1,580)', 'darkgreen'),
        (0.45, 4.5, 'Upper-middle\n(n≈464)', 'darkorange'),
        (0.45, 3, 'Middle band\n(n≈193)', 'darkblue'),
        (0.45, 1.5, 'Bottom band\n(n≈72)', 'darkred'),
    ]
    
    for x, y, text, color in band_annotations:
        ax2.text(x, y, text, fontsize=10, color=color, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('v_curves_visualization.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_summary_figure():
    """Create a summary figure explaining the phenomenon."""
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.axis('off')
    
    # Title
    ax.text(0.5, 0.95, 'Why Volcano Plots Show Multiple V-Patterns', 
            fontsize=20, fontweight='bold', ha='center', transform=ax.transAxes)
    
    # Main explanation sections
    sections = [
        {
            'y': 0.85,
            'title': '1. The Root Cause: Discrete Sample Size Groups',
            'content': (
                '• Your data doesn???t have a continuous range of sample sizes\n'
                '• Instead, it has distinct groups: n=72, n=193, n=464, n=1,580\n'
                '• Each group represents a specific test/panel combination'
            )
        },
        {
            'y': 0.65,
            'title': '2. Mathematical Consequence',
            'content': (
                '• Each sample size creates its own V-shaped curve\n'
                '• Larger n → Taller, narrower V (more statistical power)\n'
                '• Smaller n → Shorter, wider V (less statistical power)\n'
                '• The curves have different heights but all meet at r=0'
            )
        },
        {
            'y': 0.45,
            'title': '3. Visual Result: Banded or Layered Appearance',
            'content': (
                '• Multiple V-curves overlay on the same plot\n'
                '• Creates distinct "bands" or "layers"\n'
                '• NOT a data quality issue - it\'s expected!\n'
                '• Actually helps identify which results are most reliable'
            )
        },
        {
            'y': 0.25,
            'title': '4. Practical Implications',
            'content': (
                '• Results from top bands (large n) are most reliable\n'
                '• Results from bottom bands (small n) need validation\n'
                '• Best findings: consistent across multiple bands\n'
                '• Always report sample size with your correlations'
            )
        }
    ]
    
    for section in sections:
        # Title
        ax.text(0.05, section['y'], section['title'], 
                fontsize=16, fontweight='bold', transform=ax.transAxes,
                color='darkblue')
        
        # Content
        ax.text(0.05, section['y'] - 0.05, section['content'], 
                fontsize=13, transform=ax.transAxes,
                verticalalignment='top')
    
    # Add bottom note
    ax.text(0.5, 0.05, 
            'Remember: Multiple V-patterns are a FEATURE that reveals your data structure, not a bug!',
            fontsize=14, ha='center', transform=ax.transAxes,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.3),
            fontweight='bold')
    
    plt.savefig('multiple_v_patterns_summary.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

if __name__ == "__main__":
    print("Creating clear visualizations for multiple V-patterns...")
    
    # Create separate visualizations
    create_sample_size_table()
    create_v_curves_visualization()
    create_summary_figure()
    
    print("\nGenerated files:")
    print("  - sample_size_matrix_table.png: Clear table showing sample size combinations")
    print("  - v_curves_visualization.png: Side-by-side comparison of individual vs overlapped curves")
    print("  - multiple_v_patterns_summary.png: Summary explanation")
    print("\nThese visualizations clearly show why multiple V-patterns appear in volcano plots!")