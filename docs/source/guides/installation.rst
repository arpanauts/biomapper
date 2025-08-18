Installation Guide
==================

Detailed installation instructions for different environments.

System Requirements
-------------------

* Python 3.11 or higher
* Poetry package manager
* Git

Development Installation
------------------------

For developers wanting to contribute or modify Biomapper:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/arpanauts/biomapper.git
    cd biomapper
    
    # Install Poetry if not already installed
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Install all dependencies including dev tools
    poetry install --with dev,docs,api
    
    # Activate the virtual environment
    poetry shell
    
    # Verify installation
    poetry run pytest tests/unit/

Production Installation  
-----------------------

For production use (API server only):

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/arpanauts/biomapper.git
    cd biomapper
    
    # Install only runtime dependencies
    poetry install --with api
    
    # Start the API server directly from project root
    poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
    
    # API will be available at http://localhost:8000/api/docs

Docker Installation
-------------------

Docker support is available for CI/testing purposes:

.. code-block:: bash

    # Build the CI testing image
    docker build -f Dockerfile.ci -t biomapper-ci:latest .
    
    # Run tests in Docker environment
    docker run biomapper-ci:latest poetry run pytest

*Note: Production Docker deployment with docker-compose is under development.*

CLI Installation
----------------

Install the Biomapper CLI tool:

.. code-block:: bash

    # Install the CLI
    poetry install
    
    # Verify CLI installation
    poetry run biomapper --help
    poetry run biomapper health
    poetry run biomapper test-import
    poetry run biomapper strategies

Troubleshooting
---------------

**Poetry not found**
  Install Poetry using the official installer:
  ``curl -sSL https://install.python-poetry.org | python3 -``

**Python version issues**  
  Ensure Python 3.11+ is installed. Check with ``python3 --version``

**Permission errors**
  Run installation commands with appropriate permissions for your system.

**ChromaDB installation issues**
  ChromaDB may require system dependencies. Install with:
  ``sudo apt-get install build-essential`` (Ubuntu/Debian)
  ``brew install gcc`` (macOS)

**Import errors**
  Ensure you're in the Poetry virtual environment:
  ``poetry shell``

---

.. note::
   **Verification Sources** (*Last verified: 2025-01-17*)

   This documentation was verified against the following project resources:

   - ``/biomapper/pyproject.toml`` (Python 3.11+ requirement, Poetry dependencies and groups)
   - ``/biomapper/CLAUDE.md`` (essential installation commands and environment setup)
   - ``/biomapper/Makefile`` (make test, make format, make lint-fix commands)
   - ``/biomapper/Dockerfile.ci`` (CI Docker configuration for testing)
   - ``/biomapper/src/cli/minimal.py`` (CLI commands: health, test-import, strategies)
   - ``/biomapper/src/api/main.py`` (FastAPI server entry point)