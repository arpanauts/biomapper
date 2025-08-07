# Biomapper Pattern Investigation Report (Revised)
## Entity-Specific Action Design Based on 21 Mapping Analysis

**Date**: 2025-08-07  
**Analyst**: Claude Code Investigation  
**Collaborator**: Gemini (Bridge Resolution & Performance Design)  
**Total Mappings Analyzed**: 21 (6 Proteins, 10 Metabolites, 5 Chemistries)

---

## Executive Summary

This investigation analyzed 21 biological dataset mappings to identify missing actions. After initial analysis suggested generic actions with 85% code reduction, further review with Gemini revealed that **entity-specific actions** are more realistic due to the inherent complexity of biological data.

### Key Findings (Realistic Assessment)
- **Workflow pattern confirmed**: Extract → Normalize → Match applies to all entities
- **Implementation differs significantly**: Each entity type needs specialized handling  
- **Realistic code reduction**: 45-50% (not 85% as initially hoped)
- **Recommendation**: Build entity-specific actions, extract common patterns later if they emerge

---

## Why Entity-Specific Actions?

Gemini's key insight: **"The process is similar, but implementation details differ significantly"**

### Biological Reality Check
- **Proteins**: UniProt IDs with checksums, isoforms, versions
- **Metabolites**: HMDB padding issues, InChIKey validation, multiple ID systems
- **Chemistries**: Fuzzy matching is primary, vendor-specific formats, LOINC variations

### Development Benefits
1. **Clearer code**: `PROTEIN_EXTRACT_UNIPROT` vs generic `EXTRACT_FIELD`
2. **Simpler parameters**: No complex configuration for all cases
3. **Faster development**: 4 hours for specific vs 10+ hours for generic
4. **Better testing**: Focused test cases
5. **Easier maintenance**: Change proteins without breaking metabolites

---

## Revised Action Catalog

### Protein-Specific Actions (Week 1 Focus)

```yaml
PROTEIN_EXTRACT_UNIPROT_FROM_XREFS:
  purpose: "Extract UniProt IDs from compound xrefs field"
  priority: "CRITICAL - Blocks all 6 protein strategies"
  
  handles_specifically:
    - "Pattern: UniProtKB:([A-Z0-9]+)"
    - "Isoforms: P12345-1 → P12345"
    - "Versions: P12345.2 → P12345"
    - "Multiple IDs per row"
  
  parameters:
    input_key: str
    output_key: str
    keep_isoforms: bool  # Default false
    validate_checksum: bool  # UniProt-specific validation
    
  realistic_time: "4 hours with testing"
  
PROTEIN_NORMALIZE_ACCESSIONS:
  purpose: "UniProt-specific normalization"
  
  handles:
    - "Case: p12345 → P12345"
    - "Trembl/Swiss-Prot prefixes"
    - "Obsolete ID resolution"
    
  realistic_time: "3 hours"

PROTEIN_MULTI_BRIDGE:
  purpose: "Protein-specific bridge resolution"
  
  bridges:
    1: "UniProt exact (90% success)"
    2: "Gene symbol (adds 8%)"
    3: "Ensembl (adds 2%)"
    
  realistic_time: "6 hours"
```

### Metabolite-Specific Actions (Week 2)

```yaml
METABOLITE_EXTRACT_IDENTIFIERS:
  purpose: "Extract multiple metabolite ID types"
  priority: "HIGH - Blocks 10 metabolite strategies"
  
  handles_specifically:
    - "HMDB with various formats (HMDB01234, HMDB0001234, 1234)"
    - "InChIKey validation"
    - "CHEBI, KEGG, PubChem IDs"
    - "Synonyms field parsing"
  
  parameters:
    input_key: str
    id_types: List[str]  # ["hmdb", "inchikey", "chebi"]
    source_columns: Dict[str, str]  # {"hmdb": "xrefs", "inchikey": "synonyms"}
    output_key: str
    
  realistic_time: "6 hours (more complex than proteins)"

METABOLITE_NORMALIZE_HMDB:
  purpose: "HMDB-specific padding and format"
  
  handles:
    - "Padding: HMDB1234 → HMDB0001234"
    - "Version handling"
    - "Secondary accessions"
    
  realistic_time: "3 hours"

METABOLITE_CTS_BRIDGE:
  purpose: "Chemical Translation Service integration"
  
  handles:
    - "Batch API calls"
    - "Multiple ID type conversions"
    - "Timeout handling"
    
  realistic_time: "8 hours (external API complexity)"
```

### Chemistry-Specific Actions (Week 3)

```yaml
CHEMISTRY_EXTRACT_LOINC:
  purpose: "Extract LOINC codes from various formats"
  priority: "MEDIUM - Blocks 5 chemistry strategies"
  
  handles_specifically:
    - "LOINC variations: 1759-0, 1759, LP1759-0"
    - "Vendor-specific codes"
    - "Test name extraction"
  
  realistic_time: "4 hours"

CHEMISTRY_FUZZY_TEST_MATCH:
  purpose: "Fuzzy matching for test names"
  
  handles:
    - "Abbreviations: A/G ratio, AG ratio, A:G"
    - "Synonyms: glucose, blood sugar, FBS"
    - "Units: mg/dL, mmol/L"
    
  note: "This is PRIMARY matching for chemistry, not fallback"
  realistic_time: "8 hours (most complex matching)"

CHEMISTRY_VENDOR_HARMONIZATION:
  purpose: "Handle LabCorp vs Quest vs others"
  
  realistic_time: "6 hours"
```

### Shared Infrastructure (Still Generic)

```yaml
CHUNK_PROCESSOR:
  purpose: "Wrap any action for memory-safe processing"
  works_with: "All entity-specific actions"
  realistic_time: "4 hours"
  
FILTER_DATASET:
  purpose: "Simple filtering (generic enough)"
  realistic_time: "2 hours"

EXPORT_DATASET:
  purpose: "Standard output formats"
  realistic_time: "2 hours"
```

---

## Realistic Implementation Timeline

### Week 1: Proteins Only (Proof of Concept)
**Goal**: Get protein mappings working end-to-end

Day 1-2:
- PROTEIN_EXTRACT_UNIPROT_FROM_XREFS (4 hours)
- PROTEIN_NORMALIZE_ACCESSIONS (3 hours)

Day 3-4:
- PROTEIN_MULTI_BRIDGE (6 hours)
- FILTER_DATASET (generic) (2 hours)

Day 5:
- Test with real protein strategies
- Document lessons learned

**Success Metric**: 3+ protein strategies working

### Week 2: Metabolites (Apply Lessons)
**Goal**: Adapt patterns for metabolite complexity

Day 1-3:
- METABOLITE_EXTRACT_IDENTIFIERS (6 hours)
- METABOLITE_NORMALIZE_HMDB (3 hours)
- Test extraction patterns

Day 4-5:
- METABOLITE_CTS_BRIDGE (8 hours)
- Integration testing

**Success Metric**: 5+ metabolite strategies working

### Week 3: Chemistry (Most Different)
**Goal**: Handle fuzzy matching complexity

Day 1-2:
- CHEMISTRY_EXTRACT_LOINC (4 hours)
- CHEMISTRY_FUZZY_TEST_MATCH (8 hours)

Day 3-4:
- CHEMISTRY_VENDOR_HARMONIZATION (6 hours)
- Integration testing

Day 5:
- CHUNK_PROCESSOR wrapper (4 hours)
- Performance testing

**Success Metric**: 3+ chemistry strategies working

### Week 4: Optimization & Common Patterns
**Goal**: Extract any common patterns, optimize

- Look for real (not forced) common patterns
- Create base classes only if truly beneficial
- Performance optimization
- Documentation

---

## Code Reduction Reality

### Original Estimate vs Reality

| Metric | Original Estimate | Realistic Estimate | Still Valuable? |
|--------|------------------|-------------------|-----------------|
| Within entity type | 85% | 60-70% | Yes! |
| Across entity types | 85% | 30-40% | Yes |
| Total reduction | 85% | 45-50% | Definitely |
| Development time | 2 weeks | 4 weeks | Worth it |

### Where Reduction Comes From
- **Within entity**: Eliminating duplicate extraction/normalization code
- **Across entities**: Shared infrastructure (chunking, filtering, export)
- **Future benefit**: Clear patterns for new entity types

---

## Key Implementation Principles

1. **Start Specific, Generalize Later**
   - Build what works for proteins
   - Don't anticipate metabolite needs
   - Extract patterns after all three work

2. **Embrace the Differences**
   - UniProt checksums are protein-specific
   - HMDB padding is metabolite-specific
   - Fuzzy matching is chemistry-primary

3. **Test with Real Data Early**
   - Use actual xrefs from KG2c
   - Test with known edge cases
   - Get user feedback quickly

4. **Document Entity-Specific Patterns**
   - Why proteins need checksum validation
   - Why metabolites need multiple ID types
   - Why chemistry needs fuzzy as primary

---

## Success Metrics (Revised)

✅ **Week 1**: 3+ protein strategies working  
✅ **Week 2**: 5+ metabolite strategies working  
✅ **Week 3**: 3+ chemistry strategies working  
✅ **Week 4**: 45-50% code reduction achieved  
✅ **Performance**: <5 min for 100k rows (with chunking)  
✅ **Maintainability**: Entity changes don't break others  
✅ **Clarity**: Junior dev can understand code  

---

## Risk Mitigation

### What Could Go Wrong
1. **Chemistry fuzzy matching too complex**: Budget extra time
2. **External APIs (CTS) unreliable**: Build fallback/cache
3. **Memory issues earlier than expected**: Implement chunking sooner
4. **Patterns don't emerge**: Accept entity-specific is okay

### Mitigation Strategies
- Build simplest version first
- Test with real data immediately
- Get user feedback each week
- Don't force pattern extraction

---

## Recommendations

1. **Start with proteins** - Best understood, clearest patterns
2. **Build entity-specific** - Don't force generalization
3. **Accept 50% reduction** - Still very valuable
4. **Test weekly** - Get feedback early
5. **Document differences** - Help future developers understand why

---

## Conclusion

The investigation correctly identified missing actions and workflow patterns. However, biological data complexity requires entity-specific implementations rather than generic actions. This approach will:
- Deliver working solutions faster (Week 1 vs Week 3)
- Produce clearer, more maintainable code
- Still achieve meaningful code reduction (45-50%)
- Allow patterns to emerge naturally rather than forcing them

**Next Step**: Implement `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` using the pattern from ukbb_to_kg2c_proteins.yaml

---

*Report Version 2.0 - Adjusted for Realistic Implementation*