# Strategy Actions - AI Assistant Instructions (Enhanced Organization)

## Overview

This directory contains the action type implementations for biomapper's mapping strategies using an enhanced organizational structure. Each action represents a specific operation that can be performed on identifiers during the mapping process. The organization is optimized for scalability, maintainability, and parallel development.

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

### Step 2: Use Enhanced Base Classes
```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel

class MyActionParams(BaseModel):
    input_key: str = Field(..., description="Input dataset key")
    output_key: str = Field(..., description="Output dataset key")

@register_action("MY_ENTITY_ACTION_NAME")
class MyEntityAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # Type-safe implementation
        pass
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

## Enhanced Testing Structure

### Test Organization
```
tests/unit/core/strategy_actions/
├── entities/
│   ├── proteins/
│   │   ├── annotation/
│   │   │   ├── test_extract_uniprot_from_xrefs.py
│   │   │   └── test_normalize_accessions.py
│   │   └── matching/
│   │       └── test_multi_bridge.py
│   ├── metabolites/
│   └── chemistry/
├── algorithms/
└── utils/
```

### Testing Commands
```bash
# Test specific action
poetry run pytest -xvs tests/unit/core/strategy_actions/entities/proteins/annotation/test_extract_uniprot.py

# Test entity category
poetry run pytest -xvs tests/unit/core/strategy_actions/entities/proteins/annotation/

# Test entire entity
poetry run pytest -xvs tests/unit/core/strategy_actions/entities/proteins/

# Test all actions
poetry run pytest -xvs tests/unit/core/strategy_actions/
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

## Code Review Checklist (Enhanced)

Before submitting a new action:

- [ ] **Organization**: Action placed in correct entity/category directory
- [ ] **Typing**: Uses TypedStrategyAction with Pydantic models
- [ ] **Registration**: Properly registered with @register_action decorator
- [ ] **Imports**: Added to appropriate __init__.py files
- [ ] **Testing**: Comprehensive tests in matching directory structure
- [ ] **Documentation**: Entity-specific docstrings with examples
- [ ] **Algorithms**: Uses shared algorithms where appropriate
- [ ] **Utilities**: Leverages shared utilities for common operations
- [ ] **Performance**: Considers chunking for large datasets
- [ ] **Validation**: Pydantic models validate all parameters
- [ ] **Error Handling**: Comprehensive error handling and logging
- [ ] **Compatibility**: Maintains backward compatibility

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