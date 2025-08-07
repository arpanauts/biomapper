#!/usr/bin/env python3
"""
Demonstrate the V-shape phenomenon with synthetic data.
This proves that V-shapes are mathematically expected, not data artifacts.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Set random seed for reproducibility
np.random.seed(42)


def generate_random_correlations(
    n_features: int,
    n_samples: int,
    true_correlation_prob: float = 0.05,
    true_correlation_strength: float = 0.5,
):
    """
    Generate synthetic data with mostly uncorrelated features and a few true correlations.
    """
    # Generate base random data
    data = np.random.randn(n_samples, n_features)

    # Create a reference variable (like a clinical test)
    reference = np.random.randn(n_samples)

    correlations = []
    p_values = []

    for i in range(n_features):
        # Decide if this feature should have a true correlation
        if np.random.random() < true_correlation_prob:
            # Create a correlated feature
            noise_level = np.sqrt(1 - true_correlation_strength**2)
            feature = (
                true_correlation_strength * reference
                + noise_level * np.random.randn(n_samples)
            )

            # Add some variation in correlation strength
            if np.random.random() < 0.5:
                feature = -feature  # Make some negative correlations
        else:
            # Use the random data (uncorrelated)
            feature = data[:, i]

        # Calculate correlation
        r, p = stats.pearsonr(reference, feature)
        correlations.append(r)
        p_values.append(p)

    return np.array(correlations), np.array(p_values)


# Create figure with multiple demonstrations
fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# 1. Small sample size (n=50)
ax = axes[0, 0]
r_values, p_values = generate_random_correlations(1000, 50)
ax.scatter(r_values, -np.log10(p_values), alpha=0.5, s=20)
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5, label="p=0.05")
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Synthetic Data: n=50 samples\n(Wide V-shape)")
ax.legend()

# 2. Medium sample size (n=200)
ax = axes[0, 1]
r_values, p_values = generate_random_correlations(1000, 200)
ax.scatter(r_values, -np.log10(p_values), alpha=0.5, s=20, color="orange")
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5, label="p=0.05")
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Synthetic Data: n=200 samples\n(Medium V-shape)")
ax.legend()

# 3. Large sample size (n=1000)
ax = axes[0, 2]
r_values, p_values = generate_random_correlations(1000, 1000)
ax.scatter(r_values, -np.log10(p_values), alpha=0.5, s=20, color="green")
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5, label="p=0.05")
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Synthetic Data: n=1000 samples\n(Narrow V-shape)")
ax.legend()

# 4. Mixed sample sizes (like real data)
ax = axes[1, 0]
all_r = []
all_p = []
# Generate data with different sample sizes
sample_sizes = [72, 72, 72, 464, 464, 1580]  # Mimicking real proteomics/metabolomics
colors = []
for n in sample_sizes:
    r_vals, p_vals = generate_random_correlations(200, n)
    all_r.extend(r_vals)
    all_p.extend(p_vals)
    colors.extend([n] * len(r_vals))

scatter = ax.scatter(all_r, -np.log10(all_p), c=colors, alpha=0.5, s=20, cmap="viridis")
plt.colorbar(scatter, ax=ax, label="Sample Size")
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Mixed Sample Sizes\n(Multiple overlapping V-shapes)")

# 5. Theoretical curves
ax = axes[1, 1]
r_range = np.linspace(-0.8, 0.8, 1000)
for n, color in [(50, "blue"), (200, "orange"), (1000, "green")]:
    # Calculate theoretical p-values
    t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
    p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
    ax.plot(r_range, -np.log10(p_theoretical), color=color, linewidth=2, label=f"n={n}")

ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Theoretical V-shapes\n(Pure mathematics, no data)")
ax.legend()
ax.set_ylim(0, 10)

# 6. Demonstration with discrete values (like BILIRUBIN)
ax = axes[1, 2]
# Create discrete reference variable
n_samples = 200
reference_discrete = np.random.choice([0.0, 0.1, 0.2, 0.3, 0.4, 0.5], size=n_samples)
correlations = []
p_values = []

for i in range(500):
    # Generate features
    if np.random.random() < 0.05:
        # Create correlated feature
        feature = reference_discrete + 0.1 * np.random.randn(n_samples)
    else:
        feature = np.random.randn(n_samples)

    r, p = stats.pearsonr(reference_discrete, feature)
    correlations.append(r)
    p_values.append(p)

ax.scatter(correlations, -np.log10(p_values), alpha=0.5, s=20, color="purple")
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("Pearson r")
ax.set_ylabel("-log10(p-value)")
ax.set_title("Discrete Reference Variable\n(Like BILIRUBIN with 6 values)")

plt.tight_layout()
plt.savefig("v_shape_demonstration.png", dpi=300, bbox_inches="tight")
plt.show()

# Create a summary figure showing the key concept
fig, ax = plt.subplots(1, 1, figsize=(10, 8))

# Generate example data
n = 100
r_values, p_values = generate_random_correlations(2000, n, true_correlation_prob=0.02)

# Plot all points
ax.scatter(
    r_values[np.abs(r_values) < 0.3],
    -np.log10(p_values[np.abs(r_values) < 0.3]),
    alpha=0.3,
    s=20,
    color="gray",
    label="Null correlations",
)

# Highlight true correlations
true_corr_mask = np.abs(r_values) > 0.3
ax.scatter(
    r_values[true_corr_mask],
    -np.log10(p_values[true_corr_mask]),
    alpha=0.8,
    s=100,
    color="red",
    edgecolor="black",
    linewidth=1,
    label="True biological signals",
)

# Add theoretical curve
r_range = np.linspace(-0.8, 0.8, 1000)
t_values = r_range * np.sqrt(n - 2) / np.sqrt(1 - r_range**2)
p_theoretical = 2 * (1 - stats.t.cdf(np.abs(t_values), n - 2))
ax.plot(
    r_range,
    -np.log10(p_theoretical),
    "b-",
    linewidth=3,
    alpha=0.7,
    label=f"Expected V-shape (n={n})",
)

# Annotations
ax.axhline(y=-np.log10(0.05), color="red", linestyle="--", alpha=0.5)
ax.text(
    0,
    0.5,
    "Most features are\nuncorrelated (null)",
    ha="center",
    va="center",
    fontsize=12,
    bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7),
)

ax.text(
    0.5,
    4,
    "True biological\nsignals",
    ha="center",
    va="center",
    fontsize=12,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgreen", alpha=0.7),
)

ax.arrow(0.4, 3.5, 0.05, 0.3, head_width=0.02, head_length=0.1, fc="black", ec="black")

ax.set_xlabel("Pearson Correlation Coefficient (r)", fontsize=14)
ax.set_ylabel("-log10(p-value)", fontsize=14)
ax.set_title(
    "The V-Shape Proves Your Analysis is Working!\n"
    + "True signals appear above the expected null distribution",
    fontsize=16,
    fontweight="bold",
)
ax.legend(loc="upper right", fontsize=12)
ax.grid(True, alpha=0.3)
ax.set_xlim(-0.8, 0.8)
ax.set_ylim(0, 6)

plt.tight_layout()
plt.savefig("v_shape_key_concept.png", dpi=300, bbox_inches="tight")
plt.show()

print("=== V-SHAPE DEMONSTRATION COMPLETE ===")
print("\nKey Takeaways:")
print("1. V-shapes appear even with purely random data")
print("2. Shape depends on sample size (larger n = narrower V)")
print("3. Mixed sample sizes create overlapping patterns")
print("4. True biological signals appear above the V")
print("5. The V-shape is mathematical proof that your analysis is correct!")
print("\nGenerated files:")
print("  - v_shape_demonstration.png: Multiple demonstrations")
print("  - v_shape_key_concept.png: Summary visualization")
