# Task: Create Unit Tests for `ConfigLoader`

## Objective
To ensure the reliability of the strategy configuration loading mechanism, create a suite of unit tests for the `ConfigLoader` component.

## Location for Tests
Create a new test file: `tests/core/engine_components/test_config_loader.py`

## Test Strategy
- Use `pytest` and `unittest.mock` for testing.
- Mock filesystem interactions (`open`, `os.path.exists`) to simulate the presence, absence, and content of YAML configuration files without needing real files.

## Test Cases

1.  **Test Successful Loading (.yaml):**
    - Mock a valid `strategy.yaml` file.
    - Call `load_strategy` and assert that the returned dictionary matches the mock file's content.

2.  **Test Successful Loading (.yml fallback):**
    - Mock `os.path.exists` to return `False` for `strategy.yaml` but `True` for `strategy.yml`.
    - Assert that `load_strategy` successfully loads from the `.yml` file.

3.  **Test Strategy Not Found:**
    - Mock `os.path.exists` to return `False` for both `.yaml` and `.yml` files.
    - Assert that `load_strategy` raises a `ConfigurationError`.

4.  **Test Malformed YAML:**
    - Mock the content of a YAML file to be invalid (e.g., incorrect indentation).
    - Assert that `load_strategy` catches the `yaml.YAMLError` and raises a `ConfigurationError`.

5.  **Test Invalid Config Format:**
    - Mock a YAML file whose root element is not a dictionary (e.g., a list).
    - Assert that `load_strategy` raises a `ConfigurationError`.

6.  **Test Name Injection:**
    - Mock a valid strategy config that is missing the top-level `name` key.
    - Call `load_strategy` and assert that the strategy name is correctly added to the resulting dictionary.

## Acceptance Criteria
- A new test file `tests/core/engine_components/test_config_loader.py` is created.
- The tests cover all public methods of the `ConfigLoader` class and its primary error conditions.
- All tests pass successfully.
