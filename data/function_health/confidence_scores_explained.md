# Understanding Confidence Scores in Function Health & Arivale Test Mapping

## Overview

The confidence score system is used to determine how similar two test names are when performing fuzzy matching between Function Health tests and Arivale chemistries. Scores range from 0-100%, with higher scores indicating better matches.

## Confidence Score Thresholds

### 🟢 High Confidence (≥95%)
- **Meaning**: Near-perfect or perfect string match
- **Examples**: 
  - "HDL Cholesterol" → "HDL cholesterol" (100% - only case difference)
  - "BUN / Creatinine Ratio" → "Bun/Creatinine Ratio" (95% - minor formatting)
- **Action**: Automatically accepted as valid matches

### 🟡 Medium Confidence (85-94%)
- **Meaning**: Strong similarity but with some differences
- **Examples**:
  - "Gamma-glutamyl Transferase" → "Gamma-glutamyl transpeptidase" (87%)
  - "Mean Platelet Volume (MPV)" → "Mean Platelet Volume" (89%)
- **Action**: Recommended for manual review

### 🔴 Low Confidence (<85%)
- **Meaning**: Weak similarity, likely false positives
- **Examples**:
  - "DHEA-Sulfate" → "DHA" (80% - different compounds)
  - "Alpha-1 Globulin" → "PAI-1" (80% - unrelated tests)
- **Action**: Generally rejected, requires manual mapping if truly related

## Matching Algorithms

The system uses three different fuzzy matching algorithms to find the best possible matches:

### 1. Simple Ratio (`simple_ratio`)
- **Method**: Character-by-character comparison
- **Best for**: Very similar strings with minor typos or case differences
- **Example**: "HDL Cholesterol" vs "HDL cholesterol" = 100%

### 2. Token Set Ratio (`token_set_ratio`)
- **Method**: Compares sets of words, ignoring order and duplicates
- **Best for**: Same words in different order or with extra words
- **Example**: "Arachidonic Acid/EPA Ratio" matches "Arachidonic acid" = 100%

### 3. Partial Ratio (`partial_ratio`)
- **Method**: Finds the best matching substring
- **Best for**: When one string is contained within another
- **Example**: "Apolipoprotein A1" matches "Protein" = 100% (finds "protein" within)

## How Scores Are Calculated

1. **Multiple Algorithm Approach**: Each test name is evaluated using all three algorithms
2. **Best Score Selection**: The highest score from any algorithm is used
3. **Threshold Filtering**: Only matches scoring ≥80% are considered
4. **Top Matches**: Up to 3 best matches are presented for review

## Special Cases

### Exact Matches (100% Score)
- Automatically accepted without fuzzy matching
- Case-insensitive exact string matches
- Examples: "Adiponectin" → "Adiponectin", "Albumin" → "Albumin"

### Manual Mappings (100% Score)
- User-defined mappings override all automatic matching
- Always assigned 100% confidence
- Used for known relationships that fuzzy matching might miss

## Interpreting Results

### Match Distribution (from the notebook analysis)
- **Exact matches**: 39 tests (highest quality)
- **High confidence fuzzy**: 37 matches (22 actually used after deduplication)
- **Medium confidence fuzzy**: 17 matches (require review)
- **Low confidence fuzzy**: 18 matches (likely false positives)

### Quality Indicators
- **Average match score**: ~98% (very high due to many exact matches)
- **Median match score**: 100% (majority are perfect matches)
- **Success rate**: 23.1% of Function Health tests matched to 47.7% of Arivale entries

## Best Practices

1. **Trust high confidence matches** (≥95%) but spot-check a few for validation
2. **Manually review medium confidence matches** (85-94%) - many are valid but need confirmation
3. **Be skeptical of low confidence matches** (<85%) - these often match unrelated tests
4. **Use manual mappings** for known relationships that the algorithm misses
5. **Consider the match type** - token_set and partial matches may need more scrutiny than simple ratio matches

## Common Pitfalls

- **Substring matches**: "Protein" matching many protein-related tests at 100% (partial ratio)
- **Abbreviation confusion**: "DHA" (docosahexaenoic acid) matching "DHEA" (dehydroepiandrosterone)
- **Generic terms**: "Ratio" appearing in many test names causing false matches
- **Word order**: Same words in different order may score high but mean different things

## Recommendations

For the most accurate mapping:
1. Start with exact matches (most reliable)
2. Accept high-confidence fuzzy matches after brief review
3. Carefully evaluate medium-confidence matches
4. Create manual mappings for important tests that don't match well
5. Maintain a log of accepted/rejected fuzzy matches for consistency

## Slide Summary: Confidence Score System

• **Three-tier confidence system**: High (≥95%), Medium (85-94%), Low (<85%) - only high confidence matches are auto-accepted

• **Multi-algorithm approach**: Uses 3 different string matching techniques (simple ratio, token set, partial) to catch various name variations

• **Current results**: Matched 61 tests (23% of Function Health, 48% of Arivale) with 98% average confidence score

• **Quality control**: Exact matches prioritized (39), followed by validated fuzzy matches (22), with manual override capability for edge cases

• **Key insight**: System prevents duplicate mappings - each test maps to at most one entry, ensuring data integrity

## Slide Summary: Fuzzy Matching Algorithms

All three algorithms are considered "fuzzy" because they find approximate matches rather than requiring exact character-for-character equality:

• **Simple Ratio**: Character-by-character comparison that calculates the Levenshtein distance (minimum edits needed to transform one string to another)

• **Token Set Ratio**: Breaks strings into individual words (tokens), removes duplicates, ignores order, then compares the resulting sets - ideal for reordered or subset matches

• **Partial Ratio**: Finds the best matching substring by sliding the shorter string across the longer one - perfect for when one test name is contained within another

• **Best Match Selection**: The system runs all three algorithms and uses the highest score, ensuring we don't miss good matches due to algorithm limitations

• **Note**: "Exact matches" (100% case-insensitive string equality) bypass fuzzy matching entirely and are automatically accepted without using these algorithms

## Slide Summary: How Confidence Scores Are Calculated

The confidence scores are **algorithmically determined**, not arbitrary. Each technique uses mathematical formulas to calculate similarity:

• **Simple Ratio**: Uses Levenshtein distance formula: `Score = (1 - (edit_distance / max_string_length)) × 100`. For "HDL Cholesterol" vs "HDL cholesterol": only 1 edit (case change) in 14 characters = 93% score

• **Token Set Ratio**: Calculates Jaccard similarity of word sets: `Score = (matching_tokens / total_unique_tokens) × 100`. For "Blood Urea Nitrogen" vs "Urea": matches 1 of 4 unique tokens = baseline, then applies normalization = 100% due to "Urea" being a complete subset

• **Partial Ratio**: Finds best substring alignment and scores that segment: `Score = (matched_characters / shorter_string_length) × 100`. For "Apolipoprotein A1" vs "Protein": finds "protein" (7 chars) perfectly within the longer string = 100%

• **Score Range**: All algorithms produce 0-100% scores where 100% means perfect similarity according to that algorithm's criteria - no manual adjustments or arbitrary thresholds

• **Implementation**: Uses the `thefuzz` Python library (formerly FuzzyWuzzy), which implements these algorithms based on proven string similarity research from computer science