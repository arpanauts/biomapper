# Plan: Converting UKBB to HPA Protein Notebook to Service-Based Workflow

## Overview
This document outlines the steps to convert the Jupyter notebook logic from `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` into a service-based workflow using the biomapper-api.

## Current Notebook Analysis

### Notebook Structure
The notebook performs the following operations:

1. **Data Loading**: Reads UKBB and HPA protein datasets from local TSV/CSV files
2. **Data Exploration**: Analyzes the structure and content of both datasets
3. **Direct ID Resolution**: Uses UniProtHistoricalResolverClient to resolve UniProt IDs
4. **Overlap Analysis**: Calculates the overlap between UKBB and HPA proteins
5. **Pipeline Testing**: Attempts to use the UKBB_TO_HPA_PROTEIN_PIPELINE strategy

### Key Components Identified

#### Data Sources
- **UKBB**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
  - Columns: Assay (protein name), UniProt (ID), Panel (category)
  - 2,923 unique proteins
  
- **HPA**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`
  - Columns: gene (symbol), uniprot (ID), organ (specificity)
  - 2,994 unique proteins

#### Processing Steps
1. Extract UniProt IDs from both datasets
2. Handle composite IDs (e.g., "Q14213_Q8NEV9")
3. Resolve historical UniProt changes
4. Find overlap between datasets
5. Generate mapping results with provenance

## Service-Based Architecture Design

### 1. Strategy Actions Required

#### A. CompositeIdSplitter Action
```yaml
action_class_path: "biomapper.core.strategy_actions.composite_id_splitter.CompositeIdSplitter"
description: "Split composite UniProt IDs into individual components"
params:
  delimiter: "_"
  skip_prefixes: ["sp|", "tr|"]
```

#### B. UniProtHistoricalResolver Action (Already Exists)
```yaml
action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtHistoricalResolver"
description: "Resolve UniProt IDs to handle historical changes"
params:
  batch_size: 100
  include_metadata: true
```

#### C. DatasetOverlapAnalyzer Action
```yaml
action_class_path: "biomapper.core.strategy_actions.overlap_analyzer.DatasetOverlapAnalyzer"
description: "Analyze overlap between two identifier sets"
params:
  comparison_mode: "intersection"
  include_statistics: true
```

### 2. YAML Strategy Definition

Create `configs/ukbb_hpa_analysis_strategy.yaml`:

```yaml
mapping_strategies:
  - name: "UKBB_HPA_OVERLAP_ANALYSIS"
    description: "Analyze protein overlap between UKBB and HPA datasets with ID resolution"
    entity_type: "protein"
    default_source_ontology_type: "UKBB_PROTEIN_UNIPROT_ONTOLOGY"
    default_target_ontology_type: "HPA_OSP_UNIPROT_ONTOLOGY"
    steps:
      # Step 1: Load and preprocess UKBB UniProt IDs
      - step_id: "load_ukbb_ids"
        name: "Load UKBB UniProt IDs"
        action_class_path: "biomapper.core.strategy_actions.load_local_data.LoadLocalData"
        params:
          file_path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"
          file_format: "tsv"
          id_column: "UniProt"
          context_key: "ukbb_raw_ids"
      
      # Step 2: Split composite IDs in UKBB data
      - step_id: "split_ukbb_composites"
        name: "Split UKBB Composite IDs"
        action_class_path: "biomapper.core.strategy_actions.composite_id_splitter.CompositeIdSplitter"
        params:
          input_context_key: "ukbb_raw_ids"
          output_context_key: "ukbb_split_ids"
          delimiter: "_"
          track_provenance: true
      
      # Step 3: Resolve UKBB UniProt IDs
      - step_id: "resolve_ukbb_uniprot"
        name: "Resolve UKBB UniProt Historical Changes"
        action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtHistoricalResolver"
        params:
          input_context_key: "ukbb_split_ids"
          output_context_key: "ukbb_resolved_ids"
          batch_size: 100
          
      # Step 4: Load and preprocess HPA UniProt IDs
      - step_id: "load_hpa_ids"
        name: "Load HPA UniProt IDs"
        action_class_path: "biomapper.core.strategy_actions.load_local_data.LoadLocalData"
        params:
          file_path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv"
          file_format: "csv"
          id_column: "uniprot"
          context_key: "hpa_raw_ids"
      
      # Step 5: Split composite IDs in HPA data
      - step_id: "split_hpa_composites"
        name: "Split HPA Composite IDs"
        action_class_path: "biomapper.core.strategy_actions.composite_id_splitter.CompositeIdSplitter"
        params:
          input_context_key: "hpa_raw_ids"
          output_context_key: "hpa_split_ids"
          delimiter: "_"
          
      # Step 6: Resolve HPA UniProt IDs
      - step_id: "resolve_hpa_uniprot"
        name: "Resolve HPA UniProt Historical Changes"
        action_class_path: "biomapper.core.strategy_actions.uniprot_resolver.UniProtHistoricalResolver"
        params:
          input_context_key: "hpa_split_ids"
          output_context_key: "hpa_resolved_ids"
          batch_size: 100
          
      # Step 7: Analyze overlap
      - step_id: "analyze_overlap"
        name: "Analyze UKBB-HPA Overlap"
        action_class_path: "biomapper.core.strategy_actions.overlap_analyzer.DatasetOverlapAnalyzer"
        params:
          dataset1_context_key: "ukbb_resolved_ids"
          dataset2_context_key: "hpa_resolved_ids"
          dataset1_name: "UKBB"
          dataset2_name: "HPA"
          output_context_key: "overlap_results"
          generate_statistics: true
```

### 3. API Client Implementation

Create a Python client script `scripts/api_clients/ukbb_hpa_overlap_client.py`:

```python
import asyncio
import httpx
from typing import Dict, List, Optional
import json
from datetime import datetime

class UKBBHPAOverlapClient:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout
    
    async def check_api_health(self) -> bool:
        """Check if the API service is running"""
        try:
            response = await self.client.get(f"{self.api_base_url}/api/health")
            return response.status_code == 200
        except:
            return False
    
    async def execute_overlap_analysis(self) -> Dict:
        """Execute the UKBB-HPA overlap analysis strategy"""
        # First check API health
        if not await self.check_api_health():
            raise ConnectionError("biomapper-api service is not running")
        
        # Execute the strategy
        print("Starting UKBB-HPA overlap analysis...")
        response = await self.client.post(
            f"{self.api_base_url}/api/strategies/execute",
            json={
                "strategy_name": "UKBB_HPA_OVERLAP_ANALYSIS",
                "source_endpoint": "UKBB_PROTEIN",
                "target_endpoint": "HPA_OSP_PROTEIN",
                "input_identifiers": [],  # Strategy loads its own data
                "options": {
                    "use_cache": True,
                    "return_detailed_results": True
                }
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Strategy execution failed: {response.text}")
        
        result = response.json()
        mapping_id = result["mapping_id"]
        print(f"Mapping ID: {mapping_id}")
        
        # Poll for results
        return await self._poll_for_results(mapping_id)
    
    async def _poll_for_results(self, mapping_id: str, max_attempts: int = 60) -> Dict:
        """Poll for mapping results with progress updates"""
        for attempt in range(max_attempts):
            response = await self.client.get(
                f"{self.api_base_url}/api/mappings/{mapping_id}"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get mapping status: {response.text}")
            
            data = response.json()
            status = data["status"]
            
            if "progress" in data:
                print(f"Progress: {data['progress']['current']}/{data['progress']['total']} - {data['progress']['message']}")
            
            if status == "completed":
                return data["results"]
            elif status == "failed":
                raise Exception(f"Mapping failed: {data.get('error', 'Unknown error')}")
            
            await asyncio.sleep(5)  # Wait 5 seconds between polls
        
        raise TimeoutError("Mapping did not complete within timeout period")
    
    async def generate_report(self, results: Dict) -> str:
        """Generate a markdown report from the results"""
        report = f"""# UKBB-HPA Protein Overlap Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics

- **UKBB Proteins (Original):** {results['statistics']['ukbb_original_count']}
- **UKBB Proteins (After Composite Split):** {results['statistics']['ukbb_split_count']}
- **UKBB Proteins (After Resolution):** {results['statistics']['ukbb_resolved_count']}

- **HPA Proteins (Original):** {results['statistics']['hpa_original_count']}
- **HPA Proteins (After Composite Split):** {results['statistics']['hpa_split_count']}
- **HPA Proteins (After Resolution):** {results['statistics']['hpa_resolved_count']}

## Overlap Results

- **Direct Overlap (Before Processing):** {results['statistics']['direct_overlap_count']}
- **Overlap After Composite Splitting:** {results['statistics']['split_overlap_count']}
- **Overlap After Historical Resolution:** {results['statistics']['resolved_overlap_count']}

### Improvement Metrics

- **Composite ID Processing Gain:** {results['statistics']['split_overlap_count'] - results['statistics']['direct_overlap_count']} proteins
- **Historical Resolution Gain:** {results['statistics']['resolved_overlap_count'] - results['statistics']['split_overlap_count']} proteins
- **Total Improvement:** {results['statistics']['resolved_overlap_count'] - results['statistics']['direct_overlap_count']} proteins ({results['statistics']['improvement_percentage']:.1f}%)

## Sample Overlapping Proteins

{self._format_sample_proteins(results.get('sample_overlaps', []))}

## Provenance Information

- **Composite IDs Processed:** {len(results.get('composite_id_mappings', {}))}
- **Historical Resolutions:** {len(results.get('historical_resolutions', {}))}

"""
        return report
    
    def _format_sample_proteins(self, samples: List[Dict]) -> str:
        """Format sample protein information"""
        if not samples:
            return "No sample data available"
        
        lines = []
        for i, sample in enumerate(samples[:10], 1):
            lines.append(f"{i}. **{sample['id']}**")
            if 'gene_name' in sample:
                lines.append(f"   - Gene: {sample['gene_name']}")
            if 'protein_name' in sample:
                lines.append(f"   - Protein: {sample['protein_name']}")
            if 'provenance' in sample:
                lines.append(f"   - Provenance: {sample['provenance']}")
        
        return "\n".join(lines)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Main execution function"""
    client = UKBBHPAOverlapClient()
    
    try:
        # Execute the analysis
        results = await client.execute_overlap_analysis()
        
        # Generate and save report
        report = await client.generate_report(results)
        
        report_path = f"ukbb_hpa_overlap_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_path}")
        
        # Also save raw results as JSON
        json_path = f"ukbb_hpa_overlap_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Raw results saved to: {json_path}")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Integration Testing

Create integration tests `tests/integration/test_ukbb_hpa_service.py`:

```python
import pytest
import asyncio
from scripts.api_clients.ukbb_hpa_overlap_client import UKBBHPAOverlapClient

@pytest.mark.asyncio
async def test_ukbb_hpa_overlap_via_api():
    """Test the complete UKBB-HPA overlap analysis via API"""
    client = UKBBHPAOverlapClient()
    
    try:
        # Check API health
        assert await client.check_api_health(), "API service is not running"
        
        # Execute analysis
        results = await client.execute_overlap_analysis()
        
        # Verify results structure
        assert 'statistics' in results
        assert 'ukbb_resolved_count' in results['statistics']
        assert 'hpa_resolved_count' in results['statistics']
        assert 'resolved_overlap_count' in results['statistics']
        
        # Verify overlap was found
        assert results['statistics']['resolved_overlap_count'] > 0
        
        # Verify provenance tracking
        assert 'composite_id_mappings' in results
        assert 'historical_resolutions' in results
        
    finally:
        await client.close()
```

## Implementation Steps

### Phase 1: Core Development (Week 1)
1. **Implement CompositeIdSplitter action** in core library
2. **Implement DatasetOverlapAnalyzer action** in core library
3. **Create unit tests** for new actions
4. **Update YAML configuration** with new strategy

### Phase 2: API Integration (Week 2)
1. **Deploy updated biomapper-api** with new actions
2. **Test strategy execution** via API endpoints
3. **Implement progress reporting** for long-running analysis
4. **Add caching** for repeated analyses

### Phase 3: Client Development (Week 3)
1. **Develop Python client** as shown above
2. **Create CLI wrapper** for easy execution
3. **Add visualization support** for overlap results
4. **Document API usage** with examples

### Phase 4: Testing & Documentation (Week 4)
1. **Integration testing** of complete workflow
2. **Performance testing** with full datasets
3. **Create user documentation** for the service
4. **Deploy to production** environment

## Benefits of Service-Based Approach

1. **Scalability**: API can handle multiple concurrent requests
2. **Reusability**: Strategy can be executed by any API client
3. **Monitoring**: Centralized logging and metrics collection
4. **Caching**: Results cached at API level for efficiency
5. **Security**: API authentication and rate limiting
6. **Versioning**: API versioning for backward compatibility
7. **Progress Tracking**: Real-time updates for long operations

## Migration Checklist

- [ ] Extract data loading logic into LoadLocalData action
- [ ] Create CompositeIdSplitter action for ID preprocessing  
- [ ] Create DatasetOverlapAnalyzer for comparison logic
- [ ] Define YAML strategy with all steps
- [ ] Test strategy via biomapper-api
- [ ] Create Python client for API interaction
- [ ] Write integration tests
- [ ] Document API endpoints and usage
- [ ] Create migration guide for notebook users
- [ ] Deploy to production environment

## Future Enhancements

1. **Streaming Results**: Stream large result sets instead of loading all in memory
2. **Batch Processing**: Support multiple dataset comparisons in one request
3. **Export Formats**: Support various output formats (CSV, Excel, JSON)
4. **Visualization API**: Endpoint to generate overlap visualizations
5. **Scheduled Execution**: Run analysis on a schedule with change detection
6. **Webhook Notifications**: Notify when analysis completes
7. **Result Persistence**: Store results in database for historical tracking