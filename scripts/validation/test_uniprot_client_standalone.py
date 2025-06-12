# Full content for test_uniprot_client_standalone.py
import asyncio
import logging
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging to see client output
logging.basicConfig(level=logging.INFO)
logging.getLogger("biomapper").setLevel(logging.DEBUG) # Set to DEBUG for more verbose client output
logging.getLogger("aiohttp").setLevel(logging.WARNING) # Tone down aiohttp's verbosity

async def main():
    print("--- Initializing UniProtHistoricalResolverClient (Re-Verification) ---")
    client = UniProtHistoricalResolverClient()
    test_cases = {
        "single_primary": ["P12345"], # e.g. Calmodulin
        "single_secondary_to_primary": ["Q9Y260"], # e.g. B4DHW0 secondary for P12345 (example, actual might differ)
        "composite_comma_both_primary": ["P58401,Q9P2S2"], # e.g. two distinct primary IDs
        "composite_underscore_both_primary": ["Q14213_Q8NEV9"], # e.g. two distinct primary IDs
        "composite_mixed_separators": ["P0DTC2,P69905_P01308"], # e.g. COVID Spike, Human Hemoglobin, Human Insulin
        "whitespace_padding_single": [" P01308 "],
        "whitespace_padding_composite": ["P58401 , Q9P2S2 _ P69905"],
        "duplicates_in_composite": ["P12345,P12345_Q9Y260,P12345"],
        "mixed_valid_and_composite": ["P0DTC2", "P58401,Q9P2S2", "Q14213_Q8NEV9"],
        "obsolete_id_known": ["P00000"], # Example of a likely obsolete ID
        "demerged_id_example": ["P29400"], # (CALM1_HUMAN, CALM2_HUMAN, CALM3_HUMAN before demerge) - maps to P62158, P0DP23, P0DP24
        "invalid_format_general": ["INVALID-FORMAT", "12345"],
        "empty_and_delimiter_only_strings": ["", ",", "_", "_, ,", "  "],
        "complex_composite_with_secondary_and_obsolete": ["Q9Y260,P00000_P12345"] # Secondary, Obsolete, Primary
    }
    for name, ids_to_test in test_cases.items():
        print(f"\n--- Running Test Case: {name} ---")
        print(f"Input IDs: {ids_to_test}")
        try:
            # Bypass cache to ensure fresh resolution for verification
            results = await client.map_identifiers(ids_to_test, config={'bypass_cache': True})
            print("Results:")
            if results:
                for original_id, result_tuple in results.items():
                    print(f"  '{original_id}': {result_tuple}")
            else:
                print("  No results returned.")
        except Exception as e:
            print(f"An error occurred during test case '{name}': {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())