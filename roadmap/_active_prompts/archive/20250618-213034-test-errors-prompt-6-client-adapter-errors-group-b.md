# Task: Resolve Client & Adapter Errors - Group B (UniProt, KEGG, PubChem, RefMet, Translator, UMLS, UniChem)

## Objective
Address a wide range of errors (AttributeError, TypeError, AssertionError, KeyError, NameError, specific client exceptions) in tests for various external biomedical data clients, including UniProt, KEGG, PubChem, RefMet, Translator Name Resolver, UMLS, and UniChem.

## Affected Files/Modules
- `tests/mapping/clients/test_composite_gene_mapping.py` (UniProtNameClient)
- `tests/mapping/clients/uniprot/test_uniprot_mapping.py`
- `tests/mapping/clients/test_uniprot_historical_resolver_client.py`
- `tests/mapping/clients/test_kegg_client.py`
- `tests/mapping/clients/test_pubchem_client.py`
- `tests/mapping/clients/test_refmet_client.py`
- `tests/mapping/clients/test_translator_name_resolver_client.py`
- `tests/mapping/clients/test_umls_client.py`
- `tests/mapping/clients/test_unichem_client.py`

## Common Error(s)
- `AttributeError`: Object missing an expected attribute/method (e.g., `'UniProtNameClient' object has no attribute 'find_uniprot_ids_by_names'`, `'NoneType' object has no attribute 'close'`).
- `TypeError`: Incorrect argument types or usage (e.g., `UniProtIDMappingClient.__init__() got an unexpected keyword argument 'config'`).
- `AssertionError`: Test expectations not met (e.g., specific client errors not raised, return values differ, mock call counts incorrect).
- `KeyError`: Missing keys in dictionaries, often from API responses or test data (e.g., `'params'` in Translator client).
- `NameError`: Undefined variable or name (e.g., `name 'ClientInitializationError' is not defined` in UMLS client tests).
- Specific client exceptions (e.g., `biomapper.mapping.clients.pubchem_client.PubChemError`).

## Background/Context
This group of tests validates clients that interface with various external biomedical APIs. Such tests are prone to failures due to:
- Changes in the external APIs themselves (though mocks should mitigate this, mock contracts might become outdated).
- Internal refactoring of the client classes within Biomapper.
- Desynchronization between test logic/data and the current state of the client code.
- Issues with resource management (e.g., closing client sessions, as suggested by `'NoneType' object has no attribute 'close'`).

## Debugging Guidance/Hypotheses

**General Approach:**
- **One Client at a Time:** Tackle tests for each client systematically.
- **API Documentation (if necessary):** For external API related issues, briefly consulting the relevant API's documentation might clarify expected request/response formats if mocks seem incorrect.
- **Client Code Review:** Examine the `__init__` method, main mapping methods, and any resource management (e.g., `close()`) in the client class being tested.

**Specific Error Types:**
- **`AttributeError` (e.g., `find_uniprot_ids_by_names`, `close`):**
    - Verify method/attribute names in the client class. They might have been renamed or removed.
    - For `close` errors on `NoneType`, it suggests the client object itself might be `None` when `close` is called, possibly due to an earlier initialization failure or incorrect test logic.
- **`TypeError` (e.g., `unexpected keyword argument 'config'`):**
    - Check the client's `__init__` signature. The test might be passing outdated or incorrect arguments.
- **`AssertionError`:**
    - **Error Not Raised:** If a specific exception is expected but not raised, the error handling in the client might have changed, or the condition to trigger the error is not met by the test.
    - **Value Mismatch:** Compare expected vs. actual values. This could be due to changes in client logic, data processing, or mock return values.
    - **Mock Call Counts:** If mock call counts are off (e.g., `Expected '_fetch_uniprot_search_results' to have been called once. Called 2 times.`), trace the logic in the client to see why the mock is called differently than expected.
- **`KeyError` (e.g., `'params'`):**
    - Inspect the data structure (likely a dictionary from a mocked API response or internal processing) where the key is expected. The structure might have changed.
- **`NameError` (e.g., `ClientInitializationError`):**
    - Ensure all necessary exceptions and classes are imported in the test file or the client module itself.
- **Specific Client Exceptions (e.g., `PubChemError`):**
    - This indicates the client is correctly raising its specific error, but the test might not be expecting it or handling it as a failure. If the error *should* be caught and handled by the client or test, verify that logic. If the test is designed to *cause* this error, then the test itself might be failing for other reasons (e.g., an assertion after the expected error).

## Specific Error Examples
1.  `FAILED tests/mapping/clients/test_composite_gene_mapping.py::test_composite_gene_symbols - AttributeError: 'UniProtNameClient' object has no attribute 'find_uniprot_ids_by_names'`
2.  `FAILED tests/mapping/clients/uniprot/test_uniprot_mapping.py::test - TypeError: UniProtIDMappingClient.__init__() got an unexpected keyword argument 'config'`
3.  `FAILED tests/mapping/clients/test_kegg_client.py::TestKEGGClient::test_get_entity_by_id_error - AssertionError: KEGGError not raised`
4.  `FAILED tests/mapping/clients/test_pubchem_client.py::TestPubChemClient::test_search_by_name_no_results - biomapper.mapping.clients.pubchem_client.PubChemError: Search failed: API request failed: 404 Client Error: PUGREST.NotFound for url: ht...`
5.  `FAILED tests/mapping/clients/test_translator_name_resolver_client.py::test_lookup_entity_name - KeyError: 'params'`
6.  `FAILED tests/mapping/clients/test_umls_client.py::test_init - NameError: name 'ClientInitializationError' is not defined`
7.  `FAILED tests/mapping/clients/test_unichem_client.py::test_close - AttributeError: 'NoneType' object has no attribute 'close'`

## Acceptance Criteria
- All tests in the listed 'Affected Files/Modules' for these clients pass successfully.
- Client initialization, method calls, error handling, and resource management are correctly tested and functioning.
- Test assertions, mock configurations, and expected data structures are aligned with the current implementations of the respective client classes.
