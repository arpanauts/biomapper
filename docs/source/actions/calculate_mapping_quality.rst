calculate_mapping_quality
==========================

The ``CALCULATE_MAPPING_QUALITY`` action provides comprehensive quality assessment for biological identifier mappings with detailed metrics and recommendations.

Overview
--------

This action evaluates the quality of identifier mapping results across multiple dimensions:

- **Match rates and coverage** statistics
- **Confidence score distributions** and thresholds
- **Precision and recall** against reference datasets
- **Duplicate and ambiguity detection** 
- **Identifier format consistency** validation
- **Actionable recommendations** for improvement

The action is essential for validating mapping strategies and optimizing biomedical data integration pipelines.

Parameters
----------

.. code-block:: yaml

   action:
     type: CALCULATE_MAPPING_QUALITY
     params:
       source_key: "original_dataset"
       mapped_key: "mapping_results"
       source_id_column: "identifier"
       mapped_id_column: "mapped_identifier"
       confidence_column: "confidence_score"
       metrics_to_calculate: ["match_rate", "coverage", "precision", "confidence_distribution"]
       confidence_threshold: 0.8
       output_key: "quality_metrics"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**source_key** : str
    Key of the original source dataset

**mapped_key** : str
    Key of the dataset containing mapping results

**source_id_column** : str
    Column containing original source identifiers

**mapped_id_column** : str
    Column containing mapped target identifiers

**output_key** : str
    Key for storing quality metrics results

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**confidence_column** : str, default=None
    Column containing mapping confidence scores

**metrics_to_calculate** : list[str], default=["match_rate", "coverage", "precision"]
    Quality metrics to compute

**confidence_threshold** : float, default=0.8
    Threshold for high-confidence mappings

**reference_dataset_key** : str, default=None
    Reference dataset for precision/recall calculation

**include_detailed_report** : bool, default=True
    Generate detailed per-identifier analysis

Available Quality Metrics
-------------------------

Match Rate
~~~~~~~~~~
- **Definition**: Proportion of source identifiers successfully mapped
- **Formula**: successful_mappings / total_source_identifiers
- **Range**: 0.0 to 1.0
- **Interpretation**: Higher is better

Coverage
~~~~~~~~
- **Definition**: Proportion of mapping attempts that succeeded
- **Formula**: successful_mappings / total_mapped_attempts
- **Range**: 0.0 to 1.0
- **Interpretation**: Higher is better

Precision
~~~~~~~~~
- **Definition**: Proportion of predicted mappings that are correct
- **Formula**: true_positives / (true_positives + false_positives)
- **Requires**: Reference dataset for validation
- **Range**: 0.0 to 1.0

Recall
~~~~~~
- **Definition**: Proportion of actual mappings that were found
- **Formula**: true_positives / (true_positives + false_negatives)
- **Requires**: Reference dataset for validation
- **Range**: 0.0 to 1.0

F1-Score
~~~~~~~~
- **Definition**: Harmonic mean of precision and recall
- **Formula**: 2 × (precision × recall) / (precision + recall)
- **Range**: 0.0 to 1.0
- **Interpretation**: Balanced measure of accuracy

Confidence Distribution
~~~~~~~~~~~~~~~~~~~~~~~
- **Average confidence**: Mean of all confidence scores
- **Min/Max confidence**: Range of confidence values
- **High/Low confidence counts**: Based on threshold

Duplicate Rate
~~~~~~~~~~~~~~
- **Definition**: Proportion of non-unique mapped identifiers
- **Formula**: duplicate_mappings / total_mappings
- **Interpretation**: Lower is better (indicates many-to-one mappings)

Ambiguity Rate
~~~~~~~~~~~~~~
- **Definition**: Proportion of source IDs mapping to multiple targets
- **Formula**: ambiguous_sources / total_sources
- **Interpretation**: Lower is better (indicates one-to-many mappings)

Identifier Quality
~~~~~~~~~~~~~~~~~~
- **Format consistency**: Proportion of well-formatted identifiers
- **Completeness**: Proportion of non-null identifiers
- **Pattern validation**: Adherence to expected ID formats

Example Usage
-------------

Basic Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: assess_mapping_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "protein_data"
           mapped_key: "uniprot_mappings"
           source_id_column: "protein_id"
           mapped_id_column: "uniprot_accession"
           confidence_column: "mapping_confidence"
           output_key: "protein_mapping_quality"

Comprehensive Quality Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: comprehensive_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "metabolite_dataset"
           mapped_key: "hmdb_mappings"
           source_id_column: "metabolite_name"
           mapped_id_column: "hmdb_id"
           confidence_column: "match_confidence"
           metrics_to_calculate:
             - "match_rate"
             - "coverage" 
             - "precision"
             - "recall"
             - "f1_score"
             - "confidence_distribution"
             - "duplicate_rate"
             - "ambiguity_rate"
             - "identifier_quality"
           confidence_threshold: 0.85
           reference_dataset_key: "gold_standard_mappings"
           include_detailed_report: true
           output_key: "comprehensive_quality_metrics"

Pipeline Quality Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: protein_matching
       action:
         type: PROTEIN_MULTI_BRIDGE
         params:
           source_dataset_key: "experimental_proteins"
           target_dataset_key: "uniprot_database"
           output_key: "protein_matches"

     - name: validate_protein_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "experimental_proteins"
           mapped_key: "protein_matches"
           source_id_column: "protein_accession"
           mapped_id_column: "target_id"
           confidence_column: "confidence"
           metrics_to_calculate: ["match_rate", "coverage", "duplicate_rate"]
           confidence_threshold: 0.90
           output_key: "protein_quality_assessment"

Output Format
-------------

The action generates multiple types of output:

**Quality Metrics DataFrame**:
```
metric                    | value      | category
match_rate               | 0.847      | mapping_quality
coverage                 | 0.923      | mapping_quality  
avg_confidence           | 0.876      | mapping_quality
duplicate_rate           | 0.023      | mapping_quality
id_format_consistency    | 0.989      | mapping_quality
```

**Summary Statistics**:

.. code-block:: python

    {
        "total_source_identifiers": 1000,
        "total_mapped_identifiers": 923,
        "successful_mappings": 847,
        "failed_mappings": 76,
        "overall_quality_score": 0.834,
        "high_confidence_mappings": 723,
        "low_confidence_mappings": 124,
        "ambiguous_mappings": 12
    }

**Quality Distribution**:

.. code-block:: python

    {
        "high_quality": 723,    # Above confidence threshold
        "medium_quality": 124,  # Below threshold but mapped
        "low_quality": 0,       # Very low confidence
        "failed": 76           # No mapping found
    }

Detailed Reporting
------------------

When `include_detailed_report=True`, the action provides:

**Per-Identifier Analysis**:
- Success/failure status for each identifier
- Confidence scores where available
- Mapping method used
- Quality flags and warnings

**Data Quality Assessment**:
- Source dataset completeness
- Mapped dataset completeness
- Format validation results
- Anomaly detection

**Statistical Summary**:
- Distribution histograms
- Outlier identification
- Correlation analysis
- Trend detection

Recommendations Engine
----------------------

The action generates actionable recommendations based on quality metrics:

**Low Match Rate** (< 70%):
```
"Low match rate (65.2%). Consider using additional identifier types or fuzzy matching."
```

**High Duplicate Rate** (> 10%):
```  
"High duplicate rate (15.3%). Review mapping logic for one-to-many relationships."
```

**High Ambiguity Rate** (> 5%):
```
"High ambiguity rate (8.7%). Consider adding disambiguation criteria."
```

**Low Confidence** (< threshold):
```
"Low average confidence (0.72). Review confidence scoring algorithm."
```

**Poor Coverage** (< 80%):
```
"Consider preprocessing source identifiers (normalization, cleaning) to improve match rates."
```

Quality Score Calculation
-------------------------

The overall quality score is a weighted combination of metrics:

.. code-block:: python

    weights = {
        "match_rate": 0.3,           # Primary importance
        "coverage": 0.2,             # Secondary importance  
        "precision": 0.2,            # Accuracy measure
        "avg_confidence": 0.15,      # Confidence in results
        "id_format_consistency": 0.1, # Data quality
        "f1_score": 0.05            # Balanced accuracy
    }
    
    overall_score = sum(metric_value * weight for metric, weight in weights.items())
```

Integration Examples
--------------------

With Multi-Stage Matching
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: exact_matching
       action:
         type: NIGHTINGALE_NMR_MATCH
         params:
           dataset_key: "metabolites"
           output_key: "exact_matches"

     - name: assess_exact_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "metabolites"
           mapped_key: "exact_matches"
           source_id_column: "metabolite_name"
           mapped_id_column: "matched_name"
           output_key: "exact_match_quality"

     - name: fuzzy_matching  
       action:
         type: SEMANTIC_METABOLITE_MATCH
         params:
           unmatched_dataset: "unmatched_metabolites"
           output_key: "semantic_matches"

     - name: assess_semantic_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "unmatched_metabolites"
           mapped_key: "semantic_matches"
           confidence_column: "match_confidence"
           output_key: "semantic_quality"

With Quality Monitoring
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: protein_mapping
       action:
         type: PROTEIN_MULTI_BRIDGE
         # ... mapping parameters

     - name: quality_check
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "input_proteins"
           mapped_key: "protein_mappings"
           metrics_to_calculate: ["match_rate", "precision", "duplicate_rate"]
           confidence_threshold: 0.85
           output_key: "quality_metrics"

     - name: quality_gate
       action:
         type: CUSTOM_TRANSFORM
         params:
           dataset_key: "quality_metrics"
           expression: |
             if context['statistics']['overall_quality_score'] < 0.7:
                 raise ValueError(f"Quality score {context['statistics']['overall_quality_score']} below threshold")

Performance Considerations
--------------------------

**Large Dataset Optimization**:
- Sampling for detailed analysis when datasets > 10K records
- Streaming processing for memory efficiency
- Parallel computation for metric calculation

**Memory Management**:
- Chunked processing for massive datasets
- Selective metric calculation to reduce overhead
- Efficient data structures for statistics

**Computational Complexity**:
- O(n) for basic metrics (match_rate, coverage)
- O(n log n) for duplicate detection
- O(n²) for precision/recall with large reference sets

Best Practices
--------------

1. **Calculate core metrics**: Always include match_rate, coverage, and confidence_distribution
2. **Use reference datasets**: Enable precision/recall calculation when ground truth available  
3. **Set appropriate thresholds**: Adjust confidence_threshold based on application requirements
4. **Monitor trends**: Track quality metrics over time to detect pipeline degradation
5. **Review recommendations**: Act on actionable recommendations to improve mapping quality
6. **Validate against gold standards**: Use known high-quality mappings for validation

Error Handling
--------------

The action handles various data quality issues:

- **Missing datasets**: Clear error messages for missing keys
- **Column mismatches**: Validation of required columns
- **Empty datasets**: Graceful handling with appropriate warnings
- **Invalid confidence scores**: Range validation and outlier detection
- **Reference dataset issues**: Fallback when precision/recall cannot be calculated

The quality assessment action provides essential validation capabilities for any biological identifier mapping pipeline, ensuring reliable and trustworthy data integration results.