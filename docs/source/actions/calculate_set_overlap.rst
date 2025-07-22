CALCULATE_SET_OVERLAP
=====================

Calculate overlap statistics and Venn diagram analysis between two biological datasets.

Purpose
-------

This action provides comprehensive overlap analysis including:

* Set intersection and union calculations
* Overlap percentages and ratios
* Venn diagram generation (SVG format)
* Detailed statistics on unique and shared identifiers
* Performance timing metrics

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**dataset_a_key** (string)
  Context key of the first dataset for comparison.

**dataset_b_key** (string)
  Context key of the second dataset for comparison.

**output_key** (string)
  Key name to store the overlap analysis results.

Example Usage
-------------

.. code-block:: yaml

    - name: analyze_overlap
      action:
        type: CALCULATE_SET_OVERLAP
        params:
          dataset_a_key: "ukbb_proteins"
          dataset_b_key: "hpa_proteins"  
          output_key: "overlap_analysis"

Output Format
-------------

The action generates comprehensive overlap statistics:

.. code-block:: python

    {
        "datasets": {
            "overlap_analysis": {
                # Core statistics
                "dataset_a_count": 1463,
                "dataset_b_count": 1825, 
                "intersection_count": 1401,
                "union_count": 1887,
                
                # Overlap percentages
                "overlap_percentage": 74.2,
                "dataset_a_coverage": 95.8,
                "dataset_b_coverage": 76.8,
                
                # Unique identifiers
                "unique_to_a": 62,
                "unique_to_b": 424,
                "shared_identifiers": 1401,
                
                # Venn diagram data
                "venn_diagram_svg": "/path/to/output/venn_diagram.svg",
                
                # Performance metrics
                "analysis_time_seconds": 0.15,
                "merge_time_seconds": 45.2,
                "total_mapping_time_seconds": 48.7
            }
        }
    }

Generated Files
---------------

**Venn Diagram (SVG)**
  Visual representation of the overlap saved as SVG file in the results directory.

**Statistics Summary**
  Detailed breakdown of overlap metrics included in the results.

Interpretation Guide
--------------------

Key Metrics Explained
~~~~~~~~~~~~~~~~~~~~~~

**overlap_percentage**
  Percentage of dataset A identifiers found in dataset B.

**dataset_a_coverage**  
  Percentage of dataset A covered by the intersection.

**dataset_b_coverage**
  Percentage of dataset B covered by the intersection.

**intersection_count**
  Number of identifiers present in both datasets.

**union_count**
  Total unique identifiers across both datasets.

Example Analysis
~~~~~~~~~~~~~~~~

.. code-block:: python

    # High overlap scenario
    {
        "overlap_percentage": 92.5,
        "dataset_a_coverage": 92.5,
        "dataset_b_coverage": 88.1
    }
    # Interpretation: Very similar datasets with high concordance

    # Low overlap scenario  
    {
        "overlap_percentage": 23.4,
        "dataset_a_coverage": 23.4,
        "dataset_b_coverage": 31.2
    }
    # Interpretation: Datasets cover different protein sets

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

Complete workflow with overlap analysis:

.. code-block:: yaml

    name: "DATASET_OVERLAP_ANALYSIS"
    description: "Load two datasets and analyze their overlap"
    
    steps:
      - name: load_dataset_a
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/dataset_a.csv"
            identifier_column: "uniprot"
            output_key: "dataset_a"
      
      - name: load_dataset_b
        action:
          type: LOAD_DATASET_IDENTIFIERS
          params:
            file_path: "/data/dataset_b.csv"
            identifier_column: "uniprot_id"
            output_key: "dataset_b"
      
      - name: calculate_overlap
        action:
          type: CALCULATE_SET_OVERLAP
          params:
            dataset_a_key: "dataset_a"
            dataset_b_key: "dataset_b"
            output_key: "final_analysis"

See Also
--------

* :doc:`load_dataset_identifiers` - Load datasets for comparison
* :doc:`merge_with_uniprot_resolution` - Merge before overlap analysis