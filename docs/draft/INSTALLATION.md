# Biomapper Installation Guide

This guide details how to install and set up the `biomapper` toolkit, both for regular use and for development.

## Installation from PyPI

For standard usage, you can install the latest stable release directly from PyPI:

```bash
pip install biomapper
```

## Development Setup

If you intend to contribute to `biomapper` or run the latest development version, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/arpanauts/biomapper.git
    cd biomapper
    ```

2.  **Install Python 3.11:**
    We recommend using `pyenv` to manage Python versions. If you don't have `pyenv` installed:
    ```bash
    # Install pyenv dependencies (example for Debian/Ubuntu)
    sudo apt-get update
    sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl

    # Install pyenv
    curl https://pyenv.run | bash

    # Add pyenv to your shell configuration (e.g., ~/.bashrc or ~/.zshrc)
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc

    # Reload shell configuration
    source ~/.bashrc 
    # or source ~/.zshrc

    # Install Python 3.11 and set it for the project
    pyenv install 3.11
    pyenv local 3.11 
    ```

3.  **Install Poetry:**
    Poetry is used for dependency management. If you don't have it installed:
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    # Ensure Poetry's bin directory is in your PATH (usually added automatically or instructions provided)
    ```

4.  **Install Project Dependencies:**
    This command installs the core package and all development dependencies.
    ```bash
    poetry install
    ```

5.  **Set Up Pre-Commit Hooks:**
    We use pre-commit hooks to enforce code style and quality.
    ```bash
    poetry run pre-commit install
    ```

## Database Initialization (Development Setup)

`biomapper` uses two SQLite databases:

*   **Configuration Database (`data/metamapper.db`):** Stores endpoint definitions, mapping paths, etc. This is included in the repository.
*   **Mapping Cache (`~/.biomapper/data/mapping_cache.db` by default):** Stores the results of mapping operations to speed up subsequent requests. This database is *not* tracked by Git and can grow large.

**Crucial Step:** After cloning the repository and installing dependencies for the first time on a new machine, you **must** initialize the schema for the mapping cache database:

```bash
# Make sure you are in the root directory of the cloned repository
poetry run alembic upgrade head
```

This command uses Alembic (our database migration tool) to create all necessary tables in the `mapping_cache.db` file. You only need to do this once per new setup.

## Running Examples

The `examples/` directory contains tutorials and utility scripts.

1.  **Install Example Dependencies:**
    ```bash
    poetry install --with examples
    ```

2.  **Set Up Environment Variables:**
    Some examples might require API keys or other configuration.
    ```bash
    # Create a .env file from the template
    cp .env.example .env

    # Edit .env with your specific configurations (API keys, paths, etc.)
    vim .env 
    # or nano .env
    ```

3.  **Initialize Vector Store (if needed for specific examples):**
    Examples using Retrieval-Augmented Generation (RAG) rely on FastEmbed for generating embeddings and Qdrant as the vector database.
    Ensure your Qdrant instance is running and accessible, and configure connection details in your `.env` file if necessary.
    ```bash
    # Ensure Qdrant service is running (e.g., via Docker)
    # docker ps | grep qdrant 

    # Verify connection (example, replace with actual verification script if available)
    # poetry run python examples/utilities/verify_qdrant_connection.py
    ```

4.  **Run an Example:**
    Navigate to the examples directory and run a script using `poetry run`:
    ```bash
    poetry run python examples/tutorials/tutorial_basic_llm_mapping.py
    ```

Refer to the specific README within the `examples/` directory for more details on individual examples.
