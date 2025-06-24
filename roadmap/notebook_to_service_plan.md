# Plan: Convert UKBB to HPA Protein Notebook to Service-Based Workflow

## Overview

This document outlines the plan to convert the Jupyter notebook at `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` into a service-based workflow using the Biomapper API infrastructure. The notebook currently performs protein mapping between UK Biobank (UKBB) and Human Protein Atlas (HPA) datasets.

## Current Notebook Analysis

### Notebook Functionality
The notebook performs the following operations:
1. **Data Loading**: Loads UKBB and HPA protein datasets from TSV/CSV files
2. **ID Extraction**: Extracts UniProt IDs from both datasets
3. **ID Resolution**: Uses UniProtHistoricalResolverClient to resolve historical UniProt ID changes
4. **Overlap Analysis**: Calculates the overlap between UKBB and HPA proteins
5. **Pipeline Execution**: Attempts to run the UKBB_TO_HPA_PROTEIN_PIPELINE strategy

### Key Components Used
- **Data Sources**: 
  - UKBB: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
  - HPA: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`
- **Core Libraries**: `biomapper.core.mapping_executor.MappingExecutor`
- **Clients**: `biomapper.mapping.clients.uniprot_historical_resolver_client.UniProtHistoricalResolverClient`

## Service Architecture Design

### 1. API Endpoints Required

#### 1.1 File Management Endpoints (Existing)
- `POST /api/files/upload` - Upload UKBB/HPA CSV files
- `GET /api/files/{session_id}/preview` - Preview uploaded data
- `POST /api/files/server/list` - List available server files

#### 1.2 New Mapping Endpoints
- `POST /api/mapping/ukbb-to-hpa` - Execute UKBB to HPA protein mapping
- `GET /api/mapping/strategies` - List available mapping strategies
- `POST /api/mapping/strategies/{strategy_name}/execute` - Execute a named strategy

### 2. Strategy Actions Required

#### 2.1 DataLoadingAction
```yaml
name: "Load Protein Data"
action_class_path: "biomapper.core.strategy_actions.data_loader.DataLoadingAction"
params:
  source: "session_file"  # or "server_file"
  file_type: "csv"
  delimiter: "\t"
  required_columns: ["UniProt", "Assay"]  # For UKBB
```

#### 2.2 IdExtractionAction
```yaml
name: "Extract UniProt IDs"
action_class_path: "biomapper.core.strategy_actions.id_extractor.IdExtractionAction"
params:
  column_name: "UniProt"
  handle_composite_ids: true
  composite_delimiter: "_"
```

#### 2.3 UniProtResolutionAction
```yaml
name: "Resolve UniProt History"
action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtResolutionAction"
params:
  batch_size: 100
  include_obsolete: true
  cache_results: true
```

#### 2.4 DatasetOverlapAction
```yaml
name: "Calculate Dataset Overlap"
action_class_path: "biomapper.core.strategy_actions.overlap_analyzer.DatasetOverlapAction"
params:
  dataset1_key: "ukbb_resolved_ids"
  dataset2_key: "hpa_resolved_ids"
  output_format: "detailed"
```

### 3. Complete YAML Strategy Definition

```yaml
name: "ukbb_to_hpa_protein_service"
description: "Service-oriented UKBB to HPA protein mapping with overlap analysis"
version: "2.0.0"
api_config:
  timeout: 1800  # 30 minutes
  memory_limit: "2GB"
  
inputs:
  - name: "ukbb_session_id"
    type: "string"
    description: "Session ID for uploaded UKBB file"
  - name: "hpa_session_id"
    type: "string"
    description: "Session ID for uploaded HPA file"
    
steps:
  - name: "Load UKBB Data"
    action_class_path: "biomapper.core.strategy_actions.data_loader.DataLoadingAction"
    params:
      source: "session_file"
      session_id_key: "ukbb_session_id"
      required_columns: ["UniProt", "Assay", "Panel"]
      output_key: "ukbb_data"
      
  - name: "Load HPA Data"
    action_class_path: "biomapper.core.strategy_actions.data_loader.DataLoadingAction"
    params:
      source: "session_file"
      session_id_key: "hpa_session_id"
      required_columns: ["uniprot", "gene", "organ"]
      output_key: "hpa_data"
      
  - name: "Extract UKBB UniProt IDs"
    action_class_path: "biomapper.core.strategy_actions.id_extractor.IdExtractionAction"
    params:
      input_key: "ukbb_data"
      column_name: "UniProt"
      handle_composite_ids: true
      output_key: "ukbb_uniprot_ids"
      
  - name: "Extract HPA UniProt IDs"
    action_class_path: "biomapper.core.strategy_actions.id_extractor.IdExtractionAction"
    params:
      input_key: "hpa_data"
      column_name: "uniprot"
      handle_composite_ids: true
      output_key: "hpa_uniprot_ids"
      
  - name: "Resolve UKBB UniProt History"
    action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtResolutionAction"
    params:
      input_key: "ukbb_uniprot_ids"
      batch_size: 100
      output_key: "ukbb_resolved"
      
  - name: "Resolve HPA UniProt History"
    action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtResolutionAction"
    params:
      input_key: "hpa_uniprot_ids"
      batch_size: 100
      output_key: "hpa_resolved"
      
  - name: "Calculate Overlap"
    action_class_path: "biomapper.core.strategy_actions.overlap_analyzer.DatasetOverlapAction"
    params:
      dataset1_key: "ukbb_resolved"
      dataset2_key: "hpa_resolved"
      calculate_statistics: true
      output_key: "overlap_results"
      
  - name: "Generate Mapping Report"
    action_class_path: "biomapper.core.strategy_actions.report_generator.MappingReportAction"
    params:
      include_sections:
        - "summary_statistics"
        - "overlap_analysis"
        - "id_resolution_provenance"
        - "unmapped_identifiers"
      output_format: "json"
```

## Implementation Steps

### Phase 1: Create Strategy Actions (Week 1)
1. Implement `DataLoadingAction` to handle file uploads and server files
2. Implement `IdExtractionAction` with composite ID handling
3. Implement `UniProtResolutionAction` wrapping the existing client
4. Implement `DatasetOverlapAction` for overlap calculations
5. Implement `MappingReportAction` for comprehensive result generation

### Phase 2: API Integration (Week 2)
1. Create new router `/api/mapping/strategies` for strategy management
2. Implement endpoint to list available strategies from YAML configs
3. Implement generic strategy execution endpoint
4. Add specific endpoint for UKBB-HPA mapping with simplified interface
5. Update MapperService to support strategy-based execution

### Phase 3: Testing & Validation (Week 3)
1. Create unit tests for each new StrategyAction
2. Create integration tests for the complete workflow
3. Validate results match the notebook output
4. Performance testing with large datasets
5. Error scenario testing (missing columns, invalid IDs, etc.)

### Phase 4: UI Integration (Week 4)
1. Add "UKBB to HPA Mapping" option to UI
2. Create dual file upload interface
3. Display progress during multi-step execution
4. Create visualization for overlap results
5. Add export functionality for mapping results

## API Usage Example

### 1. Upload Files
```bash
# Upload UKBB file
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@UKBB_Protein_Meta.tsv" \
  -F "id_columns=UniProt"
# Returns: {"session_id": "ukbb_123", ...}

# Upload HPA file  
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@hpa_osps.csv" \
  -F "id_columns=uniprot"
# Returns: {"session_id": "hpa_456", ...}
```

### 2. Execute Mapping
```bash
curl -X POST http://localhost:8000/api/mapping/ukbb-to-hpa \
  -H "Content-Type: application/json" \
  -d '{
    "ukbb_session_id": "ukbb_123",
    "hpa_session_id": "hpa_456",
    "include_provenance": true
  }'
# Returns: {"job_id": "job_789", "status": "pending"}
```

### 3. Check Status
```bash
curl http://localhost:8000/api/mapping/jobs/job_789/status
# Returns: {"status": "processing", "progress": 0.45, "current_step": "Resolving UniProt History"}
```

### 4. Get Results
```bash
curl http://localhost:8000/api/mapping/jobs/job_789/results
# Returns comprehensive mapping results with overlap analysis
```

## Benefits of Service-Based Approach

1. **Scalability**: Can handle large datasets through async processing
2. **Reusability**: Strategy actions can be reused in other workflows
3. **Progress Tracking**: Users can monitor long-running operations
4. **Error Recovery**: Failed jobs can be retried or debugged
5. **Multi-User Support**: Multiple users can run mappings concurrently
6. **API Documentation**: Automatic OpenAPI docs for all endpoints
7. **Standardization**: Consistent interface for all mapping types

## Migration Considerations

1. **Data Access**: Service needs access to server-side data files or upload capability
2. **Memory Management**: Large datasets require streaming/chunking
3. **Caching**: UniProt resolution results should be cached
4. **Authentication**: Consider adding auth for production deployment
5. **Rate Limiting**: Protect against API abuse
6. **Monitoring**: Add metrics for performance tracking

## Success Metrics

- Service can process the same UKBB/HPA datasets as the notebook
- Results match notebook output (overlap counts, resolved IDs)
- Processing time is comparable or better than notebook
- API handles errors gracefully
- Progress tracking provides meaningful updates
- Results are easily consumable by downstream applications