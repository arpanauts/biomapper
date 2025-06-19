"""Tests for the enhanced UniProtNameClient with composite gene symbol handling."""

import asyncio
import logging
import pytest

from biomapper.mapping.clients.uniprot_name_client import UniProtNameClient

# Sample composite gene identifiers from the unmapped entries
COMPOSITE_GENES = [
    "MICB_MICA",
    "BOLA2_BOLA2B",
    "DEFB4A_DEFB4B",
    "DEFB104A_DEFB104B",
    "SPACA5_SPACA5B",
    "AMY1A_AMY1B_AMY1C",
    "FUT3_FUT5",
    "DEFA1_DEFA1B",
    "IL12A_IL12B",
    "EBI3_IL27",
]

# Regular gene symbols known to map successfully
REGULAR_GENES = [
    "TP53",  # P04637
    "BRCA1",  # P38398
    "EGFR",  # P00533
    "KRAS",  # P01116
    "CTNNB1",  # P35222
]

# Handle special case that might not be a gene symbol
SPECIAL_CASES = [
    "NTproBNP"  # Peptide/clinical marker, not a standard gene symbol
]

# Configure logging
logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_composite_gene_symbols():
    """Test the mapping of composite gene symbols."""
    client = UniProtNameClient()

    # Test composite gene identifiers
    result_dict = await client.map_identifiers(COMPOSITE_GENES)
    results = result_dict['input_to_primary']

    # Log results for analysis
    print("\n--- Composite Gene Symbol Mapping Results ---")
    for gene, uniprot_id in results.items():
        print(f"{gene}: {uniprot_id or 'No mapping'}")

    # Check if any mappings were found (we expect some to work now)
    mapped_count = sum(1 for v in results.values() if v is not None)
    print(
        f"Successfully mapped {mapped_count}/{len(COMPOSITE_GENES)} composite gene symbols"
    )

    # We should have at least some successful mappings
    assert (
        mapped_count > 0
    ), "Expected at least some composite gene symbols to map successfully"


@pytest.mark.asyncio
async def test_regular_gene_symbols():
    """Test the mapping of regular gene symbols to ensure they still work."""
    client = UniProtNameClient()

    # Test regular gene symbols
    result_dict = await client.map_identifiers(REGULAR_GENES)
    results = result_dict['input_to_primary']

    # Log results for verification
    print("\n--- Regular Gene Symbol Mapping Results ---")
    for gene, uniprot_id in results.items():
        print(f"{gene}: {uniprot_id or 'No mapping'}")

    # All regular gene symbols should map successfully
    assert all(results.values()), "All regular gene symbols should map successfully"


@pytest.mark.asyncio
async def test_special_cases():
    """Test the handling of special cases."""
    client = UniProtNameClient()

    # Test special cases
    result_dict = await client.map_identifiers(SPECIAL_CASES)
    results = result_dict['input_to_primary']

    # Log results for analysis
    print("\n--- Special Cases Mapping Results ---")
    for term, uniprot_id in results.items():
        print(f"{term}: {uniprot_id or 'No mapping'}")


if __name__ == "__main__":
    asyncio.run(test_composite_gene_symbols())
    asyncio.run(test_regular_gene_symbols())
    asyncio.run(test_special_cases())
