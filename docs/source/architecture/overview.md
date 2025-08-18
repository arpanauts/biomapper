# BioMapper Architecture

## Overview

BioMapper is a YAML-based workflow platform for biological data harmonization and ontology mapping. Built on a self-registering action system with 37+ specialized actions, it provides comprehensive workflows for mapping proteins, metabolites, chemistry data, and other biological entities.

The architecture follows a three-layer design (Client → API → Core) with type-safe actions, automatic validation, and extensibility through simple decorator-based registration.

## Core Components

### Self-Registering Action System
Actions automatically register at import time using the `@register_action` decorator, eliminating manual registration. The global `ACTION_REGISTRY` enables dynamic action lookup from YAML strategies.

### YAML Strategy System
Declarative workflow definition with variable substitution, metadata tracking, and parameter validation. Strategies execute sequentially with shared context between steps.

### Available Actions (37+)
Organized by biological entity type:

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS` - Generic CSV/TSV loader
- `MERGE_DATASETS` - Combine with deduplication
- `FILTER_DATASET` - Complex filtering
- `EXPORT_DATASET_V2` - Multi-format export
- `CUSTOM_TRANSFORM_EXPRESSION` - Dynamic transformations

**Protein Actions:**
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize UniProt IDs
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract from compound fields
- `PROTEIN_MULTI_BRIDGE` - Multi-source resolution
- `MERGE_WITH_UNIPROT_RESOLUTION` - Historical ID mapping

**Metabolite Actions:**
- `METABOLITE_CTS_BRIDGE` - Chemical Translation Service
- `NIGHTINGALE_NMR_MATCH` - Nightingale platform matching
- `SEMANTIC_METABOLITE_MATCH` - AI-powered matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity
- `METABOLITE_API_ENRICHMENT` - External API integration

**Chemistry Actions:**
- `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes
- `CHEMISTRY_FUZZY_TEST_MATCH` - Fuzzy clinical test matching
- `CHEMISTRY_VENDOR_HARMONIZATION` - Harmonize vendor codes

**Analysis & Reporting:**
- `CALCULATE_SET_OVERLAP` - Jaccard similarity with Venn diagrams
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset comparison
- `GENERATE_METABOLOMICS_REPORT` - Comprehensive reports

### REST API Layer
FastAPI service with:
- Strategy execution endpoints (`/api/strategies/v2/`)
- Job management with SQLite persistence
- Background processing with checkpointing
- Server-Sent Events for real-time progress
- OpenAPI documentation

### Python Client Library
`BiomapperClient` in `biomapper_client/client_v2.py` provides:
- Synchronous wrapper for async operations
- Automatic retry and error handling
- Progress streaming support
- Simple interface: `client.run("strategy_name")`

### Core Execution Engine
`MinimalStrategyService` in `biomapper/core/minimal_strategy_service.py`:
- Direct YAML loading from `src/biomapper/configs/strategies/`
- Sequential action execution with error handling
- Variable substitution (`${parameters.key}`, `${env.VAR}`)
- Shared execution context management
- No database dependencies

## Directory Structure

```
biomapper/
├── src/                            # Main source directory
│   ├── actions/                    # Self-registering actions
│   │   ├── entities/               # Entity-specific actions
│   │   │   ├── proteins/           # UniProt, Ensembl actions
│   │   │   ├── metabolites/        # HMDB, CHEBI, KEGG actions
│   │   │   └── chemistry/          # LOINC, clinical test actions
│   │   ├── algorithms/             # Analysis algorithms  
│   │   ├── io/                     # Import/export actions
│   │   ├── utils/                  # Utility actions
│   │   ├── workflows/              # High-level workflows
│   │   ├── typed_base.py           # TypedStrategyAction base
│   │   ├── registry.py             # Global ACTION_REGISTRY
│   │   └── base.py                 # BaseStrategyAction
│   ├── api/                        # FastAPI service
│   │   ├── main.py                 # Server configuration
│   │   ├── routes/                 # REST endpoints
│   │   └── services/
│   │       └── mapper_service.py   # Job orchestration
│   ├── client/                     # Python client
│   │   └── client_v2.py            # BiomapperClient
│   ├── core/                       # Core library
│   │   ├── minimal_strategy_service.py  # Execution engine
│   │   ├── models/                 # Data models
│   │   ├── standards/              # 2025 standardizations
│   │   └── algorithms/             # Core algorithms
│   └── configs/
│       └── strategies/             # YAML strategies
│           ├── experimental/       # Development strategies
│           ├── metabolite/         # Metabolite-specific
│           └── protein/            # Protein-specific
├── tests/
│   └── unit/                       # Unit tests
│       ├── core/
│       │   └── strategy_actions/   # Action tests
│       └── strategy_actions/       # Legacy test location
└── docs/                           # Documentation
    └── source/
        └── architecture/           # Architecture docs
```

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Client Layer                      │
│  • BiomapperClient (Python)                        │
│  • CLI Scripts                                     │
│  • Jupyter Notebooks                               │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP/REST
┌───────────────────▼─────────────────────────────────┐
│                    API Layer                        │
│  • FastAPI Server (port 8000)                      │
│  • MapperService (job orchestration)               │
│  • Background job processing                        │
│  • SQLite persistence (biomapper.db)               │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                   Core Layer                        │
│  • MinimalStrategyService (execution engine)       │
│  • ACTION_REGISTRY (global action registry)        │
│  • TypedStrategyAction (base class)                │
│  • Execution Context (shared state)                │
└─────────────────────────────────────────────────────┘
```

## Execution Flow

1. **Client Request**: `BiomapperClient.run("strategy_name")`
2. **Job Creation**: API creates background job with unique ID
3. **Strategy Loading**: MinimalStrategyService loads YAML from configs/
4. **Action Resolution**: ACTION_REGISTRY lookup for each step
5. **Parameter Validation**: Pydantic models validate action params
6. **Sequential Execution**: Actions execute via `execute_typed()`
7. **Context Updates**: Each action modifies shared context
8. **Checkpointing**: Progress saved to SQLite for recovery
9. **Result Return**: Via REST response or SSE stream

## Key Design Principles

### 1. Self-Registration
- Actions register automatically via `@register_action` decorator
- No manual registration or executor modifications needed
- Plugin-style extensibility

### 2. Type Safety
- Pydantic models for parameter validation
- `TypedStrategyAction` generic base class
- Compile-time type hints with runtime validation
- Backward compatibility during migration

### 3. Shared Execution Context
- Actions communicate through shared `Dict[str, Any]`
- Standard keys: `datasets`, `statistics`, `output_files`
- Data flows between steps via named keys

### 4. Entity-Based Organization
- Actions organized by biological entity type
- Clear navigation: `entities/proteins/`, `entities/metabolites/`
- Reusable algorithms in dedicated directories

### 5. Test-Driven Development
- Write tests first, then implementation
- Minimum 80% coverage requirement
- All new actions must use TypedStrategyAction pattern

## Creating New Actions

```python
from actions.typed_base import TypedStrategyAction, StandardActionResult
from actions.registry import register_action
from pydantic import BaseModel, Field
from typing import Dict, Any
import pandas as pd

class MyActionParams(BaseModel):
    input_key: str = Field(..., description="Input dataset key")
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    output_key: str = Field(..., description="Output dataset key")

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, StandardActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict[str, Any]) -> StandardActionResult:
        # Access input data
        datasets = context.get("datasets", {})
        input_data = datasets.get(params.input_key, pd.DataFrame())
        
        # Process data using pandas
        if not input_data.empty:
            processed = input_data[input_data["score"] >= params.threshold]
        else:
            processed = pd.DataFrame()
        
        # Store output
        if "datasets" not in context:
            context["datasets"] = {}
        context["datasets"][params.output_key] = processed
        
        return StandardActionResult(
            success=True,
            message=f"Processed {len(processed)} items",
            data={"input_count": len(input_data), "output_count": len(processed)}
        )
```

Action will auto-register - no other changes needed!

## Strategy Configuration

Strategies are defined in YAML files:

```yaml
name: "STRATEGY_NAME"
description: "Strategy description"

metadata:
  entity_type: "proteins|metabolites|chemistry"
  quality_tier: "experimental|production|test"
  version: "1.0.0"

parameters:
  input_file: "${DATA_DIR}/input.tsv"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"

steps:
  - name: step_name
    action:
      type: ACTION_TYPE
      params:
        input_key: "dataset_key"
        output_key: "result_key"
```

See [YAML Strategies](./yaml_strategies.rst) for complete documentation.

## Performance Considerations

- **Chunking**: Large datasets processed via CHUNK_PROCESSOR action
- **Async Execution**: All actions implement async execute_typed()
- **Caching**: SQLite persistence for job recovery
- **Streaming**: SSE for real-time progress without polling
- **Memory Management**: Iterative processing for large files

## Current Status

- **37+ Actions**: Comprehensive coverage of biological entities
- **Type Safety Migration**: ~35 of 37 actions use TypedStrategyAction
- **Production Ready**: Used in multiple research projects
- **Active Development**: Regular additions based on research needs

## Deployment

The system runs as a containerized FastAPI service with:
- Async HTTP handling via uvicorn
- Automatic API documentation via OpenAPI/Swagger
- Health check endpoints
- CORS support for web applications
- SQLite job persistence
- Background job processing

## Future Enhancements

### Planned Features
- JSON schema generation for YAML validation
- OpenAPI integration for auto-documentation
- Web UI for strategy creation and monitoring
- Advanced caching strategies
- Parallel action execution support

### Extensibility Points
- Custom action types via registry
- Alternative execution strategies
- Different storage backends
- Integration with external workflow systems

---

## Verification Sources
*Last verified: 2025-01-17*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/` (Self-registering actions organized by entity type with registry.py)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class with StandardActionResult)
- `/biomapper/src/core/minimal_strategy_service.py` (MinimalStrategyService execution engine)
- `/biomapper/src/api/main.py` (FastAPI server configuration with uvicorn)
- `/biomapper/src/api/services/mapper_service.py` (MapperService job orchestration)
- `/biomapper/src/client/client_v2.py` (BiomapperClient synchronous wrapper)
- `/biomapper/src/configs/strategies/` (YAML strategy templates and examples)
- `/biomapper/CLAUDE.md` (2025 standardizations and TDD development patterns)