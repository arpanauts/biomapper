# Task: Create Unit Tests for `CheckpointManager`

## Objective
To ensure the reliability of the `CheckpointManager` class, create comprehensive unit tests. This task focuses specifically on the `CheckpointManager` component.

## Location for Tests
Add tests to the file: `tests/core/engine_components/test_managers.py`
(Create this file if it doesn't exist, or add to it if `ClientManager` tests are already present).

## `CheckpointManager` Test Cases

Use `pytest`'s `tmp_path` fixture to create temporary directories for testing file operations.

1.  **Test Save Checkpoint**: Verify that `save_checkpoint` correctly creates a JSON file in the specified checkpoint directory with the expected content.
2.  **Test Load Checkpoint**: Save a checkpoint, then use `load_checkpoint` to read it back and assert that the loaded data matches the original data.
3.  **Test Clear Checkpoint**: Verify that `clear_checkpoint` successfully deletes the checkpoint file.
4.  **Test Load Non-existent Checkpoint**: Assert that `load_checkpoint` returns `None` or handles the case gracefully (e.g., by raising a specific, documented error or logging a warning and returning None) when no checkpoint file exists.
5.  **Test Checkpoint Directory Creation**: Ensure the `CheckpointManager` automatically creates the checkpoint directory (e.g., `~/.biomapper/checkpoints/`) if it does not exist when a checkpoint is saved.

## Acceptance Criteria
*   Unit tests for `CheckpointManager` are implemented in `tests/core/engine_components/test_managers.py`.
*   The test suite achieves high code coverage for `biomapper/core/engine_components/checkpoint_manager.py`.
*   All `CheckpointManager` tests pass successfully.
