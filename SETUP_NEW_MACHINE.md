# Biomapper Setup Guide for New Machines

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/biomapper.git
cd biomapper

# 2. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install --with dev,docs,api

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Start Qdrant (if using vector search)
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 6. Initialize database
cd biomapper-api
poetry run alembic upgrade head

# 7. Start API server
poetry run uvicorn app.main:app --reload --port 8001

# 8. Verify installation
cd ..
poetry run biomapper health
```

## Required Components

### 1. Core Dependencies
- **Python 3.11+** (tested with 3.11, 3.12)
- **Poetry** for dependency management
- **Git** for version control

### 2. Database Components

#### SQLite (Default)
- Automatically created at first run
- Location: `biomapper-api/biomapper.db`
- No additional setup required

#### Qdrant Vector Database (For Semantic Matching)
```bash
# Option 1: Docker (recommended)
docker run -d -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name qdrant \
  qdrant/qdrant

# Option 2: Binary installation
wget https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-gnu.tar.gz
tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
./qdrant --config-path config/config.yaml
```

**Qdrant Data Transfer:**
- Copy `qdrant_storage/` directory from existing installation
- Contains pre-built vector indices for metabolites
- Size: ~500MB compressed, ~1.5GB uncompressed

### 3. Reference Data Files

#### Required Files
These files must be present for strategies to execute:

```bash
data/
├── hmdb_metabolites.xml        # 6.1GB - HMDB database
├── nightingale_biomarkers.tsv  # 5KB - NMR reference
├── SPOKE_compounds.tsv         # ~100MB - SPOKE compound data
├── SPOKE_proteins.tsv          # ~50MB - SPOKE protein data
├── kg2c_nodes.tsv              # Variable - KG2c node data
└── kg2c_edges.tsv              # Variable - KG2c edge data
```

#### Data Transfer Options

**Option 1: Using DVC (Recommended for large files)**
```bash
# Install DVC
pip install dvc[s3]  # or dvc[gdrive]

# Pull data files
dvc pull

# Configure remote (if not set)
dvc remote add -d myremote s3://bucket/path
```

**Option 2: Direct Transfer**
```bash
# From existing installation
tar -czf biomapper_data.tar.gz data/
scp biomapper_data.tar.gz user@newmachine:/path/

# On new machine
tar -xzf biomapper_data.tar.gz
```

**Option 3: Download from Sources**
```bash
# HMDB (requires registration)
wget https://hmdb.ca/system/downloads/current/hmdb_metabolites.zip
unzip hmdb_metabolites.zip -d data/

# Create minimal test data if needed
python scripts/create_test_data.py
```

### 4. Environment Configuration

#### Essential Variables
```bash
# Required
BIOMAPPER_DATA_DIR=/path/to/data
BIOMAPPER_CONFIG_DIR=configs
DATABASE_URL=sqlite:///./biomapper.db

# For vector search
QDRANT_HOST=localhost
QDRANT_PORT=6333

# For Google Drive sync (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=folder_id_from_url
```

#### Google Drive Setup (Optional)
1. Create service account at https://console.cloud.google.com
2. Enable Google Drive API
3. Download credentials JSON
4. Share target folder with service account email
5. Set environment variables

### 5. Directory Structure

Ensure these directories exist:
```bash
mkdir -p data
mkdir -p logs
mkdir -p /tmp/biomapper/{cache,output,logs}
```

## Verification Steps

### 1. Check Core System
```bash
# Verify Poetry installation
poetry --version

# Check Python version
python --version  # Should be 3.11+

# Test imports
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print(f'Actions: {len(ACTION_REGISTRY)}')"
```

### 2. Check API Server
```bash
# Start server
cd biomapper-api
poetry run uvicorn app.main:app --port 8001 &

# Test endpoints
curl http://localhost:8001/api/health
curl http://localhost:8001/api/strategies/v2/list
```

### 3. Check Vector Database
```bash
# If using Qdrant
curl http://localhost:6333/collections

# Should show metabolites collection if data transferred
```

### 4. Run Test Strategy
```bash
# Using client
poetry run python -c "
from biomapper_client import BiomapperClient
client = BiomapperClient('http://localhost:8001')
result = client.execute_strategy('simple_test_strategy')
print(result)
"
```

## Minimal Setup (Without External Services)

For basic functionality without vector search or external APIs:

```bash
# 1. Install dependencies
poetry install --with api

# 2. Create minimal .env
cat > .env << EOF
BIOMAPPER_DATA_DIR=./data
BIOMAPPER_CONFIG_DIR=./configs
DATABASE_URL=sqlite:///./biomapper.db
ENABLE_VECTOR_FALLBACK=false
ENABLE_API_FALLBACKS=false
EOF

# 3. Create test data
mkdir -p data
echo -e "identifier\tname\nHMDB0000001\tTest" > data/test_metabolites.tsv

# 4. Start API
cd biomapper-api
poetry run uvicorn app.main:app --port 8001
```

## Troubleshooting

### Issue: Actions not registering
```bash
# Force reimport of actions
python -c "
import biomapper.core.strategy_actions
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
print(ACTION_REGISTRY.keys())
"
```

### Issue: Qdrant connection failed
```bash
# Check if Qdrant is running
docker ps | grep qdrant
curl http://localhost:6333/health

# Restart if needed
docker restart qdrant
```

### Issue: Missing data files
```bash
# Create minimal test data
python scripts/create_minimal_test_data.py

# Or disable strict validation
echo "STRICT_VALIDATION=false" >> .env
```

### Issue: Google Drive sync fails
```bash
# Test credentials
python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/creds.json'
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/drive.file']
)
print('Credentials valid')
"
```

## Data Requirements by Strategy Type

### Protein Strategies
- Required: UniProt ID mappings
- Optional: SPOKE_proteins.tsv, kg2c_nodes.tsv

### Metabolite Strategies  
- Required: hmdb_metabolites.xml or test metabolite data
- Optional: nightingale_biomarkers.tsv, SPOKE_compounds.tsv
- For semantic: Qdrant with metabolites collection

### Chemistry Strategies
- Required: LOINC reference data
- Optional: Vendor-specific test catalogs

### Multi-Entity Strategies
- Requires data for all entity types involved

## Production Deployment

For production environments:

1. Use PostgreSQL instead of SQLite
2. Set up proper logging and monitoring
3. Configure CORS for web clients
4. Use environment-specific configs
5. Set up backup strategies for data
6. Configure rate limiting for APIs
7. Use HTTPS with proper certificates

## Support

- Documentation: See README.md and docs/
- Issues: GitHub Issues
- Architecture: BIOMAPPER_ARCHITECTURE_ROADMAP.md
- Google Drive: GOOGLE_DRIVE_SETUP.md