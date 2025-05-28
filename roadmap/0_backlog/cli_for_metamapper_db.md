# Feature Idea: CLI for metamapper.db Interaction

## Parent Idea
-   Relates to: MEMORY[140ad7b0-e133-4771-a738-07e4b4926be6] (item 4: "CLI for `metamapper.db`")
-   Complements: `generalized_metamapper_db_implementation.md`

## Overview
Develop a command-line interface (CLI) tool that allows users and other scripts to dynamically query and retrieve metadata from the `metamapper.db`. This metadata would be used to configure and drive mapping pipelines, such as those executed by `MappingExecutor`.

## Problem Statement
Currently, configuring mapping pipelines might involve hardcoding endpoint names, property details, or mapping path identifiers within scripts. A CLI to `metamapper.db` would provide a dynamic and flexible way to fetch these configurations, reducing hardcoding, improving maintainability, and enabling more adaptable mapping workflows. It would allow pipeline configurations to be driven directly by the contents of the `metamapper.db`.

## Key Requirements
-   Ability to list available endpoints, mapping resources, and mapping paths.
-   Ability to retrieve detailed configuration for a specific endpoint (e.g., connection details, primary property).
-   Ability to retrieve detailed configuration for a specific mapping resource.
-   Ability to retrieve the definition of a specific mapping path (e.g., source/target endpoints, intermediate steps).
-   Output formats suitable for scripting (e.g., JSON, YAML).
-   User-friendly command structure and help messages.
-   Integration with the existing `metamapper.db` schema and data.

## Potential Benefits
-   Decouples mapping script logic from specific configurations.
-   Facilitates dynamic pipeline construction.
-   Simplifies the process of using new or updated resources defined in `metamapper.db`.
-   Improves script reusability and maintainability.
-   Provides a convenient way for users to inspect the contents and capabilities defined in `metamapper.db`.

## Dependencies
-   A stable and well-defined `metamapper.db` schema (as per `generalized_metamapper_db_implementation.md` or current state).
-   Core database interaction logic (potentially leveraging existing SQLAlchemy models).

## Success Criteria
-   CLI can successfully retrieve all necessary metadata for configuring a `MappingExecutor` run.
-   Output is easily parsable by scripts.
-   CLI commands are intuitive and well-documented.
-   The CLI reliably reflects the current state of `metamapper.db`.
