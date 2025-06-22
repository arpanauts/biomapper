# Task: Integrate DatabaseSetupService into the Builder

**Task Objective:**
Integrate the database table initialization logic, currently handled by `DatabaseSetupService` as a separate step in `MappingExecutor.create`, into the main `MappingExecutorBuilder` workflow. The goal is that a successfully built executor is guaranteed to have its required database tables initialized.

**Prerequisites:**
- The `MappingExecutorBuilder` has been created (as per `prompt-2-create-builder.md`).
- The `DatabaseSetupService` exists at `/home/ubuntu/biomapper/biomapper/core/services/database_setup_service.py`.

**Input Context:**
- `/home/ubuntu/biomapper/biomapper/core/engine_components/mapping_executor_builder.py`: The builder to be modified.
- `/home/ubuntu/biomapper/biomapper/core/services/database_setup_service.py`: The service whose logic needs to be integrated.
- `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`: The `create` method here shows the current, separate invocation of the setup service.

**Expected Outputs:**
1.  The `MappingExecutorBuilder`'s `build` method (or a new `async_build` method) will be responsible for invoking the `DatabaseSetupService` to initialize both the metamapper and cache database tables.
2.  The `MappingExecutor.create` method will be simplified, as it will no longer need to call the `DatabaseSetupService` itself.
3.  The `DatabaseSetupService` might be absorbed into the builder or `InitializationService` if its logic is simple enough, or it will be instantiated and used within the builder.

**Success Criteria:**
- Creating a `MappingExecutor` via the builder results in an instance that can immediately interact with its databases because the tables have already been created.
- The database setup logic is no longer a separate, manual step in the `create` method.
- All tests related to database interaction and executor creation pass.

**Error Recovery Instructions:**
- If making the `build` method async is problematic, create a separate `async_build` method on the builder and leave the synchronous `build` for testing scenarios that use mock databases.
- If the database service requires the `AsyncEngine`, ensure it's created first within the builder's workflow before the setup service is called.

**Environment Requirements:**
- Access to the `biomapper` codebase.
- `poetry` environment fully installed and operational.

**Task Decomposition:**
1.  Analyze `MappingExecutor.create` to understand how `DatabaseSetupService` is currently used.
2.  Modify `MappingExecutorBuilder`. Decide whether to add the logic to the existing `build` method (making it async) or create a new `async_build` method.
3.  Inside the chosen build method, instantiate `DatabaseSetupService`.
4.  Call the `initialize_tables` method for both the metamapper and cache databases using the engines created by the `InitializationService`.
5.  Remove the database setup logic from `MappingExecutor.create`, simplifying it to just use the builder.
6.  Review and update unit tests to ensure they account for this change. Tests might need to mock the `DatabaseSetupService` call.
7.  Run the full test suite.

**Validation Checkpoints:**
- After modifying the builder, write a test to ensure that the `initialize_tables` method on `DatabaseSetupService` is called during the build process.
- After simplifying `MappingExecutor.create`, run tests that use it to ensure they still work.

**Source Prompt Reference:**
- `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-204511-prompt-6-integrate-db-setup.md`

**Context from Previous Attempts:**
- This is the first attempt to integrate the database setup into the builder.
