#!/usr/bin/env python

import asyncio
import logging
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.exceptions import NoPathFoundError

# Set up logging
logging.basicConfig(level=logging.INFO)


async def main():
    print("\nTesting the fix for UnboundLocalError in MappingExecutor.execute_mapping")
    print("==================================================================")

    # Create mapping executor
    executor = MappingExecutor()

    # Mock the necessary methods to test our fix directly
    with patch.object(
        executor, "_get_ontology_type", new_callable=AsyncMock
    ) as mock_ontology:
        # Return test values for ontology types
        mock_ontology.return_value = "TEST_ONTOLOGY"

        # Mock _find_best_path to return None (no path found)
        with patch.object(
            executor, "_find_best_path", new_callable=AsyncMock
        ) as mock_find_path:
            mock_find_path.return_value = None

            # This is the key test - previously would fail with UnboundLocalError
            print("\nTest: Executing mapping with no path found...")
            # Execute with a non-existent path to trigger the error path
            try:
                result = await executor.execute_mapping(
                    # These values don't matter as we're mocking the ontology lookup
                    source_endpoint_name="test_source",
                    target_endpoint_name="test_target",
                    input_identifiers=["test1", "test2"],
                )

                # Check the result has the expected keys
                print("\nResult keys:", list(result.keys()))

                # Check if path_name is safely handled
                if "selected_path_name" in result:
                    print(
                        f"SUCCESS: 'selected_path_name' is in the result: {result['selected_path_name']}"
                    )
                else:
                    print("ERROR: 'selected_path_name' is missing from the result!")

                # Check status is properly set
                print(f"Status: {result.get('status', 'N/A')}")

                print("\nTEST PASSED! No UnboundLocalError was raised.")
                return 0  # Success exit code

            except UnboundLocalError as e:
                print(f"\nTEST FAILED! Got UnboundLocalError: {e}")
                return 1  # Failure exit code
            except Exception as e:
                print(f"\nTEST FAILED with {type(e).__name__}: {e}")
                return 1  # Failure exit code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
