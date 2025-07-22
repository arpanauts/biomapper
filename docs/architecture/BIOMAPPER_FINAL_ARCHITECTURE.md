# Biomapper Final Architecture (v2.0)

## Overview

Biomapper v2.0 is a streamlined biological data harmonization toolkit that maps identifiers between different biological databases using YAML-defined strategies.

## Core Principles

1. **Configuration-Driven**: All mapping logic defined in YAML files
2. **Stateless Execution**: No database required for mappings
3. **Direct Data Access**: Load from files, call APIs directly
4. **Minimal Abstractions**: Simple, clear code path
5. **Fast & Scalable**: Process millions of identifiers efficiently

## Architecture Diagram

```
┌─────────────────┐
│  Python Script  │
│  or Notebook    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   Biomapper     │
│   REST API      │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ YAML Strategy   │────▶│ Strategy Actions │
│    Service      │     └──────────────────┘
└────────┬────────┘              │
         │                       ▼
         │              ┌────────────────────┐
         └─────────────▶│   Data Sources     │
                        ├─ Local CSV/TSV     │
                        ├─ UniProt API       │
                        └─ Other APIs        │
                        └────────────────────┘
```

## Component Structure

```
biomapper/
├── api/                      # FastAPI application
│   ├── main.py              # API entry point
│   ├── routes/              # API endpoints
│   └── services/            # Business logic
│       └── strategy_service.py
│
├── core/                    # Core functionality
│   ├── actions/            # Strategy action implementations
│   │   ├── base.py         # TypedStrategyAction base class
│   │   ├── load_dataset.py # Load data from files
│   │   ├── merge_uniprot.py # Merge with UniProt resolution
│   │   └── calculate_overlap.py # Calculate set overlaps
│   │
│   ├── clients/            # External API clients
│   │   └── uniprot.py      # UniProt historical resolver
│   │
│   └── models/             # Pydantic models
│       ├── strategy.py     # Strategy configuration
│       └── context.py      # Execution context
│
├── configs/                # YAML strategy definitions
│   ├── ukbb_hpa_mapping.yaml
│   ├── arivale_spoke_mapping.yaml
│   └── ...
│
└── client/                 # Python client library
    └── biomapper_client.py
```

## Key Components

### 1. YAML Strategy Service
```python
class YamlStrategyService:
    """Execute YAML-defined mapping strategies."""
    
    async def execute_strategy(
        self, 
        strategy_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a named strategy with given context."""
        strategy = self.load_strategy(strategy_name)
        
        for step in strategy.steps:
            action = self.get_action(step.action.type)
            result = await action.execute(
                params=step.action.params,
                context=context
            )
            context.update(result)
            
        return context
```

### 2. Strategy Actions
```python
class TypedStrategyAction[TParams, TResult](ABC):
    """Base class for type-safe strategy actions."""
    
    @abstractmethod
    async def execute_typed(
        self,
        params: TParams,
        context: ExecutionContext
    ) -> TResult:
        """Execute the action with typed parameters."""
        pass
```

### 3. YAML Strategy Format
```yaml
name: "UKBB_HPA_PROTEIN_MAPPING"
description: "Map UK Biobank proteins to Human Protein Atlas"

steps:
  - name: load_ukbb_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/ukbb/proteins.tsv"
        identifier_column: "UniProt"
        output_key: "ukbb_proteins"
        
  - name: load_hpa_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/hpa/proteins.csv"
        identifier_column: "uniprot"
        output_key: "hpa_proteins"
        
  - name: merge_datasets
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "ukbb_proteins"
        target_dataset_key: "hpa_proteins"
        output_key: "merged_data"
        
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        input_key: "merged_data"
        output_dir: "/results/UKBB_HPA"
```

## Data Flow

1. **Client Request**: Client sends strategy name and context
2. **Strategy Loading**: Service loads YAML strategy from file
3. **Step Execution**: Each step executed sequentially
4. **Action Processing**: Actions load data, call APIs, process results
5. **Context Updates**: Results stored in execution context
6. **Final Results**: Complete context returned to client

## Deployment

### Requirements
- Python 3.11+
- FastAPI
- Pandas
- httpx (for API calls)
- matplotlib (for visualizations)

### Configuration
```bash
# Environment variables
BIOMAPPER_STRATEGIES_DIR=/path/to/strategies
BIOMAPPER_DATA_DIR=/path/to/data
BIOMAPPER_RESULTS_DIR=/path/to/results
```

### Running
```bash
# Start API
uvicorn biomapper.api.main:app --host 0.0.0.0 --port 8000

# Use client
from biomapper_client import BiomapperClient

async with BiomapperClient() as client:
    result = await client.execute_strategy(
        strategy_name="UKBB_HPA_PROTEIN_MAPPING",
        context={}
    )
```

## Performance Characteristics

- **Small datasets (5K identifiers)**: ~7-8 minutes
- **Medium datasets (20K identifiers)**: ~25-30 minutes  
- **Large datasets (250K identifiers)**: ~2-3 hours
- **Memory usage**: Linear with dataset size
- **API rate limits**: Respects UniProt rate limits

## Future Enhancements

1. **Caching Layer**: Cache UniProt resolutions locally
2. **Parallel Execution**: Process steps in parallel when possible
3. **Progress Tracking**: WebSocket for real-time progress
4. **More Actions**: Add actions for other databases
5. **Validation**: Stronger input/output validation

## Migration from v1.0

1. **No Database**: Remove all database setup/configuration
2. **Direct Execution**: Use YAML strategies instead of database strategies
3. **Simplified API**: Single endpoint for strategy execution
4. **Same Results**: Output format unchanged

## Benefits

- **Simple**: Easy to understand and modify
- **Fast**: No database overhead
- **Flexible**: Add new mappings via YAML
- **Reliable**: Stateless execution
- **Scalable**: Process large datasets efficiently