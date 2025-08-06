# Biological Actions Development Guide

## Overview

This guide helps Claude Code assist developers in creating biologically-aware actions for BioMapper. Each action should handle the inherent complexity of biological data while maintaining scientific rigor.

## Core Biological Data Principles

### 1. Many-to-Many Relationships Are Default
```python
# WRONG: Assuming 1:1 mapping
gene_to_protein = {gene: protein}

# RIGHT: Always expect multiple mappings
gene_to_proteins = defaultdict(list)
for gene, protein in mappings:
    gene_to_proteins[gene].append(protein)
```

### 2. Composite Identifiers Are Common
```python
# Handle protein complexes, gene fusions, metabolite mixtures
def handle_composite(identifier: str) -> List[str]:
    """Q14213_Q8NEV9 → ['Q14213', 'Q8NEV9', 'Q14213_Q8NEV9']"""
    parts = identifier.split('_')
    return parts + [identifier]  # Keep original AND components
```

### 3. Nomenclature Varies by Database
```python
# Metabolite synonyms example
metabolite_names = {
    "glucose": ["D-Glucose", "Dextrose", "C6H12O6", "CHEBI:17234"],
    "lactate": ["L-Lactate", "Lactic acid", "CHEBI:24996", "HMDB0000190"]
}
```

## Domain-Specific Action Patterns

### Metabolomics Actions

#### Pattern: Multi-Source Enrichment
```python
@register_action("METABOLITE_MULTI_ENRICHMENT")
class MetaboliteMultiEnrichment(TypedStrategyAction):
    """Enriches metabolite identifiers using multiple databases."""
    
    async def execute_typed(self, params, context):
        # Try multiple sources in order of reliability
        sources = ["HMDB", "ChEBI", "PubChem", "KEGG"]
        for source in sources:
            enriched = await self.query_source(source, identifier)
            if enriched:
                break
        return enriched
```

#### Pattern: Semantic Similarity Matching
```python
@register_action("SEMANTIC_METABOLITE_MATCH")
class SemanticMetaboliteMatch(TypedStrategyAction):
    """Uses embeddings for fuzzy metabolite matching."""
    
    def compute_similarity(self, name1: str, name2: str) -> float:
        # Use biochemical-aware tokenization
        tokens1 = self.biochemical_tokenize(name1)
        tokens2 = self.biochemical_tokenize(name2)
        return self.vector_similarity(tokens1, tokens2)
```

### Genomics Actions

#### Pattern: Variant Annotation
```python
@register_action("ANNOTATE_VARIANTS")
class AnnotateVariants(TypedStrategyAction):
    """Annotates genetic variants with functional predictions."""
    
    def annotate(self, variant: str) -> Dict:
        # Parse variant notation (e.g., "chr1:12345:A>G")
        chrom, pos, ref, alt = self.parse_variant(variant)
        
        # Get multiple annotation sources
        annotations = {
            "gene": self.get_overlapping_gene(chrom, pos),
            "consequence": self.predict_consequence(ref, alt),
            "frequency": self.get_population_frequency(variant),
            "pathogenicity": self.predict_pathogenicity(variant)
        }
        return annotations
```

#### Pattern: Reference Genome Handling
```python
@register_action("COORDINATE_LIFTOVER")
class CoordinateLiftover(TypedStrategyAction):
    """Converts coordinates between genome builds."""
    
    def liftover(self, chrom: str, pos: int, 
                  from_build: str = "hg19", 
                  to_build: str = "hg38") -> Tuple[str, int]:
        # Handle build-specific coordinate changes
        chain_file = self.get_chain_file(from_build, to_build)
        return self.apply_liftover(chrom, pos, chain_file)
```

### Proteomics Actions

#### Pattern: Post-Translational Modifications
```python
@register_action("MAP_PTM_SITES")
class MapPTMSites(TypedStrategyAction):
    """Maps post-translational modification sites."""
    
    def map_ptm(self, protein: str, position: int, modification: str):
        # Account for isoforms and sequence variants
        isoforms = self.get_isoforms(protein)
        mapped_positions = {}
        
        for isoform in isoforms:
            # Align sequences and map position
            aligned_pos = self.align_and_map(
                reference=protein,
                target=isoform,
                position=position
            )
            mapped_positions[isoform] = aligned_pos
        
        return mapped_positions
```

#### Pattern: Protein Complex Handling
```python
@register_action("RESOLVE_PROTEIN_COMPLEX")
class ResolveProteinComplex(TypedStrategyAction):
    """Resolves protein complexes to individual components."""
    
    def resolve(self, complex_id: str) -> Dict:
        components = self.get_complex_components(complex_id)
        return {
            "complex_id": complex_id,
            "components": components,
            "stoichiometry": self.get_stoichiometry(complex_id),
            "interactions": self.get_interactions(components)
        }
```

### Transcriptomics Actions

#### Pattern: Expression Normalization
```python
@register_action("NORMALIZE_EXPRESSION")
class NormalizeExpression(TypedStrategyAction):
    """Normalizes gene expression data."""
    
    def normalize(self, expression_matrix: pd.DataFrame, 
                   method: str = "TMM") -> pd.DataFrame:
        # Handle different normalization methods
        if method == "TMM":
            return self.tmm_normalize(expression_matrix)
        elif method == "DESeq2":
            return self.deseq2_normalize(expression_matrix)
        elif method == "TPM":
            return self.calculate_tpm(expression_matrix)
```

#### Pattern: Batch Effect Correction
```python
@register_action("CORRECT_BATCH_EFFECTS")
class CorrectBatchEffects(TypedStrategyAction):
    """Corrects batch effects in expression data."""
    
    def correct(self, data: pd.DataFrame, 
                batch_info: pd.Series) -> pd.DataFrame:
        # Preserve biological variation while removing batch effects
        design_matrix = self.create_design_matrix(data, batch_info)
        corrected = self.combat_seq(data, batch_info, design_matrix)
        return corrected
```

## Validation Patterns

### Pattern: Statistical Validation
```python
@register_action("VALIDATE_DIFFERENTIAL_EXPRESSION")
class ValidateDifferentialExpression(TypedStrategyAction):
    """Validates DE results against gold standard."""
    
    def validate(self, results: pd.DataFrame, 
                 reference: pd.DataFrame) -> Dict:
        metrics = {
            "correlation": pearsonr(results['logFC'], reference['logFC'])[0],
            "concordance": self.calculate_concordance(results, reference),
            "sensitivity": self.calculate_sensitivity(results, reference),
            "specificity": self.calculate_specificity(results, reference)
        }
        return metrics
```

### Pattern: Biological Consistency Check
```python
@register_action("CHECK_BIOLOGICAL_CONSISTENCY")
class CheckBiologicalConsistency(TypedStrategyAction):
    """Verifies biological plausibility of results."""
    
    def check(self, mappings: List[Tuple]) -> Dict:
        issues = []
        
        for source, target in mappings:
            # Check organism consistency
            if self.get_organism(source) != self.get_organism(target):
                issues.append(f"Organism mismatch: {source} → {target}")
            
            # Check molecular type consistency
            if self.get_mol_type(source) != self.get_mol_type(target):
                issues.append(f"Type mismatch: {source} → {target}")
        
        return {"valid": len(issues) == 0, "issues": issues}
```

## Error Handling Patterns

### Pattern: Graceful Degradation
```python
@register_action("ROBUST_IDENTIFIER_MAPPING")
class RobustIdentifierMapping(TypedStrategyAction):
    """Maps identifiers with fallback strategies."""
    
    async def execute_typed(self, params, context):
        try:
            # Try primary method
            result = await self.primary_mapping(params.identifiers)
        except ExternalAPIError:
            # Fallback to cached data
            result = await self.cached_mapping(params.identifiers)
        except CacheNotAvailable:
            # Final fallback to fuzzy matching
            result = self.fuzzy_mapping(params.identifiers)
        
        return result
```

### Pattern: Partial Success Handling
```python
@register_action("BATCH_ANNOTATION")
class BatchAnnotation(TypedStrategyAction):
    """Handles partial failures in batch processing."""
    
    def annotate_batch(self, items: List) -> Dict:
        successful = []
        failed = []
        
        for item in items:
            try:
                annotated = self.annotate_single(item)
                successful.append(annotated)
            except AnnotationError as e:
                failed.append({"item": item, "error": str(e)})
        
        return {
            "successful": successful,
            "failed": failed,
            "success_rate": len(successful) / len(items)
        }
```

## Performance Optimization Patterns

### Pattern: Batch Processing
```python
@register_action("BATCH_ENRICHMENT")
class BatchEnrichment(TypedStrategyAction):
    """Efficiently processes large datasets."""
    
    def process(self, identifiers: List, batch_size: int = 100):
        results = []
        for i in range(0, len(identifiers), batch_size):
            batch = identifiers[i:i+batch_size]
            batch_results = self.process_batch(batch)
            results.extend(batch_results)
        return results
```

### Pattern: Caching Strategy
```python
@register_action("CACHED_MAPPING")
class CachedMapping(TypedStrategyAction):
    """Implements intelligent caching for expensive operations."""
    
    def __init__(self, params, executor):
        super().__init__(params, executor)
        self.cache = LRUCache(maxsize=10000)
    
    def map_with_cache(self, identifier: str):
        if identifier in self.cache:
            return self.cache[identifier]
        
        result = self.expensive_mapping(identifier)
        self.cache[identifier] = result
        return result
```

## Testing Guidelines

### Unit Test Pattern
```python
class TestMetaboliteEnrichment:
    def test_handles_synonyms(self):
        """Test that action recognizes metabolite synonyms."""
        action = MetaboliteEnrichment()
        glucose_forms = ["glucose", "D-glucose", "dextrose"]
        results = [action.enrich(name) for name in glucose_forms]
        # All should map to same entity
        assert len(set(r['id'] for r in results)) == 1
    
    def test_handles_missing_data(self):
        """Test graceful handling of unknown metabolites."""
        action = MetaboliteEnrichment()
        result = action.enrich("unknown_metabolite_xyz")
        assert result['status'] == 'not_found'
```

### Integration Test Pattern
```python
class TestCompleteWorkflow:
    async def test_metabolomics_pipeline(self):
        """Test complete metabolomics harmonization workflow."""
        strategy = load_strategy("metabolomics_harmonization.yaml")
        test_data = load_test_data("metabolites_test.csv")
        
        result = await execute_strategy(strategy, test_data)
        
        # Validate against expected results
        assert result['match_rate'] > 0.7
        assert result['validation']['correlation'] > 0.95
```

## Common Pitfalls to Avoid

1. **Assuming Standard Nomenclature**: Always handle variations
2. **Ignoring Organism Specificity**: Check species compatibility
3. **Overlooking Isoforms**: Proteins have multiple forms
4. **Missing Version Control**: Track database versions
5. **Inadequate Error Messages**: Provide biological context in errors

## Development Checklist

- [ ] Handles many-to-many relationships
- [ ] Processes composite identifiers
- [ ] Includes biological validation
- [ ] Implements graceful degradation
- [ ] Provides detailed provenance
- [ ] Includes comprehensive tests
- [ ] Documents biological assumptions
- [ ] Validates against gold standards
- [ ] Optimizes for large datasets
- [ ] Follows domain conventions