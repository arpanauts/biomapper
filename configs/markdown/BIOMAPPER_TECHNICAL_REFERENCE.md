# Biomapper Technical Reference

**Last Updated**: August 2025  
**Version**: 2.0.0  
**Status**: Production-Ready with API-First Architecture

## 🏗️ Current Architecture

### Overview
Biomapper has achieved **full API-first architecture** as of August 2025. The system now operates with clean separation between client scripts and API service, with all orchestration handled by the biomapper-api.

### Key Components

#### 1. API Service Layer
- **FastAPI Server**: REST API handling all strategy execution
- **MinimalStrategyService**: Core strategy execution engine
- **Direct YAML Loading**: Strategies loaded from `configs/` at startup
- **Job Persistence**: SQLite database (`biomapper.db`) for state management

#### 2. Client Layer
- **BiomapperClient**: Async Python client for API interaction
- **Wrapper Scripts**: Simple API clients (~250 lines vs previous 691 lines)
- **No Direct Imports**: Zero core module imports in scripts
- **Clean Execution**: All orchestration delegated to API

#### 3. Action System
- **15+ Production Actions**: Complete set of biological data harmonization actions
- **Self-Registration**: Actions use `@register_action` decorator
- **Type Safety**: TypedStrategyAction with Pydantic models
- **Progressive Enhancement**: Multi-stage improvement strategies

### Execution Flow
```
Client → BiomapperClient → API → MinimalStrategyService → YAML Strategy → Actions → Results
```

## 📦 Available Action Types

### Core Actions
- `LOAD_DATASET_IDENTIFIERS` - Load biological identifiers from files
- `MERGE_WITH_UNIPROT_RESOLUTION` - UniProt mapping with historical resolution
- `CALCULATE_SET_OVERLAP` - Jaccard similarity analysis
- `MERGE_DATASETS` - Dataset combination with deduplication

### Metabolomics Actions
- `BASELINE_FUZZY_MATCH` - Fuzzy string matching (45% baseline)
- `CTS_ENRICHED_MATCH` - Chemical Translation Service enhancement (+15%)
- `VECTOR_ENHANCED_MATCH` - Semantic vector search (+10%)
- `NIGHTINGALE_NMR_MATCH` - Specialized NMR platform matching
- `SEMANTIC_METABOLITE_MATCH` - AI-powered matching
- `COMBINE_METABOLITE_MATCHES` - Multi-strategy merger
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset analysis

### Utility Actions
- `BUILD_NIGHTINGALE_REFERENCE` - Reference dataset creation
- `GENERATE_ENHANCEMENT_REPORT` - Progressive metrics reporting
- `GENERATE_METABOLOMICS_REPORT` - Domain-specific reporting
- `VALIDATE_AGAINST_REFERENCE` - Gold standard comparison

## 🚀 Quick Start

### Creating a Strategy
```yaml
name: MY_STRATEGY
description: "Clear description"
steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: /path/to/data.tsv
        identifier_column: id_col
        output_key: loaded_data
```

### Executing via Client
```python
from biomapper_client import BiomapperClient

async with BiomapperClient() as client:
    result = await client.execute_strategy(
        strategy_name="MY_STRATEGY",
        context={}
    )
```

### Using Wrapper Scripts
```bash
# Metabolomics harmonization
python scripts/main_pipelines/run_metabolomics_harmonization.py --three-way

# Protein mapping
python scripts/main_pipelines/run_arivale_ukbb_mapping.py
```

## 💡 Development Insights

### Progressive Enhancement Pattern
The most successful pattern for biological data harmonization:
1. **Baseline** (~45%): Start with fuzzy string matching
2. **API Enhancement** (+15%): Add external service enrichment
3. **Vector Search** (+10%): Semantic similarity matching
4. **Result**: 45% → 60% → 70% match rate improvement

### Data Quality Best Practices
- Always handle NaN and empty values
- Validate identifier formats before processing
- Filter invalid entries early in pipeline
- Track unmatched items for progressive enhancement

### External Service Integration
- **Rate Limiting**: Essential for API services (CTS, UniProt)
- **Caching**: TTL-based caching reduces API calls by 50%+
- **Fallback Strategies**: Graceful degradation when services unavailable
- **Connection Pooling**: Reuse connections for performance

### Testing Strategy
- **TDD Approach**: Write tests first for all new actions
- **Mock External Services**: Use mocks for API testing
- **Integration Tests**: Test complete workflows end-to-end
- **Performance Benchmarks**: Track execution time and memory

## 🔧 Configuration System

### Strategy Organization
```
configs/
├── strategies/          # Strategy YAML files
│   ├── metabolomics_progressive_enhancement.yaml
│   ├── three_way_metabolomics_complete.yaml
│   └── arivale_ukbb_mapping.yaml
├── clients/            # External service configs
│   ├── cts_config.yaml
│   └── qdrant_config.yaml
└── schemas/            # Validation schemas
```

### Environment Variables
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# External Services
CTS_API_KEY=your_key
QDRANT_URL=http://localhost:6333

# Data Paths
DATA_DIR=/procedure/data
RESULTS_DIR=/home/ubuntu/biomapper/data/results
```

## 📊 Performance Metrics

### Action Performance (10K items)
| Action | Time | Memory | Match Rate |
|--------|------|--------|------------|
| BASELINE_FUZZY_MATCH | 2.1s | 200MB | 45% |
| CTS_ENRICHED_MATCH | 8.5s | 300MB | +15% |
| VECTOR_ENHANCED_MATCH | 3.5s | 500MB | +10% |
| NIGHTINGALE_NMR_MATCH | 0.8s | 150MB | 85% |

### System Performance
- Strategy loading: <500ms
- API response time: <100ms overhead
- Job persistence: <10ms per checkpoint
- Concurrent jobs: 10+ supported

## 🛠️ Common Workflows

### Metabolomics Harmonization
```bash
# Progressive enhancement (3 stages)
python scripts/main_pipelines/run_metabolomics_harmonization.py

# Three-way analysis
python scripts/main_pipelines/run_metabolomics_harmonization.py --three-way

# Custom parameters
echo '{"threshold": 0.9}' > params.json
python scripts/main_pipelines/run_metabolomics_harmonization.py --parameters params.json
```

### Protein Mapping
```bash
# Arivale to UKBB
python scripts/main_pipelines/run_arivale_ukbb_mapping.py

# With custom output
python scripts/main_pipelines/run_arivale_ukbb_mapping.py --output-dir /custom/path
```

## 🐛 Debugging Tips

### Check Strategy Loading
```bash
# View API logs during startup
cd biomapper-api && poetry run uvicorn main:app --reload
# Look for: "Loaded strategy: STRATEGY_NAME"
```

### Validate YAML Syntax
```bash
# Use yamllint
poetry run yamllint configs/strategies/my_strategy.yaml
```

### Test Individual Actions
```python
# Create minimal test script
from biomapper.core.strategy_actions import ActionName
action = ActionName()
result = await action.execute(params, context)
```

### Monitor Execution
```bash
# Watch API logs
tail -f biomapper-api/logs/api.log

# Check job database
sqlite3 biomapper-api/biomapper.db "SELECT * FROM jobs;"
```

## 📚 Additional Resources

### Documentation
- [Configuration Organization Plan](CONFIGURATION_ORGANIZATION_PLAN.md)
- [Strategy Agent Specification](BIOMAPPER_STRATEGY_AGENT_SPEC.md)
- [Claude Development Guide](CLAUDE_STRATEGY_DEVELOPMENT.md)

### Example Strategies
- `metabolomics_progressive_enhancement.yaml` - Best example of progressive pattern
- `arivale_ukbb_mapping.yaml` - Simple protein mapping reference
- `three_way_metabolomics_complete.yaml` - Complex multi-dataset analysis

### API Endpoints
- `POST /api/strategies/{name}/execute` - Execute strategy
- `GET /api/jobs/{job_id}/status` - Check job status
- `GET /api/strategies` - List available strategies
- `GET /health` - API health check

## 🎯 Future Roadmap

### Near Term (Q3 2025)
- WebSocket support for real-time progress
- Strategy marketplace UI
- Enhanced validation framework

### Medium Term (Q4 2025)
- Community contribution system
- Enterprise security features
- Performance optimization tools

### Long Term (2026)
- AI-powered strategy generation
- Cloud-native deployment
- Multi-language client SDKs

---

*This reference represents the current production state of biomapper with full API-first architecture achieved.*