# Volcano Plot V-Shape Analysis

This folder contains comprehensive analysis of the V-shaped (or U-shaped) patterns observed in volcano plots from omics-clinical correlations.

## Summary

The multiple V-shapes in volcano plots are **mathematically expected parabolas** arising from the null distribution of Spearman's ρ, where variance = 1/(N-1). Different sample sizes create different parabolas that overlay to create the banded appearance.

## Key Files

### Core Analysis Scripts
- `diagnose_volcano_plot.py` - Initial diagnostic analysis of V-shaped patterns
- `investigate_v_shape.py` - Deep investigation into the mathematical causes
- `comprehensive_volcano_analysis.py` - Full analysis across all omics types
- `demonstrate_v_shape.py` - Synthetic data demonstration proving V-shapes are expected

### Multiple V-Pattern Analysis
- `analyze_multiple_v_patterns.py` - Analysis of why multiple V-patterns appear
- `create_clear_sample_size_visualization.py` - Clear visualizations of sample size effects

### Omics-Specific Analysis
- `metabolites_v_pattern_analysis.py` - Metabolomics-specific V-pattern analysis
- `proteomics_sample_size_analysis.md` - Analysis of proteomics sample size groups

### Mathematical Foundation
- `spearman_null_distribution_explanation.py` - Mathematical proof of parabolic relationship
- `v_shape_mathematical_summary.md` - Concise mathematical explanation

### Documentation
- `volcano_plot_explanation.md` - Original investigation results
- `volcano_plot_v_shape_explained.md` - Comprehensive explanation
- `multiple_v_patterns_explanation.md` - Explanation of multiple V-patterns

## Key Insights

1. **V-shapes are parabolas**: -log₁₀(p) ≈ (N-1)ρ²/4.6
2. **Width depends on sample size**: Width ∝ 1/√(N-1)
3. **Multiple sample sizes → Multiple parabolas**
4. **Proteomics**: Discrete sample sizes (72, 193, 464, 1,582) → Clear bands
5. **Metabolomics**: Continuous sample sizes (10-1,570) → Smooth gradient

## Generated Visualizations

- `sample_size_matrix_table.png` - Table showing how test×panel creates sample sizes
- `v_curves_visualization.png` - Individual vs overlapped V-curves
- `multiple_v_patterns_*.png` - Explanations of multiple V-patterns
- `metabolomics_*.png` - Metabolomics-specific visualizations
- `spearman_*.png` - Mathematical foundation visualizations
- `proteomics_vs_metabolomics_patterns.png` - Direct comparison

## Usage

To regenerate any analysis:
```bash
python [script_name].py
```

Most scripts will create PNG visualizations explaining different aspects of the V-shape phenomenon.