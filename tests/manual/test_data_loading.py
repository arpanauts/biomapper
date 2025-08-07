#!/usr/bin/env python
"""
Test script to verify LOAD_DATASET_IDENTIFIERS action works correctly
with all 5 dataset formats, especially SPOKE and KG2C edge cases.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from biomapper.core.strategy_actions.load_dataset_identifiers import (
    LoadDatasetIdentifiersAction,
)
from biomapper.core.strategy_actions.load_dataset_identifiers import (
    LoadDatasetIdentifiersParams,
)


class MockContext:
    """Mock context that simulates StrategyExecutionContext for MVP actions."""

    def __init__(self):
        self._data = {"custom_action_data": {}}

    def set_action_data(self, key: str, value) -> None:
        if "custom_action_data" not in self._data:
            self._data["custom_action_data"] = {}
        self._data["custom_action_data"][key] = value

    def get_action_data(self, key: str, default=None):
        return self._data.get("custom_action_data", {}).get(key, default)

    @property
    def datasets(self):
        """Get datasets from custom action data."""
        return self._data.get("custom_action_data", {}).get("datasets", {})


async def test_dataset_loading():
    """Test loading all 5 dataset types to verify column handling."""

    # Test configurations for each dataset type
    test_configs = [
        {
            "name": "UKBB",
            "file_path": "data/test_data/ukbb_proteins.tsv",
            "identifier_column": "UniProt",
            "expected_pattern": "Standard UniProt IDs, may have composites",
        },
        {
            "name": "HPA",
            "file_path": "data/test_data/hpa_proteins.csv",
            "identifier_column": "uniprot",
            "expected_pattern": "Standard UniProt IDs, may have composites",
        },
        {
            "name": "QIN",
            "file_path": "data/test_data/qin_proteins.csv",
            "identifier_column": "uniprot",
            "expected_pattern": "Standard UniProt IDs, may have composites",
        },
        {
            "name": "Arivale",
            "file_path": "data/test_data/arivale_proteins.csv",
            "identifier_column": "uniprot",
            "expected_pattern": "Standard UniProt IDs, may have composites",
        },
        {
            "name": "SPOKE",
            "file_path": "data/test_data/spoke_proteins.csv",
            "identifier_column": "identifier",
            "expected_pattern": "Bare UniProt IDs like 'P00519'",
        },
        {
            "name": "KG2C",
            "file_path": "data/test_data/kg2c_proteins.csv",
            "identifier_column": "id",
            "strip_prefix": "UniProtKB:",
            "expected_pattern": "Prefixed IDs like 'UniProtKB:P68431' -> 'P68431'",
        },
    ]

    action = LoadDatasetIdentifiersAction()
    # Create a mock context for MVP actions
    context = MockContext()

    print("🧪 Testing LOAD_DATASET_IDENTIFIERS with all dataset types...\n")

    for config in test_configs:
        print(f"📊 Testing {config['name']} dataset:")
        print(f"   File: {config['file_path']}")
        print(f"   Column: {config['identifier_column']}")
        if "strip_prefix" in config:
            print(f"   Strip prefix: {config['strip_prefix']}")
        print(f"   Expected: {config['expected_pattern']}")

        # Create parameters
        params_dict = {
            "file_path": config["file_path"],
            "identifier_column": config["identifier_column"],
            "output_key": f"{config['name'].lower()}_test",
        }

        if "strip_prefix" in config:
            params_dict["strip_prefix"] = config["strip_prefix"]

        try:
            params = LoadDatasetIdentifiersParams(**params_dict)

            # Execute action
            result = await action.execute(params, context)

            # Check results
            output_key = params.output_key
            if output_key in context.datasets:
                table_data = context.datasets[output_key]
                df = table_data.to_dataframe()

                print(f"   ✅ Loaded {len(df)} rows")
                print(f"   📋 Columns: {list(df.columns)}")

                # Show sample identifiers
                if not df.empty:
                    identifier_col = params.identifier_column
                    sample_ids = df[identifier_col].head(3).tolist()
                    print(f"   🔍 Sample IDs: {sample_ids}")

                    # Check for original column if prefix was stripped
                    if hasattr(params, "strip_prefix") and params.strip_prefix:
                        original_col = f"{identifier_col}_original"
                        if original_col in df.columns:
                            original_samples = df[original_col].head(3).tolist()
                            print(f"   📝 Original IDs: {original_samples}")

                print(f"   ✅ {config['name']} loading successful!\n")

            else:
                print(f"   ❌ Output key '{output_key}' not found in context\n")

        except FileNotFoundError:
            print(f"   ⚠️  File not found: {config['file_path']}")
            print("   ℹ️  This is expected if test data doesn't exist yet\n")

        except Exception as e:
            print(f"   ❌ Error: {e}\n")

    print("🎯 Data loading test complete!")
    print("\nNext steps:")
    print("1. Verify SPOKE uses 'identifier' column correctly")
    print("2. Verify KG2C strips 'UniProtKB:' prefix and preserves original")
    print("3. Check composite ID handling (e.g., 'P12345_Q67890')")
    print("4. Proceed with MERGE_WITH_UNIPROT_RESOLUTION testing")


if __name__ == "__main__":
    asyncio.run(test_dataset_loading())
