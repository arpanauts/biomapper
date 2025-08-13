Contributing to BioMapper
==========================

Thank you for your interest in contributing to BioMapper! This guide will help you get started.

Getting Started
---------------

1. **Fork the Repository**

   .. code-block:: bash
   
      # Fork on GitHub, then clone
      git clone https://github.com/YOUR_USERNAME/biomapper.git
      cd biomapper
      git remote add upstream https://github.com/biomapper/biomapper.git

2. **Set Up Development Environment**

   .. code-block:: bash
   
      # Install Poetry
      curl -sSL https://install.python-poetry.org | python3 -
      
      # Install dependencies
      poetry install --with dev,docs,api
      
      # Activate environment
      poetry shell
      
      # Install pre-commit hooks
      pre-commit install

3. **Create Feature Branch**

   .. code-block:: bash
   
      git checkout -b feature/your-feature-name
      # or
      git checkout -b fix/issue-description

Development Workflow
--------------------

1. Write Tests First (TDD)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/unit/test_new_feature.py
   def test_new_feature():
       """Test the new feature."""
       result = new_feature(input_data)
       assert result == expected_output

2. Implement Feature
~~~~~~~~~~~~~~~~~~~~

* Follow existing code patterns
* Add type hints
* Include docstrings
* Handle errors gracefully

3. Run Quality Checks
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Format code
   poetry run ruff format .
   
   # Fix linting issues
   poetry run ruff check . --fix
   
   # Type checking
   poetry run mypy biomapper
   
   # Run tests
   poetry run pytest
   
   # Or run all checks
   make check

4. Update Documentation
~~~~~~~~~~~~~~~~~~~~~~~

* Update relevant .rst files in ``docs/source/``
* Add docstrings to new functions/classes
* Update README if needed

Code Standards
--------------

Python Style
~~~~~~~~~~~~

* Follow PEP 8
* Use ruff for formatting
* Maximum line length: 100 characters
* Use descriptive variable names

Type Hints
~~~~~~~~~~

All functions must have type hints:

.. code-block:: python

   from typing import Dict, List, Optional, Any
   
   def process_data(
       input_data: List[Dict[str, Any]],
       threshold: float = 0.8,
       output_key: Optional[str] = None
   ) -> Dict[str, Any]:
       """Process data with threshold filtering.
       
       Args:
           input_data: List of data items
           threshold: Filter threshold (0.0-1.0)
           output_key: Optional output key name
           
       Returns:
           Processed data dictionary
       """
       ...

Docstrings
~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def complex_function(param1: str, param2: int) -> bool:
       """
       Brief description of function.
       
       Longer description explaining the function's purpose,
       behavior, and any important details.
       
       Args:
           param1: Description of param1
           param2: Description of param2
           
       Returns:
           Description of return value
           
       Raises:
           ValueError: When param1 is empty
           TypeError: When param2 is not positive
           
       Example:
           >>> complex_function("test", 42)
           True
       """

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from biomapper.core.exceptions import ValidationError
   import logging
   
   logger = logging.getLogger(__name__)
   
   try:
       result = risky_operation()
   except ValidationError as e:
       logger.error(f"Validation failed: {e}")
       return ActionResult(success=False, message=str(e))
   except Exception as e:
       logger.exception("Unexpected error")
       return ActionResult(success=False, message="Internal error")

Creating New Actions
--------------------

See :doc:`creating_actions` for detailed guide. Quick checklist:

1. ✅ Write tests first
2. ✅ Inherit from ``TypedStrategyAction``
3. ✅ Use Pydantic for parameters
4. ✅ Add ``@register_action`` decorator
5. ✅ Handle errors gracefully
6. ✅ Update context appropriately
7. ✅ Add comprehensive docstrings
8. ✅ Place in correct directory

Testing Requirements
--------------------

* Minimum 80% code coverage
* All new features must have tests
* Test edge cases and error conditions
* Use pytest fixtures for common data
* Mock external dependencies

.. code-block:: bash

   # Run tests with coverage
   poetry run pytest --cov=biomapper --cov-report=term-missing

Commit Guidelines
-----------------

Commit Messages
~~~~~~~~~~~~~~~

Follow conventional commits:

.. code-block:: text

   feat: Add metabolite CTS bridge action
   
   - Implement Chemical Translation Service integration
   - Add retry logic for API calls
   - Include comprehensive error handling
   
   Closes #123

Types:

* ``feat``: New feature
* ``fix``: Bug fix
* ``docs``: Documentation changes
* ``style``: Code style changes
* ``refactor``: Code refactoring
* ``test``: Test additions/changes
* ``chore``: Maintenance tasks

Pull Request Process
--------------------

1. **Update Your Branch**

   .. code-block:: bash
   
      git fetch upstream
      git rebase upstream/main

2. **Create Pull Request**

   * Use descriptive title
   * Reference related issues
   * Include test results
   * Add screenshots if UI changes

3. **PR Template**

   .. code-block:: markdown
   
      ## Description
      Brief description of changes
      
      ## Type of Change
      - [ ] Bug fix
      - [ ] New feature
      - [ ] Breaking change
      - [ ] Documentation update
      
      ## Testing
      - [ ] Unit tests pass
      - [ ] Integration tests pass
      - [ ] Manual testing completed
      
      ## Checklist
      - [ ] Code follows style guidelines
      - [ ] Self-review completed
      - [ ] Documentation updated
      - [ ] Tests added/updated
      - [ ] All checks passing

4. **Address Review Comments**

   * Respond to all comments
   * Make requested changes
   * Re-request review when ready

Documentation
-------------

Building Docs
~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   poetry run make html
   open build/html/index.html

Writing Docs
~~~~~~~~~~~~

* Use reStructuredText (.rst) format
* Include code examples
* Add cross-references
* Keep it concise and clear

Project Structure
-----------------

Understanding the Layout
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   biomapper/
   ├── biomapper/           # Core library
   │   └── core/
   │       └── strategy_actions/  # Actions
   ├── biomapper-api/       # REST API
   ├── biomapper_client/    # Python client
   ├── tests/              # Test suite
   ├── docs/               # Documentation
   └── configs/            # YAML strategies

Where to Add Code
~~~~~~~~~~~~~~~~~

* New actions: ``biomapper/core/strategy_actions/``
* API endpoints: ``biomapper-api/app/api/routes/``
* Client methods: ``biomapper_client/client_v2.py``
* Tests: ``tests/unit/`` or ``tests/integration/``

Getting Help
------------

* **Issues**: Check existing issues or create new ones
* **Discussions**: Use GitHub Discussions for questions
* **Documentation**: Read ``CLAUDE.md`` for AI assistance
* **Discord**: Join our community (if available)

Code of Conduct
---------------

* Be respectful and inclusive
* Welcome newcomers
* Give constructive feedback
* Focus on what's best for the community
* Show empathy towards others

License
-------

By contributing, you agree that your contributions will be licensed under the MIT License.

Recognition
-----------

Contributors are recognized in:

* GitHub contributors page
* CONTRIBUTORS.md file
* Release notes

Thank You!
----------

Your contributions make BioMapper better for everyone. We appreciate your time and effort!