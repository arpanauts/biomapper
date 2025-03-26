# Biomapper Web UI MVP Implementation Plan

This document outlines the plan for a Minimum Viable Product (MVP) web interface for the Biomapper biological data harmonization and ontology mapping toolkit, focused specifically on CSV file mapping functionality.

## MVP Scope

A web application that allows users to:
1. Upload a CSV file containing metabolite or protein identifiers
2. Select which column(s) contain IDs to be mapped
3. Choose target ID types for mapping
4. Process the mapping using Biomapper's core functionality
5. Download the original CSV enriched with new ID columns

## Technical Implementation

### 1. Backend API (FastAPI)

```
biomapper-api/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application
│   ├── routers/
│   │   ├── __init__.py
│   │   └── mapping.py         # Mapping endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_service.py     # CSV handling
│   │   └── mapper_service.py  # Biomapper integration
│   └── models/
│       ├── __init__.py
│       └── schemas.py         # Pydantic models
├── tests/
└── requirements.txt
```

#### Key API Endpoints

1. `POST /api/upload` - Upload CSV file and return a session ID
2. `GET /api/columns/{session_id}` - Get columns from the uploaded CSV
3. `POST /api/map` - Process mapping operation with the following parameters:
   - Session ID
   - Source column(s)
   - Target ID types
   - Mapping options
4. `GET /api/download/{session_id}` - Download the processed CSV

#### Backend Implementation Steps

1. **Setup FastAPI Project** (1 day)
   - Set up the basic project structure
   - Configure dependencies and environment

2. **CSV Handling Service** (2 days)
   - Create service for parsing and manipulating CSV files
   - Implement temporary file storage for session management

3. **Mapper Integration** (3 days)
   - Create service layer to integrate with Biomapper
   - Focus specifically on MetaboliteNameMapper and any protein mapping equivalent
   - Expose configuration options

4. **API Endpoints** (2 days)
   - Implement the file upload/download endpoints
   - Build the mapping processing endpoint
   - Create progress tracking functionality

5. **Testing & Refinement** (2 days)
   - Write integration tests
   - Performance optimization

### 2. Frontend (React)

```
biomapper-ui/
├── public/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── FileUpload.tsx     # CSV upload component
│   │   ├── ColumnSelector.tsx # Column selection interface
│   │   ├── MappingOptions.tsx # Mapping configuration
│   │   └── Results.tsx        # Results display and download
│   ├── services/
│   │   └── api.ts             # API client
│   └── models/
│       └── types.ts           # TypeScript interfaces
├── package.json
└── tsconfig.json
```

#### Frontend Implementation Steps

1. **Setup React Project** (1 day)
   - Initialize with Create React App or Vite
   - Configure TypeScript and basic dependencies

2. **File Upload Component** (1 day)
   - Create drag-and-drop CSV upload
   - Implement file validation

3. **Mapping Configuration UI** (2 days)
   - Build column selection interface
   - Create target ID type selection
   - Implement mapping options

4. **Results Display** (2 days)
   - Create data preview component
   - Implement download functionality
   - Add basic stats visualization

5. **API Integration & State Management** (1 day)
   - Connect UI to backend API
   - Implement proper state management
   - Handle errors and loading states

### 3. Integration and Deployment

1. **Local Development Setup** (1 day)
   - Configure Docker Compose for local development
   - Create development scripts

2. **Basic Deployment Configuration** (1 day)
   - Set up deployment scripts
   - Configure basic logging

## Implementation Timeline

Total estimated time: **3 weeks**

- **Week 1**: Backend foundation and core services
  - FastAPI setup
  - CSV handling
  - Biomapper integration

- **Week 2**: Frontend development
  - UI components
  - Form handling
  - API integration

- **Week 3**: Integration and refinement
  - Connect frontend and backend
  - Testing and bug fixes
  - Basic deployment setup

## Code Examples for Key Components

### Backend: FastAPI Mapping Endpoint

```python
@router.post("/map", response_model=MappingJobResponse)
async def create_mapping_job(
    mapping_request: MappingRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a mapping job that processes CSV data through Biomapper.
    """
    # Validate session exists
    csv_data = await csv_service.get_session_data(mapping_request.session_id)
    if not csv_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Add mapping task to background
    background_tasks.add_task(
        mapper_service.process_mapping,
        job_id=job_id,
        csv_data=csv_data,
        source_columns=mapping_request.source_columns,
        target_id_types=mapping_request.target_id_types,
        options=mapping_request.options
    )
    
    return MappingJobResponse(
        job_id=job_id,
        status="processing"
    )
```

### Frontend: Column Selection Component

```typescript
const ColumnSelector: React.FC<ColumnSelectorProps> = ({ 
  columns, 
  selectedColumns, 
  onSelectionChange 
}) => {
  return (
    <div className="p-4 border rounded shadow-sm">
      <h2 className="text-lg font-semibold mb-3">Select ID Columns to Map</h2>
      <p className="text-sm text-gray-600 mb-4">
        Choose the column(s) that contain identifiers you want to map to other formats.
      </p>
      
      <div className="space-y-2">
        {columns.map(column => (
          <div key={column} className="flex items-center">
            <input
              type="checkbox"
              id={`column-${column}`}
              checked={selectedColumns.includes(column)}
              onChange={() => {
                const newSelection = selectedColumns.includes(column)
                  ? selectedColumns.filter(c => c !== column)
                  : [...selectedColumns, column];
                onSelectionChange(newSelection);
              }}
              className="mr-2"
            />
            <label htmlFor={`column-${column}`}>{column}</label>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## Technical Considerations

1. **Session Management**
   - Use temporary file storage for CSV data
   - Implement cleanup for abandoned sessions

2. **Error Handling**
   - Provide clear feedback for mapping failures
   - Log errors comprehensively

3. **Performance**
   - Process large files efficiently
   - Implement background processing for long-running tasks

4. **Extensibility**
   - Design code to easily add new ID types
   - Keep UI components modular

## Next Steps After MVP

1. Add user authentication for persistent sessions
2. Implement job history to track past mapping operations
3. Add more advanced mapping options (confidence thresholds, etc.)
4. Integrate visualization for mapping results
5. Add the SPOKE pathway analysis capabilities

This MVP focuses on the core mapping functionality while establishing a foundation that can be extended to include the other features from the broader implementation plan.
