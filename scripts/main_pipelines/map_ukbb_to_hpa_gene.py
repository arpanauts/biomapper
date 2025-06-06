#!/usr/bin/env python3
"""
Map UKBB protein identifiers (UniProtKB ACs) to HPA gene names.
This is a workaround for identity ontology mapping issues.
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants based on the instruction
UKBB_INPUT_FILE_PATH = "/home/ubuntu/biomapper/data/UKBB_Protein_Meta_test.tsv"
UKBB_IDENTIFIER_COLUMN = "UniProt"
SOURCE_PROPERTY_NAME = "UniProt"
SOURCE_ONTOLOGY_TYPE = "UNIPROTKB_AC"
HPA_ENDPOINT_NAME = "HPA_Protein"
TARGET_ENDPOINT_NAME = HPA_ENDPOINT_NAME
TARGET_PROPERTY_NAME = "gene"
TARGET_ONTOLOGY_TYPE = "GENE_NAME"
OUTPUT_FILE_PATH = "/home/ubuntu/biomapper/output/ukbb_to_hpa_gene_mapped.tsv"


async def main():
    """Main execution function."""
    # Get configuration instance
    config = Config.get_instance()
    # Fix database paths to point to the correct location 
    config.set_for_testing("database.config_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    config.set_for_testing("database.cache_db_url", "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")
    
    logger.info(f"Using Config DB: {config_db_url}")
    logger.info(f"Using Cache DB: {cache_db_url}")

    # 1. Read UKBB input data
    logger.info(f"Reading UKBB input file: {UKBB_INPUT_FILE_PATH}")
    try:
        df_ukbb = pd.read_csv(UKBB_INPUT_FILE_PATH, sep="\t", low_memory=False)
        logger.info(f"Read {len(df_ukbb)} rows from UKBB file")
    except Exception as e:
        logger.error(f"Error reading UKBB file: {e}")
        return

    # Verify required column exists
    if UKBB_IDENTIFIER_COLUMN not in df_ukbb.columns:
        logger.error(f"Error: UKBB file must contain column '{UKBB_IDENTIFIER_COLUMN}'. Found: {df_ukbb.columns.tolist()}")
        return

    # Extract unique UniProt IDs to map
    uniprot_ids = df_ukbb[UKBB_IDENTIFIER_COLUMN].dropna().unique().tolist()
    logger.info(f"Found {len(uniprot_ids)} unique UniProt IDs to map")

    if not uniprot_ids:
        logger.info("No UniProt IDs to map. Exiting.")
        return

    # 2. Initialize MappingExecutor
    logger.info("Initializing MappingExecutor...")
    executor = await MappingExecutor.create(
        metamapper_db_url=config_db_url,
        mapping_cache_db_url=cache_db_url,
        echo_sql=False
    )

    # 3. Execute mapping from UKBB to HPA
    logger.info(f"Executing mapping from UKBB_Protein.{SOURCE_ONTOLOGY_TYPE} to {TARGET_ENDPOINT_NAME}.{TARGET_ONTOLOGY_TYPE}")
    
    mapping_result = await executor.execute_mapping(
        source_endpoint_name="UKBB_Protein",
        target_endpoint_name=TARGET_ENDPOINT_NAME,
        input_identifiers=uniprot_ids,
        source_property_name=SOURCE_PROPERTY_NAME,
        target_property_name=TARGET_PROPERTY_NAME,
        try_reverse_mapping=False,
        validate_bidirectional=False
    )

    # 4. Process results
    success_count = 0
    for result in mapping_result.values():
        if result and result.get("target_identifiers"):
            success_count += 1
    
    logger.info(f"Successfully mapped {success_count} out of {len(uniprot_ids)} UniProt IDs ({success_count/len(uniprot_ids)*100:.1f}%)")

    # 5. Merge results with original data
    # Create a mapping dictionary for easy lookup
    uniprot_to_gene = {}
    for source_id, result_data in mapping_result.items():
        if result_data and "target_identifiers" in result_data:
            target_ids = result_data["target_identifiers"]
            if target_ids:
                # For simplicity, if there are multiple gene names, take the first one
                # In practice, you might want to handle one-to-many mappings differently
                uniprot_to_gene[source_id] = target_ids[0] if target_ids else None

    # Add HPA_GENE_NAME column to the dataframe
    df_ukbb["HPA_GENE_NAME"] = df_ukbb[UKBB_IDENTIFIER_COLUMN].map(uniprot_to_gene)

    # 6. Write output
    output_path = Path(OUTPUT_FILE_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Writing results to {OUTPUT_FILE_PATH}")
    df_ukbb.to_csv(OUTPUT_FILE_PATH, sep="\t", index=False)
    logger.info(f"Output written successfully. Mapped {df_ukbb['HPA_GENE_NAME'].notna().sum()} records.")

    # Log some statistics
    mapped_count = df_ukbb["HPA_GENE_NAME"].notna().sum()
    total_count = len(df_ukbb)
    logger.info(f"Final mapping statistics: {mapped_count}/{total_count} ({mapped_count/total_count*100:.1f}%) records have HPA gene names")


if __name__ == "__main__":
    asyncio.run(main())