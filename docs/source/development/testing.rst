Testing Guide
=============

BioMapper follows Test-Driven Development (TDD) practices with comprehensive test coverage.

Test Organization
-----------------

.. code-block:: text

   tests/
   ├── unit/                    # Unit tests (fast, isolated)
   │   ├── actions/             # Action tests
   │   ├── core/                # Core library tests
   │   └── api/                 # API unit tests
   ├── integration/             # Integration tests (slower)
   │   └── strategies/          # Strategy execution tests
   ├── performance/             # Performance benchmarks
   ├── fixtures/                # Test data and fixtures
   ├── mocks/                   # Mock objects and utilities
   └── conftest.py              # Shared pytest fixtures

Running Tests
-------------

Basic Commands
~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   poetry run pytest
   
   # Run with coverage
   poetry run pytest --cov=biomapper --cov-report=html
   
   # Run specific test file
   poetry run pytest tests/unit/actions/test_my_action.py
   
   # Run tests matching pattern
   poetry run pytest -k "test_protein"
   
   # Run with verbose output
   poetry run pytest -xvs
   
   # Run and stop on first failure
   poetry run pytest -x
   
   # Run with debugging
   poetry run pytest --pdb

Test Categories
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Unit tests only (fast)
   poetry run pytest tests/unit/
   
   # Integration tests (slower)
   poetry run pytest tests/integration/
   
   # API tests
   poetry run pytest tests/api/
   
   # Specific action tests
   poetry run pytest tests/unit/actions/entities/proteins/

Writing Unit Tests
------------------

Basic Test Structure
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   from biomapper.actions.my_action import MyAction, MyActionParams
   
   class TestMyAction:
       """Test suite for MyAction."""
       
       @pytest.fixture
       def sample_context(self):
           """Provide sample execution context."""
           return {
               "datasets": {
                   "test_data": [
                       {"id": "1", "name": "Sample1"},
                       {"id": "2", "name": "Sample2"}
                   ]
               }
           }
       
       @pytest.mark.asyncio
       async def test_basic_functionality(self, sample_context):
           """Test basic action execution."""
           # Arrange
           params = MyActionParams(
               input_key="test_data",
               output_key="processed"
           )
           
           # Act
           action = MyAction()
           result = await action.execute_typed(
               current_identifiers=[],
               current_ontology_type="",
               params=params,
               source_endpoint=None,
               target_endpoint=None,
               context=sample_context
           )
           
           # Assert
           assert result.success
           assert "processed" in sample_context["datasets"]
           assert len(sample_context["datasets"]["processed"]) == 2

Testing Parameters
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pydantic import ValidationError
   
   def test_parameter_validation():
       """Test parameter validation."""
       # Valid parameters
       params = MyActionParams(
           input_key="data",
           threshold=0.5
       )
       assert params.threshold == 0.5
       
       # Invalid threshold (out of range)
       with pytest.raises(ValidationError) as exc_info:
           MyActionParams(
               input_key="data",
               threshold=1.5  # > 1.0
           )
       assert "threshold" in str(exc_info.value)
       
       # Missing required field
       with pytest.raises(ValidationError):
           MyActionParams()  # input_key is required

Testing Error Handling
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.asyncio
   async def test_missing_input_key():
       """Test handling of missing input data."""
       params = MyActionParams(input_key="missing", output_key="output")
       context = {"datasets": {}}
       
       action = MyAction()
       result = await action.execute_typed(
           current_identifiers=[],
           current_ontology_type="",
           params=params,
           source_endpoint=None,
           target_endpoint=None,
           context=context
       )
       
       assert not result.success
       assert "not found" in result.message.lower()
   
   @pytest.mark.asyncio
   async def test_empty_dataset():
       """Test handling of empty dataset."""
       params = MyActionParams(input_key="empty", output_key="output")
       context = {"datasets": {"empty": []}}
       
       action = MyAction()
       result = await action.execute_typed(
           current_identifiers=[],
           current_ontology_type="",
           params=params,
           source_endpoint=None,
           target_endpoint=None,
           context=context
       )
       
       assert result.success  # Should handle gracefully
       assert context["datasets"][params.output_key] == []

Writing Integration Tests
-------------------------

Strategy Execution Test
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/integration/strategies/test_protein_workflow.py
   import pytest
   from biomapper.api.services.strategy_execution_service import StrategyExecutionService
   
   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_protein_harmonization_workflow():
       """Test complete protein harmonization workflow."""
       # Load test strategy
       service = StrategyExecutionService()
       strategy = {
           "name": "test_protein_workflow",
           "steps": [
               {
                   "name": "load",
                   "action": {
                       "type": "LOAD_DATASET_IDENTIFIERS",
                       "params": {
                           "file_path": "tests/fixtures/proteins.csv",
                           "identifier_column": "uniprot",
                           "output_key": "proteins"
                       }
                   }
               },
               {
                   "name": "normalize",
                   "action": {
                       "type": "PROTEIN_NORMALIZE_ACCESSIONS",
                       "params": {
                           "input_key": "proteins",
                           "output_key": "normalized"
                       }
                   }
               }
           ]
       }
       
       # Execute strategy
       result = await service.execute_strategy(strategy)
       
       # Verify results
       assert result["success"]
       assert "normalized" in result["datasets"]
       assert len(result["datasets"]["normalized"]) > 0

API Integration Test
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/integration/api/test_strategy_execution.py
   import pytest
   from fastapi.testclient import TestClient
   from app.main import app
   
   @pytest.mark.integration
   def test_execute_strategy_endpoint():
       """Test strategy execution via API."""
       client = TestClient(app)
       
       # Submit strategy
       response = client.post(
           "/api/v2/strategies/execute",
           json={
               "strategy_name": "test_strategy",
               "parameters": {
                   "input_file": "/test/data.csv"
               }
           }
       )
       
       assert response.status_code == 201
       job_id = response.json()["job_id"]
       
       # Check job status
       response = client.get(f"/api/v2/jobs/{job_id}")
       assert response.status_code == 200
       assert response.json()["status"] in ["running", "completed"]

Test Fixtures
-------------

Shared Fixtures
~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/conftest.py
   import pytest
   import tempfile
   from pathlib import Path
   
   @pytest.fixture
   def temp_dir():
       """Provide temporary directory for tests."""
       with tempfile.TemporaryDirectory() as tmpdir:
           yield Path(tmpdir)
   
   @pytest.fixture
   def sample_protein_data():
       """Sample protein dataset."""
       return [
           {"uniprot": "P12345", "gene": "GENE1"},
           {"uniprot": "Q67890", "gene": "GENE2"},
           {"uniprot": "O54321", "gene": "GENE3"}
       ]
   
   @pytest.fixture
   def mock_api_client(mocker):
       """Mock API client for testing."""
       client = mocker.Mock()
       client.execute_strategy.return_value = {
           "success": True,
           "job_id": "test_job_123"
       }
       return client

Test Data Files
~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/fixtures/proteins.csv
   """
   uniprot,gene_symbol,description
   P12345,GENE1,Sample protein 1
   Q67890,GENE2,Sample protein 2
   O54321,GENE3,Sample protein 3
   """
   
   # tests/fixtures/metabolites.json
   {
       "compounds": [
           {"hmdb": "HMDB0000001", "name": "1-Methylhistidine"},
           {"hmdb": "HMDB0000002", "name": "1,3-Diaminopropane"}
       ]
   }

Mocking External Services
-------------------------

Mocking API Calls
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   from unittest.mock import patch, Mock
   
   @pytest.mark.asyncio
   async def test_cts_api_call():
       """Test CTS API integration with mock."""
       with patch('requests.get') as mock_get:
           # Setup mock response
           mock_response = Mock()
           mock_response.json.return_value = {
               "results": [{"inchikey": "XXXXX-YYYYY-Z"}]
           }
           mock_response.status_code = 200
           mock_get.return_value = mock_response
           
           # Execute action
           action = CTSBridgeAction()
           result = await action.execute_typed(params, context)
           
           # Verify API was called
           mock_get.assert_called_once()
           assert result.success

Mocking File System
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from unittest.mock import mock_open, patch
   
   def test_file_loading():
       """Test file loading with mock."""
       mock_data = "id,name\n1,test\n2,sample"
       
       with patch("builtins.open", mock_open(read_data=mock_data)):
           action = LoadDatasetAction()
           result = action.load_file("/fake/path.csv")
           
           assert len(result) == 2
           assert result[0]["name"] == "test"

Coverage Requirements
---------------------

Minimum Coverage
~~~~~~~~~~~~~~~~

* Overall: 80%
* Core actions: 90%
* API endpoints: 85%
* Utilities: 75%

Check Coverage
~~~~~~~~~~~~~~

.. code-block:: bash

   # Generate coverage report
   poetry run pytest --cov=biomapper --cov-report=html
   
   # View HTML report
   open htmlcov/index.html
   
   # Show coverage in terminal
   poetry run pytest --cov=biomapper --cov-report=term-missing

Continuous Integration
----------------------

GitHub Actions
~~~~~~~~~~~~~~

.. code-block:: yaml

   # .github/workflows/test.yml
   name: Tests
   
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: "3.11"
         - name: Install Poetry
           run: pip install poetry
         - name: Install dependencies
           run: poetry install --with dev
         - name: Run tests
           run: poetry run pytest --cov
         - name: Upload coverage
           uses: codecov/codecov-action@v3

Performance Testing
-------------------

Benchmark Tests
~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   import time
   
   @pytest.mark.benchmark
   def test_large_dataset_performance():
       """Test performance with large dataset."""
       # Create large dataset
       large_data = [{"id": i} for i in range(100000)]
       context = {"datasets": {"large": large_data}}
       
       # Measure execution time
       start = time.time()
       result = action.execute_typed(params, context)
       elapsed = time.time() - start
       
       assert elapsed < 5.0  # Should complete in 5 seconds
       assert result.success

Load Testing
~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import aiohttp
   
   async def load_test_api():
       """Load test API endpoints."""
       async with aiohttp.ClientSession() as session:
           tasks = []
           for i in range(100):
               task = session.post(
                   "http://localhost:8000/api/v2/strategies/execute",
                   json={"strategy_name": "test"}
               )
               tasks.append(task)
           
           responses = await asyncio.gather(*tasks)
           success_count = sum(1 for r in responses if r.status == 201)
           
           assert success_count > 95  # 95% success rate

Best Practices
--------------

1. **Write Tests First** - Follow TDD methodology
2. **Test Edge Cases** - Empty data, missing fields, invalid inputs
3. **Use Fixtures** - Share common test data
4. **Mock External Dependencies** - Don't rely on external services
5. **Keep Tests Fast** - Unit tests should run quickly
6. **Test One Thing** - Each test should verify one behavior
7. **Clear Test Names** - Describe what is being tested
8. **Use Markers** - Mark slow tests, integration tests
9. **Clean Up** - Remove temp files, close connections
10. **Document Complex Tests** - Add comments for complex logic

---

Verification Sources
--------------------

*Last verified: 2025-08-17*

This documentation was verified against the following project resources:

- ``/biomapper/tests/`` (current test directory structure with unit, integration, performance subdirectories)
- ``/biomapper/tests/conftest.py`` (shared pytest fixtures)
- ``/biomapper/pyproject.toml`` (pytest and coverage dependencies)
- ``/biomapper/CLAUDE.md`` (TDD approach and test commands)
- ``/biomapper/src/actions/typed_base.py`` (execute_typed method signature with StrategyExecutionContext)
- ``/biomapper/src/api/services/`` (strategy execution service for integration tests)