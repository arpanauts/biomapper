CALCULATE_THREE_WAY_OVERLAP
===========================

Calculate comprehensive three-way overlap statistics and generate visualizations for metabolite datasets.

Purpose
-------

This action performs detailed analysis of metabolite overlaps across three datasets, providing:

* Comprehensive overlap statistics (three-way and pairwise)
* Jaccard similarity indices
* Confidence distribution analysis
* Visualization generation (Venn diagrams, heatmaps, charts)
* Detailed CSV export capabilities
* Dataset membership analysis

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**input_key** (string)
  Key for combined matches from COMBINE_METABOLITE_MATCHES action.

**output_dir** (string)
  Directory path where output files and visualizations will be saved.

**mapping_combo_id** (string)
  Unique identifier for this mapping combination (used in file naming).

**output_key** (string)
  Key for storing calculated statistics in context.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**dataset_names** (list of strings)
  Names of the three datasets in order.
  Default: ["Israeli10K", "UKBB", "Arivale"]

**confidence_threshold** (float)
  Minimum confidence level (0.0-1.0) for including matches in overlap analysis.
  Default: 0.8

**generate_visualizations** (list of strings)
  List of visualizations to generate. Options:
  
  * venn_diagram_3way
  * confidence_heatmap
  * overlap_progression_chart
  * provenance_sankey
  * method_breakdown_pie
  
  Default: []

**export_detailed_results** (boolean)
  Whether to export detailed CSV files with match data.
  Default: true

Visualization Types
-------------------

**Venn Diagram (venn_diagram_3way)**
  Three-way Venn diagram showing exclusive and overlapping regions between datasets.

**Confidence Heatmap (confidence_heatmap)**
  Heatmap showing confidence level distribution across different overlap types.

**Overlap Progression Chart (overlap_progression_chart)**
  Bar chart showing metabolite distribution across datasets and overlap types.

**Provenance Sankey (provenance_sankey)**
  Flow diagram showing data provenance and matching methods (planned feature).

**Method Breakdown Pie (method_breakdown_pie)**
  Pie chart showing distribution of matching methods used (planned feature).

Example Usage
-------------

Basic Three-Way Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: calculate_overlaps
      action:
        type: CALCULATE_THREE_WAY_OVERLAP
        params:
          input_key: "combined_matches"
          output_dir: "/results/overlaps"
          mapping_combo_id: "nmr_metabolomics_v1"
          output_key: "overlap_statistics"
          confidence_threshold: 0.8

Complete Analysis with Visualizations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: comprehensive_overlap_analysis
      action:
        type: CALCULATE_THREE_WAY_OVERLAP
        params:
          input_key: "final_combined_matches"
          output_dir: "/analysis/comprehensive"
          mapping_combo_id: "three_way_metabolomics"
          output_key: "full_statistics"
          dataset_names: ["Israeli10K", "UKBB", "Arivale"]
          confidence_threshold: 0.85
          generate_visualizations:
            - "venn_diagram_3way"
            - "confidence_heatmap"
            - "overlap_progression_chart"
          export_detailed_results: true

High-Confidence Analysis
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: high_confidence_overlaps
      action:
        type: CALCULATE_THREE_WAY_OVERLAP
        params:
          input_key: "validated_matches"
          output_dir: "/results/high_confidence"
          mapping_combo_id: "validated_metabolomics"
          output_key: "validated_statistics"
          confidence_threshold: 0.9
          generate_visualizations:
            - "venn_diagram_3way"
            - "confidence_heatmap"

Custom Dataset Names
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: custom_three_way_analysis
      action:
        type: CALCULATE_THREE_WAY_OVERLAP
        params:
          input_key: "multi_cohort_matches"
          output_dir: "/analysis/custom"
          mapping_combo_id: "multi_cohort_v2"
          output_key: "custom_statistics"
          dataset_names: ["Cohort_A", "Cohort_B", "Cohort_C"]
          confidence_threshold: 0.75

Required Input Data Structure
-----------------------------

**Combined Matches Data (context['datasets'][input_key])**

.. code-block:: python

    {
        "three_way_matches": [
            {
                "metabolite_id": "cholesterol_total",
                "match_confidence": 0.95,
                "match_methods": ["fuzzy_match", "nightingale_platform"],
                "dataset_count": 3,
                "is_complete": true,
                "israeli10k": {
                    "field_name": "Total_C",
                    "display_name": "Total cholesterol",
                    "nightingale_name": "Total_C"
                },
                "ukbb": {
                    "field_id": "23400",
                    "title": "Cholesterol"
                },
                "arivale": {
                    "biochemical_name": "Cholesterol, Total",
                    "hmdb": "HMDB0000067",
                    "kegg": "C00187"
                }
            }
        ],
        "two_way_matches": [
            {
                "metabolite_id": "alanine",
                "match_confidence": 0.88,
                "match_methods": ["api_enriched"],
                "dataset_count": 2,
                "is_complete": false,
                "israeli10k": {
                    "field_name": "Ala",
                    "display_name": "Alanine",
                    "nightingale_name": "Ala"
                },
                "ukbb": {
                    "field_id": "23401",
                    "title": "Alanine"
                },
                "arivale": null
            }
        ]
    }

Output Statistics Structure
---------------------------

The action generates comprehensive statistics stored in context:

.. code-block:: python

    {
        "dataset_statistics": {
            "Israeli10K": {
                "total_metabolites": 189,
                "unique_metabolites": 45
            },
            "UKBB": {
                "total_metabolites": 203,
                "unique_metabolites": 52
            },
            "Arivale": {
                "total_metabolites": 167,
                "unique_metabolites": 38
            }
        },
        "overlap_statistics": {
            "Israeli10K_UKBB": {
                "count": 156,
                "percentage_of_first": 82.5,
                "percentage_of_second": 76.8,
                "jaccard_index": 0.745,
                "metabolite_ids": ["cholesterol_total", "glucose", "lactate"],
                "confidence_distribution": {
                    "high": 124,
                    "medium": 28,
                    "low": 4
                }
            },
            "Israeli10K_Arivale": {
                "count": 134,
                "percentage_of_first": 70.9,
                "percentage_of_second": 80.2,
                "jaccard_index": 0.623,
                "metabolite_ids": ["alanine", "glucose", "triglycerides"],
                "confidence_distribution": {
                    "high": 98,
                    "medium": 31,
                    "low": 5
                }
            },
            "UKBB_Arivale": {
                "count": 142,
                "percentage_of_first": 70.0,
                "percentage_of_second": 85.0,
                "jaccard_index": 0.651,
                "metabolite_ids": ["hdl_cholesterol", "ldl_cholesterol"],
                "confidence_distribution": {
                    "high": 106,
                    "medium": 29,
                    "low": 7
                }
            },
            "three_way": {
                "count": 89,
                "percentage_of_first": 47.1,
                "percentage_of_second": 43.8,
                "percentage_of_third": 53.3,
                "jaccard_index": 0.363,
                "metabolite_ids": ["cholesterol_total", "glucose", "alanine"],
                "confidence_distribution": {
                    "high": 71,
                    "medium": 15,
                    "low": 3
                }
            }
        },
        "visualizations": {
            "venn_diagram": "/results/overlaps/venn_diagram_3way.png",
            "confidence_heatmap": "/results/overlaps/confidence_heatmap.png",
            "overlap_progression": "/results/overlaps/overlap_progression_chart.png"
        },
        "output_directory": "/results/overlaps"
    }

Generated Output Files
----------------------

**Visualization Files**
  * ``venn_diagram_3way.png`` - Three-way Venn diagram
  * ``confidence_heatmap.png`` - Confidence distribution heatmap
  * ``overlap_progression_chart.png`` - Metabolite distribution bar chart

**CSV Export Files**
  * ``{mapping_combo_id}_three_way_matches.csv`` - Detailed match data
  * ``{mapping_combo_id}_overlap_statistics.csv`` - Statistical summaries

**Detailed Match CSV Structure**
.. code-block:: csv

    metabolite_id,match_confidence,match_methods,dataset_count,is_complete,israeli10k_field_name,israeli10k_display_name,nightingale_name,ukbb_field_id,ukbb_title,arivale_biochemical_name,arivale_hmdb,arivale_kegg
    cholesterol_total,0.95,fuzzy_match;nightingale_platform,3,True,Total_C,Total cholesterol,Total_C,23400,Cholesterol,"Cholesterol, Total",HMDB0000067,C00187
    alanine,0.88,api_enriched,2,False,Ala,Alanine,Ala,23401,Alanine,,,

**Overlap Statistics CSV Structure**
.. code-block:: csv

    overlap_type,count,jaccard_index,percentage_of_first,percentage_of_second,percentage_of_third,high_confidence_count,medium_confidence_count,low_confidence_count
    Israeli10K_UKBB,156,0.745,82.5,76.8,,124,28,4
    Israeli10K_Arivale,134,0.623,70.9,80.2,,98,31,5
    UKBB_Arivale,142,0.651,70.0,85.0,,106,29,7
    three_way,89,0.363,47.1,43.8,53.3,71,15,3

Statistical Metrics Explained
-----------------------------

**Jaccard Index**
  Measures similarity between datasets: ``|A ∩ B| / |A ∪ B|``
  
  * 1.0 = Perfect overlap
  * 0.0 = No overlap

**Percentage Calculations**
  * percentage_of_first: Overlap as percentage of first dataset
  * percentage_of_second: Overlap as percentage of second dataset
  * percentage_of_third: Overlap as percentage of third dataset (three-way only)

**Confidence Distribution**
  * high: Confidence ≥ 0.9
  * medium: 0.7 ≤ Confidence < 0.9
  * low: Confidence < 0.7

Visualization Details
---------------------

**Venn Diagram Features**
  * Color-coded regions for each dataset
  * Numerical labels showing metabolite counts
  * Statistical summary below diagram
  * High-resolution PNG output (300 DPI)

**Confidence Heatmap Features**
  * Percentage-based visualization
  * Color gradient from low to high confidence
  * Annotated cells with exact percentages
  * Separate analysis for each overlap type

**Progression Chart Features**
  * Bar chart showing distribution across categories
  * Individual dataset counts
  * Pairwise overlap counts
  * Three-way overlap count
  * Value labels on each bar

Error Handling
--------------

**Missing input data**
  .. code-block::
  
      Error: No data found for input key: 'missing_matches'
      
  Solution: Ensure COMBINE_METABOLITE_MATCHES was run first.

**Insufficient datasets**
  .. code-block::
  
      Error: Three dataset names required, got 2
      
  Solution: Provide exactly three dataset names.

**Visualization dependencies**
  .. code-block::
  
      Warning: matplotlib_venn not installed, skipping Venn diagram
      
  Solution: Install required packages with ``poetry add matplotlib-venn seaborn``.

**Output directory permissions**
  .. code-block::
  
      Error: Permission denied creating directory
      
  Solution: Ensure write permissions for output directory.

Best Practices
--------------

1. **Set appropriate confidence thresholds** - Higher thresholds for stricter analysis
2. **Generate key visualizations** - Venn diagrams and heatmaps provide best insights
3. **Use descriptive mapping IDs** - Include version and date information
4. **Export detailed results** - CSV files enable further analysis
5. **Validate input data** - Ensure combined matches contain expected structure
6. **Review statistical outputs** - Verify Jaccard indices and overlap percentages
7. **Organize output directories** - Use structured naming for multiple analyses

Performance Notes
-----------------

* Analysis scales linearly with number of matches
* Visualization generation adds 10-30 seconds depending on complexity
* CSV export time depends on match count and detail level
* Memory usage scales with dataset size and overlap complexity
* Large datasets (>10K metabolites) process efficiently

Dependencies
------------

**Required for basic functionality:**
  * pandas (CSV export)

**Required for visualizations:**
  * matplotlib (basic charts)
  * matplotlib-venn (Venn diagrams)
  * seaborn (heatmaps)

Integration
-----------

This action typically follows metabolite matching and combination:

.. code-block:: yaml

    steps:
      # ... previous matching steps ...
      
      - name: combine_all_matches
        action:
          type: COMBINE_METABOLITE_MATCHES
          params:
            nightingale_matches_key: "nightingale_baseline"
            enhanced_matches_key: "enhanced_results"
            output_key: "combined_matches"
      
      - name: analyze_overlaps
        action:
          type: CALCULATE_THREE_WAY_OVERLAP
          params:
            input_key: "combined_matches"
            output_dir: "/results/analysis"
            mapping_combo_id: "metabolomics_v1"
            output_key: "overlap_stats"
            generate_visualizations:
              - "venn_diagram_3way"
              - "confidence_heatmap"
      
      - name: generate_report
        action:
          type: GENERATE_METABOLOMICS_REPORT
          params:
            statistics_key: "overlap_stats"
            matches_key: "combined_matches"