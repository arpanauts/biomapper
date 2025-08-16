"""
Chemistry to Phenotype Bridge Action

Maps clinical chemistry/lab tests to phenotypic features via LOINC codes
and semantic associations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ActionResult(BaseModel):
    """Result from action execution."""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ChemistryToPhenotypeBridgeParams(BaseModel):
    """Parameters for chemistry to phenotype bridging."""

    source_key: str = Field(description="Key containing source chemistry/lab data")
    target_key: str = Field(description="Key containing target phenotype data")
    loinc_column: str = Field(
        default="Labcorp LOINC ID",
        description="Column containing LOINC codes in source",
    )
    phenotype_id_column: str = Field(
        default="id", description="Column containing phenotype IDs in target"
    )
    phenotype_xrefs_column: str = Field(
        default="xrefs", description="Column containing phenotype cross-references"
    )
    association_threshold: float = Field(
        default=0.7, description="Minimum confidence threshold for associations"
    )
    use_semantic_matching: bool = Field(
        default=True, description="Whether to use semantic matching for unmapped items"
    )
    output_key: str = Field(description="Key to store mapping results")


@register_action("CHEMISTRY_TO_PHENOTYPE_BRIDGE")
class ChemistryToPhenotypeBridgeAction(
    TypedStrategyAction[ChemistryToPhenotypeBridgeParams, ActionResult]
):
    """Maps chemistry/lab tests to phenotypic features."""

    def get_params_model(self) -> type[ChemistryToPhenotypeBridgeParams]:
        return ChemistryToPhenotypeBridgeParams
    
    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    async def execute_typed(
        self, params: ChemistryToPhenotypeBridgeParams, context: Dict[str, Any]
    ) -> ActionResult:
        """Execute chemistry to phenotype mapping."""
        try:
            # Get source and target datasets
            source_df = context["datasets"][params.source_key]
            target_df = context["datasets"][params.target_key]

            logger.info(
                f"Mapping {len(source_df)} chemistry tests to {len(target_df)} phenotypes"
            )

            # Initialize mappings
            mappings = []
            unmapped = []

            # Load known LOINC-to-phenotype associations
            loinc_hp_map = self._load_loinc_hp_associations()
            
            # PERFORMANCE OPTIMIZATION: Build phenotype lookup index for O(1) HP code matching
            if not hasattr(self, '_phenotype_hp_index'):
                self._phenotype_hp_index = {}
                for idx, phenotype_row in target_df.iterrows():
                    phenotype_id = str(phenotype_row.get(params.phenotype_id_column, ""))
                    phenotype_xrefs = str(phenotype_row.get(params.phenotype_xrefs_column, ""))
                    
                    # Extract all HP codes from ID and xrefs
                    all_text = phenotype_id + " " + phenotype_xrefs
                    # Simple pattern matching for HP codes (HP:XXXXXXX)
                    import re
                    hp_codes = re.findall(r'HP:\d{7}', all_text)
                    
                    for hp_code in hp_codes:
                        if hp_code not in self._phenotype_hp_index:
                            self._phenotype_hp_index[hp_code] = []
                        self._phenotype_hp_index[hp_code].append(phenotype_row.to_dict())

            # Process each chemistry test
            for idx, row in source_df.iterrows():
                chemistry_name = row.get("Name", "")
                display_name = row.get("Display Name", "")
                loinc_code = row.get(params.loinc_column, "")

                if pd.isna(loinc_code) or loinc_code == "":
                    # Try semantic matching if no LOINC code
                    if params.use_semantic_matching:
                        phenotype_match = self._semantic_match_to_phenotype(
                            chemistry_name, display_name, target_df
                        )
                        if phenotype_match:
                            mappings.append(
                                {
                                    "chemistry_id": chemistry_name,
                                    "chemistry_display": display_name,
                                    "phenotype_id": phenotype_match["id"],
                                    "phenotype_name": phenotype_match["name"],
                                    "match_type": "semantic",
                                    "confidence": phenotype_match.get(
                                        "confidence", 0.5
                                    ),
                                }
                            )
                        else:
                            unmapped.append(chemistry_name)
                    else:
                        unmapped.append(chemistry_name)
                    continue

                # Look up LOINC associations
                associated_phenotypes = loinc_hp_map.get(loinc_code, [])

                if associated_phenotypes:
                    # PERFORMANCE OPTIMIZATION: Use O(1) index lookup instead of O(m) DataFrame filtering
                    for hp_code in associated_phenotypes:
                        # Get matching phenotypes using efficient index - O(1) lookup
                        matched_phenotype_rows = self._phenotype_hp_index.get(hp_code, [])

                        for phenotype_row in matched_phenotype_rows:
                            mappings.append(
                                {
                                    "chemistry_id": chemistry_name,
                                    "chemistry_display": display_name,
                                    "loinc_code": loinc_code,
                                    "phenotype_id": phenotype_row.get(
                                        params.phenotype_id_column, ""
                                    ),
                                    "phenotype_name": phenotype_row.get("name", ""),
                                    "match_type": "loinc_association",
                                    "confidence": 0.9,
                                }
                            )
                else:
                    # Try rule-based mapping
                    phenotype_match = self._rule_based_mapping(
                        chemistry_name, display_name, loinc_code, target_df
                    )
                    if phenotype_match:
                        mappings.append(phenotype_match)
                    else:
                        unmapped.append(chemistry_name)

            # Create results dataframe
            results_df = pd.DataFrame(mappings)

            # Store in context
            context["datasets"][params.output_key] = results_df

            # Update statistics
            stats = {
                "total_chemistry_tests": len(source_df),
                "total_phenotypes": len(target_df),
                "mapped_tests": len(results_df["chemistry_id"].unique())
                if len(results_df) > 0
                else 0,
                "total_mappings": len(mappings),
                "unmapped_tests": len(unmapped),
                "mapping_types": results_df["match_type"].value_counts().to_dict()
                if len(results_df) > 0
                else {},
            }

            context.setdefault("statistics", {}).update(stats)

            logger.info(f"Mapped {stats['mapped_tests']} chemistry tests to phenotypes")
            logger.info(f"Total mappings: {stats['total_mappings']}")
            logger.info(f"Unmapped: {stats['unmapped_tests']}")

            return ActionResult(
                success=True,
                message=f"Successfully mapped {stats['mapped_tests']} chemistry tests to phenotypes",
                data=stats,
            )

        except Exception as e:
            logger.error(f"Chemistry to phenotype mapping failed: {str(e)}")
            return ActionResult(
                success=False,
                message=f"Chemistry to phenotype mapping failed: {str(e)}",
                error=str(e),
            )

    def _load_loinc_hp_associations(self) -> Dict[str, List[str]]:
        """Load known LOINC to HP (Human Phenotype) associations."""
        # This would typically load from a reference database
        # For now, return common associations
        return {
            "1742-6": [
                "HP:0002910",
                "HP:0001410",
            ],  # ALT -> Elevated hepatic transaminase, Decreased liver function
            "1751-7": ["HP:0003073"],  # Albumin -> Hypoalbuminemia
            "6768-6": [
                "HP:0002910"
            ],  # Alkaline Phosphatase -> Elevated hepatic transaminase
            "2345-7": [
                "HP:0003074",
                "HP:0003076",
            ],  # Glucose -> Hyperglycemia, Glycosuria
            "2160-0": [
                "HP:0001900",
                "HP:0003565",
            ],  # Creatinine -> Increased serum creatinine
            "3094-0": [
                "HP:0002153",
                "HP:0003259",
            ],  # BUN -> Hyperkalemia, Elevated serum creatinine
            "2823-3": [
                "HP:0003362",
                "HP:0002153",
            ],  # Potassium -> Hypokalemia, Hyperkalemia
            "2951-2": [
                "HP:0002900",
                "HP:0002901",
            ],  # Sodium -> Hyponatremia, Hypernatremia
            "718-7": [
                "HP:0001871",
                "HP:0001873",
            ],  # Hemoglobin -> Abnormality of blood hemoglobin
            "1759-0": [
                "HP:0003073",
                "HP:0012211",
            ],  # A/G Ratio -> Hypoalbuminemia, Abnormal albumin/globulin ratio
        }

    def _semantic_match_to_phenotype(
        self, chemistry_name: str, display_name: str, target_df: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """Attempt semantic matching between chemistry test and phenotypes with O(m) complexity."""
        # Simple keyword-based matching for demonstration
        test_keywords = set(
            chemistry_name.lower().split() + display_name.lower().split()
        )
        
        # PERFORMANCE OPTIMIZATION: Build phenotype keyword index once and cache it
        if not hasattr(self, '_phenotype_keyword_index'):
            self._phenotype_keyword_index = {}
            for idx, phenotype_row in target_df.iterrows():
                phenotype_name = str(phenotype_row.get("name", "")).lower()
                phenotype_desc = str(phenotype_row.get("description", "")).lower()
                
                # Create keyword set for this phenotype
                phenotype_keywords = set(
                    phenotype_name.split() + phenotype_desc.split()[:20]
                )
                
                self._phenotype_keyword_index[idx] = {
                    'keywords': phenotype_keywords,
                    'id': phenotype_row.get("id"),
                    'name': phenotype_row.get("name")
                }

        best_match = None
        best_score = 0

        # O(m) iteration through cached phenotype data instead of O(m) DataFrame iteration
        for phenotype_data in self._phenotype_keyword_index.values():
            phenotype_keywords = phenotype_data['keywords']
            common_keywords = test_keywords.intersection(phenotype_keywords)

            if len(common_keywords) > 0:
                score = len(common_keywords) / max(len(test_keywords), 1)
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = {
                        "id": phenotype_data['id'],
                        "name": phenotype_data['name'],
                        "confidence": score,
                    }

        return best_match

    def _rule_based_mapping(
        self,
        chemistry_name: str,
        display_name: str,
        loinc_code: str,
        target_df: pd.DataFrame,
    ) -> Optional[Dict[str, Any]]:
        """Apply rule-based mapping for specific chemistry tests."""
        # Map specific test patterns to phenotypes
        rules = {
            "glucose": [
                "HP:0003074",
                "HP:0011015",
            ],  # Hyperglycemia, Abnormality of blood glucose
            "cholesterol": [
                "HP:0003124",
                "HP:0003107",
            ],  # Hypercholesterolemia, Abnormal cholesterol
            "triglyceride": ["HP:0002155"],  # Hypertriglyceridemia
            "hemoglobin": ["HP:0001871", "HP:0011902"],  # Abnormality of hemoglobin
            "creatinine": [
                "HP:0003259",
                "HP:0000083",
            ],  # Elevated creatinine, Renal insufficiency
            "bilirubin": ["HP:0002904", "HP:0000952"],  # Hyperbilirubinemia, Jaundice
            "calcium": ["HP:0002901", "HP:0002900"],  # Hypercalcemia, Hypocalcemia
            "iron": [
                "HP:0011031",
                "HP:0011032",
            ],  # Abnormality of iron, Iron deficiency
        }

        chemistry_lower = chemistry_name.lower()
        display_lower = display_name.lower()

        for keyword, hp_codes in rules.items():
            if keyword in chemistry_lower or keyword in display_lower:
                # Find matching phenotypes
                for hp_code in hp_codes:
                    matched = target_df[
                        target_df["id"].str.contains(hp_code, na=False)
                        | target_df["xrefs"].str.contains(hp_code, na=False)
                    ]

                    if not matched.empty:
                        phenotype_row = matched.iloc[0]
                        return {
                            "chemistry_id": chemistry_name,
                            "chemistry_display": display_name,
                            "loinc_code": loinc_code,
                            "phenotype_id": phenotype_row["id"],
                            "phenotype_name": phenotype_row.get("name", ""),
                            "match_type": "rule_based",
                            "confidence": 0.7,
                        }

        return None
