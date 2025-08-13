"""Unit tests for expression-based CUSTOM_TRANSFORM action."""

import pytest
import pandas as pd
from biomapper.core.strategy_actions.utils.data_processing.custom_transform_expression import (
    CustomTransformExpressionAction,
    CustomTransformExpressionParams,
    TransformationSpec,
)


class TestCustomTransformExpressionAction:
    """Test suite for expression-based custom transformations."""

    @pytest.fixture
    def sample_context(self):
        """Create sample context with test data."""
        return {
            "datasets": {
                "test_proteins": pd.DataFrame(
                    [
                        {
                            "uniprot_id": "p12345",
                            "gene_symbol": "BRCA1|BRCA2",
                            "concentration": "1.5",
                        },
                        {
                            "uniprot_id": "Q67890",
                            "gene_symbol": "TP53",
                            "concentration": "2.3",
                        },
                        {
                            "uniprot_id": "a11111",
                            "gene_symbol": "EGFR|",
                            "concentration": None,
                        },
                    ]
                )
            }
        }

    @pytest.mark.asyncio
    async def test_simple_string_transformation(self, sample_context):
        """Test uppercase transformation on string column."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(column="uniprot_id", expression="value.upper()")
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        assert "transformed_proteins" in sample_context["datasets"]

        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["uniprot_id"] == "P12345"
        assert output_df.iloc[1]["uniprot_id"] == "Q67890"
        assert output_df.iloc[2]["uniprot_id"] == "A11111"

    @pytest.mark.asyncio
    async def test_complex_string_splitting(self, sample_context):
        """Test splitting gene symbols on pipe character."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="gene_symbol",
                    expression="value.split('|')[0] if '|' in value else value",
                    new_column="primary_gene",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["primary_gene"] == "BRCA1"
        assert output_df.iloc[1]["primary_gene"] == "TP53"
        assert output_df.iloc[2]["primary_gene"] == "EGFR"

    @pytest.mark.asyncio
    async def test_numeric_transformation_with_nulls(self, sample_context):
        """Test converting string to float with null handling."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="concentration",
                    expression="float(value) if value else 0.0",
                    on_error="null",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["concentration"] == 1.5
        assert output_df.iloc[1]["concentration"] == 2.3
        # Handle both 0.0 and NaN as valid results for null input
        assert output_df.iloc[2]["concentration"] == 0.0 or pd.isna(
            output_df.iloc[2]["concentration"]
        )

    @pytest.mark.asyncio
    async def test_multiple_transformations(self, sample_context):
        """Test applying multiple transformations in sequence."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(column="uniprot_id", expression="value.upper()"),
                TransformationSpec(
                    column="gene_symbol",
                    expression="value.split('|')[0] if '|' in value else value",
                ),
                TransformationSpec(
                    column="concentration",
                    expression="float(value) * 1000 if value else 0.0",
                    new_column="concentration_ng",
                ),
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        assert result.data["transformations_applied"] == 3

        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["uniprot_id"] == "P12345"
        assert output_df.iloc[0]["gene_symbol"] == "BRCA1"
        assert output_df.iloc[0]["concentration_ng"] == 1500.0

    @pytest.mark.asyncio
    async def test_error_handling_keep_original(self, sample_context):
        """Test keep_original error handling mode."""
        action = CustomTransformExpressionAction()

        # Test with invalid expression and keep_original mode
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="invalid_function(value)",
                    on_error="keep_original",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)
        assert result.success

        # Original values should be preserved
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["uniprot_id"] == "p12345"

    @pytest.mark.asyncio
    async def test_error_handling_null(self, sample_context):
        """Test null error handling mode."""
        action = CustomTransformExpressionAction()

        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="int(value)",  # Will fail on string input
                    on_error="null",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)
        assert result.success

        # Values should be null/NaN
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert pd.isna(output_df.iloc[0]["uniprot_id"])

    @pytest.mark.asyncio
    async def test_error_handling_raise(self, sample_context):
        """Test raise error handling mode."""
        action = CustomTransformExpressionAction()

        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="invalid_function(value)",
                    on_error="raise",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)
        assert not result.success
        assert "invalid_function" in result.error

    @pytest.mark.asyncio
    async def test_missing_column_handling(self, sample_context):
        """Test behavior when transforming non-existent column."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="nonexistent_column", expression="value.upper()"
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        # Should succeed but skip the missing column
        assert result.success
        assert "transformed_proteins" in sample_context["datasets"]

    @pytest.mark.asyncio
    async def test_expression_with_conditionals(self, sample_context):
        """Test complex expressions with conditionals."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression='"HUMAN_" + value.upper() if value.lower().startswith("p") else value.upper()',
                    new_column="species_prefixed_id",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["species_prefixed_id"] == "HUMAN_P12345"
        assert (
            output_df.iloc[1]["species_prefixed_id"] == "Q67890"
        )  # Doesn't start with 'p'

    @pytest.mark.asyncio
    async def test_new_column_creation(self, sample_context):
        """Test creating new columns with transformations."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id", expression="len(value)", new_column="id_length"
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert "id_length" in output_df.columns
        assert output_df.iloc[0]["id_length"] == 6  # 'p12345' has 6 characters
        assert output_df.iloc[0]["uniprot_id"] == "p12345"  # Original preserved

    @pytest.mark.asyncio
    async def test_dataframe_from_dict_format(self, sample_context):
        """Test handling different input data formats."""
        # Test with dict format containing 'data' key
        sample_context["datasets"]["test_dict_format"] = {
            "data": [{"id": "ABC123", "value": 100}, {"id": "DEF456", "value": 200}]
        }

        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_dict_format",
            output_key="transformed_dict",
            transformations=[
                TransformationSpec(column="id", expression="value.lower()")
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_dict"]
        assert output_df.iloc[0]["id"] == "abc123"

    @pytest.mark.asyncio
    async def test_parallel_transformation_mode(self, sample_context):
        """Test parallel vs sequential transformation modes."""
        action = CustomTransformExpressionAction()

        # Test with parallel=True (default)
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(column="uniprot_id", expression="value.upper()"),
                TransformationSpec(column="gene_symbol", expression="value.lower()"),
            ],
            parallel=True,
        )

        result = await action.execute_typed(params, sample_context)
        assert result.success

        # Test with parallel=False
        params.parallel = False
        result = await action.execute_typed(params, sample_context)
        assert result.success

    @pytest.mark.asyncio
    async def test_drop_original_column(self, sample_context):
        """Test dropping original columns after transformation."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="value.upper()",
                    new_column="uniprot_normalized",
                    drop_original=True,
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert "uniprot_normalized" in output_df.columns
        assert "uniprot_id" not in output_df.columns

    @pytest.mark.asyncio
    async def test_missing_input_key(self, sample_context):
        """Test error when input key doesn't exist."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="nonexistent_key",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(column="some_column", expression="value.upper()")
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_complex_lambda_expression(self, sample_context):
        """Test using lambda functions in expressions."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="gene_symbol",
                    expression='(lambda x: x.replace("|", "_") if x else "UNKNOWN")(value)',
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        assert output_df.iloc[0]["gene_symbol"] == "BRCA1_BRCA2"
        assert output_df.iloc[1]["gene_symbol"] == "TP53"
        assert output_df.iloc[2]["gene_symbol"] == "EGFR_"

    @pytest.mark.asyncio
    async def test_numpy_operations(self, sample_context):
        """Test using numpy operations in expressions."""
        action = CustomTransformExpressionAction()
        params = CustomTransformExpressionParams(
            input_key="test_proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="concentration",
                    expression="np.log10(float(value)) if value else np.nan",
                )
            ],
        )

        result = await action.execute_typed(params, sample_context)

        assert result.success
        output_df = sample_context["datasets"]["transformed_proteins"]
        # log10(1.5) ≈ 0.176
        assert abs(output_df.iloc[0]["concentration"] - 0.176) < 0.01
        # log10(2.3) ≈ 0.362
        assert abs(output_df.iloc[1]["concentration"] - 0.362) < 0.01
        assert pd.isna(output_df.iloc[2]["concentration"])
