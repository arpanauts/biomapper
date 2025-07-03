# Biomapper API

A FastAPI-based web API for the Biomapper biological data harmonization and ontology mapping toolkit.

## Overview

This API provides a web interface to the Biomapper toolkit, allowing users to:

1. Upload CSV files containing biological identifiers
2. Select columns containing IDs for mapping
3. Configure mapping operations to target ontologies
4. Process mapping jobs asynchronously
5. Download enriched result files

## Architecture

### Key Components

- **FastAPI Framework**: Modern, high-performance web framework with automatic OpenAPI documentation
- **Pydantic Models**: Type-safe request and response models
- **Async Processing**: Background tasks for long-running mapping operations
- **Session Management**: Stateful session handling for file uploads and job tracking

### Integration with Biomapper

The API integrates with the core Biomapper library, leveraging its hybrid architecture:

1. **SPOKE Knowledge Graph**: Primary source of biological relationships (ArangoDB)
2. **Extension Graph**: Custom graph to fill gaps in SPOKE's coverage (ArangoDB)
3. **Unified Ontology Layer**: Coordinates between both graphs
4. **SQL-based Mapping Cache**: Optimizes performance

## Project Structure

```
biomapper-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/                # Core application components
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration management
│   │   ├── security.py      # API security
│   │   └── session.py       # Session management
│   ├── api/                 # API routes and dependencies
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── files.py     # File upload/management endpoints
│   │   │   ├── mapping.py   # Mapping operation endpoints
│   │   │   └── health.py    # Health check endpoints
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── file.py          # File-related schemas
│   │   ├── mapping.py       # Mapping-related schemas
│   │   └── job.py           # Job status and results schemas
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── csv_service.py   # CSV file processing
│   │   ├── mapper_service.py # Integration with Biomapper
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── file_utils.py    # File handling utilities
│       └── error_utils.py   # Error handling utilities
├── tests/                   # Test suite
├── .env                     # Environment variables
├── pyproject.toml           # Project dependencies
├── Dockerfile               # Container definition
└── README.md                # Project documentation
```

## API Endpoints

### File Management

- `POST /api/files/upload`: Upload a CSV file
- `GET /api/files/{session_id}/columns`: Get columns from an uploaded file
- `GET /api/files/{session_id}/preview`: Preview the CSV data

### Mapping Operations

- `POST /api/mapping/jobs`: Create a new mapping job
- `GET /api/mapping/jobs/{job_id}/status`: Check job status
- `GET /api/mapping/jobs/{job_id}/results`: Get mapping results
- `GET /api/mapping/jobs/{job_id}/download`: Download result CSV

## Development Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) package manager
- [Biomapper](https://github.com/your-org/biomapper) library installed

### Installation

```bash
# Clone the repository (if not already done)
git clone https://github.com/your-org/biomapper.git
cd biomapper

# Install dependencies including API
poetry install --with api

# Activate the virtual environment
poetry shell

# Navigate to API directory
cd biomapper-api
```

### Configuration

Create a `.env` file in the biomapper-api directory with the following variables:

```
# API settings
DEBUG=True
HOST=0.0.0.0
PORT=8000

# CORS settings
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Biomapper settings
OPENAI_API_KEY=your_api_key_here

# Database
DATABASE_URL=sqlite+aiosqlite:///data/biomapper_api.db

# File upload limits (in MB)
MAX_UPLOAD_SIZE=100
```

### Running the API

```bash
# Development mode with auto-reload
poetry run uvicorn app.main:app --reload

# Production mode
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# With custom settings
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

## Testing

Run the test suite:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_file_endpoints.py

# Run with verbose output
poetry run pytest -v
```

## Code Quality

Maintain code quality with automated tools:

```bash
# Format code
poetry run ruff format .

# Check linting
poetry run ruff check .

# Type checking
poetry run mypy app

# All checks
poetry run ruff format . && poetry run ruff check . && poetry run mypy app
```

## API Documentation

When the API is running, you can access the auto-generated documentation:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

## Docker Deployment

Build and run with Docker:

```bash
# Build the image
docker build -t biomapper-api .

# Run the container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  biomapper-api
```

Docker Compose example:

```yaml
version: '3.8'
services:
  biomapper-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://user:password@db:5432/biomapper
    volumes:
      - ./data:/app/data
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=biomapper
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `False` |
| `HOST` | API host | `0.0.0.0` |
| `PORT` | API port | `8000` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///data/biomapper_api.db` |
| `MAX_UPLOAD_SIZE` | Max file upload size (MB) | `100` |
| `WORKERS` | Number of worker processes | `1` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Performance Tuning

For production deployments:

```bash
# Run with multiple workers
poetry run gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# With connection pooling
export DATABASE_POOL_SIZE=20
export DATABASE_POOL_TIMEOUT=30
```

## Monitoring

The API includes built-in health checks:

```bash
# Basic health check
curl http://localhost:8000/api/health

# Detailed health check
curl http://localhost:8000/api/health/detailed
```

## Security

Security best practices:

1. Always use HTTPS in production
2. Set strong API keys and rotate regularly
3. Configure CORS appropriately
4. Use rate limiting for public endpoints
5. Enable request validation
6. Log security events

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

See the main [Biomapper LICENSE](../LICENSE) file.