# LLM-Based Mapping Tutorial

This tutorial demonstrates how to use Large Language Models (LLMs) for intelligent biological entity mapping when traditional methods fail or when dealing with complex, ambiguous terms.

## Overview

LLM-based mapping leverages the knowledge embedded in large language models to:
- Map non-standard or colloquial terms
- Handle complex descriptions
- Provide reasoning for mapping decisions
- Suggest alternatives when exact matches aren't found

## Prerequisites

```python
import asyncio
from biomapper.core import MappingExecutor, MappingExecutorBuilder
from biomapper.core.models import DatabaseConfig, CacheConfig, LLMConfig
from biomapper.mvp0_pipeline.llm_mapper import LLMMapper
```

## Configuration

### Setting Up LLM Configuration

```python
# Configure LLM settings
llm_config = LLMConfig(
    provider="openai",  # or "anthropic", "gemini"
    model="gpt-4",
    temperature=0.0,  # Use 0 for deterministic results
    max_tokens=1000,
    api_key="your-api-key-here"  # Or use environment variable
)
```

### Environment Variables

Set up your API keys:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GOOGLE_API_KEY="..."
```

## Basic LLM Mapping

### Example 1: Simple Term Mapping

```python
from dotenv import load_dotenv
load_dotenv()

async def basic_llm_mapping():
    # Initialize LLM mapper
    mapper = LLMMapper(
        model="gpt-4",
        temperature=0.0,
        max_tokens=1000
    )
    
    # Map a colloquial term
    result = mapper.map_term("sugar in blood")
    
    if result.best_match:
        print(f"Query: sugar in blood")
        print(f"Mapped to: {result.best_match.target_name}")
        print(f"Standard ID: {result.best_match.target_id}")
        print(f"Confidence: {result.best_match.confidence}")
        print(f"Reasoning: {result.best_match.reasoning}")
```

### Example 2: Mapping with Target Ontology

```python
async def ontology_specific_mapping():
    mapper = LLMMapper(model="gpt-4", temperature=0.0)
    
    # Complex metabolite descriptions
    terms = [
        "the sugar that gives you energy",
        "vitamin C",
        "the molecule that carries oxygen in blood",
        "stress hormone"
    ]
    
    # Map to specific ontology
    for term in terms:
        result = mapper.map_term(
            term,
            target_ontology="CHEBI",  # ChEBI for chemicals
            include_reasoning=True
        )
        
        print(f"\nQuery: '{term}'")
        if result.best_match:
            print(f"  ChEBI ID: {result.best_match.target_id}")
            print(f"  Name: {result.best_match.target_name}")
            print(f"  Confidence: {result.best_match.confidence:.2f}")
            print(f"  Reasoning: {result.best_match.reasoning}")
```

## Integrated LLM Mapping

### Using LLM as Fallback in Strategies

Create a YAML strategy that uses LLM as a fallback:

```yaml
# configs/strategies/intelligent_metabolite_mapping.yaml
name: intelligent_metabolite_mapping
version: "1.0"
description: Metabolite mapping with LLM fallback for difficult cases

actions:
  - type: LOAD_INPUT_DATA
    name: load_metabolites
    
  - type: API_RESOLVER
    name: standard_lookup
    config:
      api_endpoint: chebi
      confidence_threshold: 0.9
      
  - type: API_RESOLVER
    name: pubchem_lookup
    config:
      api_endpoint: pubchem
      only_unmapped: true
      confidence_threshold: 0.8
      
  - type: LLM_MAPPER
    name: intelligent_fallback
    config:
      only_unmapped: true
      model: gpt-4
      temperature: 0.0
      target_ontology: CHEBI
      include_reasoning: true
      confidence_threshold: 0.7
      
  - type: SAVE_RESULTS
    name: save_with_reasoning
    config:
      include_llm_reasoning: true
```

Execute the strategy:

```python
async def intelligent_mapping_strategy():
    # Configure executor with LLM support
    executor = MappingExecutorBuilder.create(
        db_config=DatabaseConfig(url="sqlite+aiosqlite:///data/mapping.db"),
        cache_config=CacheConfig(backend="memory"),
        llm_config=LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0
        )
    )
    
    await executor.initialize()
    
    try:
        # Mix of standard and non-standard terms
        metabolites = [
            "glucose",  # Standard
            "vitamin C",  # Common name
            "blood sugar",  # Colloquial
            "happy hormone",  # Very colloquial
            "C6H12O6",  # Chemical formula
            "the stuff that makes you sleepy"  # Description
        ]
        
        result = await executor.execute_yaml_strategy(
            strategy_file="configs/strategies/intelligent_metabolite_mapping.yaml",
            input_data={"entities": metabolites}
        )
        
        # Display results with reasoning
        for mapping in result.data.get("mappings", []):
            print(f"\nTerm: {mapping['query_id']}")
            print(f"  Mapped to: {mapping['mapped_id']}")
            print(f"  Method: {mapping['source']}")
            if 'llm_reasoning' in mapping:
                print(f"  LLM Reasoning: {mapping['llm_reasoning']}")
                
    finally:
        await executor.shutdown()
```

## Advanced LLM Mapping

### Example 3: Batch Processing with Context

```python
async def batch_llm_mapping_with_context():
    """Map terms with additional context for better accuracy."""
    
    mapper = LLMMapper(model="gpt-4", temperature=0.0)
    
    # Terms with context
    terms_with_context = [
        {
            "term": "sugar",
            "context": "diabetes management",
            "expected_type": "clinical marker"
        },
        {
            "term": "sugar", 
            "context": "baking ingredient",
            "expected_type": "food compound"
        },
        {
            "term": "iron",
            "context": "anemia treatment",
            "expected_type": "nutrient"
        },
        {
            "term": "iron",
            "context": "metal element",
            "expected_type": "chemical element"
        }
    ]
    
    for item in terms_with_context:
        result = mapper.map_term(
            term=item["term"],
            metadata={
                "context": item["context"],
                "expected_type": item["expected_type"]
            }
        )
        
        print(f"\nTerm: '{item['term']}' in context of '{item['context']}'")
        if result.best_match:
            print(f"  Mapped to: {result.best_match.target_name}")
            print(f"  ID: {result.best_match.target_id}")
```

### Example 4: Multi-Language Support

```python
async def multilingual_mapping():
    """Map terms in different languages."""
    
    mapper = LLMMapper(
        model="gpt-4",
        temperature=0.0,
        system_prompt="You are a multilingual biomedical term mapper."
    )
    
    # Terms in different languages
    multilingual_terms = [
        ("glucose", "en"),
        ("глюкоза", "ru"),  # glucose in Russian
        ("葡萄糖", "zh"),   # glucose in Chinese
        ("グルコース", "ja"), # glucose in Japanese
        ("glucosa", "es"),   # glucose in Spanish
    ]
    
    for term, lang in multilingual_terms:
        result = mapper.map_term(
            term,
            metadata={"language": lang},
            target_ontology="CHEBI"
        )
        
        print(f"\n{term} ({lang})")
        if result.best_match:
            print(f"  → {result.best_match.target_name}")
            print(f"  ChEBI: {result.best_match.target_id}")
```

### Example 5: Complex Reasoning Chains

```python
async def complex_reasoning_mapping():
    """Handle complex descriptions requiring reasoning."""
    
    mapper = LLMMapper(
        model="gpt-4",
        temperature=0.0,
        max_tokens=2000  # More tokens for complex reasoning
    )
    
    # Complex medical descriptions
    complex_terms = [
        "the enzyme that breaks down milk sugar",
        "the protein that transports oxygen but isn't hemoglobin",
        "the hormone that opposes insulin action",
        "the neurotransmitter involved in pleasure and reward"
    ]
    
    for term in complex_terms:
        result = mapper.map_term(
            term,
            target_ontology="UniProt",  # For proteins/enzymes
            include_alternatives=True,
            max_alternatives=3
        )
        
        print(f"\nQuery: '{term}'")
        if result.best_match:
            print(f"Best match: {result.best_match.target_name}")
            print(f"Reasoning: {result.best_match.reasoning}")
            
        if result.alternatives:
            print("Alternatives:")
            for alt in result.alternatives:
                print(f"  - {alt.target_name} (confidence: {alt.confidence:.2f})")
```

## Cost Management

### Monitoring API Usage

```python
async def cost_aware_mapping():
    """Track costs when using LLM mapping."""
    
    mapper = LLMMapper(
        model="gpt-4",
        temperature=0.0,
        track_usage=True
    )
    
    terms = ["glucose", "ATP", "insulin", "dopamine"]
    total_cost = 0.0
    
    for term in terms:
        result = mapper.map_term(term)
        
        # Track costs
        if result.metrics:
            total_cost += result.metrics.cost
            print(f"{term}: ${result.metrics.cost:.4f}")
            print(f"  Tokens: {result.metrics.total_tokens}")
    
    print(f"\nTotal cost: ${total_cost:.4f}")
```

### Implementing Caching

```python
from functools import lru_cache

class CachedLLMMapper(LLMMapper):
    """LLM Mapper with built-in caching."""
    
    @lru_cache(maxsize=1000)
    def map_term_cached(self, term: str, target_ontology: str = None):
        """Cached version of map_term."""
        return super().map_term(term, target_ontology)
    
    def map_term(self, term: str, **kwargs):
        """Override to use cache when possible."""
        # Use cache for simple queries
        if not kwargs or (len(kwargs) == 1 and 'target_ontology' in kwargs):
            return self.map_term_cached(term, kwargs.get('target_ontology'))
        # Fall back to uncached for complex queries
        return super().map_term(term, **kwargs)
```

## Best Practices

### 1. Use Appropriate Models

```python
# For simple mappings - use smaller, faster models
simple_mapper = LLMMapper(model="gpt-3.5-turbo", temperature=0.0)

# For complex reasoning - use more capable models
complex_mapper = LLMMapper(model="gpt-4", temperature=0.0)

# For cost-sensitive applications - use specialized models
budget_mapper = LLMMapper(model="gpt-3.5-turbo", max_tokens=500)
```

### 2. Provide Clear Context

```python
# Good: Specific context
result = mapper.map_term(
    "CAT",
    metadata={
        "domain": "enzymology",
        "full_text": "CAT enzyme activity was measured",
        "expected_type": "protein"
    }
)

# Less effective: Ambiguous term without context
result = mapper.map_term("CAT")  # Could be catalase or feline!
```

### 3. Validate LLM Output

```python
async def validated_llm_mapping(term: str):
    """Map with validation of LLM results."""
    
    mapper = LLMMapper(model="gpt-4")
    result = mapper.map_term(term, target_ontology="CHEBI")
    
    if result.best_match:
        # Validate the suggested ID exists
        validation_result = await validate_chebi_id(
            result.best_match.target_id
        )
        
        if validation_result.exists:
            return result.best_match
        else:
            print(f"Warning: LLM suggested non-existent ID: "
                  f"{result.best_match.target_id}")
            return None
```

## Error Handling

```python
async def robust_llm_mapping():
    """Handle various error conditions."""
    
    mapper = LLMMapper(model="gpt-4")
    
    try:
        result = mapper.map_term(
            "some complex term",
            timeout=30  # Set timeout for API calls
        )
    except TimeoutError:
        print("LLM request timed out")
        # Fall back to simpler method
    except RateLimitError:
        print("Rate limit exceeded")
        # Implement backoff strategy
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Log and handle gracefully
```

## Performance Optimization

### Batch Processing

```python
async def batch_llm_processing(terms: List[str]):
    """Process multiple terms efficiently."""
    
    # Group similar terms
    grouped_terms = group_by_similarity(terms)
    
    # Process each group with appropriate context
    results = []
    for group in grouped_terms:
        # Create group context
        context = f"Mapping {len(group)} related terms"
        
        # Map with shared context
        for term in group:
            result = mapper.map_term(
                term,
                metadata={"group_context": context}
            )
            results.append(result)
    
    return results
```

## Next Steps

- Explore [RAG-based Mapping](metabolite_mapping_rag.md) for combining LLM with retrieval
- Learn about [Strategy Development](yaml_mapping_strategies.md) for complex workflows
- Check [Performance Optimization](../guides/performance.md) for large-scale mapping