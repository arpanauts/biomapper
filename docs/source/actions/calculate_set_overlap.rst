CALCULATE_SET_OVERLAP
=====================

Calculate overlap statistics from merged datasets with match metadata and generate Venn diagrams.

Purpose
-------

This action analyzes merged datasets from MERGE_WITH_UNIPROT_RESOLUTION to provide:

* Comprehensive overlap statistics between source and target datasets
* High-quality and total match statistics based on confidence thresholds
* Venn diagram generation (SVG and PNG formats)
* Detailed breakdown by match type and confidence
* Standardized output directory structure

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Context key of the merged dataset with match metadata from MERGE_WITH_UNIPROT_RESOLUTION.

**source_name** (string)
  Source dataset name for labeling (e.g., 'UKBB', 'ARV').

**target_name** (string)
  Target dataset name for labeling (e.g., 'HPA', 'KG2C').

**mapping_combo_id** (string)
  Unique mapping identifier (e.g., 'UKBB_HPA'). Used for output directory naming.

**output_key** (string)
  Key name to store the overlap statistics in context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**confidence_threshold** (float)
  Minimum confidence score for 'high quality' statistics. Default: 0.8 (range: 0.0-1.0)

**output_dir** (string)
  Base output directory for results. Default: "results"

Example Usage
-------------

.. code-block:: yaml

    - name: calculate_overlap
      action:
        type: CALCULATE_SET_OVERLAP
        params:
          input_key: "merged_data"
          source_name: "UKBB"
          target_name: "HPA"
          mapping_combo_id: "UKBB_HPA"
          confidence_threshold: 0.8
          output_dir: "results"
          output_key: "overlap_stats"

Output Format
-------------

The action generates multiple output files in `results/[mapping_combo_id]/`:

**Generated Files**

1. **statistics.csv** - Summary statistics with key metrics
2. **breakdown.csv** - Detailed breakdown by match type
3. **venn_diagram.svg** - Vector graphics Venn diagram
4. **venn_diagram.png** - Raster image Venn diagram  
5. **merged_dataset.csv** - Complete merged dataset with metadata

**Statistics Structure**

.. code-block:: python

    {
        "statistics": {
            "overlap_stats": {
                # Core counts
                "source_total": 1463,
                "target_total": 1825,
                "matched_total": 1401,
                "unmatched_total": 62,
                
                # Match rates
                "source_match_rate": 0.958,
                "target_match_rate": 0.768,
                "jaccard_index": 0.742,
                
                # High quality matches (above threshold)
                "high_quality_matches": 1350,
                "high_quality_rate": 0.964,
                
                # Match type breakdown
                "exact_matches": 1200,
                "fuzzy_matches": 150,
                "semantic_matches": 51,
                
                # File paths
                "output_files": [
                    "results/UKBB_HPA/statistics.csv",
                    "results/UKBB_HPA/breakdown.csv",
                    "results/UKBB_HPA/venn_diagram.svg",
                    "results/UKBB_HPA/venn_diagram.png",
                    "results/UKBB_HPA/merged_dataset.csv"
                ]
            }
        }
    }

Interpretation Guide
--------------------

Key Metrics Explained
~~~~~~~~~~~~~~~~~~~~~~

**source_match_rate**
  Percentage of source dataset identifiers that found matches in target.

**target_match_rate**  
  Percentage of target dataset covered by matches from source.

**jaccard_index**
  Similarity coefficient (intersection/union). Values closer to 1.0 indicate higher similarity.

**high_quality_rate**
  Percentage of matches above the confidence threshold.

**Match Type Distribution**
  - **exact_matches**: Direct UniProt accession matches
  - **fuzzy_matches**: Matches via alternative identifiers
  - **semantic_matches**: AI-powered semantic similarity matches

Example Analysis
~~~~~~~~~~~~~~~~

.. code-block:: python

    # High overlap scenario
    {
        "source_match_rate": 0.958,
        "target_match_rate": 0.768,
        "jaccard_index": 0.742,
        "high_quality_rate": 0.964
    }
    # Interpretation: Excellent source coverage with high-confidence matches

    # Low overlap scenario  
    {
        "source_match_rate": 0.234,
        "target_match_rate": 0.312,
        "jaccard_index": 0.156,
        "high_quality_rate": 0.450
    }
    # Interpretation: Limited overlap with low confidence matches

Use Cases
---------

**Dataset Comparison**
  Compare protein coverage between different studies or platforms.

**Quality Assessment**
  Evaluate how well datasets overlap with reference sets.

**Merge Planning**
  Determine the value of merging datasets based on overlap.

**Validation**
  Check expected overlaps between related datasets.

Best Practices
--------------

1. **Run after data loading** and any necessary merging steps
2. **Use descriptive output keys** like "ukbb_hpa_overlap" 
3. **Save Venn diagrams** for reports and presentations
4. **Compare multiple dataset pairs** in complex analyses
5. **Review timing metrics** to optimize large dataset processing

Integration Example
-------------------

Complete workflow with merge and overlap analysis:

.. code-block:: yaml

    name: "PROTEIN_OVERLAP_ANALYSIS"
    description: "Load, merge, and analyze protein dataset overlap"
    
    steps:
      - name: load_source
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/ukbb_proteins.csv"
            identifier_column: "uniprot"
            output_key: "source_data"
      
      - name: load_target
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/hpa_proteins.csv"
            identifier_column: "uniprot_id"
            output_key: "target_data"
      
      - name: merge_datasets
        action:
          type: MERGE_WITH_UNIPROT_RESOLUTION
          params:
            source_dataset_key: "source_data"
            target_dataset_key: "target_data"
            output_key: "merged_data"
      
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            input_key: "merged_data"
            source_name: "UKBB"
            target_name: "HPA"
            mapping_combo_id: "UKBB_HPA"
            confidence_threshold: 0.8
            output_key: "overlap_statistics"

See Also
--------

* :doc:`load_dataset_identifiers` - Load datasets for comparison
* :doc:`merge_with_uniprot_resolution` - Merge before overlap analysis