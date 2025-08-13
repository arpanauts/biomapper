import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Any

import aiohttp

# Configuration constants
DEFAULT_UNIPROT_SYNC_IDMAPPING_API_URL = "https://idmapping.uniprot.org/cgi-bin/idmapping_http_client3"  # Corrected based on documentation
DEFAULT_TIMEOUT = 60  # Default timeout for HTTP requests in seconds
DEFAULT_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

logger = logging.getLogger(__name__)


class UniProtIDMappingClient:
    """A client for the UniProt ID Mapping service (synchronous API endpoint).
    Updated to use POST, manage session, and include retry logic.
    """

    def __init__(
        self,
        from_db: str = "ACC",
        to_db: str = "ACC",
        base_url: str = DEFAULT_UNIPROT_SYNC_IDMAPPING_API_URL,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.from_db = from_db
        self.to_db = to_db
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Python UniProtIDMappingClient/1.1",
            "Accept": "text/plain",
        }
        if session:
            self.session = session
            self._session_managed_internally = False
        else:
            self.session = aiohttp.ClientSession()
            self._session_managed_internally = True
        logger.info(
            f"UniProtIDMappingClient initialized: {from_db} -> {to_db}, URL: {base_url}"
        )

    def _get_from_param(self) -> str:
        """Helper method to get the actual from_db parameter for debugging"""
        return self.from_db

    async def _make_request(self, payload: Dict[str, Any]) -> Optional[str]:
        """Makes an HTTP GET request to the UniProt ID Mapping API with retry logic."""
        max_retries = 3
        base_delay = 1.0  # seconds
        request_timeout = aiohttp.ClientTimeout(total=self.timeout)

        for attempt in range(max_retries):
            try:
                ids_to_log = payload.get("ids", "")
                if isinstance(ids_to_log, str):
                    ids_to_log = ids_to_log.split(
                        ","
                    )  # Assuming ids is comma-separated for logging
                logger.debug(
                    f"Attempt {attempt + 1} to GET from {self.base_url} with {len(ids_to_log)} IDs (params: {payload})..."
                )
                # Use GET and pass payload as params
                async with self.session.get(
                    self.base_url,
                    params=payload,
                    headers=self.headers,
                    timeout=request_timeout,
                ) as response:
                    if response.status == 200:
                        return await response.text()

                    retriable_statuses = [500, 502, 503, 504]
                    if response.status in retriable_statuses:
                        logger.warning(
                            f"Request failed with status {response.status} (retriable). Attempt {attempt + 1} of {max_retries}."
                        )
                        if attempt + 1 == max_retries:
                            logger.error(
                                f"Max retries reached. Request failed with status {response.status}: {await response.text()}"
                            )
                            return None
                        delay = base_delay * (2**attempt)
                        logger.info(f"Retrying in {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        error_text = await response.text()
                        # Handle 405 specifically for this GET attempt - means method is wrong for this URL too
                        if response.status == 405:
                            logger.error(
                                f"Request failed with 405 Method Not Allowed for GET to {self.base_url}. Params: {payload}"
                            )
                        else:
                            logger.error(
                                f"Request failed with non-retriable status {response.status}: {error_text}"
                            )
                        logger.debug(f"Failed params for GET: {payload}")
                        return None
            except aiohttp.ClientError as e:
                logger.warning(
                    f"AIOHTTP client error: {e}. Attempt {attempt + 1} of {max_retries}."
                )
                if attempt + 1 == max_retries:
                    logger.error(f"Max retries reached after AIOHTTP client error: {e}")
                    return None
                delay = base_delay * (2**attempt)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(
                    f"Unexpected error during request: {e}. Attempt {attempt + 1} of {max_retries}."
                )
                if attempt + 1 == max_retries:
                    logger.error(f"Max retries reached after unexpected error: {e}")
                    return None
                delay = base_delay * (2**attempt)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
        return None

    def _parse_response(
        self, response_text: str, input_ids_map: Dict[str, str]
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Parses the tab-separated response from UniProt ID Mapping service."""
        final_mapping: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {
            k: (None, None) for k in input_ids_map.keys()
        }
        count = 0
        lines = response_text.strip().split("\n")

        for line in lines:
            if not line.strip():
                continue
            if line.startswith("MSG:"):
                logger.info(f"UniProt message: {line}")
                continue

            parts = line.split("\t")
            if len(parts) >= 2:
                mapped_from_id, output_ids_str = parts[0], parts[1]
                original_input_id = mapped_from_id

                if original_input_id in final_mapping:
                    primary_ids = [
                        pid.strip() for pid in output_ids_str.split(";") if pid.strip()
                    ]
                    if primary_ids:
                        final_mapping[original_input_id] = (
                            primary_ids,
                            original_input_id,
                        )
                        count += len(primary_ids)
                        logger.debug(f"Resolved {original_input_id} -> {primary_ids}")
                    else:
                        logger.warning(
                            f"Input ID {original_input_id} returned empty mapping result part."
                        )
                else:
                    logger.warning(
                        f"Mapped ID '{mapped_from_id}' from UniProt results was not in the original input list (or not expected). Original inputs: {list(input_ids_map.keys())[:5]}..."
                    )
            elif len(parts) == 1 and parts[0] in final_mapping:
                logger.debug(f"No match found for input ID: {parts[0]}")
            else:
                logger.warning(f"Unexpected line format in UniProt result: '{line}'")

        logger.info(
            f"Successfully parsed {count} primary mappings for {len(input_ids_map)} original input identifiers."
        )
        return final_mapping

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Maps a list of identifiers using the UniProt ID Mapping service."""
        if not identifiers:
            return {}

        original_ids_map = {original_id: original_id for original_id in identifiers}

        params = {
            "ids": ",".join(identifiers),
            "from": self.from_db,
            "to": self.to_db,
            "format": "tab",
            "async": "NO",  # Crucial for synchronous requests
        }
        if config and "taxonId" in config:
            params["taxonId"] = str(config["taxonId"])

        response_text = await self._make_request(params)

        if response_text:
            return self._parse_response(response_text, original_ids_map)
        else:
            logger.error(
                f"No response text received from _make_request for {len(identifiers)} IDs. Returning empty mappings."
            )
            return {k: (None, None) for k in identifiers}

    async def close_session(self):
        """Closes the aiohttp session if it was managed internally."""
        if (
            self._session_managed_internally
            and self.session
            and not self.session.closed
        ):
            await self.session.close()
            logger.info("Internal aiohttp session closed for UniProtIDMappingClient.")


async def run_example() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Running UniProt Sync ID Mapping Client Example...")

    default_client = UniProtIDMappingClient()

    # Test with different from_db values for gene name mapping
    gn_client_1 = UniProtIDMappingClient(from_db="Gene_Name")  # Original value
    gn_client_2 = UniProtIDMappingClient(from_db="Gene name")  # Current value
    gn_client_3 = UniProtIDMappingClient(from_db="GENE_NAME")  # Test uppercase
    gn_client_4 = UniProtIDMappingClient(from_db="GENENAME")  # Test without space
    gn_client_5 = UniProtIDMappingClient(from_db="genename")  # Test lowercase
    gn_client_6 = UniProtIDMappingClient(
        from_db="gene_name"
    )  # Test lowercase with underscore
    gn_client_7 = UniProtIDMappingClient(from_db="gene-name")  # Test with hyphen
    gn_client_8 = UniProtIDMappingClient(from_db="HGNC")  # Test HGNC option
    gn_client_9 = UniProtIDMappingClient(from_db="GeneID")  # Test GeneID option
    gn_client_10 = UniProtIDMappingClient(
        from_db="GeneSymbol"
    )  # Test GeneSymbol option

    ensp_client = UniProtIDMappingClient(from_db="Ensembl_Protein")
    enst_client = UniProtIDMappingClient(from_db="Ensembl_Transcript")

    try:
        # Test with well-known gene names
        well_known_genes = ["TP53", "BRCA1", "ALB", "EGFR", "TNF", "IL6"]
        taxon_config = {"taxonId": "9606"}  # Homo sapiens

        # Create list of clients to test
        gn_clients = [
            ("Gene_Name", gn_client_1),
            ("Gene name", gn_client_2),
            ("GENE_NAME", gn_client_3),
            ("GENENAME", gn_client_4),
            ("genename", gn_client_5),
            ("gene_name", gn_client_6),
            ("gene-name", gn_client_7),
            ("HGNC", gn_client_8),
            ("GeneID", gn_client_9),
            ("GeneSymbol", gn_client_10),
        ]

        # Test each client with the same gene names
        for client_name, client in gn_clients:
            print(f"\n\n{'=' * 80}")
            print(f"TESTING CLIENT: from_db = {client_name}")
            print(f"{'=' * 80}")

            logger.info(f"\nTesting {client_name} -> ACC mapping...")
            # First check the URL and parameters being used
            params = {
                "ids": ",".join(well_known_genes),
                "from": client._get_from_param(),
                "to": client.to_db,
                "format": "tab",
                "async": "NO",
                "taxonId": "9606",
            }
            print(f"\nUsing URL: {client.base_url}")
            print(f"With params: {params}")

            # Now make the actual request
            results = await client.map_identifiers(
                identifiers=well_known_genes, config=taxon_config
            )

            print(f"\n--- Mapping Results ({client_name} -> ACC) ---")
            for input_id, result_tuple in results.items():
                primary_ids, component_id = result_tuple
                print(
                    f"  Input: {input_id} -> Mapped Primary: {primary_ids}, Component: {component_id}"
                )

            # Check if any genes were successfully mapped
            primary_results = {k: v[0] for k, v in results.items() if v[0] is not None}
            num_mapped = len(primary_results)
            print(f"\nSuccessfully mapped {num_mapped}/{len(well_known_genes)} genes.")

            if "TP53" in primary_results:
                tp53_map_result = primary_results["TP53"]
                print(f"TP53 mapped to: {tp53_map_result}")
                if "P04637" in tp53_map_result:
                    print("✅ Successfully mapped TP53 to P04637")
                else:
                    print("❌ TP53 mapping does not include P04637")
            else:
                print("❌ Failed to map TP53")

        # Basic test with default client (ACC -> ACC)
        logger.info("\nTesting default ACC -> ACC mapping...")
        test_ids_acc = ["P0DOY2", "P0CG05", "P12345", "NONEXISTENT"]
        results_acc = await default_client.map_identifiers(identifiers=test_ids_acc)
        print("\n--- Mapping Results (ACC -> Primary ACC) ---")
        for input_id, result_tuple in results_acc.items():
            primary_ids, component_id = result_tuple
            print(
                f"  Input: {input_id} -> Mapped Primary: {primary_ids}, Component: {component_id}"
            )
        primary_results_acc = {
            k: v[0] for k, v in results_acc.items() if v[0] is not None
        }

        # Test Ensembl mapping as a sanity check
        logger.info("\nTesting Ensembl Protein ID -> ACC mapping...")
        ensembl_protein_ids_to_test = ["ENSP00000269305", "ENSP00000000000"]
        results_ensp = await ensp_client.map_identifiers(
            identifiers=ensembl_protein_ids_to_test
        )
        print("\n--- Mapping Results (Ensembl_Protein -> ACC) ---")
        for input_id, result_tuple in results_ensp.items():
            primary_ids, component_id = result_tuple
            print(
                f"  Input: {input_id} -> Mapped Primary: {primary_ids}, Component: {component_id}"
            )
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
    finally:
        # Clean up all clients
        clients_to_close = [
            default_client,
            gn_client_1,
            gn_client_2,
            gn_client_3,
            gn_client_4,
            gn_client_5,
            gn_client_6,
            gn_client_7,
            gn_client_8,
            gn_client_9,
            gn_client_10,
            ensp_client,
            enst_client,
        ]
        for client in clients_to_close:
            if (
                hasattr(client, "_session_managed_internally")
                and client._session_managed_internally
            ):
                await client.close_session()


if __name__ == "__main__":
    asyncio.run(run_example())

# --- Helper functions for external use ---


async def map_gene_names_to_uniprot_acs(
    gene_names: List[str],
    taxon_id: str,
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, Optional[List[str]]]:
    """
    Maps a list of gene names to UniProtKB Accession IDs for a specific taxon.

    IMPORTANT: This function uses "GENENAME" for the from_db parameter, which is the
    only value that works reliably for gene name mapping in our testing. Other seemingly
    valid values like "Gene_Name" or "Gene name" will not work correctly.

    Some considerations when using this function:
    1. The taxon_id parameter helps filter results, but the API may still return entries
       from other species. Additional filtering may be needed.
    2. Results often include unreviewed TrEMBL entries (A0A* pattern) alongside reviewed
       Swiss-Prot entries (P*/Q*/O* pattern).
    3. Not all UniProt ACs returned will match your target database (e.g., Arivale).
       Consider implementing prioritization/filtering based on AC patterns.

    Args:
        gene_names: A list of gene name strings.
        taxon_id: The NCBI taxonomy ID for the species (e.g., "9606" for Homo sapiens).
        session: Optional aiohttp.ClientSession to reuse. If None, a new one is created and managed by the helper.

    Returns:
        A dictionary where keys are input gene names and values are lists of
        mapped UniProtKB ACs. Returns None as value for a gene name if no mapping found or error.
    """
    # If no external session is provided, the client (and this helper) will manage its own.
    # IMPORTANT: "GENENAME" is the correct from_db parameter value - other values like
    # "Gene_Name" or "Gene name" do not work with the UniProt API for gene name mapping
    client = UniProtIDMappingClient(from_db="GENENAME", to_db="ACC", session=session)
    mapping_config = {"taxonId": taxon_id}
    primary_results: Dict[str, Optional[List[str]]] = {}
    try:
        results = await client.map_identifiers(
            identifiers=gene_names, config=mapping_config
        )
        for input_id, result_tuple in results.items():
            (
                primary_ids,
                _,
            ) = result_tuple  # We only care about the primary IDs list here
            primary_results[input_id] = primary_ids
    except Exception as e:
        logger.error(f"Error in map_gene_names_to_uniprot_acs: {e}", exc_info=True)
        # Ensure all input genes are represented in the output, even if with None for errors
        for gn in gene_names:
            if gn not in primary_results:
                primary_results[gn] = None
    finally:
        # If the session was created by *this helper's client instance* (i.e., session arg was None),
        # then the client's close_session will handle it.
        # If an external session was passed, the caller is responsible for closing it.
        if (
            client._session_managed_internally
        ):  # Check if the client created the session
            await client.close_session()
    return primary_results


async def map_ensembl_ids_to_uniprot_acs(
    ensembl_ids: List[str],
    ensembl_db_type: str = "Ensembl_Protein",  # Default, UniProt also lists "Ensembl_Genomes_Protein", "Ensembl_Genomes_Transcript"
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, Optional[List[str]]]:
    """
    Maps a list of Ensembl IDs (Protein or Transcript primarily) to UniProtKB Accession IDs.

    Args:
        ensembl_ids: A list of Ensembl ID strings.
        ensembl_db_type: The type of Ensembl ID. Common UniProt `from_db` values for Ensembl include:
                         "Ensembl_Protein", "Ensembl_Transcript", "Ensembl_Gene", "Ensembl".
                         Check UniProt's official list for all valid types: https://www.uniprot.org/help/id_mapping
                         Defaults to "Ensembl_Protein".
        session: Optional aiohttp.ClientSession to reuse. If None, a new one is created and managed by the helper.

    Returns:
        A dictionary where keys are input Ensembl IDs and values are lists of
        mapped UniProtKB ACs. Returns None as value for an ID if no mapping found or error.
    """
    # Validate ensembl_db_type against a broader but still common set.
    # For full validity, user should consult UniProt's current list.
    # Example valid types: "Ensembl_Protein", "Ensembl_Transcript", "EMBL-GenBank-DDBJ_CDS", "Ensembl_Gene"
    # For simplicity, we'll just pass it through, but a more robust implementation might validate more strictly.
    # logger.info(f"Mapping Ensembl IDs from type: {ensembl_db_type}")

    client = UniProtIDMappingClient(
        from_db=ensembl_db_type, to_db="ACC", session=session
    )
    primary_results: Dict[str, Optional[List[str]]] = {}
    try:
        results = await client.map_identifiers(identifiers=ensembl_ids)
        for input_id, result_tuple in results.items():
            primary_ids, _ = result_tuple
            primary_results[input_id] = primary_ids
    except Exception as e:
        logger.error(f"Error in map_ensembl_ids_to_uniprot_acs: {e}", exc_info=True)
        for ens_id in ensembl_ids:
            if ens_id not in primary_results:
                primary_results[ens_id] = None
    finally:
        if client._session_managed_internally:
            await client.close_session()
    return primary_results
