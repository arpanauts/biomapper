# Database Restoration and PubChem/KEGG Integration

## 1. Recent Accomplishments

- Successfully restored the SQLite database (`metamapper.db`) with the proper schema to support ontology mapping
- Fixed Python 3.11 compatibility issues in multiple files by updating Union type syntax
- Created two setup scripts (`setup_pubchem_paths.py` and `setup_kegg_paths.py`) to register resources and define mapping paths
- Successfully registered and configured PubChem (ID 6) and KEGG (ID 9) resources in the database
- Defined and added mapping paths for both PubChem and KEGG to enable multi-step compound identifier mapping
- Simplified the dependency structure to avoid unnecessary requirements (chromadb, langfuse)
- Committed all changes to GitHub in a structured, logical manner

## 2. Current Project State

- The biomapper project is now operational with a functioning SQLite database containing PubChem and KEGG integrations
- Core mapping functionality is stable and can be used for chemical compound identifier mapping
- The database schema is structured with tables including `resources` and `mapping_paths`
- Metadata system configuration points to `metamapper.db` as the primary database file
- RAG components are temporarily commented out to avoid dependency issues, as they're not required for the core mapping functionality
- The Python code is now compatible with Python 3.11, addressing issues with Union type syntax

## 3. Technical Context

### Database Structure
- The `mapping_paths` table schema includes columns: id, source_type, target_type, path_steps, performance_score, success_rate, usage_count, last_used, last_discovered
- Resource configuration is stored as JSON in the `resources` table
- Mapping paths define multi-step processes for converting between different identifier types

### Mapping Architecture
- Multi-step mapping paths allow for converting between different identifier systems:
  - NAME → PUBCHEM/KEGG → INCHI/INCHIKEY/SMILES/FORMULA/CHEBI
  - Each step specifies source, target, method, and resources to use
- Performance scores prioritize different mapping paths (higher scores indicate preferred paths)

### Python 3.11 Compatibility
- Updated code to replace the pipe operator (`|`) with proper `Union` types
- Fixed type hints and annotations in various files including:
  - `ramp_client.py`
  - `unichem_client.py`
  - `metabolite.py`

## 4. Next Steps

- Implement proper RAG functionality with fastembed instead of chromadb as requested
- Update the remaining references to `metadata.db` to ensure consistent use of `metamapper.db`
- Develop tests to verify the PubChem and KEGG integrations are working as expected
- Set up automated testing for the mapping paths to ensure they function correctly
- Add more mapping paths as needed based on project requirements
- Consider optimizing database queries for performance, especially for complex multi-step mappings

## 5. Open Questions & Considerations

- Should we fully migrate from chromadb to fastembed for RAG functionality, or maintain parallel implementations?
- How should we handle the discrepancy between references to `metadata.db` and `metamapper.db` in the codebase?
- What metrics should we use to evaluate the performance and accuracy of different mapping paths?
- Are there additional identifier types or resources we should integrate beyond PubChem and KEGG?
- How should we handle rate limiting or API quotas when making requests to external services like PubChem and KEGG?
- Do we need to implement caching mechanisms to improve performance for repeated mapping requests?
