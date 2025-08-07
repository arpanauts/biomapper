#!/usr/bin/env python3
"""
Setup script to load HMDB data into Qdrant.

Usage:
    python scripts/setup_hmdb_qdrant.py --xml-path /path/to/hmdb_metabolites.xml
    python scripts/setup_hmdb_qdrant.py --xml-path /home/ubuntu/biomapper/data/hmdb_metabolites.xml --batch-size 50
"""

import asyncio
import logging
import argparse
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biomapper.processors.hmdb import HMDBProcessor
from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
from biomapper.rag.metabolite_search import MetaboliteSearcher


def setup_logging(log_level: str = "INFO", log_file: str = "hmdb_qdrant_setup.log"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )


async def verify_setup(searcher: MetaboliteSearcher, test_compounds: list):
    """Verify the setup by testing searches for known compounds."""
    logger = logging.getLogger(__name__)
    logger.info("Verifying setup with test searches...")

    verification_results = {}

    for compound in test_compounds:
        try:
            results = await searcher.search_by_name(compound, limit=3)
            verification_results[compound] = {
                "found": len(results) > 0,
                "top_score": results[0]["score"] if results else 0.0,
                "matches": len(results),
            }

            if results:
                logger.info(
                    f"✓ Found {len(results)} matches for '{compound}' (top score: {results[0]['score']:.3f})"
                )
                logger.info(
                    f"  Best match: {results[0]['name']} ({results[0]['hmdb_id']})"
                )
            else:
                logger.warning(f"✗ No matches found for '{compound}'")

        except Exception as e:
            logger.error(f"Error searching for '{compound}': {e}")
            verification_results[compound] = {"found": False, "error": str(e)}

    return verification_results


async def main():
    parser = argparse.ArgumentParser(description="Load HMDB metabolites into Qdrant")
    parser.add_argument(
        "--xml-path", type=Path, required=True, help="Path to HMDB metabolites XML file"
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default="localhost:6333",
        help="Qdrant server URL (default: localhost:6333)",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="hmdb_metabolites",
        help="Collection name (default: hmdb_metabolites)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="BAAI/bge-small-en-v1.5",
        help="FastEmbed model name (default: BAAI/bge-small-en-v1.5)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="hmdb_qdrant_setup.log",
        help="Log file path (default: hmdb_qdrant_setup.log)",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip verification step at the end",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)

    # Validate XML file exists
    if not args.xml_path.exists():
        logger.error(f"XML file not found: {args.xml_path}")
        return 1

    logger.info("Starting HMDB metabolite loading process")
    logger.info(f"XML file: {args.xml_path}")
    logger.info(f"Qdrant URL: {args.qdrant_url}")
    logger.info(f"Collection: {args.collection_name}")
    logger.info(f"Embedding model: {args.embedding_model}")
    logger.info(f"Batch size: {args.batch_size}")

    try:
        # Initialize components
        logger.info("Initializing processor and loader...")
        processor = HMDBProcessor(args.xml_path)
        loader = HMDBQdrantLoader(
            processor=processor,
            qdrant_url=args.qdrant_url,
            collection_name=args.collection_name,
            embedding_model=args.embedding_model,
            batch_size=args.batch_size,
        )

        # Setup collection
        logger.info("Setting up Qdrant collection...")
        await loader.setup_collection()

        # Load metabolites with timing
        logger.info("Starting metabolite loading...")
        start_time = time.time()

        stats = await loader.load_metabolites()

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Report results
        logger.info("=" * 60)
        logger.info("LOADING COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total processed: {stats['total_processed']:,}")
        logger.info(f"Total errors: {stats['total_errors']:,}")
        logger.info(f"Elapsed time: {elapsed_time:.1f} seconds")

        if stats["total_processed"] > 0:
            logger.info(
                f"Processing rate: {stats['total_processed'] / elapsed_time:.1f} metabolites/second"
            )
            success_rate = (
                stats["total_processed"]
                / (stats["total_processed"] + stats["total_errors"])
            ) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        # Verification step
        if not args.skip_verification and stats["total_processed"] > 0:
            logger.info("\nStarting verification...")
            searcher = MetaboliteSearcher(
                qdrant_url=args.qdrant_url,
                collection_name=args.collection_name,
                embedding_model=args.embedding_model,
            )

            # Test compounds from Arivale dataset
            test_compounds = [
                "spermidine",
                "cholesterol",
                "glucose",
                "12,13-DiHOME",
                "S-1-pyrroline-5-carboxylate",
                "1-methylnicotinamide",
            ]

            verification_results = await verify_setup(searcher, test_compounds)

            # Summary
            successful_searches = sum(
                1 for r in verification_results.values() if r.get("found", False)
            )
            logger.info(
                f"\nVerification Summary: {successful_searches}/{len(test_compounds)} test compounds found"
            )

            if successful_searches == len(test_compounds):
                logger.info("✓ All test compounds found - setup appears successful!")
            elif successful_searches > len(test_compounds) // 2:
                logger.warning(
                    "⚠ Some test compounds not found - setup may need tuning"
                )
            else:
                logger.error("✗ Many test compounds not found - setup may have issues")

        logger.info("\nSetup completed successfully!")
        return 0

    except KeyboardInterrupt:
        logger.warning("Setup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Setup failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
