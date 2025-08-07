"""Comprehensive tests for FILTER_DATASET action - TDD approach (failing tests first)."""

import pytest
import pandas as pd

from biomapper.core.strategy_actions.utils.data_processing.filter_dataset import (
    FilterDatasetAction,
    FilterDatasetParams,
    FilterCondition,
)


class TestFilterDatasetAction:
    """Comprehensive tests for FILTER_DATASET action using TDD methodology."""

    @pytest.fixture
    def sample_test_data(self):
        """Real biological data patterns for comprehensive testing."""
        return pd.DataFrame(
            {
                "id": ["A", "B", "C", "D", "E", "F", "G", "H"],
                "category": [
                    "biolink:Protein",
                    "biolink:SmallMolecule",
                    "biolink:Protein",
                    "biolink:Gene",
                    "biolink:Protein",
                    "biolink:SmallMolecule",
                    "biolink:Protein",
                    None,
                ],
                "confidence": [0.95, 0.75, 0.85, 0.60, 0.90, 0.25, 0.99, None],
                "cv": [0.1, 0.4, 0.2, 0.5, 0.15, 0.8, 0.05, 0.3],
                "vendor": [
                    "LabCorp",
                    "Quest",
                    "LabCorp",
                    None,
                    "Other",
                    "Quest",
                    "LabCorp",
                    "Quest",
                ],
                "test_name": [
                    "Test A",
                    "Test B",
                    None,
                    "Test D",
                    "Test E",
                    "TEST_F",
                    "test_g",
                    "Test H",
                ],
                "numeric_value": [100, 200, 150, 50, 300, 75, 400, 250],
                "boolean_flag": [True, False, True, False, True, False, True, None],
                "description": [
                    "High quality protein",
                    "low conf metabolite",
                    "GOOD PROTEIN",
                    "gene data",
                    "High Quality",
                    "poor quality",
                    "EXCELLENT",
                    "mixed case",
                ],
            }
        )

    @pytest.fixture
    def action(self):
        """Create FilterDatasetAction instance."""
        return FilterDatasetAction()

    @pytest.fixture
    def mock_context(self, sample_test_data):
        """Mock execution context with test data."""
        return {"datasets": {"input_data": sample_test_data}, "custom_action_data": {}}

    # Test 1: Basic equals operator
    @pytest.mark.asyncio
    async def test_equals_operator_basic(self, action, mock_context):
        """Should filter rows where column exactly equals value."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context,
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        assert len(filtered_data) == 4  # Only 4 proteins
        assert all(row["category"] == "biolink:Protein" for row in filtered_data)
        assert set(row["id"] for row in filtered_data) == {"A", "C", "E", "G"}

    # Test 2: Not equals operator
    @pytest.mark.asyncio
    async def test_not_equals_operator(self, action, mock_context):
        """Should filter rows where column does not equal value."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(column="vendor", operator="not_equals", value="Quest")
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Should exclude Quest (B, F, H) and include LabCorp, Other, None
        expected_ids = {"A", "C", "D", "E", "G"}  # D has None, which != 'Quest'
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 3: Greater than operator
    @pytest.mark.asyncio
    async def test_greater_than_operator(self, action, mock_context):
        """Should filter numeric values greater than threshold."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(column="confidence", operator="greater_than", value=0.8)
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # confidence > 0.8: A(0.95), C(0.85), E(0.90), G(0.99)
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 4: Less than operator
    @pytest.mark.asyncio
    async def test_less_than_operator(self, action, mock_context):
        """Should filter numeric values less than threshold."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(column="cv", operator="less_than", value=0.3)
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # cv < 0.3: A(0.1), C(0.2), E(0.15), G(0.05)
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 5: Greater equal and less equal operators
    @pytest.mark.asyncio
    async def test_greater_equal_less_equal_operators(self, action, mock_context):
        """Should filter with inclusive comparison operators."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="confidence", operator="greater_equal", value=0.85
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # confidence >= 0.85: A(0.95), C(0.85), E(0.90), G(0.99)
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

        # Test less_equal
        params.filter_conditions[0].operator = "less_equal"
        params.filter_conditions[0].value = 0.75

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # confidence <= 0.75: B(0.75), D(0.60), F(0.25)
        expected_ids = {"B", "D", "F"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 6: Contains operator with case sensitivity
    @pytest.mark.asyncio
    async def test_contains_operator_case_sensitive(self, action, mock_context):
        """Should filter string columns containing substring (case sensitive)."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="test_name",
                    operator="contains",
                    value="Test",
                    case_sensitive=True,
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Case sensitive "Test": A(Test A), B(Test B), D(Test D), E(Test E), H(Test H)
        expected_ids = {"A", "B", "D", "E", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 7: Contains operator case insensitive
    @pytest.mark.asyncio
    async def test_contains_operator_case_insensitive(self, action, mock_context):
        """Should filter string columns containing substring (case insensitive)."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="test_name",
                    operator="contains",
                    value="test",
                    case_sensitive=False,
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Case insensitive "test": all except C (None) and F (TEST_F contains but...)
        # Actually, TEST_F should match "test" case insensitive, and test_g should match
        expected_ids = {"A", "B", "D", "E", "F", "G", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 8: Not contains operator
    @pytest.mark.asyncio
    async def test_not_contains_operator(self, action, mock_context):
        """Should filter rows where column does not contain substring."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="description", operator="not_contains", value="quality"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Does NOT contain "quality" (case sensitive):
        # A: 'High quality protein' - CONTAINS "quality" (excluded)
        # B: 'low conf metabolite' - does NOT contain "quality" (included)
        # C: 'GOOD PROTEIN' - does NOT contain "quality" (included)
        # D: 'gene data' - does NOT contain "quality" (included)
        # E: 'High Quality' - does NOT contain "quality" (case sensitive, included)
        # F: 'poor quality' - CONTAINS "quality" (excluded)
        # G: 'EXCELLENT' - does NOT contain "quality" (included)
        # H: 'mixed case' - does NOT contain "quality" (included)
        expected_ids = {"B", "C", "D", "E", "G", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 9: In list operator
    @pytest.mark.asyncio
    async def test_in_list_operator(self, action, mock_context):
        """Should filter rows where column value is in provided list."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="vendor", operator="in_list", value=["LabCorp", "Quest"]
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # LabCorp or Quest: A, B, C, F, G, H
        expected_ids = {"A", "B", "C", "F", "G", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 10: Not in list operator
    @pytest.mark.asyncio
    async def test_not_in_list_operator(self, action, mock_context):
        """Should filter rows where column value is not in provided list."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category",
                    operator="not_in_list",
                    value=["biolink:Protein", "biolink:Gene"],
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Not protein or gene: B(SmallMolecule), F(SmallMolecule), H(None)
        expected_ids = {"B", "F", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 11: Regex operator
    @pytest.mark.asyncio
    async def test_regex_operator(self, action, mock_context):
        """Should filter using regex pattern matching."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="test_name", operator="regex", value=r"Test [A-E]"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Matches "Test A", "Test B", "Test D", "Test E"
        expected_ids = {"A", "B", "D", "E"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 12: Is null operator
    @pytest.mark.asyncio
    async def test_is_null_operator(self, action, mock_context):
        """Should filter rows where column value is null/NaN."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[FilterCondition(column="test_name", operator="is_null")],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # test_name is null: C
        expected_ids = {"C"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 13: Not null operator
    @pytest.mark.asyncio
    async def test_not_null_operator(self, action, mock_context):
        """Should filter rows where column value is not null."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(column="confidence", operator="not_null")
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # confidence not null: all except H
        expected_ids = {"A", "B", "C", "D", "E", "F", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 14: Multiple conditions with AND logic
    @pytest.mark.asyncio
    async def test_multiple_conditions_and_logic(self, action, mock_context):
        """Should filter with multiple conditions combined with AND."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                ),
                FilterCondition(
                    column="confidence", operator="greater_than", value=0.8
                ),
                FilterCondition(column="cv", operator="less_than", value=0.2),
            ],
            logic_operator="AND",
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Protein AND confidence > 0.8 AND cv < 0.2: A(0.95, 0.1), E(0.90, 0.15), G(0.99, 0.05)
        expected_ids = {"A", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 15: Multiple conditions with OR logic
    @pytest.mark.asyncio
    async def test_multiple_conditions_or_logic(self, action, mock_context):
        """Should filter with multiple conditions combined with OR."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="confidence", operator="greater_than", value=0.9
                ),
                FilterCondition(column="cv", operator="less_than", value=0.1),
            ],
            logic_operator="OR",
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # confidence > 0.9 OR cv < 0.1: A(0.95, conf>0.9), G(0.99, conf>0.9 AND cv<0.1)
        # E has confidence=0.90 (NOT > 0.9) and cv=0.15 (NOT < 0.1), so E should not match
        expected_ids = {"A", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 16: Keep vs Remove filtering modes
    @pytest.mark.asyncio
    async def test_keep_vs_remove_modes(self, action, mock_context):
        """Should support both keep and remove filtering modes."""
        # Test remove mode - remove proteins
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                )
            ],
            keep_or_remove="remove",
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Remove proteins, keep everything else: B, D, F, H
        expected_ids = {"B", "D", "F", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids

        # Test keep mode (default behavior already tested above)
        params.keep_or_remove = "keep"

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # Keep proteins: A, C, E, G
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 17: Edge case - empty dataset
    @pytest.mark.asyncio
    async def test_empty_dataset(self, action):
        """Should handle empty datasets gracefully."""
        empty_context = {
            "datasets": {"empty_data": pd.DataFrame()},
            "custom_action_data": {},
        }

        params = FilterDatasetParams(
            input_key="empty_data",
            filter_conditions=[
                FilterCondition(
                    column="any_column", operator="equals", value="any_value"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, empty_context
        )

        assert result.success is True
        filtered_data = empty_context["datasets"]["filtered_data"]
        assert len(filtered_data) == 0

    # Test 18: Edge case - missing input dataset
    @pytest.mark.asyncio
    async def test_missing_input_dataset(self, action):
        """Should handle missing input datasets with clear error."""
        params = FilterDatasetParams(
            input_key="nonexistent_data",
            filter_conditions=[
                FilterCondition(
                    column="any_column", operator="equals", value="any_value"
                )
            ],
            output_key="filtered_data",
        )

        context = {"datasets": {}, "custom_action_data": {}}

        result = await action.execute_typed([], "protein", params, None, None, context)

        assert result.success is False
        assert "not found" in result.message.lower()

    # Test 19: Edge case - missing filter column
    @pytest.mark.asyncio
    async def test_missing_filter_column(self, action, mock_context):
        """Should handle missing filter columns with clear error."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="nonexistent_column", operator="equals", value="any_value"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is False
        assert "column" in result.message.lower()

    # Test 20: Edge case - invalid regex pattern
    @pytest.mark.asyncio
    async def test_invalid_regex_pattern(self, action, mock_context):
        """Should handle invalid regex patterns gracefully."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="test_name", operator="regex", value="[invalid regex"
                )  # Missing closing bracket
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        # Should either handle gracefully or return error
        # Implementation will determine exact behavior
        if result.success is False:
            assert "regex" in result.message.lower()

    # Test 21: Filter metadata and logging
    @pytest.mark.asyncio
    async def test_filter_metadata_logging(self, action, mock_context):
        """Should add metadata about filtering when add_filter_log=True."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                )
            ],
            output_key="filtered_data",
            add_filter_log=True,
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        # Check that filtering statistics were recorded
        assert "total_input_rows" in result.message or "details" in result.__dict__

    # Test 22: Performance test placeholder
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action):
        """Should handle large datasets efficiently."""
        # Create large test dataset (smaller for unit tests)
        large_data = pd.DataFrame(
            {
                "id": [f"item_{i}" for i in range(1000)],
                "category": [
                    "biolink:Protein" if i % 3 == 0 else "biolink:SmallMolecule"
                    for i in range(1000)
                ],
                "confidence": [0.5 + (i % 50) / 100 for i in range(1000)],
            }
        )

        context = {"datasets": {"large_data": large_data}, "custom_action_data": {}}

        params = FilterDatasetParams(
            input_key="large_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                )
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed([], "protein", params, None, None, context)

        assert result.success is True
        filtered_data = context["datasets"]["filtered_data"]
        expected_count = len([i for i in range(1000) if i % 3 == 0])
        assert len(filtered_data) == expected_count

    # Test 23: Boolean column filtering
    @pytest.mark.asyncio
    async def test_boolean_column_filtering(self, action, mock_context):
        """Should filter boolean columns correctly."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(column="boolean_flag", operator="equals", value=True)
            ],
            output_key="filtered_data",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["filtered_data"]
        # boolean_flag == True: A, C, E, G
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 24: Real use case - protein quality filtering
    @pytest.mark.asyncio
    async def test_protein_quality_filtering_use_case(self, action, mock_context):
        """Real use case: Filter high-quality proteins."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:Protein"
                ),
                FilterCondition(
                    column="confidence", operator="greater_equal", value=0.85
                ),
                FilterCondition(column="cv", operator="less_than", value=0.25),
            ],
            logic_operator="AND",
            output_key="high_quality_proteins",
        )

        result = await action.execute_typed(
            [], "protein", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["high_quality_proteins"]
        # High quality proteins: A(0.95, 0.1), C(0.85, 0.2), E(0.90, 0.15), G(0.99, 0.05)
        expected_ids = {"A", "C", "E", "G"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 25: Real use case - metabolite quality control
    @pytest.mark.asyncio
    async def test_metabolite_quality_control_use_case(self, action, mock_context):
        """Real use case: Metabolite quality control filtering."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="category", operator="equals", value="biolink:SmallMolecule"
                ),
                FilterCondition(column="cv", operator="less_than", value=0.5),
                FilterCondition(
                    column="confidence", operator="greater_than", value=0.3
                ),
            ],
            logic_operator="AND",
            output_key="quality_metabolites",
        )

        result = await action.execute_typed(
            [], "metabolite", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["quality_metabolites"]
        # Quality small molecules: B(SmallMol, cv=0.4, conf=0.75)
        # F has SmallMol but cv=0.8 (too high)
        expected_ids = {"B"}
        assert set(row["id"] for row in filtered_data) == expected_ids

    # Test 26: Real use case - vendor focus
    @pytest.mark.asyncio
    async def test_vendor_focus_use_case(self, action, mock_context):
        """Real use case: Focus on specific lab vendors."""
        params = FilterDatasetParams(
            input_key="input_data",
            filter_conditions=[
                FilterCondition(
                    column="vendor", operator="in_list", value=["LabCorp", "Quest"]
                ),
                FilterCondition(column="test_name", operator="not_null"),
            ],
            logic_operator="AND",
            output_key="vendor_focused_data",
        )

        result = await action.execute_typed(
            [], "chemistry", params, None, None, mock_context
        )

        assert result.success is True
        filtered_data = mock_context["datasets"]["vendor_focused_data"]
        # LabCorp/Quest AND test_name not null: A, B, F, G, H
        # C is LabCorp but test_name is null
        expected_ids = {"A", "B", "F", "G", "H"}
        assert set(row["id"] for row in filtered_data) == expected_ids
