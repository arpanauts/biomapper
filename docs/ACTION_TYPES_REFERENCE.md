# Biomapper Action Types Reference

This document describes the available action types that can be used in mapping strategies.

## Overview

Action types are the building blocks of mapping strategies. Each action type corresponds to a method in the MappingExecutor that performs a specific transformation or filtering operation on identifiers.

## Configuration Context

Action types are used within mapping strategies, which are now centrally defined in `mapping_strategies_config.yaml`. This separation allows:
- **Generic strategies** to use action types that work across all entity types
- **Entity-specific strategies** to use specialized action types as needed
- **Reusable components** through the EXECUTE_MAPPING_PATH action type

See the [Configuration Migration Guide](/home/ubuntu/biomapper/docs/CONFIGURATION_MIGRATION_GUIDE.md) for details on the new structure.

## Available Action Types

### CONVERT_IDENTIFIERS_LOCAL
**Purpose**: Convert identifiers using local data files defined in the endpoint configuration.

**Parameters**:
- `endpoint_context`: "SOURCE" or "TARGET" - which endpoint's data to use
- `output_ontology_type`: The target ontology type for conversion
- `input_ontology_type` (optional): Override the input ontology type

**Example**:
```yaml
action:
  type: "CONVERT_IDENTIFIERS_LOCAL"
  endpoint_context: "SOURCE"
  output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Converting UKBB Assay IDs to UniProt ACs using the UKBB's local mapping file.

---

### EXECUTE_MAPPING_PATH
**Purpose**: Execute a predefined mapping path from the `mapping_paths` section.

**Parameters**:
- `path_name`: Name of the mapping path to execute

**Example**:
```yaml
action:
  type: "EXECUTE_MAPPING_PATH"
  path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
```

**Use Case**: Running complex multi-step conversions that are reused across strategies.

---

### FILTER_IDENTIFIERS_BY_TARGET_PRESENCE
**Purpose**: Keep only identifiers that exist in the target endpoint's data.

**Parameters**:
- `endpoint_context`: "TARGET" - uses the target endpoint
- `ontology_type_to_match`: Which ontology type to check for presence

**Example**:
```yaml
action:
  type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
  endpoint_context: "TARGET"
  ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Filtering proteins to keep only those present in HPA dataset.

---

### FILTER_BY_TARGET_PRESENCE
**Purpose**: Alias for FILTER_IDENTIFIERS_BY_TARGET_PRESENCE (backward compatibility).

**Parameters**: Same as FILTER_IDENTIFIERS_BY_TARGET_PRESENCE

---

### MATCH_SHARED_ONTOLOGY
**Purpose**: Find matching identifiers between source and target using a shared ontology type.

**Parameters**:
- `shared_ontology_type`: The ontology type that both endpoints have

**Example**:
```yaml
action:
  type: "MATCH_SHARED_ONTOLOGY"
  shared_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Direct matching when both datasets have the same identifier type.

---

## Implemented Action Types

Strategy actions are primarily implemented as Python classes inheriting from `BaseStrategyAction` within the `biomapper.core.strategy_actions` package. They are typically specified in YAML strategies using `action_class_path` for dynamic loading, or by a simple `type: "ACTION_NAME"` for core, aliased actions.

*   **`biomapper.core.strategy_actions.bidirectional_match.BidirectionalMatchAction`**
    *   **YAML Type Alias:** `BIDIRECTIONAL_MATCH`
    *   **Purpose:** Performs intelligent bidirectional matching between source and target endpoints with support for composite identifier handling and many-to-many mapping relationships.
    *   **Key Parameters:**
        *   `source_ontology`: (string, required) Ontology type in source endpoint
        *   `target_ontology`: (string, required) Ontology type in target endpoint
        *   `match_mode`: (string) Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        *   `composite_handling`: (string) How to handle composite IDs - 'split_and_match', 'match_whole', 'both' (default: 'split_and_match')
        *   `track_unmatched`: (boolean) Whether to track unmatched identifiers (default: true)
        *   `save_matched_to`: (string) Context key to save matched pairs (default: 'matched_identifiers')
        *   `save_unmatched_source_to`: (string) Context key for unmatched source IDs (default: 'unmatched_source')
        *   `save_unmatched_target_to`: (string) Context key for unmatched target IDs (default: 'unmatched_target')
        *   `case_sensitive`: (boolean) Whether matching is case-sensitive (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "BIDIRECTIONAL_MATCH"
          source_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          match_mode: "many_to_many"
          composite_handling: "split_and_match"
          track_unmatched: true
          save_matched_to: "direct_matches"
          save_unmatched_source_to: "unmatched_ukbb"
          save_unmatched_target_to: "unmatched_hpa"
        ```

*   **`biomapper.core.strategy_actions.collect_matched_targets.CollectMatchedTargetsAction`**
    *   **YAML Type Alias:** `COLLECT_MATCHED_TARGETS`
    *   **Purpose:** Collect target identifiers from various match data structures in context. Extracts target identifiers from direct match pairs, match objects, and other structured match data.
    *   **Key Parameters:**
        *   `match_sources`: (list, required) List of context keys containing match data
        *   `output_key`: (string) Context key to save collected identifiers (default: 'matched_targets')
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "COLLECT_MATCHED_TARGETS"
          match_sources: ["direct_matches", "all_matches"]
          output_key: "matched_targets"
        ```

*   **`biomapper.core.strategy_actions.convert_identifiers_local.ConvertIdentifiersLocalAction`**
    *   **YAML Type Alias:** `CONVERT_IDENTIFIERS_LOCAL`
    *   **Purpose:** Convert identifiers from one ontology type to another using local data within a single endpoint.
    *   **Key Parameters:**
        *   `endpoint_context`: (string, required) "SOURCE" or "TARGET"
        *   `output_ontology_type`: (string, required) Target ontology type
        *   `input_ontology_type`: (string) Override current ontology type (optional)
        *   `mapping_path_name`: (string) Use specific mapping path for property selection (optional)
        *   `input_from`: (string) Context key to read identifiers from (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "SOURCE"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        ```

*   **`biomapper.core.strategy_actions.execute_mapping_path.ExecuteMappingPathAction`**
    *   **YAML Type Alias:** `EXECUTE_MAPPING_PATH`
    *   **Purpose:** Execute a predefined mapping path from the database.
    *   **Key Parameters:**
        *   `path_name`: (string, required) Name of the mapping path to execute
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "EXECUTE_MAPPING_PATH"
          path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
        ```

*   **`biomapper.core.strategy_actions.export_results.ExportResultsAction`**
    *   **YAML Type Alias:** `EXPORT_RESULTS`
    *   **Purpose:** Export mapping results in various structured formats (CSV, JSON, TSV) with support for custom column selection, mapping metadata, and provenance information.
    *   **Key Parameters:**
        *   `output_format`: (string, required) Format for export ('csv', 'json', 'tsv')
        *   `output_file`: (string) File path for saving results (required unless save_to_context)
        *   `columns`: (list) List of columns to include (optional, default: all available)
        *   `include_metadata`: (boolean) Include mapping metadata columns (default: true)
        *   `include_provenance`: (boolean) Include provenance information (default: false)
        *   `save_to_context`: (string) Context key to save exported data (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "EXPORT_RESULTS"
          output_format: "csv"
          output_file: "${OUTPUT_DIR}/ukbb_to_hpa_mapping_results.csv"
          include_metadata: true
          include_provenance: false
        ```

*   **`biomapper.core.strategy_actions.format_and_save_results_action.FormatAndSaveResultsAction`**
    *   **YAML Type Alias:** (None currently defined; use `action_class_path`)
    *   **Purpose:** Formats the final mapping results from context (mapped, unmapped, new identifiers) into a structured Pandas DataFrame, saves it to a CSV file, and generates a comprehensive JSON summary file. Supports `${OUTPUT_DIR}` expansion for output paths by resolving environment variables.
    *   **Key Parameters:**
        *   `mapped_data_context_key`: (string, required) Context key for the primary list/dictionary of successfully mapped identifiers (e.g., "mapped_identifiers_with_source").
        *   `unmapped_source_context_key`: (string, required) Context key for the list of source identifiers that remained unmapped (e.g., "final_unmapped_source").
        *   `new_target_context_key`: (string, required) Context key for target identifiers identified as new or not present in the initial source list (e.g., "final_new_targets").
        *   `output_csv_path`: (string, required) File path (supports `${OUTPUT_DIR}`) for saving the detailed mapping results in CSV format (e.g., "${OUTPUT_DIR}/mapping_results.csv").
        *   `output_json_summary_path`: (string, required) File path (supports `${OUTPUT_DIR}`) for saving the JSON summary of the mapping execution (e.g., "${OUTPUT_DIR}/mapping_summary.json").
        *   `execution_id_context_key`: (string, optional) Context key to retrieve the execution ID. Defaults to "execution_id". If not in context, attempts to read from `EXECUTION_ID` environment variable.
        *   `strategy_name_context_key`: (string, optional) Context key to retrieve the strategy name. Defaults to "strategy_name". If not in context, attempts to read from `STRATEGY_NAME` environment variable.
        *   `start_time_context_key`: (string, optional) Context key to retrieve the execution start time. Defaults to "start_time". If not in context, attempts to read from `START_TIME` environment variable.
    *   **Example YAML Usage:**
        ```yaml
        action:
          action_class_path: "biomapper.core.strategy_actions.format_and_save_results_action.FormatAndSaveResultsAction"
          params:
            mapped_data_context_key: "mapped_identifiers_with_source"
            unmapped_source_context_key: "final_unmapped_source"
            new_target_context_key: "final_new_targets"
            output_csv_path: "${OUTPUT_DIR}/ukbb_to_hpa_mapping_results_efficient.csv"
            output_json_summary_path: "${OUTPUT_DIR}/ukbb_to_hpa_mapping_summary_efficient.json"
        ```

*   **`biomapper.core.strategy_actions.filter_by_target_presence.FilterByTargetPresenceAction`**
    *   **YAML Type Alias:** `FILTER_BY_TARGET_PRESENCE` or `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`
    *   **Purpose:** Filter a list of identifiers, retaining only those that are present in the target endpoint's data.
    *   **Key Parameters:**
        *   `endpoint_context`: (string, required) Must be "TARGET"
        *   `ontology_type_to_match`: (string, required) Ontology type to check in target
        *   `conversion_path_to_match_ontology`: (string) Path to convert identifiers before checking (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "FILTER_BY_TARGET_PRESENCE"
          endpoint_context: "TARGET"
          ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        ```

*   **`biomapper.core.strategy_actions.generate_detailed_report.GenerateDetailedReportAction`**
    *   **YAML Type Alias:** `GENERATE_DETAILED_REPORT`
    *   **Purpose:** Generate a comprehensive mapping analysis report with detailed breakdown by mapping step, unmatched identifier analysis, provenance tracking, and many-to-many relationship analysis.
    *   **Key Parameters:**
        *   `output_file`: (string) File path for saving report (optional)
        *   `include_unmatched`: (boolean) Include analysis of unmatched identifiers (default: true)
        *   `grouping_strategy`: (string) How to group results ('by_step', 'by_ontology', 'by_method') (default: 'by_step')
        *   `format`: (string) Output format ('json', 'markdown', 'html') (default: 'markdown')
        *   `save_to_context`: (string) Context key to save report data (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "GENERATE_DETAILED_REPORT"
          output_file: "${OUTPUT_DIR}/ukbb_to_hpa_detailed_report.md"
          format: "markdown"
          include_unmatched: true
          grouping_strategy: "by_step"
        ```

*   **`biomapper.core.strategy_actions.generate_mapping_summary.GenerateMappingSummaryAction`**
    *   **YAML Type Alias:** `GENERATE_MAPPING_SUMMARY`
    *   **Purpose:** Generate a high-level summary of mapping results including aggregated statistics, coverage metrics, and timing information.
    *   **Key Parameters:**
        *   `output_format`: (string) Format for output ('console', 'json', 'csv') (default: 'console')
        *   `include_statistics`: (boolean) Include detailed statistics (default: true)
        *   `output_file`: (string) File path for saving summary (optional)
        *   `save_to_context`: (string) Context key to save summary data (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "GENERATE_MAPPING_SUMMARY"
          output_format: "console"
          include_statistics: true
          save_to_context: "mapping_summary"
        ```

*   **`biomapper.core.strategy_actions.load_endpoint_identifiers_action.LoadEndpointIdentifiersAction`**
    *   **YAML Type Alias:** (None currently defined; use `action_class_path`)
    *   **Purpose:** Loads a list of identifiers from a specified endpoint and ontology type, then stores this list into the execution context under a designated key. This action is typically used as the first step in a strategy to acquire the initial set of identifiers to be processed.
    *   **Key Parameters:**
        *   `endpoint_name`: (string, required) The name of the endpoint (defined in `protein_config.yaml` or similar) from which to load identifiers (e.g., "UKBB_PROTEIN").
        *   `ontology_type_name`: (string, required) The specific ontology type of the identifiers to be loaded from the endpoint (e.g., "PROTEIN_UNIPROTKB_AC_ONTOLOGY").
        *   `output_context_key`: (string, required) The key under which the loaded list of identifiers will be stored in the execution context (e.g., "initial_source_identifiers").
    *   **Example YAML Usage:**
        ```yaml
        action:
          action_class_path: "biomapper.core.strategy_actions.load_endpoint_identifiers_action.LoadEndpointIdentifiersAction"
          params:
            endpoint_name: "UKBB_PROTEIN"
            ontology_type_name: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
            output_context_key: "initial_source_identifiers"
        ```

*   **`biomapper.core.strategy_actions.populate_context.PopulateContextAction`**
    *   **YAML Type Alias:** `POPULATE_CONTEXT`
    *   **Purpose:** Populate context with execution metadata needed by reporting actions. Ensures that reporting actions have access to initial_identifiers, mapping_results, all_provenance, and step_results.
    *   **Key Parameters:**
        *   `mode`: (string) 'initialize' to set initial values, 'finalize' to compute final results
        *   `initial_identifiers_key`: (string) Context key to read initial identifiers from (for finalize mode)
    *   **Example YAML Usage:**
        ```yaml
        action:
          action_class_path: "biomapper.core.strategy_actions.populate_context.PopulateContextAction"
          params:
            mode: "initialize"
        ```

*   **`biomapper.core.strategy_actions.resolve_and_match_forward.ResolveAndMatchForwardAction`**
    *   **YAML Type Alias:** `RESOLVE_AND_MATCH_FORWARD`
    *   **Purpose:** Resolve historical/secondary identifiers via UniProt Historical API and match against target. Handles composite identifiers and supports many-to-many mappings.
    *   **Key Parameters:**
        *   `input_from`: (string) Context key to read from (default: 'unmatched_source')
        *   `match_against`: (string) Which endpoint to match against (default: 'TARGET')
        *   `resolver`: (string) Which resolver to use (default: 'UNIPROT_HISTORICAL_API')
        *   `target_ontology`: (string, required) Ontology type to match in target
        *   `append_matched_to`: (string) Where to append matches (default: 'all_matches')
        *   `update_unmatched`: (string) Update unmatched list (default: 'unmatched_source')
        *   `composite_handling`: (string) How to handle composite IDs (default: 'split_and_match')
        *   `match_mode`: (string) Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        *   `batch_size`: (integer) Batch size for API calls (default: 100)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "RESOLVE_AND_MATCH_FORWARD"
          input_from: "unmatched_ukbb"
          match_against: "TARGET"
          target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          resolver: "UNIPROT_HISTORICAL_API"
          append_matched_to: "all_matches"
          update_unmatched: "unmatched_ukbb"
          batch_size: 100
        ```

*   **`biomapper.core.strategy_actions.resolve_and_match_reverse.ResolveAndMatchReverse`**
    *   **YAML Type Alias:** `RESOLVE_AND_MATCH_REVERSE`
    *   **Purpose:** Resolve target identifiers via UniProt Historical API and match them against remaining source identifiers, maximizing match coverage for bidirectional mapping strategies.
    *   **Key Parameters:**
        *   `input_from`: (string) Context key for target IDs to resolve (default: 'unmatched_target')
        *   `match_against_remaining`: (string) Context key for remaining source IDs (default: 'unmatched_source')
        *   `resolver`: (string) Resolver type to use (default: 'UNIPROT_HISTORICAL_API')
        *   `source_ontology`: (string, required) Ontology type in source dataset
        *   `append_matched_to`: (string) Context key to append matches to (default: 'all_matches')
        *   `save_final_unmatched`: (string) Context key for final unmatched IDs (default: 'final_unmatched')
        *   `composite_handling`: (string) How to handle composite IDs (default: 'split_and_match')
        *   `match_mode`: (string) Matching mode - 'many_to_many' or 'one_to_one' (default: 'many_to_many')
        *   `batch_size`: (integer) Batch size for API calls (default: 100)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "RESOLVE_AND_MATCH_REVERSE"
          input_from: "unmatched_hpa"
          match_against_remaining: "unmatched_ukbb"
          source_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          resolver: "UNIPROT_HISTORICAL_API"
          append_matched_to: "all_matches"
          save_final_unmatched: "final_unmatched"
          batch_size: 100
        ```

*   **`biomapper.core.strategy_actions.visualize_mapping_flow.VisualizeMappingFlowAction`**
    *   **YAML Type Alias:** `VISUALIZE_MAPPING_FLOW`
    *   **Purpose:** Generate visual representation of mapping process including flow diagrams, charts for step-by-step statistics, and support for multiple visualization types (sankey, bar, flow).
    *   **Key Parameters:**
        *   `output_file`: (string, required) File path for saving visualization
        *   `chart_type`: (string) Type of chart ('sankey', 'bar', 'flow', 'json') (default: 'json')
        *   `show_statistics`: (boolean) Include detailed statistics (default: true)
        *   `save_to_context`: (string) Context key to save visualization data (optional)
    *   **Example YAML Usage:**
        ```yaml
        action:
          type: "VISUALIZE_MAPPING_FLOW"
          output_file: "${OUTPUT_DIR}/ukbb_to_hpa_flow.json"
          chart_type: "sankey"
          show_statistics: true
        ```

## Planned Action Types

As the system evolves, we anticipate adding:

### TRANSFORM_IDENTIFIERS
**Purpose**: Apply transformations like uppercase, lowercase, prefix/suffix operations, regex replacements.

**Parameters**:
- `transformation_type`: "uppercase", "lowercase", "prefix", "suffix", "regex"
- `transformation_value`: Value to add/remove/replace (for prefix/suffix/regex)

**Example**:
```yaml
action:
  type: "TRANSFORM_IDENTIFIERS"
  transformation_type: "prefix"
  transformation_value: "CHEMBL"
```

### MERGE_IDENTIFIER_SETS
**Purpose**: Combine results from multiple parallel paths or previous steps.

**Parameters**:
- `merge_strategy`: "union", "intersection", "difference"
- `source_sets`: List of previous step IDs to merge

**Example**:
```yaml
action:
  type: "MERGE_IDENTIFIER_SETS"
  merge_strategy: "union"
  source_sets: ["S2_PATH_A", "S2_PATH_B"]
```

### VALIDATE_IDENTIFIERS
**Purpose**: Check identifier format and validity, filtering out invalid ones.

**Parameters**:
- `validation_type`: "regex", "checksum", "api_verify"
- `validation_pattern`: Pattern or rules for validation
- `on_invalid`: "remove", "flag", "fail"

**Example**:
```yaml
action:
  type: "VALIDATE_IDENTIFIERS"
  validation_type: "regex"
  validation_pattern: "^[A-Z][0-9]{5}$"
  on_invalid: "remove"
```

### ENRICH_WITH_METADATA
**Purpose**: Add metadata from external sources without changing identifiers.

**Parameters**:
- `metadata_source`: Source of metadata (endpoint name or API)
- `metadata_fields`: List of fields to retrieve
- `join_on`: Ontology type to use for joining

**Example**:
```yaml
action:
  type: "ENRICH_WITH_METADATA"
  metadata_source: "uniprot_api"
  metadata_fields: ["protein_name", "organism", "length"]
  join_on: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### SPLIT_COMPOSITE_IDENTIFIERS
**Purpose**: Handle composite identifiers like "Q14213_Q8NEV9" by splitting them.

**Parameters**:
- `delimiter`: Character(s) that separate the parts
- `keep_original`: Whether to keep the composite ID alongside split ones

**Example**:
```yaml
action:
  type: "SPLIT_COMPOSITE_IDENTIFIERS"
  delimiter: "_"
  keep_original: false
```

### RESOLVE_DEPRECATED_IDENTIFIERS
**Purpose**: Update obsolete/deprecated identifiers to current versions.

**Parameters**:
- `resolver_service`: Which service to use (e.g., "uniprot_history", "ncbi_gene_history")
- `include_secondary`: Whether to include secondary/alternative IDs

**Example**:
```yaml
action:
  type: "RESOLVE_DEPRECATED_IDENTIFIERS"
  resolver_service: "uniprot_history"
  include_secondary: true
```

### DEDUPLICATE_IDENTIFIERS
**Purpose**: Remove duplicate identifiers, with options for handling associated data.

**Parameters**:
- `dedup_strategy`: "keep_first", "keep_last", "merge_metadata"
- `case_sensitive`: Whether to consider case in deduplication

**Example**:
```yaml
action:
  type: "DEDUPLICATE_IDENTIFIERS"
  dedup_strategy: "keep_first"
  case_sensitive: false
```

### BATCH_API_LOOKUP
**Purpose**: Efficiently query external APIs with batching and rate limiting.

**Parameters**:
- `api_endpoint`: API service to query
- `batch_size`: Number of identifiers per request
- `rate_limit`: Requests per second
- `retry_strategy`: How to handle failures

**Example**:
```yaml
action:
  type: "BATCH_API_LOOKUP"
  api_endpoint: "pubchem_compound_lookup"
  batch_size: 100
  rate_limit: 5
  retry_strategy: "exponential_backoff"
```

---

## Creating New Action Types

To add a new action type:

1.  **Design the Action:**
    *   Define its purpose, required parameters, and how it will interact with the execution context.
    *   Document these aspects (e.g., by adding an entry to this reference file under a "Planned" or new section if it's a significant, reusable action).

2.  **Implement the Action Class:**
    *   Create a new Python module in the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/` directory (e.g., `my_new_action.py`).
    *   Inside this module, define a class (e.g., `MyNewAction`) that inherits from `biomapper.core.strategy_actions.base_action.BaseStrategyAction`.
    *   Implement the `__init__(self, params: dict, executor: 'MappingExecutor')` method to store and validate parameters received from the YAML configuration.
    *   Implement the `async execute(self, context: dict) -> dict` method to perform the action's logic, modifying and returning the context.
    *   Refer to `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/CLAUDE.md` for detailed guidelines on action implementation.

3.  **Make the Action Discoverable:**
    *   Add your new action class to the `__all__` list in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/__init__.py`. This allows the `MappingExecutor` to dynamically import it when specified via `action_class_path` in a YAML strategy.
    *   Example in `__init__.py`:
        ```python
        from .my_new_action import MyNewAction
        __all__ = [
            # ... other actions
            "MyNewAction",
        ]
        ```

4.  **Configure in YAML Strategy:**
    *   In your `mapping_strategies_config.yaml` (or other relevant YAML configuration), use the `action_class_path` to specify your new action:
        ```yaml
        steps:
          - step_id: "S1_DO_NEW_THING"
            description: "Perform my new custom action"
            action:
              action_class_path: "biomapper.core.strategy_actions.my_new_action.MyNewAction"
              params:
                my_param: "value"
                # ... other parameters your action expects
        ```
    *   If the action is very common and core, a simple `type: "MY_NEW_ACTION_ALIAS"` might be configured in `MappingExecutor` to map to the class, but `action_class_path` is the standard for custom actions.

5.  **Update JSON Schema (if using type aliases):**
    *   If you introduce a new simple `type` alias (not `action_class_path`), add this type to the relevant JSON schema enum for validation purposes.

6.  **Create Unit Tests:**
    *   Write comprehensive unit tests for your new action class in the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/unit/core/strategy_actions/` directory.

7.  **Document in this Reference:**
    *   Once stable, add/move the action's documentation to the "Implemented Action Types" section of this file, detailing its `action_class_path`, purpose, parameters, and an example.

8.  **Update Example Strategies:**
    *   If applicable, update or create example strategies to demonstrate the usage of the new action.

---

## Best Practices

1. **Keep actions atomic** - Each action should do one thing well
2. **Use descriptive names** - Action types should clearly indicate their purpose
3. **Document parameters** - All parameters should be clearly documented
4. **Provide examples** - Include real-world usage examples
5. **Consider reusability** - Design actions to work across different entity types

---

## Cross-Entity Considerations

Some action types are generic enough to work across entity types:
- CONVERT_IDENTIFIERS_LOCAL
- EXECUTE_MAPPING_PATH
- FILTER_IDENTIFIERS_BY_TARGET_PRESENCE

Others might be entity-specific:
- RESOLVE_CHEMICAL_STRUCTURE (for metabolites)
- NORMALIZE_CLINICAL_UNITS (for clinical labs)

This suggests that core action types should remain entity-agnostic where possible.