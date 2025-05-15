# Feature Idea: Generalized Composite Identifier Handling

## Overview
Develop a systematic, configuration-driven approach to handling composite identifiers across all mapping clients, replacing the current client-specific implementations.

## Problem Statement
Current handling of composite identifiers (e.g., comma-separated values like "P29460,P29459") is implemented in client-specific ways, making the solution neither scalable nor easily maintainable as new entity types and mapping resources are added to the system.

## Key Requirements
- Standardized approach to detecting and processing composite identifiers
- Consistent handling of identifier splitting and re-joining
- Clear rules for prioritization when multiple identifiers exist
- Support for different composite formats (comma-separated, semicolon-separated, etc.)
- Integration with the mapping pipeline's metadata tracking

## Potential Approaches
- Configurable pre-processing within the `MappingExecutor` before identifiers reach clients
- Dedicated resolver resources in `metamapper.db` that act as intermediate steps in multi-hop paths
- Middleware/decorator patterns applied to client calls for transparent handling
- Registry of identifier patterns and corresponding handling rules

## Related Considerations
- Handling of outdated/secondary IDs (similar pattern to composite IDs)
- Version detection in identifiers (e.g., UniProt AC with version numbers)
- Normalization rules for different identifier types

## Success Criteria
- Elimination of redundant code across different mapping clients
- Consistent handling of composite identifiers across all entity types
- Configuration-driven approach that requires minimal code changes for new patterns
- Comprehensive test coverage for various composite identifier scenarios
- Improved traceability of identifier transformations in mapping metadata
