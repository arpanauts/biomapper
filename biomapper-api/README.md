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

- Python 3.10+
- [Biomapper](https://github.com/your-org/biomapper) library installed

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/biomapper.git
cd biomapper/biomapper-api

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

Create a `.env` file in the project root with the following variables:

```
# API settings
DEBUG=True
HOST=0.0.0.0
PORT=8000

# CORS settings
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Biomapper settings
OPENAI_API_KEY=your_api_key_here
```

### Running the API

```bash
# Development mode
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

When the API is running, you can access the auto-generated documentation:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json
