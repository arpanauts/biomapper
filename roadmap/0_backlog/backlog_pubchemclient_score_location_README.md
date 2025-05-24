# Backlog: PubChemRAGMappingClient - Configurable Score Return Location

## 1. Overview

The `PubChemRAGMappingClient` currently ensures backward compatibility by returning the best Qdrant similarity score as a string within the `component_id` field of its primary `map_identifiers` method's return tuple. While this is great for existing integrations, new integrations might prefer accessing the score more directly or as a numeric type without parsing.

This task is to add a configuration option to the `PubChemRAGMappingClient` to allow users to choose how the primary score is returned:
    a. Embedded in `component_id` (current default, backward compatible).
    b. In a new, dedicated field within the primary return structure (e.g., as an additional element in the tuple, or by modifying the tuple's structure if deemed appropriate).

## 2. Goal

*   Provide flexibility for client users regarding how they access the primary Qdrant similarity score.
*   Maintain backward compatibility by default.
*   Clearly document the new configuration option and its effects.

## 3. Scope

*   Modify `PubChemRAGMappingClient` to include a new configuration parameter (e.g., during initialization or as a method parameter).
*   Adjust the `map_identifiers` method to alter its return behavior based on this configuration.
*   Update all relevant unit tests, integration tests, and documentation (including docstrings and the example script).

## 4. Potential Considerations

*   Impact on the existing return type `Dict[str, Tuple[Optional[List[str]], Optional[str]]]`. If a new field is added to the tuple, its type needs careful consideration.
*   Clarity of the configuration option and its naming.
