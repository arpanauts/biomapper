# Biomapper Installation Guide

## System Requirements

- **Python**: 3.11 or later
- **Operating System**: Linux, macOS, or Windows (with WSL recommended)
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large datasets)
- **Storage**: 2GB free space (more for vector stores and caching)

## Installation Methods

### 1. Development Installation (Recommended)

For active development or accessing the latest features:

```bash
# Clone the repository
git clone https://github.com/your-org/biomapper.git
cd biomapper

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies with all optional groups
poetry install --with dev,docs,api

# Activate the virtual environment
poetry shell
```

### 2. Basic Installation

For using Biomapper as a library:

```bash
# Clone and install core dependencies only
git clone https://github.com/your-org/biomapper.git
cd biomapper
poetry install
```

### 3. API Server Installation

To run the Biomapper API server:

```bash
# Install with API dependencies
poetry install --with api

# Navigate to API directory
cd biomapper-api

# Run the server
poetry run uvicorn app.main:app --reload
```

## Configuration

### 1. Environment Variables

Copy the environment template and configure:

```bash
cp .env_template .env
```

Edit `.env` with your settings:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///data/metamapper.db
SQLALCHEMY_ECHO=false

# Cache
CACHE_BACKEND=memory  # or redis, disk
REDIS_URL=redis://localhost:6379

# API Keys (for external services)
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Vector Stores
CHROMA_PATH=./data/chroma
QDRANT_HOST=localhost
QDRANT_PORT=6333

# SPOKE Database (optional)
SPOKE_NEO4J_URL=bolt://localhost:7687
SPOKE_NEO4J_USER=neo4j
SPOKE_NEO4J_PASSWORD=password
```

### 2. Database Setup

Initialize the database:

```bash
# Create database directory
mkdir -p data

# Run database migrations
poetry run alembic upgrade head

# (Optional) Seed with example data
poetry run biomapper metamapper-db init --seed
```

### 3. Vector Store Setup (Optional)

For RAG-based mapping capabilities:

#### ChromaDB
```bash
# ChromaDB is included in dependencies
# Data will be stored in CHROMA_PATH directory
```

#### Qdrant
```bash
# Run Qdrant using Docker
docker run -p 6333:6333 qdrant/qdrant
```

## Platform-Specific Notes

### macOS

If you encounter issues with ChromaDB on Apple Silicon:

```bash
# Install system dependencies
brew install cmake

# Set environment variable
export HNSWLIB_NO_NATIVE=1
```

### Windows

Use WSL2 for best compatibility:

```bash
# In WSL2 terminal
sudo apt-get update
sudo apt-get install python3.11 python3.11-dev
```

### Linux

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-dev build-essential

# Fedora/RHEL
sudo dnf install python3.11 python3.11-devel gcc gcc-c++
```

## Dependency Groups

Biomapper uses Poetry dependency groups for modular installation:

- **Core**: Essential dependencies (installed by default)
- **dev**: Development tools (pytest, ruff, mypy)
- **docs**: Documentation building (sphinx, myst-parser)
- **api**: API server dependencies (FastAPI, uvicorn)
- **rag**: RAG/vector store dependencies (chromadb, qdrant-client)
- **llm**: LLM provider SDKs (openai, anthropic)

Install specific groups:

```bash
# Development environment
poetry install --with dev

# Documentation building
poetry install --with docs

# Full installation
poetry install --with dev,docs,api,rag,llm
```

## Verification

Verify your installation:

```bash
# Check CLI
poetry run biomapper --version

# Run health check
poetry run biomapper health

# Run tests
poetry run pytest tests/unit/

# Check code quality
poetry run ruff check .
poetry run mypy biomapper
```

## Common Issues

### 1. Poetry Not Found

```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall
curl -sSL https://install.python-poetry.org | python3 - --uninstall
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Python Version Mismatch

```bash
# Check Python version
python3 --version

# Use pyenv to install Python 3.11
curl https://pyenv.run | bash
pyenv install 3.11.7
pyenv local 3.11.7
```

### 3. Database Connection Errors

```bash
# Check database file permissions
ls -la data/

# Recreate database
rm -f data/metamapper.db
poetry run alembic upgrade head
```

### 4. Memory Issues

For large datasets, increase available memory:

```bash
# Set environment variable
export BIOMAPPER_MAX_MEMORY=8G

# Or in .env file
BIOMAPPER_MAX_MEMORY=8G
```

## Next Steps

1. Read the [Getting Started Guide](../source/guides/getting_started.md)
2. Explore [CLI Commands](../CLI_REFERENCE.md)
3. Try the [Tutorials](../source/tutorials/)
4. Configure your [Mapping Strategies](../source/configuration.rst)

## Upgrading

To upgrade to the latest version:

```bash
# Update repository
git pull origin main

# Update dependencies
poetry update

# Run any new migrations
poetry run alembic upgrade head
```

## Uninstallation

To completely remove Biomapper:

```bash
# Deactivate virtual environment
exit  # or deactivate

# Remove virtual environment
poetry env remove python

# Remove project directory
cd ..
rm -rf biomapper

# (Optional) Remove Poetry
curl -sSL https://install.python-poetry.org | python3 - --uninstall
```