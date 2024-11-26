#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Creating annotation-engine project structure...${NC}"

# Create root directory and navigate into it
mkdir -p annotation-engine
cd annotation-engine

# Create directory structure
mkdir -p .github/workflows
mkdir -p docs/{api,examples,diagrams}
mkdir -p tests/fixtures
mkdir -p annotation_engine/{core,standardization,mapping,utils,schemas}
mkdir -p scripts

# Create empty __init__.py files
find annotation_engine -type d -exec touch {}/__init__.py \;
touch tests/__init__.py

# Create basic config.py
cat << 'ENDCONFIG' > annotation_engine/config.py
"""
Configuration settings for the annotation engine.
"""

class Config:
    DB_HOST = "localhost"
    DB_PORT = 5432
    API_TIMEOUT = 30
    LOG_LEVEL = "INFO"
ENDCONFIG

# Create basic test file
cat << 'ENDTEST' > tests/test_core.py
import pytest

def test_sample():
    assert True
ENDTEST

# Create requirements.txt
cat << 'ENDREQ' > requirements.txt
requests>=2.25.1
pandas>=1.2.0
sqlalchemy>=1.4.0
pyyaml>=5.4.1
ENDREQ

# Create requirements-dev.txt
cat << 'ENDREQDEV' > requirements-dev.txt
-r requirements.txt
pytest>=6.2.5
pytest-cov>=2.12.1
black>=21.5b2
flake8>=3.9.2
mypy>=0.910
ENDREQDEV
