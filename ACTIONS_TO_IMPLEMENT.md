# Actions That Need Implementation for V2.2 Strategy

## 🔴 Missing Actions (Need Full Implementation)

### 1. **PARSE_COMPOSITE_IDENTIFIERS** (From Parallel Team 1)
**Purpose:** Handle comma-separated UniProt IDs like "Q8NEV9,Q14213"
**Location:** `biomapper/core/strategy_actions/utils/data_processing/parse_composite_identifiers.py`
```python
class ParseCompositeIdentifiersAction:
    # Params: dataset_key, id_field, separators, output_key, track_expansion
    # Expands rows with composite IDs into multiple rows
    # Tracks expansion factor in statistics
```

### 2. **PROTEIN_EXTRACT_UNIPROT_FROM_XREFS** 
**Purpose:** Extract UniProt IDs from cross-reference fields
**Location:** `biomapper/core/strategy_actions/entities/proteins/annotation/extract_uniprot_from_xrefs.py`
```python
class ProteinExtractUniProtFromXrefsAction:
    # Params: dataset_key, xref_columns, output_key
    # Extracts UniProt IDs from various xref columns
```

### 3. **PROTEIN_NORMALIZE_ACCESSIONS**
**Purpose:** Normalize protein accession formats
**Location:** `biomapper/core/strategy_actions/entities/proteins/annotation/normalize_accessions.py`
```python
class ProteinNormalizeAccessionsAction:
    # Params: dataset_key, id_column, output_key
    # Standardizes UniProt accession formats
```

### 4. **PROTEIN_HISTORICAL_RESOLUTION**
**Purpose:** Resolve deprecated/updated UniProt IDs
**Location:** `biomapper/core/strategy_actions/entities/proteins/matching/historical_resolution.py`
```python
class ProteinHistoricalResolutionAction:
    # Params: dataset_key, unmatched_from, reference_dataset, output_key
    # Uses UniProt history API to resolve old IDs
```

### 5. **PROTEIN_GENE_SYMBOL_BRIDGE**
**Purpose:** Map proteins via gene symbols
**Location:** `biomapper/core/strategy_actions/entities/proteins/matching/gene_symbol_bridge.py`
```python
class ProteinGeneSymbolBridgeAction:
    # Params: dataset_key, unmatched_from, reference_dataset, output_key
    # Maps proteins through gene symbol intermediates
```

### 6. **PROTEIN_ENSEMBL_BRIDGE**
**Purpose:** Map proteins via Ensembl IDs
**Location:** `biomapper/core/strategy_actions/entities/proteins/matching/ensembl_bridge.py`
```python
class ProteinEnsemblBridgeAction:
    # Params: dataset_key, unmatched_from, reference_dataset, output_key
    # Maps proteins through Ensembl gene/transcript IDs
```

### 7. **CALCULATE_MAPPING_STATISTICS**
**Purpose:** Calculate comprehensive mapping statistics
**Location:** `biomapper/core/strategy_actions/reports/calculate_mapping_statistics.py`
```python
class CalculateMappingStatisticsAction:
    # Params: dataset_key, grouping_columns, confidence_column, output_key
    # Calculates match rates, confidence distributions, etc.
```

### 8. **ANALYZE_ONE_TO_MANY_MAPPINGS**
**Purpose:** Analyze one-to-many mapping patterns
**Location:** `biomapper/core/strategy_actions/reports/analyze_one_to_many.py`
```python
class AnalyzeOneToManyMappingsAction:
    # Params: dataset_key, source_column, target_column, output_key
    # Identifies and analyzes one-to-many mappings
```

### 9. **GENERATE_MAPPING_VISUALIZATIONS** (From Parallel Team 3)
**Purpose:** Generate charts and graphs
**Location:** `biomapper/core/strategy_actions/reports/generate_visualizations.py`
```python
class GenerateMappingVisualizationsAction:
    # Params: dataset_keys, output_dir, formats, charts, style
    # Creates: pie charts, histograms, Sankey diagrams, scatter plots
```

### 10. **GENERATE_HTML_REPORT** (From Parallel Team 2) 
**Purpose:** Generate comprehensive HTML reports
**Location:** `biomapper/core/strategy_actions/reports/generate_html_report.py`
```python
class GenerateHtmlReportAction:
    # Params: template_name, title, output_path, sections
    # Uses Jinja2 templates for professional reports
```

### 11. **EXPORT_MAPPING_SUMMARY**
**Purpose:** Export mapping summary as JSON
**Location:** `biomapper/core/strategy_actions/io/export_mapping_summary.py`
```python
class ExportMappingSummaryAction:
    # Params: statistics_key, one_to_many_key, output_path
    # Exports comprehensive JSON summary
```

## 🟡 Actions That Need Fixes

### 1. **EXPORT_DATASET**
**Issue:** Missing `get_result_model()` method
**Fix:** Add the required method to comply with TypedStrategyAction base class

### 2. **FILTER_DATASET** 
**Issue:** Missing `execute` method or incorrect inheritance
**Fix:** Ensure proper TypedStrategyAction implementation

### 3. **MERGE_DATASETS**
**Issue:** Parameter compatibility (from Parallel Team 2)
**Fix:** Support both old format (dataset1_key, dataset2_key) and new format (dataset_keys list)

## 🟢 Working Actions

These actions already exist and work:
- `LOAD_DATASET_IDENTIFIERS` ✅
- `CALCULATE_SET_OVERLAP` ✅
- `CUSTOM_TRANSFORM` ✅ (but basic)
- `SYNC_TO_GOOGLE_DRIVE` ✅ (needs credentials)

## Implementation Priority

### Phase 1: Core Functionality (Required for basic v2.2)
1. Fix `EXPORT_DATASET` - Critical for output
2. Fix `FILTER_DATASET` - Needed for unmapped identification
3. Fix `MERGE_DATASETS` - Ensure backward compatibility

### Phase 2: Enhanced Protein Mapping
4. `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`
5. `PROTEIN_NORMALIZE_ACCESSIONS`
6. `PARSE_COMPOSITE_IDENTIFIERS`

### Phase 3: Progressive Matching
7. `PROTEIN_HISTORICAL_RESOLUTION`
8. `PROTEIN_GENE_SYMBOL_BRIDGE` 
9. `PROTEIN_ENSEMBL_BRIDGE`

### Phase 4: Reporting & Visualization
10. `CALCULATE_MAPPING_STATISTICS`
11. `ANALYZE_ONE_TO_MANY_MAPPINGS`
12. `GENERATE_HTML_REPORT`
13. `GENERATE_MAPPING_VISUALIZATIONS`
14. `EXPORT_MAPPING_SUMMARY`

## TDD Implementation Approach

For each action:
1. Create test file: `tests/unit/core/strategy_actions/test_[action_name].py`
2. Write comprehensive tests FIRST
3. Implement minimal code to pass tests
4. Refactor while keeping tests green
5. Ensure 80%+ coverage

## Example Implementation Template

```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel, Field
from typing import Dict, Any

class MyActionParams(BaseModel):
    dataset_key: str = Field(..., description="Input dataset key")
    output_key: str = Field(..., description="Output dataset key")
    # Add other parameters

class MyActionResult(BaseModel):
    success: bool
    message: str
    rows_processed: int = 0

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, MyActionResult]):
    
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    def get_result_model(self) -> type[MyActionResult]:
        return MyActionResult
    
    async def execute_typed(
        self, 
        params: MyActionParams, 
        context: Dict[str, Any]
    ) -> MyActionResult:
        # Implementation
        try:
            # Access input data
            input_data = context["datasets"].get(params.dataset_key, [])
            
            # Process data
            processed_data = self.process(input_data)
            
            # Store output
            context["datasets"][params.output_key] = processed_data
            
            return MyActionResult(
                success=True,
                message=f"Processed {len(processed_data)} rows",
                rows_processed=len(processed_data)
            )
        except Exception as e:
            return MyActionResult(
                success=False,
                message=str(e),
                rows_processed=0
            )
    
    def process(self, data):
        # Actual processing logic
        return data
```

## Notes

- All actions must inherit from `TypedStrategyAction`
- All actions must use `@register_action` decorator
- Handle both dict and MockContext in context parameter
- Data flows as list of dicts between actions
- Store results in `context["datasets"][output_key]`
- Track statistics in `context["statistics"]`