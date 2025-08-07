# Dataset Investigation Report - Mapping Pattern Analysis

## Mission Statement

You are tasked with conducting a comprehensive investigation of biological datasets and mapping relationships to identify patterns, commonalities, and opportunities for modular action design. This is purely an analytical exercise - you will examine data, document findings, and provide recommendations without implementing any code.

## Current System Constraints (IMPORTANT)

- Actions must work with dict-based context (no Pydantic models for now)
- In-memory job storage limits large dataset processing
- Missing actions (CUSTOM_TRANSFORM, FILTER_DATASET) are blocking strategies
- Simple, generic actions are preferred over complex, specialized ones

## Context Files to Analyze

### Primary Analysis Target
- `/home/ubuntu/biomapper/configs/MIGRATION_CHECKLIST.md` - Contains all 21 mappings to analyze
- `/home/ubuntu/biomapper/configs/mappings_list.csv` - Raw mapping relationships
- `/home/ubuntu/biomapper/configs/STRATEGY_ORGANIZATION_GUIDE.md` - Organizational framework

### Data Sources to Examine
Investigate sample data from each source to understand structure:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/*.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/*.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/*.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/*.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/*.csv`

### Agent Resources
Consider using these specialized agents for deeper analysis:
- `Task biomapper-action-developer` - For designing new action types
- `Task biomapper-strategy-developer` - For strategy optimization patterns

## Investigation Framework (Prioritized)

### PRIORITY 1: Common Data Transformation Needs 🔴
**Why Critical**: These missing pieces (CUSTOM_TRANSFORM, FILTER_DATASET) are blocking protein strategies

#### Focus Areas:
1. **Extracting identifiers from compound fields**
   - Example: UniProt IDs from xrefs column ("UniProtKB:P12345|RefSeq:NP_001234")
   - Document all extraction patterns needed
   - Note which datasets have compound fields

2. **Normalizing identifier formats**
   - Removing/adding prefixes ("P12345" vs "UniProtKB:P12345")
   - Standardizing case and punctuation
   - Handling variants and isoforms (P12345-1 → P12345)

3. **Parsing structured fields**
   - JSON fields
   - Pipe-delimited values
   - Comma-separated lists
   - Nested structures

#### Deliverable for Priority 1:
```yaml
EXTRACT_STRUCTURED_FIELD:
  purpose: "Extract identifiers from compound fields"
  frequency: "8/10 datasets"
  parameters:
    - source_column: "configurable"
    - extraction_method: "regex|json_path|delimiter"
    - target_identifier_type: "uniprot|hmdb|etc"
  implementation_complexity: "Low (dict-based)"
  blocks_strategies: ["prot_arv_to_kg2c", "prot_ukb_to_kg2c"]
```

### PRIORITY 2: Bridge Identifier Patterns 🟡
**Why Important**: Core to the mapping problem

#### Focus Areas:
1. **Identifier coverage analysis**
   - Which identifiers appear across multiple datasets?
   - Coverage statistics (% rows with each ID type)
   - Quality/reliability ranking

2. **Bridge effectiveness**
   - Which IDs serve as reliable bridges?
   - Success rates for each bridge type
   - Fallback options when primary fails

### PRIORITY 3: Action Sequence Patterns 🟢
**Why Useful**: Reveals reusable workflow patterns

#### Focus Areas:
1. **Minimal viable sequences**
   - What's the simplest successful path?
   - Which steps are essential vs optional?

2. **Divergence points**
   - Where do workflows differ by entity type?
   - Can these be parameterized instead?

## Additional Investigation Requirements

### Failure Point Analysis 🚨
Document where current strategies fail:
1. **Data Quality Issues**
   - Missing required columns
   - Inconsistent formats
   - Empty/null values
   - Type mismatches

2. **Action Failures**
   - Which actions are missing?
   - Which throw errors and why?
   - Performance bottlenecks

3. **Recovery Patterns**
   - What's the fallback when primary mapping fails?
   - How to handle partial matches?
   - Error reporting needs

### 3. Collaboration with Gemini

For each pattern identified, collaborate with Gemini to:

```markdown
"I've identified a pattern where [describe pattern]. 

In the biomapper framework:
- Current implementation: [how it's done now]
- Proposed modular action: [your design]
- Reusability across: [which mappings would use it]

Please provide feedback on:
1. Potential edge cases I haven't considered
2. Performance implications of this design
3. Alternative approaches that might be more flexible
4. How this pattern might extend to future mapping types

Context: We're building modular actions for biological data harmonization across proteins, metabolites, and clinical chemistry tests."
```

## Analysis Guidelines

### What TO Document
- ✅ Data patterns observed across datasets
- ✅ Common transformation needs
- ✅ Identifier types and their coverage
- ✅ Repeated workflow sequences
- ✅ Current failure points and blockers
- ✅ Opportunities for reuse and modularity

### What NOT TO Do
- ❌ Don't write any code implementations
- ❌ Don't create new action files
- ❌ Don't modify existing strategies
- ❌ Just observe, analyze, and report findings

## Primary Deliverables

### 1. Action Pattern Catalog (With Implementation Priority)

Structure each action like this:

```yaml
# Action Pattern Entry
EXTRACT_STRUCTURED_FIELD:
  purpose: "Extract identifiers from compound fields"
  frequency: "Found in 8/10 datasets analyzed"
  parameters_needed:
    - source_column: "xrefs, synonyms, etc."
    - extraction_method: "regex|json_path|delimiter"
    - target_identifier_type: "uniprot|hmdb|kegg"
  priority: "HIGH - Blocks protein strategies"
  implementation_complexity: "Low (dict-based)"
  blocked_strategies: 
    - "prot_arv_to_kg2c_uniprot_v1_base"
    - "prot_ukb_to_kg2c_uniprot_v1_base"
  typical_use_cases:
    - "Extracting UniProt IDs from kg2c xrefs column"
    - "Parsing HMDB IDs from metabolite synonyms"
    - "Getting LOINC codes from compound test descriptions"
```

### 2. Strategy Sharing Matrix

Show which actions each strategy would use:

| Action Type | Proteins | Metabolites | Chemistries | Notes |
|------------|----------|-------------|-------------|-------|
| EXTRACT_STRUCTURED_FIELD | ✓ | ✓ | ✓ | Universal need |
| NORMALIZE_IDENTIFIER | ✓ | ✓ | ✓ | Different rules per type |
| BRIDGE_VIA_UNIPROT | ✓ | ○ | ○ | Protein-centric |
| BRIDGE_VIA_CTS | ○ | ✓ | ○ | Metabolite-specific |
| FILTER_BY_CONFIDENCE | ✓ | ✓ | ✓ | Universal need |

Legend: ✓ = Required, ○ = Optional/Not needed

### 3. Implementation Roadmap

```markdown
## Phase 1: Unblock Current Failures (Week 1)
Priority: CRITICAL
Actions:
1. EXTRACT_STRUCTURED_FIELD - Unblocks 6 strategies
2. FILTER_DATASET - Unblocks 4 strategies
3. CUSTOM_TRANSFORM - Unblocks 3 strategies

## Phase 2: Core Transformations (Week 2)
Priority: HIGH
Actions:
1. NORMALIZE_IDENTIFIER_FORMAT
2. PARSE_COMPOUND_FIELD
3. VALIDATE_AND_CLEAN

## Phase 3: Bridge Services (Week 3)
Priority: MEDIUM
Actions:
1. GENERIC_API_BRIDGE
2. BATCH_RESOLUTION
3. CACHE_MANAGER
```

## Investigation Process

### Step 1: Data Survey (2 hours)
- [ ] Examine all source/target file structures
- [ ] Document column naming patterns
- [ ] Identify identifier formats
- [ ] Note data quality issues

### Step 2: Pattern Mining (3 hours)
- [ ] Group mappings by entity type
- [ ] Identify common transformation needs
- [ ] Find repeated identifier bridges
- [ ] Document workflow sequences

### Step 3: Analysis & Synthesis (2 hours)
- [ ] Identify modular opportunities
- [ ] Create reusability matrix
- [ ] Document parameter patterns
- [ ] Note failure points

### Step 4: Gemini Collaboration (1 hour)
- [ ] Present findings for feedback
- [ ] Refine pattern identification
- [ ] Validate observations
- [ ] Consider edge cases

### Step 5: Report Writing (1 hour)
- [ ] Write investigation findings
- [ ] Document pattern catalog
- [ ] Provide recommendations
- [ ] Summarize opportunities

## Success Criteria

Your investigation is successful when:

1. **Pattern Coverage**: 90% of mappings can be implemented using identified patterns
2. **Code Reduction**: Proposed actions reduce total codebase by >50%
3. **Modularity**: No action exceeds 200 lines of code
4. **Reusability**: Each action is used by at least 3 strategies
5. **Clarity**: Another developer can implement from your specifications
6. **Performance**: No performance degradation vs current approach
7. **Extensibility**: Easy to add new entity types or bridge identifiers

## Example Output Format

Your analysis should produce entries like this:

```yaml
# CRITICAL PRIORITY - Blocking current strategies
EXTRACT_STRUCTURED_FIELD:
  purpose: "Extract identifiers from compound/structured fields"
  
  data_evidence:
    - "kg2c_proteins.csv has xrefs column with 'UniProtKB:P12345|RefSeq:NP_001'"
    - "spoke_metabolites.csv has synonyms with 'HMDB0001|ChEBI:12345'"
    - "8 of 10 target datasets have compound identifier fields"
  
  current_failures:
    - "prot_arv_to_kg2c fails at parsing xrefs"
    - "met_isr_to_spoke cannot extract from synonyms"
  
  parameters:
    source_column: "xrefs"  # Configurable
    extraction_method: "regex"  # Options: regex, split, json_path
    pattern: "UniProtKB:(\w+)"  # Configurable pattern
    output_column: "extracted_uniprot"  # Where to store
    
  transformation_logic_needed:
    - "Parse pipe-delimited values"
    - "Extract using regex patterns"
    - "Handle missing/malformed values"
    - "Support multiple extraction methods"
        
  blocked_strategies: 6
  estimated_impact: "Unblocks protein mappings immediately"
  implementation_time: "2 hours"
```

## Notes

- Focus on patterns that appear in 3+ mappings
- Consider future entity types (pathways, diseases)
- Think about cloud/distributed execution
- Keep actions stateless for parallelization
- Document any biomapper-specific constraints
- Consider integration with external services (APIs, databases)

---

*This investigation will establish the foundation for a modular, maintainable, and scalable biomapper action system.*