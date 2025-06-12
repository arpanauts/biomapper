# Prompt: Verify UniProt Historical Resolver Client

## 1. Task Objective
Create and execute a standalone Python script to test the `UniProtHistoricalResolverClient`, verifying its ability to correctly handle a diverse set of UniProt ID formats (single, composite, invalid, etc.).

## 2. Expected Outputs
1.  **Test Script:** A Python script created at `/home/ubuntu/biomapper/scripts/validation/test_uniprot_client_standalone.py`.
2.  **Feedback File:** A single markdown file created at `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-11-214645-feedback-verify-uniprot-client.md`.

## 3. Task Decomposition
1.  **Create Test Script:** Create the file `/home/ubuntu/biomapper/scripts/validation/test_uniprot_client_standalone.py` with the exact Python code provided below.
2.  **Execute Test Script:** Run the command `python /home/ubuntu/biomapper/scripts/validation/test_uniprot_client_standalone.py`.
3.  **Generate Feedback:** Create the feedback file specified above. Populate it with the full source code of the test script and the full, unedited console output from its execution. Conclude the file with a structured outcome report as shown in the template below.

## 4. Test Script Source Code
```python
# Full content for test_uniprot_client_standalone.py
import asyncio
import logging
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging to see client output
logging.basicConfig(level=logging.INFO)
logging.getLogger("biomapper").setLevel(logging.INFO)

async def main():
    print("--- Initializing UniProtHistoricalResolverClient ---")
    client = UniProtHistoricalResolverClient()
    test_cases = {
        "single_primary": ["P12345"],
        "single_secondary": ["Q9Y260"],
        "composite_comma": ["P58401,Q9P2S2"],
        "composite_underscore": ["Q14213_Q8NEV9"],
        "composite_mixed": ["P12345,Q14213_Q8NEV9"],
        "whitespace_padding": [" P12345 ", "P58401 , Q9P2S2_P00001"],
        "duplicates_in_composite": ["P12345,P12345_Q9Y260"],
        "mixed_valid_and_composite": ["P0DTC2", "P58401,Q9P2S2", "Q14213_Q8NEV9"],
        "obsolete_id": ["P00000"],
        "invalid_format": ["INVALID-FORMAT"],
        "empty_and_delimiter_strings": ["", ",", "_", "_, ,"]
    }
    for name, ids in test_cases.items():
        print(f"\n--- Running Test Case: {name} ---")
        print(f"Input IDs: {ids}")
        try:
            results = await client.map_identifiers(ids, bypass_cache=True)
            print("Results:")
            for original_id, result in results.items():
                print(f"  '{original_id}': {result}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Feedback File Template
Please use the following template for the feedback file.

````markdown
# Feedback: UniProt Client Verification

## Test Script Code
```python
<PASTE FULL SOURCE CODE OF THE TEST SCRIPT HERE>
```

## Execution Output
```bash
<PASTE FULL CONSOLE OUTPUT FROM RUNNING THE SCRIPT HERE>
```

## Outcome Analysis

**Status:** (Choose one: `COMPLETE_SUCCESS`, `PARTIAL_SUCCESS`, `FAILED_NEEDS_ESCALATION`)

**Summary:**
<Provide a brief summary of the outcome. If successful, state that the client handled all test cases correctly. If failed, describe which test case failed and why.>
````

## 6. Source Prompt Reference
*   `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-11-214645-prompt-verify-uniprot-client.md`
