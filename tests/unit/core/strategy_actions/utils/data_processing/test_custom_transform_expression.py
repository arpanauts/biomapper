"""Tests for custom transformation expressions with security validation."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

from actions.utils.data_processing.custom_transform_expression import (
    CustomTransformExpressionAction,
    CustomTransformExpressionParams,
    TransformationSpec
)


class TestTransformationSpec:
    """Test TransformationSpec model validation."""
    
    def test_transformation_spec_creation(self):
        """Test TransformationSpec creation and validation."""
        
        spec = TransformationSpec(
            column="uniprot_id",
            expression="value.replace('UniProtKB:', '')",
            new_column="clean_uniprot_id",
            on_error="keep_original",
            drop_original=True
        )
        
        assert spec.column == "uniprot_id"
        assert spec.expression == "value.replace('UniProtKB:', '')"
        assert spec.new_column == "clean_uniprot_id"
        assert spec.on_error == "keep_original"
        assert spec.drop_original is True
    
    def test_transformation_spec_defaults(self):
        """Test TransformationSpec default values."""
        
        minimal_spec = TransformationSpec(
            column="test_column",
            expression="value.upper()"
        )
        
        assert minimal_spec.new_column is None
        assert minimal_spec.on_error == "keep_original"
        assert minimal_spec.drop_original is False


class TestCustomTransformExpressionParams:
    """Test CustomTransformExpressionParams validation."""
    
    def test_params_creation(self):
        """Test parameter model creation."""
        
        transformations = [
            TransformationSpec(
                column="protein_id",
                expression="value.split('|')[0]"
            ),
            TransformationSpec(
                column="confidence",
                expression="float(value) if value else 0.0"
            )
        ]
        
        params = CustomTransformExpressionParams(
            input_key="raw_proteins",
            output_key="processed_proteins",
            transformations=transformations,
            parallel=False
        )
        
        assert params.input_key == "raw_proteins"
        assert params.output_key == "processed_proteins"
        assert len(params.transformations) == 2
        assert params.parallel is False
    
    def test_params_validation(self):
        """Test parameter validation."""
        
        # Test empty transformations list should be valid but unusual
        params = CustomTransformExpressionParams(
            input_key="test",
            output_key="test_out",
            transformations=[]
        )
        
        assert len(params.transformations) == 0


class TestCustomTransformExpressionAction:
    """Test CustomTransformExpressionAction functionality."""
    
    @pytest.fixture
    def biological_datasets(self):
        """Create biological datasets for testing."""
        return {
            "proteins": pd.DataFrame({
                "uniprot_id": ["UniProtKB:P12345", "UniProtKB:Q9Y6R4", "O00533"],
                "gene_symbol": ["TP53", "BRCA1", "CD4"],
                "xrefs": ["UniProtKB:P12345|RefSeq:NP_000546", "Q9Y6R4;P38398", "O00533"],
                "confidence": ["0.95", "0.85", "0.75"],
                "length": [393, 1863, 458]
            }),
            "metabolites": pd.DataFrame({
                "hmdb_id": ["HMDB0000001", "HMDB0000002", "HMDB0000003"],
                "compound_name": ["1-methylhistidine", "1,3-diaminopropane", "L-alanine"],
                "mass": ["169.085", "74.084", "89.047"],
                "formula": ["C7H11N3O2", "C3H10N2", "C3H7NO2"]
            }),
            "edge_cases": pd.DataFrame({
                "mixed_ids": ["P12345|Q9Y6R4", "Q6EMK4", ""],  # Include problematic Q6EMK4
                "scores": ["0.95,0.85", "0.45", None],
                "notes": ["High quality", "Problematic identifier", "Missing data"]
            })
        }
    
    @pytest.fixture
    def action_context(self, biological_datasets):
        """Create test action context."""
        return {
            "datasets": biological_datasets,
            "statistics": {},
            "output_files": []
        }
    
    @pytest.mark.asyncio
    async def test_simple_string_transformation(self, action_context):
        """Test simple string transformations on biological data."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="transformed_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="value.replace('UniProtKB:', '')",
                    new_column="clean_uniprot_id"
                ),
                TransformationSpec(
                    column="gene_symbol",
                    expression="value.upper()"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        assert result.data["transformations_applied"] == 2
        assert result.data["rows_processed"] == 3
        
        # Verify transformations were applied
        transformed_data = action_context["datasets"]["transformed_proteins"]
        assert "clean_uniprot_id" in transformed_data.columns
        assert transformed_data.loc[0, "clean_uniprot_id"] == "P12345"
        assert transformed_data.loc[1, "clean_uniprot_id"] == "Q9Y6R4"
        assert transformed_data.loc[0, "gene_symbol"] == "TP53"  # Should remain uppercase
    
    @pytest.mark.asyncio
    async def test_numeric_conversions(self, action_context):
        """Test numeric type conversions with biological data."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="numeric_proteins",
            transformations=[
                TransformationSpec(
                    column="confidence",
                    expression="float(value)",
                    new_column="confidence_numeric"
                ),
                TransformationSpec(
                    column="length",
                    expression="int(value) if value > 0 else 0"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify numeric conversions
        transformed_data = action_context["datasets"]["numeric_proteins"]
        assert transformed_data.loc[0, "confidence_numeric"] == 0.95
        assert isinstance(transformed_data.loc[0, "confidence_numeric"], float)
        assert transformed_data.loc[0, "length"] == 393
        assert isinstance(transformed_data.loc[0, "length"], (int, np.integer))
    
    @pytest.mark.asyncio
    async def test_conditional_transformations(self, action_context):
        """Test conditional transformation expressions."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="conditional_proteins",
            transformations=[
                TransformationSpec(
                    column="xrefs",
                    expression="value.split('|')[0] if '|' in value else value.split(';')[0] if ';' in value else value",
                    new_column="primary_id"
                ),
                TransformationSpec(
                    column="confidence",
                    expression="'high' if float(value) >= 0.9 else 'medium' if float(value) >= 0.7 else 'low'",
                    new_column="confidence_category"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify conditional transformations
        transformed_data = action_context["datasets"]["conditional_proteins"]
        assert transformed_data.loc[0, "primary_id"] == "UniProtKB:P12345"  # Split on |
        assert transformed_data.loc[1, "primary_id"] == "Q9Y6R4"  # Split on ; (fallback)
        assert transformed_data.loc[0, "confidence_category"] == "high"  # 0.95 >= 0.9
        assert transformed_data.loc[1, "confidence_category"] == "medium"  # 0.85 in [0.7, 0.9)
    
    @pytest.mark.asyncio
    async def test_numpy_mathematical_operations(self, action_context):
        """Test mathematical operations using numpy."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="metabolites",
            output_key="calculated_metabolites",
            transformations=[
                TransformationSpec(
                    column="mass",
                    expression="np.log10(float(value)) if float(value) > 0 else np.nan",
                    new_column="log_mass"
                ),
                TransformationSpec(
                    column="mass",
                    expression="round(float(value), 2)",
                    new_column="rounded_mass"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify mathematical operations
        transformed_data = action_context["datasets"]["calculated_metabolites"]
        log_mass_0 = transformed_data.loc[0, "log_mass"]
        assert abs(log_mass_0 - np.log10(169.085)) < 0.001  # Should be close to log10(169.085)
        assert transformed_data.loc[0, "rounded_mass"] == 169.09  # Rounded to 2 decimal places
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self, action_context):
        """Test handling of edge cases including Q6EMK4 and missing data."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="edge_cases",
            output_key="processed_edge_cases",
            transformations=[
                TransformationSpec(
                    column="mixed_ids",
                    expression="'Q6EMK4_EDGE_CASE' if value == 'Q6EMK4' else value.split('|')[0] if value and '|' in value else value",
                    new_column="processed_id"
                ),
                TransformationSpec(
                    column="scores",
                    expression="float(value.split(',')[0]) if value and ',' in value else float(value) if value else 0.0",
                    new_column="primary_score"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify edge case handling
        transformed_data = action_context["datasets"]["processed_edge_cases"]
        assert transformed_data.loc[0, "processed_id"] == "P12345"  # Split composite ID
        assert transformed_data.loc[1, "processed_id"] == "Q6EMK4_EDGE_CASE"  # Special handling for Q6EMK4
        assert transformed_data.loc[2, "processed_id"] == ""  # Empty string preserved
        
        assert transformed_data.loc[0, "primary_score"] == 0.95  # First score from comma-separated
        assert transformed_data.loc[1, "primary_score"] == 0.45  # Single score
        assert transformed_data.loc[2, "primary_score"] == 0.0   # None converted to 0.0
    
    @pytest.mark.asyncio
    async def test_error_handling_keep_original(self, action_context):
        """Test error handling with keep_original strategy."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="error_test_proteins",
            transformations=[
                TransformationSpec(
                    column="gene_symbol",
                    expression="int(value)",  # This will fail for string values
                    on_error="keep_original"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True  # Should succeed despite errors
        
        # Verify original values are kept when transformation fails
        transformed_data = action_context["datasets"]["error_test_proteins"]
        assert transformed_data.loc[0, "gene_symbol"] == "TP53"  # Original value kept
        assert transformed_data.loc[1, "gene_symbol"] == "BRCA1"  # Original value kept
    
    @pytest.mark.asyncio
    async def test_error_handling_null_replacement(self, action_context):
        """Test error handling with null replacement strategy."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="null_test_proteins",
            transformations=[
                TransformationSpec(
                    column="gene_symbol",
                    expression="int(value)",  # This will fail for string values
                    on_error="null",
                    new_column="numeric_gene"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify null values are set when transformation fails
        transformed_data = action_context["datasets"]["null_test_proteins"]
        assert pd.isna(transformed_data.loc[0, "numeric_gene"])
        assert pd.isna(transformed_data.loc[1, "numeric_gene"])
    
    @pytest.mark.asyncio
    async def test_error_handling_raise_exception(self, action_context):
        """Test error handling with raise strategy."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="raise_test_proteins",
            transformations=[
                TransformationSpec(
                    column="gene_symbol",
                    expression="int(value)",  # This will fail for string values
                    on_error="raise"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        # Should return error result when raise strategy is used
        assert result.success is False
        assert "failed on column" in result.error
    
    @pytest.mark.asyncio
    async def test_drop_original_column(self, action_context):
        """Test dropping original column after transformation."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="drop_test_proteins",
            transformations=[
                TransformationSpec(
                    column="uniprot_id",
                    expression="value.replace('UniProtKB:', '')",
                    new_column="clean_id",
                    drop_original=True
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify original column was dropped and new column exists
        transformed_data = action_context["datasets"]["drop_test_proteins"]
        assert "uniprot_id" not in transformed_data.columns
        assert "clean_id" in transformed_data.columns
        assert transformed_data.loc[0, "clean_id"] == "P12345"
    
    @pytest.mark.asyncio
    async def test_create_new_column_from_expression(self, action_context):
        """Test creating entirely new columns from expressions."""
        action = CustomTransformExpressionAction()
        
        params = CustomTransformExpressionParams(
            input_key="proteins",
            output_key="new_column_proteins",
            transformations=[
                TransformationSpec(
                    column="new_computed_field",  # Column doesn't exist initially
                    expression="'PROTEIN_' + str(len('test'))",  # Create new computed value
                    new_column="computed_label"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert result.success is True
        
        # Verify new column was created
        transformed_data = action_context["datasets"]["new_column_proteins"]
        assert "computed_label" in transformed_data.columns
        # Note: The exact value depends on how the action handles non-existent columns


class TestExpressionSecurity:
    """Test security aspects of expression evaluation."""
    
    @pytest.fixture
    def security_context(self):
        """Create minimal context for security testing."""
        return {
            "datasets": {
                "test_data": pd.DataFrame({
                    "values": ["test1", "test2", "test3"]
                })
            },
            "statistics": {},
            "output_files": []
        }
    
    @pytest.mark.asyncio
    async def test_safe_expressions_allowed(self, security_context):
        """Test that safe expressions are allowed."""
        action = CustomTransformExpressionAction()
        
        safe_expressions = [
            "value.upper()",
            "value.replace('old', 'new')",
            "len(value)",
            "str(value)",
            "float(value) if value.isdigit() else 0.0",
            "value.split(',')[0] if ',' in value else value",
            "np.log10(float(value)) if value else np.nan"
        ]
        
        for expr in safe_expressions:
            params = CustomTransformExpressionParams(
                input_key="test_data",
                output_key="safe_test",
                transformations=[
                    TransformationSpec(
                        column="values",
                        expression=expr,
                        on_error="keep_original"
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="test",
                params=params,
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context=security_context
            )
            
            # Safe expressions should succeed
            assert result.success is True, f"Safe expression failed: {expr}"
    
    @pytest.mark.asyncio
    async def test_unsafe_expressions_blocked(self, security_context):
        """Test that unsafe expressions are properly restricted."""
        action = CustomTransformExpressionAction()
        
        # These expressions should fail due to restricted builtins
        unsafe_expressions = [
            "__import__('os').system('rm -rf /')",
            "eval('malicious_code')",
            "exec('import subprocess')",
            "open('/etc/passwd', 'r')",
            "globals()",
            "locals()",
            "compile('code', 'string', 'exec')"
        ]
        
        # Special case: __builtins__ doesn't fail but returns empty dict
        special_expressions = {
            "__builtins__": {}  # This expression "succeeds" but returns empty dict
        }
        
        for i, expr in enumerate(unsafe_expressions):
            # Create fresh context for each test to avoid cross-contamination
            fresh_context = {
                "datasets": {
                    "test_data": pd.DataFrame({
                        "values": ["test1", "test2", "test3"]
                    })
                },
                "statistics": {},
                "output_files": []
            }
            
            params = CustomTransformExpressionParams(
                input_key="test_data",
                output_key=f"unsafe_test_{i}",  # Unique output key for each test
                transformations=[
                    TransformationSpec(
                        column="values",
                        expression=expr,
                        on_error="keep_original"  # Should keep original due to security error
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="test",
                params=params,
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context=fresh_context
            )
            
            # Unsafe expressions should either fail or keep original values
            if result.success:
                # If it succeeds, original values should be preserved (due to expression failure)
                transformed_data = fresh_context["datasets"][f"unsafe_test_{i}"]
                assert transformed_data.loc[0, "values"] == "test1", f"Expression {expr} should preserve original value"
                
        # Test special expressions that don't fail but return restricted values
        for i, (expr, expected_value) in enumerate(special_expressions.items()):
            # Create fresh context for each test to avoid cross-contamination
            fresh_context = {
                "datasets": {
                    "test_data": pd.DataFrame({
                        "values": ["test1", "test2", "test3"]
                    })
                },
                "statistics": {},
                "output_files": []
            }
            
            params = CustomTransformExpressionParams(
                input_key="test_data",
                output_key=f"special_test_{i}",  # Unique output key for each test
                transformations=[
                    TransformationSpec(
                        column="values",
                        expression=expr,
                        on_error="keep_original"
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="test",
                params=params,
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context=fresh_context
            )
            
            # Special expressions succeed but return the restricted value
            if result.success:
                transformed_data = fresh_context["datasets"][f"special_test_{i}"]
                # All rows should have the expected restricted value
                for row_idx in range(len(transformed_data)):
                    assert transformed_data.loc[row_idx, "values"] == expected_value, f"Expression {expr} should return restricted value {expected_value}"
    
    @pytest.mark.asyncio
    async def test_restricted_namespace_enforcement(self, security_context):
        """Test that the namespace is properly restricted."""
        action = CustomTransformExpressionAction()
        
        # Test that only allowed functions/modules are available
        namespace_test_expressions = [
            "str(value)",      # Should work - str is allowed
            "int(value) if value.isdigit() else 0",  # Should work - int is allowed
            "np.nan",          # Should work - np is allowed
            "pd.isna(value)",  # Should work - pd is allowed
            "len(value)"       # Should work - len is allowed
        ]
        
        for expr in namespace_test_expressions:
            params = CustomTransformExpressionParams(
                input_key="test_data",
                output_key="namespace_test",
                transformations=[
                    TransformationSpec(
                        column="values",
                        expression=expr,
                        on_error="keep_original"
                    )
                ]
            )
            
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type="test",
                params=params,
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context=security_context
            )
            
            # These should work with the allowed namespace
            assert result.success is True, f"Allowed namespace expression failed: {expr}"
    
    @pytest.mark.asyncio
    async def test_null_value_handling_security(self, security_context):
        """Test secure handling of null/None values."""
        action = CustomTransformExpressionAction()
        
        # Add dataset with null values
        security_context["datasets"]["null_data"] = pd.DataFrame({
            "values": ["test1", None, "test3", ""]
        })
        
        params = CustomTransformExpressionParams(
            input_key="null_data",
            output_key="null_security_test",
            transformations=[
                TransformationSpec(
                    column="values",
                    expression="value.upper() if value else 'NULL_VALUE'",
                    on_error="keep_original"
                )
            ]
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=security_context
        )
        
        assert result.success is True
        
        # Verify null handling doesn't cause security issues
        transformed_data = security_context["datasets"]["null_security_test"]
        assert transformed_data.loc[0, "values"] == "TEST1"
        assert transformed_data.loc[1, "values"] == "NULL_VALUE"  # None handled safely
        assert transformed_data.loc[2, "values"] == "TEST3"
        assert transformed_data.loc[3, "values"] == "NULL_VALUE"  # Empty string handled


class TestPerformanceAndScalability:
    """Test performance and scalability of custom transformations."""
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """Test transformation performance with large biological datasets."""
        action = CustomTransformExpressionAction()
        
        # Generate large dataset
        large_size = 10000
        large_dataset = pd.DataFrame({
            "protein_id": [f"P{i:05d}" for i in range(large_size)],
            "confidence": [str(0.5 + (i % 100) / 200) for i in range(large_size)],
            "description": [f"Protein_{i}" for i in range(large_size)]
        })
        
        context = {
            "datasets": {"large_proteins": large_dataset},
            "statistics": {},
            "output_files": []
        }
        
        params = CustomTransformExpressionParams(
            input_key="large_proteins",
            output_key="transformed_large_proteins",
            transformations=[
                TransformationSpec(
                    column="confidence",
                    expression="float(value)",
                    new_column="confidence_numeric"
                ),
                TransformationSpec(
                    column="description",
                    expression="value.upper()"
                )
            ]
        )
        
        import time
        start_time = time.time()
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=context
        )
        
        execution_time = time.time() - start_time
        
        assert result.success is True
        assert result.data["rows_processed"] == large_size
        assert result.data["transformations_applied"] == 2
        
        # Performance assertion (generous bound for CI environments)
        assert execution_time < 30.0  # Should complete in reasonable time
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency of transformations."""
        action = CustomTransformExpressionAction()
        
        # Create dataset with moderate size
        dataset_size = 50000
        test_dataset = pd.DataFrame({
            "id": range(dataset_size),
            "data": ["x" * 20] * dataset_size  # 20 chars per row
        })
        
        context = {
            "datasets": {"memory_test": test_dataset},
            "statistics": {},
            "output_files": []
        }
        
        params = CustomTransformExpressionParams(
            input_key="memory_test",
            output_key="memory_test_output",
            transformations=[
                TransformationSpec(
                    column="data",
                    expression="value.upper()"
                )
            ]
        )
        
        # Monitor memory usage
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=context
        )
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        assert result.success is True
        assert result.data["rows_processed"] == dataset_size
        
        # Memory increase should be reasonable (generous bound)
        assert memory_increase < 200 * 1024 * 1024  # < 200MB increase
    
    @pytest.mark.asyncio
    async def test_complex_expression_performance(self):
        """Test performance with complex expressions."""
        action = CustomTransformExpressionAction()
        
        dataset = pd.DataFrame({
            "composite_id": [f"P{i:05d}|Q{i:05d}|O{i:05d}" for i in range(1000)],
            "scores": [f"{0.8 + i/10000},{0.7 + i/10000},{0.6 + i/10000}" for i in range(1000)]
        })
        
        context = {
            "datasets": {"complex_test": dataset},
            "statistics": {},
            "output_files": []
        }
        
        params = CustomTransformExpressionParams(
            input_key="complex_test",
            output_key="complex_output",
            transformations=[
                TransformationSpec(
                    column="composite_id",
                    expression="[x.strip() for x in value.split('|') if x.startswith('P')][0] if any(x.startswith('P') for x in value.split('|')) else value",
                    new_column="primary_protein"
                ),
                TransformationSpec(
                    column="scores",
                    expression="np.mean([float(x) for x in value.split(',')]) if ',' in value else float(value)",
                    new_column="average_score"
                )
            ]
        )
        
        import time
        start_time = time.time()
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=context
        )
        
        execution_time = time.time() - start_time
        
        assert result.success is True
        assert execution_time < 10.0  # Complex expressions should still be reasonably fast