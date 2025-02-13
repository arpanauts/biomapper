# Filtering Cardiolipins from HMDB Matches

## Background
When searching for metabolite matches in HMDB using vector similarity, cardiolipins often appear in search results but rarely represent meaningful matches. This is due to several factors:

1. **Complex Structure**: Cardiolipins are large phospholipids with four fatty acid chains attached to two phosphatidyl groups, making them structurally distinct from most metabolites.

2. **Verbose Naming**: Cardiolipin names in HMDB contain extensive structural information (e.g., "CL(14:0/i-21:0/23:0/a-25:0)"), which can create noise in text matching.

3. **Different Biochemical Role**: Cardiolipins are primarily structural membrane lipids found in mitochondria, while most metabolites we're matching are smaller metabolic intermediates or signaling molecules.

## Implementation
To improve search result quality, we implemented a simple filtering approach:

```python
# Get more initial results since we'll filter some out
similar_compounds = await mapper.vector_store.get_similar(
    query=query,
    k=10
)

# Filter out cardiolipins
filtered_compounds = []
for doc in similar_compounds:
    if not any(x in doc.name.lower() for x in ['cardiolipin', 'cl(']):
        filtered_compounds.append(doc)
    if len(filtered_compounds) >= 5:
        break
```

The filtering works by:
- Converting compound names to lowercase for case-insensitive matching
- Excluding compounds containing either 'cardiolipin' or 'cl(' patterns
- Maintaining a maximum of 5 filtered results

## Future Improvements
Potential enhancements to the filtering system could include:
- Adding more compound classes that aren't useful for matching
- Implementing more sophisticated chemical structure-based filtering
- Using substructure matching to identify specific molecular patterns
- Adding configurable filtering rules based on compound properties

## Related
- [[HMDB compound matching]]
- [[Vector similarity search]]
- [[Metabolite identification]]
