# Biomapper Tutorials

The main Biomapper tutorials can be found in the following sections:

## Getting Started
- [Getting Started Guide](../guides/getting_started.md) - Complete walkthrough of basic usage
- [First Mapping Tutorial](../guides/first_mapping.rst) - Step-by-step first example

## Foundational Actions

Biomapper currently ships with three foundational actions, with the architecture designed to support additional specialized actions:

- [LOAD_DATASET_IDENTIFIERS](../actions/load_dataset_identifiers.rst) - Load data from CSV/TSV files
- [MERGE_WITH_UNIPROT_RESOLUTION](../actions/merge_with_uniprot_resolution.rst) - Merge datasets with ID resolution
- [CALCULATE_SET_OVERLAP](../actions/calculate_set_overlap.rst) - Calculate overlap statistics and Venn diagrams

## Complete Examples

The repository includes working YAML strategy examples in the `configs/strategies/` directory:
- `UKBB_HPA_COMPARISON.yaml` - Complete protein dataset comparison workflow
- Other example strategies showing the foundational actions in use

## Extensible Architecture

The action-based architecture is designed for easy expansion. New actions can be added to support specialized mapping approaches as requirements evolve. See [Action System](../architecture/action_system.rst) for details on developing new actions.

## Next Steps

For comprehensive usage patterns and advanced configuration:
- [Configuration Guide](../configuration.rst)
- [Usage Guide](../usage.rst)
- [API Documentation](../api/)