# BioMapper

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency-poetry-blue.svg)](https://python-poetry.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

BioMapper is a YAML-based workflow platform built on a self-registering action system. While originally designed for biological data harmonization (proteins, metabolites, chemistry), its extensible architecture supports any workflow that can be expressed as a sequence of actions operating on shared execution context.

## 🎯 Key Features

- **Self-registering action system** - Actions automatically register via decorators
- **Type-safe parameters** - Pydantic models provide validation and IDE support
- **YAML workflow definition** - Declarative strategies without coding
- **Real-time progress tracking** - SSE events for long-running jobs
- **Extensible architecture** - Easy to add new actions and entity types
- **AI-ready design** - Built for integration with Claude Code and LLM assistance

## 🏗️ Architecture

### Overview

BioMapper follows a modern microservices architecture with clear separation of concerns:

**Three-Layer Design:**
1. **Client Layer** - Python client library (`biomapper_client`) provides programmatic access
2. **API Layer** - FastAPI service handles HTTP requests, job management, and background processing
3. **Core Layer** - Business logic with self-registering actions and strategy execution engine

**Key Architectural Patterns:**
- **Registry Pattern** - Actions self-register at import time using decorators, eliminating manual registration
- **Strategy Pattern** - YAML configurations define workflows as sequences of pluggable actions
- **Pipeline Pattern** - Actions process data through a shared execution context, enabling complex workflows
- **Type Safety** - Pydantic models provide runtime validation and compile-time type checking

**Data Flow:**
1. User defines a workflow in YAML (strategy) or calls the API directly
2. Client sends request to FastAPI server
3. Server validates request and creates a background job
4. MinimalStrategyService loads the strategy and executes actions sequentially
5. Each action reads from and writes to a shared execution context
6. Results persist to SQLite for recovery and progress tracking
7. Client receives results via REST response or Server-Sent Events (SSE)

**Design Principles:**
- **Modularity** - Each action is independent and reusable
- **Extensibility** - New actions can be added without modifying core code
- **Type Safety** - Strong typing prevents runtime errors
- **Reproducibility** - YAML strategies ensure consistent execution
- **Fault Tolerance** - Job persistence enables recovery from failures

### System Architecture Diagram

```mermaid
flowchart TB
    Client[Client Request] --> BiomapperClient
    BiomapperClient --> API[FastAPI Server]
    API --> MapperService[MapperService]
    MapperService --> MSS[MinimalStrategyService]
    
    MSS --> |Loads at startup| Config[(configs/strategies/*.yaml)]
    MSS --> |Executes actions| Registry["ACTION_REGISTRY<br/>Global Dict"]
    
    Registry --> |Lookup by name| ActionClass[Action Classes]
    ActionClass --> |Self-register| Decorator["@register_action"]
    
    ActionClass --> Execute[Execute Action]
    Execute --> Context["Execution Context<br/>Dict[str, Any]"]
    Context --> |Shared state| NextAction[Next Action]
    
    ActionClass -.-> TypedAction[TypedStrategyAction]
    ActionClass -.-> Pydantic[Pydantic Models]
    
    MSS --> |Job persistence| DB[(SQLite biomapper.db)]
```

### Core Components

| Component | Description | Location |
|-----------|-------------|----------|
| **biomapper/** | Core library with action implementations | Root package |
| **biomapper-api/** | FastAPI REST service | `biomapper-api/` |
| **biomapper_client/** | Python client library | `biomapper_client/` |
| **ACTION_REGISTRY** | Global action registry | `biomapper/core/strategy_actions/registry.py` |
| **MinimalStrategyService** | Strategy execution engine | `biomapper/core/services/strategy_service_v2_minimal.py` |

## 📦 Installation

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Git for version control

### Quick Start

```bash
# Clone repository
git clone https://github.com/biomapper/biomapper.git
cd biomapper

# Install dependencies with Poetry
poetry install --with dev,docs,api

# Activate virtual environment
poetry shell

# Run tests to verify installation
poetry run pytest

# Start the API server
cd biomapper-api && poetry run uvicorn app.main:app --reload
```

## 🚀 Usage

### Command Line Interface

```bash
# Basic CLI commands
poetry run biomapper --help
poetry run biomapper health
poetry run biomapper metadata list

# Run a strategy
poetry run python scripts/run_strategy.py --strategy test_metabolite_simple
```

### Python Client

```python
from biomapper_client import BiomapperClient

# Synchronous usage (recommended for scripts)
client = BiomapperClient(base_url="http://localhost:8000")
result = client.run("test_metabolite_simple", parameters={
    "input_file": "/data/metabolites.csv",
    "output_dir": "/results"
})
print(f"Results: {result}")

# Async usage (for integration)
import asyncio

async def run_async():
    async with BiomapperClient() as client:
        result = await client.execute_strategy(
            "test_metabolite_simple",
            parameters={"input_file": "/data/metabolites.csv"}
        )
        return result

asyncio.run(run_async())
```

### YAML Strategy Definition

Create strategies in `configs/strategies/`:

```yaml
name: metabolite_harmonization
description: Harmonize metabolite identifiers across platforms

parameters:
  input_file: "${DATA_DIR}/metabolites.tsv"
  output_dir: "${OUTPUT_DIR}"
  fuzzy_threshold: 0.85

steps:
  - name: load_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.input_file}"
        identifier_column: "compound_name"
        output_key: "input_metabolites"

  - name: enrich_with_cts
    action:
      type: METABOLITE_CTS_BRIDGE
      params:
        input_key: "input_metabolites"
        output_key: "cts_enriched"
        from_format: "Chemical Name"
        to_format: "InChIKey"

  - name: export_results
    action:
      type: EXPORT_DATASET_V2
      params:
        input_key: "cts_enriched"
        output_file: "${parameters.output_dir}/harmonized.csv"
        format: "csv"
```

## 📚 Available Actions

### Data Operations
| Action | Description |
|--------|-------------|
| `LOAD_DATASET_IDENTIFIERS` | Load biological identifiers from CSV/TSV files |
| `MERGE_DATASETS` | Combine multiple datasets with deduplication |
| `FILTER_DATASET` | Apply filtering criteria to datasets |
| `EXPORT_DATASET_V2` | Export results to CSV/TSV/JSON formats |
| `CUSTOM_TRANSFORM_EXPRESSION` | Apply Python expressions to transform data |

### Protein Actions
| Action | Description |
|--------|-------------|
| `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` | Extract UniProt IDs from compound reference fields |
| `PROTEIN_NORMALIZE_ACCESSIONS` | Standardize protein accession formats |
| `PROTEIN_MULTI_BRIDGE` | Multi-source protein identifier resolution |
| `MERGE_WITH_UNIPROT_RESOLUTION` | Map identifiers to UniProt accessions |

### Metabolite Actions
| Action | Description |
|--------|-------------|
| `METABOLITE_CTS_BRIDGE` | Chemical Translation Service API integration |
| `METABOLITE_EXTRACT_IDENTIFIERS` | Extract metabolite IDs from text fields |
| `METABOLITE_NORMALIZE_HMDB` | Standardize HMDB identifier formats |
| `METABOLITE_MULTI_BRIDGE` | Multi-database metabolite resolution |
| `NIGHTINGALE_NMR_MATCH` | Nightingale NMR platform matching |
| `SEMANTIC_METABOLITE_MATCH` | AI-powered semantic matching |
| `VECTOR_ENHANCED_MATCH` | Vector embedding similarity matching |
| `METABOLITE_API_ENRICHMENT` | Enrich via external metabolite APIs |
| `COMBINE_METABOLITE_MATCHES` | Merge results from multiple strategies |

### Chemistry Actions
| Action | Description |
|--------|-------------|
| `CHEMISTRY_EXTRACT_LOINC` | Extract LOINC codes from clinical data |
| `CHEMISTRY_FUZZY_TEST_MATCH` | Fuzzy matching for clinical test names |
| `CHEMISTRY_VENDOR_HARMONIZATION` | Harmonize vendor-specific test codes |
| `CHEMISTRY_TO_PHENOTYPE_BRIDGE` | Link chemistry results to phenotypes |

### Analysis & Reporting
| Action | Description |
|--------|-------------|
| `CALCULATE_SET_OVERLAP` | Calculate Jaccard similarity between datasets |
| `CALCULATE_THREE_WAY_OVERLAP` | Three-way dataset comparison analysis |
| `CALCULATE_MAPPING_QUALITY` | Assess mapping quality metrics |
| `GENERATE_METABOLOMICS_REPORT` | Generate comprehensive metabolomics reports |
| `GENERATE_ENHANCEMENT_REPORT` | Create validation and enhancement reports |

### IO & Integration
| Action | Description |
|--------|-------------|
| `SYNC_TO_GOOGLE_DRIVE_V2` | Upload results to Google Drive |
| `CHUNK_PROCESSOR` | Process large datasets in chunks |

## 🧪 Development

### Creating New Actions

Follow Test-Driven Development (TDD) approach:

```python
# 1. Write test first (tests/unit/core/strategy_actions/test_my_action.py)
import pytest
from biomapper.core.strategy_actions.my_action import MyAction, MyActionParams

async def test_my_action():
    params = MyActionParams(input_key="test", threshold=0.8)
    context = {"datasets": {"test": [{"id": "1", "name": "test"}]}}
    
    action = MyAction()
    result = await action.execute_typed(params, context)
    
    assert result.success
    assert "processed" in context["datasets"]

# 2. Implement action (biomapper/core/strategy_actions/my_action.py)
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel, Field

class MyActionParams(BaseModel):
    input_key: str = Field(..., description="Input dataset key")
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    output_key: str = Field("processed", description="Output dataset key")

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    """Process biological data with threshold filtering."""
    
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # Get input data
        input_data = context["datasets"].get(params.input_key, [])
        
        # Process with threshold
        processed = [item for item in input_data 
                    if item.get("score", 0) >= params.threshold]
        
        # Store results
        context["datasets"][params.output_key] = processed
        
        return ActionResult(
            success=True,
            message=f"Processed {len(processed)} items",
            data={"filtered_count": len(input_data) - len(processed)}
        )
```

### Testing

```bash
# Run all tests with coverage
poetry run pytest --cov=biomapper --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/                    # Unit tests only
poetry run pytest tests/integration/             # Integration tests
poetry run pytest -k "test_my_action"           # Specific test by name

# Debug failing test
poetry run pytest -xvs --pdb tests/unit/core/strategy_actions/test_my_action.py
```

### Code Quality

```bash
# Format code
poetry run ruff format .

# Check and fix linting issues
poetry run ruff check . --fix

# Type checking
poetry run mypy biomapper biomapper-api biomapper_client

# Run all checks (recommended before committing)
make check  # Runs format, lint, typecheck, test, and docs
```

### Makefile Commands

```bash
make test          # Run tests with coverage
make format        # Format code with ruff
make lint-fix      # Auto-fix linting issues
make typecheck     # Run mypy type checking
make check         # Run all checks
make docs          # Build documentation
make clean         # Clean cache files
```

## 📂 Project Structure

```
biomapper/
├── biomapper/                      # Core library
│   ├── core/
│   │   ├── strategy_actions/       # Action implementations
│   │   │   ├── entities/          # Entity-specific actions
│   │   │   │   ├── proteins/      # Protein actions
│   │   │   │   ├── metabolites/   # Metabolite actions
│   │   │   │   └── chemistry/     # Chemistry actions
│   │   │   ├── algorithms/        # Reusable algorithms
│   │   │   ├── utils/             # Utilities
│   │   │   └── registry.py        # Action registry
│   │   └── services/              # Core services
│   └── __init__.py
├── biomapper-api/                  # FastAPI service
│   ├── app/
│   │   ├── api/                   # API routes
│   │   ├── core/                  # Core API logic
│   │   └── main.py               # FastAPI app
│   └── pyproject.toml
├── biomapper_client/               # Python client
│   ├── client_v2.py              # Main client class
│   └── __init__.py
├── configs/
│   └── strategies/                # YAML strategy definitions
├── tests/                         # Test suite
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── scripts/                       # Utility scripts
├── docs/                         # Documentation
├── CLAUDE.md                     # Claude Code instructions
├── Makefile                      # Development commands
└── pyproject.toml               # Project configuration
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Data Directories
DATA_DIR=/path/to/data
OUTPUT_DIR=/path/to/output

# External Services (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
OPENAI_API_KEY=your-api-key
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

### Strategy Parameters

Strategies support variable substitution:
- `${parameters.key}` - Access strategy parameters
- `${env.VAR_NAME}` - Environment variables
- `${DATA_DIR}` - Shorthand for environment variables

## 🤖 AI Integration

BioMapper is designed for AI-assisted development with Claude Code:

1. **CLAUDE.md** - Provides context and instructions for Claude Code
2. **Type-safe actions** - Enable better code completion and error detection
3. **Self-documenting** - Pydantic models include descriptions
4. **TDD approach** - Tests provide clear specifications

Example Claude Code usage:
```
"Help me create a new action that extracts gene symbols from protein descriptions"
"Debug why my metabolite matching strategy is returning empty results"
"Optimize the CTS API calls to handle rate limiting better"
```

## 🚧 Current Development Focus

1. **Type Safety Migration** - Converting remaining actions to TypedStrategyAction pattern
2. **Enhanced Organization** - Entity-based action structure for better discoverability
3. **Performance Optimization** - Chunking and caching for large datasets
4. **External Integrations** - Expanding API connections (Google Drive, external databases)

## 📖 Documentation

- [CLAUDE.md](CLAUDE.md) - Instructions for Claude Code and development
- [Architecture Overview](biomapper/core/strategy_actions/ARCHITECTURE.md) - Detailed architecture
- [Action Development](biomapper/core/strategy_actions/CLAUDE.md) - Creating new actions
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when server running)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests first (TDD approach)
4. Implement your feature
5. Run checks (`make check`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Pydantic](https://docs.pydantic.dev/)
- Testing with [pytest](https://docs.pytest.org/)
- Code quality with [ruff](https://github.com/astral-sh/ruff)
- Dependency management with [Poetry](https://python-poetry.org/)

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub or contact the maintainers.

---

**Note:** This is an active research project. APIs and interfaces may change as we improve the platform based on user feedback and research needs.