Actions Reference
=================

BioMapper provides 13 self-registering actions for biological data processing. All actions follow the 2025 standardizations for parameter naming, context handling, and type safety.

.. toctree::
   :maxdepth: 1
   :caption: Data Operations
   
   load_dataset_identifiers
   merge_datasets
   filter_dataset
   export_dataset
   custom_transform

.. toctree::
   :maxdepth: 1
   :caption: Protein Actions
   
   protein_extract_uniprot
   protein_normalize_accessions

.. toctree::
   :maxdepth: 1
   :caption: Metabolite Actions
   
   nightingale_nmr_match
   semantic_metabolite_match

.. toctree::
   :maxdepth: 1
   :caption: Chemistry Actions
   
   chemistry_fuzzy_test_match

Quick Reference
---------------

Data Operations
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``LOAD_DATASET_IDENTIFIERS``
     - Load biological identifiers from CSV/TSV files
   * - ``MERGE_DATASETS``
     - Combine multiple datasets with deduplication
   * - ``FILTER_DATASET``
     - Apply filtering criteria to datasets
   * - ``EXPORT_DATASET``
     - Export results to various formats including CSV, JSON, and Excel
   * - ``CUSTOM_TRANSFORM``
     - Apply Python expressions to transform data columns
   * - ``CUSTOM_TRANSFORM_EXPRESSION``
     - Enhanced expression-based data transformation
   * - ``PARSE_COMPOSITE_IDENTIFIERS``
     - Parse and extract identifiers from composite fields

Protein Actions
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``PROTEIN_EXTRACT_UNIPROT_FROM_XREFS``
     - Extract UniProt IDs from compound reference fields
   * - ``PROTEIN_NORMALIZE_ACCESSIONS``
     - Standardize protein accession formats

Metabolite Actions
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``NIGHTINGALE_NMR_MATCH``
     - Nightingale NMR platform matching
   * - ``SEMANTIC_METABOLITE_MATCH``
     - AI-powered semantic matching

Chemistry Actions
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``CHEMISTRY_FUZZY_TEST_MATCH``
     - Match clinical test names using fuzzy string matching

Integration Actions
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``SYNC_TO_GOOGLE_DRIVE_V2``
     - Upload and sync results to Google Drive with chunked transfer

Usage Example
-------------

.. code-block:: yaml

   name: protein_processing_workflow
   description: Complete protein data processing and export
   
   steps:
     - name: load_source
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "/data/ukbb_proteins.csv"
           identifier_column: "uniprot"
           output_key: "source_data"
     
     - name: extract_uniprot_ids
       action:
         type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
         params:
           input_key: "source_data"
           xref_column: "protein_refs"
           output_key: "extracted_data"
     
     - name: normalize_accessions
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "extracted_data"
           accession_column: "uniprot_id"
           output_key: "normalized_data"
     
     - name: filter_results
       action:
         type: FILTER_DATASET
         params:
           input_key: "normalized_data"
           conditions:
             - "confidence > 0.8"
           output_key: "filtered_data"
     
     - name: export_results
       action:
         type: EXPORT_DATASET
         params:
           input_key: "filtered_data"
           file_path: "/results/processed_proteins.csv"

2025 Standardizations
---------------------

**Parameter Naming**
  All actions use standardized parameter names:
  
  - ``input_key`` (not ``dataset_key``, ``data_key``)
  - ``output_key`` (not ``result_key``, ``target_key``)
  - ``file_path`` (not ``filepath``, ``input_file``)

**Context Handling**
  Actions use UniversalContext wrapper for robust context handling across different execution environments.

**Type Safety**
  Actions inherit from TypedStrategyAction with Pydantic parameter validation and structured results.

**Performance**
  All actions are audited for algorithmic complexity to prevent O(n²)+ performance issues.

**File Loading**
  Uses BiologicalFileLoader for robust parsing with automatic encoding detection and biological data optimization.

Strategy File Locations
-----------------------

Strategy YAML files are located in ``src/biomapper/configs/strategies/`` and organized by:

- **Entity Type**: ``prot_*``, ``met_*``, ``chem_*``, ``multi_*``
- **Source-Target**: ``ukb_to_hpa``, ``arv_to_kg2c``
- **Approach**: ``uniprot_v1_base``, ``semantic_v1_enhanced``

Example: ``prot_ukb_to_hpa_uniprot_v1_base.yaml``

---

## Verification Sources
*Last verified: 2025-08-18*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/` (action implementations and self-registration - verified 13 actual actions)
- `/biomapper/src/actions/registry.py` (global ACTION_REGISTRY and @register_action decorator)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class)
- `/biomapper/CLAUDE.md` (2025 standardization requirements and patterns)
- `/biomapper/src/configs/strategies/` (strategy YAML file organization)
- `/biomapper/src/core/standards/` (standardized utilities and validators)
- `/biomapper/pyproject.toml` (project dependencies and structure)