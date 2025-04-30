# /home/ubuntu/biomapper/biomapper/mapping/resources/clients/unichem_client.py
import logging
from typing import Optional, Tuple, Dict

import aiohttp

logger = logging.getLogger()  # Use root logger to inherit basicConfig

# UniChem REST API base URL
UNICHEM_BASE_URL = "https://www.ebi.ac.uk/unichem"

# Mapping from Biomapper ontology names to UniChem source IDs
# See: https://www.ebi.ac.uk/unichem/rest/src_ids
# TODO: Expand this mapping as needed based on resources in metamapper.db
ONTOLOGY_TO_UNICHEM_SRC_ID: Dict[str, int] = {
    "chebi": 1,
    "drugbank": 2,
    "pdb": 3,  # Protein Data Bank
    "gtopdb": 4,  # IUPHAR/BPS Guide to PHARMACOLOGY
    "hmdb": 5,
    "pubchem": 21,  # Changed from 22 to 21 - Testing if this is for CIDs
    "pubchem_cid": 21,  # Changed from 22 to 21 - Testing if this is for CIDs
    "chembl": 6,
    "zinc": 7,
    "emolecules": 8,
    "ibm": 9,  # IBM Patent Data
    "atlas": 10,  # FDA NMEs & BLA Drug Approval Mappings
    "kegg": 21,  # KEGG Compound
    # Add more mappings: KEGG_DRUG, KEGG_GLYCAN, etc. if needed
    # Example: 'kegg_drug': 41,
    # Need to verify exact source IDs from UniChem documentation/API
}

# TODO: Define mapping for Biomapper ontology -> UniChem prefix (if any)
# E.g., some sources might need specific prefixes in UniChem queries
ONTOLOGY_PREFIX: Dict[str, str] = {
    "hmdb": "HMDB",  # UniChem often expects IDs without the prefix for query
    # Add others if necessary
}


async def map_with_unichem(
    input_entity: str,
    input_ontology: str,
    target_ontology: str,
    session: aiohttp.ClientSession,  # Pass session for connection pooling
) -> Tuple[Optional[str], float]:
    """
    Maps an entity from a source ontology to a target ontology using the UniChem API.
    Handles both direct source ID mapping and InChIKey connectivity search.

    Args:
        input_entity: The identifier of the entity to map.
        input_ontology: The ontology type of the input entity (e.g., 'hmdb', 'chebi', 'inchikey').
        target_ontology: The desired ontology type for the output (e.g., 'pubchem', 'chebi').
        session: An aiohttp.ClientSession for making requests.

    Returns:
        A tuple containing the mapped entity identifier (or None if not found/error)
        and a confidence score (1.0 for success, 0.0 for failure).
    """
    input_ontology_lower = input_ontology.lower()
    target_ontology_lower = target_ontology.lower()

    # --- InChIKey Connectivity Search Logic ---
    if input_ontology_lower == "inchikey":
        # Correct endpoint uses /api/ not /rest/
        request_url = (
            "https://www.ebi.ac.uk/unichem/api/v1/connectivity"  # Changed base path
        )
        payload = {"type": "inchikey", "compound": input_entity}
        logger.debug(
            f"UniChem Client: Requesting Connectivity URL: {request_url} with payload: {payload}"
        )
        try:
            async with session.post(
                request_url, json=payload, headers={"Accept": "application/json"}
            ) as response:
                response.raise_for_status()
                results = (
                    await response.json()
                )  # Response is expected to be a list of compound objects
                logger.debug(
                    f"UniChem Client (Connectivity): Raw API response: {results}"
                )  # Log raw response

                compound_data = None
                # Check if the response is a list as expected
                if isinstance(results, list):
                    if not results:
                        logger.warning(
                            f"UniChem Client (Connectivity): Empty list returned for InChIKey {input_entity}"
                        )
                        return None, 0.0
                    try:
                        # Assume the first element is the match for the full InChIKey
                        compound_data = results[0]
                    except IndexError:
                        logger.warning(
                            f"UniChem Client (Connectivity): Results list was unexpectedly empty after check? InChIKey {input_entity}"
                        )
                        return None, 0.0
                elif isinstance(results, dict):
                    # If it's a dictionary, extract data from 'searchedCompound'
                    logger.debug(
                        f"UniChem Client (Connectivity): API returned a dictionary. Attempting to extract from 'searchedCompound' key."
                    )
                    compound_data = results.get("searchedCompound")
                    if not isinstance(compound_data, dict):
                        logger.error(
                            f"UniChem Client (Connectivity): 'searchedCompound' key missing or not a dict in response. Keys: {results.keys()}"
                        )
                        return None, 0.0
                else:
                    logger.error(
                        f"UniChem Client (Connectivity): Unexpected API response type: {type(results)}. Response: {results}"
                    )
                    return None, 0.0

                if not compound_data:
                    logger.error(
                        f"UniChem Client (Connectivity): Failed to extract compound data from response. Response: {results}"
                    )
                    return None, 0.0

                # --- Now parse compound_data (which should be a dictionary) ---
                if compound_data.get("standardInchiKey") != input_entity:
                    logger.warning(
                        f"UniChem Client (Connectivity): Result InChIKey '{compound_data.get('standardInchiKey')}' doesn't match input '{input_entity}'. Check response details."
                    )
                    # Decide if mismatch is critical. For now, proceed assuming it's the right compound group.

                # Get the list of sources from the TOP-LEVEL results dict
                sources = results.get("sources", [])
                if not sources:
                    logger.warning(
                        f"UniChem Client (Connectivity): No sources found for InChIKey {input_entity} in top-level response: {results}"
                    )
                    return None, 0.0

                # Find the target ontology within the sources list
                for source in sources:
                    if source.get("name", "").lower() == target_ontology_lower:
                        mapped_entity = source.get("src_compound_id")
                        if mapped_entity:
                            logger.info(
                                f"UniChem Client (Connectivity): Mapped {input_ontology}:{input_entity} -> {target_ontology}:{mapped_entity}"
                            )
                            return mapped_entity, 1.0
                        else:
                            logger.warning(
                                f"UniChem Client (Connectivity): Found target source '{target_ontology_lower}', but 'src_compound_id' key missing. Source data: {source}"
                            )
                            return None, 0.0  # Indicate failure if ID is missing

                # If loop completes without finding the target ontology
                logger.warning(
                    f"UniChem Client (Connectivity): Target ontology '{target_ontology_lower}' not found in sources for InChIKey {input_entity}. Available sources: {[s.get('name') for s in sources]}"
                )
                return None, 0.0

        except aiohttp.ClientResponseError as e:
            # Handle specific errors for POST request
            if e.status == 404:
                logger.warning(
                    f"UniChem Client (Connectivity): 404 Not Found for InChIKey {input_entity} at URL {request_url}. Endpoint correct?"
                )
            elif e.status == 400:
                logger.error(
                    f"UniChem Client (Connectivity): 400 Bad Request for URL {request_url}. Check payload: {payload}"
                )
            elif e.status == 422:  # Unprocessable Entity - likely bad InChIKey format
                logger.error(
                    f"UniChem Client (Connectivity): 422 Unprocessable Entity for URL {request_url}. Invalid InChIKey format? Input: {input_entity}"
                )
            else:
                logger.error(
                    f"UniChem Client (Connectivity): HTTP error {e.status} for URL {request_url}: {e.message}"
                )
            return None, 0.0
        except aiohttp.ClientError as e:
            logger.error(
                f"UniChem Client (Connectivity): Connection or other client error for URL {request_url}: {e}"
            )
            return None, 0.0
        except Exception as e:
            logger.exception(
                f"UniChem Client (Connectivity): An unexpected error occurred during mapping for {input_ontology}:{input_entity} -> {target_ontology}"
            )
            return None, 0.0

    # --- Original Direct Source ID Mapping Logic (for non-InChIKey inputs) ---
    else:
        source_id = ONTOLOGY_TO_UNICHEM_SRC_ID.get(input_ontology_lower)
        target_id = ONTOLOGY_TO_UNICHEM_SRC_ID.get(target_ontology_lower)

        if not source_id:
            logger.error(
                f"UniChem Client (Direct): Unknown source ontology '{input_ontology}'"
            )
            return None, 0.0
        if not target_id:
            logger.error(
                f"UniChem Client (Direct): Unknown target ontology '{target_ontology}'"
            )
            return None, 0.0

        # Handle known prefixes that UniChem might not expect in the query URL path
        formatted_input_entity = input_entity
        input_prefix = ONTOLOGY_PREFIX.get(input_ontology_lower)
        if input_prefix and input_entity.upper().startswith(input_prefix):
            formatted_input_entity = input_entity[len(input_prefix) :]
            logger.debug(
                f"UniChem Client (Direct): Removed prefix '{input_prefix}' from '{input_entity}', using '{formatted_input_entity}'"
            )

        request_url = f"{UNICHEM_BASE_URL}/rest/src_compound_id/{formatted_input_entity}/{source_id}/{target_id}"
        logger.debug(f"UniChem Client (Direct): Requesting URL: {request_url}")

        try:
            async with session.get(
                request_url, headers={"Accept": "application/json"}
            ) as response:
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                results = await response.json()

                if not results:
                    logger.warning(
                        f"UniChem Client (Direct): No mapping found for {input_ontology}:{input_entity} -> {target_ontology}"
                    )
                    return None, 0.0

                mapped_entity = results[0].get("src_compound_id")

                if mapped_entity:
                    logger.info(
                        f"UniChem Client (Direct): Mapped {input_ontology}:{input_entity} -> {target_ontology}:{mapped_entity}"
                    )
                    return mapped_entity, 1.0
                else:
                    logger.warning(
                        f"UniChem Client (Direct): Found mapping result, but 'src_compound_id' key missing. Response: {results[0]}"
                    )
                    return None, 0.0

        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.warning(
                    f"UniChem Client (Direct): 404 Not Found for {input_ontology}:{input_entity} -> {target_ontology} at URL {request_url}"
                )
            elif e.status == 400:
                logger.error(
                    f"UniChem Client (Direct): 400 Bad Request for URL {request_url}. Check input format/IDs. Input: {input_entity}"
                )
            else:
                logger.error(
                    f"UniChem Client (Direct): HTTP error {e.status} for URL {request_url}: {e.message}"
                )
            return None, 0.0
        except aiohttp.ClientError as e:
            logger.error(
                f"UniChem Client (Direct): Connection or other client error for URL {request_url}: {e}"
            )
            return None, 0.0
        except Exception as e:
            logger.exception(
                f"UniChem Client (Direct): An unexpected error occurred during mapping for {input_ontology}:{input_entity} -> {target_ontology}"
            )
            return None, 0.0
