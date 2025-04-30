"""Test the UKBB_GeneName_to_Arivale_Protein mapping path."""
import asyncio
import json
import logging
from biomapper.core.mapping_executor import MappingExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Set biomapper executor to DEBUG level
logging.getLogger("biomapper.core.mapping_executor").setLevel(logging.DEBUG)


async def main():
    """Run the UKBB_GeneName_to_Arivale_Protein mapping test."""

    executor = MappingExecutor()

    # Test with a small set of known genes
    input_ids = ["APP", "BRCA1", "TP53", "EGFR", "TNF"]

    # Use the specific path we want to test (UKBB_GeneName_to_Arivale_Protein)
    source_endpoint = "UKBB_Protein"
    source_property = "PrimaryIdentifier"  # Gene name
    target_endpoint = "Arivale_Protein"
    target_property = "PrimaryIdentifier"  # Arivale protein ID

    logging.info(
        f"Executing mapping: {source_endpoint}.{source_property} -> {target_endpoint}.{target_property}"
    )
    mapping_output = await executor.execute_mapping(
        source_endpoint_name=source_endpoint,
        target_endpoint_name=target_endpoint,
        input_identifiers=input_ids,
        source_property_name=source_property,
        target_property_name=target_property,
    )

    logging.info(f"\n--- Mapping Output ---")
    logging.info(json.dumps(mapping_output, indent=2))

    # Count successful mappings
    if "results" in mapping_output:
        successful = sum(
            1 for value in mapping_output["results"].values() if value is not None
        )
        total = len(mapping_output["results"])
        logging.info(
            f"Successfully mapped {successful}/{total} gene names to Arivale protein identifiers"
        )


if __name__ == "__main__":
    asyncio.run(main())
