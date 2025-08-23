# Strategy Actions - AI Assistant Instructions (2025 Standardized Framework)

## Overview

This directory contains the action type implementations for biomapper's mapping strategies using the **2025 standardized framework**. Each action represents a specific operation that can be performed on identifiers during the mapping process. 

**🎯 CRITICAL**: All actions MUST follow the 10 biomapper standardizations implemented in January 2025 to prevent pipeline failures and ensure reliability.

## 🛡️ Required Standards Compliance

Before implementing any action, ensure you follow ALL these standards:

### 1. Parameter Naming Standard ✅
- Use `input_key`, `output_key`, `file_path` (not `dataset_key`, `filepath`, etc.)
- Validate with: `from biomapper.core.standards.parameter_validator import ParameterValidator`

### 2. Context Type Handling ✅  
- Always use: `from biomapper.core.standards.context_handler import UniversalContext`
- Pattern: `ctx = UniversalContext.wrap(context)`

### 3. Algorithm Complexity Standards ✅
- Audit with: `python audits/complexity_audit.py` before implementation
- Use: `from biomapper.core.algorithms.efficient_matching import EfficientMatcher`

### 4. Identifier Normalization ✅
- Always normalize biological IDs: `from biomapper.core.standards.identifier_registry import normalize_identifier`

### 5. Pydantic Model Flexibility ✅
- Inherit from: `from biomapper.core.standards.base_models import ActionParamsBase`

### Additional Standards: File loading robustness, API validation, environment config, edge case debugging, three-level testing

## Enhanced Directory Structure

```
strategy_actions/
├── entities/                       # Entity-specific actions
│   ├── proteins/                   # Protein-specific actions
│   │   ├── annotation/             # ID extraction & normalization
│   │   │   ├── extract_uniprot_from_xrefs.py
│   │   │   └── normalize_accessions.py
│   │   ├── matching/               # Matching strategies
│   │   │   └── multi_bridge.py
│   │   └── structure/              # Future: protein structure
│   ├── metabolites/                # Metabolite-specific actions
│   │   ├── identification/         # ID extraction & normalization
│   │   │   ├── extract_identifiers.py
│   │   │   └── normalize_hmdb.py
│   │   ├── matching/               # Matching strategies
│   │   │   ├── cts_bridge.py
│   │   │   ├── nightingale_nmr_match.py
│   │   │   ├── semantic_match.py
│   │   │   └── vector_enhanced_match.py
│   │   └── enrichment/             # External data
│   │       └── api_enrichment.py
│   ├── chemistry/                  # Chemistry-specific actions
│   │   ├── identification/         # LOINC extraction
│   │   ├── matching/               # Fuzzy test matching
│   │   └── harmonization/          # Vendor differences
│   └── genes/                      # Future expansion
│
├── algorithms/                     # Reusable algorithms
│   ├── fuzzy_matching/             # String similarity algorithms
│   ├── normalization/              # ID standardization
│   └── validation/                 # Data validation
│
├── utils/                          # General utilities
│   ├── data_processing/            # DataFrame operations
│   ├── io_helpers/                 # File I/O utilities
│   └── logging/                    # Action logging
│
├── workflows/                      # High-level workflows
├── io/                            # Data input/output
├── reports/                       # Analysis & reporting
└── deprecated/                    # Legacy actions
```

## Organizational Principles

### 1. **Entity-Based Organization**
Actions are organized by the biological entity they primarily handle:

- **proteins/**: UniProt, Ensembl, gene symbol processing
- **metabolites/**: HMDB, InChIKey, CHEBI, KEGG handling
- **chemistry/**: LOINC, clinical test matching
- **genes/**: Gene-specific operations (future)

### 2. **Functional Sub-Categories**
Within each entity, actions are organized by function:

- **annotation/**: Identifier extraction and normalization
- **matching/**: Identifier resolution and mapping
- **enrichment/**: External data integration
- **structure/**: Structural analysis (proteins)
- **identification/**: ID format handling
- **harmonization/**: Cross-platform standardization

### 3. **Separation of Concerns**
- **Actions**: Business logic for biological data processing
- **Algorithms**: Reusable computational methods
- **Utils**: General-purpose helper functions

## Naming Conventions

### File Naming (Pythonic)
```python
extract_uniprot_from_xrefs.py     # verb_object_from_source
normalize_hmdb_ids.py             # verb_object_type
match_via_semantic_similarity.py  # verb_via_method
```

### Action Registration (Consistent)
```python
@register_action("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS")
@register_action("METABOLITE_NORMALIZE_HMDB")
@register_action("CHEMISTRY_FUZZY_TEST_MATCH")
```

### Class and Function Names
```python
# Classes: PascalCase
class ProteinExtractUniprotFromXrefs(TypedStrategyAction):

# Functions: snake_case
def extract_uniprot_ids(xrefs_field: str) -> List[str]:
def normalize_hmdb_format(hmdb_id: str) -> str:
```

## Enhanced Development Workflow

### Step 1: Determine Action Category
Choose the appropriate location in the enhanced structure:

```python
# Entity-specific processing
entities/proteins/annotation/     # UniProt extraction, normalization
entities/metabolites/matching/    # CTS bridge, semantic matching
entities/chemistry/identification/ # LOINC extraction

# Shared functionality
algorithms/fuzzy_matching/        # Reusable matching algorithms
utils/data_processing/            # DataFrame manipulation
workflows/                        # Multi-step orchestration
```

### Step 2: Use Standardized Base Classes (2025 Framework)
```python
# REQUIRED: Use standardized imports
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.standards.base_models import ActionParamsBase  # STANDARD 5
from biomapper.core.standards.context_handler import UniversalContext  # STANDARD 2
from biomapper.core.standards.identifier_registry import normalize_identifier  # STANDARD 4
from pydantic import Field

# STANDARD 1: Parameter naming compliance
class MyActionParams(ActionParamsBase):  # Inherits debug/trace/timeout
    input_key: str = Field(..., description="Input dataset key")  # STANDARD NAME
    output_key: str = Field(..., description="Output dataset key")  # STANDARD NAME
    threshold: float = Field(0.8, description="Processing threshold")

@register_action("MY_ENTITY_ACTION_NAME")
class MyEntityAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # STANDARD 2: Context handling
        ctx = UniversalContext.wrap(context)
        input_data = ctx.get_dataset(params.input_key)
        
        # STANDARD 4: Identifier normalization for biological data
        if self._has_biological_identifiers(input_data):
            input_data = self._normalize_identifiers(input_data)
        
        # STANDARD 3: Algorithm complexity - use efficient patterns
        if len(input_data) > 1000:  # Large dataset
            from biomapper.core.algorithms.efficient_matching import EfficientMatcher
            processed_data = self._process_large_dataset_efficiently(input_data)
        else:
            processed_data = self._process_small_dataset(input_data)
        
        # Store results using standardized context
        ctx.set_dataset(params.output_key, processed_data)
        
        return ActionResult(success=True, message=f"Processed {len(processed_data)} items")
        
    def _normalize_identifiers(self, data):
        """Apply biological identifier normalization"""
        for col in ['uniprot_id', 'protein_id', 'gene_id']:
            if col in data.columns:
                data[f'{col}_normalized'] = data[col].apply(
                    lambda x: normalize_identifier(x).base_id if normalize_identifier(x) else x
                )
        return data
```

### Step 3: Leverage Shared Components
```python
# Use shared algorithms
from ..algorithms.fuzzy_matching import string_similarity
from ..algorithms.normalization import identifier_patterns

# Use shared utilities
from ..utils.data_processing import chunk_processor
from ..utils.logging import action_logger
```

## Standardized Three-Level Testing Framework (2025)

### REQUIRED: Follow Three-Level Testing Pattern
All action tests MUST implement the standardized three-level framework:

```python
# tests/unit/core/strategy_actions/entities/proteins/test_my_action.py
from biomapper.testing.base import ActionTestBase
from biomapper.testing.data_generator import BiologicalDataGenerator
from biomapper.testing.performance import PerformanceProfiler

class TestMyAction(ActionTestBase):
    
    def test_level_1_minimal_data(self):
        """Level 1: Unit test with minimal data (<1s execution)"""
        # Generate realistic biological data (3-5 rows)
        minimal_data = BiologicalDataGenerator.generate_uniprot_dataset(5)
        
        # Execute action with minimal context
        result = await self.execute_action_with_data("MY_ACTION", minimal_data)
        
        # Basic functionality assertions
        assert result.success
        assert len(result.data) == 5
        
    def test_level_2_sample_data(self):
        """Level 2: Integration test with sample data (<10s execution)"""
        # Generate sample dataset (100-1000 rows)
        sample_data = BiologicalDataGenerator.generate_uniprot_dataset(1000)
        
        # Test with performance profiling
        with PerformanceProfiler() as profiler:
            result = await self.execute_action_with_data("MY_ACTION", sample_data)
        
        # Performance and complexity assertions
        assert result.success
        self.assert_complexity_linear(profiler.execution_time, len(sample_data))
        self.assert_memory_usage_reasonable(profiler.peak_memory)
        
    def test_level_3_production_subset(self):
        """Level 3: Production subset test (<60s execution)"""
        # Use real production data subset (1000+ rows)
        prod_data = self.load_production_subset("arivale_proteins", 5000)
        
        # Execute with edge case monitoring
        result = await self.execute_action_with_data("MY_ACTION", prod_data)
        
        # Real-world validation
        assert result.success
        assert result.data['edge_cases_handled'] > 0
        self.validate_biological_data_integrity(result.data)
        
    def test_edge_cases_q6emk4_pattern(self):
        """Test known edge cases like Q6EMK4"""
        edge_case_data = BiologicalDataGenerator.generate_edge_cases(['Q6EMK4'])
        result = await self.execute_action_with_data("MY_ACTION", edge_case_data)
        # Validate edge case handling
        assert 'Q6EMK4' in result.data['processed_identifiers']
```

### Test Organization (Standardized)
```
tests/unit/core/strategy_actions/
├── entities/
│   ├── proteins/
│   │   ├── annotation/
│   │   │   ├── test_extract_uniprot_from_xrefs.py  # Three-level tests
│   │   │   └── test_normalize_accessions.py        # Three-level tests
│   │   └── matching/
│   │       └── test_multi_bridge.py                # Three-level tests
│   ├── metabolites/
│   └── chemistry/
├── algorithms/
└── utils/
```

### Testing Commands (Enhanced)
```bash
# Run three-level tests for specific action
python scripts/run_three_level_tests.py proteins --action extract_uniprot

# Run with performance benchmarking
python scripts/run_three_level_tests.py proteins --performance

# Run specific levels only
python scripts/run_three_level_tests.py proteins --level 1  # Fast unit tests
python scripts/run_three_level_tests.py proteins --level 2  # Integration tests  
python scripts/run_three_level_tests.py proteins --level 3  # Production subset

# Traditional pytest (still supported)
poetry run pytest -xvs tests/unit/core/strategy_actions/entities/proteins/annotation/test_extract_uniprot.py
```

## Import Strategy and Registration

### Main Module Imports
```python
# biomapper/core/strategy_actions/__init__.py

from . import registry

# Entity imports (triggers action registration)
from .entities import *

# Algorithm and utility imports
from .algorithms import *
from .utils import *
from .workflows import *
from .io import *
from .reports import *

__all__ = ['registry']
```

### Entity Module Imports
```python
# biomapper/core/strategy_actions/entities/proteins/__init__.py

# Import all protein action categories
from .annotation import *  # extract_uniprot, normalize_accessions
from .matching import *    # multi_bridge
# from .structure import * # Future expansion

__all__ = []  # Actions register themselves
```

### Category Module Imports
```python
# biomapper/core/strategy_actions/entities/proteins/annotation/__init__.py

# Import all annotation actions to trigger registration
from .extract_uniprot_from_xrefs import *
from .normalize_accessions import *

__all__ = []  # Actions register themselves
```

## Entity-Specific Development Guidelines

### Proteins
**Focus**: UniProt accessions, gene symbols, Ensembl IDs
**Common Patterns**:
- UniProt format: P12345, O00533 (6-character)
- Ensembl proteins: ENSP00000123456
- Gene symbols: HGNC official symbols

**Key Actions**:
```python
PROTEIN_EXTRACT_UNIPROT_FROM_XREFS  # annotation/
PROTEIN_NORMALIZE_ACCESSIONS        # annotation/
PROTEIN_MULTI_BRIDGE               # matching/
```

### Metabolites
**Focus**: HMDB, InChIKey, CHEBI, KEGG, PubChem
**Common Patterns**:
- HMDB: HMDB0001234 (7-digit standard)
- InChIKey: BQJCRHHNABKAKU-KBQPJGBKSA-N
- CHEBI: CHEBI:28001

**Key Actions**:
```python
METABOLITE_EXTRACT_IDENTIFIERS     # identification/
METABOLITE_NORMALIZE_HMDB          # identification/
METABOLITE_CTS_BRIDGE             # matching/
```

### Chemistry
**Focus**: LOINC codes, clinical test names, vendor harmonization
**Common Patterns**:
- LOINC: 12345-6 (numeric-check format)
- Test names: Highly variable, fuzzy matching required

**Key Actions**:
```python
CHEMISTRY_EXTRACT_LOINC            # identification/
CHEMISTRY_FUZZY_TEST_MATCH         # matching/
CHEMISTRY_VENDOR_HARMONIZATION     # harmonization/
```

## Performance and Scalability

### Chunking for Large Datasets
```python
from ..utils.data_processing.chunk_processor import ChunkProcessor

# Use shared chunking utility
processor = ChunkProcessor(chunk_size=10000)
for chunk in processor.process_dataframe(large_df):
    # Process chunk
    results.extend(process_chunk(chunk))
```

### Algorithm Reuse
```python
from ..algorithms.fuzzy_matching import calculate_similarity
from ..algorithms.normalization import standardize_identifiers

# Reuse across entity types
similarity_score = calculate_similarity(source_name, target_name)
standardized_ids = standardize_identifiers(raw_ids, id_type="hmdb")
```

### Caching and Optimization
```python
from ..utils.data_processing import cached_operation

@cached_operation(cache_key="uniprot_patterns")
def load_uniprot_patterns():
    # Expensive operation cached across actions
    return patterns
```

## Documentation Requirements

### Entity Module Documentation
```python
# entities/proteins/__init__.py
"""
Protein-specific actions for biomapper.

This module provides comprehensive protein identifier processing,
normalization, and matching capabilities.

Submodules:
    annotation: UniProt extraction, accession normalization
    matching: Multi-bridge resolution strategies
    structure: Protein structure analysis (future)

Common Data Patterns:
    UniProt: P12345, O00533 (standard 6-character accessions)
    Ensembl: ENSP00000123456 (protein IDs)
    Gene symbols: CD4, TP53 (HGNC official symbols)

Example Workflow:
    1. Load protein datasets with LOAD_DATASET_IDENTIFIERS
    2. Extract UniProt IDs with PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
    3. Normalize formats with PROTEIN_NORMALIZE_ACCESSIONS
    4. Match across datasets with PROTEIN_MULTI_BRIDGE
"""
```

### Action Documentation
```python
@register_action("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS")
class ProteinExtractUniprotFromXrefs(TypedStrategyAction):
    """
    Extract UniProt accession IDs from compound xrefs fields.
    
    This action handles the complex task of extracting UniProt identifiers
    from KG2c and SPOKE xrefs fields that contain multiple identifier types
    separated by various delimiters.
    
    Handles:
    - Multiple UniProt IDs per xrefs field
    - Isoform suffixes (P12345-1) - configurable removal
    - Version numbers (P12345.2) - automatic removal
    - Various prefix formats (UniProtKB:, uniprot:)
    
    Args:
        params: ProteinExtractUniprotParams with extraction configuration
        context: Execution context with datasets
        
    Returns:
        ActionResult with extracted UniProt identifiers
        
    Example:
        # Input xrefs: "UniProtKB:P12345|RefSeq:NP_001234|KEGG:K12345"
        # Output: ["P12345"]
    """
```

## Migration Strategy

### Phase 1: Structure Creation
1. Create enhanced directory structure
2. Update main `__init__.py` imports
3. Test backward compatibility

### Phase 2: Action Migration
1. Move existing actions to appropriate entity directories
2. Update imports throughout codebase
3. Test all existing functionality

### Phase 3: Enhancement
1. Add shared algorithms and utilities
2. Implement new entity-specific actions
3. Add comprehensive documentation

### Phase 4: Optimization
1. Leverage shared components for performance
2. Add enhanced testing and validation
3. Optimize import strategy

## Code Review Checklist (2025 Standards Compliance)

Before submitting a new action, ensure ALL standards are followed:

### 🎯 Critical Standards Compliance
- [ ] **Parameter Naming (Standard 1)**: Uses `input_key`, `output_key`, `file_path` (validated)
- [ ] **Context Handling (Standard 2)**: Uses `UniversalContext.wrap(context)`
- [ ] **Algorithm Complexity (Standard 3)**: Audited with complexity checker, uses EfficientMatcher
- [ ] **Identifier Normalization (Standard 4)**: Biological IDs normalized with registry
- [ ] **File Loading (Standard 5)**: Uses `BiologicalFileLoader` for data ingestion
- [ ] **API Validation (Standard 6)**: API clients validated with `APIMethodValidator`
- [ ] **Environment Config (Standard 7)**: Uses `EnvironmentManager` for configuration
- [ ] **Pydantic Models (Standard 8)**: Inherits from `ActionParamsBase` for flexibility
- [ ] **Edge Case Handling (Standard 9)**: Known issues documented in registry
- [ ] **Three-Level Testing (Standard 10)**: Level 1, 2, 3 tests implemented

### 📋 Traditional Checks (Still Required)
- [ ] **Organization**: Action placed in correct entity/category directory
- [ ] **Typing**: Uses TypedStrategyAction with Pydantic models
- [ ] **Registration**: Properly registered with @register_action decorator
- [ ] **Imports**: Added to appropriate __init__.py files
- [ ] **Documentation**: Entity-specific docstrings with examples
- [ ] **Error Handling**: Comprehensive error handling and logging
- [ ] **Compatibility**: Maintains backward compatibility

### 🚀 Performance and Quality
- [ ] **Performance Benchmarked**: Level 2 tests include performance assertions
- [ ] **Edge Cases Covered**: Q6EMK4-style issues tested and documented
- [ ] **Memory Efficient**: Large datasets handled with chunking/efficient algorithms
- [ ] **Biological Data Validated**: Real-world biological patterns tested

### 🔍 Pre-Submission Commands
```bash
# 1. Validate parameter naming
python -c "from biomapper.core.standards.parameter_validator import ParameterValidator; ParameterValidator.audit_action('MY_ACTION')"

# 2. Check algorithm complexity
python audits/complexity_audit.py --file my_action.py

# 3. Run three-level tests
python scripts/run_three_level_tests.py my_entity --action MY_ACTION

# 4. Type checking
poetry run mypy biomapper/core/strategy_actions/entities/my_entity/my_action.py
```

## Getting Help with Enhanced Organization

### Finding Existing Actions
```bash
# Search by entity type
find entities/proteins/ -name "*.py" | grep -v __pycache__

# Search by function
find . -path "*/matching/*" -name "*.py"

# Search by pattern in action names
grep -r "EXTRACT.*UNIPROT" entities/
```

### Understanding Dependencies
```bash
# See what algorithms an action uses
grep -r "from.*algorithms" entities/proteins/

# See what utilities are shared
ls utils/*/
```

### Development Commands
```bash
# Run entity-specific tests
poetry run pytest tests/unit/core/strategy_actions/entities/proteins/

# Run algorithm tests
poetry run pytest tests/unit/core/strategy_actions/algorithms/

# Type checking for specific entity
poetry run mypy biomapper/core/strategy_actions/entities/proteins/
```

Remember: The enhanced organization enables scalable development while maintaining the robust, tested patterns that make biomapper actions reliable for complex bioinformatics data processing.

## Action Development Checklist

### Before You Start
- [ ] Does this action already exist? Check registry
- [ ] Which entity does it belong to? (proteins/metabolites/chemistry)
- [ ] Have you written tests FIRST? (TDD mandatory)
- [ ] Is there a similar action to reference?

### During Development
- [ ] Using TypedStrategyAction base class?
- [ ] Parameters extend ActionParamsBase?
- [ ] Context wrapped with UniversalContext?
- [ ] Identifiers normalized with registry?
- [ ] Complexity checked (<O(n²))?
- [ ] Progress events emitted?

### Before Commit
- [ ] Tests pass (unit, integration, production)?
- [ ] Type checking passes (mypy)?
- [ ] Coverage >80% for new code?
- [ ] Action auto-registers correctly?
- [ ] Documentation in docstrings?

## Debugging Guide

### Action Not Found
```python
# Check registration
from src.actions.registry import ACTION_REGISTRY
print(ACTION_REGISTRY.keys())
```

### Context Issues
```python
# Always wrap context
from biomapper.core.standards.context_handler import UniversalContext
ctx = UniversalContext.wrap(context)
```

### Performance Problems
```bash
# Profile your action
python audits/complexity_audit.py src/actions/your_action.py
```

## Entity-Specific Patterns

### Proteins
- Always handle composite IDs (P12345,P67890)
- Normalize UniProt accessions
- Preserve original IDs in _original_* columns

### Metabolites  
- Multiple ID types (HMDB, InChIKey, CAS, KEGG)
- Use progressive matching (direct → fuzzy → semantic)
- Track match confidence scores

### Chemistry
- LOINC code extraction
- Clinical test name normalization
- Unit conversion handling