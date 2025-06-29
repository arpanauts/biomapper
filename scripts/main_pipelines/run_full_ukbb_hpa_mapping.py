#!/usr/bin/env python
"""
Executes the UKBB-HPA protein overlap analysis pipeline via the Biomapper API.

This script serves as a modern client for the Biomapper service. It uses the
`biomapper-client` SDK to connect to the running API and trigger the execution
of a predefined YAML strategy.

This approach replaces the old, monolithic script, decoupling the client
from the core mapping logic and promoting a more robust, scalable, and
maintainable service-oriented architecture.

Usage:
    1. Ensure the biomapper-api service is running.
    2. Ensure the `biomapper_client` package is installed in the environment.
       (e.g., `pip install -e biomapper_client` from the project root)
    3. Run the script:
       python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
"""
import asyncio
import logging
from pprint import pprint
import pandas as pd

# It's assumed the biomapper_client package is installed in the environment.
# If not, you might need to adjust sys.path or install it.
try:
    from biomapper_client import BiomapperClient, ApiError, NetworkError
except ImportError:
    print("Error: The 'biomapper-client' package is not installed.")
    print("Please install it by running 'pip install -e biomapper_client' from the project root.")
    exit(1)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def main():
    """
    Main function to connect to the Biomapper API and execute the overlap analysis strategy.
    """
    # The API client, configured to connect to the default local service.
    # The base_url can be changed to target a remote API instance.
    client = BiomapperClient(base_url="http://localhost:8000")

    # Load the initial list of UKBB protein assay IDs from the data file.
    ukbb_file_path = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"
    logging.info(f"Loading initial identifiers from {ukbb_file_path}")
    try:
        # Using pandas for robust CSV/TSV parsing
        df = pd.read_csv(ukbb_file_path, sep='\t', engine='python')
        input_ids = df['Assay'].dropna().unique().tolist()
        logging.info(f"Loaded {len(input_ids)} unique assay IDs to be mapped.")
    except FileNotFoundError:
        logging.error(f"Input data file not found: {ukbb_file_path}")
        return
    except Exception as e:
        logging.error(f"Failed to load or parse input data file: {e}")
        return

    # Define the initial data context for the strategy.
    initial_context = {
        "input_identifiers": input_ids
    }

    strategy_name = "UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS"
    logging.info(f"Executing strategy: '{strategy_name}' via the API...")

    try:
        # Use the client to execute the strategy. This sends a request to the API,
        # which then runs the full workflow defined in the corresponding YAML file.
        async with client:
            final_context = await client.execute_strategy(
                strategy_name=strategy_name,
                context=initial_context
            )

        logging.info("Strategy execution complete. Final results:")
        
        # Pretty-print the final context returned from the API.
        # The structure of this dictionary depends on the actions in the strategy.
        pprint(final_context)

    except ApiError as e:
        logging.error(f"API Error: The server returned an error (Status: {e.status_code}).")
        logging.error(f"Response: {e.response_body}")
    except NetworkError as e:
        logging.error(f"Network Error: Could not connect to the Biomapper API at {client.base_url}.")
        logging.error(f"Please ensure the API service is running. Details: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())