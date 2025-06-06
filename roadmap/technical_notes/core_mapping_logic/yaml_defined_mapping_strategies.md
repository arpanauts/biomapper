# YAML-Defined Mapping Strategies in Biomapper

## 1. Introduction & Rationale

*   **Purpose:** This document outlines the approach for defining explicit, multi-step mapping strategies within Biomapper using YAML configuration. This method allows for precise control over the mapping pipeline, enhances reproducibility, and provides flexibility for integrating diverse datasets with unique mapping requirements.
*   **Motivation:**
    *   **Explicit Control:** Provides clear, human-readable definitions of mapping sequences, especially for complex scenarios that go beyond default iterative logic.
    *   **Reproducibility:** Ensures that a given mapping task always follows the same sequence of operations.
    *   **Extensibility for Unique Needs:** Caters to the reality that different entity types (e.g., proteins, metabolites, questionnaire data) or specific dataset pairs may require bespoke mapping pipelines.
    *   **Minimizing Core Logic Risk:** Allows for the definition of custom pipelines without requiring extensive modifications to the `MappingExecutor`'s core iterative discovery logic for each new scenario.
*   **Complementation of Existing Logic:** This approach complements the `MappingExecutor`'s existing iterative capabilities. YAML-defined strategies can be used for specific, well-understood pipelines, while the iterative logic might still serve for simpler cases or discovery-oriented tasks.

## 2. Core Concept: The `mapping_strategies` YAML Section

*   **Location and Context:** The `mapping_strategies` section is a key part of the comprehensive `*_config.yaml` files (e.g., `protein_config.yaml`). These YAML files also define other critical entities such as `ontologies`, `databases` (Endpoints), `additional_resources` (MappingResources), and importantly, `mapping_paths`. All these definitions are parsed by a script (e.g., `scripts/populate_metamapper_db.py`) and loaded into the `metamapper.db` database, making them available at runtime.
*   **Structure:**
    *   A top-level `mapping_strategies` key.
    *   Under this, each key is a unique `strategy_name` (e.g., `HPA_TO_UKBB_PROTEIN_RESOLVED`).
    *   Each strategy contains:
        *   `description` (String): Human-readable explanation.
        *   `default_source_ontology_type` (String, Optional): The expected input ID type for the strategy's first step if not overridden in the `execute_mapping` call.
        *   `default_target_ontology_type` (String, Optional): The final output ID type for the strategy's last step if not overridden.
        *   `mapping_strategy_steps` (List): An ordered sequence of operations.
            *   Each step is an object with:
                *   `step_name` (String): A descriptive name for the step (for logging, debugging).
                *   `action` (String): Specifies the kind of operation (e.g., `CONVERT_IDENTIFIERS_LOCAL`). This is a key from a predefined set of action types.
                *   `action_parameters` (Object): Parameters specific to the action type.
                *   `is_required` (Boolean, Optional): Whether the step must succeed for the strategy to continue. Defaults to `true`. When `false`, step failures are logged but execution continues.
*   **Data Flow:** The output (a list/set of identifiers, potentially with associated metadata) from `step N` automatically becomes the input for `step N+1`. The `MappingExecutor` manages these intermediate results.

## 3. `action.type` Primitives

*   **Concept:** Each `action.type` string is a command that instructs the `MappingExecutor` to execute a specific, modular piece of Python logic (an action handler).
*   **Initial Proposed Action Types:**
    *   **`CONVERT_IDENTIFIERS_LOCAL`**
        *   **Description:** Converts identifiers from one type to another using a local database table.
        *   **Action Parameters:**
            *   `source_column` (String): The column containing source identifiers.
            *   `target_column` (String): The column name for converted identifiers.
            *   `conversion_table` (String): The database table to use for conversion.
            *   `source_id_type` (String): The type of the source identifiers.
            *   `target_id_type` (String): The desired target identifier type.
    *   **`EXECUTE_MAPPING_PATH`**
        *   **Description:** Executes a `MappingPath` that is pre-defined in the `mapping_paths` section of a `*_config.yaml` file and has been loaded into the `metamapper.db`.
        *   **Functionality:** This action type allows a strategy to leverage complex, multi-step transformation routes as a single, reusable step. The `MappingExecutor` looks up the specified `MappingPath` by its name and entity type in the database and then executes its defined sequence of path steps.
        *   **Action Parameters:**
            *   `path_name` (String): The unique name of the `MappingPath` (as defined in the `mapping_paths` section of the YAML and loaded into the database) to execute.
            *   `source_column` (String, Optional): Override the default source column.
            *   `target_column` (String, Optional): Override the default target column.
    *   **`FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`**
        *   **Description:** Filters the dataset to only include rows where identifiers exist in the target resource.
        *   **Action Parameters:**
            *   `target_resource` (String): The target resource to check against.
            *   `identifier_column` (String): The column containing identifiers to check.
            *   `identifier_type` (String): The type of identifiers being checked.
*   **Adding New `action.type`s:**
    *   Define a new, unique `action.type` string.
    *   Implement a corresponding Python handler module/function (see Code Organization).
    *   Document the new action type, its parameters, and behavior.
*   **Code Organization for Action Handlers:**
    *   Handler logic for each `action.type` should reside in modular Python files, e.g., within a `biomapper/core/strategy_actions/` directory.
    *   Example: `biomapper/core/strategy_actions/local_converter_action.py`.

## 4. `MappingExecutor` Integration

*   The `MappingExecutor.execute_mapping(...)` method will be enhanced to accept an optional `strategy_name` parameter.
*   If `strategy_name` is provided:
    *   The `MappingExecutor` will load the specified strategy from the configuration.
    *   It will then iterate through the strategy's `steps`, dispatching to the appropriate internal action handler for each `action.type`.
    *   It will manage the flow of identifiers and associated metadata (e.g., provenance) between steps.
*   If `strategy_name` is not provided, the `MappingExecutor` may default to its existing iterative discovery logic or raise an error if a strategy is required for the given context.

## 5. Benefits & Use Cases

*   **Handling Multi-Step, Specific Mapping Pipelines:** Ideal for scenarios requiring a precise sequence of operations, such as the HPA-QIN-UKBB protein mapping involving UniProt API resolution.
*   **Supporting Diverse Entity Types:** Allows different entity types (proteins, metabolites, etc.) to have their own tailored mapping strategies defined in their respective configuration files without over-complicating a single, universal mapping logic.
*   **Experimentation and Refinement:** Facilitates trying different sequences of operations or alternative clients/paths by modifying the YAML strategy definition rather than Python code.
*   **Clarity and Maintainability:** Makes complex mapping logic explicit and easier to understand and maintain through declarative YAML.

## 6. Example Strategy (HPA to UKBB Protein Mapping)

```yaml
# In protein_config.yaml
mapping_strategies:
  hpa_to_ukbb_protein:
    mapping_strategy_steps:
      - step_name: "convert_hpa_to_uniprot"
        action: "CONVERT_IDENTIFIERS_LOCAL"
        action_parameters:
          source_column: "hpa_protein_id"
          target_column: "uniprot_ac"
          conversion_table: "hpa_uniprot_mapping"
          source_id_type: "HPA_PROTEIN_ID"
          target_id_type: "UniProt_AC"
        is_required: true

      - step_name: "resolve_uniprot_history"
        action: "EXECUTE_MAPPING_PATH"
        action_parameters:
          mapping_path: "uniprot_history_resolver"
          source_column: "uniprot_ac"
          target_column: "resolved_uniprot_ac"
        is_required: false  # Optional: Continue if API fails

      - step_name: "filter_by_ukbb_presence"
        action: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
        action_parameters:
          target_resource: "UKBB"
          identifier_column: "resolved_uniprot_ac"
          identifier_type: "UniProt_AC"
        is_required: false  # Optional: Allow partial results

      - step_name: "convert_to_ukbb_assay"
        action: "CONVERT_IDENTIFIERS_LOCAL"
        action_parameters:
          source_column: "resolved_uniprot_ac"
          target_column: "ukbb_assay_id"
          conversion_table: "ukbb_uniprot_to_assay"
          source_id_type: "UniProt_AC"
          target_id_type: "UKBB_ASSAY_ID"
        is_required: true
```

## 7. The `is_required` Field and Error Handling

*   **Purpose:** The `is_required` field provides fine-grained control over strategy execution flow in the presence of step failures.
*   **Behavior:**
    *   `is_required: true` (default): If the step fails, the entire strategy execution halts. Previous successful steps' results are preserved and returned.
    *   `is_required: false`: If the step fails, a warning is logged, but execution continues with the next step. This enables:
        *   **Optional enrichment steps** that enhance data when possible but aren't critical
        *   **Fallback mechanisms** where multiple approaches are tried in sequence
        *   **Partial result scenarios** where some mappings are better than none
*   **Use Cases:**
    *   **Critical conversions:** Set `is_required: true` for steps that convert between essential identifier types
    *   **API calls:** Set `is_required: false` for external API calls that might fail due to network issues
    *   **Filtering steps:** Often set `is_required: false` as filtering is typically an optimization
    *   **Alternative paths:** Use multiple optional steps to try different mapping approaches

## 8. Documentation and Management of Actions & Strategies

*   **Action Type Registry:** A central place (e.g., in documentation or a dedicated registry within the code) should list all available `action.type`s.
*   **Action Documentation:** Each `action.type` must be documented with:
    *   Its purpose.
    *   Required and optional YAML parameters.
    *   Expected input and output (identifier types, metadata structure).
*   **Strategy Documentation:** Complex or commonly used strategies should be documented, explaining their purpose and flow.
*   **Schema Validation:** Consider implementing JSON Schema validation for the `mapping_strategies` section in the YAML to catch structural errors early.

## 9. Relationship to Other Mapping Approaches

It's important to understand how YAML-Defined Mapping Strategies fit within the broader Biomapper mapping ecosystem, particularly in relation to the default iterative mapping strategy and the concept of bidirectional mapping with reconciliation.

*   **YAML-Defined Strategies vs. Default Iterative Strategy:**
    *   Both YAML-defined strategies and the default iterative strategy (the behavior of `MappingExecutor` when no explicit `strategy_name` is provided) are methods for achieving **unidirectional mapping** (i.e., mapping identifiers from a source endpoint to a target endpoint).
    *   **YAML-Defined Strategy:** Offers *explicit, fine-grained control*. The user defines the exact sequence of operations (actions) in the YAML. This is ideal for complex, well-understood pipelines or when specific intermediate steps (like an API call for historical ID resolution) are mandatory.
    *   **Default Iterative Strategy:** Provides a more *automated, discovery-oriented approach*. The `MappingExecutor` uses a built-in, prioritized logic to attempt various `mapping_paths` and conversion tactics to find mappings. This is suitable for simpler cases or when the exact mapping path is not known beforehand and the system should attempt to find one.
    *   **Usage:** Typically, for a given unidirectional mapping task (e.g., HPA proteins to UKBB proteins), you would choose to use either a YAML-defined strategy *or* rely on the default iterative strategy, not both simultaneously for the same single mapping execution.

*   **Role in Bidirectional Mapping and Reconciliation:**
    *   Bidirectional mapping aims to produce a high-confidence set of mappings by performing the mapping in both directions (e.g., Source -> Target and Target -> Source) and then reconciling the results.
    *   The **unidirectional mapping** steps required for bidirectional mapping can be powered by *either* YAML-defined strategies *or* the default iterative strategy.
        *   **Forward Mapping (Source -> Target):** Can use a YAML-defined strategy or the iterative strategy.
        *   **Reverse Mapping (Target -> Source):** Can also use a YAML-defined strategy (which might be different from the forward strategy) or the iterative strategy.
    *   **Reconciliation Phase:** This is a distinct process that occurs *after* both unidirectional mappings are complete. A separate reconciliation module takes the outputs of the forward and reverse mappings as input. It compares these two sets, identifies concordant and discordant pairs, and applies rules to produce a final, reconciled mapping set.
    *   In essence, YAML-defined strategies (and the iterative strategy) serve as engines that can generate the raw directional mapping data that is then fed into the subsequent reconciliation process.

By understanding these distinctions, users can choose the most appropriate method for their specific mapping tasks, leveraging explicit strategies for control and precision, the iterative approach for automated discovery, and bidirectional reconciliation for achieving the highest quality mapping results.

