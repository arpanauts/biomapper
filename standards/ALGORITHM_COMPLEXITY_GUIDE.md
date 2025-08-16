# Algorithm Complexity Best Practices Guide

## Overview

This guide provides best practices for writing efficient algorithms in the biomapper codebase. Following these guidelines will prevent performance issues that can turn minutes of computation into hours.

## Critical Anti-Patterns to Avoid

### 1. Nested Loops Over Different Collections (O(n*m))

**❌ BAD: Nested Loop Matching**
```python
matches = []
for source_item in source_list:  # O(n)
    for target_item in target_list:  # O(m)
        if source_item['id'] == target_item['id']:  # O(n*m) comparisons
            matches.append((source_item, target_item))
```
**Result:** 1,000 × 100,000 = 100,000,000 operations

**✅ GOOD: Index-Based Matching**
```python
from biomapper.core.algorithms.efficient_matching import EfficientMatcher

# Build index once - O(m)
target_index = EfficientMatcher.build_index(
    target_list, 
    key_func=lambda x: x['id']
)

# Match using index - O(n)
matches = EfficientMatcher.match_with_index(
    source_list, 
    target_index,
    source_key_func=lambda x: x['id']
)
```
**Result:** 1,000 + 100,000 = 101,000 operations (990x faster!)

### 2. DataFrame.iterrows() in Loops

**❌ BAD: Nested iterrows()**
```python
for idx1, row1 in df1.iterrows():  # Slow iteration
    for idx2, row2 in df2.iterrows():  # Even slower
        if row1['id'] == row2['id']:
            # Process match
```

**✅ GOOD: Vectorized Operations**
```python
# Use pandas merge (hash join)
merged = pd.merge(df1, df2, on='id', how='inner')

# Or use vectorized operations
df['new_col'] = df['col1'] * 2  # Vectorized
mask = df['id'].isin(target_ids)  # Vectorized filtering
```

### 3. Repeated Lookups in Loops

**❌ BAD: Lookup in Every Iteration**
```python
for item in items:
    # This does a lookup every iteration
    value = expensive_dict[item['key']]
    enriched = api_call(value)  # Even worse if API call
    process(enriched)
```

**✅ GOOD: Batch and Cache**
```python
# Pre-compute all lookups
keys = [item['key'] for item in items]
values = EfficientMatcher.batch_lookup(keys, expensive_dict)

# Or cache results
cache = {item['key']: expensive_dict[item['key']] for item in items}
for item in items:
    process(cache[item['key']])
```

## Efficient Patterns to Use

### 1. Dictionary/Set Indexing for Matching

```python
# For exact matching
def efficient_exact_match(source, target, key_field):
    target_index = {item[key_field]: item for item in target}
    matches = []
    for source_item in source:
        if source_item[key_field] in target_index:
            matches.append((source_item, target_index[source_item[key_field]]))
    return matches
```

### 2. Set Operations for Unique Items

```python
# Fast intersection/difference
source_ids = set(source_list)
target_ids = set(target_list)

common = source_ids & target_ids  # O(min(n,m))
source_only = source_ids - target_ids  # O(n)
target_only = target_ids - source_ids  # O(m)
```

### 3. Sorted Merge for Large Datasets

```python
# When both lists are sorted
def sorted_merge(list1, list2):
    i, j = 0, 0
    matches = []
    while i < len(list1) and j < len(list2):
        if list1[i] == list2[j]:
            matches.append((list1[i], list2[j]))
            i += 1
            j += 1
        elif list1[i] < list2[j]:
            i += 1
        else:
            j += 1
    return matches
```

### 4. Chunked Processing for Memory Efficiency

```python
from biomapper.core.algorithms.efficient_matching import EfficientMatcher

# Process large dataset in chunks
results = EfficientMatcher.chunked_processing(
    large_dataset,
    process_func=lambda chunk: process_chunk(chunk),
    chunk_size=10000
)
```

## Complexity Quick Reference

| Operation | Complexity | Use When |
|-----------|------------|----------|
| Dictionary lookup | O(1) | Exact key matching |
| Set membership | O(1) | Checking existence |
| List append | O(1)* | Building results |
| Dictionary build | O(n) | Pre-processing for lookups |
| Set intersection | O(min(n,m)) | Finding common elements |
| Sorting | O(n log n) | Preparing for merge |
| Nested loops | O(n*m) | AVOID! |
| DataFrame.iterrows() | O(n) | AVOID! Use vectorized ops |

## DataFrame Best Practices

### Use Vectorized Operations

```python
# ✅ GOOD: Vectorized
df['new_col'] = df['col1'] * df['col2']
df['category'] = pd.cut(df['value'], bins=[0, 10, 20, 30])
df_filtered = df[df['value'] > threshold]

# ❌ BAD: Loop-based
for idx, row in df.iterrows():
    df.loc[idx, 'new_col'] = row['col1'] * row['col2']
```

### Use .apply() for Row Operations

```python
# When you must process row-by-row
def process_row(row):
    return complex_calculation(row['col1'], row['col2'])

df['result'] = df.apply(process_row, axis=1)  # Better than iterrows
```

### Use Built-in Methods

```python
# Grouping and aggregation
grouped = df.groupby('category')['value'].sum()

# Merging
merged = pd.merge(df1, df2, on='id', how='inner')

# Filtering
filtered = df.query('value > 100 and category == "A"')
```

## Memory vs Time Trade-offs

### When to Use More Memory

1. **Building Indexes**: Use O(n) memory to get O(1) lookups
2. **Caching Results**: Store computed values to avoid recomputation
3. **Denormalization**: Duplicate data to avoid joins

### When to Optimize Memory

1. **Streaming Large Files**: Process line-by-line
2. **Chunked Processing**: Process in batches
3. **Generator Expressions**: Use generators instead of lists

## Testing for Performance

### Use the Complexity Checker

```python
from biomapper.core.standards.complexity_checker import ComplexityChecker

checker = ComplexityChecker()
analysis = checker.analyze_function(my_function)
if analysis['estimated_complexity'] == 'O(n^2)' or worse:
    # Refactor needed!
```

### Benchmark Different Approaches

```python
import time

def benchmark(func, *args):
    start = time.time()
    result = func(*args)
    elapsed = time.time() - start
    return result, elapsed

# Compare approaches
result1, time1 = benchmark(nested_loop_approach, data)
result2, time2 = benchmark(indexed_approach, data)
print(f"Speedup: {time1/time2:.1f}x")
```

### Profile Your Code

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = your_function(data)

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(10)  # Top 10 time consumers
```

## Common Optimizations for Biomapper

### 1. Protein Matching

```python
# Use multi-key indexing for protein identifiers
from biomapper.core.algorithms.efficient_matching import EfficientMatcher

protein_index = EfficientMatcher.multi_key_index(
    proteins,
    key_funcs=[
        lambda p: p.get('uniprot_id'),
        lambda p: p.get('gene_symbol'),
        lambda p: p.get('ensembl_id')
    ]
)
```

### 2. Metabolite Matching

```python
# Use set operations for identifier matching
def match_metabolites(source_metabolites, target_metabolites):
    # Extract all possible identifiers
    source_ids = set()
    for m in source_metabolites:
        source_ids.update([m.get('hmdb'), m.get('chebi'), m.get('kegg')])
    
    target_index = {}
    for m in target_metabolites:
        for id_val in [m.get('hmdb'), m.get('chebi'), m.get('kegg')]:
            if id_val:
                target_index[id_val] = m
    
    # Fast matching
    matches = []
    for id_val in source_ids:
        if id_val in target_index:
            matches.append(target_index[id_val])
    
    return matches
```

### 3. Large File Processing

```python
# Process large TSV files in chunks
def process_large_file(file_path, chunk_size=10000):
    for chunk in pd.read_csv(file_path, sep='\t', chunksize=chunk_size):
        # Process chunk
        processed = process_chunk(chunk)
        yield processed
```

## Checklist Before Committing

- [ ] No nested loops over different collections
- [ ] No DataFrame.iterrows() in performance-critical code
- [ ] Used dictionary/set for lookups instead of list searches
- [ ] Benchmarked solution with realistic data sizes
- [ ] Added performance tests for critical paths
- [ ] Documented expected complexity in docstrings
- [ ] Used EfficientMatcher utilities where applicable

## Red Flags in Code Review

1. **Nested for loops** with different iterables
2. **DataFrame.iterrows()** especially if nested
3. **List comprehensions** with nested loops
4. **'in' operator** on lists in loops (use sets)
5. **Repeated API calls** in loops (batch them)
6. **String concatenation** in loops (use join)
7. **Sorting inside loops** (sort once outside)

## Getting Help

If you're unsure about algorithm complexity:

1. Use the complexity checker: `python audits/complexity_audit.py`
2. Run performance tests: `poetry run pytest tests/performance/`
3. Ask for review if dealing with large datasets (>10k items)
4. Profile before and after optimization

## Remember

**A single O(n*m) algorithm can turn a 2-minute process into a 3-hour nightmare.**

Always think about data size scaling:
- Will this work with 100 items? ✓
- Will this work with 10,000 items? ✓
- Will this work with 1,000,000 items? 🤔

When in doubt, use the EfficientMatcher utilities!