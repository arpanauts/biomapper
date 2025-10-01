# Kraken Mapping Directory

## Purpose
This directory contains **final cross-cohort integration results** that map harmonized entities to the Kraken knowledge graph. These are the production-ready mappings used for cross-cohort analysis and knowledge graph integration.

## Directory Structure

```
kraken_mapping/
├── proteins/                        # Protein → Kraken entity mappings
│   ├── arivale_to_kraken_*/        # Arivale proteins
│   ├── ukbb_to_kraken_*/           # UKBB proteins
│   └── israeli10k_to_kraken_*/     # Israeli10K proteins
├── metabolites/                     # Metabolite → Kraken entity mappings
│   ├── arivale_to_kraken_*/        # Arivale metabolites
│   ├── ukbb_to_kraken_*/           # UKBB metabolites (Nightingale)
│   └── israeli10k_to_kraken_*/     # Israeli10K metabolites (Nightingale)
├── chemistry/                       # Clinical chemistry → Kraken mappings
│   ├── arivale_to_kraken_*/        # Arivale clinical tests
│   ├── ukbb_nightingale_*/         # UKBB Nightingale clinical
│   └── israeli10k_nightingale_*/   # Israeli10K Nightingale clinical
├── demographics/                    # Demographics → Kraken mappings
│   ├── arivale_to_kraken_*/        # Arivale demographics
│   ├── ukbb_to_kraken_*/           # UKBB demographics
│   └── israeli10k_to_kraken_*/     # Israeli10K demographics (planned)
└── questionnaires/                  # Final integrated questionnaire mappings
    ├── arivale_to_kraken_*/         # Arivale questionnaires
    ├── ukbb_to_kraken_*/            # UKBB questionnaires
    └── israeli10k_to_kraken_*/      # Israeli10K questionnaires
```

## Key Differences from Harmonization

| Aspect | Harmonization | Kraken Mapping (This Directory) |
|--------|---------------|----------------------------------|
| **Purpose** | Map to standard ontologies | Integrate with knowledge graph |
| **Input** | Raw cohort data | Harmonized ontology mappings |
| **Output** | LOINC codes, MONDO IDs | Kraken entity IDs |
| **Stage** | Intermediate processing | Final production mappings |
| **Scope** | Single cohort → ontology | Multiple cohorts → unified graph |

## Current Coverage

### Proteins
- **Arivale**: ✅ 3,394/3,479 mapped (97.6%)
- **UKBB**: ✅ 2,768/2,923 mapped (94.7%)
- **Israeli10K**: ❌ Not available (no proteomics data)

### Metabolites
- **Arivale**: ✅ 5/5 mapped (100%)
- **UKBB**: ✅ 37/43 mapped (86.0%)
- **Israeli10K**: ✅ 17/17 mapped (100%)

### Chemistry
- **Arivale**: ⚠️ 66/128 mapped (51.6%)
- **UKBB**: ✅ 17/17 mapped (100%)
- **Israeli10K**: ✅ 6/6 mapped (100%)

### Demographics
- **Arivale**: ⚠️ 12/37 mapped (32.4%)
- **UKBB**: ⚠️ 16/45 mapped (35.6%)
- **Israeli10K**: ❌ Not started

### Questionnaires
- Final integration pending completion of LOINC and MONDO harmonization

## Kraken Knowledge Graph Integration

### Entity Types
- **Proteins**: UniProt accessions → Kraken protein nodes
- **Metabolites**: ChEBI/HMDB IDs → Kraken metabolite nodes
- **Chemistry**: LOINC codes → Kraken clinical test nodes
- **Demographics**: LOINC codes → Kraken demographic nodes
- **Questionnaires**: LOINC/MONDO → Kraken observation/disease nodes

### Mapping Process
1. **Input**: Harmonized identifiers from `/harmonization/`
2. **Enrichment**: Add Kraken-specific metadata
3. **Validation**: Verify entities exist in Kraken
4. **Output**: TSV files with Kraken entity mappings

## Usage

### Running Kraken Mappings
Most mappings are generated through biomapper strategies:
```bash
# Example: Run protein mapping strategy
poetry run biomapper run prot_arv_to_kg2c_uniprot_v3.0

# Check available strategies
ls /home/ubuntu/biomapper/src/configs/strategies/experimental/
```

### Output Format
All result files follow the pattern:
- `{cohort}_to_kraken_{entity}_mapping.tsv`
- Tab-separated values
- Includes source identifier, Kraken ID, confidence scores

## Quality Metrics
- **Coverage**: Percentage of source entities successfully mapped
- **Confidence**: Mapping confidence scores (0.0-1.0)
- **Validation**: Cross-reference with multiple ontologies

## Notes
- Kraken mappings depend on completed harmonization
- All cohorts maintain separate mapping files
- Failed mappings are tracked for investigation
- Regular updates as Kraken knowledge graph evolves