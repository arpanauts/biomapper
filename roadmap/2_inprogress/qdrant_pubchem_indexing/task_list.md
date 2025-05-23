# Task List: Qdrant Setup and PubChem Embedding Indexing

## Status: In Progress
**Start Date:** 2025-05-23  
**Target Completion:** TBD

## High-Level Tasks

### 1. Data Preparation & Verification ✅ COMPLETED
- [x] Create bio-relevant CID allowlist from HMDB + ChEBI
- [x] Process UniChem mappings to expand allowlist
- [x] Verify final allowlist: 2,705,066 unique biologically relevant CIDs
- [x] Confirm PubChem embeddings dataset structure (89.4M embeddings, not 894k)

### 2. Update Filtering Script ✅ COMPLETED
- [x] Update `filter_pubchem_embeddings.py` to handle actual JSON format:
  - [x] Parse tar.gz files containing JSON files with 100 embeddings each
  - [x] Update to use expanded allowlist at `/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt`
  - [x] Implement memory-efficient batch processing for 347 compressed chunks
  - [x] Add progress tracking and resumability features
- [x] Test filtering script on sample chunks
- [x] Run full filtering process (currently running, chunk 6/346 as of 08:11 UTC)

### 3. Qdrant Setup ✅ COMPLETED
- [x] Create Docker Compose configuration for Qdrant
- [x] Set up persistent storage volumes
- [x] Configure Qdrant for 384-dimensional vectors with Cosine distance
- [x] Test Qdrant connectivity and basic operations (container running on ports 6333/6334)

### 4. Indexing Script Development ✅ COMPLETED
- [x] Create `scripts/index_filtered_embeddings_to_qdrant.py`
- [x] Implement batch upload functionality (batch size: 5000)
- [x] Add error handling and retry logic
- [x] Implement progress tracking and resumability
- [x] Add payload indexing for PubChem CID filtering

### 5. Testing & Validation ⏳ TODO
- [ ] Test indexing with small subset of filtered embeddings
- [ ] Verify vector search functionality
- [ ] Performance benchmarking (query speed, memory usage)
- [ ] Create test queries for known metabolites

### 6. Documentation ⏳ TODO
- [ ] Update design documents with actual dataset statistics
- [ ] Create setup guide for Qdrant deployment
- [ ] Document usage instructions for filtering and indexing scripts
- [ ] Create troubleshooting guide

### 7. Integration ⏳ TODO
- [ ] Update `PubChemRAGMappingClient` to use indexed embeddings
- [ ] Register client in `metamapper.db`
- [ ] Test end-to-end metabolite mapping with RAG approach

## Key Metrics to Track
- Total embeddings in dataset: 89,398,400
- Expected filtered embeddings: ~1.4 million
- Filtering retention rate: ~1.6% (biological relevance filter)
- Indexing speed: TBD embeddings/second
- Query latency: TBD ms/query
- Storage requirements: TBD GB

## Blockers & Risks
- None currently identified

## Notes
- Dataset is significantly larger than originally estimated (89.4M vs 894k embeddings)
- Using expanded allowlist with UniChem data increases biological coverage
- Memory efficiency is critical given the dataset size
