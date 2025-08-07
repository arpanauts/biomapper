#!/usr/bin/env python3
"""
Analyze and visualize the V-pattern phenomenon specifically for metabolomics data.
Metabolites show a different pattern due to more variable sample sizes.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import matplotlib.patches as patches
import seaborn as sns

# Set style
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")


def create_metabolomics_sample_size_table():
    """Create a table showing metabolomics sample size variations."""

    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.axis("off")

    # Title
    ax.text(
        0.5,
        0.95,
        "Metabolomics Sample Size Patterns: More Variable Than Proteomics",
        fontsize=18,
        fontweight="bold",
        ha="center",
        transform=ax.transAxes,
    )

    # Create table data
    table_data = [
        [
            "Clinical Test",
            "Coverage",
            "×",
            "Metabolite",
            "Coverage",
            "→",
            "Expected n",
            "→",
            "V-curve Characteristic",
        ],
        ["─" * 15, "─" * 8, " ", "─" * 15, "─" * 8, " ", "─" * 12, " ", "─" * 20],
        [
            "GLUCOSE",
            "95%",
            "×",
            "Most metabolites",
            "~90%",
            "→",
            "n ≈ 1,400-1,570",
            "→",
            "Very tall, narrow V",
        ],
        [
            "CHOLESTEROL",
            "95%",
            "×",
            "Most metabolites",
            "~90%",
            "→",
            "n ≈ 1,400-1,570",
            "→",
            "Very tall, narrow V",
        ],
        [
            "TRIGLYCERIDES",
            "92%",
            "×",
            "Common metabolites",
            "~85%",
            "→",
            "n ≈ 1,200-1,400",
            "→",
            "Tall, narrow V",
        ],
        [
            "ALBUMIN",
            "90%",
            "×",
            "Variable coverage",
            "10-90%",
            "→",
            "n ≈ 100-1,400",
            "→",
            "Multiple overlapping Vs",
        ],
        [
            "BILIRUBIN, DIRECT",
            "30%",
            "×",
            "Most metabolites",
            "~90%",
            "→",
            "n ≈ 400-500",
            "→",
            "Medium height V",
        ],
        [
            "COPPER, RBC",
            "30%",
            "×",
            "Variable coverage",
            "10-90%",
            "→",
            "n ≈ 50-450",
            "→",
            "Wide range of Vs",
        ],
        [
            "SELENIUM",
            "25%",
            "×",
            "Rare metabolites",
            "~10%",
            "→",
            "n ≈ 30-50",
            "→",
            "Very wide, short V",
        ],
        [
            "Leptin",
            "10%",
            "×",
            "Any metabolite",
            "varies",
            "→",
            "n ≈ 10-165",
            "→",
            "Lowest, widest Vs",
        ],
    ]

    # Position for table
    y_start = 0.82
    row_height = 0.07

    # Column positions
    col_positions = [0.03, 0.18, 0.26, 0.30, 0.45, 0.53, 0.58, 0.71, 0.76]

    # Draw table
    for i, row in enumerate(table_data):
        y_pos = y_start - i * row_height

        # Header row styling
        if i == 0:
            rect = patches.Rectangle(
                (0.02, y_pos - 0.02),
                0.96,
                row_height,
                facecolor="lightcoral",
                alpha=0.3,
                transform=ax.transAxes,
            )
            ax.add_patch(rect)
            fontweight = "bold"
            fontsize = 12
        elif i == 1:
            fontweight = "normal"
            fontsize = 10
        else:
            fontweight = "normal"
            fontsize = 11

            # Alternate row coloring
            if (i - 2) % 2 == 1:
                rect = patches.Rectangle(
                    (0.02, y_pos - 0.02),
                    0.96,
                    row_height,
                    facecolor="gray",
                    alpha=0.1,
                    transform=ax.transAxes,
                )
                ax.add_patch(rect)

        # Draw each cell
        for j, (text, x_pos) in enumerate(zip(row, col_positions)):
            # Color coding for sample sizes
            if j == 6 and i > 1:  # Sample size column
                if "1,400" in text or "1,570" in text:
                    color = "darkgreen"
                elif "400" in text or "500" in text:
                    color = "darkorange"
                elif "100" in text or "200" in text:
                    color = "darkblue"
                elif "30" in text or "50" in text:
                    color = "darkred"
                else:
                    color = "purple"
            else:
                color = "black"

            ax.text(
                x_pos,
                y_pos,
                text,
                fontsize=fontsize,
                fontweight=fontweight,
                transform=ax.transAxes,
                color=color,
            )

    # Add key differences box
    diff_y = 0.15
    differences_text = (
        "Key Differences from Proteomics:\n"
        + "• Metabolomics has MORE VARIABLE sample sizes (n = 10 to 1,570)\n"
        + "• Coverage varies continuously rather than in discrete groups\n"
        + '• Results in a SMOOTHER, less "banded" V-pattern\n'
        + "• Still shows multiple Vs, but they blend together more"
    )

    ax.text(
        0.5,
        diff_y,
        differences_text,
        fontsize=13,
        ha="center",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8),
    )

    plt.savefig(
        "metabolomics_sample_size_table.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()


def create_metabolomics_v_curves():
    """Create visualization showing metabolomics V-curve patterns."""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Left plot: Representative V-curves for metabolomics
    r_range = np.linspace(-0.8, 0.8, 1000)

    # Define representative sample sizes for metabolomics
    # More varied than proteomics
    sample_groups = [
        (1500, "n≈1,500 (Well-measured test + common metabolite)", "darkgreen"),
        (1200, "n≈1,200", "#228B22"),
        (800, "n≈800", "#FFA500"),
        (500, "n≈500 (Sparse test + common metabolite)", "darkorange"),
        (200, "n≈200", "darkblue"),
        (100, "n≈100", "#4169E1"),
        (50, "n≈50 (Sparse test + rare metabolite)", "darkred"),
    ]

    for n, label, color in sample_groups:
        t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
        p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))

        # Only show label for key sizes
        if n in [1500, 500, 50]:
            ax1.plot(
                r_range,
                -np.log10(p_theoretical),
                color=color,
                linewidth=2.5,
                label=label,
                alpha=0.8,
            )
        else:
            ax1.plot(
                r_range, -np.log10(p_theoretical), color=color, linewidth=1.5, alpha=0.5
            )

    ax1.axhline(
        y=-np.log10(0.05),
        color="black",
        linestyle="--",
        alpha=0.5,
        label="p=0.05 threshold",
    )
    ax1.set_xlabel("Correlation (r)", fontsize=14)
    ax1.set_ylabel("-log10(p-value)", fontsize=14)
    ax1.set_title(
        "Metabolomics: More Sample Size Variation", fontsize=16, fontweight="bold"
    )
    ax1.legend(loc="upper right", fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(-0.8, 0.8)
    ax1.set_ylim(0, 10)

    # Right plot: Simulated metabolomics volcano plot
    # Generate data with continuous sample size variation
    np.random.seed(42)

    all_r = []
    all_p = []
    all_n = []

    # Generate correlations with varied sample sizes
    # More continuous distribution than proteomics
    for _ in range(5000):
        # Sample size distribution for metabolomics
        # Bimodal but with more intermediate values
        if np.random.random() < 0.6:
            # High coverage metabolites
            n = int(np.random.normal(1400, 200))
            n = np.clip(n, 800, 1570)
        elif np.random.random() < 0.8:
            # Medium coverage
            n = int(np.random.normal(500, 150))
            n = np.clip(n, 200, 800)
        else:
            # Low coverage
            n = int(np.random.normal(100, 50))
            n = np.clip(n, 10, 200)

        # Generate correlation (mostly null)
        if np.random.random() < 0.02:  # 2% true correlations
            r = np.random.choice([-1, 1]) * np.random.uniform(0.3, 0.8)
        else:
            r = np.random.normal(0, 0.05)

        # Calculate p-value
        if abs(r) < 0.9999:
            t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
            p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
        else:
            p = 0

        all_r.append(r)
        all_p.append(p)
        all_n.append(n)

    # Convert to arrays
    all_r = np.array(all_r)
    all_p = np.array(all_p)
    all_n = np.array(all_n)

    # Plot with color by sample size
    scatter = ax2.scatter(
        all_r,
        -np.log10(all_p),
        c=all_n,
        cmap="viridis",
        alpha=0.4,
        s=10,
        edgecolor="none",
    )
    plt.colorbar(scatter, ax=ax2, label="Sample Size (n)")

    ax2.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Correlation (r)", fontsize=14)
    ax2.set_ylabel("-log10(p-value)", fontsize=14)
    ax2.set_title(
        "Metabolomics Volcano Plot Pattern\n(Smoother gradient, less discrete bands)",
        fontsize=16,
        fontweight="bold",
    )
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-0.8, 0.8)
    ax2.set_ylim(0, 10)

    # Add annotations
    ax2.text(
        0.5,
        8.5,
        "High n region\n(continuous)",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8),
    )
    ax2.text(
        0.5,
        4,
        "Mixed n region\n(gradient)",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
    )
    ax2.text(
        0.5,
        1.5,
        "Low n region\n(sparse)",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="lightcoral", alpha=0.8),
    )

    plt.tight_layout()
    plt.savefig(
        "metabolomics_v_curves.png", dpi=300, bbox_inches="tight", facecolor="white"
    )
    plt.close()


def create_proteomics_vs_metabolomics_comparison():
    """Create a direct comparison of proteomics vs metabolomics V-patterns."""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Proteomics pattern (discrete)
    np.random.seed(42)

    # Discrete sample sizes for proteomics
    prot_sample_sizes = [72, 193, 464, 1582]
    prot_r = []
    prot_p = []
    prot_n = []

    for n in prot_sample_sizes:
        n_points = 300
        r_vals = np.random.normal(0, 0.08, n_points)

        # Add some outliers
        n_outliers = int(n_points * 0.02)
        outlier_idx = np.random.choice(n_points, n_outliers, replace=False)
        r_vals[outlier_idx] = np.random.choice([-1, 1]) * np.random.uniform(
            0.3, 0.7, n_outliers
        )

        for r in r_vals:
            if abs(r) < 0.9999:
                t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
                p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
            else:
                p = 0

            prot_r.append(r)
            prot_p.append(p)
            prot_n.append(n)

    scatter1 = ax1.scatter(
        prot_r,
        -np.log10(prot_p),
        c=prot_n,
        cmap="viridis",
        alpha=0.5,
        s=20,
        edgecolor="none",
    )
    cbar1 = plt.colorbar(scatter1, ax=ax1, label="Sample Size (n)")
    cbar1.set_ticks([72, 193, 464, 1582])

    ax1.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
    ax1.set_xlabel("Correlation (r)", fontsize=14)
    ax1.set_ylabel("-log10(p-value)", fontsize=14)
    ax1.set_title(
        'Proteomics: Discrete Sample Size Groups\n→ Clear "Banded" Pattern',
        fontsize=16,
        fontweight="bold",
    )
    ax1.set_xlim(-0.8, 0.8)
    ax1.set_ylim(0, 8)

    # Add text showing discrete groups
    ax1.text(
        0.95,
        0.95,
        "Discrete n values:\n72, 193, 464, 1582",
        transform=ax1.transAxes,
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        verticalalignment="top",
        horizontalalignment="right",
    )

    # Metabolomics pattern (continuous)
    metab_r = []
    metab_p = []
    metab_n = []

    # Continuous sample size distribution
    for _ in range(1200):
        # More continuous distribution
        rand = np.random.random()
        if rand < 0.5:
            n = int(np.random.normal(1400, 150))
        elif rand < 0.8:
            n = int(np.random.normal(700, 200))
        else:
            n = int(np.random.normal(200, 100))

        n = np.clip(n, 10, 1570)

        # Generate correlation
        if np.random.random() < 0.02:
            r = np.random.choice([-1, 1]) * np.random.uniform(0.3, 0.8)
        else:
            r = np.random.normal(0, 0.06)

        if abs(r) < 0.9999:
            t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
            p = 2 * (1 - stats.t.cdf(abs(t), n - 2))
        else:
            p = 0

        metab_r.append(r)
        metab_p.append(p)
        metab_n.append(n)

    scatter2 = ax2.scatter(
        metab_r,
        -np.log10(metab_p),
        c=metab_n,
        cmap="plasma",
        alpha=0.5,
        s=20,
        edgecolor="none",
    )
    plt.colorbar(scatter2, ax=ax2, label="Sample Size (n)")

    ax2.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
    ax2.set_xlabel("Correlation (r)", fontsize=14)
    ax2.set_ylabel("-log10(p-value)", fontsize=14)
    ax2.set_title(
        'Metabolomics: Continuous Sample Size Range\n→ Smooth "Gradient" Pattern',
        fontsize=16,
        fontweight="bold",
    )
    ax2.set_xlim(-0.8, 0.8)
    ax2.set_ylim(0, 8)

    # Add text showing continuous range
    ax2.text(
        0.95,
        0.95,
        "Continuous n range:\n10 to 1,570",
        transform=ax2.transAxes,
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        verticalalignment="top",
        horizontalalignment="right",
    )

    plt.tight_layout()
    plt.savefig(
        "proteomics_vs_metabolomics_patterns.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()


def create_metabolomics_summary():
    """Create a summary figure for metabolomics V-patterns."""

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.axis("off")

    # Title
    ax.text(
        0.5,
        0.95,
        "Metabolomics V-Pattern Characteristics",
        fontsize=20,
        fontweight="bold",
        ha="center",
        transform=ax.transAxes,
    )

    # Main sections
    sections = [
        {
            "y": 0.85,
            "title": "1. Why Metabolomics Looks Different",
            "content": (
                "• Sample sizes vary CONTINUOUSLY from n=10 to n=1,570\n"
                "• Metabolite coverage is highly variable (10% to 90%)\n"
                "• Clinical test coverage also varies widely\n"
                "• Result: Smooth gradient rather than discrete bands"
            ),
        },
        {
            "y": 0.65,
            "title": "2. The V-Pattern Still Exists",
            "content": (
                "• Same mathematical relationship applies\n"
                "• Multiple V-curves are present but blend together\n"
                '• Creates a "filled-in" appearance\n'
                "• Outliers (true correlations) still visible above the V"
            ),
        },
        {
            "y": 0.45,
            "title": "3. Interpretation Guidelines",
            "content": (
                "• Color-code by sample size to see the pattern\n"
                "• High-n correlations (n>1000) are most reliable\n"
                "• Low-n correlations (n<100) need careful validation\n"
                "• Look for biological consistency (e.g., glucose vs glucose metabolite)"
            ),
        },
        {
            "y": 0.25,
            "title": "4. Known Positive Controls in Metabolomics",
            "content": (
                "• GLUCOSE vs glucose metabolite (r≈0.84)\n"
                "• CREATININE vs creatinine metabolite (r≈0.80)\n"
                "• URIC ACID vs urate (r≈0.84)\n"
                "• These appear as clear outliers above the V-pattern"
            ),
        },
    ]

    for section in sections:
        # Title
        ax.text(
            0.05,
            section["y"],
            section["title"],
            fontsize=16,
            fontweight="bold",
            transform=ax.transAxes,
            color="darkblue",
        )

        # Content
        ax.text(
            0.05,
            section["y"] - 0.05,
            section["content"],
            fontsize=13,
            transform=ax.transAxes,
            verticalalignment="top",
        )

    # Add comparison box
    ax.text(
        0.5,
        0.08,
        "Key Difference: Proteomics has DISCRETE sample size groups → Clear bands\n"
        + "Metabolomics has CONTINUOUS sample size variation → Smooth gradient",
        fontsize=14,
        ha="center",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightcoral", alpha=0.3),
        fontweight="bold",
    )

    plt.savefig(
        "metabolomics_v_pattern_summary.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()


if __name__ == "__main__":
    print("Creating metabolomics-specific V-pattern analysis...")

    # Create visualizations
    create_metabolomics_sample_size_table()
    create_metabolomics_v_curves()
    create_proteomics_vs_metabolomics_comparison()
    create_metabolomics_summary()

    print("\nGenerated files:")
    print(
        "  - metabolomics_sample_size_table.png: Sample size patterns in metabolomics"
    )
    print("  - metabolomics_v_curves.png: V-curve patterns specific to metabolomics")
    print("  - proteomics_vs_metabolomics_patterns.png: Direct comparison")
    print("  - metabolomics_v_pattern_summary.png: Summary and interpretation guide")
    print(
        "\nMetabolomics shows smoother V-patterns due to continuous sample size variation!"
    )
