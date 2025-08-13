GENERATE_METABOLOMICS_REPORT
============================

Generate comprehensive multi-format reports for metabolomics mapping results.

Purpose
-------

This action creates detailed, professional reports documenting metabolomics mapping results across multiple datasets. It provides:

* Comprehensive analysis of three-way metabolite overlaps
* Progressive matching methodology documentation
* Quality metrics and confidence distributions
* Multiple export formats (Markdown, HTML, JSON)
* Actionable recommendations for improvement
* Visual integration support

Parameters
----------

Required Parameters
~~~~~~~~~~~~~~~~~~~

**statistics_key** (string)
  Key for overlap statistics in context['results'].

**matches_key** (string)
  Key for three-way matches dataset in context['datasets'].

**nightingale_reference** (string)
  Key for Nightingale reference data in context['datasets'].

**output_dir** (string)
  Output directory path where reports will be saved.

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**metrics_keys** (list of strings)
  Keys for stage-specific metrics data from context['metrics'].
  Default: []

**report_format** (string)
  Primary report format for generation.
  Default: "markdown"

**include_sections** (list of strings)
  Report sections to include. Available sections:
  
  * executive_summary
  * methodology_overview
  * dataset_overview
  * progressive_matching_results
  * three_way_overlap_analysis
  * confidence_distribution
  * quality_metrics
  * recommendations
  
  Default: All sections

**export_formats** (list of strings)
  Output formats to generate: 'markdown', 'html', 'json', 'pdf'.
  Default: ["markdown", "html"]

**template_dir** (string)
  Custom template directory for report styling.
  Default: None

**include_visualizations** (boolean)
  Embed visualization references in report.
  Default: true

**max_examples** (integer)
  Maximum number of examples to include per section.
  Default: 10

Report Sections
---------------

**Executive Summary**
  High-level overview with key achievements, metrics, and recommendations.

**Methodology Overview**
  Detailed description of the three-stage progressive enhancement approach.

**Dataset Overview**
  Analysis of input datasets, platform characteristics, and data quality.

**Progressive Matching Results**
  Stage-by-stage results from Nightingale harmonization through semantic matching.

**Three-Way Overlap Analysis**
  Comprehensive overlap statistics, Venn diagram analysis, and biological significance.

**Confidence Distribution**
  Analysis of matching confidence levels and quality indicators.

**Quality Metrics**
  Data quality assessment, validation rates, and method effectiveness.

**Recommendations**
  Actionable recommendations for validation, process improvement, and strategic direction.

Example Usage
-------------

Complete Report Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: generate_comprehensive_report
      action:
        type: GENERATE_METABOLOMICS_REPORT
        params:
          statistics_key: "three_way_overlap_stats"
          matches_key: "three_way_matches"
          nightingale_reference: "nightingale_reference"
          output_dir: "/reports/metabolomics"
          export_formats: ["markdown", "html", "json"]
          include_visualizations: true

Custom Section Selection
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: generate_summary_report
      action:
        type: GENERATE_METABOLOMICS_REPORT
        params:
          statistics_key: "overlap_results"
          matches_key: "final_matches"
          nightingale_reference: "nmr_reference"
          output_dir: "/reports/summary"
          include_sections:
            - "executive_summary"
            - "three_way_overlap_analysis"
            - "recommendations"
          export_formats: ["markdown", "html"]

Quality-Focused Report
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: generate_quality_report
      action:
        type: GENERATE_METABOLOMICS_REPORT
        params:
          statistics_key: "validation_stats"
          matches_key: "validated_matches"
          nightingale_reference: "reference_data"
          output_dir: "/reports/quality"
          include_sections:
            - "confidence_distribution"
            - "quality_metrics"
            - "recommendations"
          max_examples: 20

Multiple Format Export
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    - name: export_all_formats
      action:
        type: GENERATE_METABOLOMICS_REPORT
        params:
          statistics_key: "final_statistics"
          matches_key: "all_matches"
          nightingale_reference: "nmr_ref"
          output_dir: "/reports/complete"
          export_formats: ["markdown", "html", "json", "pdf"]
          include_visualizations: true

Required Input Data Structure
-----------------------------

**Statistics Data (context['results'][statistics_key])**
.. code-block:: python

    {
        "total_unique_metabolites": 245,
        "three_way_overlap": {
            "count": 89,
            "percentage": 36.3
        },
        "pairwise_overlaps": {
            "Israeli10K_UKBB": {
                "overlap_count": 156,
                "jaccard_index": 0.745
            },
            "Israeli10K_Arivale": {
                "overlap_count": 134,
                "jaccard_index": 0.623
            },
            "UKBB_Arivale": {
                "overlap_count": 142,
                "jaccard_index": 0.651
            }
        },
        "dataset_counts": {
            "Israeli10K": {"total": 189, "unique": 167},
            "UKBB": {"total": 203, "unique": 178},
            "Arivale": {"total": 167, "unique": 145}
        },
        "overlap_summary": {
            "three_datasets": 89,
            "two_datasets": 98,
            "only_one_dataset": 58
        }
    }

**Matches Data (context['datasets'][matches_key])**
.. code-block:: python

    [
        {
            "metabolite_name": "Total cholesterol",
            "Israeli10K_id": "Total_C",
            "UKBB_id": "Total_C", 
            "Arivale_id": "Cholesterol, Total",
            "confidence_score": 0.95,
            "match_method": "fuzzy_match"
        },
        {
            "metabolite_name": "Alanine",
            "Israeli10K_id": "Ala",
            "UKBB_id": "Ala",
            "Arivale_id": "L-Alanine",
            "confidence_score": 0.92,
            "match_method": "api_enriched"
        }
    ]

Output Files
------------

**Markdown Report (.md)**
  Primary structured report with full analysis and recommendations.

**HTML Report (.html)**
  Styled web version with tables, formatting, and embedded visualizations.

**JSON Data (.json)**
  Structured data export of all report statistics and metadata.

**PDF Report (.pdf)**
  Print-ready version (requires additional dependencies).

Report Structure Example
------------------------

.. code-block:: markdown

    # Three-Way Metabolomics Mapping Report
    
    Generated: 2024-01-15 14:30:00
    
    ## Table of Contents
    1. [Executive Summary](#executive-summary)
    2. [Methodology Overview](#methodology-overview)
    3. [Dataset Overview](#dataset-overview)
    4. [Progressive Matching Results](#progressive-matching-results)
    5. [Three-Way Overlap Analysis](#three-way-overlap-analysis)
    6. [Confidence Distribution](#confidence-distribution)
    7. [Quality Metrics](#quality-metrics)
    8. [Recommendations](#recommendations)
    
    # Executive Summary
    
    ## Key Achievements
    - Successfully mapped **245** unique metabolites across three cohorts
    - Achieved **36.3%** three-way overlap (89 metabolites)
    - Overall mapping success rate: **76.3%**
    
    ## Mapping Performance by Stage
    | Stage | Method | Matches | Success Rate | Avg Confidence |
    |-------|--------|---------|--------------|----------------|
    | Stage 1 | Nightingale Platform | 156 | 92.3% | 0.94 |
    | Stage 2.1 | Direct Fuzzy Match | 78 | 85.2% | 0.89 |
    | Stage 2.2 | API Enhanced | 45 | 78.9% | 0.86 |
    | Stage 2.3 | Semantic Match | 23 | 73.1% | 0.82 |

Output Format Details
---------------------

The action stores generated files in the execution context:

.. code-block:: python

    # Context after execution
    {
        "output_files": {
            "metabolomics_report_markdown": "/reports/metabolomics_mapping_report_20240115_143000.md",
            "metabolomics_report_html": "/reports/metabolomics_mapping_report_20240115_143000.html",
            "metabolomics_report_json": "/reports/metabolomics_mapping_report_20240115_143000_data.json"
        }
    }

Quality Metrics Included
-------------------------

**Data Quality Indicators**
  Input completeness, identifier coverage, validation rates

**Matching Quality**
  Confidence distribution, method effectiveness, success rates

**Overlap Analysis**
  Three-way overlap statistics, pairwise comparisons, Jaccard indices

**Performance Metrics**
  Processing times, resource utilization, scalability metrics

Visualization Integration
-------------------------

When ``include_visualizations`` is enabled:

* References to generated visualization files
* Venn diagrams for overlap analysis
* Distribution charts for confidence levels
* Performance comparison graphs

Error Handling
--------------

**Missing data keys**
  .. code-block::
  
      Error: Statistics key 'missing_stats' not found in context
      
  Solution: Verify all required data keys exist from previous actions.

**Output directory issues**
  .. code-block::
  
      Error: Permission denied creating directory '/reports/'
      
  Solution: Ensure write permissions for output directory.

**Template errors**
  .. code-block::
  
      Warning: Section 'custom_section' generator not found
      
  Solution: Use only supported section names or extend with custom generators.

Best Practices
--------------

1. **Run after all mapping steps** - Generate reports as final pipeline step
2. **Include all relevant sections** - Comprehensive reports provide better insights
3. **Use multiple formats** - Different formats serve different audiences
4. **Organize output directories** - Use timestamped directories for version control
5. **Validate input data** - Ensure all required statistics and matches are available
6. **Review generated reports** - Manually verify key metrics and recommendations

Performance Notes
-----------------

* Report generation is typically fast (< 1 minute for large datasets)
* HTML conversion requires markdown library
* PDF generation requires additional dependencies (weasyprint)
* JSON export enables programmatic analysis of results
* Memory usage scales with number of matches and statistics

Integration Patterns
--------------------

**End-of-Pipeline Reporting**
.. code-block:: yaml

    steps:
      # ... all mapping steps ...
      
      - name: calculate_final_overlaps
        action:
          type: CALCULATE_THREE_WAY_OVERLAP
          params:
            datasets: ["israeli10k", "ukbb", "arivale"]
            output_key: "final_overlaps"
      
      - name: generate_report
        action:
          type: GENERATE_METABOLOMICS_REPORT
          params:
            statistics_key: "final_overlaps"
            matches_key: "three_way_matches"
            nightingale_reference: "nmr_reference"
            output_dir: "/results/reports"

**Quality Assessment Workflow**
.. code-block:: yaml

    steps:
      # ... mapping and validation steps ...
      
      - name: quality_focused_report
        action:
          type: GENERATE_METABOLOMICS_REPORT
          params:
            statistics_key: "quality_metrics"
            matches_key: "validated_matches"
            nightingale_reference: "reference"
            output_dir: "/quality/reports"
            include_sections:
              - "executive_summary"
              - "confidence_distribution"
              - "quality_metrics"
              - "recommendations"

Common Use Cases
----------------

**Research Publication**
  Generate comprehensive reports for manuscript supplementary materials

**Quality Control**
  Create quality-focused reports for data validation and review

**Stakeholder Communication**
  Produce executive summaries for non-technical audiences

**Method Validation**
  Document mapping methodology and performance metrics

**Reproducibility**
  Provide detailed documentation for analysis replication