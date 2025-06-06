# Biomapper Scripts Directory

This directory contains standalone scripts for various biomapper operations, organized by functionality.

## Directory Structure

### 🚀 main_pipelines/
Primary mapping and pipeline execution scripts for production use.
- `map_ukbb_to_*.py` - Main UKBB mapping pipelines
- `run_full_ukbb_hpa_mapping.py` - Complete UKBB to HPA mapping workflow
- `phase3_bidirectional_reconciliation.py` - Bidirectional mapping reconciliation
- `mvp_ukbb_arivale_*/` - MVP pipeline implementations

### ⚙️ setup_and_configuration/
Database setup, initialization, and configuration scripts.
- `populate_metamapper_db.py` - Initialize metamapper database
- `db_management/` - Database administration utilities
- `resources/` - Resource path configuration scripts

### 📊 data_preprocessing/
Data preparation and transformation scripts.
- `create_bio_relevant_cid_allowlist*.py` - Generate biological compound ID filters
- `filter_pubchem_embeddings.py` - Filter PubChem embedding data
- `process_unichem_mappings.py` - Process UniChem identifier mappings

### 🧠 embeddings_and_rag/
Embedding generation and RAG (Retrieval-Augmented Generation) utilities.
- `index_filtered_embeddings_to_qdrant.py` - Index embeddings in Qdrant vector DB
- `embedder_cli.py` - Command-line interface for embedding operations

### 🧪 testing_and_validation/
Test scripts, debugging tools, and validation utilities.
- `test_*.py` - Unit and integration test scripts
- `debug_*.py` - Debugging utilities for specific issues
- `db_verification/` - Database integrity checks
- Shell scripts for test execution workflows

### 📈 analysis_and_reporting/
Post-processing analysis and report generation.
- `analyze_*.py` - Various analysis scripts
- `knowledge_graph/` - Knowledge graph exploration tools
- Result analysis and reporting utilities

### 🔧 utility_and_tools/
General-purpose utilities and helper scripts.
- `clear_uniprot_cache.py` - Cache management
- `parse_*.py` - Data parsing utilities
- Other maintenance and utility scripts

### 📦 archived_or_experimental/
Deprecated scripts, backups, and experimental code.
- `*.backup` - Backup versions of scripts
- `simple_*.py` - Simplified/older versions of mappers
- Test outputs and historical logs

### ❓ needs_categorization/
Scripts requiring manual review for proper categorization.

## Usage Guidelines

### Running Scripts

Most scripts can be run directly from the biomapper root directory:

```bash
# From /home/ubuntu/biomapper/
python scripts/main_pipelines/map_ukbb_to_hpa.py --input data/ukbb_proteins.csv

# Or from the scripts directory
cd scripts/main_pipelines
python map_ukbb_to_hpa.py --input ../../data/ukbb_proteins.csv
```

### Common Workflows

1. **Full UKBB to HPA Mapping**
   ```bash
   python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
   ```

2. **Initialize Metamapper Database**
   ```bash
   python scripts/setup_and_configuration/populate_metamapper_db.py
   ```

3. **Run Tests**
   ```bash
   cd scripts/testing_and_validation
   ./test_phase3_with_real_data.sh
   ```

### Important Notes

- **Path Dependencies**: Some scripts may have hardcoded paths or expect to be run from specific directories. Check script headers for requirements.
- **Environment**: Ensure your biomapper environment is activated before running scripts.
- **Configuration**: Many scripts rely on biomapper configuration files. Set up your environment variables and config files before running.

## Development Guidelines

### Adding New Scripts

1. Choose the appropriate category directory
2. Follow existing naming conventions:
   - `map_*.py` for mapping scripts
   - `test_*.py` for test scripts
   - `debug_*.py` for debugging utilities
3. Include a docstring explaining the script's purpose
4. Add command-line argument parsing for flexibility

### Script Requirements

- All scripts should have proper error handling
- Include logging for debugging purposes
- Use absolute imports when referencing biomapper modules
- Document external dependencies

## Maintenance

- Regularly review `needs_categorization/` for uncategorized scripts
- Move deprecated scripts to `archived_or_experimental/`
- Keep test outputs and logs in `.gitignore`
- Update this README when adding new script categories