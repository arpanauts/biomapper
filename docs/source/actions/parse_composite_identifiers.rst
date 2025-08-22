Parse Composite Identifiers
===========================

.. automodule:: src.actions.utils.data_processing.parse_composite_identifiers_v2

Overview
--------

The ``PARSE_COMPOSITE_IDENTIFIERS`` action handles the common biological data challenge of composite identifiers - single fields containing multiple identifiers separated by various delimiters. This action safely parses, expands, and normalizes composite identifiers while preserving original values for traceability.

This is essential for processing real-world biological datasets where identifiers are often stored as comma-separated or pipe-separated values (e.g., "P12345,P67890|Q11128").

Key Features
------------

- **Multi-delimiter Support**: Handles commas, pipes, semicolons, and custom separators
- **Normalization**: Standardizes identifier formats (removes prefixes, versions)
- **Expansion**: Creates multiple rows from single composite entries
- **Preservation**: Maintains original composite values for audit trails
- **Validation**: Filters invalid or malformed identifiers

Common Use Cases
----------------

1. **KG2c xrefs Fields**: "UniProtKB:P12345|RefSeq:NP_001234|KEGG:K12345"
2. **SPOKE Identifiers**: "P12345,P67890;Q11128"
3. **Literature Mining**: "protein1|protein2|protein3" 
4. **Cross-references**: Multiple database IDs in single field

Parameters
----------

.. list-table::
   :widths: 25 15 10 50
   :header-rows: 1

   * - Parameter
     - Type
     - Required
     - Description
   * - ``input_key``
     - string
     - Yes
     - Key for the input dataset
   * - ``output_key``
     - string
     - Yes
     - Key for the expanded output dataset
   * - ``identifier_column``
     - string
     - Yes
     - Column containing composite identifiers
   * - ``separator_pattern``
     - string
     - No
     - Regex pattern for separators (default: "[,;|]")
   * - ``prefix_pattern``
     - string
     - No
     - Regex pattern to remove prefixes (default: UniProt patterns)
   * - ``normalize_ids``
     - boolean
     - No
     - Enable ID normalization (default: true)
   * - ``preserve_original``
     - boolean
     - No
     - Keep original composite value (default: true)
   * - ``filter_invalid``
     - boolean
     - No
     - Remove invalid identifiers (default: true)

Example Usage
-------------

YAML Strategy
~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: parse_composites
       action:
         type: PARSE_COMPOSITE_IDENTIFIERS
         params:
           input_key: kg2c_proteins
           output_key: expanded_proteins
           identifier_column: xrefs
           separator_pattern: "[,;|]"
           normalize_ids: true
           preserve_original: true

Python Client
~~~~~~~~~~~~~

.. code-block:: python

   from src.client.client_v2 import BiomapperClient

   client = BiomapperClient(base_url="http://localhost:8000")
   
   # Load dataset with composite identifiers
   context = {"datasets": {"composite_data": composite_df}}
   
   result = await client.run_action(
       action_type="PARSE_COMPOSITE_IDENTIFIERS",
       params={
           "input_key": "composite_data",
           "output_key": "parsed_data",
           "identifier_column": "protein_ids",
           "separator_pattern": "[,|]",
           "normalize_ids": True
       },
       context=context
   )

Input/Output Example
--------------------

Input Dataset
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - gene_name
     - xrefs
   * - CD4
     - UniProtKB:P01730|RefSeq:NP_000607
   * - TP53
     - UniProtKB:P04637,P04637-1|KEGG:hsa:7157
   * - BRCA1
     - P38398;Q3LRH6|UniProtKB:P38398

Output Dataset
~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 35 35 10
   :header-rows: 1

   * - gene_name
     - extracted_uniprot
     - _original_xrefs
     - _row_id
   * - CD4
     - P01730
     - UniProtKB:P01730|RefSeq:NP_000607
     - 1
   * - TP53
     - P04637
     - UniProtKB:P04637,P04637-1|KEGG:hsa:7157
     - 2a
   * - TP53
     - P04637
     - UniProtKB:P04637,P04637-1|KEGG:hsa:7157
     - 2b
   * - BRCA1
     - P38398
     - P38398;Q3LRH6|UniProtKB:P38398
     - 3a
   * - BRCA1
     - Q3LRH6
     - P38398;Q3LRH6|UniProtKB:P38398
     - 3b
   * - BRCA1
     - P38398
     - P38398;Q3LRH6|UniProtKB:P38398
     - 3c

Processing Steps
----------------

1. **Parsing Phase**
   
   - Split composite strings using separator pattern
   - Handle nested separators (commas within pipe-separated groups)
   - Remove empty strings and whitespace

2. **Normalization Phase**
   
   - Remove database prefixes (UniProtKB:, RefSeq:, etc.)
   - Strip version numbers (P12345.2 → P12345)
   - Handle isoform suffixes (P12345-1 → P12345 or preserve)
   - Apply format validation

3. **Expansion Phase**
   
   - Create multiple rows for each parsed identifier
   - Preserve all original columns
   - Add tracking columns (_original_*, _row_id)

4. **Validation Phase**
   
   - Filter malformed identifiers
   - Remove duplicates within same composite
   - Validate against expected patterns

Advanced Configuration
----------------------

Custom Separator Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # For complex separators
   separator_pattern: "[,;|\\s]+"  # Includes whitespace
   
   # For specific formats
   separator_pattern: "\\s*[,|]\\s*"  # Comma or pipe with optional spaces

Custom Prefix Removal
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Remove specific database prefixes
   prefix_pattern: "^(UniProtKB|RefSeq|KEGG):"
   
   # Remove version numbers
   prefix_pattern: "\\.[0-9]+$"

Normalization Options
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Preserve isoforms
   normalize_ids: true
   isoform_handling: "preserve"  # keep -1, -2 suffixes
   
   # Strict normalization
   normalize_ids: true
   isoform_handling: "remove"   # P12345-1 → P12345

Performance Considerations
--------------------------

Processing Speed
~~~~~~~~~~~~~~~~

Typical performance for different dataset sizes:
- **Small** (1K rows): <1 second
- **Medium** (10K rows): 2-5 seconds  
- **Large** (100K rows): 20-60 seconds
- **Very Large** (1M+ rows): 2-10 minutes

Performance factors:
- Number of composite identifiers per row
- Complexity of separator patterns
- Normalization processing enabled
- Output dataset size after expansion

Memory Usage
~~~~~~~~~~~~

Memory usage increases with expansion ratio:
- **Input**: 10K rows with average 2 IDs per composite
- **Output**: ~20K rows (2x expansion)
- **Memory**: ~3x input size during processing

Optimization Tips
~~~~~~~~~~~~~~~~~

1. **Batch Processing**: Process large datasets in chunks
2. **Pattern Optimization**: Use simple patterns when possible
3. **Selective Normalization**: Disable if not needed
4. **Memory Management**: Monitor expansion ratios

Real-World Examples
-------------------

KG2c Protein Processing
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Process KG2c xrefs for UniProt extraction
   - name: parse_kg2c_xrefs
     action:
       type: PARSE_COMPOSITE_IDENTIFIERS
       params:
         input_key: kg2c_proteins
         output_key: expanded_proteins
         identifier_column: xrefs
         separator_pattern: "[|,]"
         prefix_pattern: "^UniProtKB:"
         normalize_ids: true

SPOKE Identifier Expansion
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Handle SPOKE multi-identifier format
   - name: expand_spoke_ids
     action:
       type: PARSE_COMPOSITE_IDENTIFIERS
       params:
         input_key: spoke_data
         output_key: individual_proteins
         identifier_column: protein_identifiers
         separator_pattern: "[,;]"
         preserve_original: true

Coverage Impact Analysis
------------------------

Typical coverage improvements:
- **Before parsing**: 1,165 composite entries
- **After parsing**: 2,500+ individual identifiers
- **Unique identifiers**: 1,800+ after deduplication
- **Coverage gain**: 15-25% in subsequent matching stages

Best Practices
--------------

1. **Pattern Testing**: Validate separator patterns on sample data
2. **Original Preservation**: Always preserve original composite values
3. **Row Tracking**: Use _row_id for linking back to original entries
4. **Validation**: Check expansion ratios for reasonableness
5. **Deduplication**: Handle duplicates in downstream processing

Common Issues and Solutions
---------------------------

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Issue
     - Solution
   * - Unexpected expansion ratio
     - Check separator pattern specificity
   * - Missing identifiers after parsing
     - Verify prefix_pattern doesn't over-filter
   * - Performance issues
     - Process in smaller batches
   * - Memory errors
     - Reduce chunk size or increase memory limits
   * - Duplicate identifiers
     - Enable deduplication in downstream actions

Integration with Matching Actions
---------------------------------

The parsed identifiers typically feed into matching actions:

.. code-block:: yaml

   steps:
     - name: parse_composites
       action:
         type: PARSE_COMPOSITE_IDENTIFIERS
         params:
           input_key: raw_data
           output_key: expanded_data
           
     - name: direct_matching
       action:
         type: PROTEIN_NORMALIZE_ACCESSIONS
         params:
           input_key: expanded_data  # Uses parsed output
           output_key: normalized_data
           
     - name: merge_results
       action:
         type: MERGE_DATASETS
         params:
           input_keys: [normalized_data, reference_data]
           output_key: matched_results

See Also
--------

- :doc:`protein_extract_uniprot` - UniProt-specific extraction
- :doc:`protein_normalize_accessions` - Identifier normalization
- :doc:`../workflows/protein_mapping` - Complete protein workflows
- :doc:`../examples/real_world_cases` - Production use cases