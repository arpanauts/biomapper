"""Tests for exceptions.py."""


from core.exceptions import (
    ErrorCode,
    BiomapperError,
    NoPathFoundError,
    MappingExecutionError,
    ClientError,
    ClientExecutionError,
    ClientInitializationError,
    ConfigurationError,
    CacheError,
    CacheTransactionError,
    CacheRetrievalError,
    CacheStorageError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError,
    StrategyNotFoundError,
    InactiveStrategyError,
    DatasetNotFoundError,
    TransformationError,
    SchemaValidationError,
    MappingQualityError,
    ValidationError,
    ProcessingError
)


class TestErrorCode:
    """Test ErrorCode enum."""
    
    def test_error_code_enum_values(self):
        """Test error code enum has expected values."""
        # General errors
        assert ErrorCode.UNKNOWN_ERROR.value == 1
        assert ErrorCode.CONFIGURATION_ERROR.value == 2
        assert ErrorCode.NOT_IMPLEMENTED.value == 3
        
        # Client errors
        assert ErrorCode.CLIENT_INITIALIZATION_ERROR.value == 100
        assert ErrorCode.CLIENT_EXECUTION_ERROR.value == 101
        assert ErrorCode.CLIENT_TIMEOUT_ERROR.value == 102
        
        # Database errors
        assert ErrorCode.DATABASE_CONNECTION_ERROR.value == 200
        assert ErrorCode.DATABASE_QUERY_ERROR.value == 201
        assert ErrorCode.DATABASE_TRANSACTION_ERROR.value == 202
        
        # Mapping errors
        assert ErrorCode.NO_PATH_FOUND_ERROR.value == 400
        assert ErrorCode.MAPPING_EXECUTION_ERROR.value == 401
        assert ErrorCode.STRATEGY_NOT_FOUND_ERROR.value == 403
    
    def test_error_code_names(self):
        """Test error code names are correct."""
        assert ErrorCode.UNKNOWN_ERROR.name == "UNKNOWN_ERROR"
        assert ErrorCode.CLIENT_EXECUTION_ERROR.name == "CLIENT_EXECUTION_ERROR"
        assert ErrorCode.MAPPING_EXECUTION_ERROR.name == "MAPPING_EXECUTION_ERROR"
    
    def test_error_code_ranges(self):
        """Test error codes are in expected ranges."""
        # General errors (1-99)
        general_codes = [ErrorCode.UNKNOWN_ERROR, ErrorCode.CONFIGURATION_ERROR, ErrorCode.NOT_IMPLEMENTED]
        for code in general_codes:
            assert 1 <= code.value <= 99
        
        # Client errors (100-199)
        client_codes = [ErrorCode.CLIENT_INITIALIZATION_ERROR, ErrorCode.CLIENT_EXECUTION_ERROR, ErrorCode.CLIENT_TIMEOUT_ERROR]
        for code in client_codes:
            assert 100 <= code.value <= 199
        
        # Database errors (200-299)
        db_codes = [ErrorCode.DATABASE_CONNECTION_ERROR, ErrorCode.DATABASE_QUERY_ERROR, ErrorCode.DATABASE_TRANSACTION_ERROR]
        for code in db_codes:
            assert 200 <= code.value <= 299


class TestBiomapperError:
    """Test BiomapperError base exception class."""
    
    def test_basic_error_instantiation(self):
        """Test basic error instantiation."""
        error = BiomapperError("Test error message")
        
        assert str(error) == "[UNKNOWN_ERROR] Test error message"
        assert error.message == "Test error message"
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.details == {}
    
    def test_error_with_custom_code(self):
        """Test error with custom error code."""
        error = BiomapperError(
            "Custom error",
            error_code=ErrorCode.CONFIGURATION_ERROR
        )
        
        assert error.error_code == ErrorCode.CONFIGURATION_ERROR
        assert str(error) == "[CONFIGURATION_ERROR] Custom error"
    
    def test_error_with_details(self):
        """Test error with details dictionary."""
        details = {
            "protein_id": "P12345",
            "dataset": "uniprot",
            "attempted_action": "normalize_accession"
        }
        
        error = BiomapperError(
            "Protein normalization failed",
            error_code=ErrorCode.TRANSFORMATION_ERROR,
            details=details
        )
        
        assert error.details == details
        assert "protein_id=P12345" in str(error)
        assert "dataset=uniprot" in str(error)
        assert "attempted_action=normalize_accession" in str(error)
    
    def test_error_inheritance(self):
        """Test error inheritance from Exception."""
        error = BiomapperError("Test error")
        
        assert isinstance(error, Exception)
        assert isinstance(error, BiomapperError)
    
    def test_error_str_formatting(self):
        """Test error string formatting."""
        error = BiomapperError(
            "Test message",
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            details={"key1": "value1", "key2": "value2"}
        )
        
        error_str = str(error)
        
        assert "[CLIENT_EXECUTION_ERROR]" in error_str
        assert "Test message" in error_str
        assert "key1=value1" in error_str
        assert "key2=value2" in error_str
    
    def test_error_with_empty_details(self):
        """Test error with empty details."""
        error = BiomapperError("Test error", details={})
        
        assert error.details == {}
        assert str(error) == "[UNKNOWN_ERROR] Test error"
    
    def test_error_with_none_details(self):
        """Test error with None details."""
        error = BiomapperError("Test error", details=None)
        
        assert error.details == {}
        assert str(error) == "[UNKNOWN_ERROR] Test error"
    
    def test_biological_data_in_details(self):
        """Test error with biological data in details."""
        details = {
            "uniprot_ids": ["P12345", "Q9Y6R4"],
            "hmdb_ids": ["HMDB0000001", "HMDB0000123"],
            "failed_mapping_count": 42,
            "success_rate": 0.73
        }
        
        error = BiomapperError(
            "Biological mapping failed",
            error_code=ErrorCode.MAPPING_EXECUTION_ERROR,
            details=details
        )
        
        error_str = str(error)
        assert "uniprot_ids=['P12345', 'Q9Y6R4']" in error_str
        assert "failed_mapping_count=42" in error_str


class TestSpecificExceptions:
    """Test specific exception classes."""
    
    def test_no_path_found_error(self):
        """Test NoPathFoundError."""
        details = {"source": "uniprot", "target": "hmdb", "attempted_paths": 5}
        error = NoPathFoundError("No mapping path found", details=details)
        
        assert error.error_code == ErrorCode.NO_PATH_FOUND_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_mapping_execution_error(self):
        """Test MappingExecutionError."""
        details = {"strategy": "protein_mapping", "step": "normalize_ids"}
        error = MappingExecutionError("Mapping step failed", details=details)
        
        assert error.error_code == ErrorCode.MAPPING_EXECUTION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        details = {"config_file": "strategy.yaml", "missing_field": "parameters.output_dir"}
        error = ConfigurationError("Invalid configuration", details=details)
        
        assert error.error_code == ErrorCode.CONFIGURATION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_strategy_not_found_error(self):
        """Test StrategyNotFoundError."""
        details = {"strategy_name": "missing_strategy", "available_strategies": ["strategy1", "strategy2"]}
        error = StrategyNotFoundError("Strategy not found", details=details)
        
        assert error.error_code == ErrorCode.STRATEGY_NOT_FOUND_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_inactive_strategy_error(self):
        """Test InactiveStrategyError."""
        details = {"strategy_name": "inactive_strategy", "status": "disabled"}
        error = InactiveStrategyError("Strategy is inactive", details=details)
        
        assert error.error_code == ErrorCode.INACTIVE_STRATEGY_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_dataset_not_found_error(self):
        """Test DatasetNotFoundError."""
        details = {"dataset_key": "protein_data", "available_keys": ["metabolite_data", "gene_data"]}
        error = DatasetNotFoundError("Dataset not found", details=details)
        
        assert error.error_code == ErrorCode.DATASET_NOT_FOUND_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_transformation_error(self):
        """Test TransformationError."""
        details = {"transformation": "normalize_identifiers", "input_count": 100, "failed_count": 25}
        error = TransformationError("Data transformation failed", details=details)
        
        assert error.error_code == ErrorCode.TRANSFORMATION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_schema_validation_error(self):
        """Test SchemaValidationError."""
        details = {"schema": "protein_schema", "validation_errors": ["missing_id_column", "invalid_format"]}
        error = SchemaValidationError("Schema validation failed", details=details)
        
        assert error.error_code == ErrorCode.SCHEMA_VALIDATION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_mapping_quality_error(self):
        """Test MappingQualityError."""
        details = {"quality_threshold": 0.8, "actual_quality": 0.6, "metric": "jaccard_similarity"}
        error = MappingQualityError("Mapping quality below threshold", details=details)
        
        assert error.error_code == ErrorCode.MAPPING_QUALITY_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_validation_error(self):
        """Test ValidationError."""
        details = {"field": "uniprot_id", "value": "invalid_id", "expected_format": "P[0-9]{5}"}
        error = ValidationError("Validation failed", details=details)
        
        assert error.error_code == ErrorCode.API_VALIDATION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details
    
    def test_processing_error(self):
        """Test ProcessingError."""
        details = {"processor": "metabolite_enricher", "batch_size": 1000, "failure_point": "api_timeout"}
        error = ProcessingError("Data processing failed", details=details)
        
        assert error.error_code == ErrorCode.MAPPING_EXECUTION_ERROR
        assert isinstance(error, BiomapperError)
        assert error.details == details


class TestClientErrors:
    """Test client-related error classes."""
    
    def test_client_error_base_class(self):
        """Test ClientError base class."""
        details = {"endpoint": "https://api.uniprot.org", "timeout": 30}
        error = ClientError(
            "Client error occurred",
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            client_name="UniProtClient",
            details=details
        )
        
        assert error.error_code == ErrorCode.CLIENT_EXECUTION_ERROR
        assert error.client_name == "UniProtClient"
        assert error.details["client_name"] == "UniProtClient"
        assert error.details["endpoint"] == "https://api.uniprot.org"
        assert isinstance(error, BiomapperError)
    
    def test_client_error_without_client_name(self):
        """Test ClientError without client name."""
        error = ClientError(
            "Client error",
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR
        )
        
        assert error.client_name is None
        assert "client_name" not in error.details
    
    def test_client_error_non_dict_details(self):
        """Test ClientError with non-dict details."""
        error = ClientError(
            "Client error",
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            details="string_details"
        )
        
        assert isinstance(error.details, dict)
        assert error.details["original_details"] == "string_details"
    
    def test_client_execution_error(self):
        """Test ClientExecutionError."""
        details = {"method": "map_identifiers", "input_ids": ["P12345", "Q9Y6R4"]}
        error = ClientExecutionError(
            "Client execution failed",
            client_name="UniProtClient",
            details=details
        )
        
        assert error.error_code == ErrorCode.CLIENT_EXECUTION_ERROR
        assert error.client_name == "UniProtClient"
        assert isinstance(error, ClientError)
        assert isinstance(error, BiomapperError)
    
    def test_client_initialization_error(self):
        """Test ClientInitializationError."""
        details = {"config_file": "uniprot_config.yaml", "missing_key": "api_endpoint"}
        error = ClientInitializationError(
            "Client initialization failed",
            client_name="UniProtClient",
            details=details
        )
        
        assert error.error_code == ErrorCode.CLIENT_INITIALIZATION_ERROR
        assert error.client_name == "UniProtClient"
        assert isinstance(error, ClientError)
        assert isinstance(error, BiomapperError)


class TestCacheErrors:
    """Test cache-related error classes."""
    
    def test_cache_error_base_class(self):
        """Test CacheError base class."""
        error = CacheError(
            "Cache error occurred",
            error_code=ErrorCode.CACHE_RETRIEVAL_ERROR,
            details={"cache_type": "redis", "key": "protein_mapping_cache"}
        )
        
        assert error.error_code == ErrorCode.CACHE_RETRIEVAL_ERROR
        assert isinstance(error, BiomapperError)
    
    def test_cache_transaction_error(self):
        """Test CacheTransactionError."""
        details = {"operation": "commit", "transaction_id": "tx_12345"}
        error = CacheTransactionError("Cache transaction failed", details=details)
        
        assert error.error_code == ErrorCode.CACHE_TRANSACTION_ERROR
        assert isinstance(error, CacheError)
        assert isinstance(error, BiomapperError)
    
    def test_cache_retrieval_error(self):
        """Test CacheRetrievalError."""
        details = {"cache_key": "uniprot:P12345", "cache_type": "memory"}
        error = CacheRetrievalError("Failed to retrieve from cache", details=details)
        
        assert error.error_code == ErrorCode.CACHE_RETRIEVAL_ERROR
        assert isinstance(error, CacheError)
        assert isinstance(error, BiomapperError)
    
    def test_cache_storage_error(self):
        """Test CacheStorageError."""
        details = {"cache_key": "hmdb:HMDB0000001", "data_size": "10MB", "error": "disk_full"}
        error = CacheStorageError("Failed to store in cache", details=details)
        
        assert error.error_code == ErrorCode.CACHE_STORAGE_ERROR
        assert isinstance(error, CacheError)
        assert isinstance(error, BiomapperError)


class TestDatabaseErrors:
    """Test database-related error classes."""
    
    def test_database_error_base_class(self):
        """Test DatabaseError base class."""
        error = DatabaseError(
            "Database error occurred",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
            details={"database": "biomapper.db", "host": "localhost"}
        )
        
        assert error.error_code == ErrorCode.DATABASE_CONNECTION_ERROR
        assert isinstance(error, BiomapperError)
    
    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        details = {"host": "db.example.com", "port": 5432, "database": "biomapper"}
        error = DatabaseConnectionError("Failed to connect to database", details=details)
        
        assert error.error_code == ErrorCode.DATABASE_CONNECTION_ERROR
        assert isinstance(error, DatabaseError)
        assert isinstance(error, BiomapperError)
    
    def test_database_query_error(self):
        """Test DatabaseQueryError."""
        details = {"query": "SELECT * FROM mappings", "error": "syntax_error"}
        error = DatabaseQueryError("Database query failed", details=details)
        
        assert error.error_code == ErrorCode.DATABASE_QUERY_ERROR
        assert isinstance(error, DatabaseError)
        assert isinstance(error, BiomapperError)
    
    def test_database_transaction_error(self):
        """Test DatabaseTransactionError."""
        details = {"transaction_id": "tx_789", "operation": "rollback"}
        error = DatabaseTransactionError("Database transaction failed", details=details)
        
        assert error.error_code == ErrorCode.DATABASE_TRANSACTION_ERROR
        assert isinstance(error, DatabaseError)
        assert isinstance(error, BiomapperError)


class TestErrorSerialization:
    """Test error serialization and deserialization."""
    
    def test_error_context_preservation(self):
        """Test error context is preserved through string conversion."""
        details = {
            "biological_context": {
                "source_type": "protein",
                "target_type": "metabolite",
                "identifiers": ["P12345", "HMDB0000001"]
            },
            "execution_context": {
                "strategy": "multi_omics_integration",
                "step": "cross_reference_mapping"
            }
        }
        
        error = MappingExecutionError("Complex mapping failed", details=details)
        error_str = str(error)
        
        # Check that important context is preserved in string
        assert "biological_context" in error_str
        assert "execution_context" in error_str
        assert "P12345" in error_str
        assert "multi_omics_integration" in error_str
    
    def test_error_stack_trace_preservation(self):
        """Test error stack trace preservation."""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            details = {"original_error": str(e), "error_type": type(e).__name__}
            biomapper_error = ProcessingError("Wrapped error", details=details)
            
            assert biomapper_error.details["original_error"] == "Original error"
            assert biomapper_error.details["error_type"] == "ValueError"
    
    def test_nested_exception_handling(self):
        """Test handling of nested exceptions."""
        try:
            try:
                raise ConnectionError("Network timeout")
            except ConnectionError:
                raise ClientExecutionError(
                    "API client failed",
                    client_name="MetaboliteAPI",
                    details={"operation": "fetch_metabolite_data"}
                )
        except ClientExecutionError as e:
            assert e.client_name == "MetaboliteAPI"
            assert e.error_code == ErrorCode.CLIENT_EXECUTION_ERROR
            assert "fetch_metabolite_data" in str(e)


class TestErrorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_large_details(self):
        """Test error with very large details dictionary."""
        large_details = {
            f"protein_{i}": f"P{str(i).zfill(5)}" 
            for i in range(1000)
        }
        large_details["description"] = "Large protein dataset mapping error"
        
        error = MappingExecutionError("Large dataset error", details=large_details)
        
        assert len(error.details) == 1001  # 1000 proteins + description
        assert error.details["protein_0"] == "P00000"
        assert error.details["description"] == "Large protein dataset mapping error"
    
    def test_unicode_in_error_messages(self):
        """Test error messages with unicode characters."""
        details = {
            "protein_name": "α-synuclein",
            "metabolite_name": "β-alanine",
            "pathway": "γ-aminobutyric acid metabolism"
        }
        
        error = BiomapperError("Unicode test: αβγδε", details=details)
        error_str = str(error)
        
        assert "α-synuclein" in error_str
        assert "β-alanine" in error_str
        assert "γ-aminobutyric" in error_str
    
    def test_none_and_empty_values_in_details(self):
        """Test error with None and empty values in details."""
        details = {
            "none_value": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "valid_value": "test"
        }
        
        error = BiomapperError("Test with empty values", details=details)
        error_str = str(error)
        
        # Should handle all value types gracefully
        assert "none_value=None" in error_str
        assert "empty_string=" in error_str
        assert "valid_value=test" in error_str
    
    def test_circular_reference_in_details(self):
        """Test error with circular references in details."""
        details = {"key1": "value1"}
        details["self_reference"] = details  # Create circular reference
        
        # Should not cause infinite recursion in string conversion
        error = BiomapperError("Circular reference test", details=details)
        error_str = str(error)
        
        # Basic functionality should still work
        assert "key1=value1" in error_str
        assert "UNKNOWN_ERROR" in error_str
    
    def test_complex_nested_details(self):
        """Test error with deeply nested details."""
        details = {
            "mapping": {
                "proteins": {
                    "uniprot": {
                        "P12345": {
                            "gene_name": "TP53",
                            "interactions": ["Q9Y6R4", "O15552"]
                        }
                    }
                },
                "metabolites": {
                    "hmdb": {
                        "HMDB0000001": {
                            "name": "1-Methylhistidine",
                            "pathways": ["histidine_metabolism"]
                        }
                    }
                }
            }
        }
        
        error = TransformationError("Complex nested data error", details=details)
        error_str = str(error)
        
        # Should handle nested structures
        assert "mapping=" in error_str
        assert isinstance(error.details, dict)
        assert error.details["mapping"]["proteins"]["uniprot"]["P12345"]["gene_name"] == "TP53"