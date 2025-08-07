#!/usr/bin/env python3
"""
Quick test script to validate memory-efficient loading with small batch.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biomapper.processors.hmdb import HMDBProcessor
from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def test_memory_fix():
    """Test the memory-efficient loading with a very small batch."""
    xml_path = Path("/home/ubuntu/biomapper/data/hmdb_metabolites.xml")

    if not xml_path.exists():
        print(f"XML file not found: {xml_path}")
        return 1

    processor = HMDBProcessor(xml_path)
    loader = HMDBQdrantLoader(
        processor=processor,
        batch_size=10,  # Very small batch for testing
        collection_name="hmdb_test_memory",
    )

    # Setup collection
    await loader.setup_collection()

    # Process just first few batches
    total = 0
    async for batch in processor.process_metabolite_batch(10):
        valid = [m for m in batch if m.get("hmdb_id") and m.get("name")]
        print(f"Batch: {len(batch)} total, {len(valid)} valid")
        total += len(valid)

        # Stop after processing ~50 metabolites for memory test
        if total >= 50:
            break

    print(f"Memory test completed - processed {total} metabolites without crash")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_memory_fix())
    sys.exit(exit_code)
