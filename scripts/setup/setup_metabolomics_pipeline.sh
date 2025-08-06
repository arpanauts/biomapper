#!/bin/bash

# Setup script for metabolomics harmonization pipeline
# This script prepares the environment for first-time users

set -e  # Exit on error

echo "========================================="
echo "Metabolomics Pipeline Setup"
echo "========================================="

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Check Poetry
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is required. Install from https://python-poetry.org"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required"
    exit 1
fi

echo "✓ Prerequisites check passed"

# Install dependencies
echo "Installing Python dependencies..."
cd /home/ubuntu/biomapper
poetry install --with dev,api

# Create required directories
echo "Creating directories..."
mkdir -p data/{results,logs,cache}
mkdir -p data/logs/pipelines
mkdir -p data/cache/cts
mkdir -p qdrant_storage

# Setup Qdrant
echo "Setting up Qdrant..."
docker pull qdrant/qdrant

# Download and index HMDB data
echo "Setting up HMDB data..."
if [ ! -f "data/hmdb_metabolites.xml" ]; then
    echo "Downloading HMDB data..."
    cd data
    wget https://hmdb.ca/system/downloads/current/hmdb_metabolites.zip
    unzip hmdb_metabolites.zip
    cd ..
fi

# Run HMDB indexing
echo "Indexing HMDB data in Qdrant..."
docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
sleep 10  # Wait for Qdrant to start

poetry run python scripts/setup_qdrant_hmdb.py

echo "✓ Setup complete!"
echo ""
echo "To run the pipeline:"
echo "  poetry run python scripts/main_pipelines/run_metabolomics_harmonization.py"