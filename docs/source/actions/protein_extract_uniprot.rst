PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
===================================

Extract UniProt accession IDs from compound xrefs fields in protein datasets.

Purpose
-------

This action extracts UniProt accession IDs from xrefs fields commonly found in KG2c and SPOKE protein datasets. It provides:

* Pattern-based extraction using regex matching
* Multiple output format options
* Isoform handling (keep or strip -1, -2 suffixes)
* Validation of extracted UniProt IDs
* Row expansion for multiple matches
* Comprehensive statistics and metadata

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**dataset_key** (string)
  Key of the dataset in context to process.

**xrefs_column** (string)
  Name of the column containing xrefs data with UniProt references.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**output_column** (string)
  Name of the output column for extracted UniProt IDs.
  Default: "uniprot_id"

**handle_multiple** (string)
  How to handle multiple UniProt IDs: 'list', 'first', or 'expand_rows'.
  Default: 'list'

**keep_isoforms** (boolean)
  Whether to keep isoform suffixes (e.g., P12345-1, P12345-2).
  Default: false

**drop_na** (boolean)
  Whether to drop rows with no UniProt IDs found.
  Default: true

UniProt Extraction Pattern
--------------------------

The action uses the regex pattern: ``UniProtKB:([A-Z0-9]+(?:-\d+)?)``

This pattern matches:
* Standard UniProt format: ``UniProtKB:P12345``
* Isoform variants: ``UniProtKB:P12345-1``
* Newer formats: ``UniProtKB:A0A123B4C5``

Handle Multiple Options
-----------------------

**list** (default)
  Keep all extracted UniProt IDs as a list in the output column.

**first** 
  Take only the first UniProt ID found and store as a single value.

**expand_rows**
  Create separate rows for each UniProt ID found.

Example Usage
-------------

Basic UniProt Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: extract_uniprot_ids
      action:
        type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
        params:
          dataset_key: "kg2c_proteins"
          xrefs_column: "all_node_curie"
          output_column: "uniprot_id"
          handle_multiple: "list"
          keep_isoforms: false

First Match Only
~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: extract_primary_uniprot
      action:
        type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
        params:
          dataset_key: "spoke_proteins"
          xrefs_column: "xrefs"
          output_column: "primary_uniprot"
          handle_multiple: "first"
          drop_na: true

Expand Rows for Each UniProt ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: expand_uniprot_matches
      action:
        type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
        params:
          dataset_key: "protein_data"
          xrefs_column: "external_refs"
          output_column: "uniprot_id"
          handle_multiple: "expand_rows"
          keep_isoforms: true

Keep Isoform Information
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: extract_with_isoforms
      action:
        type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
        params:
          dataset_key: "detailed_proteins"
          xrefs_column: "cross_references"
          output_column: "uniprot_accession"
          handle_multiple: "list"
          keep_isoforms: true
          drop_na: false

Input Data Format
-----------------

**Typical xrefs format:**
.. code-block::

    # Example xrefs content
    "NCBIGene:1234|UniProtKB:P12345|HGNC:5678|UniProtKB:P12345-1"
    
    # Multiple references separated by pipes
    "ENSEMBL:ENSG123|UniProtKB:Q67890|RefSeq:NP_001234"
    
    # Complex format with various databases
    "MONDO:0001234|HP:5678901|UniProtKB:O11111|UniProtKB:O11111-2|KEGG:hsa:999"

**Expected input dataset structure:**
.. code-block:: python

    [
        {
            "gene_name": "EXAMPLE1",
            "all_node_curie": "NCBIGene:1234|UniProtKB:P12345|HGNC:5678",
            "description": "Example protein 1"
        },
        {
            "gene_name": "EXAMPLE2", 
            "all_node_curie": "UniProtKB:Q67890|UniProtKB:Q67890-1",
            "description": "Example protein 2"
        }
    ]

Output Formats
--------------

**List Output (handle_multiple='list')**
.. code-block:: python

    [
        {
            "gene_name": "EXAMPLE1",
            "all_node_curie": "NCBIGene:1234|UniProtKB:P12345|HGNC:5678",
            "uniprot_id": ["P12345"],
            "description": "Example protein 1"
        },
        {
            "gene_name": "EXAMPLE2",
            "all_node_curie": "UniProtKB:Q67890|UniProtKB:Q67890-1", 
            "uniprot_id": ["Q67890"],  # Isoforms stripped if keep_isoforms=false
            "description": "Example protein 2"
        }
    ]

**First Match Output (handle_multiple='first')**
.. code-block:: python

    [
        {
            "gene_name": "EXAMPLE1",
            "all_node_curie": "NCBIGene:1234|UniProtKB:P12345|HGNC:5678",
            "uniprot_id": "P12345",
            "description": "Example protein 1"
        }
    ]

**Expanded Rows Output (handle_multiple='expand_rows')**
.. code-block:: python

    [
        {
            "gene_name": "EXAMPLE1",
            "all_node_curie": "NCBIGene:1234|UniProtKB:P12345|HGNC:5678",
            "uniprot_id": "P12345",
            "description": "Example protein 1"
        },
        {
            "gene_name": "EXAMPLE2",
            "all_node_curie": "UniProtKB:Q67890|UniProtKB:Q67890-1",
            "uniprot_id": "Q67890",
            "description": "Example protein 2"
        },
        {
            "gene_name": "EXAMPLE2",
            "all_node_curie": "UniProtKB:Q67890|UniProtKB:Q67890-1",
            "uniprot_id": "Q67890",  # If keep_isoforms=false, duplicates removed
            "description": "Example protein 2"
        }
    ]

Statistics and Metadata
------------------------

The action provides detailed statistics in the context:

.. code-block:: python

    {
        "statistics": {
            "uniprot_extraction": {
                "total_rows_processed": 1000,
                "rows_with_uniprot_ids": 847,
                "extraction_rate": 0.847
            }
        }
    }

UniProt ID Validation
---------------------

**Valid Format Patterns:**
* Standard: 6-10 alphanumeric characters (e.g., P12345, Q9Y6K1)
* Newer format: Up to 10 characters (e.g., A0A123B4C5)
* Isoforms: Base ID + dash + number (e.g., P12345-1)

**Invalid IDs are filtered out:**
* Too short: < 6 characters
* Too long: > 10 characters (excluding isoform suffix)
* Invalid characters: Only A-Z and 0-9 allowed
* Malformed isoforms: Invalid suffix patterns

Error Handling
--------------

**Column not found**
  .. code-block::
  
      Error: Column 'missing_xrefs' not found in dataset
      
  Solution: Verify the xrefs_column name matches exactly.

**Dataset not found**
  .. code-block::
  
      Error: Dataset key 'missing_data' not found in context
      
  Solution: Ensure dataset exists in context from previous actions.

**No UniProt IDs found**
  .. code-block::
  
      Warning: No valid UniProt IDs extracted from dataset
      
  Solution: Check xrefs format and UniProt reference patterns.

Best Practices
--------------

1. **Inspect xrefs format** before extraction to understand data structure
2. **Choose appropriate handling** for multiple IDs based on downstream needs
3. **Consider isoform requirements** - biological significance vs. analysis complexity
4. **Validate extraction results** by checking statistics and sample outputs
5. **Use expand_rows carefully** - can significantly increase dataset size
6. **Filter empty results** appropriately with drop_na parameter

Performance Notes
-----------------

* Regex extraction is efficient for datasets up to 100K+ rows
* Row expansion can significantly increase memory usage
* Validation adds minimal overhead
* Processing time scales linearly with dataset size and xrefs complexity

Common Use Cases
----------------

**Knowledge Graph Integration**
  Extract UniProt IDs from KG2c or SPOKE protein nodes for mapping

**Data Standardization**
  Convert complex xrefs to standardized UniProt identifiers

**Multi-Database Reconciliation**
  Extract UniProt IDs as primary keys for cross-database mapping

**Protein Network Analysis**
  Prepare protein datasets with clean UniProt identifiers

Integration
-----------

This action typically follows data loading and precedes mapping operations:

.. code-block:: yaml

    steps:
      # 1. Load protein data with xrefs
      - name: load_kg2c_proteins
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/kg2c_proteins.csv"
            identifier_column: "node_id"
            output_key: "kg2c_raw"
      
      # 2. Extract UniProt IDs
      - name: extract_uniprot
        action:
          type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
          params:
            dataset_key: "kg2c_raw"
            xrefs_column: "all_node_curie"
            output_column: "uniprot_id"
            handle_multiple: "first"
            keep_isoforms: false
            drop_na: true
      
      # 3. Continue with protein mapping
      - name: map_to_reference
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "kg2c_raw"
            target_dataset_key: "reference_proteins"
            output_key: "mapped_proteins"