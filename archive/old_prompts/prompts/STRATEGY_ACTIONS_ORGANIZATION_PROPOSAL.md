# Strategy Actions Directory Organization Proposal

## Current Problem

The `/home/ubuntu/biomapper/biomapper/core/strategy_actions/` directory currently uses a flat structure with all 20+ actions in a single directory. With 12+ new entity-specific actions planned, this will become difficult to navigate and maintain.

## Proposed Organization (Based on biomapper-strategy-developer.md patterns)

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
│   │   ├── extract_uniprot_from_xrefs.py
│   │   ├── normalize_accessions.py
│   │   └── multi_bridge.py
│   ├── metabolites/                # Metabolite-specific actions
│   │   ├── __init__.py
│   │   ├── extract_identifiers.py
│   │   ├── normalize_hmdb.py
│   │   ├── cts_bridge.py
│   │   ├── nightingale_nmr_match.py      # Moved from root
│   │   ├── semantic_match.py             # Moved from root
│   │   ├── vector_enhanced_match.py      # Moved from root
│   │   ├── combine_matches.py            # Moved from root
│   │   └── api_enrichment.py             # Moved from root
│   ├── chemistry/                  # Chemistry-specific actions
│   │   ├── __init__.py
│   │   ├── extract_loinc.py
│   │   ├── fuzzy_test_match.py
│   │   └── vendor_harmonization.py
│   └── shared/                     # Cross-entity utilities
│       ├── __init__.py
│       ├── filter_dataset.py
│       └── chunk_processor.py
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
    └── data_patterns.py                  # Biological ID patterns
```

### Naming Convention for Actions

#### File Naming Pattern:
```
[verb]_[object]_[modifier].py
```

**Examples:**
- `extract_uniprot_from_xrefs.py` (verb_object_from_source)
- `normalize_hmdb_ids.py` (verb_object_type)
- `match_via_fuzzy_string.py` (verb_via_method)

#### Action Class Naming Pattern:
```
[ENTITY]_[VERB]_[OBJECT]_[METHOD]
```

**Examples:**
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`
- `METABOLITE_NORMALIZE_HMDB`
- `CHEMISTRY_FUZZY_TEST_MATCH`

### Import Strategy

#### Main __init__.py (Automatic Registration)
```python
# biomapper/core/strategy_actions/__init__.py

# Import all action modules to trigger registration
from . import registry

# Entity-specific imports
from .entities.proteins import *
from .entities.metabolites import *
from .entities.chemistry import *
from .entities.shared import *

# Workflow imports
from .workflows import *

# IO imports
from .io import *

# Reports imports
from .reports import *

# Export registry for external access
__all__ = ['registry']
```

#### Entity-specific __init__.py files
```python
# biomapper/core/strategy_actions/entities/proteins/__init__.py

# Import all protein actions to trigger registration
from .extract_uniprot_from_xrefs import *
from .normalize_accessions import *
from .multi_bridge import *

__all__ = []  # Actions register themselves
```

### Documentation Strategy

#### CLAUDE.md Structure
```markdown
# Strategy Actions Development Guide

## Organization Principles

### Entity-Based Organization
- **proteins/**: UniProt, Ensembl, gene symbol handling
- **metabolites/**: HMDB, InChIKey, CHEBI, KEGG, PubChem handling  
- **chemistry/**: LOINC, test name fuzzy matching, vendor harmonization
- **shared/**: Generic utilities (filtering, chunking, validation)

### Action Naming Conventions
[Detailed naming guide...]

### Import Guidelines
[How to properly import and register actions...]
```

#### Per-Entity Documentation
```python
# biomapper/core/strategy_actions/entities/proteins/__init__.py
"""
Protein-specific actions for biomapper.

This module contains actions for handling protein identifier mapping,
normalization, and bridge resolution.

Available Actions:
- PROTEIN_EXTRACT_UNIPROT_FROM_XREFS: Extract UniProt IDs from xrefs fields
- PROTEIN_NORMALIZE_ACCESSIONS: Standardize UniProt accession formats
- PROTEIN_MULTI_BRIDGE: Multi-strategy protein matching

Data Patterns:
- UniProt: P12345, O00533 (6-character format)
- Ensembl: ENSP00000123456 (protein IDs)
- Gene symbols: CD4, TP53 (official HGNC symbols)

Usage Example:
    @register_action("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS")
    class ProteinExtractUniprotFromXrefs(TypedStrategyAction):
        ...
"""
```

## Migration Strategy

### Phase 1: Create Structure (Week 1)
1. Create new directory structure
2. Update main `__init__.py` with new import strategy
3. Create entity-specific `__init__.py` files
4. Test that existing actions still load correctly

### Phase 2: Move Existing Actions (Week 2)
1. Move metabolite actions to `entities/metabolites/`
2. Move workflow actions to `workflows/`
3. Move I/O actions to `io/`
4. Move deprecated actions to `deprecated/`
5. Update all imports and test

### Phase 3: Add New Actions (Weeks 3-6)
1. Add protein actions to `entities/proteins/`
2. Add chemistry actions to `entities/chemistry/`
3. Add shared utilities to `entities/shared/`
4. Add missing I/O actions

### Phase 4: Documentation (Week 7)
1. Update all CLAUDE.md files
2. Add per-entity documentation
3. Create reference patterns documentation
4. Update developer guides

## Benefits of This Organization

### For Developers
- **Clear separation**: Entity-specific logic isolated
- **Easy navigation**: Find actions by biological entity type
- **Scalability**: Can add more entity types (genes, pathways, diseases)
- **Maintenance**: Related actions grouped together

### For Biomapper Framework
- **Import efficiency**: Only load needed action categories
- **Testing**: Test entity types independently
- **Documentation**: Clear per-entity developer guides
- **Future growth**: Ready for new biological entity types

### For Strategy Development  
- **Action discovery**: Easier to find relevant actions
- **Entity-specific expertise**: Clear specialization areas
- **Pattern recognition**: Similar actions grouped together
- **Template reuse**: Entity-specific action templates

## Compatibility Considerations

### Backward Compatibility
- All existing imports continue to work
- Registry system unchanged
- Action names unchanged
- Client code unaffected

### Forward Compatibility
- New entity types easily added
- Action templates per entity type
- Consistent patterns across entities
- Documentation scales with organization

## Implementation Priority

**HIGH PRIORITY (Essential for parallel development):**
1. Create `entities/` structure for new actions
2. Create shared utilities structure
3. Update main `__init__.py` imports

**MEDIUM PRIORITY (Quality of life):**
1. Move existing actions to appropriate directories
2. Create entity-specific documentation
3. Add reference patterns documentation

**LOW PRIORITY (Polish):**
1. Move deprecated actions
2. Create advanced templates
3. Add cross-entity pattern analysis

## Success Metrics

### Organization Success
- [ ] All actions load correctly after reorganization
- [ ] New actions can be added in logical locations
- [ ] Developer onboarding time reduced
- [ ] Action discovery improved

### Development Success  
- [ ] Parallel development enabled
- [ ] Entity-specific expertise clear
- [ ] Testing isolation achieved
- [ ] Documentation scalable

---

This organization mirrors the successful strategy organization patterns while addressing the unique needs of the growing action codebase.