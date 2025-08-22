# Metabolomics Pipeline Expert Review Workflow Guide

## Overview

This guide provides a practical workflow for reviewing flagged metabolite matches from the progressive metabolomics pipeline. With conservative thresholds, approximately **15% of metabolites** (~38 out of 250) will require expert review.

## Time Estimate: 2-3 Hours Total

| Priority Level | Expected Count | Time per Item | Total Time |
|---------------|---------------|---------------|------------|
| High Priority | 5-10 items | 3-5 minutes | 30 minutes |
| Medium Priority | 20-25 items | 3-4 minutes | 90 minutes |
| Low Priority | 5-10 items | 2-3 minutes | 30 minutes |
| **Total** | **~38 items** | **~4 minutes avg** | **2.5 hours** |

## Step-by-Step Review Process

### 1. Initial Setup (10 minutes)

1. **Open the Review CSV** in your preferred tool:
   - Excel (recommended for most users)
   - R Studio (for statistical analysis)
   - Python/Pandas (for programmatic review)

2. **Sort by Priority Column**:
   ```
   Priority 1 = High (review first)
   Priority 2 = Medium (review second)
   Priority 3 = Low (review last)
   ```

3. **Prepare Reference Resources**:
   - Open [HMDB](https://hmdb.ca/) in browser
   - Open [ChEBI](https://www.ebi.ac.uk/chebi/) in browser
   - Have your institutional metabolite database ready

### 2. High Priority Reviews (30 minutes)

High priority items typically include:
- Structural conflicts (molecular formula mismatches)
- Known edge cases (e.g., stereoisomers)
- Critical clinical markers

**For each high priority item:**

1. **Check Molecular Structure** (if available):
   ```
   - Compare source and matched molecular formulas
   - Allow for hydration differences (H2O)
   - Check for salt forms (Na+ vs H+)
   ```

2. **Verify in HMDB**:
   ```
   - Search for the metabolite name
   - Check synonyms and alternative names
   - Verify molecular formula
   ```

3. **Make Decision**:
   - **Accept**: Structure and biological context match
   - **Reject**: Clear mismatch or incorrect identification
   - **Needs More Info**: Requires additional investigation

4. **Document Decision**:
   ```csv
   reviewer_name: "JD"
   reviewer_decision: "accept"
   reviewer_comments: "Verified in HMDB, formula matches with hydration"
   review_date: "2024-01-19"
   final_confidence_score: 0.90
   ```

### 3. Medium Priority Reviews (90 minutes)

Medium priority items typically include:
- Confidence scores between 0.60-0.85
- Multiple candidate matches
- Fuzzy string matches

**Batch Review Strategy:**

1. **Group Similar Metabolites**:
   - Review all amino acids together
   - Review all lipids together
   - Review all clinical markers together

2. **Quick Validation Process**:
   ```
   For each metabolite:
   1. Check if name is reasonable synonym
   2. Quick HMDB search for verification
   3. If confidence > 0.75 and name similar → Accept
   4. If confidence < 0.70 and name different → Reject
   5. Otherwise → Needs more info
   ```

3. **Use Batch Operations** (Excel):
   ```
   - Select multiple similar cases
   - Apply same decision if appropriate
   - Copy reviewer comments for similar cases
   ```

### 4. Low Priority Reviews (30 minutes)

Low priority items typically include:
- Single fuzzy matches with moderate confidence
- Well-characterized metabolites with slightly low scores

**Rapid Review Process:**

1. **Apply 80/20 Rule**:
   - 80% can likely be quickly accepted or rejected
   - 20% may need closer look

2. **Quick Decision Tree**:
   ```
   If metabolite is common (glucose, cholesterol, etc.):
     → Accept if name roughly matches
   If metabolite is rare or specialized:
     → Review more carefully
   If confidence < 0.65:
     → Generally reject unless name exact match
   ```

## Review Decision Guidelines

### When to ACCEPT ✅

- Molecular formula matches (allowing for hydration/salt differences)
- Name is a known synonym or abbreviation
- Confidence score aligns with match quality
- Biological context is appropriate
- HMDB/ChEBI confirms the match

**Example Accept Case:**
```
Source: "Total cholesterol"
Match: "Cholesterol"
Confidence: 0.82
Decision: Accept - Common abbreviation, high confidence
```

### When to REJECT ❌

- Clear molecular formula mismatch
- Biologically implausible match (e.g., plant metabolite for human sample)
- Very low confidence with poor name match
- Different metabolite class (e.g., amino acid matched to lipid)

**Example Reject Case:**
```
Source: "Glucose"
Match: "Fructose"
Confidence: 0.65
Decision: Reject - Different sugars, isomers but functionally different
```

### When to flag NEEDS MORE INFO ❓

- Structural isomers requiring detailed verification
- Metabolite not found in reference databases
- Conflicting information between databases
- Novel or rarely studied metabolites
- Confidence score doesn't match apparent quality

**Example Needs More Info Case:**
```
Source: "Dihydroxy-cholesterol"
Match: "25-hydroxycholesterol"
Confidence: 0.72
Decision: Needs more info - Multiple dihydroxy forms exist, need specificity
```

## Confidence Score Interpretation

| Score Range | Interpretation | Default Action |
|------------|---------------|----------------|
| ≥ 0.85 | High confidence | Auto-accepted (not in review) |
| 0.75-0.84 | Good confidence | Usually accept unless issues |
| 0.65-0.74 | Moderate confidence | Careful review needed |
| 0.60-0.64 | Low confidence | Usually reject unless exact match |
| < 0.60 | Very low confidence | Auto-rejected (not in review) |

## Common Patterns to Watch For

### 1. Naming Variations
- "Total cholesterol" vs "Cholesterol" → Usually accept
- "HDL-C" vs "HDL cholesterol" → Accept
- "Glc" vs "Glucose" → Accept if confidence high

### 2. Chemical Modifications
- Base compound vs salts (accept if biologically equivalent)
- Hydrated vs anhydrous forms (usually accept)
- Different ionization states (context-dependent)

### 3. Stereoisomers
- L- vs D- amino acids (reject if wrong form for biological context)
- Cis vs trans fatty acids (usually need to differentiate)
- Alpha vs beta forms (depends on biological relevance)

## Excel Tips for Efficient Review

### Use Filters
```excel
1. Filter by Priority = 1 first
2. Filter by confidence_score 0.7-0.8 for bulk review
3. Filter by matched_stage to review similar matches together
```

### Conditional Formatting
```excel
1. Highlight confidence < 0.70 in red
2. Highlight confidence > 0.80 in green
3. Bold high priority items
```

### Keyboard Shortcuts
- `Ctrl+D` - Fill down (copy decision to multiple cells)
- `Ctrl+;` - Insert today's date
- `Alt+Enter` - New line in cell (for comments)

## Quality Control Checklist

Before submitting review:

- [ ] All flagged items have a decision
- [ ] Reviewer name filled for all reviewed items
- [ ] Review date added
- [ ] High priority items have detailed comments
- [ ] Final confidence scores adjusted where needed
- [ ] No blank decision cells
- [ ] File saved with timestamp (e.g., `review_complete_20240119.csv`)

## Submission Process

1. **Save Completed Review**:
   ```
   expert_review_complete_YYYYMMDD.csv
   ```

2. **Email to Pipeline Admin**:
   ```
   Subject: Metabolomics Review Complete - [Date]
   Attachment: expert_review_complete_YYYYMMDD.csv
   
   Body:
   Review complete for [X] metabolites
   High priority items: [X] reviewed
   Issues identified: [Brief summary if any]
   ```

3. **Log Any Systematic Issues**:
   - Recurring false positives
   - Missing metabolites in reference
   - Threshold adjustment suggestions

## Feedback for Pipeline Improvement

Please track and report:

1. **False Positives**: Incorrect matches with high confidence
2. **False Negatives**: Correct matches with low confidence  
3. **Systematic Patterns**: Recurring issues with specific metabolite classes
4. **Reference Gaps**: Metabolites not in our reference databases
5. **Threshold Suggestions**: Based on review patterns

## Support Resources

- **HMDB**: https://hmdb.ca/
- **ChEBI**: https://www.ebi.ac.uk/chebi/
- **KEGG**: https://www.kegg.jp/
- **PubChem**: https://pubchem.ncbi.nlm.nih.gov/
- **Pipeline Documentation**: [Internal link]
- **Technical Support**: [Contact email]

## FAQ

**Q: How long should each review take?**
A: High priority: 3-5 min, Medium: 3-4 min, Low: 2-3 min

**Q: What if I'm unsure about a match?**
A: Mark as "needs_more_info" with specific questions in comments

**Q: Can I batch accept similar metabolites?**
A: Yes, for medium/low priority items with similar characteristics

**Q: Should I adjust confidence scores?**
A: Yes, update final_confidence_score based on your expertise

**Q: What about metabolites not in HMDB?**
A: Check ChEBI, KEGG, and document in comments if not found

---

*Last Updated: January 2024*
*Version: 1.0 - MVP Production Release*