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
    git clone https://github.com/your-org/biomapper.git
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
    git clone https://github.com/your-org/biomapper.git
    cd biomapper
    
    # Install only runtime dependencies
    poetry install --with api
    
    # Start the API server
    cd biomapper-api
    poetry run uvicorn main:app --host 0.0.0.0 --port 8000

Docker Installation
-------------------

*Coming Soon*

Troubleshooting
---------------

**Poetry not found**
  Install Poetry using the official installer or package manager.

**Python version issues**  
  Ensure Python 3.11+ is installed and available.

**Permission errors**
  Run installation commands with appropriate permissions for your system.