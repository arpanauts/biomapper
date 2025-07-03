# Enhanced Mapping Executor (DEPRECATED)

> **⚠️ DEPRECATION NOTICE**: This document describes a proposed enhancement that was never fully integrated into the main MappingExecutor. The current MappingExecutor uses a different architecture based on the facade pattern with coordinator services. For current architecture documentation, see [mapping_executor_architecture.md](./mapping_executor_architecture.md).

## Historical Context

This document is preserved for historical reference. It describes an earlier proposal for enhancing the MappingExecutor with features like:

- Robust error handling with retry logic
- YAML strategy execution
- Checkpoint and resume functionality
- Execution state management

While these features exist in the current implementation, they were implemented differently than described here:

- **Error handling**: Implemented in the ExecutionCoordinatorService
- **YAML strategies**: Handled by StrategyCoordinatorService
- **Checkpointing**: Managed by CheckpointManager service
- **State management**: Handled by ExecutionSet and context flow

## Current Implementation

The current MappingExecutor follows a facade pattern where:

1. The MappingExecutor provides a simple public interface
2. All complexity is delegated to specialized coordinator services
3. Services are composed using dependency injection via MappingExecutorBuilder

For accurate documentation of the current system, please refer to:
- [Biomapper Architecture Guide](./mapping_executor_architecture.md)
- [Strategy Action Development](./strategy_action_development.md)
- [YAML Strategy Schema](./source/architecture/yaml_strategy_schema.md)

---

*The content below is the original proposal and does not reflect the current implementation.*

[Original content preserved below for reference...]