# /home/ubuntu/biomapper/scripts/migrate_path_steps_format.py
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Assuming models.py is in biomapper/db/
# Adjust the import path if your project structure is different
from biomapper.db.models import MappingPath

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Resource Name to ID Mapping ---
# Case-insensitive mapping
RESOURCE_NAME_TO_ID = {
    "unichem": 10,
    "pubchem": 6,
    "pubchem_api": 6,
    "kegg": 9,
    "chebi": 5,
    "chebi_api": 5,
    "chebi_property_extractor": 5,
    "ramp": 12,
    "refmet": 11,
    # Add other mappings if necessary
}

def get_database_url() -> str:
    """Gets the database URL from environment variables."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set or .env file not found.")
    return db_url

def normalize_resource_name(name: Optional[str]) -> Optional[str]:
    """Converts resource name to lowercase for case-insensitive matching."""
    return name.lower() if name else None

def get_resource_id(resource_name: Optional[str]) -> Optional[int]:
    """Finds resource ID from the mapping."""
    normalized_name = normalize_resource_name(resource_name)
    return RESOURCE_NAME_TO_ID.get(normalized_name) if normalized_name else None

def extract_value(step_dict: Dict[str, Any], keys: List[str]) -> Optional[str]:
    """Extracts value from dict trying multiple keys."""
    for key in keys:
        if key in step_dict:
            return str(step_dict[key]) # Ensure string type
    return None

async def migrate_paths(session: AsyncSession):
    """Fetches, converts, and updates mapping paths."""
    logger.info("Querying all MappingPaths...")
    stmt = select(MappingPath)
    result = await session.execute(stmt)
    all_paths = result.scalars().all()
    logger.info(f"Found {len(all_paths)} total mapping paths to process.")

    updated_count = 0
    failed_count = 0
    skipped_no_change = 0

    paths_to_update = []

    for path in all_paths:
        original_steps_str = path.path_steps
        new_steps_list: List[Dict[str, Any]] = []
        conversion_failed = False

        if not original_steps_str:
            logger.warning(f"Path ID {path.id}: Original path_steps is empty or null. Skipping.")
            continue

        try:
            old_steps = json.loads(original_steps_str)
            if not isinstance(old_steps, list):
                logger.error(f"Path ID {path.id}: path_steps is not a JSON list. Content: {original_steps_str}. Skipping.")
                failed_count += 1
                continue

            if not old_steps:
                 logger.warning(f"Path ID {path.id}: path_steps JSON list is empty. Skipping.")
                 continue


            for i, old_step in enumerate(old_steps):
                if not isinstance(old_step, dict):
                    logger.error(f"Path ID {path.id}, Step {i+1}: Step is not a dictionary. Content: {old_step}. Path conversion failed.")
                    conversion_failed = True
                    break

                # Extract source, target, and resource
                source_type = extract_value(old_step, ["source_type", "source", "from_type"])
                target_type = extract_value(old_step, ["target_type", "target", "to_type"])
                resource_name: Optional[str] = None
                if "resources" in old_step and isinstance(old_step["resources"], list) and old_step["resources"]:
                    resource_name = str(old_step["resources"][0]) # Take the first resource name
                elif "resource" in old_step: # Handle single 'resource' key if present
                     resource_name = str(old_step["resource"])

                if not source_type or not target_type:
                    logger.error(f"Path ID {path.id}, Step {i+1}: Could not extract source ('{source_type}') or target ('{target_type}'). Path conversion failed.")
                    conversion_failed = True
                    break

                resource_id = get_resource_id(resource_name)

                if resource_id is None:
                    logger.error(f"Path ID {path.id}, Step {i+1}: Could not find resource ID for name '{resource_name}'. Path conversion failed.")
                    conversion_failed = True
                    break

                # Construct new step
                new_step = {
                    "source_type": source_type,
                    "target_type": target_type,
                    "resource_id": resource_id,
                }
                # Preserve other keys if necessary (optional)
                # for key, value in old_step.items():
                #     if key not in ["source_type", "source", "from_type", "target_type", "target", "to_type", "resources", "resource"]:
                #         new_step[key] = value
                new_steps_list.append(new_step)

            if conversion_failed:
                failed_count += 1
                continue # Skip update for this path

            # Successfully converted all steps for this path
            new_steps_str = json.dumps(new_steps_list)

            # Check if the new JSON string is actually different from the old one
            if new_steps_str != original_steps_str:
                logger.info(f"Path ID {path.id}: Converted successfully. Original: {original_steps_str}, New: {new_steps_str}")
                paths_to_update.append({"id": path.id, "path_steps": new_steps_str})
            else:
                 logger.info(f"Path ID {path.id}: Already in correct format or conversion resulted in no change. Skipping update.")
                 skipped_no_change += 1


        except json.JSONDecodeError:
            logger.error(f"Path ID {path.id}: Failed to decode original path_steps JSON: {original_steps_str}. Skipping.")
            failed_count += 1
        except Exception as e:
            logger.error(f"Path ID {path.id}: Unexpected error during conversion: {e}. Skipping.")
            failed_count += 1

    # --- Perform Batch Update ---
    if paths_to_update:
        logger.info(f"Attempting to update {len(paths_to_update)} paths in the database...")
        try:
            # Using Core API update for potentially better performance with many updates
            update_stmt = update(MappingPath).where(MappingPath.id == sqlalchemy.bindparam('path_id')).values(path_steps=sqlalchemy.bindparam('new_steps'))
            await session.execute(update_stmt, [{"path_id": p["id"], "new_steps": p["path_steps"]} for p in paths_to_update])
            await session.commit()
            updated_count = len(paths_to_update)
            logger.info(f"Successfully committed updates for {updated_count} paths.")
        except SQLAlchemyError as e:
            logger.error(f"Database error during update commit: {e}")
            await session.rollback()
            updated_count = 0 # Reset count as commit failed
            failed_count += len(paths_to_update) # Assume all attempted updates failed
        except Exception as e:
            logger.error(f"Unexpected error during database update: {e}")
            await session.rollback()
            updated_count = 0
            failed_count += len(paths_to_update)

    logger.info("--- Migration Summary ---")
    logger.info(f"Paths successfully updated: {updated_count}")
    logger.info(f"Paths skipped (no change needed): {skipped_no_change}")
    logger.info(f"Paths failed conversion or update: {failed_count}")
    logger.info(f"Total paths processed: {len(all_paths)}")
    logger.info("-------------------------")

async def main():
    """Main execution function."""
    try:
        db_url = get_database_url()
        engine = create_async_engine(db_url)
        async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session_factory() as session:
            await migrate_paths(session)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}")

if __name__ == "__main__":
    # Ensure the script can find the biomapper package
    # Add project root to sys.path if necessary, or run with `poetry run`
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Need to import sqlalchemy.bindparam after adding to sys.path if needed
    import sqlalchemy

    asyncio.run(main())
