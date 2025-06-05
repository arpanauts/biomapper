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

*   **Location:** Defined within the relevant `*_config.yaml` file (e.g., `protein_config.yaml`) or potentially a shared `strategies.yaml`.
*   **Structure:**
    *   A top-level `mapping_strategies` key.
    *   Under this, each key is a unique `strategy_name` (e.g., `HPA_TO_UKBB_PROTEIN_RESOLVED`).
    *   Each strategy contains:
        *   `description` (String): Human-readable explanation.
        *   `default_source_ontology_type` (String, Optional): The expected input ID type for the strategy's first step if not overridden in the `execute_mapping` call.
        *   `default_target_ontology_type` (String, Optional): The final output ID type for the strategy's last step if not overridden.
        *   `steps` (List): An ordered sequence of operations.
            *   Each step is an object with:
                *   `step_id` (String): A unique identifier for the step (for logging, debugging).
                *   `description` (String, Optional): Explanation of the step's purpose.
                *   `action` (Object): Defines the operation for this step.
                    *   `type` (String): Specifies the kind of operation (e.g., `CONVERT_IDENTIFIERS_LOCAL`). This is a key from a predefined set of action types.
                    *   Additional parameters specific to the `action.type`.
*   **Data Flow:** The output (a list/set of identifiers, potentially with associated metadata) from `step N` automatically becomes the input for `step N+1`. The `MappingExecutor` manages these intermediate results.

## 3. `action.type` Primitives

*   **Concept:** Each `action.type` string is a command that instructs the `MappingExecutor` to execute a specific, modular piece of Python logic (an action handler).
*   **Initial Proposed `action.type`s:**
    *   **`CONVERT_IDENTIFIERS_LOCAL`**
        *   **Description:** Converts identifiers from one ontology type to another using the local data and mappings defined within a single endpoint.
        *   **YAML Parameters:**
            *   `endpoint_context` (String: "SOURCE" or "TARGET"): Specifies whether to use the source or target endpoint passed to `execute_mapping`.
            *   `output_ontology_type` (String): The desired ontology type for the output identifiers.
            *   `input_ontology_type` (String, Optional): The ontology type of the input identifiers for this step. If omitted, it's inferred from the previous step's output or the strategy's `default_source_ontology_type`.
    *   **`EXECUTE_MAPPING_PATH`**
        *   **Description:** Executes a predefined atomic `mapping_path` (which typically involves a mapping client).
        *   **YAML Parameters:**
            *   `path_name` (String): The name of the `mapping_path` (defined in the `mapping_paths` section of the YAML) to execute.
    *   **`FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`**
        *   **Description:** Filters a list of identifiers, retaining only those that are present in a specified ontology type within the target endpoint's data.
        *   **YAML Parameters:**
            *   `endpoint_context` (String: must be "TARGET" or resolve to the target endpoint).
            *   `ontology_type_to_match` (String): The ontology type in the target endpoint against which the input identifiers will be checked.
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
  HPA_TO_UKBB_PROTEIN_RESOLVED:
    description: "Maps HPA OSP proteins to UKBB proteins, including UniProt historical resolution, outputting UKBB native IDs."
    default_source_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
    default_target_ontology_type: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
    steps:
      - step_id: "S1_HPA_NATIVE_TO_UNIPROT"
        description: "Convert source HPA native IDs to their UniProt ACs."
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "SOURCE"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"

      - step_id: "S2_RESOLVE_UNIPROT_HISTORY"
        description: "Resolve UniProt ACs via UniProt API."
        action:
          type: "EXECUTE_MAPPING_PATH"
          path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"

      - step_id: "S3_MATCH_RESOLVED_UNIPROT_IN_UKBB"
        description: "Filter resolved UniProt ACs by presence in UKBB data."
        action:
          type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
          endpoint_context: "TARGET"
          ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"

      - step_id: "S4_UKBB_UNIPROT_TO_NATIVE"
        description: "Convert matching UKBB UniProt ACs to UKBB native Assay IDs."
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "TARGET"
          input_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY" # Explicitly stating input for clarity
          output_ontology_type: "{{STRATEGY_TARGET_ONTOLOGY_TYPE}}" # Uses strategy's default target
```

## 7. Documentation and Management of Actions & Strategies

*   **Action Type Registry:** A central place (e.g., in documentation or a dedicated registry within the code) should list all available `action.type`s.
*   **Action Documentation:** Each `action.type` must be documented with:
    *   Its purpose.
    *   Required and optional YAML parameters.
    *   Expected input and output (identifier types, metadata structure).
*   **Strategy Documentation:** Complex or commonly used strategies should be documented, explaining their purpose and flow.
*   **Schema Validation:** Consider implementing JSON Schema validation for the `mapping_strategies` section in the YAML to catch structural errors early.

## 8. Relationship to Other Mapping Approaches

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

