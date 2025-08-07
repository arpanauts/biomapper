# Biomapper API Complete Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [API Architecture](#api-architecture)
3. [Available Endpoints](#available-endpoints)
4. [Strategy Execution](#strategy-execution)
5. [Working Examples](#working-examples)
6. [Current Limitations](#current-limitations)
7. [Troubleshooting](#troubleshooting)
8. [Development Guide](#development-guide)

---

## Quick Start

### Starting the API Server

```bash
# Navigate to the API directory
cd /home/ubuntu/biomapper/biomapper-api

# Start the server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative if port 8000 is busy
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Basic Health Check

```bash
# Check if API is running
curl http://localhost:8000/api/health/

# Expected response:
# {"status":"healthy","version":"0.1.0"}
```

### Python Client Usage

```python
from biomapper_client.client_v2 import BiomapperClient

async with BiomapperClient() as client:
    # Check health
    health = await client.health_check()
    print(health)
```

---

## API Architecture

### System Flow

```
Client Request
    ↓
FastAPI Server (port 8000)
    ↓
/api/strategies/v2/execute endpoint
    ↓
MinimalStrategyService
    ↓
Load YAML from configs/strategies/
    ↓
ACTION_REGISTRY (self-registered actions)
    ↓
Execute actions sequentially
    ↓
Return accumulated context
```

### Key Components

1. **FastAPI Server** (`biomapper-api/app/main.py`)
   - Hosts REST endpoints
   - Routes requests to appropriate handlers
   - Currently uses in-memory job storage

2. **MinimalStrategyService** (`biomapper/core/minimal_strategy_service.py`)
   - Loads YAML strategies from disk
   - Orchestrates action execution
   - Manages execution context

3. **Action Registry** (`biomapper/core/strategy_actions/registry.py`)
   - Actions self-register via `@register_action` decorator
   - Maps action types to implementation classes
   - Dynamically loaded at runtime

4. **Execution Context**
   - Shared dictionary passed between actions
   - Accumulates results from each action
   - Contains: `datasets`, `statistics`, `output_files`, `current_identifiers`

---

## Available Endpoints

### Core V2 Endpoints (Recommended)

#### 1. Execute Strategy
```http
POST /api/strategies/v2/execute
Content-Type: application/json

{
    "strategy": "STRATEGY_NAME",
    "parameters": {},
    "options": {}
}
```

**Response:**
```json
{
    "job_id": "uuid-string",
    "status": "running",
    "message": "Strategy 'STRATEGY_NAME' execution started"
}
```

#### 2. Check Job Status
```http
GET /api/strategies/v2/jobs/{job_id}/status
```

**Response:**
```json
{
    "job_id": "uuid-string",
    "status": "running|completed|failed",
    "strategy_name": "STRATEGY_NAME",
    "error": "error message if failed"
}
```

#### 3. Get Job Results
```http
GET /api/strategies/v2/jobs/{job_id}/results
```

**Response:**
```json
{
    "datasets": {
        "dataset_key": { "identifiers": [...], "metadata": {...} }
    },
    "statistics": {
        "metric_name": value
    },
    "output_files": ["path/to/file1.tsv"],
    "current_identifiers": [...]
}
```

### Other Endpoints

#### Health Check
```http
GET /api/health/
```

#### OpenAPI Documentation
```http
GET /api/docs
GET /api/openapi.json
```

---

## Strategy Execution

### Available Strategies

Located in `/home/ubuntu/biomapper/configs/strategies/`:

#### Working Strategies
- **SIMPLE_DATA_LOADER_DEMO** - Loads and merges datasets (fully working)

#### Partially Working Strategies
- **THREE_WAY_METABOLOMICS_COMPLETE** - Loads data successfully, fails at NIGHTINGALE_NMR_MATCH
- **METABOLOMICS_PROGRESSIVE_ENHANCEMENT** - Similar issues with Pydantic validation

#### Not Working (Missing Actions)
- **ARIVALE_TO_KG2C_PROTEINS** - Uses unimplemented CUSTOM_TRANSFORM, FILTER_DATASET
- **UKBB_TO_KG2C_PROTEINS** - Same missing actions

### Implemented Action Types

✅ **Working Actions:**
- `LOAD_DATASET_IDENTIFIERS` - Load data from TSV/CSV files
- `MERGE_DATASETS` - Combine multiple datasets
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map to UniProt (needs testing)
- `CALCULATE_SET_OVERLAP` - Calculate Jaccard similarity

❌ **Actions with Issues:**
- `NIGHTINGALE_NMR_MATCH` - Pydantic validation errors
- `CTS_ENRICHED_MATCH` - Pydantic validation errors
- Other metabolomics actions - Similar validation issues

❌ **Unimplemented Actions:**
- `CUSTOM_TRANSFORM` - Data transformation
- `FILTER_DATASET` - Filter results
- `EXPORT_DATASET` - Export to files
- `GENERATE_REPORT` - Create reports

---

## Working Examples

### Example 1: Simple Data Loading (Works!)

```python
import httpx
import asyncio
import json

async def load_data():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Submit job
        response = await client.post(
            "/api/strategies/v2/execute",
            json={
                "strategy": "SIMPLE_DATA_LOADER_DEMO",
                "parameters": {},
                "options": {}
            }
        )
        
        if response.status_code == 200:
            job_id = response.json()["job_id"]
            print(f"Job created: {job_id}")
            
            # Wait for completion
            await asyncio.sleep(3)
            
            # Check status
            status_response = await client.get(
                f"/api/strategies/v2/jobs/{job_id}/status"
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"Status: {status['status']}")
                
                if status['status'] == 'completed':
                    # Get results
                    results_response = await client.get(
                        f"/api/strategies/v2/jobs/{job_id}/results"
                    )
                    results = results_response.json()
                    print(f"Loaded datasets: {list(results.get('datasets', {}).keys())}")

# Run it
await load_data()
```

### Example 2: Using cURL

```bash
# Submit a strategy
curl -X POST http://localhost:8000/api/strategies/v2/execute \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "SIMPLE_DATA_LOADER_DEMO",
    "parameters": {},
    "options": {}
  }'

# Response: {"job_id":"abc-123","status":"running","message":"..."}

# Check status
curl http://localhost:8000/api/strategies/v2/jobs/abc-123/status

# Get results (when completed)
curl http://localhost:8000/api/strategies/v2/jobs/abc-123/results
```

### Example 3: Custom Strategy YAML

Create `/home/ubuntu/biomapper/configs/strategies/my_strategy.yaml`:

```yaml
name: MY_CUSTOM_STRATEGY
description: "Load a single dataset"
parameters:
  data_file: "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv"

steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_file}"
        identifier_column: "Description"
        output_key: "my_data"
        drop_empty: true
```

Then execute it:

```python
response = await client.post(
    "/api/strategies/v2/execute",
    json={"strategy": "MY_CUSTOM_STRATEGY", "parameters": {}, "options": {}}
)
```

---

## Current Limitations

### 1. In-Memory Job Storage
- Jobs are lost when API restarts
- No persistence between sessions
- Solution: Use database-backed `/api/jobs` endpoints (not fully implemented)

### 2. Pydantic Validation Issues
**Problem:** Actions expect `StrategyExecutionContext` with specific fields
```
Field required: provenance.source
Field required: provenance.timestamp
```

**Affected Actions:**
- NIGHTINGALE_NMR_MATCH
- CTS_ENRICHED_MATCH
- Most metabolomics-specific actions

**Root Cause:** Actions use strict Pydantic models incompatible with minimal context

### 3. Missing Action Implementations
**Protein strategies need:**
- CUSTOM_TRANSFORM
- FILTER_DATASET
- EXPORT_DATASET
- GENERATE_REPORT

### 4. BiomapperClient Issues
- Datetime validation errors (requires kernel restart after fixes)
- Some methods not fully implemented
- Workaround: Use direct HTTP requests with httpx

---

## Troubleshooting

### Issue: "Job not found" Error

**Cause:** API restarted, in-memory jobs lost

**Solution:**
```python
# Create a fresh job each time
response = await client.post("/api/strategies/v2/execute", ...)
job_id = response.json()["job_id"]
# Use this new job_id immediately
```

### Issue: Datetime Validation Errors

**Cause:** BiomapperClient expects datetime objects but gets empty strings

**Solution:**
1. Restart Jupyter kernel after client fixes
2. Or use direct HTTP requests:

```python
import httpx
async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    response = await client.post("/api/strategies/v2/execute", ...)
```

### Issue: Port 8000 Already in Use

**Solution:**
```bash
# Find and kill the process
ps aux | grep uvicorn
kill -9 [PID]

# Or use a different port
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Issue: Strategy Fails with Validation Error

**Temporary Workaround:** Use only these actions:
- LOAD_DATASET_IDENTIFIERS
- MERGE_DATASETS

**Long-term Solution:** Fix action implementations to handle minimal context

### Issue: Old Endpoint Returns Wrong Fields

**Cause:** Old `/api/strategies` endpoint expects obsolete fields

**Solution:** Always use v2 endpoint: `/api/strategies/v2/execute`

---

## Development Guide

### Adding a New Strategy

1. Create YAML file in `/home/ubuntu/biomapper/configs/strategies/`
2. Use only implemented actions
3. No restart needed - API loads on request

### Adding a New Action

1. Create action class in `biomapper/core/strategy_actions/`
2. Use the decorator: `@register_action("ACTION_NAME")`
3. Inherit from `TypedStrategyAction` for type safety
4. Handle minimal execution context (don't require strict Pydantic models)

Example:
```python
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction):
    async def execute_typed(self, params, context):
        # Your implementation
        context['datasets']['my_result'] = processed_data
        return context
```

### Testing Strategies

1. **Check YAML syntax:**
```bash
python3 -c "import yaml; yaml.safe_load(open('my_strategy.yaml'))"
```

2. **Test with simple data first:**
```yaml
steps:
  - name: test_load
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/path/to/small/test/file.tsv"
        identifier_column: "id"
        output_key: "test_data"
```

3. **Check API logs:**
```bash
# API logs show detailed execution info
# Look for successful data loading messages
```

### Debugging Tips

1. **Enable debug mode in strategy:**
```json
{
    "strategy": "MY_STRATEGY",
    "parameters": {},
    "options": {"debug_mode": true}
}
```

2. **Check execution context:**
- The entire context is returned in results
- Look at intermediate datasets
- Check statistics for counts

3. **API logs show:**
- Which actions execute
- How many rows load
- Where failures occur
- Full error messages

---

## Summary

### ✅ What Works
- V2 API endpoint structure
- Job submission and tracking
- YAML strategy loading
- Basic data loading (LOAD_DATASET_IDENTIFIERS)
- Dataset merging (MERGE_DATASETS)

### 🚧 What Needs Work
- Fix Pydantic validation in metabolomics actions
- Implement missing actions for protein strategies
- Add persistent job storage
- Complete BiomapperClient implementation

### 📝 Next Steps
1. Fix action implementations to work with minimal context
2. Implement missing action types
3. Add database persistence for jobs
4. Create more working example strategies

---

## Quick Reference

### Essential URLs
- API Docs: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/api/health/
- OpenAPI Spec: http://localhost:8000/api/openapi.json

### Key File Locations
- Strategies: `/home/ubuntu/biomapper/configs/strategies/`
- Actions: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- API Routes: `/home/ubuntu/biomapper/biomapper-api/app/api/routes/`
- Client: `/home/ubuntu/biomapper/biomapper_client/`

### Working Strategy Names
- `SIMPLE_DATA_LOADER_DEMO` - Fully functional demo
- Custom strategies using only LOAD_DATASET_IDENTIFIERS and MERGE_DATASETS

### Contact & Support
- Check API logs for detailed error messages
- Review this guide for common issues
- Create test strategies with minimal actions first

---

*Last Updated: August 2025*
*Version: 1.0.0*