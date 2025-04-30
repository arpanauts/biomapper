import asyncio
import logging
import pandas as pd
from biomapper.core.mapping_executor import MappingExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
INPUT_FILE_PATH = (
    "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"
)
IDENTIFIER_COLUMN = "Assay"
SOURCE_ENDPOINT_NAME = "UKBB_Protein"
TARGET_ENDPOINT_NAME = "UKBB_Protein"  # Mapping within the same endpoint context
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"  # Corresponds to GENE_NAME
TARGET_PROPERTY_NAME = "EnsemblGeneID"  # Corresponds to ENSEMBL_GENE
# -------------------


async def main():
    """Reads identifiers from the UKBB file and runs mapping."""
    logger.info(
        f"Reading identifiers from {INPUT_FILE_PATH}, column '{IDENTIFIER_COLUMN}'"
    )

    try:
        df = pd.read_csv(INPUT_FILE_PATH, sep="\t", usecols=[IDENTIFIER_COLUMN])
        # Get unique, non-null identifiers
        input_ids = df[IDENTIFIER_COLUMN].dropna().unique().tolist()
        logger.info(f"Read {len(input_ids)} unique identifiers.")
    except FileNotFoundError:
        logger.error(f"Error: Input file not found at {INPUT_FILE_PATH}")
        return
    except KeyError:
        logger.error(
            f"Error: Column '{IDENTIFIER_COLUMN}' not found in {INPUT_FILE_PATH}"
        )
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return

    if not input_ids:
        logger.warning("No identifiers found in the specified column. Exiting.")
        return

    # Initialize the executor (it will use the DB URLs from config)
    executor = MappingExecutor()

    logger.info("Starting mapping execution...")
    logger.info(
        f"Mapping from {SOURCE_ENDPOINT_NAME}:{SOURCE_PROPERTY_NAME} to {TARGET_ENDPOINT_NAME}:{TARGET_PROPERTY_NAME}"
    )

    # Execute the mapping
    mapping_results = await executor.execute_mapping(
        source_endpoint_name=SOURCE_ENDPOINT_NAME,
        target_endpoint_name=TARGET_ENDPOINT_NAME,
        input_identifiers=input_ids,
        source_property_name=SOURCE_PROPERTY_NAME,
        target_property_name=TARGET_PROPERTY_NAME,
    )

    logger.info("Mapping execution finished.")

    # Print summary
    print("\n--- Mapping Results Summary ---")
    print(f"Status: {mapping_results.get('status')}")
    print(f"Selected Path ID: {mapping_results.get('selected_path_id')}")
    print(f"Selected Path Name: {mapping_results.get('selected_path_name')}")
    print(f"Error: {mapping_results.get('error')}")

    results_dict = mapping_results.get("results", {})
    mapped_count = sum(1 for v in results_dict.values() if v is not None)
    unmapped_count = len(input_ids) - mapped_count

    print(f"Total Input Identifiers: {len(input_ids)}")
    print(f"Successfully Mapped: {mapped_count}")
    print(f"Unmapped: {unmapped_count}")

    # Optionally print a few results (can be very long)
    # print("\n--- Sample Mappings (first 10) ---")
    # count = 0
    # for source_id, target_id in results_dict.items():
    #     print(f"{source_id} -> {target_id}")
    #     count += 1
    #     if count >= 10:
    #         break


if __name__ == "__main__":
    # Ensure the script can find the biomapper package
    # This might require running with `python -m scripts.run_ukbb_mapping`
    # or ensuring the project root is in PYTHONPATH
    asyncio.run(main())
