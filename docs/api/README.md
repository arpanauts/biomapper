# Biomapper REST API Documentation

## Overview

The Biomapper API provides a RESTful interface for biological data mapping operations. Built with FastAPI, it offers automatic OpenAPI documentation, type validation, and async support.

## Base URL

```
http://localhost:8000/api
```

## Authentication

The API uses session-based authentication. Each session is identified by a unique `session_id` that is returned when uploading files.

## API Endpoints

### Health Check

#### Check API Health

```http
GET /api/health/
```

Returns the health status of the API and its dependencies.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "dependencies": {
    "database": "connected",
    "cache": "connected"
  }
}
```

### File Management

#### Upload File

```http
POST /api/files/upload
```

Upload a CSV file for processing. The file size limit is dynamically set based on available system memory.

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload with field name `file`

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "proteins.csv",
  "file_size": 1024,
  "columns": ["id", "name", "sequence"],
  "row_count": 100
}
```

**Error Responses:**
- `400 Bad Request`: Invalid file format
- `413 Payload Too Large`: File exceeds size limit

#### Get File Columns

```http
GET /api/files/{session_id}/columns
```

Retrieve column information for an uploaded file.

**Parameters:**
- `session_id` (path): The session identifier from file upload

**Response:**
```json
{
  "columns": [
    {
      "name": "id",
      "type": "string",
      "sample_values": ["P12345", "Q67890", "A12345"]
    },
    {
      "name": "name",
      "type": "string",
      "sample_values": ["Protein A", "Protein B", "Protein C"]
    }
  ]
}
```

#### Preview File Data

```http
GET /api/files/{session_id}/preview
```

Get a preview of the uploaded file data.

**Parameters:**
- `session_id` (path): The session identifier
- `rows` (query, optional): Number of rows to preview (default: 10, max: 100)

**Response:**
```json
{
  "total_rows": 1000,
  "preview_rows": 10,
  "data": [
    {"id": "P12345", "name": "Protein A", "sequence": "MVKT..."},
    {"id": "Q67890", "name": "Protein B", "sequence": "MALK..."}
  ]
}
```

#### List Server Files

```http
GET /api/files/server/list
```

List files available on the server for processing.

**Response:**
```json
{
  "files": [
    {
      "filename": "reference_proteins.csv",
      "path": "/data/reference_proteins.csv",
      "size": 2048576,
      "modified": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Load Server File

```http
POST /api/files/server/load
```

Load a file from the server for processing.

**Request:**
```json
{
  "filepath": "/data/reference_proteins.csv"
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "reference_proteins.csv",
  "file_size": 2048576,
  "columns": ["id", "name", "sequence"],
  "row_count": 5000
}
```

### Mapping Operations

#### Create Mapping Job

```http
POST /api/mapping/jobs
```

Create a new mapping job for biological entity resolution.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_column": "gene_name",
  "entity_type": "gene",
  "target_namespaces": ["ensembl", "entrez"],
  "options": {
    "include_synonyms": true,
    "confidence_threshold": 0.85
  }
}
```

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

#### Get Job Status

```http
GET /api/mapping/jobs/{job_id}/status
```

Check the status of a mapping job.

**Parameters:**
- `job_id` (path): The job identifier

**Response:**
```json
{
  "job_id": "job_123456",
  "status": "completed",
  "progress": 100,
  "total_items": 1000,
  "processed_items": 1000,
  "success_count": 950,
  "error_count": 50,
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z"
}
```

**Status Values:**
- `pending`: Job is queued
- `running`: Job is being processed
- `completed`: Job finished successfully
- `failed`: Job encountered an error
- `cancelled`: Job was cancelled

#### Get Job Results

```http
GET /api/mapping/jobs/{job_id}/results
```

Retrieve the results of a completed mapping job.

**Parameters:**
- `job_id` (path): The job identifier
- `page` (query, optional): Page number (default: 1)
- `page_size` (query, optional): Results per page (default: 100, max: 1000)

**Response:**
```json
{
  "job_id": "job_123456",
  "total_results": 1000,
  "page": 1,
  "page_size": 100,
  "results": [
    {
      "source_id": "TP53",
      "mappings": [
        {
          "target_namespace": "ensembl",
          "target_id": "ENSG00000141510",
          "confidence": 1.0,
          "mapping_type": "exact"
        },
        {
          "target_namespace": "entrez",
          "target_id": "7157",
          "confidence": 1.0,
          "mapping_type": "exact"
        }
      ]
    }
  ]
}
```

#### Download Job Results

```http
GET /api/mapping/jobs/{job_id}/download
```

Download mapping results as a CSV file.

**Parameters:**
- `job_id` (path): The job identifier
- `format` (query, optional): Output format (`csv`, `tsv`, `json`) (default: `csv`)

**Response:**
- Content-Type: `text/csv` (or appropriate for format)
- Content-Disposition: `attachment; filename="mapping_results_{job_id}.csv"`

#### Relationship Mapping

```http
POST /api/mapping/relationship
```

Perform relationship-based mapping using predefined relationship configurations.

**Request:**
```json
{
  "relationship_id": "gene_to_protein",
  "source_data": [
    {"id": "BRCA1", "type": "gene_symbol"},
    {"id": "TP53", "type": "gene_symbol"}
  ],
  "options": {
    "include_metadata": true,
    "max_targets_per_source": 10
  }
}
```

**Response:**
```json
{
  "relationship_id": "gene_to_protein",
  "results": [
    {
      "source": {"id": "BRCA1", "type": "gene_symbol"},
      "targets": [
        {
          "id": "P38398",
          "type": "uniprot_id",
          "confidence": 1.0,
          "metadata": {
            "protein_name": "Breast cancer type 1 susceptibility protein",
            "organism": "Homo sapiens"
          }
        }
      ]
    }
  ]
}
```

### Strategy Execution

#### Execute Strategy

```http
POST /api/strategies/{strategy_name}/execute
```

Execute a predefined mapping strategy.

**Parameters:**
- `strategy_name` (path): Name of the strategy to execute

**Request:**
```json
{
  "input_data": [
    {"id": "P12345", "name": "Protein A"},
    {"id": "Q67890", "name": "Protein B"}
  ],
  "options": {
    "parallel_execution": true,
    "checkpoint_enabled": true
  }
}
```

**Response:**
```json
{
  "execution_id": "exec_789012",
  "strategy_name": "protein_comprehensive_mapping",
  "status": "running",
  "checkpoint_id": "ckpt_345678"
}
```

### Endpoints

#### List Available Endpoints

```http
GET /api/endpoints/
```

Get a list of all available mapping endpoints and their capabilities.

**Response:**
```json
{
  "endpoints": [
    {
      "id": "uniprot",
      "name": "UniProt",
      "type": "protein",
      "supported_operations": ["search", "id_mapping", "metadata"],
      "rate_limit": {
        "requests_per_second": 10,
        "burst": 20
      }
    },
    {
      "id": "ensembl",
      "name": "Ensembl",
      "type": "gene",
      "supported_operations": ["search", "id_mapping"],
      "rate_limit": {
        "requests_per_second": 5,
        "burst": 10
      }
    }
  ]
}
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:

### Error Response Format

```json
{
  "detail": "Detailed error message",
  "type": "error_type",
  "field_errors": [
    {
      "field": "source_column",
      "message": "Column not found in uploaded file"
    }
  ]
}
```

### Common Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- Default: 100 requests per minute per IP
- File uploads: 10 per hour per session
- Mapping jobs: 20 concurrent jobs per session

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp for limit reset

## WebSocket Support

For real-time job updates, the API supports WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/jobs/{job_id}');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Job ${update.job_id}: ${update.status} (${update.progress}%)`);
};
```

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## SDK Support

Official Python SDK:

```python
from biomapper_client import BiomapperClient

client = BiomapperClient(base_url="http://localhost:8000")

# Upload file
session = client.upload_file("proteins.csv")

# Create mapping job
job = client.create_mapping_job(
    session_id=session.session_id,
    source_column="gene_name",
    entity_type="gene",
    target_namespaces=["ensembl", "entrez"]
)

# Wait for completion
result = client.wait_for_job(job.job_id)

# Download results
client.download_results(job.job_id, "results.csv")
```

## Examples

### Complete Mapping Workflow

```bash
# 1. Upload file
curl -X POST -F "file=@proteins.csv" http://localhost:8000/api/files/upload

# 2. Create mapping job
curl -X POST http://localhost:8000/api/mapping/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_column": "gene_name",
    "entity_type": "gene",
    "target_namespaces": ["ensembl"]
  }'

# 3. Check status
curl http://localhost:8000/api/mapping/jobs/job_123456/status

# 4. Get results
curl http://localhost:8000/api/mapping/jobs/job_123456/results

# 5. Download as CSV
curl -o results.csv http://localhost:8000/api/mapping/jobs/job_123456/download
```

### Using a Strategy

```python
import httpx
import asyncio

async def run_strategy():
    async with httpx.AsyncClient() as client:
        # Execute strategy
        response = await client.post(
            "http://localhost:8000/api/strategies/protein_mapping/execute",
            json={
                "input_data": [{"id": "P12345", "name": "BRCA1"}],
                "options": {"checkpoint_enabled": True}
            }
        )
        
        execution = response.json()
        print(f"Execution started: {execution['execution_id']}")

asyncio.run(run_strategy())
```

## Best Practices

1. **Use Session IDs**: Always include session IDs for file-based operations
2. **Handle Pagination**: Use pagination for large result sets
3. **Monitor Job Status**: Poll job status or use WebSocket for real-time updates
4. **Respect Rate Limits**: Implement exponential backoff for retries
5. **Use Checkpoints**: Enable checkpoints for long-running operations
6. **Validate Input**: Ensure data formats match entity type requirements

## Versioning

The API uses URL versioning. Currently at version 1 (`/api/v1/`).
Future versions will be available at `/api/v2/`, etc.