#!/usr/bin/env python3
"""
Quick test to verify chemistry actions are properly registered and working.
"""

import asyncio
import pandas as pd
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
from biomapper.core.strategy_actions.entities.chemistry.identification.extract_loinc import (
    ChemistryExtractLoincAction,
)
from biomapper.core.strategy_actions.entities.chemistry.matching.fuzzy_test_match import (
    ChemistryFuzzyTestMatchAction,
    ChemistryFuzzyTestMatchParams,
)
from biomapper.core.strategy_actions.entities.chemistry.harmonization.vendor_harmonization import (
    ChemistryVendorHarmonizationAction,
)
from biomapper.core.strategy_actions.chemistry_to_phenotype_bridge import (
    ChemistryToPhenotypeBridgeAction,
    ChemistryToPhenotypeBridgeParams,
)


async def test_chemistry_actions():
    """Test that all chemistry actions are registered and can execute."""

    # Test 1: Check that all chemistry actions are registered
    print("=" * 60)
    print("Testing Chemistry Action Registration")
    print("=" * 60)

    expected_actions = [
        "CHEMISTRY_EXTRACT_LOINC",
        "CHEMISTRY_FUZZY_TEST_MATCH",
        "CHEMISTRY_VENDOR_HARMONIZATION",
        "CHEMISTRY_TO_PHENOTYPE_BRIDGE",
    ]

    for action_name in expected_actions:
        if action_name in ACTION_REGISTRY:
            print(f"✅ {action_name} is registered")
        else:
            print(f"❌ {action_name} is NOT registered")

    # Test 2: Test CHEMISTRY_EXTRACT_LOINC
    print("\n" + "=" * 60)
    print("Testing CHEMISTRY_EXTRACT_LOINC")
    print("=" * 60)

    # Create test data
    test_data = pd.DataFrame(
        [
            {"test_name": "Glucose", "value": 95, "unit": "mg/dL"},
            {"test_name": "HbA1c", "value": 5.6, "unit": "%"},
            {"test_name": "Cholesterol Total", "value": 180, "unit": "mg/dL"},
            {"test_name": "HDL Cholesterol", "value": 55, "unit": "mg/dL"},
            {
                "test_name": "Creatinine",
                "value": 0.9,
                "unit": "mg/dL",
                "loinc": "2160-0",
            },
        ]
    )

    context = {"datasets": {"chemistry_data": test_data}}

    # Test LOINC extraction
    action = ChemistryExtractLoincAction()
    params = {
        "input_key": "chemistry_data",
        "output_key": "loinc_extracted",
        "test_name_column": "test_name",
        "loinc_column": "loinc",
        "validate_format": True,
        "extract_from_name": True,
    }

    try:
        result = await action.execute(params, context)
        print(f"Success: {result.success}")
        print(f"Total rows: {result.total_rows}")
        print(f"Rows with LOINC: {result.rows_with_loinc}")
        print(f"Valid LOINC codes: {result.valid_loinc_codes}")

        # Check extracted data
        if "loinc_extracted" in context["datasets"]:
            extracted_df = context["datasets"]["loinc_extracted"]
            print("\nExtracted LOINC codes:")
            for _, row in extracted_df.iterrows():
                if pd.notna(row.get("extracted_loinc")):
                    print(
                        f"  {row['test_name']}: {row['extracted_loinc']} "
                        f"(source: {row.get('loinc_extraction_source', 'unknown')})"
                    )
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Test CHEMISTRY_FUZZY_TEST_MATCH
    print("\n" + "=" * 60)
    print("Testing CHEMISTRY_FUZZY_TEST_MATCH")
    print("=" * 60)

    source_data = pd.DataFrame(
        [
            {"test_name": "Glu", "value": 100},
            {"test_name": "Chol", "value": 200},
            {"test_name": "HbA1c", "value": 6.0},
        ]
    )

    target_data = pd.DataFrame(
        [
            {"test_name": "Glucose", "loinc": "2345-7"},
            {"test_name": "Cholesterol Total", "loinc": "2093-3"},
            {"test_name": "Hemoglobin A1c", "loinc": "4548-4"},
        ]
    )

    context = {"datasets": {"source": source_data, "target": target_data}}

    action = ChemistryFuzzyTestMatchAction()
    params = ChemistryFuzzyTestMatchParams(
        source_key="source",
        target_key="target",
        output_key="matched",
        source_test_column="test_name",
        target_test_column="test_name",
        match_threshold=0.7,
        use_synonyms=True,
        use_abbreviations=True,
    )

    try:
        result = await action.execute_typed(params, context)
        print(f"Success: {result.success}")
        if result.data:
            print(f"Matches found: {result.data.get('total_matches', 0)}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Test CHEMISTRY_VENDOR_HARMONIZATION
    print("\n" + "=" * 60)
    print("Testing CHEMISTRY_VENDOR_HARMONIZATION")
    print("=" * 60)

    vendor_data = pd.DataFrame(
        [
            {
                "test_name": "Glucose, Serum",
                "value": "95",
                "unit": "mg/dL",
                "vendor": "labcorp",
            },
            {
                "test_name": "Blood Sugar",
                "value": "5.3",
                "unit": "mmol/L",
                "vendor": "quest",
            },
            {"test_name": "GLU", "value": "100", "unit": "mg/dL", "vendor": "mayo"},
        ]
    )

    context = {"datasets": {"vendor_data": vendor_data}}

    action = ChemistryVendorHarmonizationAction()
    params = {
        "input_key": "vendor_data",
        "output_key": "harmonized",
        "test_name_column": "test_name",
        "value_column": "value",
        "unit_column": "unit",
        "vendor_column": "vendor",
        "standardize_test_names": True,
        "standardize_units": True,
    }

    try:
        result = await action.execute(params, context)
        print(
            f"Success: {result['success'] if isinstance(result, dict) else result.success}"
        )

        if "harmonized" in context["datasets"]:
            harmonized_df = context["datasets"]["harmonized"]
            print(f"\nHarmonized data ({len(harmonized_df)} rows):")
            for _, row in harmonized_df.head(3).iterrows():
                print(
                    f"  {row.get('standardized_test_name', row['test_name'])}: "
                    f"{row['value']} {row.get('standardized_unit', row['unit'])}"
                )
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 5: Test CHEMISTRY_TO_PHENOTYPE_BRIDGE
    print("\n" + "=" * 60)
    print("Testing CHEMISTRY_TO_PHENOTYPE_BRIDGE")
    print("=" * 60)

    chemistry_data = pd.DataFrame(
        [
            {"test_name": "Glucose", "loinc": "2345-7", "value": 200, "unit": "mg/dL"},
            {"test_name": "HbA1c", "loinc": "4548-4", "value": 8.5, "unit": "%"},
            {
                "test_name": "Cholesterol",
                "loinc": "2093-3",
                "value": 250,
                "unit": "mg/dL",
            },
        ]
    )

    context = {"datasets": {"chemistry": chemistry_data}}

    action = ChemistryToPhenotypeBridgeAction()
    # Need both source and target for phenotype bridge
    phenotype_data = pd.DataFrame([
        {"id": "HP:0003074", "name": "Hyperglycemia", "xrefs": "HP:0003074"},
        {"id": "HP:0003124", "name": "Hypercholesterolemia", "xrefs": "HP:0003124"},
    ])
    
    context["datasets"]["phenotypes"] = phenotype_data
    
    params = ChemistryToPhenotypeBridgeParams(
        source_key="chemistry",
        target_key="phenotypes",
        output_key="mapped_phenotypes",
        loinc_column="loinc"
    )

    try:
        result = await action.execute_typed(params, context)
        print(f"Success: {result.success}")
        if result.data:
            print(f"Phenotypes identified: {result.data.get('phenotypes_count', 0)}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Chemistry Actions Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chemistry_actions())
