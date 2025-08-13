# PARALLEL 2B: Implement Chemistry & NMR Actions Bundle

**Prerequisites: PRIORITY_1_fix_variable_substitution.md must be completed first**

## Problem Statement

Chemistry and Nightingale NMR strategies are failing due to missing action implementations. These actions are critical for clinical chemistry data harmonization and NMR biomarker matching.

## Objective

Implement a bundle of chemistry-related actions that work together to enable LOINC extraction, fuzzy matching, vendor harmonization, and NMR biomarker matching.

## Actions to Implement

### 1. CHEMISTRY_EXTRACT_LOINC
Extracts LOINC codes from clinical chemistry test names and metadata.

### 2. CHEMISTRY_FUZZY_TEST_MATCH  
Performs fuzzy matching of clinical test names across different naming conventions.

### 3. CHEMISTRY_VENDOR_HARMONIZATION
Harmonizes test results from different vendors (LabCorp, Quest, Mayo, etc.).

### 4. CHEMISTRY_TO_PHENOTYPE_BRIDGE
Maps chemistry results to phenotypic features for disease association.

## Implementation Plan

### Part 1: CHEMISTRY_EXTRACT_LOINC

Create `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/chemistry/identification/extract_loinc.py`:

```python
"""
LOINC extraction action for clinical chemistry data.

Extracts and validates LOINC codes from various sources including
direct LOINC columns, test names, and vendor-specific identifiers.
"""

from typing import Dict, Any, List, Optional, Set
import pandas as pd
import re
import logging
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.models import ActionResult

logger = logging.getLogger(__name__)

class ChemistryExtractLOINCParams(BaseModel):
    """Parameters for LOINC extraction."""
    input_key: str = Field(..., description="Key for input chemistry data")
    output_key: str = Field(..., description="Key for output with LOINC codes")
    loinc_column: Optional[str] = Field(None, description="Direct LOINC column if exists")
    test_name_column: str = Field("test_name", description="Column with test names")
    vendor_column: Optional[str] = Field(None, description="Vendor/source column")
    vendor_id_column: Optional[str] = Field(None, description="Vendor-specific ID column")
    validate_format: bool = Field(True, description="Validate LOINC format")
    add_metadata: bool = Field(True, description="Add LOINC metadata")

@register_action("CHEMISTRY_EXTRACT_LOINC")
class ChemistryExtractLOINCAction(TypedStrategyAction[ChemistryExtractLOINCParams, ActionResult]):
    """Extract and validate LOINC codes from chemistry data."""
    
    # Common test name to LOINC mappings
    COMMON_LOINC_MAP = {
        'glucose': '2345-7',
        'blood glucose': '2345-7',
        'cholesterol': '2093-3',
        'cholesterol total': '2093-3',
        'hdl': '2085-9',
        'hdl cholesterol': '2085-9',
        'ldl': '2089-1',
        'ldl cholesterol': '2089-1',
        'triglycerides': '2571-8',
        'hemoglobin a1c': '4548-4',
        'hba1c': '4548-4',
        'creatinine': '2160-0',
        'egfr': '77147-7',
        'alt': '1742-6',
        'ast': '1920-8',
        'tsh': '3016-3',
        'vitamin d': '1989-3',
        '25-hydroxyvitamin d': '1989-3'
    }
    
    # Vendor-specific patterns
    VENDOR_PATTERNS = {
        'labcorp': r'^\d{6}$',  # 6-digit codes
        'quest': r'^[A-Z0-9]{4,6}$',  # Alphanumeric codes
        'mayo': r'^[A-Z]{2,4}\d{0,3}$'  # Letter prefix with optional numbers
    }
    
    def get_params_model(self) -> type[ChemistryExtractLOINCParams]:
        return ChemistryExtractLOINCParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult
    
    async def execute_typed(
        self,
        params: ChemistryExtractLOINCParams,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Extract LOINC codes from chemistry data."""
        try:
            # Get input data
            if params.input_key not in context:
                raise ValueError(f"Input key '{params.input_key}' not found")
            
            input_data = context[params.input_key]
            df = self._to_dataframe(input_data)
            
            logger.info(f"Extracting LOINC codes from {len(df)} chemistry records")
            
            # Extract LOINC codes
            loinc_codes = []
            extraction_methods = []
            
            for idx, row in df.iterrows():
                loinc, method = await self._extract_loinc_from_row(row, params)
                loinc_codes.append(loinc)
                extraction_methods.append(method)
            
            # Add to dataframe
            df['extracted_loinc'] = loinc_codes
            df['extraction_method'] = extraction_methods
            
            # Validate if requested
            if params.validate_format:
                df['loinc_valid'] = df['extracted_loinc'].apply(self._validate_loinc_format)
            
            # Add metadata if requested
            if params.add_metadata:
                df = await self._add_loinc_metadata(df)
            
            # Calculate statistics
            total_records = len(df)
            extracted_count = df['extracted_loinc'].notna().sum()
            valid_count = df['loinc_valid'].sum() if 'loinc_valid' in df else extracted_count
            
            # Store result
            context[params.output_key] = {
                'data': df.to_dict('records'),
                'statistics': {
                    'total_records': total_records,
                    'loinc_extracted': extracted_count,
                    'loinc_valid': valid_count,
                    'extraction_rate': extracted_count / total_records if total_records > 0 else 0
                }
            }
            
            return ActionResult(
                success=True,
                message=f"Extracted {extracted_count}/{total_records} LOINC codes",
                data={
                    'extraction_rate': extracted_count / total_records if total_records > 0 else 0,
                    'methods_used': list(set(m for m in extraction_methods if m))
                }
            )
            
        except Exception as e:
            logger.error(f"LOINC extraction failed: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )
    
    async def _extract_loinc_from_row(
        self,
        row: pd.Series,
        params: ChemistryExtractLOINCParams
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract LOINC from a single row using multiple strategies."""
        
        # Strategy 1: Direct LOINC column
        if params.loinc_column and params.loinc_column in row:
            loinc = str(row[params.loinc_column]).strip()
            if loinc and loinc.lower() not in ['nan', 'none', '']:
                return loinc, 'direct_column'
        
        # Strategy 2: Test name mapping
        if params.test_name_column in row:
            test_name = str(row[params.test_name_column]).lower().strip()
            if test_name in self.COMMON_LOINC_MAP:
                return self.COMMON_LOINC_MAP[test_name], 'name_mapping'
        
        # Strategy 3: Vendor-specific extraction
        if params.vendor_column and params.vendor_id_column:
            vendor = str(row.get(params.vendor_column, '')).lower()
            vendor_id = str(row.get(params.vendor_id_column, ''))
            
            if vendor == 'labcorp' and vendor_id:
                # LabCorp specific logic
                loinc = await self._extract_labcorp_loinc(vendor_id)
                if loinc:
                    return loinc, 'vendor_labcorp'
        
        # Strategy 4: Pattern matching in test name
        if params.test_name_column in row:
            test_name = str(row[params.test_name_column])
            loinc_pattern = r'\b(\d{4,5}-\d)\b'
            match = re.search(loinc_pattern, test_name)
            if match:
                return match.group(1), 'pattern_match'
        
        return None, None
    
    async def _extract_labcorp_loinc(self, labcorp_id: str) -> Optional[str]:
        """Extract LOINC from LabCorp test ID."""
        # Simplified mapping - in production would use full lookup table
        LABCORP_TO_LOINC = {
            '001818': '2345-7',  # Glucose
            '001065': '2093-3',  # Cholesterol
            '001869': '2085-9',  # HDL
            '001867': '2089-1',  # LDL
            '001735': '2571-8',  # Triglycerides
        }
        return LABCORP_TO_LOINC.get(labcorp_id)
    
    def _validate_loinc_format(self, loinc: Any) -> bool:
        """Validate LOINC code format."""
        if pd.isna(loinc) or not loinc:
            return False
        
        # LOINC format: 1-5 digits, hyphen, 1 digit
        pattern = r'^\d{1,5}-\d$'
        return bool(re.match(pattern, str(loinc)))
    
    async def _add_loinc_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add LOINC metadata like test category and units."""
        # Simplified metadata - in production would query LOINC database
        LOINC_METADATA = {
            '2345-7': {'category': 'Chemistry', 'common_unit': 'mg/dL'},
            '2093-3': {'category': 'Lipids', 'common_unit': 'mg/dL'},
            '2085-9': {'category': 'Lipids', 'common_unit': 'mg/dL'},
            '2089-1': {'category': 'Lipids', 'common_unit': 'mg/dL'},
            '2571-8': {'category': 'Lipids', 'common_unit': 'mg/dL'},
            '4548-4': {'category': 'Chemistry', 'common_unit': '%'},
            '2160-0': {'category': 'Renal', 'common_unit': 'mg/dL'},
        }
        
        df['loinc_category'] = df['extracted_loinc'].map(
            lambda x: LOINC_METADATA.get(x, {}).get('category')
        )
        df['loinc_unit'] = df['extracted_loinc'].map(
            lambda x: LOINC_METADATA.get(x, {}).get('common_unit')
        )
        
        return df
    
    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        """Convert various input types to DataFrame."""
        if isinstance(data, pd.DataFrame):
            return data.copy()
        elif isinstance(data, dict) and 'data' in data:
            return pd.DataFrame(data['data'])
        elif isinstance(data, list):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Cannot convert {type(data)} to DataFrame")
```

### Part 2: CHEMISTRY_FUZZY_TEST_MATCH

Create `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/chemistry/matching/fuzzy_test_match.py`:

```python
"""
Fuzzy matching for clinical chemistry test names.

This is the PRIMARY matching method for chemistry tests, not a fallback.
Uses multiple algorithms to match test names across different naming conventions.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz, process
import re
import logging
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.models import ActionResult

logger = logging.getLogger(__name__)

class ChemistryFuzzyMatchParams(BaseModel):
    """Parameters for fuzzy test matching."""
    input_key: str = Field(..., description="Input chemistry data key")
    output_key: str = Field(..., description="Output matched data key")
    test_name_column: str = Field("test_name", description="Column with test names")
    reference_key: Optional[str] = Field(None, description="Reference dataset key for matching")
    match_threshold: int = Field(80, description="Minimum similarity score (0-100)")
    use_abbreviations: bool = Field(True, description="Expand/match abbreviations")
    use_synonyms: bool = Field(True, description="Use synonym groups")
    max_matches: int = Field(3, description="Maximum matches per test")

@register_action("CHEMISTRY_FUZZY_TEST_MATCH")
class ChemistryFuzzyTestMatchAction(TypedStrategyAction[ChemistryFuzzyMatchParams, ActionResult]):
    """
    Primary fuzzy matching for chemistry test names.
    
    Uses 6 matching algorithms:
    1. Exact match (case-insensitive)
    2. Abbreviation expansion
    3. Synonym grouping
    4. Token set ratio (order-independent)
    5. Partial ratio (substring matching)
    6. Weighted ratio (combined scoring)
    """
    
    # Common abbreviations in chemistry tests
    ABBREVIATIONS = {
        'glu': 'glucose',
        'gluc': 'glucose',
        'chol': 'cholesterol',
        'trig': 'triglycerides',
        'hgb': 'hemoglobin',
        'hb': 'hemoglobin',
        'a1c': 'hemoglobin a1c',
        'hba1c': 'hemoglobin a1c',
        'creat': 'creatinine',
        'cr': 'creatinine',
        'egfr': 'estimated glomerular filtration rate',
        'gfr': 'glomerular filtration rate',
        'alt': 'alanine aminotransferase',
        'ast': 'aspartate aminotransferase',
        'tsh': 'thyroid stimulating hormone',
        'ft3': 'free t3',
        'ft4': 'free t4',
        'vit d': 'vitamin d',
        'vit': 'vitamin',
        'ldl-c': 'ldl cholesterol',
        'hdl-c': 'hdl cholesterol',
        'tc': 'total cholesterol',
        'bg': 'blood glucose',
        'fbg': 'fasting blood glucose',
        'rbs': 'random blood sugar',
        'ppg': 'postprandial glucose',
        'bun': 'blood urea nitrogen',
        'ua': 'uric acid',
        'alk phos': 'alkaline phosphatase',
        'alp': 'alkaline phosphatase',
        'ggt': 'gamma-glutamyl transferase',
        'ldh': 'lactate dehydrogenase',
        'ck': 'creatine kinase',
        'cpk': 'creatine phosphokinase',
        'psa': 'prostate specific antigen',
        'cea': 'carcinoembryonic antigen',
        'afp': 'alpha fetoprotein',
        'hcg': 'human chorionic gonadotropin',
        'bhcg': 'beta human chorionic gonadotropin',
        'pth': 'parathyroid hormone',
        'acth': 'adrenocorticotropic hormone',
        'igf': 'insulin-like growth factor',
        'gh': 'growth hormone',
        'fsh': 'follicle stimulating hormone',
        'lh': 'luteinizing hormone',
        'prl': 'prolactin',
        'e2': 'estradiol',
        'prog': 'progesterone',
        'test': 'testosterone',
        'dhea': 'dehydroepiandrosterone',
        'cort': 'cortisol',
        'tg': 'thyroglobulin',
        'tpo': 'thyroid peroxidase',
        'trab': 'tsh receptor antibody',
        'ana': 'antinuclear antibody',
        'rf': 'rheumatoid factor',
        'crp': 'c-reactive protein',
        'hscrp': 'high sensitivity c-reactive protein',
        'esr': 'erythrocyte sedimentation rate',
        'sed rate': 'erythrocyte sedimentation rate',
        'pt': 'prothrombin time',
        'ptt': 'partial thromboplastin time',
        'aptt': 'activated partial thromboplastin time',
        'inr': 'international normalized ratio',
        'wbc': 'white blood cell',
        'rbc': 'red blood cell',
        'hct': 'hematocrit',
        'mcv': 'mean corpuscular volume',
        'mch': 'mean corpuscular hemoglobin',
        'mchc': 'mean corpuscular hemoglobin concentration',
        'plt': 'platelet',
        'neut': 'neutrophil',
        'lymph': 'lymphocyte',
        'mono': 'monocyte',
        'eos': 'eosinophil',
        'baso': 'basophil',
        'retic': 'reticulocyte',
        'b12': 'vitamin b12',
        'folate': 'folic acid',
        'fe': 'iron',
        'tibc': 'total iron binding capacity',
        'ferr': 'ferritin',
        'tsat': 'transferrin saturation',
        'mg': 'magnesium',
        'phos': 'phosphorus',
        'ca': 'calcium',
        'na': 'sodium',
        'k': 'potassium',
        'cl': 'chloride',
        'co2': 'carbon dioxide',
        'bicarb': 'bicarbonate',
        'ag': 'anion gap',
        'osm': 'osmolality',
        'lact': 'lactate',
        'amm': 'ammonia',
        'bili': 'bilirubin',
        't bili': 'total bilirubin',
        'd bili': 'direct bilirubin',
        'i bili': 'indirect bilirubin',
        'alb': 'albumin',
        'glob': 'globulin',
        'tp': 'total protein',
        'a/g': 'albumin/globulin ratio',
        'ldl/hdl': 'ldl/hdl ratio'
    }
    
    # Synonym groups for tests with multiple names
    SYNONYM_GROUPS = [
        {'glucose', 'blood glucose', 'blood sugar', 'plasma glucose', 'serum glucose'},
        {'hemoglobin a1c', 'hba1c', 'glycated hemoglobin', 'glycohemoglobin', 'a1c'},
        {'cholesterol', 'total cholesterol', 'cholesterol total', 'serum cholesterol'},
        {'triglycerides', 'trigs', 'triglyceride', 'serum triglycerides'},
        {'creatinine', 'serum creatinine', 'creat', 'blood creatinine'},
        {'alanine aminotransferase', 'alt', 'sgpt', 'alanine transaminase'},
        {'aspartate aminotransferase', 'ast', 'sgot', 'aspartate transaminase'},
        {'thyroid stimulating hormone', 'tsh', 'thyrotropin'},
        {'vitamin d', '25-hydroxyvitamin d', '25-oh vitamin d', '25(oh)d', 'calcidiol'},
        {'blood urea nitrogen', 'bun', 'urea nitrogen', 'urea'},
        {'alkaline phosphatase', 'alk phos', 'alp', 'alkaline phosphatase'},
        {'gamma-glutamyl transferase', 'ggt', 'gamma gt', 'ggtp'},
        {'c-reactive protein', 'crp', 'c reactive protein'},
        {'high sensitivity c-reactive protein', 'hs-crp', 'hscrp', 'cardio crp'},
        {'erythrocyte sedimentation rate', 'esr', 'sed rate', 'sedimentation rate'},
        {'international normalized ratio', 'inr', 'pt/inr'},
        {'white blood cell', 'wbc', 'white cell count', 'leukocyte count'},
        {'red blood cell', 'rbc', 'red cell count', 'erythrocyte count'},
        {'mean corpuscular volume', 'mcv', 'mean cell volume'},
        {'mean corpuscular hemoglobin', 'mch', 'mean cell hemoglobin'},
        {'platelet', 'plt', 'platelet count', 'thrombocyte count'}
    ]
    
    def get_params_model(self) -> type[ChemistryFuzzyMatchParams]:
        return ChemistryFuzzyMatchParams
    
    async def execute_typed(
        self,
        params: ChemistryFuzzyMatchParams,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Execute fuzzy matching on chemistry test names."""
        try:
            # Implementation continues...
            # This is a skeleton - full implementation would include all matching logic
            
            return ActionResult(
                success=True,
                message="Fuzzy matching completed",
                data={'matches_found': 0}
            )
            
        except Exception as e:
            logger.error(f"Fuzzy matching failed: {e}")
            return ActionResult(success=False, error=str(e))
```

### Unit Tests

Create `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/entities/chemistry/test_chemistry_actions.py`:

```python
import pytest
import pandas as pd
from biomapper.core.strategy_actions.entities.chemistry.identification.extract_loinc import (
    ChemistryExtractLOINCAction,
    ChemistryExtractLOINCParams
)
from biomapper.core.strategy_actions.entities.chemistry.matching.fuzzy_test_match import (
    ChemistryFuzzyTestMatchAction,
    ChemistryFuzzyMatchParams
)

class TestChemistryActions:
    
    @pytest.fixture
    def chemistry_context(self):
        """Create test context with chemistry data."""
        return {
            'chemistry_data': {
                'data': [
                    {'test_name': 'Glucose', 'value': 95, 'unit': 'mg/dL'},
                    {'test_name': 'HbA1c', 'value': 5.6, 'unit': '%'},
                    {'test_name': 'Cholesterol Total', 'value': 180, 'unit': 'mg/dL'},
                    {'test_name': 'HDL-C', 'value': 55, 'unit': 'mg/dL'},
                    {'test_name': 'LDL Cholesterol', 'value': 105, 'unit': 'mg/dL'},
                    {'test_name': 'Triglycerides', 'value': 100, 'unit': 'mg/dL'},
                    {'test_name': 'Creatinine', 'value': 0.9, 'unit': 'mg/dL', 'loinc': '2160-0'},
                    {'test_name': 'ALT (SGPT)', 'value': 25, 'unit': 'U/L'},
                ]
            }
        }
    
    @pytest.mark.asyncio
    async def test_loinc_extraction_from_direct_column(self, chemistry_context):
        """Test extracting LOINC from direct column."""
        action = ChemistryExtractLOINCAction()
        params = ChemistryExtractLOINCParams(
            input_key='chemistry_data',
            output_key='loinc_extracted',
            loinc_column='loinc',
            test_name_column='test_name'
        )
        
        result = await action.execute_typed(params, chemistry_context)
        
        assert result.success
        assert 'loinc_extracted' in chemistry_context
        
        # Check that creatinine LOINC was extracted
        output_data = chemistry_context['loinc_extracted']['data']
        creat_row = [r for r in output_data if r['test_name'] == 'Creatinine'][0]
        assert creat_row['extracted_loinc'] == '2160-0'
        assert creat_row['extraction_method'] == 'direct_column'
    
    @pytest.mark.asyncio
    async def test_loinc_extraction_from_test_names(self, chemistry_context):
        """Test extracting LOINC from test name mapping."""
        action = ChemistryExtractLOINCAction()
        params = ChemistryExtractLOINCParams(
            input_key='chemistry_data',
            output_key='loinc_extracted',
            test_name_column='test_name',
            validate_format=True
        )
        
        result = await action.execute_typed(params, chemistry_context)
        
        assert result.success
        
        output_data = chemistry_context['loinc_extracted']['data']
        
        # Check glucose mapping
        glucose_row = [r for r in output_data if 'Glucose' in r['test_name']][0]
        assert glucose_row['extracted_loinc'] == '2345-7'
        assert glucose_row['loinc_valid'] == True
        
        # Check statistics
        stats = chemistry_context['loinc_extracted']['statistics']
        assert stats['loinc_extracted'] > 0
        assert stats['extraction_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_fuzzy_matching_with_abbreviations(self):
        """Test fuzzy matching expands abbreviations."""
        context = {
            'test_data': {
                'data': [
                    {'test_name': 'Glu'},
                    {'test_name': 'Chol'},
                    {'test_name': 'Trig'},
                    {'test_name': 'HbA1c'},
                    {'test_name': 'Creat'}
                ]
            }
        }
        
        action = ChemistryFuzzyTestMatchAction()
        params = ChemistryFuzzyMatchParams(
            input_key='test_data',
            output_key='matched_tests',
            test_name_column='test_name',
            use_abbreviations=True
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        # Further assertions would check abbreviation expansion
    
    @pytest.mark.asyncio
    async def test_fuzzy_matching_with_synonyms(self):
        """Test fuzzy matching uses synonym groups."""
        context = {
            'test_data': {
                'data': [
                    {'test_name': 'Blood Sugar'},
                    {'test_name': 'Glycated Hemoglobin'},
                    {'test_name': 'Total Cholesterol'},
                    {'test_name': 'SGPT'},
                    {'test_name': 'SGOT'}
                ]
            }
        }
        
        action = ChemistryFuzzyTestMatchAction()
        params = ChemistryFuzzyMatchParams(
            input_key='test_data',
            output_key='matched_tests',
            test_name_column='test_name',
            use_synonyms=True
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success
        # Verify synonym matching worked
```

## Success Criteria

1. ✅ All 4 chemistry actions are implemented and registered
2. ✅ Unit tests pass for each action
3. ✅ At least one chemistry strategy executes successfully
4. ✅ Fuzzy matching achieves >80% accuracy on test data
5. ✅ LOINC extraction handles multiple vendor formats

## Deliverables

1. Four action implementation files
2. Comprehensive unit tests
3. Integration test showing chemistry strategy working
4. Performance metrics for fuzzy matching
5. Documentation of abbreviations and synonyms used

## Time Estimate

- CHEMISTRY_EXTRACT_LOINC: 45 minutes
- CHEMISTRY_FUZZY_TEST_MATCH: 45 minutes  
- CHEMISTRY_VENDOR_HARMONIZATION: 30 minutes
- CHEMISTRY_TO_PHENOTYPE_BRIDGE: 30 minutes
- Testing and documentation: 30 minutes
- **Total: 3 hours**

## Notes

- Focus on the most common clinical chemistry tests first
- Make fuzzy matching the PRIMARY method, not fallback
- Include comprehensive abbreviation and synonym lists
- Consider performance for large datasets (>10k records)
- Ensure vendor-specific logic is extensible