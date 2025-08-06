"""Calculate comprehensive three-way overlap statistics and generate visualizations."""

from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field
from pathlib import Path
import logging
import json
from collections import defaultdict
from datetime import datetime

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class CalculateThreeWayOverlapParams(BaseModel):
    """Parameters for three-way overlap calculation."""
    
    input_key: str = Field(..., description="Key for combined matches from COMBINE_METABOLITE_MATCHES")
    dataset_names: List[str] = Field(
        default=["Israeli10K", "UKBB", "Arivale"],
        min_items=3,
        max_items=3,
        description="Names of three datasets in order"
    )
    confidence_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for overlap inclusion"
    )
    output_dir: str = Field(..., description="Directory for output files")
    mapping_combo_id: str = Field(..., description="Identifier for this mapping combination")
    generate_visualizations: List[str] = Field(
        default_factory=list,
        description="List of visualizations to generate"
    )
    output_key: str = Field(..., description="Key for storing statistics")
    export_detailed_results: bool = Field(True, description="Export detailed CSV files")


class OverlapStatistics(BaseModel):
    """Statistics for an overlap between datasets."""
    
    count: int
    percentage_of_first: float
    percentage_of_second: float
    percentage_of_third: Optional[float] = None
    jaccard_index: float
    metabolite_ids: List[str]
    confidence_distribution: Dict[str, int]


@register_action("CALCULATE_THREE_WAY_OVERLAP")
class CalculateThreeWayOverlapAction(
    TypedStrategyAction[CalculateThreeWayOverlapParams, StandardActionResult]
):
    """Calculate comprehensive three-way overlap statistics and generate visualizations."""
    
    def get_params_model(self) -> type[CalculateThreeWayOverlapParams]:
        """Return the params model class."""
        return CalculateThreeWayOverlapParams
    
    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult
    
    def _extract_dataset_memberships(
        self,
        three_way_matches: List[Dict[str, Any]],
        two_way_matches: List[Dict[str, Any]],
        confidence_threshold: float
    ) -> Dict[str, Set[str]]:
        """Extract which metabolites belong to which datasets."""
        
        memberships = {
            "Israeli10K": set(),
            "UKBB": set(),
            "Arivale": set(),
            "Israeli10K_UKBB": set(),
            "Israeli10K_Arivale": set(),
            "UKBB_Arivale": set(),
            "Israeli10K_UKBB_Arivale": set()
        }
        
        # Process all matches (both three-way and two-way)
        all_matches = three_way_matches + two_way_matches
        
        for match in all_matches:
            if match.get("match_confidence", 0) < confidence_threshold:
                continue
                
            metabolite_id = match["metabolite_id"]
            datasets_present = []
            
            if match.get("israeli10k"):
                datasets_present.append("Israeli10K")
            if match.get("ukbb"):
                datasets_present.append("UKBB")
            if match.get("arivale"):
                datasets_present.append("Arivale")
            
            # Add to individual dataset sets
            for dataset in datasets_present:
                memberships[dataset].add(metabolite_id)
            
            # Add to appropriate overlap sets
            if len(datasets_present) == 2:
                # Pairwise overlap
                if "Israeli10K" in datasets_present and "UKBB" in datasets_present:
                    memberships["Israeli10K_UKBB"].add(metabolite_id)
                elif "Israeli10K" in datasets_present and "Arivale" in datasets_present:
                    memberships["Israeli10K_Arivale"].add(metabolite_id)
                elif "UKBB" in datasets_present and "Arivale" in datasets_present:
                    memberships["UKBB_Arivale"].add(metabolite_id)
            elif len(datasets_present) == 3:
                # Three-way overlap
                memberships["Israeli10K_UKBB_Arivale"].add(metabolite_id)
                # Also add to pairwise overlaps
                memberships["Israeli10K_UKBB"].add(metabolite_id)
                memberships["Israeli10K_Arivale"].add(metabolite_id)
                memberships["UKBB_Arivale"].add(metabolite_id)
        
        return memberships
    
    def _get_confidence_distribution(
        self,
        metabolite_ids: Set[str],
        all_matches: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get confidence distribution for a set of metabolites."""
        
        distribution = {
            "high": 0,      # >= 0.9
            "medium": 0,    # >= 0.7
            "low": 0        # < 0.7
        }
        
        # Build a map of metabolite_id to match for fast lookup
        match_map = {match["metabolite_id"]: match for match in all_matches}
        
        for metabolite_id in metabolite_ids:
            if metabolite_id in match_map:
                confidence = match_map[metabolite_id].get("match_confidence", 0)
                if confidence >= 0.9:
                    distribution["high"] += 1
                elif confidence >= 0.7:
                    distribution["medium"] += 1
                else:
                    distribution["low"] += 1
        
        return distribution
    
    def _calculate_overlap_statistics(
        self,
        memberships: Dict[str, Set[str]],
        dataset_names: List[str],
        all_matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate detailed overlap statistics."""
        
        stats = {}
        
        # Individual dataset stats
        for dataset in dataset_names:
            stats[dataset] = {
                "total_metabolites": len(memberships[dataset]),
                "unique_metabolites": len(
                    memberships[dataset] - 
                    (memberships["Israeli10K_UKBB_Arivale"] |
                     memberships[f"{dataset}_UKBB" if dataset == "Israeli10K" else f"Israeli10K_{dataset}"] |
                     memberships[f"{dataset}_Arivale" if dataset != "Arivale" else f"UKBB_Arivale"])
                    if dataset == "Israeli10K" else
                    memberships[dataset] - 
                    (memberships["Israeli10K_UKBB_Arivale"] |
                     memberships[f"Israeli10K_{dataset}" if dataset == "UKBB" else f"{dataset}_UKBB"] |
                     memberships[f"{dataset}_Arivale" if dataset != "Arivale" else f"Israeli10K_Arivale"])
                    if dataset == "UKBB" else
                    memberships[dataset] - 
                    (memberships["Israeli10K_UKBB_Arivale"] |
                     memberships["Israeli10K_Arivale"] |
                     memberships["UKBB_Arivale"])
                )
            }
        
        # Pairwise overlaps
        for i, ds1 in enumerate(dataset_names):
            for j, ds2 in enumerate(dataset_names[i+1:], i+1):
                pair_key = f"{ds1}_{ds2}"
                overlap = memberships[ds1] & memberships[ds2]
                
                stats[pair_key] = OverlapStatistics(
                    count=len(overlap),
                    percentage_of_first=100 * len(overlap) / len(memberships[ds1]) if memberships[ds1] else 0,
                    percentage_of_second=100 * len(overlap) / len(memberships[ds2]) if memberships[ds2] else 0,
                    jaccard_index=len(overlap) / len(memberships[ds1] | memberships[ds2]) if (memberships[ds1] | memberships[ds2]) else 0,
                    metabolite_ids=list(overlap)[:10],  # Sample for display
                    confidence_distribution=self._get_confidence_distribution(overlap, all_matches)
                )
        
        # Three-way overlap
        three_way = memberships["Israeli10K_UKBB_Arivale"]
        stats["three_way"] = OverlapStatistics(
            count=len(three_way),
            percentage_of_first=100 * len(three_way) / len(memberships["Israeli10K"]) if memberships["Israeli10K"] else 0,
            percentage_of_second=100 * len(three_way) / len(memberships["UKBB"]) if memberships["UKBB"] else 0,
            percentage_of_third=100 * len(three_way) / len(memberships["Arivale"]) if memberships["Arivale"] else 0,
            jaccard_index=len(three_way) / len(memberships["Israeli10K"] | memberships["UKBB"] | memberships["Arivale"]) if (memberships["Israeli10K"] | memberships["UKBB"] | memberships["Arivale"]) else 0,
            metabolite_ids=list(three_way)[:10],
            confidence_distribution=self._get_confidence_distribution(three_way, all_matches)
        )
        
        return stats
    
    def _generate_visualizations(
        self,
        memberships: Dict[str, Set[str]],
        stats: Dict[str, Any],
        output_dir: Path,
        visualizations: List[str]
    ) -> Dict[str, str]:
        """Generate requested visualizations."""
        
        viz_paths = {}
        
        if "venn_diagram_3way" in visualizations:
            viz_paths["venn_diagram"] = self._create_venn_diagram(memberships, output_dir)
        
        if "confidence_heatmap" in visualizations:
            viz_paths["confidence_heatmap"] = self._create_confidence_heatmap(stats, output_dir)
        
        if "provenance_sankey" in visualizations:
            viz_paths["provenance_sankey"] = self._create_provenance_sankey(stats, output_dir)
        
        if "method_breakdown_pie" in visualizations:
            viz_paths["method_breakdown"] = self._create_method_breakdown(stats, output_dir)
        
        if "overlap_progression_chart" in visualizations:
            viz_paths["overlap_progression"] = self._create_progression_chart(stats, output_dir)
        
        return viz_paths
    
    def _create_venn_diagram(self, memberships: Dict[str, Set[str]], output_dir: Path) -> str:
        """Create 3-way Venn diagram."""
        try:
            import matplotlib.pyplot as plt
            from matplotlib_venn import venn3, venn3_circles
        except ImportError:
            logger.warning("matplotlib_venn not installed, skipping Venn diagram")
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Calculate exclusive regions for Venn diagram
        # Using set operations to get each region
        i10k_only = memberships["Israeli10K"] - memberships["UKBB"] - memberships["Arivale"]
        ukbb_only = memberships["UKBB"] - memberships["Israeli10K"] - memberships["Arivale"]
        arivale_only = memberships["Arivale"] - memberships["Israeli10K"] - memberships["UKBB"]
        
        i10k_ukbb_only = (memberships["Israeli10K"] & memberships["UKBB"]) - memberships["Arivale"]
        i10k_arivale_only = (memberships["Israeli10K"] & memberships["Arivale"]) - memberships["UKBB"]
        ukbb_arivale_only = (memberships["UKBB"] & memberships["Arivale"]) - memberships["Israeli10K"]
        
        all_three = memberships["Israeli10K_UKBB_Arivale"]
        
        # Create Venn diagram
        venn = venn3(
            subsets=(
                len(i10k_only),          # 100
                len(ukbb_only),          # 010
                len(i10k_ukbb_only),     # 110
                len(arivale_only),       # 001
                len(i10k_arivale_only),  # 101
                len(ukbb_arivale_only),  # 011
                len(all_three)           # 111
            ),
            set_labels=('Israeli10K', 'UKBB', 'Arivale'),
            alpha=0.5
        )
        
        # Customize colors
        if venn.get_patch_by_id('100'):
            venn.get_patch_by_id('100').set_color('lightblue')
        if venn.get_patch_by_id('010'):
            venn.get_patch_by_id('010').set_color('lightgreen')
        if venn.get_patch_by_id('001'):
            venn.get_patch_by_id('001').set_color('lightcoral')
        
        # Add circles
        venn3_circles(subsets=(1, 1, 1, 1, 1, 1, 1), linewidth=2)
        
        plt.title("Three-Way Metabolite Overlap", fontsize=16, fontweight='bold')
        
        # Add statistics text
        total_unique = len(memberships["Israeli10K"] | memberships["UKBB"] | memberships["Arivale"])
        three_way_count = len(memberships["Israeli10K_UKBB_Arivale"])
        plt.text(0.5, -0.1, f"Total unique metabolites: {total_unique}\nThree-way overlap: {three_way_count}",
                 transform=ax.transAxes, ha='center', fontsize=10)
        
        output_path = output_dir / "venn_diagram_3way.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _create_confidence_heatmap(self, stats: Dict[str, Any], output_dir: Path) -> str:
        """Create confidence distribution heatmap."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            import numpy as np
        except ImportError:
            logger.warning("seaborn not installed, skipping confidence heatmap")
            return ""
        
        # Prepare data for heatmap
        overlap_types = ["Israeli10K_UKBB", "Israeli10K_Arivale", "UKBB_Arivale", "three_way"]
        confidence_levels = ["high", "medium", "low"]
        
        data = []
        for overlap_type in overlap_types:
            if overlap_type in stats and isinstance(stats[overlap_type], OverlapStatistics):
                row = []
                conf_dist = stats[overlap_type].confidence_distribution
                total = sum(conf_dist.values())
                for level in confidence_levels:
                    # Calculate percentage
                    if total > 0:
                        row.append(100 * conf_dist[level] / total)
                    else:
                        row.append(0)
                data.append(row)
        
        if not data:
            logger.warning("No confidence data available for heatmap")
            return ""
        
        data_array = np.array(data)
        
        plt.figure(figsize=(8, 6))
        ax = sns.heatmap(
            data_array,
            annot=True,
            fmt='.1f',
            cmap='YlOrRd',
            xticklabels=["High (≥0.9)", "Medium (≥0.7)", "Low (<0.7)"],
            yticklabels=["Israeli10K-UKBB", "Israeli10K-Arivale", "UKBB-Arivale", "Three-way"],
            cbar_kws={'label': 'Percentage (%)'}
        )
        
        plt.title("Confidence Distribution by Overlap Type", fontsize=14, fontweight='bold')
        plt.xlabel("Confidence Level", fontsize=12)
        plt.ylabel("Overlap Type", fontsize=12)
        
        output_path = output_dir / "confidence_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _create_provenance_sankey(self, stats: Dict[str, Any], output_dir: Path) -> str:
        """Create provenance Sankey diagram (placeholder for now)."""
        # This would require plotly or similar library
        # For now, we'll create a simple flow diagram using matplotlib
        logger.info("Provenance Sankey diagram generation not implemented yet")
        return ""
    
    def _create_method_breakdown(self, stats: Dict[str, Any], output_dir: Path) -> str:
        """Create method breakdown pie chart (placeholder for now)."""
        logger.info("Method breakdown pie chart generation not implemented yet")
        return ""
    
    def _create_progression_chart(self, stats: Dict[str, Any], output_dir: Path) -> str:
        """Create overlap progression chart."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib not installed, skipping progression chart")
            return ""
        
        # Extract data for chart
        categories = []
        counts = []
        
        # Individual datasets
        for dataset in ["Israeli10K", "UKBB", "Arivale"]:
            if dataset in stats:
                categories.append(f"{dataset} only")
                unique_count = stats[dataset].get("unique_metabolites", 0)
                counts.append(unique_count)
        
        # Pairwise overlaps (exclusive)
        pairwise_data = []
        for pair_key in ["Israeli10K_UKBB", "Israeli10K_Arivale", "UKBB_Arivale"]:
            if pair_key in stats and isinstance(stats[pair_key], OverlapStatistics):
                # This is total overlap, we need exclusive pairwise
                # For now, we'll use the total
                pairwise_data.append((pair_key.replace("_", "-"), stats[pair_key].count))
        
        # Sort pairwise by count
        pairwise_data.sort(key=lambda x: x[1], reverse=True)
        for name, count in pairwise_data:
            categories.append(name)
            counts.append(count)
        
        # Three-way overlap
        if "three_way" in stats and isinstance(stats["three_way"], OverlapStatistics):
            categories.append("Three-way")
            counts.append(stats["three_way"].count)
        
        # Create bar chart
        plt.figure(figsize=(10, 6))
        bars = plt.bar(categories, counts, color=['lightblue', 'lightgreen', 'lightcoral', 
                                                  'gold', 'orange', 'purple', 'red'])
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        plt.title("Metabolite Distribution Across Datasets", fontsize=14, fontweight='bold')
        plt.xlabel("Dataset/Overlap Type", fontsize=12)
        plt.ylabel("Number of Metabolites", fontsize=12)
        plt.xticks(rotation=45, ha='right')
        
        output_path = output_dir / "overlap_progression_chart.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _export_detailed_results(
        self,
        three_way_matches: List[Dict[str, Any]],
        two_way_matches: List[Dict[str, Any]],
        stats: Dict[str, Any],
        output_dir: Path,
        mapping_combo_id: str
    ):
        """Export detailed results to CSV files."""
        try:
            import pandas as pd
        except ImportError:
            logger.warning("pandas not installed, skipping CSV export")
            return
        
        # 1. Export all matches (three-way and two-way)
        all_matches = three_way_matches + two_way_matches
        matches_data = []
        
        for m in all_matches:
            row = {
                "metabolite_id": m["metabolite_id"],
                "match_confidence": m.get("match_confidence", 0),
                "match_methods": ";".join(m.get("match_methods", [])),
                "dataset_count": m.get("dataset_count", 0),
                "is_complete": m.get("is_complete", False),
            }
            
            # Add Israeli10K data
            if m.get("israeli10k"):
                row["israeli10k_field_name"] = m["israeli10k"].get("field_name", "")
                row["israeli10k_display_name"] = m["israeli10k"].get("display_name", "")
                row["nightingale_name"] = m["israeli10k"].get("nightingale_name", "")
            else:
                row["israeli10k_field_name"] = ""
                row["israeli10k_display_name"] = ""
                row["nightingale_name"] = ""
            
            # Add UKBB data
            if m.get("ukbb"):
                row["ukbb_field_id"] = m["ukbb"].get("field_id", "")
                row["ukbb_title"] = m["ukbb"].get("title", "")
            else:
                row["ukbb_field_id"] = ""
                row["ukbb_title"] = ""
            
            # Add Arivale data
            if m.get("arivale"):
                row["arivale_biochemical_name"] = m["arivale"].get("biochemical_name", "")
                row["arivale_hmdb"] = m["arivale"].get("hmdb", "")
                row["arivale_kegg"] = m["arivale"].get("kegg", "")
            else:
                row["arivale_biochemical_name"] = ""
                row["arivale_hmdb"] = ""
                row["arivale_kegg"] = ""
            
            matches_data.append(row)
        
        matches_df = pd.DataFrame(matches_data)
        matches_df.to_csv(
            output_dir / f"{mapping_combo_id}_three_way_matches.csv",
            index=False
        )
        
        # 2. Export overlap statistics
        stats_data = []
        for key, stat in stats.items():
            if isinstance(stat, OverlapStatistics):
                stats_data.append({
                    "overlap_type": key,
                    "count": stat.count,
                    "jaccard_index": stat.jaccard_index,
                    "percentage_of_first": stat.percentage_of_first,
                    "percentage_of_second": stat.percentage_of_second,
                    "percentage_of_third": stat.percentage_of_third,
                    "high_confidence_count": stat.confidence_distribution.get("high", 0),
                    "medium_confidence_count": stat.confidence_distribution.get("medium", 0),
                    "low_confidence_count": stat.confidence_distribution.get("low", 0),
                })
        
        if stats_data:
            pd.DataFrame(stats_data).to_csv(
                output_dir / f"{mapping_combo_id}_overlap_statistics.csv",
                index=False
            )
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: CalculateThreeWayOverlapParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any
    ) -> StandardActionResult:
        """Execute the three-way overlap calculation."""
        logger.info("Starting CALCULATE_THREE_WAY_OVERLAP action")
        
        # Get datasets from context
        datasets = context.get_action_data("datasets", {})
        
        # Get combined matches from previous action
        combined_data = datasets.get(params.input_key, {})
        if not combined_data:
            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[],
                details={
                    "success": False,
                    "error": f"No data found for input key: {params.input_key}"
                }
            )
        
        three_way_matches = combined_data.get("three_way_matches", [])
        two_way_matches = combined_data.get("two_way_matches", [])
        
        logger.info(
            f"Processing {len(three_way_matches)} three-way matches and "
            f"{len(two_way_matches)} two-way matches"
        )
        
        # Extract dataset memberships
        memberships = self._extract_dataset_memberships(
            three_way_matches,
            two_way_matches,
            params.confidence_threshold
        )
        
        # Calculate overlap statistics
        all_matches = three_way_matches + two_way_matches
        stats = self._calculate_overlap_statistics(
            memberships,
            params.dataset_names,
            all_matches
        )
        
        # Create output directory
        import os
        output_dir = Path(os.path.expandvars(params.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate visualizations
        viz_paths = {}
        if params.generate_visualizations:
            viz_paths = self._generate_visualizations(
                memberships,
                stats,
                output_dir,
                params.generate_visualizations
            )
        
        # Export detailed results
        if params.export_detailed_results:
            self._export_detailed_results(
                three_way_matches,
                two_way_matches,
                stats,
                output_dir,
                params.mapping_combo_id
            )
        
        # Prepare result statistics
        result_stats = {
            "dataset_statistics": {},
            "overlap_statistics": {},
            "visualizations": viz_paths,
            "output_directory": str(output_dir),
        }
        
        # Add dataset statistics
        for dataset in params.dataset_names:
            if dataset in stats:
                result_stats["dataset_statistics"][dataset] = stats[dataset]
        
        # Add overlap statistics
        for key, stat in stats.items():
            if isinstance(stat, OverlapStatistics):
                result_stats["overlap_statistics"][key] = stat.dict()
        
        # Store results in context
        datasets[params.output_key] = result_stats
        context.set_action_data("datasets", datasets)
        
        # Create provenance entry
        provenance_entry = {
            "action": "CALCULATE_THREE_WAY_OVERLAP",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "parameters": params.dict(),
            "summary": {
                "total_three_way_matches": len(three_way_matches),
                "total_two_way_matches": len(two_way_matches),
                "confidence_threshold": params.confidence_threshold,
                "visualizations_generated": len(viz_paths),
            }
        }
        
        logger.info(
            f"Three-way overlap calculation complete. "
            f"Generated {len(viz_paths)} visualizations and exported results to {output_dir}"
        )
        
        return StandardActionResult(
            input_identifiers=current_identifiers,
            output_identifiers=current_identifiers,  # Pass through
            output_ontology_type=current_ontology_type,
            provenance=[provenance_entry],
            details={
                "success": True,
                "message": "Successfully calculated three-way overlap statistics",
                "statistics": result_stats,
                "visualizations_generated": list(viz_paths.keys()),
                "output_directory": str(output_dir),
            }
        )