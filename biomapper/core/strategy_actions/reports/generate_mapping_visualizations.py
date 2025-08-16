"""Generate mapping visualizations and statistics files."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action


class VisualizationResult(BaseModel):
    """Result of visualization generation."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class GenerateMappingVisualizationsParams(BaseModel):
    """Parameters for generating mapping visualizations."""
    
    input_key: str = Field(..., description="Input dataset key containing mapping results")
    output_dir: str = Field(..., description="Directory to write visualization files")
    generate_statistics: bool = Field(True, description="Generate statistics TSV file")
    generate_summary: bool = Field(True, description="Generate text summary file")
    generate_json_report: bool = Field(True, description="Generate JSON report file")
    prefix: str = Field("", description="Prefix for output filenames")


@register_action("GENERATE_MAPPING_VISUALIZATIONS")
class GenerateMappingVisualizationsAction(TypedStrategyAction[GenerateMappingVisualizationsParams, VisualizationResult]):
    """Generate comprehensive mapping visualizations and statistics files."""
    
    def get_params_model(self) -> type[GenerateMappingVisualizationsParams]:
        return GenerateMappingVisualizationsParams
    
    def get_result_model(self) -> type[VisualizationResult]:
        return VisualizationResult
    
    async def execute_typed(
        self,
        params: GenerateMappingVisualizationsParams,
        context: Dict[str, Any],
        **kwargs
    ) -> VisualizationResult:
        """Generate visualization and statistics files."""
        try:
            # Get input data
            df = context["datasets"].get(params.input_key)
            if df is None or df.empty:
                return VisualizationResult(
                    success=False,
                    error=f"No data found for key: {params.input_key}"
                )
            
            # Create output directory
            output_dir = Path(params.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            files_created = []
            
            # Generate statistics TSV
            if params.generate_statistics:
                stats_file = self._generate_statistics_tsv(df, output_dir, params.prefix)
                files_created.append(stats_file)
                
            # Generate text summary
            if params.generate_summary:
                summary_file = self._generate_text_summary(df, output_dir, params.prefix, context)
                files_created.append(summary_file)
                
            # Generate JSON report
            if params.generate_json_report:
                json_file = self._generate_json_report(df, output_dir, params.prefix, context)
                files_created.append(json_file)
            
            # Store file paths in context for Google Drive sync
            if "output_files" not in context:
                context["output_files"] = {}
            
            for file_path in files_created:
                file_name = file_path.stem
                context["output_files"][file_name] = str(file_path)
            
            return VisualizationResult(
                success=True,
                data={
                    "files_created": [str(f) for f in files_created],
                    "output_directory": str(output_dir),
                    "message": f"Generated {len(files_created)} visualization files"
                }
            )
            
        except Exception as e:
            return VisualizationResult(
                success=False,
                error=f"Failed to generate visualizations: {str(e)}"
            )
    
    def _generate_statistics_tsv(self, df: pd.DataFrame, output_dir: Path, prefix: str) -> Path:
        """Generate statistics TSV file."""
        stats_data = []
        
        # Overall statistics
        total_proteins = len(df['uniprot'].unique()) if 'uniprot' in df.columns else len(df)
        
        stats_data.append({
            'Category': 'Overall',
            'Metric': 'Total Proteins',
            'Value': total_proteins,
            'Percentage': '100.0%'
        })
        
        # Mapped vs unmapped
        if 'confidence_score' in df.columns:
            mapped = df[df['confidence_score'] > 0]
            unmapped = df[df['confidence_score'] == 0]
            
            unique_mapped = len(mapped['uniprot'].unique()) if 'uniprot' in mapped.columns else len(mapped)
            unique_unmapped = len(unmapped['uniprot'].unique()) if 'uniprot' in unmapped.columns else len(unmapped)
            
            stats_data.extend([
                {
                    'Category': 'Overall',
                    'Metric': 'Mapped Proteins',
                    'Value': unique_mapped,
                    'Percentage': f"{unique_mapped/total_proteins*100:.1f}%"
                },
                {
                    'Category': 'Overall',
                    'Metric': 'Unmapped Proteins',
                    'Value': unique_unmapped,
                    'Percentage': f"{unique_unmapped/total_proteins*100:.1f}%"
                }
            ])
        
        # Match type breakdown
        if 'match_type' in df.columns:
            for match_type in df['match_type'].unique():
                type_df = df[df['match_type'] == match_type]
                unique_count = len(type_df['uniprot'].unique()) if 'uniprot' in type_df.columns else len(type_df)
                stats_data.append({
                    'Category': 'Match Type',
                    'Metric': match_type.capitalize(),
                    'Value': unique_count,
                    'Percentage': f"{unique_count/total_proteins*100:.1f}%"
                })
        
        # Confidence distribution
        if 'confidence_score' in df.columns:
            ranges = [
                ('High (≥0.9)', df['confidence_score'] >= 0.9),
                ('Medium (0.8-0.9)', (df['confidence_score'] >= 0.8) & (df['confidence_score'] < 0.9)),
                ('Low (<0.8)', (df['confidence_score'] > 0) & (df['confidence_score'] < 0.8)),
                ('Unmapped (0)', df['confidence_score'] == 0)
            ]
            
            for label, mask in ranges:
                unique_count = len(df[mask]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[mask])
                stats_data.append({
                    'Category': 'Confidence',
                    'Metric': label,
                    'Value': unique_count,
                    'Percentage': f"{unique_count/total_proteins*100:.1f}%"
                })
        
        # Save statistics
        stats_df = pd.DataFrame(stats_data)
        file_name = f"{prefix}mapping_statistics.tsv" if prefix else "mapping_statistics.tsv"
        stats_path = output_dir / file_name
        stats_df.to_csv(stats_path, sep='\t', index=False)
        
        return stats_path
    
    def _generate_text_summary(self, df: pd.DataFrame, output_dir: Path, prefix: str, context: Dict) -> Path:
        """Generate text summary with ASCII visualizations."""
        summary = []
        summary.append("=" * 60)
        summary.append("PROTEIN MAPPING RESULTS SUMMARY")
        summary.append("=" * 60)
        summary.append("")
        
        # Basic statistics
        total_proteins = len(df['uniprot'].unique()) if 'uniprot' in df.columns else len(df)
        summary.append(f"Total Unique Proteins: {total_proteins:,}")
        
        if 'confidence_score' in df.columns:
            mapped = df[df['confidence_score'] > 0]
            unmapped = df[df['confidence_score'] == 0]
            unique_mapped = len(mapped['uniprot'].unique()) if 'uniprot' in mapped.columns else len(mapped)
            unique_unmapped = len(unmapped['uniprot'].unique()) if 'uniprot' in unmapped.columns else len(unmapped)
            
            summary.append(f"Successfully Mapped: {unique_mapped:,} ({unique_mapped/total_proteins*100:.1f}%)")
            summary.append(f"Unmapped: {unique_unmapped:,} ({unique_unmapped/total_proteins*100:.1f}%)")
            summary.append("")
            
            # ASCII bar chart for match types
            if 'match_type' in df.columns:
                summary.append("Match Type Distribution:")
                summary.append("-" * 40)
                
                for match_type in ['direct', 'composite', 'historical', 'unmapped']:
                    if match_type in df['match_type'].values:
                        type_df = df[df['match_type'] == match_type]
                        unique_count = len(type_df['uniprot'].unique()) if 'uniprot' in type_df.columns else len(type_df)
                        pct = unique_count / total_proteins * 100
                        bar_length = int(pct / 2)  # Scale to 50 chars max
                        bar = '█' * bar_length + '░' * (50 - bar_length)
                        summary.append(f"{match_type:12} [{bar}] {unique_count:5,} ({pct:5.1f}%)")
                
                summary.append("")
            
            # Confidence score distribution
            summary.append("Confidence Score Distribution:")
            summary.append("-" * 40)
            
            ranges = [
                ('High (≥0.9)', df['confidence_score'] >= 0.9),
                ('Medium (0.8-0.9)', (df['confidence_score'] >= 0.8) & (df['confidence_score'] < 0.9)),
                ('Low (<0.8)', (df['confidence_score'] > 0) & (df['confidence_score'] < 0.8)),
                ('None (0.0)', df['confidence_score'] == 0)
            ]
            
            for label, mask in ranges:
                unique_count = len(df[mask]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[mask])
                pct = unique_count / total_proteins * 100
                bar_length = int(pct / 2)
                bar = '█' * bar_length + '░' * (50 - bar_length)
                summary.append(f"{label:15} [{bar}] {unique_count:5,} ({pct:5.1f}%)")
        
        summary.append("")
        summary.append("=" * 60)
        
        # Save summary
        file_name = f"{prefix}results_summary.txt" if prefix else "results_summary.txt"
        summary_path = output_dir / file_name
        with open(summary_path, 'w') as f:
            f.write('\n'.join(summary))
        
        return summary_path
    
    def _generate_json_report(self, df: pd.DataFrame, output_dir: Path, prefix: str, context: Dict) -> Path:
        """Generate comprehensive JSON report."""
        total_proteins = len(df['uniprot'].unique()) if 'uniprot' in df.columns else len(df)
        
        report = {
            "strategy": context.get("strategy_name", "unknown"),
            "version": context.get("strategy_version", "1.0"),
            "execution_date": pd.Timestamp.now().isoformat(),
            "input": {
                "total_rows": len(df),
                "unique_proteins": total_proteins
            },
            "results": {}
        }
        
        if 'confidence_score' in df.columns:
            mapped = df[df['confidence_score'] > 0]
            unmapped = df[df['confidence_score'] == 0]
            unique_mapped = len(mapped['uniprot'].unique()) if 'uniprot' in mapped.columns else len(mapped)
            
            report["results"] = {
                "mapped_proteins": unique_mapped,
                "unmapped_proteins": total_proteins - unique_mapped,
                "match_rate_percentage": round(unique_mapped / total_proteins * 100, 1)
            }
        
        if 'match_type' in df.columns:
            match_breakdown = {}
            for match_type in df['match_type'].unique():
                type_df = df[df['match_type'] == match_type]
                unique_count = len(type_df['uniprot'].unique()) if 'uniprot' in type_df.columns else len(type_df)
                match_breakdown[match_type] = unique_count
            report["match_type_breakdown"] = match_breakdown
        
        if 'confidence_score' in df.columns:
            report["confidence_distribution"] = {
                "high_0.9_plus": len(df[df['confidence_score'] >= 0.9]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[df['confidence_score'] >= 0.9]),
                "medium_0.8_0.9": len(df[(df['confidence_score'] >= 0.8) & (df['confidence_score'] < 0.9)]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[(df['confidence_score'] >= 0.8) & (df['confidence_score'] < 0.9)]),
                "low_below_0.8": len(df[(df['confidence_score'] > 0) & (df['confidence_score'] < 0.8)]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[(df['confidence_score'] > 0) & (df['confidence_score'] < 0.8)]),
                "unmapped_0.0": len(df[df['confidence_score'] == 0]['uniprot'].unique()) if 'uniprot' in df.columns else len(df[df['confidence_score'] == 0])
            }
        
        # Progressive stats if available
        if "progressive_stats" in context:
            report["progressive_stats"] = context["progressive_stats"]
        
        # Save JSON report
        file_name = f"{prefix}mapping_report.json" if prefix else "mapping_report.json"
        json_path = output_dir / file_name
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return json_path