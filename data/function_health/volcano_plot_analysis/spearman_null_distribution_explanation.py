#!/usr/bin/env python3
"""
Mathematical explanation of V-shapes in volcano plots based on Spearman's rho null distribution.
The key insight: Variance of null distribution = 1/(N-1), leading to parabolic relationship.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import matplotlib.patches as patches

# Set style
plt.style.use('seaborn-v0_8-whitegrid')

def create_mathematical_explanation():
    """Create figure showing the mathematical foundation of V-shapes."""
    
    fig = plt.figure(figsize=(18, 12))
    
    # 1. Mathematical derivation
    ax1 = plt.subplot(3, 3, 1)
    ax1.axis('off')
    
    math_text = r"""Mathematical Foundation:

For Spearman's $\rho$ under null hypothesis:
• Mean = 0
• Variance = $\frac{1}{N-1}$

For large N, test statistic:
$z = \rho \sqrt{N-1}$

Therefore:
$-\log_{10}(p) \approx \frac{z^2}{4.6} = \frac{(N-1)\rho^2}{4.6}$

This is a PARABOLA with width $\propto \frac{1}{\sqrt{N-1}}$
"""
    
    ax1.text(0.05, 0.95, math_text, transform=ax1.transAxes, 
             fontsize=12, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    # 2. Variance visualization
    ax2 = plt.subplot(3, 3, 2)
    n_values = np.arange(10, 2000, 10)
    variance = 1 / (n_values - 1)
    
    ax2.plot(n_values, variance, 'b-', linewidth=2)
    ax2.set_xlabel('Sample Size (N)', fontsize=12)
    ax2.set_ylabel('Variance of Null Distribution', fontsize=12)
    ax2.set_title('Variance = 1/(N-1)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add specific points
    for n in [50, 200, 500, 1500]:
        var = 1/(n-1)
        ax2.plot(n, var, 'ro', markersize=8)
        ax2.annotate(f'N={n}\nVar={var:.4f}', xy=(n, var), 
                    xytext=(n+100, var+0.001),
                    arrowprops=dict(arrowstyle='->', color='red'))
    
    # 3. Standard deviation (width of distribution)
    ax3 = plt.subplot(3, 3, 3)
    std_dev = np.sqrt(variance)
    
    ax3.plot(n_values, std_dev, 'g-', linewidth=2)
    ax3.set_xlabel('Sample Size (N)', fontsize=12)
    ax3.set_ylabel('Std Dev of Null Distribution', fontsize=12)
    ax3.set_title('Std Dev = 1/√(N-1)', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # 4. Parabolic relationship visualization
    ax4 = plt.subplot(3, 3, 4)
    
    rho_range = np.linspace(-0.6, 0.6, 1000)
    
    for n, color, label in [(50, 'red', 'N=50'), 
                            (200, 'orange', 'N=200'), 
                            (500, 'green', 'N=500'), 
                            (1500, 'blue', 'N=1500')]:
        # Using the parabolic approximation
        log_p_approx = (n - 1) * rho_range**2 / 4.6
        ax4.plot(rho_range, log_p_approx, color=color, linewidth=2.5, 
                label=f'{label} (width ∝ 1/√{n-1:.0f})')
    
    ax4.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5)
    ax4.set_xlabel('Spearman ρ', fontsize=12)
    ax4.set_ylabel('-log₁₀(p)', fontsize=12)
    ax4.set_title('Parabolic Approximation: -log₁₀(p) ≈ (N-1)ρ²/4.6', fontsize=14, fontweight='bold')
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 10)
    
    # 5. Exact vs approximation comparison
    ax5 = plt.subplot(3, 3, 5)
    
    n = 200
    # Exact calculation using t-distribution
    t_values = rho_range * np.sqrt(n - 2) / np.sqrt(1 - rho_range**2)
    p_exact = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
    
    # Parabolic approximation
    z_approx = rho_range * np.sqrt(n - 1)
    p_approx = 2 * (1 - stats.norm.cdf(np.abs(z_approx)))
    
    ax5.plot(rho_range, -np.log10(p_exact), 'b-', linewidth=2, label='Exact (t-distribution)')
    ax5.plot(rho_range, -np.log10(p_approx), 'r--', linewidth=2, label='Approximation (normal)')
    ax5.set_xlabel('Spearman ρ', fontsize=12)
    ax5.set_ylabel('-log₁₀(p)', fontsize=12)
    ax5.set_title(f'Exact vs Approximation (N={n})', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.set_ylim(0, 8)
    
    # 6. Width scaling visualization
    ax6 = plt.subplot(3, 3, 6)
    
    # Calculate width at p=0.05 for different N
    p_threshold = 0.05
    z_threshold = stats.norm.ppf(1 - p_threshold/2)
    
    n_values_plot = np.logspace(1.5, 3.2, 50)
    rho_threshold = z_threshold / np.sqrt(n_values_plot - 1)
    
    ax6.plot(n_values_plot, rho_threshold, 'purple', linewidth=3)
    ax6.set_xlabel('Sample Size (N)', fontsize=12)
    ax6.set_ylabel('|ρ| at p=0.05', fontsize=12)
    ax6.set_title('V-Shape Width: |ρ| threshold ∝ 1/√(N-1)', fontsize=14, fontweight='bold')
    ax6.set_xscale('log')
    ax6.grid(True, alpha=0.3)
    
    # Add annotations
    for n in [50, 200, 1000]:
        rho_val = z_threshold / np.sqrt(n - 1)
        ax6.plot(n, rho_val, 'ro', markersize=8)
        ax6.annotate(f'N={n}\n|ρ|={rho_val:.3f}', xy=(n, rho_val),
                    xytext=(n*1.5, rho_val*1.1))
    
    # 7. Null distribution visualization
    ax7 = plt.subplot(3, 3, 7)
    
    # Show null distributions for different N
    rho_dist = np.linspace(-0.5, 0.5, 1000)
    
    for n, color in [(50, 'red'), (200, 'orange'), (1000, 'blue')]:
        variance = 1/(n-1)
        std = np.sqrt(variance)
        pdf = stats.norm.pdf(rho_dist, 0, std)
        ax7.plot(rho_dist, pdf, color=color, linewidth=2, label=f'N={n}')
        ax7.fill_between(rho_dist, 0, pdf, alpha=0.2, color=color)
    
    ax7.set_xlabel('Spearman ρ', fontsize=12)
    ax7.set_ylabel('Probability Density', fontsize=12)
    ax7.set_title('Null Distribution of Spearman ρ', fontsize=14, fontweight='bold')
    ax7.legend()
    ax7.grid(True, alpha=0.3)
    
    # 8. Key insight summary
    ax8 = plt.subplot(3, 3, 8)
    ax8.axis('off')
    
    insight_text = """KEY INSIGHTS:

1. Only parameter in null distribution: N
   Var(ρ) = 1/(N-1)

2. V-shape is a PARABOLA
   -log₁₀(p) ≈ (N-1)ρ²/4.6

3. Width of V ∝ 1/√(N-1)
   • Large N → Narrow V
   • Small N → Wide V

4. Multiple sample sizes →
   Multiple parabolas →
   Multiple V-patterns!
"""
    
    ax8.text(0.1, 0.9, insight_text, transform=ax8.transAxes,
             fontsize=13, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
             fontweight='bold')
    
    # 9. Visual demonstration of multiple parabolas
    ax9 = plt.subplot(3, 3, 9)
    
    rho_range_demo = np.linspace(-0.4, 0.4, 1000)
    
    # Sample sizes from your data
    sample_sizes = [72, 193, 464, 1582]
    colors = plt.cm.viridis(np.linspace(0, 1, len(sample_sizes)))
    
    for n, color in zip(sample_sizes, colors):
        # Parabolic relationship
        log_p = (n - 1) * rho_range_demo**2 / 4.6
        ax9.plot(rho_range_demo, log_p, color=color, linewidth=3, 
                label=f'N={n}', alpha=0.8)
        
        # Add some scattered points
        n_points = 50
        rho_scatter = np.random.normal(0, 0.05, n_points)
        log_p_scatter = (n - 1) * rho_scatter**2 / 4.6 + np.random.normal(0, 0.1, n_points)
        ax9.scatter(rho_scatter, log_p_scatter, color=color, alpha=0.3, s=20)
    
    ax9.axhline(y=-np.log10(0.05), color='red', linestyle='--', alpha=0.5)
    ax9.set_xlabel('Spearman ρ', fontsize=12)
    ax9.set_ylabel('-log₁₀(p)', fontsize=12)
    ax9.set_title('Multiple Parabolas = Multiple V-Patterns', fontsize=14, fontweight='bold')
    ax9.legend()
    ax9.grid(True, alpha=0.3)
    ax9.set_ylim(0, 6)
    
    plt.tight_layout()
    plt.savefig('spearman_null_distribution_explanation.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_simplified_explanation():
    """Create a simplified, focused explanation."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Left: The mathematical relationship
    ax1.text(0.5, 0.95, 'The Mathematics of V-Shapes', 
             fontsize=18, fontweight='bold', ha='center', transform=ax1.transAxes)
    
    # Draw the key equations
    equations = [
        (0.5, 0.8, r'Null distribution variance: $\sigma^2 = \frac{1}{N-1}$', 20),
        (0.5, 0.65, r'Test statistic: $z = \rho\sqrt{N-1}$', 18),
        (0.5, 0.5, r'Therefore: $-\log_{10}(p) \approx \frac{z^2}{4.6} = \frac{(N-1)\rho^2}{4.6}$', 18),
        (0.5, 0.35, r'This is a PARABOLA!', 20),
        (0.5, 0.2, r'Width $\propto \frac{1}{\sqrt{N-1}}$', 18),
    ]
    
    for x, y, text, size in equations:
        if 'PARABOLA' in text:
            ax1.text(x, y, text, fontsize=size, fontweight='bold', 
                    ha='center', transform=ax1.transAxes,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        else:
            ax1.text(x, y, text, fontsize=size, ha='center', transform=ax1.transAxes)
    
    ax1.axis('off')
    
    # Right: Visual demonstration
    rho = np.linspace(-0.5, 0.5, 1000)
    
    # Show parabolas for different N
    for n, color, width in [(50, 'red', 3), 
                           (200, 'orange', 2.5), 
                           (500, 'green', 2), 
                           (1500, 'blue', 1.5)]:
        # The parabolic relationship
        log_p = (n - 1) * rho**2 / 4.6
        
        ax2.plot(rho, log_p, color=color, linewidth=width, 
                label=f'N={n}: width ∝ 1/√{n-1:.0f} = {1/np.sqrt(n-1):.3f}')
    
    ax2.axhline(y=-np.log10(0.05), color='black', linestyle='--', alpha=0.5, label='p=0.05')
    ax2.set_xlabel('Spearman ρ', fontsize=16)
    ax2.set_ylabel('-log₁₀(p)', fontsize=16)
    ax2.set_title('Each Sample Size Creates Its Own Parabola', fontsize=18, fontweight='bold')
    ax2.legend(fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-0.5, 0.5)
    ax2.set_ylim(0, 8)
    
    # Add width annotations
    ax2.annotate('', xy=(0.28, 0.5), xytext=(-0.28, 0.5),
                arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax2.text(0, 0.3, 'Wide\n(N=50)', ha='center', fontsize=12, color='red')
    
    ax2.annotate('', xy=(0.08, 4), xytext=(-0.08, 4),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    ax2.text(0, 3.8, 'Narrow\n(N=1500)', ha='center', fontsize=12, color='blue')
    
    plt.tight_layout()
    plt.savefig('spearman_parabola_simple.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    print("Creating mathematical explanation of V-shapes based on Spearman's null distribution...")
    
    create_mathematical_explanation()
    create_simplified_explanation()
    
    print("\nGenerated files:")
    print("  - spearman_null_distribution_explanation.png: Comprehensive mathematical explanation")
    print("  - spearman_parabola_simple.png: Simplified visualization")
    print("\nThe V-shapes are parabolas because -log(p) ∝ (N-1)ρ²!")