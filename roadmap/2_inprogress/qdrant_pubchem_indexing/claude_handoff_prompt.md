# Claude Handoff Prompt: PubChem Embedding Filtering and Qdrant Indexing

## Project Context

You are working on the Biomapper project, specifically on filtering and indexing PubChem embeddings for a RAG-based metabolite mapping system. The goal is to improve the current low mapping success rate (0.2-0.5%) by using semantic search over biologically relevant compound embeddings.

## Current Status

### Completed Work
1. **Bio-relevant CID Allowlist Created**: 
   - Successfully processed HMDB, ChEBI, and UniChem data
   - Created expanded allowlist with 2,705,066 unique biologically relevant CIDs
   - Location: `/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt`

2. **Dataset Analysis Completed**:
   - PubChem embeddings location: `/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/`
   - 347 tar.gz files containing JSON files
   - Each JSON file contains 100 embeddings (CID -> 384-dimensional vector)
   - Total: 89,398,400 embeddings (~89.4 million, not 894k as originally thought)
   - Coverage: 51.68% of PubChem's 173M CID range
   - Expected overlap with our allowlist: ~1.4 million compounds

3. **Filtering Script Updated**:
   - Script: `/home/ubuntu/biomapper/scripts/filter_pubchem_embeddings.py`
   - Updated to handle actual JSON format (100 embeddings per file)
   - Added resumability and progress tracking
   - Configured to use expanded allowlist

## Your Immediate Tasks

### Task 1: Test Filtering Script on Sample Data
Before running the full filtering process, test on a small sample:

```bash
# Create a test directory
mkdir -p /home/ubuntu/biomapper/data/test_filtering

# Test with just the first chunk
python3 /home/ubuntu/biomapper/scripts/filter_pubchem_embeddings.py \
    --embeddings-dir /procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks \
    --output-dir /home/ubuntu/biomapper/data/test_filtering \
    --skip-qdrant-format \
    --resume-from 0

# After it processes the first chunk, interrupt with Ctrl+C
# Check the output
ls -la /home/ubuntu/biomapper/data/test_filtering/
cat /home/ubuntu/biomapper/data/test_filtering/processing_stats.json
```

### Task 2: Run Full Filtering Process
Once the test is successful:

```bash
# Run the full filtering (this will take several hours)
nohup python3 /home/ubuntu/biomapper/scripts/filter_pubchem_embeddings.py \
    --embeddings-dir /procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks \
    --output-dir /home/ubuntu/biomapper/data/filtered_embeddings \
    > /home/ubuntu/biomapper/data/filtering_log.txt 2>&1 &

# Monitor progress
tail -f /home/ubuntu/biomapper/data/filtering_log.txt
```

### Task 3: Set Up Qdrant Docker Instance
While filtering is running, set up Qdrant:

1. Create Docker Compose file at `/home/ubuntu/biomapper/docker/qdrant/docker-compose.yml`:
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
```

2. Start Qdrant:
```bash
cd /home/ubuntu/biomapper/docker/qdrant
docker-compose up -d
```

### Task 4: Create Indexing Script
Create `/home/ubuntu/biomapper/scripts/rag/index_pubchem_embeddings.py` following the design in:
- `/home/ubuntu/biomapper/roadmap/2_inprogress/qdrant_pubchem_indexing/design.md`

Key requirements:
- Load the filtered embeddings from pickle files
- Create Qdrant collection with 384 dimensions, Cosine distance
- Batch upload (recommended batch size: 1000-5000)
- Progress tracking and resumability
- Use the CID as the point ID (or the mapping created by filter script)

### Task 5: Index to Qdrant
Once filtering is complete and Qdrant is running:

```bash
python3 /home/ubuntu/biomapper/scripts/rag/index_pubchem_embeddings.py \
    --input-path /home/ubuntu/biomapper/data/pubchem_bio_embeddings_qdrant.pkl.gz \
    --qdrant-host localhost \
    --qdrant-port 6333 \
    --collection-name pubchem_bge_small_v1_5 \
    --batch-size 5000
```

## Important Considerations

1. **Memory Management**: The filtering process handles large files. Monitor system memory usage.

2. **Disk Space**: Ensure sufficient space for:
   - Filtered embeddings: ~10-20GB estimated
   - Qdrant storage: ~15-25GB estimated

3. **Resume Capability**: If filtering is interrupted, use `--resume-from N` where N is the last completed chunk index.

4. **Validation**: After indexing, test with known metabolite CIDs to verify the system works.

## Project Documentation

- Feature folder: `/home/ubuntu/biomapper/roadmap/2_inprogress/qdrant_pubchem_indexing/`
- Task list: `task_list.md` in feature folder
- Implementation notes: `implementation_notes.md` in feature folder
- RAG strategy: `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`

## Success Criteria

1. Successfully filter ~1.4M biologically relevant embeddings from 89.4M total
2. Index filtered embeddings into Qdrant
3. Achieve query latency < 100ms for vector search
4. Document the entire process for future reference

## Questions to Address

1. What's the optimal batch size for Qdrant uploads given our server resources?
2. Should we implement parallel processing for the filtering step?
3. How should we handle CIDs that can't be converted to integers for Qdrant IDs?

## Next Steps After Completion

1. Update the `PubChemRAGMappingClient` to use the indexed embeddings
2. Test with challenging metabolite names that current methods fail to map
3. Measure improvement in mapping success rate
4. Document performance metrics and resource usage

Remember to update the implementation notes in the feature folder as you progress!
