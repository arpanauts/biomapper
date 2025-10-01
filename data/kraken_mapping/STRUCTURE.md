# Kraken Mapping Directory Structure

## Organization by Entity Type

Each entity type has its own directory containing cohort-specific proto-strategies:

```
kraken_mapping/
├── proteins/
│   ├── arivale_to_kraken_to_convert_to_biomapper/       # Project 03
│   ├── ukbb_to_kraken_to_convert_to_biomapper/          # Project 04
│   └── israeli10k_to_kraken_to_convert_to_biomapper/    # Project 05
│
├── metabolites/
│   ├── arivale_to_kraken_to_convert_to_biomapper/       # Project 07
│   ├── ukbb_to_kraken_to_convert_to_biomapper/          # Project 08
│   └── israeli10k_to_kraken_to_convert_to_biomapper/    # Project 09
│
├── chemistry/
│   ├── arivale_to_kraken_to_convert_to_biomapper/       # Project 12
│   ├── ukbb_standard_to_kraken_to_convert_to_biomapper/ # Project 13
│   ├── ukbb_nightingale_to_kraken_to_convert_to_biomapper/    # Project 14
│   └── israeli10k_nightingale_to_kraken_to_convert_to_biomapper/ # Project 15
│
├── demographics/
│   ├── arivale_to_kraken_to_convert_to_biomapper/       # Project 16
│   ├── ukbb_to_kraken_to_convert_to_biomapper/          # Project 17
│   └── israeli10k_to_kraken_to_convert_to_biomapper/    # Project 18
│
└── questionnaires/
    ├── arivale_to_kraken_to_convert_to_biomapper/       # Project 19
    ├── ukbb_to_kraken_to_convert_to_biomapper/          # Project 20
    └── israeli10k_to_kraken_to_convert_to_biomapper/    # Project 21
```

## Project Mapping

| Project # | Entity | Cohort | Location |
|-----------|--------|--------|----------|
| 03 | Proteins | Arivale | `proteins/arivale_to_kraken_to_convert_to_biomapper/` |
| 04 | Proteins | UKBB | `proteins/ukbb_to_kraken_to_convert_to_biomapper/` |
| 05 | Proteins | Israeli10K | `proteins/israeli10k_to_kraken_to_convert_to_biomapper/` |
| 07 | Metabolites | Arivale | `metabolites/arivale_to_kraken_to_convert_to_biomapper/` |
| 08 | Metabolites | UKBB | `metabolites/ukbb_to_kraken_to_convert_to_biomapper/` |
| 09 | Metabolites | Israeli10K | `metabolites/israeli10k_to_kraken_to_convert_to_biomapper/` |
| 12 | Chemistry | Arivale | `chemistry/arivale_to_kraken_to_convert_to_biomapper/` |
| 13 | Chemistry | UKBB Standard | `chemistry/ukbb_standard_to_kraken_to_convert_to_biomapper/` |
| 14 | Chemistry | UKBB Nightingale | `chemistry/ukbb_nightingale_to_kraken_to_convert_to_biomapper/` |
| 15 | Chemistry | Israeli10K Nightingale | `chemistry/israeli10k_nightingale_to_kraken_to_convert_to_biomapper/` |
| 16 | Demographics | Arivale | `demographics/arivale_to_kraken_to_convert_to_biomapper/` |
| 17 | Demographics | UKBB | `demographics/ukbb_to_kraken_to_convert_to_biomapper/` |
| 18 | Demographics | Israeli10K | `demographics/israeli10k_to_kraken_to_convert_to_biomapper/` |
| 19 | Questionnaires | Arivale | `questionnaires/arivale_to_kraken_to_convert_to_biomapper/` |
| 20 | Questionnaires | UKBB | `questionnaires/ukbb_to_kraken_to_convert_to_biomapper/` |
| 21 | Questionnaires | Israeli10K | `questionnaires/israeli10k_to_kraken_to_convert_to_biomapper/` |

## Each Proto-Strategy Should Contain

1. **Numbered Python scripts**: `01_load_data.py`, `02_map_to_kraken.py`, etc.
2. **Orchestrator**: `run_all.sh` to execute scripts in order
3. **Data directory**: `data/` for intermediate files
4. **Results directory**: `results/` for final Kraken mappings

## Input Sources

- **Harmonization outputs**: `/home/ubuntu/biomapper/data/harmonization/{entity}/*/results/`
- **LOINC mappings**: `/home/ubuntu/biomapper/data/harmonization/{demographics,questionnaires}/loinc_*/results/`
- **Kraken KG2C**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/`