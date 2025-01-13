import asyncio
from pathlib import Path
import sys
import os
import logging
from typing import NoReturn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('hmdb_load.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from biomapper.loaders.hmdb_loader import HMDBLoader

async def main() -> None:
    """Load HMDB metabolites into Chroma database."""
    try:
        # Configure paths
        xml_path = Path("/home/trentleslie/github/biomapper/hmdb_metabolites.xml")
        chroma_path = "/home/trentleslie/github/biomapper/vector_store"
        
        # Initialize and run loader
        loader = HMDBLoader(chroma_path)
        await loader.load_file(xml_path)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
