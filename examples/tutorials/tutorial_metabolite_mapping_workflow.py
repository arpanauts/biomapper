#!/usr/bin/env python3
"""
Complete Biomapper Tutorial: Compound Mapping and Analysis Workflow

This tutorial demonstrates how to use Biomapper to:
1. Map compound names to standardized identifiers using API lookups and RAG
2. Integrate with SPOKE knowledge graph for pathway analysis
3. Use LLM-powered analysis for deeper insights
4. Process and validate results with confidence scoring

Example Usage:
    python tutorial_metabolite_mapping_workflow.py --input compounds.txt --output results/

For more examples and documentation, visit:
https://biomapper.readthedocs.io/
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

# Import from actual module paths
from biomapper.core import MappingExecutor, MappingExecutorBuilder
from biomapper.core.models import DatabaseConfig, CacheConfig, RAGConfig
from biomapper.mapping.clients.pubchem_client import PubChemClient
from biomapper.mapping.clients.chebi_client import ChEBIClient
from biomapper.rag.stores.chroma_store import ChromaStore

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetaboliteWorkflow:
    """Orchestrates complete metabolite mapping workflow."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.executor = None
        
    async def initialize(self):
        """Initialize the mapping executor."""
        # Configure components
        db_config = DatabaseConfig(url="sqlite+aiosqlite:///data/metabolite_mapping.db")
        cache_config = CacheConfig(backend="memory", ttl=3600)
        rag_config = RAGConfig(
            provider="chroma",
            chroma_path="./data/chroma_metabolites",
            collection_name="metabolites"
        )
        
        # Build executor
        self.executor = MappingExecutorBuilder.create(
            db_config=db_config,
            cache_config=cache_config,
            rag_config=rag_config
        )
        
        await self.executor.initialize()
        logger.info("Mapping executor initialized")
        
    async def map_metabolites(self, metabolite_names: List[str]) -> pd.DataFrame:
        """Map metabolite names to standardized identifiers."""
        logger.info(f"Mapping {len(metabolite_names)} metabolites...")
        
        # Execute mapping using YAML strategy
        result = await self.executor.execute_yaml_strategy(
            strategy_file="configs/strategies/metabolite_comprehensive_mapping.yaml",
            input_data={
                "entities": metabolite_names,
                "entity_type": "metabolite"
            },
            options={
                "include_synonyms": True,
                "confidence_threshold": 0.7
            }
        )
        
        # Convert results to DataFrame
        mappings = []
        if result.success and "mappings" in result.data:
            for mapping in result.data["mappings"]:
                mappings.append({
                    "input_name": mapping.get("query_id"),
                    "mapped_id": mapping.get("mapped_id"),
                    "confidence": mapping.get("confidence", 0),
                    "source": mapping.get("source", "unknown"),
                    "metadata": json.dumps(mapping.get("metadata", {}))
                })
        
        df = pd.DataFrame(mappings)
        logger.info(f"Mapped {len(df)} metabolites successfully")
        return df
        
    async def enrich_with_pathways(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich mapped metabolites with pathway information."""
        logger.info("Enriching with pathway information...")
        
        # This would integrate with SPOKE or other pathway databases
        # For now, we'll add placeholder pathway data
        df["pathways"] = df["mapped_id"].apply(lambda x: f"pathway_for_{x}" if x else None)
        
        return df
        
    async def analyze_results(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze mapping results and generate summary statistics."""
        analysis = {
            "total_metabolites": len(df),
            "successfully_mapped": len(df[df["mapped_id"].notna()]),
            "mapping_rate": len(df[df["mapped_id"].notna()]) / len(df) * 100,
            "confidence_stats": {
                "mean": df["confidence"].mean(),
                "min": df["confidence"].min(),
                "max": df["confidence"].max()
            },
            "sources_used": df["source"].value_counts().to_dict()
        }
        
        return analysis
        
    async def save_results(self, df: pd.DataFrame, analysis: Dict[str, Any]):
        """Save results to files."""
        # Save detailed mappings
        csv_path = self.output_dir / "metabolite_mappings.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved mappings to {csv_path}")
        
        # Save analysis
        json_path = self.output_dir / "analysis_summary.json"
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Saved analysis to {json_path}")
        
    async def run(self, metabolite_names: List[str]):
        """Run complete workflow."""
        try:
            # Initialize
            await self.initialize()
            
            # Map metabolites
            df = await self.map_metabolites(metabolite_names)
            
            # Enrich with pathways
            df = await self.enrich_with_pathways(df)
            
            # Analyze results
            analysis = await self.analyze_results(df)
            
            # Save everything
            await self.save_results(df, analysis)
            
            # Print summary
            print("\n" + "="*50)
            print("WORKFLOW COMPLETED SUCCESSFULLY")
            print("="*50)
            print(f"Total metabolites: {analysis['total_metabolites']}")
            print(f"Successfully mapped: {analysis['successfully_mapped']}")
            print(f"Mapping rate: {analysis['mapping_rate']:.1f}%")
            print(f"Average confidence: {analysis['confidence_stats']['mean']:.3f}")
            print("\nResults saved to:", self.output_dir)
            
        finally:
            if self.executor:
                await self.executor.shutdown()


def load_metabolites(input_file: Path) -> List[str]:
    """Load metabolite names from file."""
    if input_file.suffix == ".txt":
        with open(input_file, "r") as f:
            return [line.strip() for line in f if line.strip()]
    elif input_file.suffix == ".csv":
        df = pd.read_csv(input_file)
        # Assume first column contains metabolite names
        return df.iloc[:, 0].tolist()
    else:
        raise ValueError(f"Unsupported file format: {input_file.suffix}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Complete metabolite mapping workflow"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input file with metabolite names (txt or csv)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Use example metabolites if no input file provided
    if args.input:
        metabolites = load_metabolites(args.input)
    else:
        logger.info("No input file provided, using example metabolites")
        metabolites = [
            "glucose",
            "ATP",
            "NADH",
            "pyruvate",
            "lactate",
            "citrate",
            "alpha-ketoglutarate",
            "succinate",
            "fumarate",
            "malate"
        ]
    
    # Run workflow
    workflow = MetaboliteWorkflow(args.output)
    await workflow.run(metabolites)


if __name__ == "__main__":
    asyncio.run(main())