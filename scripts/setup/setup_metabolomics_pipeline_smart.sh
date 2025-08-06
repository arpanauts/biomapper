#!/bin/bash

# Smart setup script for metabolomics harmonization pipeline
# This script checks existing state and only sets up what's missing

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Metabolomics Pipeline Smart Setup"
echo "========================================="
echo ""
echo "This script will check your existing setup and only install what's missing."
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to check if Docker container is running
container_running() {
    docker ps --format '{{.Names}}' | grep -q "^$1$"
}

# Function to check if Docker container exists (running or stopped)
container_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^$1$"
}

# Function to check if Qdrant collection exists
qdrant_collection_exists() {
    if curl -s http://localhost:6333/collections/hmdb_metabolites 2>/dev/null | grep -q '"status":"ok"'; then
        return 0
    else
        return 1
    fi
}

# Track what needs to be done
NEEDS_POETRY_INSTALL=false
NEEDS_DIRECTORIES=false
NEEDS_QDRANT_START=false
NEEDS_HMDB_DOWNLOAD=false
NEEDS_HMDB_INDEX=false

echo "Checking prerequisites..."
echo "-------------------------"

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Python 3 is installed (version $PYTHON_VERSION)"
else
    echo -e "${RED}✗${NC} Python 3 is required"
    exit 1
fi

# Check Poetry
if command_exists poetry; then
    POETRY_VERSION=$(poetry --version | cut -d' ' -f3)
    echo -e "${GREEN}✓${NC} Poetry is installed (version $POETRY_VERSION)"
else
    echo -e "${RED}✗${NC} Poetry is required. Install from https://python-poetry.org"
    exit 1
fi

# Check Docker
if command_exists docker; then
    echo -e "${GREEN}✓${NC} Docker is installed"
else
    echo -e "${RED}✗${NC} Docker is required"
    exit 1
fi

echo ""
echo "Checking existing setup..."
echo "-------------------------"

# Change to project directory
cd /home/ubuntu/biomapper

# Check if Python dependencies are installed
if poetry run python -c "import biomapper" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Python dependencies already installed"
else
    echo -e "${YELLOW}!${NC} Python dependencies need to be installed"
    NEEDS_POETRY_INSTALL=true
fi

# Check directories
DIRS_TO_CHECK=("data/results" "data/logs/pipelines" "data/cache/cts" "qdrant_storage")
for dir in "${DIRS_TO_CHECK[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $dir"
    else
        echo -e "${YELLOW}!${NC} Directory missing: $dir"
        NEEDS_DIRECTORIES=true
    fi
done

# Check Qdrant status
echo ""
echo "Checking Qdrant setup..."
echo "------------------------"

if container_running "qdrant"; then
    echo -e "${GREEN}✓${NC} Qdrant container is running"
    
    # Check if collection exists
    if qdrant_collection_exists; then
        # Get collection info
        COLLECTION_INFO=$(curl -s http://localhost:6333/collections/hmdb_metabolites)
        VECTOR_COUNT=$(echo "$COLLECTION_INFO" | grep -oP '"vectors_count":\K[0-9]+' || echo "0")
        echo -e "${GREEN}✓${NC} HMDB collection exists with $VECTOR_COUNT metabolites"
    else
        echo -e "${YELLOW}!${NC} HMDB collection not found"
        NEEDS_HMDB_INDEX=true
    fi
elif container_exists "qdrant"; then
    echo -e "${YELLOW}!${NC} Qdrant container exists but is stopped"
    NEEDS_QDRANT_START=true
else
    echo -e "${YELLOW}!${NC} Qdrant container not found"
    NEEDS_QDRANT_START=true
    NEEDS_HMDB_INDEX=true
fi

# Check HMDB data file
echo ""
echo "Checking HMDB data..."
echo "---------------------"

if [ -f "data/hmdb_metabolites.xml" ]; then
    FILE_SIZE=$(du -h data/hmdb_metabolites.xml | cut -f1)
    echo -e "${GREEN}✓${NC} HMDB data file exists ($FILE_SIZE)"
elif [ -f "/home/ubuntu/biomapper/data/hmdb_metabolites.zip" ]; then
    echo -e "${YELLOW}!${NC} HMDB zip exists but needs extraction"
    NEEDS_HMDB_DOWNLOAD=true
else
    echo -e "${YELLOW}!${NC} HMDB data not found"
    NEEDS_HMDB_DOWNLOAD=true
fi

# Summary of what needs to be done
echo ""
echo "Setup Summary"
echo "============="

if [ "$NEEDS_POETRY_INSTALL" = false ] && [ "$NEEDS_DIRECTORIES" = false ] && \
   [ "$NEEDS_QDRANT_START" = false ] && [ "$NEEDS_HMDB_DOWNLOAD" = false ] && \
   [ "$NEEDS_HMDB_INDEX" = false ]; then
    echo -e "${GREEN}Everything is already set up! You're ready to run the pipeline.${NC}"
    echo ""
    echo "To run the pipeline:"
    echo "  poetry run python scripts/main_pipelines/run_metabolomics_harmonization.py"
    exit 0
fi

echo "The following actions will be performed:"
[ "$NEEDS_POETRY_INSTALL" = true ] && echo "  - Install Python dependencies"
[ "$NEEDS_DIRECTORIES" = true ] && echo "  - Create missing directories"
[ "$NEEDS_QDRANT_START" = true ] && echo "  - Start Qdrant container"
[ "$NEEDS_HMDB_DOWNLOAD" = true ] && echo "  - Process HMDB data"
[ "$NEEDS_HMDB_INDEX" = true ] && echo "  - Index HMDB data in Qdrant"

echo ""
read -p "Continue with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# Perform setup actions
echo ""
echo "Performing setup..."
echo "==================="

# Install Python dependencies if needed
if [ "$NEEDS_POETRY_INSTALL" = true ]; then
    echo "Installing Python dependencies..."
    poetry install --with dev,api
    echo -e "${GREEN}✓${NC} Dependencies installed"
fi

# Create directories if needed
if [ "$NEEDS_DIRECTORIES" = true ]; then
    echo "Creating directories..."
    mkdir -p data/{results,logs,cache}
    mkdir -p data/logs/pipelines
    mkdir -p data/cache/cts
    mkdir -p qdrant_storage
    echo -e "${GREEN}✓${NC} Directories created"
fi

# Start Qdrant if needed
if [ "$NEEDS_QDRANT_START" = true ]; then
    echo "Setting up Qdrant..."
    
    # Pull image if not exists
    if ! docker images | grep -q "qdrant/qdrant"; then
        echo "Pulling Qdrant image..."
        docker pull qdrant/qdrant
    fi
    
    # Start or restart container
    if container_exists "qdrant"; then
        echo "Starting existing Qdrant container..."
        docker start qdrant
    else
        echo "Creating new Qdrant container..."
        docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
    fi
    
    # Wait for Qdrant to be ready
    echo "Waiting for Qdrant to start..."
    for i in {1..30}; do
        if curl -s http://localhost:6333/health | grep -q "ok"; then
            echo -e "${GREEN}✓${NC} Qdrant is ready"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗${NC} Qdrant failed to start"
            exit 1
        fi
    done
fi

# Process HMDB data if needed
if [ "$NEEDS_HMDB_DOWNLOAD" = true ]; then
    echo "Processing HMDB data..."
    
    # Check if zip exists and extract
    if [ -f "data/hmdb_metabolites.zip" ]; then
        echo "Extracting existing HMDB zip..."
        cd data
        unzip -o hmdb_metabolites.zip
        cd ..
    else
        echo "Downloading HMDB data..."
        cd data
        wget https://hmdb.ca/system/downloads/current/hmdb_metabolites.zip
        unzip hmdb_metabolites.zip
        cd ..
    fi
    echo -e "${GREEN}✓${NC} HMDB data ready"
fi

# Index HMDB data if needed
if [ "$NEEDS_HMDB_INDEX" = true ]; then
    echo "Indexing HMDB data in Qdrant..."
    echo "This may take several minutes..."
    
    # Run the indexing script
    if [ -f "scripts/setup_hmdb_qdrant.py" ]; then
        poetry run python scripts/setup_hmdb_qdrant.py --xml-path data/hmdb_metabolites.xml
    else
        echo -e "${RED}✗${NC} Indexing script not found: scripts/setup_hmdb_qdrant.py"
        echo "Please ensure the HMDB indexing script is available"
        exit 1
    fi
    
    # Verify indexing
    if qdrant_collection_exists; then
        VECTOR_COUNT=$(curl -s http://localhost:6333/collections/hmdb_metabolites | grep -oP '"vectors_count":\K[0-9]+' || echo "0")
        echo -e "${GREEN}✓${NC} HMDB indexing complete: $VECTOR_COUNT metabolites indexed"
    else
        echo -e "${RED}✗${NC} HMDB indexing may have failed"
    fi
fi

echo ""
echo "========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "========================================="
echo ""
echo "Your environment is ready. To run the pipeline:"
echo "  poetry run python scripts/main_pipelines/run_metabolomics_harmonization.py"
echo ""
echo "For more options:"
echo "  poetry run python scripts/main_pipelines/run_metabolomics_harmonization.py --help"
echo ""
echo "Current status:"
if container_running "qdrant"; then
    VECTOR_COUNT=$(curl -s http://localhost:6333/collections/hmdb_metabolites 2>/dev/null | grep -oP '"vectors_count":\K[0-9]+' || echo "unknown")
    echo "  - Qdrant: Running with $VECTOR_COUNT metabolites indexed"
else
    echo "  - Qdrant: Not running"
fi
echo "  - Python dependencies: Installed"
echo "  - Data directories: Ready"