import asyncio
from pathlib import Path
import sys
import logging
from biomapper.loaders.hmdb_loader import HMDBLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("hmdb_load.log")],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Load HMDB metabolites into Chroma database."""
    try:
        # Configure paths
        project_root = Path(__file__).parent.parent
        sys.path.append(str(project_root))
        xml_path = Path(project_root) / "hmdb_metabolites.xml"
        chroma_path = str(Path(project_root) / "vector_store")

        # Initialize and run loader
        loader = HMDBLoader(chroma_path)
        await loader.load_file(xml_path)

    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
