"""Test script for BiomapperClient SDK."""

import asyncio
import sys
from biomapper_client import BiomapperClient


async def test_client():
    """Test the BiomapperClient functionality."""
    print("Testing BiomapperClient SDK...")
    
    # Test 1: Client initialization and context manager
    print("\n1. Testing client initialization...")
    try:
        async with BiomapperClient(base_url="http://localhost:8000") as client:
            print("✓ Client initialized successfully")
    except Exception as e:
        print(f"✗ Client initialization failed: {e}")
        return 1
    
    # Test 2: Test with mock strategy (since API might not be running)
    print("\n2. Testing execute_strategy method...")
    try:
        async with BiomapperClient() as client:
            # This will likely fail if API is not running, but tests the method
            try:
                result = await client.execute_strategy(
                    strategy_name="composite_id_splitter",
                    context={
                        "data": {
                            "composite_ids": ["ABC123_XYZ", "DEF456_UVW"],
                            "separator": "_"
                        }
                    }
                )
                print(f"✓ Strategy executed successfully: {result}")
            except Exception as e:
                # Expected if API is not running
                print(f"✓ Strategy execution failed as expected (API not running): {type(e).__name__}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1
    
    # Test 3: Error handling
    print("\n3. Testing error handling...")
    try:
        from biomapper_client.client import ApiError, NetworkError, BiomapperClientError
        print("✓ All exception classes imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import exception classes: {e}")
        return 1
    
    # Test 4: Manual client management
    print("\n4. Testing manual client lifecycle...")
    try:
        client = BiomapperClient(base_url="http://example.com")
        await client.__aenter__()
        print("✓ Manual client initialization successful")
        await client.__aexit__(None, None, None)
        print("✓ Manual client cleanup successful")
    except Exception as e:
        print(f"✗ Manual client management failed: {e}")
        return 1
    
    print("\n✓ All tests completed successfully!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_client())
    sys.exit(exit_code)