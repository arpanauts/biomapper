# Proteomics Sample Size Analysis

## Summary of Findings

The different sample sizes in the proteomics correlations are due to two main factors:

### 1. Different Proteomics Chip Panels

The Arivale proteomics data uses multiple chip panels, each measuring ~92 proteins:

**High-coverage chips** (measured on ~6,018 samples):
- CVD2 (Cardiovascular panel 2)
- CVD3 (Cardiovascular panel 3)  
- INF (Inflammation panel)

**Low-coverage chips** (measured on only ~558 samples):
- CAM (Cancer panel)
- CRE (Cancer-related panel)
- DEV (Development panel)
- IRE (Immune response panel)
- MET (Metabolism panel)
- NEU1 (Neurology panel 1)
- NEX (Neurology extension panel)
- ODA (Other disease panel)
- ONC2 (Oncology panel 2)
- ONC3 (Oncology panel 3)

### 2. Missing Values in Clinical Chemistry Tests

Many clinical chemistry tests have substantial missing data:

**Well-measured tests** (1,582 non-null values after merging):
- LDL SMALL
- HOMOCYSTEINE, SERUM
- CHOLESTEROL, TOTAL
- TRIGLYCERIDES
- GLUCOSE
- ALBUMIN

**Poorly-measured tests** (~464 non-null values):
- BILIRUBIN, DIRECT
- COPPER, RBC
- LDL MEDIUM
- SELENIUM, SERUM
- NEUTROPHIL, SEGS
- HDL LARGE
- LDL PEAK SIZE

**Very sparse tests**:
- leptin (only 165 non-null values)

## Resulting Correlation Sample Sizes

The combination of these two factors creates different sample sizes:

1. **n ≈ 1,580**: Well-measured clinical test + CVD2/CVD3/INF protein
2. **n ≈ 464**: Poorly-measured clinical test + CVD2/CVD3/INF protein  
3. **n ≈ 193**: Well-measured clinical test + rare chip protein (CAM, CRE, etc.)
4. **n ≈ 72**: Poorly-measured clinical test + rare chip protein
5. **n ≈ 32**: leptin + rare chip protein

## Example Combinations

- **ALBUMIN vs CVD2_O00182**: n = 1,582 (both well-measured)
- **ALBUMIN vs CAM_O00533**: n = 193 (well-measured test, rare chip)
- **COPPER, RBC vs CVD2_O00182**: n = 463 (sparse test, common chip)
- **COPPER, RBC vs CAM_O00533**: n = 72 (sparse test, rare chip)
- **leptin vs CAM_O00533**: n = 32 (very sparse test, rare chip)

## Implications

1. **Statistical Power**: Correlations with n=72 have much less statistical power than those with n=1,580
2. **Multiple Testing**: The different sample sizes create a heterogeneous multiple testing problem
3. **Interpretation**: Strong correlations found with small n should be interpreted cautiously
4. **Chip Selection**: The rare chips were likely run on a subset of samples for cost or research reasons

## Recommendation

When interpreting the correlation results:
- Filter by minimum sample size (e.g., n ≥ 100) for more reliable findings
- Be especially cautious with correlations from rare chip proteins
- Consider the biological relevance of why certain chips were run on fewer samples
- Account for the different statistical power when comparing correlations