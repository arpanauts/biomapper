# Implementation Notes: Qdrant Setup and PubChem Embedding Indexing

## Date: 2025-05-23

### Progress:

- Completed creation and expansion of bio-relevant CID allowlist (2.7M CIDs)
- Analyzed PubChem embeddings dataset structure - discovered 89.4M embeddings (not 894k)
- Verified embeddings format: JSON files with 100 embeddings each, 384-dimensional vectors
- Identified existing `filter_pubchem_embeddings.py` script that needs updates

### Decisions Made:

- Use expanded allowlist with UniChem data for better biological coverage
- Process embeddings in memory-efficient batches due to large dataset size
- Maintain original 384-dimensional vectors from BAAI/bge-small-en-v1.5 model
- Target ~1.4M filtered embeddings based on 51.68% coverage rate

### Challenges Encountered:

- Dataset size significantly larger than originally estimated (100x)
- Existing filtering script assumes wrong file format (individual CID files vs JSON batches)
- Memory constraints require careful batch processing strategy

### Next Steps:

- Update `filter_pubchem_embeddings.py` to handle actual JSON batch format
- Implement proper tar.gz extraction and JSON parsing logic
- Add progress tracking and resumability features to handle 347 chunks

## Date: 2025-05-23 (Update 2)

### Progress:

- Successfully tested filtering script on sample data
- Started full filtering process with nohup (currently processing chunk 6/346)
- Set up Qdrant Docker instance successfully (running on ports 6333/6334)
- Created comprehensive indexing script with features:
  - Support for both single file and directory input
  - Batch uploading with progress tracking
  - Resumability for interrupted uploads
  - Optimized Qdrant collection settings for semantic search
  - Test search functionality to verify indexing

### Decisions Made:

- Use timeout-based testing for initial script validation
- Run filtering as background process due to multi-hour duration
- Configure Qdrant with:
  - Cosine distance for semantic similarity
  - HNSW indexing after 10k vectors
  - Batch size of 5000 for uploads
  - Optimized segment and indexing thresholds

### Challenges Encountered:

- First chunk contains 3387 JSON files, taking ~80 seconds to process
- Estimated total processing time: 6-8 hours for all 346 chunks
- Need to handle both integer CIDs and non-integer CIDs in Qdrant IDs

### Next Steps:

- Monitor filtering progress and check for completion
- Once filtering completes, run indexing script
- Test with known metabolite CIDs to verify system functionality
- Update PubChemRAGMappingClient to use indexed embeddings
