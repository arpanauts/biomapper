# Metabolite Mapping Strategy Development - Learning from Protein Mapping

## Executive Summary

You are about to embark on developing metabolite mapping strategies for the biomapper project. This document captures critical lessons learned from implementing protein mapping strategies, helping you avoid pitfalls and accelerate development.

## What is Biomapper?

Biomapper is a bioinformatics pipeline for harmonizing biological identifiers across heterogeneous datasets. It uses a **strategy-action pattern** where:
- **Strategies** are YAML files defining sequential steps
- **Actions** are Python classes that process data
- **Context** is a shared dictionary that flows between actions

## Critical Lessons from Protein Mapping

### 1. The Context Problem (Our Biggest Challenge)

**What Went Wrong:**
- Actions couldn't share data properly
- TypedStrategyAction created MockContext wrappers that didn't sync
- Dict vs StrategyExecutionContext incompatibility caused silent failures

**The Solution:**
```python
# Always handle multiple context types in your actions
if isinstance(context, dict):
    ctx = context
elif hasattr(context, '_dict'):  # MockContext
    ctx = context._dict
else:  # StrategyExecutionContext
    ctx = adapt_context(context)
```

**For Metabolites:** Start with this pattern from day one. Don't assume context type.

### 2. Data Format Consistency

**What We Learned:**
- Actions receive data as **list of dicts**, not DataFrames
- Always convert: `df = pd.DataFrame(data)` when needed
- Store back as: `ctx["datasets"][key] = df.to_dict("records")`

**For Metabolites:** Maintain this convention religiously. It ensures interoperability.

### 3. Composite Identifiers Are Everywhere

**Protein Example:** "Q8NEV9,Q14213" (comma-separated UniProt IDs)

**Metabolite Reality:** Even worse!
- Multiple HMDB IDs: "HMDB0000001,HMDB0000002"
- Synonym lists: "Glucose;D-Glucose;Dextrose"
- Cross-references: "CHEBI:17234|KEGG:C00031|CAS:50-99-7"

**Solution Pattern:**
```python
def parse_composite_metabolites(identifier: str) -> List[str]:
    """Handle various separators in metabolite IDs."""
    separators = [",", ";", "|", "/"]
    for sep in separators:
        if sep in identifier:
            return [id.strip() for id in identifier.split(sep)]
    return [identifier]
```

### 4. One-to-Many Mapping Tracking

**Why It Matters:**
- Single metabolite → multiple database entries
- Affects statistics (expansion factor)
- Impacts downstream analysis

**Implementation:**
```python
# Track in statistics
ctx["statistics"]["metabolite_mapping"] = {
    "one_to_many_count": 47,
    "expansion_factor": 1.23,
    "ambiguous_metabolites": ["Glucose", "ATP", "NAD+"]
}
```

### 5. Progressive Mapping Strategy

**Protein Approach (65-70% success):**
1. Direct match
2. Normalization
3. Historical resolution
4. Gene symbol bridge

**Metabolite Approach (Recommended):**
```yaml
steps:
  1. Direct HMDB match
  2. InChIKey exact match
  3. CTS (Chemical Translation Service) lookup
  4. Name/synonym fuzzy matching
  5. SMILES structure similarity
  6. Semantic embedding match
  7. Manual curation candidates
```

### 6. Parameter Mismatches Kill Strategies

**Common Failures:**
- YAML: `input_key` vs Action expects: `dataset_key`
- YAML: `output_file` vs Action expects: `output_path`

**Prevention:**
1. Write tests FIRST (TDD)
2. Use Pydantic models with clear field names
3. Document parameter names in action docstrings

## Metabolite-Specific Considerations

### Available Metabolite Actions (Already Working!)

Located in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/metabolites/`:

1. **NIGHTINGALE_NMR_MATCH** - Nightingale platform biomarker matching
2. **CTS_ENRICHED_MATCH** - Chemical Translation Service integration
3. **METABOLITE_API_ENRICHMENT** - External API enrichment (PubChem, HMDB)
4. **SEMANTIC_METABOLITE_MATCH** - AI-powered name matching
5. **VECTOR_ENHANCED_MATCH** - Embedding-based similarity
6. **COMBINE_METABOLITE_MATCHES** - Merge results from multiple approaches

### Metabolite Identifier Landscape

```python
METABOLITE_ID_PATTERNS = {
    'HMDB': r'^HMDB\d{7}$',           # HMDB0000001
    'CHEBI': r'^CHEBI:\d+$',          # CHEBI:17234
    'KEGG': r'^C\d{5}$',              # C00031
    'InChIKey': r'^[A-Z]{14}-[A-Z]{10}-[A-Z]$',  # RYYVLZVUVIJVGH-UHFFFAOYSA-N
    'CAS': r'^\d{2,7}-\d{2}-\d$',     # 50-99-7
    'PubChem': r'^CID\d+$',           # CID5793
}
```

### Chemical Structure Considerations

Metabolites have structural information that proteins lack:
- SMILES strings for structure
- InChI for unique identification
- Molecular formula for validation
- Stereochemistry matters!

## TDD Approach (Non-Negotiable!)

### Step 1: Write Test FIRST
```python
# tests/unit/core/strategy_actions/entities/metabolites/test_your_action.py
class TestMetaboliteAction:
    def test_handles_hmdb_ids(self):
        """Test HMDB ID extraction and normalization."""
        assert extract_hmdb("HMDB0000001") == "HMDB0000001"
        assert extract_hmdb("HMDB00001") == "HMDB0000001"  # Normalize
        
    def test_handles_composite_ids(self):
        """Test composite metabolite ID parsing."""
        result = parse_metabolite_ids("HMDB0000001,HMDB0000002")
        assert len(result) == 2
```

### Step 2: Run Test (Expect Failure)
```bash
poetry run pytest tests/unit/core/strategy_actions/entities/metabolites/test_your_action.py -xvs
```

### Step 3: Implement Minimal Code

### Step 4: Refactor with Safety

## Common Metabolite Mapping Challenges

### 1. Name Variability
- "Vitamin C" vs "L-Ascorbic acid" vs "Ascorbate"
- Solution: Semantic matching with embeddings

### 2. Stereoisomers
- D-Glucose vs L-Glucose (different HMDB IDs!)
- Solution: Preserve stereochemistry in matching

### 3. Charged States
- "ATP" vs "ATP4-" vs "ATP3-"
- Solution: Normalize to neutral form for matching

### 4. Database Inconsistencies
- HMDB might have different IDs for same compound
- Solution: Use InChIKey as universal identifier

## Recommended Metabolite Strategy Structure

```yaml
name: metabolite_comprehensive_mapping
description: Progressive metabolite harmonization with fallback strategies

parameters:
  source_file: "${SOURCE_FILE}"
  target_file: "${TARGET_FILE}"
  output_dir: "${OUTPUT_DIR}"
  
steps:
  # Stage 1: Direct Matching
  - name: extract_metabolite_ids
    action:
      type: METABOLITE_EXTRACT_IDS
      params:
        dataset_key: "source_raw"
        id_columns: ["metabolite", "compound", "name"]
        output_key: "source_extracted"
        
  - name: parse_composite_metabolites
    action:
      type: PARSE_COMPOSITE_IDENTIFIERS
      params:
        dataset_key: "source_extracted"
        id_field: "metabolite_id"
        separators: [",", ";", "|"]
        output_key: "source_parsed"
        
  # Stage 2: Chemical Translation
  - name: cts_enrichment
    action:
      type: CTS_ENRICHED_MATCH
      params:
        dataset_key: "source_parsed"
        from_format: "name"
        to_format: ["InChIKey", "HMDB", "KEGG"]
        output_key: "cts_enriched"
        
  # Stage 3: Semantic Matching
  - name: semantic_match
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        dataset_key: "cts_enriched"
        reference_key: "target_metabolites"
        threshold: 0.85
        output_key: "semantic_matched"
        
  # Stage 4: Structure-Based Matching
  - name: structure_similarity
    action:
      type: SMILES_SIMILARITY_MATCH
      params:
        dataset_key: "semantic_matched"
        reference_key: "target_structures"
        tanimoto_threshold: 0.9
        output_key: "structure_matched"
        
  # Stage 5: Combine and Report
  - name: combine_results
    action:
      type: COMBINE_METABOLITE_MATCHES
      params:
        dataset_keys: ["cts_enriched", "semantic_matched", "structure_matched"]
        voting_strategy: "weighted"
        weights: [0.4, 0.3, 0.3]
        output_key: "final_mapping"
```

## File Organization for Metabolites

```
biomapper/core/strategy_actions/entities/metabolites/
├── identification/
│   ├── extract_hmdb.py
│   ├── extract_inchikey.py
│   └── parse_metabolite_names.py
├── matching/
│   ├── cts_match.py         # Chemical Translation Service
│   ├── semantic_match.py    # Name/synonym matching
│   ├── structure_match.py   # SMILES/InChI similarity
│   └── vector_match.py      # Embedding-based
├── enrichment/
│   ├── pubchem_api.py
│   ├── hmdb_api.py
│   └── chebi_api.py
└── validation/
    ├── validate_inchi.py
    └── validate_formula.py
```

## Performance Optimization Tips

1. **Batch API Calls**: CTS and PubChem have rate limits
2. **Cache Results**: Store API responses locally
3. **Chunk Large Datasets**: Process in 1000-row batches
4. **Parallel Processing**: Use asyncio for API calls

## Integration Points

### With Existing Systems
- Nightingale NMR platform
- UK Biobank metabolomics
- Clinical chemistry panels (LOINC codes)

### Output Requirements
- Confidence scores for each mapping
- Provenance tracking (which method succeeded)
- Ambiguous mapping reports
- Visualization of mapping coverage

## Real-World Metabolite Data Examples

### What You'll Actually Encounter

```python
# Example from Nightingale NMR platform
{
    "metabolite": "Citrate",  # Common name
    "platform_id": "NGALE_CITRATE_NMR",
    "units": "mmol/L",
    "synonyms": "Citric acid;2-Hydroxypropane-1,2,3-tricarboxylic acid"
}

# Example from UK Biobank
{
    "field_id": "23400",
    "description": "Glucose",
    "hmdb": "HMDB0000122,HMDB0003345",  # Multiple IDs for different forms!
    "kegg": "C00031",
    "chebi": "CHEBI:17234"
}

# Example problematic entry
{
    "name": "3-Hydroxybutyrate",  # Could be D- or L- form
    "measured_as": "Total 3-HB",  # Ambiguous
    "possible_ids": "HMDB0000357;HMDB0000011"  # Both forms
}
```

### Database-Specific Quirks

**HMDB Issues:**
- Version differences (HMDB 4.0 vs 5.0 have different IDs)
- Secondary IDs that redirect
- Missing entries for common metabolites

**KEGG Issues:**
- Generic compounds (C00031) vs specific forms (C00221)
- Glycan entries separate from compounds
- Drug entries mixed with metabolites

**ChEBI Issues:**
- Parent/child relationships complex
- Charges indicated in names inconsistently
- Ontology changes between versions

## Performance Benchmarks from Protein Work

### What to Expect
- **Direct matching**: 45-55% success (worse than proteins' 65-70%)
- **After normalization**: 60-65% success
- **After CTS lookup**: 75-80% success
- **After semantic matching**: 85-88% success
- **Unmappable**: 12-15% (higher than proteins' 8-10%)

### Processing Times (1000 metabolites)
- Direct match: <1 second
- CTS API calls: 30-60 seconds (rate limited)
- Semantic matching: 5-10 seconds
- Structure similarity: 15-20 seconds

## API Rate Limiting Strategies

### CTS (Chemical Translation Service)
```python
import asyncio
from typing import List, Dict

async def batch_cts_lookup(metabolites: List[str], batch_size: int = 10):
    """Batch CTS lookups to respect rate limits."""
    results = []
    for i in range(0, len(metabolites), batch_size):
        batch = metabolites[i:i+batch_size]
        batch_results = await cts_api_call(batch)
        results.extend(batch_results)
        await asyncio.sleep(1)  # 1 second between batches
    return results
```

### Caching Strategy
```python
# Cache API responses locally
CACHE_DIR = Path("/tmp/biomapper_cache/metabolites")
CACHE_EXPIRY = 7 * 24 * 3600  # 7 days

def get_cached_or_fetch(metabolite_id: str) -> Dict:
    cache_file = CACHE_DIR / f"{metabolite_id}.json"
    if cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < CACHE_EXPIRY:
            return json.loads(cache_file.read_text())
    
    # Fetch from API
    result = fetch_from_api(metabolite_id)
    cache_file.write_text(json.dumps(result))
    return result
```

## Validation Strategies for Metabolite Matches

### Confidence Scoring Framework
```python
def calculate_match_confidence(source: Dict, target: Dict) -> float:
    """Multi-factor confidence scoring for metabolite matches."""
    confidence = 0.0
    
    # InChIKey match (highest confidence)
    if source.get('inchikey') == target.get('inchikey'):
        confidence = 1.0
    
    # SMILES similarity (structure-based)
    elif source.get('smiles') and target.get('smiles'):
        similarity = calculate_tanimoto(source['smiles'], target['smiles'])
        confidence = max(confidence, similarity * 0.95)
    
    # Name matching (lower confidence)
    elif fuzzy_match(source.get('name'), target.get('name')) > 0.9:
        confidence = max(confidence, 0.7)
    
    # Penalize for stereochemistry uncertainty
    if 'stereochemistry' in source.get('notes', '').lower():
        confidence *= 0.8
    
    return confidence
```

### Validation Rules
```python
VALIDATION_RULES = {
    'mass_tolerance': 0.01,  # Da
    'formula_must_match': True,
    'charge_state_matters': False,  # Normalize to neutral
    'stereochemistry_required': True,  # For biological contexts
    'minimum_confidence': 0.6
}
```

## Critical Warnings

### ⚠️ Common Pitfalls to Avoid

1. **Don't Trust Names Alone**
   - "Glucose" could mean D-glucose, L-glucose, or glucose-6-phosphate
   - Always verify with structure or database IDs

2. **Lipid Nomenclature is Chaos**
   - "PC(16:0/18:1)" vs "PC(34:1)" - same molecule, different notation
   - Consider using LipidMaps API for standardization

3. **Salts and Hydrates**
   - "Sodium citrate" vs "Citrate" - different HMDB IDs
   - Normalize to free acid/base form when possible

4. **Tautomers**
   - Same compound, different structures
   - InChI handles this, SMILES doesn't always

## Success Metrics

Track these metrics for metabolite mapping:

```python
METABOLITE_METRICS = {
    'total_input': 0,
    'direct_match': 0,
    'cts_resolved': 0,
    'semantic_matched': 0,
    'structure_matched': 0,
    'ambiguous': 0,  # Multiple equally good matches
    'unmapped': 0,
    'confidence_distribution': {
        'high': 0,    # >0.9
        'medium': 0,  # 0.7-0.9
        'low': 0,     # 0.5-0.7
        'uncertain': 0  # <0.5
    }
}
```

## Quick Start Checklist

- [ ] Read this document completely
- [ ] Review existing metabolite actions in `/entities/metabolites/`
- [ ] Set up test environment with `poetry install --with dev`
- [ ] Create test file FIRST (TDD)
- [ ] Implement PARSE_COMPOSITE_IDENTIFIERS for metabolites
- [ ] Test with real metabolite data from `/procedure/data/local_data/`
- [ ] Handle context properly (dict vs MockContext)
- [ ] Track one-to-many mappings
- [ ] Set up caching for API calls
- [ ] Implement confidence scoring
- [ ] Generate comprehensive reports

## Contact and Resources

- Existing metabolite strategies: `/configs/strategies/metabolomics/`
- Test data: `/procedure/data/local_data/MAPPING_ONTOLOGIES/`
- Documentation: `/docs/source/actions/`
- Example working action: `NIGHTINGALE_NMR_MATCH`

## Final Advice

1. **Start Simple**: Get direct HMDB matching working first
2. **Test Early**: Write tests before implementation
3. **Handle Missing Data**: Many metabolites lack identifiers
4. **Document Everything**: Future you will thank you
5. **Ask for Help**: If context issues arise, check protein solutions first

Remember: Metabolites are messier than proteins. Plan for ambiguity, embrace progressive matching, and always track your confidence scores.

Good luck! You're building on a solid foundation - use it wisely.