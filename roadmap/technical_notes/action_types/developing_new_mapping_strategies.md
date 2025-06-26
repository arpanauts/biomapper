# Developing New Mapping Strategies

This guide provides a comprehensive overview of how to create new mapping strategies in Biomapper using YAML. Mapping strategies are the core of Biomapper's workflow orchestration, defining a series of actions to be executed to transform, map, and analyze biological data.

## 1. Introduction to Mapping Strategies

A mapping strategy is a declarative workflow defined in a YAML file. It specifies a sequence of steps, where each step invokes a specific `StrategyAction` to perform a task. Strategies are designed to be modular, reusable, and easy to understand.

They orchestrate the flow of data through various actions, managing a shared `ActionContext` that allows steps to communicate and share results.

## 2. Anatomy of a Strategy YAML File

A strategy YAML file has the following top-level structure:

```yaml
name: UNIQUE_STRATEGY_NAME
version: "1.0.0"
description: "A brief but clear description of what this strategy accomplishes."
author: "Your Name"
requirements:
  - biomapper_version: ">=0.1.0"
  - specific_package: "==1.2.3" # Optional package requirements
context:
  # Initial context values required to run the strategy
  initial_inputs:
    - name: input_data_key
      description: "Description of this input."
      required: true
      type: "list[str]" # Expected data type
steps:
  # A list of action steps to execute in sequence
  - ...
```

### Key Fields:

-   `name`: A unique identifier for the strategy. This is used to retrieve and execute the strategy via the API.
-   `version`: The version of the strategy, following semantic versioning.
-   `description`: A human-readable summary of the strategy's purpose.
-   `author`: The author of the strategy.
-   `requirements`: (Optional) A list of dependencies required for the strategy to run, such as a minimum Biomapper version or other Python packages.
-   `context`: Defines the initial data required by the strategy.
    -   `initial_inputs`: A list of required input keys that must be present in the `ActionContext` when the strategy execution begins. Each input has a `name`, `description`, `required` flag, and expected `type`.
-   `steps`: A list of dictionaries, where each dictionary defines a single step in the workflow.

## 3. Defining Strategy Steps

Each step in the `steps` list defines an action to be executed. It has the following structure:

```yaml
steps:
  - name: descriptive_step_name
    action: ActionClassName
    description: "What this step does."
    parameters:
      # Action-specific parameters
      param_1: value_1
      param_2: "value_2"
    on_error: "fail" # or "continue"
    optional: false
```

### Step Fields:

-   `name`: A unique, descriptive name for the step within the strategy.
-   `action`: The class name of the `StrategyAction` to execute (e.g., `LocalIdConverter`, `ApiResolver`).
-   `description`: A brief explanation of the step's purpose.
-   `parameters`: A dictionary of parameters passed to the action's `execute` method. These are specific to each action. You can use context variables here.
-   `on_error`: (Optional, default: `fail`) Defines the behavior if the action raises an error.
    -   `fail`: The strategy execution stops immediately.
    -   `continue`: The strategy logs the error and proceeds to the next step.
-   `optional`: (Optional, default: `false`) If `true`, this step can be skipped if its required input parameters are not available in the context.

## 4. Data Flow and the Action Context

The `ActionContext` is a Python dictionary that is passed through the entire sequence of steps. It acts as a shared state, allowing actions to pass data to subsequent actions.

### Using Context Variables

You can reference values from the `ActionContext` in your step parameters using a special syntax: `${context.key_name}`.

**Example:**

An action might place a list of identifiers in the context under the key `uniprot_ids`. A subsequent action can then use these identifiers:

```yaml
steps:
  - name: get_initial_ids
    action: LoadFromFileAction
    parameters:
      filepath: "/path/to/data.csv"
      output_context_key: "initial_ids"

  - name: convert_ids
    action: LocalIdConverter
    parameters:
      input_identifiers: "${context.initial_ids}"
      output_context_key: "converted_ids"
```

In this example, `LoadFromFileAction` reads data and saves it to `context['initial_ids']`. The `LocalIdConverter` then accesses this data using `${context.initial_ids}`.

## 5. Example Strategy: UKBB-HPA Protein Overlap

Here is a simplified version of a strategy that finds overlapping proteins between UKBB and HPA datasets.

```yaml
name: UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS
version: "1.0.0"
description: "Identifies overlapping proteins between UKBB and HPA datasets."
author: "Biomapper Team"

context:
  initial_inputs:
    - name: ukbb_protein_ids
      description: "A list of protein identifiers from the UKBB dataset."
      required: true
      type: "list[str]"
    - name: hpa_protein_ids
      description: "A list of protein identifiers from the HPA dataset."
      required: true
      type: "list[str]"

steps:
  - name: find_common_proteins
    action: BidirectionalMatchAction
    description: "Finds common identifiers between the two protein lists."
    parameters:
      endpoint1_identifiers: "${context.ukbb_protein_ids}"
      endpoint2_identifiers: "${context.hpa_protein_ids}"
      match_type: "intersection"
      output_context_key: "overlapping_proteins"

  - name: generate_summary_report
    action: GenerateMappingSummaryAction
    description: "Generates a summary of the overlap results."
    parameters:
      input_data: "${context.overlapping_proteins}"
      output_format: "console"
```

## 6. Best Practices

-   **Modularity:** Keep strategies focused on a single, well-defined goal. For complex workflows, consider breaking them into smaller, chainable strategies.
-   **Clear Naming:** Use descriptive names for strategies, steps, and context keys. This makes the workflow easier to understand and debug.
-   **Documentation:** Write clear descriptions for the strategy and each step. Document the expected inputs and outputs in the `context` section.
-   **Error Handling:** Use `on_error` and `optional` fields judiciously to create robust and resilient workflows.
-   **Versioning:** Increment the strategy version when you make significant changes to its logic or parameters.

By following these guidelines, you can create powerful, flexible, and maintainable mapping strategies to drive your data analysis pipelines in Biomapper.
