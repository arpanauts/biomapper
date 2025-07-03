# YAML Naming Quick Reference

## 🎯 The Formula
```
{source}_{target}_{purpose}_{variant}.yaml
```

## 📝 Examples

### Basic Mappings
```
ukbb_hpa_overlap.yaml              # Simple overlap analysis
uniprot_ensemble_mapping.yaml      # ID mapping
gene_protein_conversion.yaml       # Type conversion
```

### With Variants
```
ukbb_hpa_overlap_historical.yaml   # With historical resolution
ukbb_hpa_overlap_fast.yaml         # Performance optimized
ukbb_hpa_overlap_validated.yaml    # With validation steps
```

## 🚫 What NOT to Do
```
❌ strategy_v2_final_FINAL.yaml
❌ ukbb_hpa_new_updated_fixed.yaml
❌ test_test_production.yaml
❌ mapping_strategy_v1.2.3.yaml
```

## ✅ Common Patterns

### By Purpose
- `_overlap` - Dataset comparison
- `_mapping` - ID translation
- `_resolution` - Historical ID handling
- `_conversion` - Type transformation
- `_validation` - Data quality checks

### By Feature
- `_historical` - Includes historical resolution
- `_bidirectional` - Two-way mapping
- `_cached` - Uses caching
- `_batch` - Optimized for large datasets
- `_streaming` - Processes data in streams

### By Environment
- `_dev` - Development
- `_prod` - Production
- `_test` - Testing only

## 📁 Where to Put Files
```
configs/strategies/
├── production/     # Ready for use
├── experimental/   # In development
├── examples/       # Documentation
└── deprecated/     # Old versions
```

## 🏷️ Required Metadata
```yaml
name: STRATEGY_NAME
version: "1.0.0"
metadata:
  description: "What this does"
  variant: "historical"
  status: "production"
```

## 🤔 When to Create New vs. Modify?

**New File:**
- Different algorithm
- Different purpose
- Major feature addition

**Modify Existing:**
- Bug fixes
- Parameter tuning
- Minor improvements

## 📚 Abbreviation Glossary
- `ukbb` - UK Biobank
- `hpa` - Human Protein Atlas
- `ensemble` - Ensemble database
- `uniprot` - UniProt database

Remember: **Clear > Clever**