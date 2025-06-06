import asyncio
import json
import importlib
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.db.models import MappingResource # Keep this for MappingResource
from biomapper.db.session import get_async_session # Import the async session getter
from biomapper.config import settings # Import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_client_initialization(resource_name: str):
    """Fetches a MappingResource and attempts to initialize its client."""
    async with await get_async_session() as session: # Await the coroutine to get the session object
        try:
            stmt = select(MappingResource).where(MappingResource.name == resource_name)
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()

            if not resource:
                logger.error(f"MappingResource '{resource_name}' not found in the database.")
                return False

            logger.info(f"Found resource: {resource.name}")
            logger.info(f"Client class path: {resource.client_class_path}")
            logger.info(f"Config template: {resource.config_template}")

            # Dynamically import the client class
            module_path, class_name = resource.client_class_path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                client_class = getattr(module, class_name)
            except ImportError as e:
                logger.error(f"Failed to import module {module_path}: {e}")
                return False
            except AttributeError as e:
                logger.error(f"Failed to get class {class_name} from module {module_path}: {e}")
                return False

            # Parse the config template (JSON string)
            try:
                config = json.loads(resource.config_template)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse config_template JSON: {e}")
                logger.error(f"Problematic JSON string: {resource.config_template}")
                return False
            
            # Instantiate the client
            logger.info(f"Attempting to initialize client {class_name} with config: {config}")
            client_instance = client_class(**config)
            logger.info(f"Successfully initialized client: {client_instance}")
            return True

        except Exception as e:
            logger.exception(f"An error occurred during client initialization test for '{resource_name}': {e}")
            return False

async def main():
    # Configure the correct database URL
    # project_root is defined globally in this script
    correct_db_url = f"sqlite+aiosqlite:///{project_root}/data/metamapper.db"
    logger.info(f"Overriding settings.cache_db_url to: {correct_db_url}")
    settings.cache_db_url = correct_db_url

    # Test with one of the Arivale clients whose config was updated
    # For example, 'Arivale_UniProt_Lookup' which uses ArivaleMetadataLookupClient
    resource_to_test = "Arivale_UniProt_Lookup"
    success = await verify_client_initialization(resource_to_test)
    if success:
        logger.info(f"Verification successful for {resource_to_test}.")
    else:
        logger.error(f"Verification FAILED for {resource_to_test}.")

if __name__ == "__main__":
    asyncio.run(main())
