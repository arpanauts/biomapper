"""
METABOLITE_NIGHTINGALE_BRIDGE action for Stage 1 of progressive metabolite mapping.
Processes Nightingale CSV with 45 ID entries and 205 name-only entries.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from pydantic import BaseModel, Field

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.models.execution_context import StrategyExecutionContext

logger = logging.getLogger(__name__)


class NightingaleBridgeParams(BaseModel):
    """Parameters for Nightingale metabolite bridge action."""
    
    csv_file_path: str = Field(
        default="/home/ubuntu/biomapper/data/nightingale/Nightingale-Health-CoreMetabolomics-Blood-CVs-PubChemIDs.csv",
        description="Path to Nightingale CSV file"
    )
    output_key: str = Field(
        default="nightingale_matched",
        description="Key for storing matched metabolites in context"
    )
    unmapped_key: str = Field(
        default="nightingale_unmapped", 
        description="Key for storing unmapped metabolites for Stage 2"
    )
    track_statistics: bool = Field(
        default=True,
        description="Track progressive statistics"
    )
    use_fuzzy_matching: bool = Field(
        default=False,
        description="Enable fuzzy name matching (for Stage 2 integration)"
    )
    

class NightingaleBridgeResult(BaseModel):
    """Result of Nightingale bridge processing."""
    
    success: bool
    total_processed: int
    matched_with_ids: int
    name_only_for_stage2: int
    coverage: float
    confidence_distribution: Dict[float, int]
    message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


@register_action("METABOLITE_NIGHTINGALE_BRIDGE")
class MetaboliteNightingaleBridge(TypedStrategyAction[NightingaleBridgeParams, NightingaleBridgeResult]):
    """
    Stage 1 of progressive metabolite mapping using Nightingale resource.
    
    Processes the Nightingale Health CoreMetabolomics CSV to extract:
    - 45 metabolites with PubChem/CHEBI IDs (high confidence)
    - 205 metabolites with names only (for Stage 2 semantic matching)
    
    Confidence scoring:
    - PubChem ID: 0.98
    - CHEBI ID: 0.95
    - Exact name match: 0.90
    - Fuzzy name match: 0.80
    """
    
    # Confidence constants
    PUBCHEM_CONFIDENCE = 0.98
    CHEBI_CONFIDENCE = 0.95
    NAME_EXACT_CONFIDENCE = 0.90
    NAME_FUZZY_CONFIDENCE = 0.80
    
    def get_params_model(self) -> type[NightingaleBridgeParams]:
        """Return the params model class."""
        return NightingaleBridgeParams
    
    def get_result_model(self) -> type[NightingaleBridgeResult]:
        """Return the result model class."""
        return NightingaleBridgeResult
    
    def parse_chebi_id(self, chebi_str: Optional[str]) -> Optional[str]:
        """Parse CHEBI ID from various formats."""
        if not chebi_str or pd.isna(chebi_str):
            return None
            
        chebi_str = str(chebi_str).strip()
        
        # Handle various CHEBI formats
        patterns = [
            r'CHEBI:\s*(\d+)',  # "CHEBI: 12345" or "CHEBI:12345"
            r'chebi:\s*(\d+)',  # lowercase variant
            r'^(\d+)$'          # Just the number
        ]
        
        for pattern in patterns:
            match = re.match(pattern, chebi_str)
            if match:
                return match.group(1)
        
        return None
    
    def standardize_name(self, name: str) -> str:
        """Standardize metabolite names for better matching."""
        if not name:
            return name
            
        # Common replacements
        replacements = {
            '_C': ' cholesterol',
            '_TG': ' triglycerides',
            '_PL': ' phospholipids',
            '_CE': ' cholesteryl esters',
            '_FC': ' free cholesterol',
            '_L': ' lipids',
            '_P': ' particles',
            '_pct': ' percentage',
            'bOHbutyrate': 'beta-hydroxybutyrate',
            'Total-': 'Total ',
            'non-': 'non-',
            '_': ' '
        }
        
        standardized = name
        for old, new in replacements.items():
            standardized = standardized.replace(old, new)
        
        # Clean up multiple spaces
        standardized = ' '.join(standardized.split())
        
        return standardized
    
    def extract_pubchem_ids(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract metabolites with PubChem IDs."""
        results = []
        
        for _, row in df.iterrows():
            pubchem_id = row.get('PubChem_ID', '')
            if pubchem_id and str(pubchem_id).strip() and str(pubchem_id).strip() != '':
                results.append({
                    'name': row.get('Biomarker_name', ''),
                    'csv_name': row.get('CSV_column_name', ''),
                    'pubchem_id': str(pubchem_id).strip(),
                    'confidence': self.PUBCHEM_CONFIDENCE,
                    'source': 'nightingale_pubchem'
                })
        
        return results
    
    def extract_chebi_ids(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract metabolites with CHEBI IDs."""
        results = []
        
        for _, row in df.iterrows():
            cas_chebi_field = row.get('CAS_CHEBI_or_Uniprot_ID', '')
            if cas_chebi_field and 'CHEBI' in str(cas_chebi_field).upper():
                chebi_id = self.parse_chebi_id(cas_chebi_field)
                if chebi_id:
                    results.append({
                        'name': row.get('Biomarker_name', ''),
                        'csv_name': row.get('CSV_column_name', ''),
                        'chebi_id': chebi_id,
                        'confidence': self.CHEBI_CONFIDENCE,
                        'source': 'nightingale_chebi'
                    })
        
        return results
    
    def extract_all_ids(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract all metabolites with any form of ID, combining when possible."""
        metabolite_map = {}
        
        # First pass: PubChem IDs (highest priority)
        for _, row in df.iterrows():
            name = row.get('Biomarker_name', '')
            csv_name = row.get('CSV_column_name', '')
            pubchem_id = row.get('PubChem_ID', '')
            
            # Check for valid PubChem ID (not nan, not empty string)
            if pubchem_id and not pd.isna(pubchem_id) and str(pubchem_id).strip() and str(pubchem_id).strip() != 'nan':
                key = csv_name or name
                metabolite_map[key] = {
                    'name': name,
                    'csv_name': csv_name,
                    'pubchem_id': str(int(float(pubchem_id))),  # Convert to int to remove .0
                    'confidence': self.PUBCHEM_CONFIDENCE,
                    'source': 'nightingale'
                }
        
        # Second pass: Add CHEBI IDs
        for _, row in df.iterrows():
            name = row.get('Biomarker_name', '')
            csv_name = row.get('CSV_column_name', '')
            cas_chebi_field = row.get('CAS_CHEBI_or_Uniprot_ID', '')
            
            if cas_chebi_field and 'CHEBI' in str(cas_chebi_field).upper():
                chebi_id = self.parse_chebi_id(cas_chebi_field)
                if chebi_id:
                    key = csv_name or name
                    if key in metabolite_map:
                        # Add CHEBI to existing entry
                        metabolite_map[key]['chebi_id'] = chebi_id
                    else:
                        # Create new entry with CHEBI only
                        metabolite_map[key] = {
                            'name': name,
                            'csv_name': csv_name,
                            'chebi_id': chebi_id,
                            'confidence': self.CHEBI_CONFIDENCE,
                            'source': 'nightingale'
                        }
        
        return list(metabolite_map.values())
    
    def process_nightingale_data(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Process Nightingale data and separate matched from unmapped."""
        matched = []
        unmapped = []
        
        # Get all metabolites with IDs
        matched = self.extract_all_ids(df)
        matched_names = {m['csv_name'] for m in matched}
        
        # Find unmapped entries (no PubChem or CHEBI)
        for _, row in df.iterrows():
            csv_name = row.get('CSV_column_name', '')
            name = row.get('Biomarker_name', '')
            
            if csv_name not in matched_names:
                # Check if it's a protein (Uniprot) - these go to unmapped
                cas_chebi_field = row.get('CAS_CHEBI_or_Uniprot_ID', '')
                if cas_chebi_field and 'Uniprot' in str(cas_chebi_field):
                    unmapped.append({
                        'name': name,
                        'csv_name': csv_name,
                        'uniprot_id': cas_chebi_field.replace('Uniprot:', '').strip(),
                        'reason': 'protein_not_metabolite'
                    })
                elif name:  # Name-only entry for Stage 2
                    unmapped.append({
                        'name': self.standardize_name(name),
                        'csv_name': csv_name,
                        'original_name': name,
                        'for_stage': 2,
                        'reason': 'no_external_id'
                    })
        
        return matched, unmapped
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: NightingaleBridgeParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: StrategyExecutionContext
    ) -> NightingaleBridgeResult:
        """Execute the Nightingale bridge action."""
        
        try:
            # Load Nightingale CSV
            csv_path = Path(params.csv_file_path)
            if not csv_path.exists():
                return NightingaleBridgeResult(
                    success=False,
                    total_processed=0,
                    matched_with_ids=0,
                    name_only_for_stage2=0,
                    coverage=0.0,
                    confidence_distribution={},
                    message=f"CSV file not found: {csv_path}"
                )
            
            df = pd.read_csv(csv_path)
            total_rows = len(df)
            
            # Process data
            matched, unmapped = self.process_nightingale_data(df)
            
            # Calculate statistics
            matched_count = len(matched)
            unmapped_count = len(unmapped)
            coverage = matched_count / total_rows if total_rows > 0 else 0.0
            
            # Confidence distribution
            confidence_dist = {}
            for m in matched:
                conf = m['confidence']
                confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
            
            # Store in context
            datasets = context.get_action_data("datasets", {})
            datasets[params.output_key] = matched
            datasets[params.unmapped_key] = unmapped
            context.set_action_data("datasets", datasets)
            
            # Track statistics if enabled
            if params.track_statistics:
                statistics = context.get_action_data("statistics", {})
                statistics["nightingale_bridge"] = {
                    "stage": 1,
                    "total_processed": total_rows,
                    "matched": matched_count,
                    "unmapped": unmapped_count,
                    "coverage": coverage,
                    "confidence_distribution": confidence_dist,
                    "name_only_for_stage2": len([u for u in unmapped if u.get('for_stage') == 2])
                }
                context.set_action_data("statistics", statistics)
            
            # Log summary
            logger.info(f"Nightingale Bridge Stage 1 Results:")
            logger.info(f"  Total metabolites: {total_rows}")
            logger.info(f"  Matched with IDs: {matched_count} ({coverage:.1%})")
            logger.info(f"  Name-only for Stage 2: {len([u for u in unmapped if u.get('for_stage') == 2])}")
            logger.info(f"  Confidence distribution: {confidence_dist}")
            
            return NightingaleBridgeResult(
                success=True,
                total_processed=total_rows,
                matched_with_ids=matched_count,
                name_only_for_stage2=len([u for u in unmapped if u.get('for_stage') == 2]),
                coverage=coverage,
                confidence_distribution=confidence_dist,
                message=f"Successfully processed {total_rows} Nightingale metabolites"
            )
            
        except Exception as e:
            logger.error(f"Error in Nightingale bridge: {str(e)}")
            return NightingaleBridgeResult(
                success=False,
                total_processed=0,
                matched_with_ids=0,
                name_only_for_stage2=0,
                coverage=0.0,
                confidence_distribution={},
                message=f"Error: {str(e)}"
            )