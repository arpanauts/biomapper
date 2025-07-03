# Biomapper CLI Reference

The Biomapper command-line interface provides tools for biological data mapping, metadata management, and system health monitoring.

## Installation

After installing Biomapper with Poetry, the CLI is available through:

```bash
poetry run biomapper [command]
```

Or, if you've activated the Poetry shell:

```bash
poetry shell
biomapper [command]
```

## Global Options

```
--help, -h          Show help message
--version           Show version information
--verbose, -v       Enable verbose output
--quiet, -q         Suppress non-essential output
```

## Commands

### `biomapper health`

Check the health status of the Biomapper system and its dependencies.

```bash
biomapper health
```

**Options:**
- `--detailed`: Show detailed health information for each component
- `--format [text|json]`: Output format (default: text)

**Example:**
```bash
poetry run biomapper health --detailed --format json
```

**Output:**
- Database connection status
- Cache backend status
- API service availability
- RAG store connection status
- System resource usage

### `biomapper metadata`

Manage mapping metadata and configurations.

#### `metadata list`

List all available mapping strategies and metadata.

```bash
biomapper metadata list [OPTIONS]
```

**Options:**
- `--type [strategy|endpoint|resource]`: Filter by metadata type
- `--format [table|json|yaml]`: Output format (default: table)

**Example:**
```bash
poetry run biomapper metadata list --type strategy --format table
```

#### `metadata show`

Show detailed information about a specific metadata item.

```bash
biomapper metadata show <name> [OPTIONS]
```

**Arguments:**
- `name`: Name of the strategy, endpoint, or resource

**Options:**
- `--version`: Show specific version (default: latest)
- `--format [yaml|json]`: Output format (default: yaml)

**Example:**
```bash
poetry run biomapper metadata show protein_mapping --format yaml
```

#### `metadata validate`

Validate a metadata configuration file.

```bash
biomapper metadata validate <file> [OPTIONS]
```

**Arguments:**
- `file`: Path to YAML or JSON configuration file

**Options:**
- `--type [strategy|endpoint]`: Specify configuration type
- `--strict`: Enable strict validation

**Example:**
```bash
poetry run biomapper metadata validate configs/strategies/my_strategy.yaml --type strategy
```

### `biomapper metamapper`

Execute mapping operations and manage mapping strategies.

#### `metamapper execute`

Execute a mapping strategy on input data.

```bash
biomapper metamapper execute [OPTIONS]
```

**Options:**
- `--strategy, -s`: Name of the strategy to execute (required)
- `--input, -i`: Input file path (CSV, TSV, or TXT)
- `--output, -o`: Output file path
- `--column, -c`: Column name containing entities to map
- `--entity-type, -t`: Entity type (protein, gene, metabolite, disease)
- `--format [csv|json|tsv]`: Output format (default: csv)
- `--checkpoint`: Enable checkpointing for resume capability
- `--parallel`: Number of parallel workers (default: 1)

**Example:**
```bash
poetry run biomapper metamapper execute \
    --strategy protein_comprehensive_mapping \
    --input proteins.csv \
    --column "protein_name" \
    --entity-type protein \
    --output mapped_proteins.csv \
    --parallel 4
```

#### `metamapper populate`

Populate the database with metadata configurations.

```bash
biomapper metamapper populate [OPTIONS]
```

**Options:**
- `--config-dir`: Directory containing configuration files
- `--type [all|strategies|endpoints|resources]`: What to populate
- `--clear`: Clear existing data before populating
- `--validate`: Validate configurations before loading

**Example:**
```bash
poetry run biomapper metamapper populate \
    --config-dir configs/ \
    --type strategies \
    --validate
```

#### `metamapper resume`

Resume a checkpointed mapping operation.

```bash
biomapper metamapper resume <checkpoint-id> [OPTIONS]
```

**Arguments:**
- `checkpoint-id`: ID of the checkpoint to resume from

**Options:**
- `--output, -o`: Output file path (can override original)
- `--parallel`: Number of parallel workers

**Example:**
```bash
poetry run biomapper metamapper resume ckpt_20240115_123456 --output resumed_results.csv
```

### `biomapper metamapper-db`

Database management commands for the metamapper system.

#### `metamapper-db init`

Initialize the metamapper database.

```bash
biomapper metamapper-db init [OPTIONS]
```

**Options:**
- `--force`: Force initialization (drops existing tables)
- `--seed`: Seed with example data

**Example:**
```bash
poetry run biomapper metamapper-db init --seed
```

#### `metamapper-db migrate`

Run database migrations.

```bash
biomapper metamapper-db migrate [OPTIONS]
```

**Options:**
- `--target`: Target migration version
- `--dry-run`: Show migrations without applying

**Example:**
```bash
poetry run biomapper metamapper-db migrate --dry-run
```

#### `metamapper-db backup`

Create a database backup.

```bash
biomapper metamapper-db backup [OPTIONS]
```

**Options:**
- `--output, -o`: Backup file path
- `--compress`: Compress backup file

**Example:**
```bash
poetry run biomapper metamapper-db backup --output backups/metamapper_backup.sql --compress
```

### `biomapper relationship`

Manage entity relationships and relationship-based mappings.

#### `relationship list`

List available relationship configurations.

```bash
biomapper relationship list [OPTIONS]
```

**Options:**
- `--source-type`: Filter by source entity type
- `--target-type`: Filter by target entity type
- `--format [table|json]`: Output format

**Example:**
```bash
poetry run biomapper relationship list --source-type gene --target-type protein
```

#### `relationship map`

Perform relationship-based mapping.

```bash
biomapper relationship map <relationship-id> [OPTIONS]
```

**Arguments:**
- `relationship-id`: ID of the relationship to use

**Options:**
- `--input, -i`: Input file with source entities
- `--output, -o`: Output file path
- `--column, -c`: Column containing source entities
- `--include-metadata`: Include relationship metadata in output

**Example:**
```bash
poetry run biomapper relationship map gene_to_protein \
    --input genes.csv \
    --column "gene_symbol" \
    --output gene_protein_mappings.csv \
    --include-metadata
```

## Configuration

### Environment Variables

```bash
# Database configuration
BIOMAPPER_DB_URL=sqlite+aiosqlite:///data/biomapper.db
BIOMAPPER_DB_POOL_SIZE=5

# Cache configuration
BIOMAPPER_CACHE_BACKEND=redis
BIOMAPPER_CACHE_URL=redis://localhost:6379
BIOMAPPER_CACHE_TTL=3600

# API configuration
BIOMAPPER_API_TIMEOUT=30
BIOMAPPER_API_RETRY_COUNT=3

# Logging
BIOMAPPER_LOG_LEVEL=INFO
BIOMAPPER_LOG_FILE=/var/log/biomapper/biomapper.log
```

### Configuration File

Create a `.biomapper.yaml` in your home directory or project root:

```yaml
database:
  url: sqlite+aiosqlite:///data/biomapper.db
  pool_size: 5

cache:
  backend: redis
  url: redis://localhost:6379
  ttl: 3600

api:
  timeout: 30
  retry_count: 3

logging:
  level: INFO
  file: /var/log/biomapper/biomapper.log
```

## Examples

### Complete Workflow Example

```bash
# 1. Check system health
poetry run biomapper health

# 2. List available strategies
poetry run biomapper metadata list --type strategy

# 3. Validate your input file
head -n 5 proteins.csv

# 4. Execute mapping
poetry run biomapper metamapper execute \
    --strategy protein_comprehensive_mapping \
    --input proteins.csv \
    --column "protein_name" \
    --output results.csv \
    --checkpoint

# 5. Check results
head -n 5 results.csv
```

### Batch Processing Example

```bash
#!/bin/bash
# batch_process.sh

# Process multiple files with the same strategy
for file in data/*.csv; do
    output="results/$(basename $file .csv)_mapped.csv"
    poetry run biomapper metamapper execute \
        --strategy metabolite_mapping \
        --input "$file" \
        --column "compound_name" \
        --output "$output" \
        --parallel 4
done
```

### Custom Strategy Development

```bash
# 1. Create your strategy YAML
cat > my_custom_strategy.yaml << EOF
name: my_custom_mapping
version: "1.0"
entity_type: protein
actions:
  - type: LOAD_INPUT_DATA
    name: load_proteins
  - type: API_RESOLVER
    name: uniprot_lookup
    config:
      api_endpoint: uniprot
EOF

# 2. Validate the strategy
poetry run biomapper metadata validate my_custom_strategy.yaml --type strategy

# 3. Test with sample data
poetry run biomapper metamapper execute \
    --strategy my_custom_strategy.yaml \
    --input sample_proteins.txt \
    --output test_results.csv
```

## Troubleshooting

### Common Issues

1. **Database connection errors**
   ```bash
   poetry run biomapper health --detailed
   ```

2. **Strategy not found**
   ```bash
   poetry run biomapper metadata list --type strategy
   ```

3. **Memory issues with large files**
   ```bash
   # Use parallel processing with limited workers
   poetry run biomapper metamapper execute \
       --strategy your_strategy \
       --input large_file.csv \
       --parallel 2 \
       --checkpoint
   ```

4. **Resume after failure**
   ```bash
   # Find checkpoint ID in logs or output
   poetry run biomapper metamapper resume ckpt_20240115_123456
   ```

### Getting Help

```bash
# Command-specific help
poetry run biomapper metamapper execute --help

# General help
poetry run biomapper --help

# Version information
poetry run biomapper --version
```