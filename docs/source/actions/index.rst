Actions Reference
=================

BioMapper provides 30+ self-registering actions for biological data processing.

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
   protein_multi_bridge
   merge_with_uniprot_resolution

.. toctree::
   :maxdepth: 1
   :caption: Metabolite Actions
   
   metabolite_cts_bridge
   metabolite_extract_identifiers
   metabolite_normalize_hmdb
   nightingale_nmr_match
   semantic_metabolite_match
   vector_enhanced_match

.. toctree::
   :maxdepth: 1
   :caption: Chemistry Actions
   
   chemistry_extract_loinc
   chemistry_fuzzy_test_match
   chemistry_vendor_harmonization

.. toctree::
   :maxdepth: 1
   :caption: Analysis Actions
   
   calculate_set_overlap
   calculate_three_way_overlap
   calculate_mapping_quality
   generate_metabolomics_report

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
   * - ``EXPORT_DATASET_V2``
     - Export results to various formats
   * - ``CUSTOM_TRANSFORM_EXPRESSION``
     - Apply Python expressions to transform data

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
   * - ``PROTEIN_MULTI_BRIDGE``
     - Multi-source protein identifier resolution
   * - ``MERGE_WITH_UNIPROT_RESOLUTION``
     - Map identifiers to UniProt accessions

Metabolite Actions
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``METABOLITE_CTS_BRIDGE``
     - Chemical Translation Service API integration
   * - ``METABOLITE_EXTRACT_IDENTIFIERS``
     - Extract metabolite IDs from text fields
   * - ``METABOLITE_NORMALIZE_HMDB``
     - Standardize HMDB identifier formats
   * - ``NIGHTINGALE_NMR_MATCH``
     - Nightingale NMR platform matching
   * - ``SEMANTIC_METABOLITE_MATCH``
     - AI-powered semantic matching
   * - ``VECTOR_ENHANCED_MATCH``
     - Vector embedding similarity matching

Chemistry Actions
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``CHEMISTRY_EXTRACT_LOINC``
     - Extract and validate LOINC codes from clinical chemistry data
   * - ``CHEMISTRY_FUZZY_TEST_MATCH``
     - Match clinical test names using fuzzy string matching
   * - ``CHEMISTRY_VENDOR_HARMONIZATION``
     - Harmonize vendor-specific test names to standard nomenclature

Analysis Actions
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - Description
   * - ``CALCULATE_SET_OVERLAP``
     - Calculate Jaccard similarity and set overlaps
   * - ``CALCULATE_THREE_WAY_OVERLAP``
     - Three-way dataset intersection analysis
   * - ``CALCULATE_MAPPING_QUALITY``
     - Comprehensive quality assessment for identifier mappings
   * - ``GENERATE_METABOLOMICS_REPORT``
     - Generate detailed metabolomics analysis reports

Usage Example
-------------

.. code-block:: yaml

   name: example_workflow
   description: Example multi-action workflow
   
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "/data/proteins.csv"
           identifier_column: "uniprot"
           output_key: "proteins"
     
     - name: normalize
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: "proteins"
           output_key: "normalized"
     
     - name: export
       action:
         type: EXPORT_DATASET_V2
         params:
           input_key: "normalized"
           output_file: "/results/output.csv"