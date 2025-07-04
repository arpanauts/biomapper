# Biomapper Development Context Refresh

## Key Context Points
- Biomapper is a biological data harmonization toolkit
- Core components: biomapper/, biomapper-api/, biomapper_client/
- Uses Poetry for dependency management
- Strategy actions in biomapper/core/strategy_actions/
- YAML strategies in configs/strategies/
- Always use poetry commands (never pip directly)
- Follow strict type hints and MyPy settings
- Use async patterns for I/O operations