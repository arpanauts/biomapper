from typing import List, Dict, Optional
import asyncio
import httpx
import logging
from biomapper.schemas.mvp0_schema import PubChemAnnotation

# Configure logging
logger = logging.getLogger(__name__)

# Attributes to fetch from PubChem (as per design.md and mvp0_schema.py)
# Example: title (Preferred Term), iupac_name, molecular_formula, canonical_smiles,
#          inchi_key, description, synonyms, parent_cid (from CanonicalizedCompound).
PUBCHEM_ATTRIBUTES_TO_FETCH = [
    "Title", "IUPACName", "MolecularFormula", "CanonicalSMILES",
    "InChIKey", "Description", "Synonym", # Note: Synonym might return a list
    # For Parent CID, might need to inspect Compound object from PubChemPy or specific PUG REST endpoint
]

# PubChem API configuration
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
RATE_LIMIT_SEMAPHORE = asyncio.Semaphore(5)  # 5 requests per second
BATCH_SIZE = 10  # Process CIDs in batches of 10


async def fetch_single_cid_annotation(client: httpx.AsyncClient, cid: int) -> Optional[PubChemAnnotation]:
    """
    Fetches annotation for a single CID from PubChem.
    
    Args:
        client: The httpx AsyncClient to use for requests.
        cid: The PubChem Compound ID to fetch.
        
    Returns:
        PubChemAnnotation object if successful, None if error.
    """
    async with RATE_LIMIT_SEMAPHORE:
        try:
            # Fetch compound properties in JSON format
            property_list = "Title,IUPACName,MolecularFormula,CanonicalSMILES,InChIKey"
            url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/{property_list}/JSON"
            
            logger.debug(f"Fetching properties for CID {cid}")
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            properties = data.get("PropertyTable", {}).get("Properties", [{}])[0]
            
            # Fetch synonyms separately (they're not in the property endpoint)
            synonyms_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/synonyms/JSON"
            synonyms_response = await client.get(synonyms_url, timeout=10.0)
            synonyms_data = []
            if synonyms_response.status_code == 200:
                synonyms_json = synonyms_response.json()
                synonyms_data = synonyms_json.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])[:10]  # Limit to 10
            
            # Fetch description separately
            description_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/description/JSON"
            description_response = await client.get(description_url, timeout=10.0)
            description_text = None
            if description_response.status_code == 200:
                desc_json = description_response.json()
                descriptions = desc_json.get("InformationList", {}).get("Information", [])
                # Get the first available description
                for desc in descriptions:
                    if desc.get("Description"):
                        description_text = desc["Description"]
                        break
            
            # Create PubChemAnnotation object
            annotation = PubChemAnnotation(
                cid=cid,
                title=properties.get("Title"),
                iupac_name=properties.get("IUPACName"),
                molecular_formula=properties.get("MolecularFormula"),
                canonical_smiles=properties.get("CanonicalSMILES"),
                inchi_key=properties.get("InChIKey"),
                description=description_text,
                synonyms=synonyms_data,
                parent_cid=None  # Parent CID would require additional API call to canonicalized compound
            )
            
            logger.info(f"Successfully fetched annotations for CID {cid}")
            return annotation
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"CID {cid} not found in PubChem")
            else:
                logger.error(f"HTTP error fetching CID {cid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching annotations for CID {cid}: {type(e).__name__}: {e}")
            return None


async def fetch_pubchem_annotations(cids: List[int]) -> Dict[int, PubChemAnnotation]:
    """
    Fetches detailed annotations for a list of PubChem CIDs.

    Args:
        cids: A list of PubChem Compound IDs.

    Returns:
        A dictionary mapping each CID to its PubChemAnnotation object.
        If a CID cannot be found or an error occurs for it, it is omitted from results.
    """
    if not cids:
        logger.warning("No CIDs provided for annotation")
        return {}
    
    logger.info(f"Starting annotation fetch for {len(cids)} CIDs")
    annotations_map: Dict[int, PubChemAnnotation] = {}
    
    # Use httpx async client with connection pooling
    async with httpx.AsyncClient() as client:
        # Process CIDs in batches to manage concurrent requests
        for i in range(0, len(cids), BATCH_SIZE):
            batch = cids[i:i + BATCH_SIZE]
            logger.debug(f"Processing batch {i//BATCH_SIZE + 1}: CIDs {batch}")
            
            # Create tasks for concurrent requests
            tasks = [fetch_single_cid_annotation(client, cid) for cid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for cid, result in zip(batch, results):
                if isinstance(result, PubChemAnnotation):
                    annotations_map[cid] = result
                elif isinstance(result, Exception):
                    logger.error(f"Exception while fetching CID {cid}: {result}")
                # If result is None, it means the CID was not found or another error occurred
                # (already logged in fetch_single_cid_annotation)
            
            # Add a small delay between batches to avoid overwhelming the API
            if i + BATCH_SIZE < len(cids):
                await asyncio.sleep(0.2)
    
    logger.info(f"Successfully annotated {len(annotations_map)} out of {len(cids)} CIDs")
    return annotations_map


# Example usage (for testing this component independently)
async def main():
    """Example usage demonstrating the PubChem annotation fetcher."""
    # Configure logging for the example
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test CIDs including known compounds and a non-existent one
    cids_to_annotate = [
        5793,       # Glucose
        107526,     # beta-D-Glucopyranose
        2244,       # Aspirin
        5280343,    # Quercetin
        999999999   # Non-existent CID for error handling test
    ]
    
    print(f"Fetching annotations for {len(cids_to_annotate)} CIDs...")
    print(f"CIDs: {cids_to_annotate}\n")
    
    # Fetch annotations
    annotations = await fetch_pubchem_annotations(cids_to_annotate)
    
    # Display results
    print(f"\nSuccessfully annotated {len(annotations)} out of {len(cids_to_annotate)} CIDs\n")
    
    for cid in cids_to_annotate:
        if cid in annotations:
            annotation = annotations[cid]
            print(f"CID {cid}:")
            print(f"  Title: {annotation.title or 'N/A'}")
            print(f"  IUPAC Name: {annotation.iupac_name or 'N/A'}")
            print(f"  Molecular Formula: {annotation.molecular_formula or 'N/A'}")
            print(f"  SMILES: {annotation.canonical_smiles or 'N/A'}")
            print(f"  InChIKey: {annotation.inchi_key or 'N/A'}")
            if annotation.synonyms:
                print(f"  Synonyms (first 3): {', '.join(annotation.synonyms[:3])}")
            else:
                print(f"  Synonyms: N/A")
            if annotation.description:
                print(f"  Description: {annotation.description[:100]}...")
            else:
                print(f"  Description: N/A")
            print()
        else:
            print(f"CID {cid}: Failed to fetch annotations (see logs for details)\n")


if __name__ == "__main__":
    asyncio.run(main())
