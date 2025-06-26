# Task 3: Implement and Test `ApiResolver` Strategy Action

**Source Prompt Reference:** This task is part of recreating the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Implement a new, reusable `ApiResolver` strategy action. This action will be responsible for resolving historical or deprecated identifiers by querying an external API, such as UniProt. This replaces the legacy `RESOLVE_UNIPROT_HISTORY_VIA_API` path.

## 2. Service Architecture Context
- **Primary Service:** `biomapper` (core library)
- **Affected Module:** A new file, `biomapper.core.strategy_actions.api_resolver`
- **Service Dependencies:** This action will make external network requests.

## 3. Task Decomposition
1.  **Design Action Interface:** Define the parameters the action will take. This should include the input context key, output context key, the base URL of the API, and any necessary request parameters.
2.  **Implement Core Logic:** Use a robust HTTP client like `httpx` to make asynchronous requests to the external API. Implement logic to handle batching, rate limiting, and retries to ensure the action is resilient.
3.  **Add Unit Tests:** Create unit tests in `tests/unit/strategy_actions/`. Use a mocking library (like `pytest-mock` or `respx`) to mock the external API calls, allowing you to test the action's logic without making real network requests. Test for success cases, API errors, and network failures.
4.  **Register the Action:** Register the new action as `API_RESOLVER` using the `@register_action` decorator.
5.  **Add Documentation:** Write a comprehensive docstring explaining the action's purpose, its parameters, and an example of how to configure it in a strategy YAML for resolving UniProt IDs.

## 4. Implementation Requirements
- **New Action File:** `/home/trentleslie/github/biomapper/biomapper/core/strategy_actions/api_resolver.py`
- **New Test File:** `/home/trentleslie/github/biomapper/tests/unit/strategy_actions/test_api_resolver.py`
- The action must handle API errors gracefully.
- The action must produce provenance data, including the API endpoint queried.

## 5. Success Criteria and Validation
- [ ] The new action is implemented and registered.
- [ ] Unit tests achieve 100% code coverage.
- [ ] The action is documented with a clear docstring and usage example.
- [ ] The implementation is clean, follows project coding standards, and is free of linting errors.
