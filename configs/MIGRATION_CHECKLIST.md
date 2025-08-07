# Strategy Migration Checklist

## Overview
This checklist guides the migration of existing strategies to the new organizational framework.

## Current Strategies to Migrate

### Existing Files (2 strategies)
- [ ] `strategies/arivale_to_kg2c_proteins.yaml` → `prot_arv_to_kg2c_uniprot_v1_base.yaml`
- [ ] `strategies/ukbb_to_kg2c_proteins.yaml` → `prot_ukb_to_kg2c_uniprot_v1_base.yaml`

### Planned Strategies from mappings_list.csv (19 additional)
Based on the 21 mappings identified, we need to create:

#### Protein Mappings (4 more)
- [ ] Row 18: `prot_arv_to_spoke_uniprot_v1_base.yaml` (Arivale → SPOKE proteins)
- [ ] Row 19: `prot_ukb_to_spoke_uniprot_v1_base.yaml` (UKBB → SPOKE proteins)
- [ ] Cross-KG: `prot_kg2c_to_spoke_uniprot_v1_base.yaml` (KG2c ↔ SPOKE proteins)
- [ ] Multi-source: `prot_multi_to_unified_uniprot_v1_enhanced.yaml`

#### Metabolite Mappings (10 strategies)
- [ ] Row 3: `met_arv_to_ukb_multi_v1_base.yaml` (Arivale ↔ UKBB metabolites)
- [ ] Row 5: `met_isr_to_kg2c_multi_v1_base.yaml` (Israeli10k metabolomics → KG2c)
- [ ] Row 6: `met_isr_lipid_to_kg2c_multi_v1_base.yaml` (Israeli10k lipidomics → KG2c)
- [ ] Row 7: `met_arv_to_kg2c_multi_v1_base.yaml` (Arivale → KG2c metabolites)
- [ ] Row 11: `met_ukb_to_kg2c_nmr_v1_base.yaml` (UKBB NMR → KG2c)
- [ ] Row 12: `met_isr_to_spoke_inchikey_v1_base.yaml` (Israeli10k → SPOKE metabolites)
- [ ] Row 14: `met_isr_lipid_to_spoke_inchikey_v1_base.yaml` (Israeli10k lipids → SPOKE)
- [ ] Row 16: `met_arv_to_spoke_multi_v1_base.yaml` (Arivale → SPOKE metabolites)
- [ ] Row 20: `met_ukb_to_spoke_nmr_v1_base.yaml` (UKBB NMR → SPOKE)
- [ ] Cross-KG: `met_kg2c_to_spoke_inchikey_v1_base.yaml`

#### Chemistry/Clinical Lab Mappings (5 strategies)
- [ ] Row 8: `chem_arv_to_spoke_loinc_v1_base.yaml` (Arivale → SPOKE clinical labs)
- [ ] Row 13: `chem_isr_met_to_spoke_semantic_v1_base.yaml` (Israeli10k metabolomics → clinical)
- [ ] Row 15: `chem_isr_to_spoke_loinc_v1_base.yaml` (Israeli10k chemistries → SPOKE)
- [ ] Row 17: `chem_arv_to_spoke_loinc_v1_strict.yaml` (Arivale strict LOINC match)
- [ ] Row 21: `chem_ukb_to_spoke_nmr_v1_base.yaml` (UKBB NMR → SPOKE clinical)

## Migration Steps for Each Strategy

### Phase 1: File Migration
For each existing strategy file:

1. **Rename file** according to naming convention:
   ```bash
   # Example
   mv strategies/arivale_to_kg2c_proteins.yaml \
      strategies/experimental/prot_arv_to_kg2c_uniprot_v1_base.yaml
   ```

2. **Add metadata section** at the top of the file:
   ```yaml
   metadata:
     id: "prot_arv_to_kg2c_uniprot_v1_base"
     name: "Arivale Proteins to KG2c via UniProt"
     version: "1.0.0"
     created: "2025-01-08"
     # ... complete metadata
   ```

3. **Update parameters section** to use metadata references:
   ```yaml
   parameters:
     output_dir: "${OUTPUT_DIR:-/tmp/biomapper/outputs}"
     # ... other parameters
   ```

4. **Validate YAML syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('path/to/strategy.yaml'))"
   ```

### Phase 2: Testing & Validation

5. **Create test dataset** (10-20 rows from source):
   ```bash
   head -20 /procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv > test_data.tsv
   ```

6. **Run strategy test**:
   ```bash
   poetry run biomapper execute-strategy STRATEGY_ID --test
   ```

7. **Record metrics** in metadata:
   - Execution time
   - Memory usage
   - Match rate
   - Error rate

### Phase 3: Documentation

8. **Update registry** (`metadata/strategy_registry.json`):
   ```json
   "prot_arv_to_kg2c_uniprot_v1_base": {
     "status": "experimental",
     "location": "strategies/experimental/prot_arv_to_kg2c_uniprot_v1_base.yaml",
     "last_validated": "2025-01-08",
     // ... metrics
   }
   ```

9. **Create benchmark file** (`benchmarks/validation_results/STRATEGY_ID.json`):
   ```json
   {
     "strategy_id": "prot_arv_to_kg2c_uniprot_v1_base",
     "test_date": "2025-01-08",
     "metrics": { ... }
   }
   ```

10. **Update documentation** if needed in `docs/strategy_guides/`

### Phase 4: Quality Promotion

11. **Promotion criteria checklist**:
    - [ ] Strategy executes without errors
    - [ ] Match rate meets expectations (±10%)
    - [ ] Performance acceptable (<5 min for test data)
    - [ ] All metadata fields complete
    - [ ] Peer review completed

12. **Move to appropriate tier**:
    ```bash
    # After validation
    mv strategies/experimental/STRATEGY.yaml strategies/production/STRATEGY.yaml
    ```

## Priority Order

### Week 1: Core Existing Strategies
- [ ] Migrate 2 existing protein strategies
- [ ] Test and validate
- [ ] Update registry

### Week 2: High-Priority New Strategies
- [ ] Create 3 metabolite → KG2c strategies (rows 5, 6, 7)
- [ ] Create 2 chemistry → SPOKE strategies (rows 8, 15)

### Week 3: Cross-Dataset Mappings
- [ ] Create remaining metabolite strategies
- [ ] Create cross-KG mappings (KG2c ↔ SPOKE)

### Week 4: Complete & Optimize
- [ ] Create remaining chemistry strategies
- [ ] Multi-source unified strategies
- [ ] Performance optimization

## Success Criteria

- [ ] All strategies follow naming convention
- [ ] All strategies have complete metadata
- [ ] Registry is up-to-date
- [ ] Templates cover 80% of use cases
- [ ] Average match rate > 70%
- [ ] Documentation complete

## Notes

- Keep original files in `strategies/` until migration is validated
- Use `git mv` when renaming to preserve history
- Run tests on small datasets first
- Document any deviations from templates
- Update this checklist as strategies are migrated

---

*Last updated: 2025-01-08*
*Total strategies to migrate: 21 (2 existing + 19 new)*