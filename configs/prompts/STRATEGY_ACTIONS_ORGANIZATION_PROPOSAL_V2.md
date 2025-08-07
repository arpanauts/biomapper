# Strategy Actions Directory Organization Proposal v2
## (Incorporating Gemini Feedback)

## Current Problem

The `/home/ubuntu/biomapper/biomapper/core/strategy_actions/` directory uses a flat structure with all 20+ actions in a single directory. With 12+ new entity-specific actions planned, this will become difficult to navigate and maintain.

## Refined Organization (v2 - Enhanced with Gemini Feedback)

### Directory Structure
```
biomapper/core/strategy_actions/
├── __init__.py                     # Main imports and registry loading
├── registry.py                     # ACTION_REGISTRY (unchanged)
├── base.py                         # Base classes (unchanged)
├── typed_base.py                   # Typed base classes (unchanged)
├── CLAUDE.md                       # Action development guidance
│
├── entities/                       # Entity-specific actions
│   ├── __init__.py
│   ├── proteins/                   # Protein-specific actions
│   │   ├── __init__.py
│   │   ├── annotation/             # Protein annotation actions
│   │   │   ├── extract_uniprot_from_xrefs.py
│   │   │   └── normalize_accessions.py
│   │   ├── matching/               # Protein matching strategies
│   │   │   └── multi_bridge.py
│   │   └── structure/              # Future: protein structure actions
│   ├── metabolites/                # Metabolite-specific actions
│   │   ├── __init__.py
│   │   ├── identification/         # ID extraction and normalization
│   │   │   ├── extract_identifiers.py
│   │   │   └── normalize_hmdb.py
│   │   ├── matching/               # Matching strategies
│   │   │   ├── cts_bridge.py
│   │   │   ├── nightingale_nmr_match.py      # Moved from root
│   │   │   ├── semantic_match.py             # Moved from root
│   │   │   ├── vector_enhanced_match.py      # Moved from root
│   │   │   └── combine_matches.py            # Moved from root
│   │   └── enrichment/             # External data enrichment
│   │       └── api_enrichment.py             # Moved from root
│   ├── chemistry/                  # Chemistry-specific actions
│   │   ├── __init__.py
│   │   ├── identification/         # Clinical chemistry ID handling
│   │   │   └── extract_loinc.py
│   │   ├── matching/               # Test matching strategies
│   │   │   └── fuzzy_test_match.py
│   │   └── harmonization/          # Vendor differences
│   │       └── vendor_harmonization.py
│   └── genes/                      # Future: gene-specific actions
│       └── __init__.py
│
├── algorithms/                     # Independent, reusable algorithms
│   ├── __init__.py
│   ├── fuzzy_matching/             # Fuzzy matching algorithms
│   │   ├── __init__.py
│   │   ├── string_similarity.py
│   │   └── semantic_similarity.py
│   ├── normalization/              # ID normalization algorithms
│   │   ├── __init__.py
│   │   ├── identifier_patterns.py
│   │   └── format_standardizers.py
│   └── validation/                 # Data validation algorithms
│       ├── __init__.py
│       └── biological_validators.py
│
├── utils/                          # General utility functions
│   ├── __init__.py
│   ├── data_processing/            # Data manipulation utilities
│   │   ├── __init__.py
│   │   ├── chunk_processor.py
│   │   ├── filter_dataset.py
│   │   └── data_validators.py
│   ├── io_helpers/                 # File I/O utilities
│   │   ├── __init__.py
│   │   ├── file_readers.py
│   │   └── format_converters.py
│   └── logging/                    # Logging utilities
│       ├── __init__.py
│       └── action_logger.py
│
├── workflows/                      # High-level workflow actions
│   ├── __init__.py
│   ├── merge_with_uniprot_resolution.py  # Moved from root
│   ├── calculate_set_overlap.py          # Moved from root
│   ├── calculate_three_way_overlap.py    # Moved from root
│   └── merge_datasets.py                 # Moved from root
│
├── io/                            # Data input/output actions
│   ├── __init__.py
│   ├── load_dataset_identifiers.py      # Moved from root
│   └── export_dataset.py                # To be created
│
├── reports/                       # Reporting and analysis
│   ├── __init__.py
│   ├── generate_metabolomics_report.py  # Moved from root
│   └── generate_enhancement_report.py   # Moved from root
│
├── deprecated/                    # Legacy actions (for reference)
│   ├── __init__.py
│   ├── format_and_save_results_action_old.py
│   └── load_endpoint_identifiers_action_old.py
│
└── reference/                     # Reference data and documentation
    ├── METABOLOMICS_ALIASES.md           # Moved from root
    ├── biological_patterns.py           # ID patterns and validation
    └── entity_schemas.py                # Pydantic models for entities
```

## Key Improvements from Gemini Feedback

### 1. Enhanced Entity Organization
- **Sub-categorization**: Each entity type (proteins, metabolites, chemistry) has functional subdirectories
- **Future-ready**: Structure supports additional entity types (genes, pathways, diseases)
- **Logical grouping**: Actions grouped by function within entity types

### 2. Separation of Concerns
- **`algorithms/`**: Independent, reusable algorithms (not actions)
- **`utils/`**: General utility functions used across multiple actions
- **Clear distinction**: Actions vs utilities vs algorithms

### 3. Better Scalability Support
- **Modular algorithms**: Fuzzy matching, normalization, validation as separate modules
- **Utility organization**: Data processing, I/O helpers, logging separated
- **Dependency clarity**: Clear hierarchy of dependencies

## Refined Naming Convention

### File Naming (Pythonic)
```python
# More readable, less verbose than original proposal
extract_uniprot_from_xrefs.py     # verb_object_from_source
normalize_hmdb_ids.py             # verb_object_type  
match_via_fuzzy_string.py         # verb_via_method
```

### Action Registration (Consistent with existing)
```python
# Keep existing all-caps pattern for consistency
@register_action("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS")
@register_action("METABOLITE_NORMALIZE_HMDB")
@register_action("CHEMISTRY_FUZZY_TEST_MATCH")
```

### Function/Class Names (snake_case)
```python
# Internal functions use snake_case
def extract_uniprot_ids(xrefs_field: str) -> List[str]:
def normalize_hmdb_format(hmdb_id: str) -> str:

class ProteinExtractUniprotFromXrefs(TypedStrategyAction):
```

## Enhanced Import Strategy

### Main __init__.py (Automatic Registration)
```python
# biomapper/core/strategy_actions/__init__.py

# Import registry first
from . import registry

# Entity-specific imports (triggers action registration)
from .entities import *

# Algorithm imports (for use by actions)
from .algorithms import *

# Utility imports (for use by actions)
from .utils import *

# Workflow imports
from .workflows import *

# IO imports  
from .io import *

# Reports imports
from .reports import *

# Export registry and key utilities
__all__ = ['registry']
```

### Entity-specific imports with sub-organization
```python
# biomapper/core/strategy_actions/entities/proteins/__init__.py

# Import all protein action subdirectories
from .annotation import *  # extract_uniprot, normalize_accessions
from .matching import *    # multi_bridge
# from .structure import * # Future expansion

__all__ = []  # Actions register themselves
```

## Addressing Gemini's Scalability Concerns

### 1. Dependency Management
```yaml
# Already using Poetry - pyproject.toml handles this
[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.0"
pandas = "^2.0"
# ... existing dependencies
```

### 2. Configuration Management
```python
# Enhanced action parameters with configuration support
class ProteinExtractUniprotParams(BaseModel):
    # Direct parameters
    input_key: str
    output_key: str
    
    # Configuration-driven parameters
    extraction_patterns: Dict[str, List[str]] = Field(
        default_factory=lambda: load_config("protein_patterns.yaml")
    )
    validation_rules: ValidationConfig = Field(
        default_factory=ValidationConfig
    )
```

### 3. Enhanced Documentation Strategy
```python
# biomapper/core/strategy_actions/entities/proteins/__init__.py
"""
Protein-specific actions for biomapper.

This module provides a comprehensive suite of protein identifier processing,
normalization, and matching capabilities for biological data harmonization.

Submodules:
    annotation: UniProt extraction, accession normalization
    matching: Multi-bridge resolution strategies
    structure: Protein structure analysis (future)

Common Patterns:
    UniProt: P12345, O00533 (6-character accessions)
    Ensembl: ENSP00000123456 (protein IDs)
    Gene symbols: CD4, TP53 (HGNC official symbols)

Example Usage:
    # Extract UniProt IDs from KG2c xrefs field
    action = ProteinExtractUniprotFromXrefs()
    result = await action.execute(params, context)
    
    # Normalize extracted accessions
    normalize_action = ProteinNormalizeAccessions()
    normalized = await normalize_action.execute(norm_params, context)
"""
```

### 4. CLI and Testing Integration
```python
# Enhanced testing with entity-specific test suites
# tests/unit/core/strategy_actions/entities/proteins/test_extract_uniprot.py

class TestProteinExtractUniprot:
    """Comprehensive tests for UniProt extraction."""
    
    @pytest.fixture
    def sample_kg2c_data(self):
        """Sample KG2c protein data with xrefs."""
        return load_test_data("kg2c_proteins_sample.csv")
    
    def test_extract_standard_uniprot_format(self, sample_kg2c_data):
        """Test extraction of standard UniProt:P12345 format."""
        # TDD test implementation
        pass
```

## Migration Strategy (Refined)

### Phase 1: Create Enhanced Structure (Week 1)
1. Create new directory structure with sub-organization
2. Create `algorithms/` and `utils/` directories
3. Update main `__init__.py` with enhanced import strategy
4. Test backward compatibility

### Phase 2: Move and Reorganize Existing Actions (Week 2)
1. Move metabolite actions to `entities/metabolites/matching/`
2. Move workflow actions to `workflows/`
3. Extract common algorithms to `algorithms/`
4. Extract utilities to `utils/`
5. Update all imports and test thoroughly

### Phase 3: Add New Entity-Specific Actions (Weeks 3-6)
1. Add protein actions to `entities/proteins/annotation/` and `matching/`
2. Add chemistry actions to `entities/chemistry/` subdirectories
3. Add shared utilities to `utils/data_processing/`
4. Implement enhanced configuration support

### Phase 4: Documentation and Polish (Week 7)
1. Update all module docstrings with comprehensive examples
2. Create per-entity developer guides
3. Add reference patterns documentation
4. Implement enhanced logging and CLI features

## Benefits of Enhanced Organization

### For Bioinformatics Domain
- **Entity expertise**: Clear biological specialization areas
- **Algorithm reuse**: Common bioinformatics algorithms available to all actions
- **Pattern recognition**: Biological ID patterns centralized
- **Validation consistency**: Standardized validation across entity types

### For Software Architecture  
- **Separation of concerns**: Actions, algorithms, utilities clearly distinguished
- **Dependency clarity**: Clear hierarchy and relationships
- **Testing isolation**: Entity-specific test suites
- **Scalability**: Ready for new entity types and algorithms

### For Developer Experience
- **Intuitive navigation**: Logical entity-based organization
- **Code reuse**: Algorithms and utilities prevent duplication
- **Documentation discoverability**: Clear per-entity guides
- **Onboarding efficiency**: New developers can focus on specific entity types

## Success Metrics (Enhanced)

### Immediate (Weeks 1-2)
- [ ] All existing actions load correctly after reorganization
- [ ] Backward compatibility maintained for all client code
- [ ] Enhanced import system works correctly
- [ ] Test suite passes with new structure

### Medium-term (Weeks 3-6)
- [ ] New entity-specific actions integrate smoothly
- [ ] Algorithm reuse reduces code duplication
- [ ] Developer onboarding time reduced by 50%
- [ ] Testing isolation enables parallel development

### Long-term (Weeks 7+)
- [ ] New entity types easily added (genes, pathways)
- [ ] Algorithm library grows and benefits all actions
- [ ] Documentation scales with framework growth
- [ ] Framework supports 100+ actions without navigation issues

---

**This enhanced proposal addresses Gemini's feedback while maintaining the successful patterns from the biomapper strategy organization system.**