# Volcano Plot V-Shape Investigation Results

## Executive Summary

The V-shaped patterns observed in the volcano plots are **NOT a bug or data quality issue**. They are the expected statistical pattern when analyzing correlations between mostly unrelated biological variables with consistent sample sizes.

## Key Findings

### 1. Data Quality Check ✓
- **No proteins with zero variance**: All 1,195 proteomics features show variation
- **No missing value issues**: Data is properly loaded and merged
- **Sample sizes are reasonable**: Most correlations use 72-464 samples for proteomics, 1,400+ for metabolomics

### 2. Statistical Explanation

The V-shape occurs because:

1. **Most correlations are near zero** (as expected for unrelated biological features)
   - Proteomics: Mean r = 0.003, median r = 0.002
   - Metabolomics: Mean r = 0.014, median r = 0.008

2. **Consistent sample sizes create predictable r-p relationships**
   - For BILIRUBIN, DIRECT: 77% of proteomics correlations use n=72 samples
   - This creates a mathematical relationship: p-value = f(r, n)
   - The V-shape is the visualization of this relationship

3. **The statistical test is working correctly**
   - Manual calculations confirm the automated results
   - The pattern matches theoretical expectations perfectly

### 3. Specific Example: BILIRUBIN, DIRECT

Investigation revealed:
- BILIRUBIN, DIRECT has only 6 unique values (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
- This discrete nature contributes to the pattern but doesn't invalidate correlations
- The V-shape is still present with continuous variables like GLUCOSE

### 4. Biological Interpretation

The V-shape actually helps identify meaningful correlations:
- Points that deviate from the V-pattern are the biologically interesting findings
- 32,917 correlations are statistically significant (FDR < 0.05)
- 1,798 are both significant AND have meaningful effect sizes (|r| > 0.3)

## Visualization Examples

### Theoretical vs Actual Volcano Plot
For n=72 samples (most common in proteomics), the theoretical curve perfectly matches the observed V-shape:
- Small correlations (|r| < 0.1) cluster at the bottom of the V
- Larger correlations climb the sides of the V
- The apex at r=0 represents the null hypothesis

### Why Proteomics Shows Sharper V than Metabolomics
1. **Smaller, consistent sample sizes** in proteomics (mostly n=72)
2. **Larger, varied sample sizes** in metabolomics (n=10-1570)
3. Larger sample sizes create a narrower, taller V-shape

## Recommendations

1. **No action needed** - the V-shape is correct and expected
2. **Focus on the outliers** - correlations that deviate from the V are the interesting findings
3. **Consider effect size filters** - use both p-value and correlation strength (|r| > 0.3)
4. **The current analysis is valid** - the 1,798 significant correlations with |r| > 0.3 are real findings

## Top Findings Remain Valid

The strongest correlations identified are biologically plausible:
- UREA NITROGEN vs urea metabolite (r=0.86)
- URIC ACID vs urate metabolite (r=0.84)
- GLUCOSE vs glucose metabolite (r=0.84)
- CREATININE vs creatinine metabolite (r=0.80)

These strong correlations between clinical tests and their corresponding metabolites serve as positive controls, validating the analysis approach.

## Conclusion

The V-shaped volcano plots are a sign that the correlation analysis is working correctly, not a problem to be fixed. The pattern emerges from the statistical properties of correlation testing with consistent sample sizes and mostly null relationships—exactly what we expect in large-scale omics analyses.