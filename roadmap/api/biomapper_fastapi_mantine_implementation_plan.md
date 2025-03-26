# Biomapper Web UI Implementation Plan

## Table of Contents
- [Overview](#overview)
- [Backend Implementation (FastAPI)](#backend-implementation-fastapi)
  - [Project Structure](#project-structure)
  - [Core Components](#core-components)
  - [API Endpoints](#api-endpoints)
  - [Service Layer](#service-layer)
  - [Data Models](#data-models)
  - [Error Handling](#error-handling)
  - [Testing Strategy](#testing-strategy)
- [Frontend Implementation (Mantine)](#frontend-implementation-mantine)
  - [Project Setup](#project-setup)
  - [Component Architecture](#component-architecture)
  - [State Management](#state-management)
  - [UI/UX Components](#uiux-components)
  - [API Integration](#api-integration)
  - [Testing Strategy](#testing-strategy-1)
- [Integration Workflow](#integration-workflow)
- [Development Timeline](#development-timeline)
- [Extensibility Considerations](#extensibility-considerations)
- [Deployment Options](#deployment-options)

## Overview

This document outlines the implementation plan for the Biomapper Web UI, focusing on a FastAPI backend and Mantine-based frontend. The goal is to create a Minimum Viable Product (MVP) that allows users to upload CSV files containing biological identifiers, select columns for mapping, configure mapping options, and download the enriched results.

The implementation prioritizes:
- Simplicity while maintaining extensibility
- Clean separation of concerns
- Effective use of existing Biomapper components
- AI-friendly code patterns for future enhancements
- Maintainable and testable architecture

## Backend Implementation (FastAPI)

### Project Structure

```
biomapper-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration management
│   │   ├── security.py      # API security (tokens, etc.)
│   │   └── session.py       # Session management
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── files.py     # File upload/management endpoints
│   │   │   ├── mapping.py   # Mapping operation endpoints
│   │   │   └── health.py    # Health check endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── file.py          # File-related schemas
│   │   ├── mapping.py       # Mapping-related schemas
│   │   └── job.py           # Job status and results schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_service.py   # CSV file processing
│   │   ├── mapper_service.py # Integration with Biomapper
│   │   └── job_service.py   # Background job management
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py    # File handling utilities
│       └── error_utils.py   # Error handling utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test configuration
│   ├── test_files.py        # File endpoint tests
│   └── test_mapping.py      # Mapping endpoint tests
├── .env                     # Environment variables
├── pyproject.toml           # Project dependencies
├── Dockerfile               # Container definition
└── README.md                # Project documentation
```

### Core Components

1. **Session Management**
   - Handles user sessions for file uploads and mapping jobs
   - Generates unique session IDs for maintaining state
   - Manages temporary file storage and cleanup

2. **Background Tasks**
   - Processes mapping operations asynchronously
   - Provides job status updates
   - Handles errors and retries

3. **File Management**
   - CSV file validation and processing
   - Secure temporary storage
   - File cleanup after processing

### API Endpoints

#### File Management

```python
# POST /api/files/upload
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = Depends()
) -> FileUploadResponse:
    """Upload a CSV file for mapping."""
    # Implementation
```

```python
# GET /api/files/{session_id}/columns
@router.get("/{session_id}/columns", response_model=ColumnsResponse)
async def get_columns(
    session_id: str
) -> ColumnsResponse:
    """Get column names from an uploaded CSV file."""
    # Implementation
```

```python
# GET /api/files/{session_id}/preview
@router.get("/{session_id}/preview", response_model=CSVPreviewResponse)
async def preview_file(
    session_id: str,
    limit: int = 10
) -> CSVPreviewResponse:
    """Get a preview of the CSV data."""
    # Implementation
```

#### Mapping Operations

```python
# POST /api/mapping/jobs
@router.post("/jobs", response_model=MappingJobResponse)
async def create_mapping_job(
    job_config: MappingJobCreate,
    background_tasks: BackgroundTasks = Depends()
) -> MappingJobResponse:
    """Create a new mapping job."""
    # Implementation
```

```python
# GET /api/mapping/jobs/{job_id}/status
@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(
    job_id: str
) -> JobStatus:
    """Get the status of a mapping job."""
    # Implementation
```

```python
# GET /api/mapping/jobs/{job_id}/results
@router.get("/jobs/{job_id}/results", response_model=MappingResults)
async def get_job_results(
    job_id: str
) -> MappingResults:
    """Get the results of a completed mapping job."""
    # Implementation
```

```python
# GET /api/mapping/jobs/{job_id}/download
@router.get("/jobs/{job_id}/download")
async def download_results(
    job_id: str
) -> StreamingResponse:
    """Download the mapped CSV file."""
    # Implementation
```

### Service Layer

#### CSVService

```python
class CSVService:
    """Service for CSV file operations."""
    
    async def save_file(self, session_id: str, file: UploadFile) -> str:
        """Save uploaded file to temporary storage."""
        # Implementation
    
    async def get_columns(self, session_id: str) -> List[str]:
        """Get column names from a CSV file."""
        # Implementation
    
    async def preview_data(self, session_id: str, limit: int = 10) -> Dict:
        """Get preview of CSV data."""
        # Implementation
```

#### MapperService

```python
class MapperService:
    """Service for mapping operations."""
    
    async def create_job(
        self, 
        session_id: str, 
        columns: List[str], 
        target_ontologies: List[str]
    ) -> str:
        """Create a new mapping job."""
        # Implementation
    
    async def process_mapping_job(self, job_id: str) -> None:
        """Process a mapping job (runs asynchronously)."""
        # Implementation using Biomapper components
    
    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get the status of a mapping job."""
        # Implementation
    
    async def get_job_results(self, job_id: str) -> MappingResults:
        """Get the results of a completed mapping job."""
        # Implementation
```

### Data Models

#### File Models

```python
class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    session_id: str
    filename: str
    created_at: datetime
    
class ColumnsResponse(BaseModel):
    """Response model for column retrieval."""
    columns: List[str]
    
class CSVPreviewResponse(BaseModel):
    """Response model for CSV preview."""
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
```

#### Mapping Models

```python
class MappingJobCreate(BaseModel):
    """Request model for creating a mapping job."""
    session_id: str
    id_columns: List[str]
    target_ontologies: List[str]
    options: Optional[Dict[str, Any]] = None
    
class MappingJobResponse(BaseModel):
    """Response model for mapping job creation."""
    job_id: str
    created_at: datetime
    
class JobStatus(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
class MappingResults(BaseModel):
    """Response model for mapping results."""
    job_id: str
    summary: Dict[str, Any]
    preview: List[Dict[str, Any]]
    download_url: str
```

### Error Handling

Implement a consistent error handling strategy:

```python
class APIError(Exception):
    """Base API error class."""
    def __init__(
        self, 
        status_code: int,
        detail: str,
        error_code: str = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(self.detail)

# Error handler
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )
```

### Testing Strategy

1. **Unit Tests**
   - Test each service in isolation with mocked dependencies
   - Validate request/response models

2. **Integration Tests**
   - Test API endpoints with test clients
   - Verify correct interaction between services

3. **End-to-End Tests**
   - Complete workflows from file upload to result download
   - Test with real CSV files

## Frontend Implementation (Mantine)

### Project Setup

```
biomapper-ui/
├── public/
│   ├── favicon.ico
│   └── assets/
├── src/
│   ├── main.tsx            # Entry point
│   ├── App.tsx             # Root component
│   ├── config/
│   │   └── api.ts          # API configuration
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx   # Main layout wrapper
│   │   │   ├── Navbar.tsx     # Side navigation
│   │   │   └── Header.tsx     # Top header
│   │   ├── common/
│   │   │   ├── LoadingOverlay.tsx
│   │   │   ├── ErrorAlert.tsx
│   │   │   └── ActionButton.tsx
│   │   ├── file-upload/
│   │   │   ├── FileUploader.tsx
│   │   │   ├── CSVPreview.tsx
│   │   │   └── ColumnSelector.tsx
│   │   ├── mapping/
│   │   │   ├── MappingConfig.tsx
│   │   │   ├── JobStatus.tsx
│   │   │   └── ResultsViewer.tsx
│   ├── features/
│   │   ├── upload/
│   │   │   ├── UploadPage.tsx
│   │   │   └── uploadSlice.ts
│   │   ├── mapping/
│   │   │   ├── MappingPage.tsx
│   │   │   └── mappingSlice.ts
│   │   └── results/
│   │       ├── ResultsPage.tsx
│   │       └── resultsSlice.ts
│   ├── services/
│   │   ├── api.ts          # API client
│   │   ├── fileService.ts  # File-related API calls
│   │   └── mappingService.ts # Mapping-related API calls
│   ├── types/
│   │   ├── file.ts
│   │   ├── mapping.ts
│   │   └── job.ts
│   ├── utils/
│   │   ├── formatters.ts
│   │   └── validators.ts
│   └── hooks/
│       ├── useFileUpload.ts
│       ├── useColumns.ts
│       └── useMapping.ts
├── tests/
│   ├── components/
│   │   ├── FileUploader.test.tsx
│   │   └── ResultsViewer.test.tsx
│   └── services/
│       └── api.test.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

### Component Architecture

#### Core Pages

1. **UploadPage**
   - File upload with drag-and-drop
   - CSV preview and validation
   - Navigation to column selection

2. **MappingPage**
   - Column selection for ID fields
   - Target ontology selection
   - Mapping configuration options
   - Job submission

3. **ResultsPage**
   - Job status monitoring
   - Results preview and visualization
   - Download options

#### Layout Components

1. **AppShell**
   - Main layout wrapper from Mantine
   - Responsive sidebar and header
   - Content area

2. **Navbar**
   - Navigation links
   - Process status indicator
   - Help resources

### State Management

Use React Query for API state and Redux Toolkit for application state:

```typescript
// Example Redux slice for file upload
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UploadState {
  sessionId: string | null;
  columns: string[];
  isUploading: boolean;
  error: string | null;
}

const initialState: UploadState = {
  sessionId: null,
  columns: [],
  isUploading: false,
  error: null,
};

export const uploadSlice = createSlice({
  name: 'upload',
  initialState,
  reducers: {
    setSessionId: (state, action: PayloadAction<string>) => {
      state.sessionId = action.payload;
    },
    setColumns: (state, action: PayloadAction<string[]>) => {
      state.columns = action.payload;
    },
    setUploading: (state, action: PayloadAction<boolean>) => {
      state.isUploading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    resetUpload: (state) => {
      return initialState;
    },
  },
});
```

### UI/UX Components

#### FileUploader

```tsx
import { Group, Text, useMantineTheme, rem } from '@mantine/core';
import { Dropzone, DropzoneProps } from '@mantine/dropzone';
import { IconUpload, IconX, IconFile } from '@tabler/icons-react';

export function FileUploader({ onUpload }: { onUpload: (file: File) => void }) {
  const theme = useMantineTheme();
  
  return (
    <Dropzone
      onDrop={(files) => onUpload(files[0])}
      maxSize={3 * 1024 ** 2}
      accept={['text/csv', 'application/vnd.ms-excel']}
    >
      <Group position="center" spacing="xl" style={{ minHeight: rem(220), pointerEvents: 'none' }}>
        <Dropzone.Accept>
          <IconUpload
            size="3.2rem"
            stroke={1.5}
            color={theme.colors[theme.primaryColor][theme.colorScheme === 'dark' ? 4 : 6]}
          />
        </Dropzone.Accept>
        <Dropzone.Reject>
          <IconX
            size="3.2rem"
            stroke={1.5}
            color={theme.colors.red[theme.colorScheme === 'dark' ? 4 : 6]}
          />
        </Dropzone.Reject>
        <Dropzone.Idle>
          <IconFile size="3.2rem" stroke={1.5} />
        </Dropzone.Idle>

        <div>
          <Text size="xl" inline>
            Drag CSV file here or click to select
          </Text>
          <Text size="sm" color="dimmed" inline mt={7}>
            Files should not exceed 3MB
          </Text>
        </div>
      </Group>
    </Dropzone>
  );
}
```

#### ColumnSelector

```tsx
import { useState } from 'react';
import { Table, Checkbox, Button, Group, Text } from '@mantine/core';

interface ColumnSelectorProps {
  columns: string[];
  onSelect: (selected: string[]) => void;
}

export function ColumnSelector({ columns, onSelect }: ColumnSelectorProps) {
  const [selected, setSelected] = useState<string[]>([]);
  
  const handleToggle = (column: string) => {
    setSelected((current) => 
      current.includes(column) 
        ? current.filter(c => c !== column) 
        : [...current, column]
    );
  };
  
  return (
    <>
      <Text size="lg" weight={500} mb="md">
        Select columns containing identifiers to map:
      </Text>
      
      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>Select</th>
            <th>Column Name</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((column) => (
            <tr key={column}>
              <td>
                <Checkbox
                  checked={selected.includes(column)}
                  onChange={() => handleToggle(column)}
                />
              </td>
              <td>{column}</td>
            </tr>
          ))}
        </tbody>
      </Table>
      
      <Group position="right" mt="md">
        <Button 
          onClick={() => onSelect(selected)}
          disabled={selected.length === 0}
        >
          Continue with Selected Columns
        </Button>
      </Group>
    </>
  );
}
```

### API Integration

Use React Query for API calls:

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { fileService } from '../services/fileService';

export function useFileUpload() {
  const uploadMutation = useMutation({
    mutationFn: fileService.uploadFile,
    onSuccess: (data) => {
      queryClient.invalidateQueries(['columns', data.sessionId]);
    },
  });
  
  return {
    uploadFile: uploadMutation.mutate,
    isUploading: uploadMutation.isLoading,
    error: uploadMutation.error,
    sessionId: uploadMutation.data?.sessionId,
  };
}

export function useColumns(sessionId: string | null) {
  return useQuery({
    queryKey: ['columns', sessionId],
    queryFn: () => fileService.getColumns(sessionId!),
    enabled: !!sessionId,
  });
}
```

### Testing Strategy

1. **Component Tests**
   - Test UI components in isolation
   - Validate user interactions

2. **Integration Tests**
   - Test API integration with mocked responses
   - Verify rendering of data

3. **End-to-End Tests**
   - Complete user workflows
   - File upload and download functionality

## Integration Workflow

The complete user workflow will be:

1. **Upload Phase**
   - User uploads CSV file
   - System validates file format
   - CSV preview is displayed

2. **Configuration Phase**
   - User selects ID columns
   - User chooses target ontologies
   - User sets optional mapping parameters

3. **Processing Phase**
   - System creates mapping job
   - User sees progress indication
   - Job runs asynchronously

4. **Results Phase**
   - User views mapping results summary
   - Preview of mapped data is displayed
   - User can download enriched CSV

## Development Timeline

### Week 1: Setup and Core Infrastructure
- Set up FastAPI project structure
- Implement file upload and session management
- Create basic Mantine frontend scaffolding

### Week 2: API Implementation
- Develop mapping job endpoints
- Implement CSV service functionality
- Add background task processing

### Week 3: Frontend Core Components
- Implement file upload and preview components
- Create column selection interface
- Build mapping configuration interface

### Week 4: Integration and Results
- Connect frontend to API endpoints
- Implement job status monitoring
- Create results visualization and download

### Week 5: Testing and Refinement
- Implement unit and integration tests
- Refine UI/UX based on feedback
- Performance optimization

## Extensibility Considerations

### Backend Extensibility
- Use dependency injection for easy component replacement
- Implement service interfaces for potential alternative implementations
- Version API endpoints for future changes

### Frontend Extensibility
- Component-based architecture for easy replacement
- Clear separation of UI components and business logic
- Theme customization for potential whitelabeling

## Deployment Options

### Local Development
- FastAPI backend on localhost:8000
- React frontend on localhost:3000
- Proxy configuration for API requests

### Production Deployment
- Docker containers for backend and frontend
- Nginx for static file serving and API routing
- Environment variables for configuration
