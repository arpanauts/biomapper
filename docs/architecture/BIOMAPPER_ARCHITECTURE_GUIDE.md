# Biomapper Architecture Guide for LLM Agents

## Overview

Biomapper is a service-oriented biological data harmonization toolkit that maps identifiers between different biological databases. This guide helps LLM agents understand the architecture and work effectively with the codebase.

## Core Architecture Principles

1. **Service-Oriented Architecture**: The system is split into modular services with clear responsibilities
2. **Configuration-Driven**: Mapping strategies are defined in YAML files, not hardcoded
3. **Action-Based Execution**: Complex mappings are broken down into reusable action steps
4. **Database-Backed**: Strategies, endpoints, and configurations are stored in SQLite databases

## Key Components

### 1. Mapping Strategies (YAML Configuration)
- **Location**: `/home/ubuntu/biomapper/configs/`
- **Purpose**: Define multi-step mapping workflows declaratively
- **Structure**:
  ```yaml
  name: STRATEGY_NAME
  description: "What this strategy does"
  steps:
    - name: STEP_NAME
      action:
        type: ACTION_TYPE  # Must match registered action
        params:
          key: value
  ```

### 2. Strategy Actions
- **Location**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- **Purpose**: Reusable building blocks for mapping operations
- **Key Actions**:
  - `LOCAL_ID_CONVERTER`: Maps IDs using local CSV/TSV files
  - `LOAD_ENDPOINT_IDENTIFIERS`: Loads all IDs from an endpoint
  - `DATASET_OVERLAP_ANALYZER`: Analyzes overlap between two datasets
  - `API_RESOLVER`: Resolves IDs using external APIs

### 3. Endpoints
- **Purpose**: Define data sources (files, APIs, databases)
- **Stored in**: SQLite database (`metamapper.db`)
- **Properties**:
  - `name`: Unique identifier
  - `type`: file/api/database
  - `connection_details`: JSON with file paths or API URLs
  - `primary_property_name`: Main identifier column

### 4. API Service Layer
- **Location**: `/home/ubuntu/biomapper/biomapper-api/`
- **Purpose**: RESTful API for executing strategies
- **Key Routes**:
  - `POST /api/strategies/{name}/execute`: Execute a mapping strategy
  - `GET /api/endpoints/`: List available endpoints

## Working with Strategy Actions

### Creating a New Action

1. **Create Action Class**:
   ```python
   # In biomapper/core/strategy_actions/your_action.py
   from biomapper.core.strategy_actions.base import BaseStrategyAction
   from biomapper.core.strategy_actions.registry import register_action

   @register_action("YOUR_ACTION_TYPE")
   class YourAction(BaseStrategyAction):
       async def execute(self, current_identifiers, current_ontology_type, 
                        action_params, source_endpoint, target_endpoint, context):
           # Implementation
           return {
               'output_identifiers': result_list,
               'output_ontology_type': result_type,
               'details': {...}
           }
   ```

2. **Use in Strategy YAML**:
   ```yaml
   - name: "Use Your Action"
     action:
       type: YOUR_ACTION_TYPE
       params:
         param1: value1
   ```

### Modifying Existing Actions

1. **Understand the Contract**:
   - Input: `current_identifiers`, `action_params`, `context`
   - Output: Must include `output_identifiers` and `output_ontology_type`
   - Context: Shared state across strategy steps

2. **Common Patterns**:
   - Use `context` to share data between steps
   - Access previous results via `context[key]`
   - Log operations for debugging
   - Handle errors gracefully

## Working with Strategies

### Strategy Development Workflow

1. **Design the Strategy**:
   - Identify source and target endpoints
   - Break down into logical steps
   - Determine which actions to use

2. **Create YAML Configuration**:
   ```yaml
   name: YOUR_STRATEGY
   description: "Maps X to Y using Z"
   steps:
     - name: "Load Source Data"
       action:
         type: LOAD_ENDPOINT_IDENTIFIERS
         params:
           endpoint_name: "SOURCE_ENDPOINT"
           output_context_key: "source_ids"
   ```

3. **Update Database**:
   ```bash
   # If strategy exists in DB, update it:
   poetry run python scripts/update_strategy.py
   ```

4. **Test the Strategy**:
   ```bash
   # Via API
   curl -X POST http://localhost:8000/api/strategies/YOUR_STRATEGY/execute \
        -H "Content-Type: application/json" \
        -d '{"source_endpoint_name": "X", "target_endpoint_name": "Y", 
             "input_identifiers": ["id1", "id2"]}'
   ```

## Best Practices for LLM Agents

### DO:
1. **Understand Context Flow**: Actions communicate via the `context` dictionary
2. **Check Parameter Names**: Action parameters must match exactly (e.g., `dataset1_context_key` not `input_context_key_1`)
3. **Validate Action Types**: Ensure action types are registered in the ACTION_REGISTRY
4. **Test Incrementally**: Test each step of a strategy independently
5. **Use Existing Patterns**: Look at working strategies for examples

### DON'T:
1. **Don't Hardcode Paths**: Use endpoints for file locations
2. **Don't Skip Registration**: All actions must be registered with `@register_action`
3. **Don't Ignore Context**: The context is essential for multi-step strategies
4. **Don't Mix Concerns**: Keep actions focused on one task

## Common Issues and Solutions

### Issue: "Unknown action type"
**Solution**: Ensure the action is registered and the type matches exactly

### Issue: "Parameter X is required"
**Solution**: Check the action's execute method for required parameters

### Issue: "No property configuration found"
**Solution**: Endpoints need property configurations linking to extraction configs

### Issue: Strategy validation errors
**Solution**: Check YAML syntax and ensure all required fields are present

## Debugging Tips

1. **Check Logs**:
   ```bash
   tail -f /tmp/api_server.log
   ```

2. **Verify Database State**:
   ```bash
   # Check strategies in DB
   sqlite3 /home/ubuntu/biomapper/data/metamapper.db \
     "SELECT name FROM mapping_strategies;"
   ```

3. **Test Actions Individually**:
   Create minimal strategies to test single actions

## Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐
│   YAML Config   │────▶│   API Service    │
│  (Strategies)   │     │ (FastAPI Server) │
└─────────────────┘     └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Strategy Executor   │
                    │ (Orchestrates Steps) │
                    └──────────────────────┘
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
           ┌─────────────────┐    ┌─────────────────┐
           │ Action Classes  │    │   Endpoints     │
           │ (Registered)    │    │ (DB + Configs) │
           └─────────────────┘    └─────────────────┘
```

## Quick Reference

- **Add new action**: Create class → Register with decorator → Use in YAML
- **Update strategy**: Edit YAML → Run update script → Restart API
- **Debug execution**: Check logs → Verify parameters → Test incrementally
- **Common parameters**: `output_context_key`, `input_context_key`, `endpoint_name`

Remember: The system is designed for extensibility through configuration, not code changes. When possible, create new strategies by combining existing actions rather than writing new code.