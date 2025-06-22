# Prompt: Final Troubleshooting and Cleanup of `mapping_executor.py`

**Objective:** Perform a definitive fix of `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`. The file has been left in a corrupted state after multiple failed refactoring attempts. The goal is to resolve all syntax errors, logical inconsistencies, and linting issues, restoring it to a clean, functional state.

**Context:** The `MappingExecutor` is intended to be a lean facade that delegates complex operations to a suite of specialized services. However, a series of incorrect edits have introduced severe syntax errors and logical flaws, particularly within the `__init__` method. This prompt provides the known-good code blocks required to repair the file.

**File to be Modified:**

*   `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

--- 

### **Task 1: Replace the Entire `__init__` Method**

The current `__init__` method is the primary source of errors. It has incorrect service initialization ordering and contains stray code fragments causing fatal syntax errors. 

**Action:** Replace the entire existing `__init__` method (from `def __init__(...):` to the last line of the method) with the following correct implementation. This version ensures all services are initialized in the correct dependency order.

```python
def __init__(
    self,
    metamapper_db_url: Optional[str] = None,
    mapping_cache_db_url: Optional[str] = None,
    echo_sql: bool = False,
    path_cache_size: int = 100,
    path_cache_expiry_seconds: int = 300,
    max_concurrent_batches: int = 5,
    enable_metrics: bool = True,
    checkpoint_enabled: bool = False,
    checkpoint_dir: Optional[str] = None,
    batch_size: int = 100,
    max_retries: int = 3,
    retry_delay: int = 5,
    # Pre-initialized components (new style)
    session_manager=None,
    client_manager=None,
    config_loader=None,
    strategy_handler=None,
    path_finder=None,
    path_execution_manager=None,
    cache_manager=None,
    identifier_loader=None,
    strategy_orchestrator=None,
    checkpoint_manager=None,
    progress_reporter=None,
    langfuse_tracker=None,
):
    """
    Initializes the MappingExecutor as a lean facade.
    All component initialization is delegated to InitializationService.
    """
    super().__init__()
    self.logger = logging.getLogger(__name__)

    # Use InitializationService to initialize all components
    initialization_service = InitializationService()
    components = initialization_service.initialize_components(
        self,
        metamapper_db_url=metamapper_db_url,
        mapping_cache_db_url=mapping_cache_db_url,
        echo_sql=echo_sql,
        path_cache_size=path_cache_size,
        path_cache_expiry_seconds=path_cache_expiry_seconds,
        max_concurrent_batches=max_concurrent_batches,
        enable_metrics=enable_metrics,
        checkpoint_enabled=checkpoint_enabled,
        checkpoint_dir=checkpoint_dir,
        batch_size=batch_size,
        max_retries=max_retries,
        retry_delay=retry_delay,
        session_manager=session_manager,
        client_manager=client_manager,
        config_loader=config_loader,
        strategy_handler=strategy_handler,
        path_finder=path_finder,
        path_execution_manager=path_execution_manager,
        cache_manager=cache_manager,
        identifier_loader=identifier_loader,
        strategy_orchestrator=strategy_orchestrator,
        checkpoint_manager=checkpoint_manager,
        progress_reporter=progress_reporter,
        langfuse_tracker=langfuse_tracker,
    )

    # Assign all components from the initialization service to self
    for key, value in components.items():
        setattr(self, key, value)

    # Initialize the execution services first, as coordinators depend on them.
    self.result_aggregation_service = ResultAggregationService(logger=self.logger)
    
    self.iterative_execution_service = IterativeExecutionService(
        direct_mapping_service=self.direct_mapping_service,
        iterative_mapping_service=self.iterative_mapping_service,
        bidirectional_validation_service=self.bidirectional_validation_service,
        result_aggregation_service=self.result_aggregation_service,
        path_finder=self.path_finder,
        composite_handler=self._composite_handler,
        async_metamapper_session=self.async_metamapper_session,
        metadata_query_service=self.metadata_query_service,
        logger=self.logger,
    )
    
    self.db_strategy_execution_service = DbStrategyExecutionService(
        strategy_execution_service=self.strategy_execution_service,
        logger=self.logger,
    )
    
    self.yaml_strategy_execution_service = YamlStrategyExecutionService(
        strategy_orchestrator=self.strategy_orchestrator,
        logger=self.logger,
    )

    # Now, initialize Coordinator and Manager services that compose other services
    self.strategy_coordinator = StrategyCoordinatorService(
        db_strategy_execution_service=self.db_strategy_execution_service,
        yaml_strategy_execution_service=self.yaml_strategy_execution_service,
        robust_execution_coordinator=self.robust_execution_coordinator,
        logger=self.logger
    )

    self.mapping_coordinator = MappingCoordinatorService(
        iterative_execution_service=self.iterative_execution_service,
        path_execution_service=self.path_execution_service,
        logger=self.logger
    )

    self.lifecycle_manager = LifecycleManager(
        session_manager=self.session_manager,
        execution_lifecycle_service=self.lifecycle_service,
        client_manager=self.client_manager,
        cache_manager=self.cache_manager,
        path_finder=self.path_finder,
        path_execution_manager=self.path_execution_manager,
        composite_handler=self,  # MappingExecutor implements composite handling
        step_execution_service=self.step_execution_service,
        logger=self.logger
    )

    # Set executor reference for services that need it for callbacks/delegation
    self.path_execution_service.set_executor(self)
    self.iterative_execution_service.set_executor(self)

    self.logger.info("MappingExecutor initialization complete")
```

--- 

### **Task 2: Fix the `execute_mapping` Method**

The `execute_mapping` method also contains duplicated and malformed code.

**Action:** Replace the entire `execute_mapping` method with this clean, correct version.

```python
    async def execute_mapping(
        self,
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: Optional[List[str]] = None,
        input_data: Optional[List[Dict[str, Any]]] = None,
        source_property_name: str = 'id',
        target_property_name: str = 'id',
        source_ontology_type: Optional[str] = None,
        target_ontology_type: Optional[str] = None,
        use_cache: bool = True,
        max_cache_age_days: Optional[int] = None,
        mapping_direction: str = 'forward',
        try_reverse_mapping: bool = True,
        validate_bidirectional: bool = False,
        progress_callback: Optional[Callable] = None,
        batch_size: int = 100,
        max_concurrent_batches: int = 5,
        max_hop_count: int = 5,
        min_confidence: float = 0.0,
        enable_metrics: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a complete mapping workflow from source to target.

        This method now delegates entirely to the MappingCoordinatorService.
        """
        return await self.mapping_coordinator.execute_mapping(
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_identifiers=input_identifiers,
            input_data=input_data,
            source_property_name=source_property_name,
            target_property_name=target_property_name,
            source_ontology_type=source_ontology_type,
            target_ontology_type=target_ontology_type,
            use_cache=use_cache,
            max_cache_age_days=max_cache_age_days,
            mapping_direction=mapping_direction,
            try_reverse_mapping=try_reverse_mapping,
            validate_bidirectional=validate_bidirectional,
            progress_callback=progress_callback,
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
            max_hop_count=max_hop_count,
            min_confidence=min_confidence,
            enable_metrics=enable_metrics
        )
```

--- 

### **Task 3: Final Review and Linting**

After applying the fixes above, the major syntax errors should be resolved. A final pass is needed to catch any remaining issues.

**Action:**
1.  Review the entire file for any residual syntax errors or indentation problems that may have been missed.
2.  Remove any unused imports at the top of the file.
3.  Ensure consistent formatting throughout the file.

### **Success Criteria:**

*   The file `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` is completely free of syntax errors and can be imported without issues.
*   The `MappingExecutor` class correctly initializes and delegates its methods as intended.
*   The code is clean, well-formatted, and free of linting errors.
