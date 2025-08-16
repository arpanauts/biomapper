# FUZZY_NAME_MATCH Action Type

## Overview

`FUZZY_NAME_MATCH` performs string similarity matching between entity names from different datasets. This action is crucial when exact ID matching fails but entities may be the same based on their names or descriptions.

### Purpose
- Match entities by name similarity when IDs don't align
- Support multiple string matching algorithms
- Handle biological nomenclature variations
- Provide confidence scores for matches
- Work across all entity types

### Use Cases
- Match protein names when UniProt IDs differ
- Align metabolite common names with systematic names
- Match gene symbols with full gene names
- Harmonize clinical test names across institutions
- Resolve drug brand names to generic names

## Design Decisions

### Algorithm Selection
1. **Multiple Algorithms**: Different algorithms for different use cases
2. **Biological Awareness**: Special handling for biological nomenclature
3. **Performance Optimization**: Blocking strategies for large datasets
4. **Configurable Thresholds**: Entity-specific similarity thresholds
5. **Ensemble Scoring**: Combine multiple algorithms for robustness

## Implementation Details

### Parameter Model
```python
class StringMatchAlgorithm(str, Enum):
    """Available string matching algorithms."""
    EXACT = "exact"
    LEVENSHTEIN = "levenshtein"  # Edit distance
    JARO_WINKLER = "jaro_winkler"  # Good for typos
    TOKEN_SET_RATIO = "token_set_ratio"  # Order-independent
    PARTIAL_RATIO = "partial_ratio"  # Substring matching
    PHONETIC = "phonetic"  # Soundex/Metaphone
    BIOLOGICAL = "biological"  # Custom for bio entities
    ENSEMBLE = "ensemble"  # Combination of methods

class BiologicalNormalization(BaseModel):
    """Biological-specific text normalization."""
    remove_organism_suffix: bool = Field(default=True)  # Remove "(human)", "[Homo sapiens]"
    normalize_greek_letters: bool = Field(default=True)  # α -> alpha
    remove_modifications: bool = Field(default=True)  # Remove phospho-, methyl-, etc.
    expand_abbreviations: bool = Field(default=True)  # IL -> Interleukin
    
class FuzzyNameMatchParams(BaseModel):
    """Parameters for fuzzy name matching."""
    
    # Input configuration
    source_context_key: str = Field(..., description="Source dataset")
    source_name_field: str = Field(..., description="Name field in source")
    source_id_field: str = Field(..., description="ID field in source")
    
    target_context_key: str = Field(..., description="Target dataset")
    target_name_field: str = Field(..., description="Name field in target")
    target_id_field: str = Field(..., description="ID field in target")
    
    # Matching configuration
    algorithms: List[StringMatchAlgorithm] = Field(
        default=[StringMatchAlgorithm.TOKEN_SET_RATIO],
        description="Algorithms to use"
    )
    threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    
    # Preprocessing
    case_sensitive: bool = Field(default=False)
    remove_punctuation: bool = Field(default=True)
    normalize_whitespace: bool = Field(default=True)
    biological_normalization: Optional[BiologicalNormalization] = Field(None)
    
    # Performance optimization
    use_blocking: bool = Field(default=True, description="Use blocking for large datasets")
    block_on: Optional[List[str]] = Field(None, description="Fields to block on")
    max_candidates_per_source: int = Field(default=10)
    
    # Entity-specific configuration
    entity_type: Optional[str] = Field(None)
    use_synonyms: bool = Field(default=True)
    synonym_context_key: Optional[str] = Field(None)
    
    # Output configuration
    output_context_key: str = Field(...)
    include_all_scores: bool = Field(default=False)
    min_matches_per_source: int = Field(default=1)
    max_matches_per_source: int = Field(default=3)
    
    # Error handling
    continue_on_error: bool = Field(default=True)
    fallback_to_exact: bool = Field(default=True)
```

### Result Model
```python
class NameMatch(BaseModel):
    """A single name match result."""
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    similarity_score: float
    algorithm_used: str
    algorithm_scores: Optional[Dict[str, float]]
    is_exact_match: bool
    rank: int  # Rank among matches for this source

class FuzzyNameMatchResult(ActionResult):
    """Result from fuzzy name matching."""
    
    # Summary statistics
    total_source_entities: int
    total_target_entities: int
    matched_source_count: int
    exact_match_count: int
    fuzzy_match_count: int
    
    # Score distribution
    score_distribution: Dict[str, int]  # score_range -> count
    average_best_score: float
    algorithm_effectiveness: Dict[str, float]  # algorithm -> avg contribution
    
    # Matches
    matches: List[NameMatch]
    unmatched_source_ids: List[str]
    
    # Performance metrics
    comparisons_made: int
    blocking_reduction_ratio: float
```

### Core Implementation
```python
class FuzzyNameMatch(TypedStrategyAction[FuzzyNameMatchParams, FuzzyNameMatchResult]):
    """Fuzzy string matching for entity names."""
    
    def __init__(self):
        super().__init__()
        self.normalizers = self._initialize_normalizers()
        self.matchers = self._initialize_matchers()
    
    def get_params_model(self) -> type[FuzzyNameMatchParams]:
        return FuzzyNameMatchParams
    
    async def execute_typed(
        self,
        params: FuzzyNameMatchParams,
        context: ExecutionContext,
        executor: MappingExecutor
    ) -> FuzzyNameMatchResult:
        """Perform fuzzy name matching."""
        
        # Load datasets
        source_data = self._load_name_data(
            context.get(params.source_context_key),
            params.source_name_field,
            params.source_id_field
        )
        
        target_data = self._load_name_data(
            context.get(params.target_context_key),
            params.target_name_field,
            params.target_id_field
        )
        
        # Load synonyms if requested
        synonym_map = {}
        if params.use_synonyms and params.synonym_context_key:
            synonym_map = context.get(params.synonym_context_key, {})
        
        # Normalize names
        source_normalized = self._normalize_names(
            source_data,
            params,
            synonym_map
        )
        
        target_normalized = self._normalize_names(
            target_data,
            params,
            synonym_map
        )
        
        # Apply blocking if enabled
        candidate_pairs = self._generate_candidate_pairs(
            source_normalized,
            target_normalized,
            params
        )
        
        # Perform matching
        all_matches = []
        unmatched_source = set(source_data.keys())
        algorithm_scores = defaultdict(list)
        comparisons = 0
        
        for source_id, source_names in source_normalized.items():
            best_matches = []
            
            for target_id in candidate_pairs.get(source_id, []):
                target_names = target_normalized[target_id]
                
                # Compare all name variants
                for s_name in source_names:
                    for t_name in target_names:
                        comparisons += 1
                        
                        # Calculate similarity
                        score, algorithm, all_scores = self._calculate_similarity(
                            s_name, t_name, params
                        )
                        
                        if score >= params.threshold:
                            best_matches.append(NameMatch(
                                source_id=source_id,
                                source_name=source_data[source_id],
                                target_id=target_id,
                                target_name=target_data[target_id],
                                similarity_score=score,
                                algorithm_used=algorithm,
                                algorithm_scores=all_scores if params.include_all_scores else None,
                                is_exact_match=(score == 1.0),
                                rank=0  # Will be set later
                            ))
                            
                            # Track algorithm effectiveness
                            algorithm_scores[algorithm].append(score)
            
            # Rank and filter matches for this source
            if best_matches:
                # Sort by score descending
                best_matches.sort(key=lambda x: x.similarity_score, reverse=True)
                
                # Assign ranks
                for i, match in enumerate(best_matches):
                    match.rank = i + 1
                
                # Keep top N matches
                kept_matches = best_matches[
                    :min(params.max_matches_per_source, len(best_matches))
                ]
                
                all_matches.extend(kept_matches)
                unmatched_source.discard(source_id)
        
        # Calculate statistics
        score_distribution = self._calculate_score_distribution(all_matches)
        
        # Store results
        context[params.output_context_key] = all_matches
        
        return FuzzyNameMatchResult(
            status='success',
            processed_count=len(source_data),
            error_count=0,
            total_source_entities=len(source_data),
            total_target_entities=len(target_data),
            matched_source_count=len(source_data) - len(unmatched_source),
            exact_match_count=sum(1 for m in all_matches if m.is_exact_match),
            fuzzy_match_count=sum(1 for m in all_matches if not m.is_exact_match),
            score_distribution=score_distribution,
            average_best_score=self._calculate_average_best_score(all_matches),
            algorithm_effectiveness=self._calculate_algorithm_effectiveness(algorithm_scores),
            matches=all_matches,
            unmatched_source_ids=list(unmatched_source),
            comparisons_made=comparisons,
            blocking_reduction_ratio=self._calculate_blocking_reduction(
                len(source_data), len(target_data), comparisons
            )
        )
    
    def _normalize_names(
        self,
        name_data: Dict[str, str],
        params: FuzzyNameMatchParams,
        synonym_map: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Normalize names and expand with synonyms."""
        
        normalized = {}
        
        for entity_id, name in name_data.items():
            variants = [name]
            
            # Add synonyms
            if params.use_synonyms:
                variants.extend(synonym_map.get(entity_id, []))
                variants.extend(synonym_map.get(name, []))
            
            # Normalize each variant
            normalized_variants = []
            for variant in variants:
                norm = variant
                
                # Basic normalization
                if not params.case_sensitive:
                    norm = norm.lower()
                
                if params.remove_punctuation:
                    norm = re.sub(r'[^\w\s]', ' ', norm)
                
                if params.normalize_whitespace:
                    norm = ' '.join(norm.split())
                
                # Biological normalization
                if params.biological_normalization:
                    norm = self._apply_biological_normalization(
                        norm, params.biological_normalization
                    )
                
                normalized_variants.append(norm)
            
            normalized[entity_id] = list(set(normalized_variants))  # Unique variants
        
        return normalized
    
    def _apply_biological_normalization(
        self,
        text: str,
        config: BiologicalNormalization
    ) -> str:
        """Apply biological-specific normalizations."""
        
        if config.remove_organism_suffix:
            # Remove common organism indicators
            text = re.sub(r'\s*\([Hh]uman\)\s*$', '', text)
            text = re.sub(r'\s*\[Homo sapiens\]\s*$', '', text)
            text = re.sub(r'\s*\[Mouse\]\s*$', '', text)
        
        if config.normalize_greek_letters:
            # Greek letter mapping
            greek_map = {
                'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
                'ε': 'epsilon', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu'
            }
            for greek, latin in greek_map.items():
                text = text.replace(greek, latin)
        
        if config.remove_modifications:
            # Remove common modifications
            mods = ['phospho', 'methyl', 'acetyl', 'ubiquitin']
            for mod in mods:
                text = re.sub(rf'\b{mod}-?\s*', '', text, flags=re.I)
        
        if config.expand_abbreviations:
            # Common abbreviations
            abbrev_map = {
                r'\bIL\b': 'Interleukin',
                r'\bTNF\b': 'Tumor Necrosis Factor',
                r'\bHLA\b': 'Human Leukocyte Antigen'
            }
            for abbrev, full in abbrev_map.items():
                text = re.sub(abbrev, full, text, flags=re.I)
        
        return text
    
    def _calculate_similarity(
        self,
        name1: str,
        name2: str,
        params: FuzzyNameMatchParams
    ) -> Tuple[float, str, Dict[str, float]]:
        """Calculate similarity using configured algorithms."""
        
        scores = {}
        
        for algorithm in params.algorithms:
            if algorithm == StringMatchAlgorithm.EXACT:
                scores[algorithm.value] = 1.0 if name1 == name2 else 0.0
            
            elif algorithm == StringMatchAlgorithm.LEVENSHTEIN:
                scores[algorithm.value] = 1 - (editdistance.eval(name1, name2) / 
                                              max(len(name1), len(name2)))
            
            elif algorithm == StringMatchAlgorithm.JARO_WINKLER:
                scores[algorithm.value] = jellyfish.jaro_winkler_similarity(name1, name2)
            
            elif algorithm == StringMatchAlgorithm.TOKEN_SET_RATIO:
                scores[algorithm.value] = fuzz.token_set_ratio(name1, name2) / 100
            
            elif algorithm == StringMatchAlgorithm.PARTIAL_RATIO:
                scores[algorithm.value] = fuzz.partial_ratio(name1, name2) / 100
            
            elif algorithm == StringMatchAlgorithm.PHONETIC:
                # Use Soundex or Metaphone
                scores[algorithm.value] = 1.0 if jellyfish.soundex(name1) == jellyfish.soundex(name2) else 0.0
            
            elif algorithm == StringMatchAlgorithm.BIOLOGICAL:
                # Custom biological similarity
                scores[algorithm.value] = self._biological_similarity(name1, name2)
        
        # Determine best score and algorithm
        if StringMatchAlgorithm.ENSEMBLE in params.algorithms:
            # Weighted average
            final_score = sum(scores.values()) / len(scores)
            best_algorithm = "ensemble"
        else:
            best_algorithm = max(scores, key=scores.get)
            final_score = scores[best_algorithm]
        
        return final_score, best_algorithm, scores
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_basic_fuzzy_matching():
    """Test basic fuzzy name matching."""
    action = FuzzyNameMatch()
    
    context = {
        'source_proteins': [
            {'id': 'P1', 'name': 'Tumor necrosis factor alpha'},
            {'id': 'P2', 'name': 'Interleukin-6'},
            {'id': 'P3', 'name': 'BRCA1'}
        ],
        'target_proteins': [
            {'id': 'T1', 'name': 'TNF-alpha'},
            {'id': 'T2', 'name': 'IL-6'},
            {'id': 'T3', 'name': 'Breast cancer type 1 susceptibility protein'}
        ]
    }
    
    result = await action.execute_typed(
        params=FuzzyNameMatchParams(
            source_context_key='source_proteins',
            source_name_field='name',
            source_id_field='id',
            target_context_key='target_proteins',
            target_name_field='name',
            target_id_field='id',
            algorithms=[StringMatchAlgorithm.TOKEN_SET_RATIO],
            threshold=0.7,
            biological_normalization=BiologicalNormalization(
                expand_abbreviations=True
            ),
            output_context_key='name_matches'
        ),
        context=context,
        executor=mock_executor
    )
    
    assert result.matched_source_count >= 2  # At least TNF and IL-6
    matches = {m.source_id: m.target_id for m in result.matches}
    assert matches.get('P1') == 'T1'  # TNF match
    assert matches.get('P2') == 'T2'  # IL-6 match

@pytest.mark.asyncio
async def test_biological_normalization():
    """Test biological-specific normalizations."""
    # Test Greek letter normalization
    # Test organism suffix removal
    # Test modification removal
    pass
```

## Examples

### Basic Protein Name Matching
```yaml
- action:
    type: FUZZY_NAME_MATCH
    params:
      source_context_key: "ukbb_proteins"
      source_name_field: "protein_name"
      source_id_field: "uniprot_id"
      target_context_key: "hpa_proteins"
      target_name_field: "gene_description"
      target_id_field: "ensembl_id"
      algorithms: ["token_set_ratio", "jaro_winkler"]
      threshold: 0.85
      biological_normalization:
        remove_organism_suffix: true
        normalize_greek_letters: true
      output_context_key: "protein_name_matches"
```

### Metabolite Name Harmonization
```yaml
- action:
    type: FUZZY_NAME_MATCH
    params:
      source_context_key: "local_metabolites"
      source_name_field: "common_name"
      source_id_field: "local_id"
      target_context_key: "hmdb_metabolites"
      target_name_field: "name"
      target_id_field: "accession"
      algorithms: ["token_set_ratio", "partial_ratio", "biological"]
      threshold: 0.8
      use_synonyms: true
      synonym_context_key: "metabolite_synonyms"
      max_matches_per_source: 5
      output_context_key: "metabolite_name_matches"
```

### Clinical Test Name Matching
```yaml
- action:
    type: FUZZY_NAME_MATCH
    params:
      source_context_key: "hospital_lab_tests"
      source_name_field: "test_name"
      source_id_field: "test_code"
      target_context_key: "loinc_tests"
      target_name_field: "long_name"
      target_id_field: "loinc_code"
      algorithms: ["ensemble"]  # Use all algorithms
      threshold: 0.75
      use_blocking: true
      block_on: ["test_category"]
      output_context_key: "lab_test_matches"
```

## Integration Notes

### Typically Used When
- ID-based matching fails or is incomplete
- Datasets use different naming conventions
- Need to match legacy names to current ones
- Building initial mappings for curation

### Performance Optimization
- Use blocking for datasets >10K entities
- Pre-compute normalized names
- Cache similarity scores
- Use parallel processing for large comparisons

### Combines Well With
- `VALIDATE_IDENTIFIER_FORMAT` - Verify matched IDs
- `RANK_MAPPING_CANDIDATES` - Combine with other evidence
- `GENERATE_MAPPING_REPORT` - Include name matches