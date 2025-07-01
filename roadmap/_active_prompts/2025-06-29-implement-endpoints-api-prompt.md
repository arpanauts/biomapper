# Prompt: Implement Missing Endpoints API Route

**Objective:**

Your task is to implement a critical, missing feature in the `biomapper-api`: an API route that allows clients to retrieve a list of all available data endpoints from the database. This is essential for the service-oriented architecture and is currently blocking all pipeline execution and verification.

**Problem Description:**

Currently, any request to `/api/endpoints` results in a `404 Not Found` error because the route does not exist. You must build this functionality from the ground up, touching the service layer, the API routing layer, and the data models.

--- 

### **Part 1: Implement the Service Layer Logic**

**File to Modify:**

*   `/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py`

**Implementation Steps:**

1.  **Add Necessary Imports:** You will need to import the `Endpoint` model from `biomapper.db.models` and `select` from `sqlalchemy`.

2.  **Create a New `get_endpoints` Method:** Add a new asynchronous method to the `MapperService` class that retrieves all `Endpoint` objects from the database.

    ```python
    from sqlalchemy import select
    from biomapper.db.models import Endpoint
    from typing import List

    # Inside the MapperService class

    async def get_endpoints(self) -> List[Endpoint]:
        """Retrieve all available endpoints from the database."""
        async with self.get_session() as session:
            stmt = select(Endpoint)
            result = await session.execute(stmt)
            endpoints = result.scalars().all()
            return list(endpoints)
    ```

--- 

### **Part 2: Create the API Route and Response Model**

**New File to Create:**

*   `/home/ubuntu/biomapper/biomapper-api/app/api/routes/endpoints.py`

**Implementation Steps:**

1.  **Create the new router file.**

2.  **Define the Pydantic Response Model:** Create a Pydantic model that defines the structure of a single endpoint in the API response. This should be a subset of the full database model.

    ```python
    from pydantic import BaseModel
    from typing import List

    class EndpointResponse(BaseModel):
        name: str
        description: str
        type: str

        class Config:
            orm_mode = True # Use this to map SQLAlchemy models to Pydantic models
    ```

3.  **Create the API Router and Route:** Define a new `APIRouter` and create a `GET /` route that uses the `get_endpoints` service method you created in Part 1.

    ```python
    from fastapi import APIRouter, Depends
    from app.services.mapper_service import MapperService
    from app.api.deps import get_mapper_service

    router = APIRouter()

    @router.get("/", response_model=List[EndpointResponse])
    async def list_endpoints(
        mapper_service: MapperService = Depends(get_mapper_service)
    ):
        """Retrieve a list of all available data endpoints."""
        return await mapper_service.get_endpoints()
    ```

--- 

### **Part 3: Integrate the New Router into the Main Application**

**File to Modify:**

*   `/home/ubuntu/biomapper/biomapper-api/app/main.py`

**Implementation Steps:**

1.  **Import the New Router:** Add `endpoints` to the list of imported routers.

    ```python
    from app.api.routes import files, mapping, health, strategies, endpoints
    ```

2.  **Include the New Router:** Add the `endpoints.router` to the FastAPI application with the correct prefix.

    ```python
    app.include_router(endpoints.router, prefix="/api/endpoints", tags=["endpoints"])
    ```

--- 

### **Verification**

After completing all steps, you must verify that the new endpoint is working correctly.

1.  **Restart the API Server:**
    ```bash
    # From the /home/ubuntu/biomapper/biomapper-api/ directory
    # (You may need to stop the existing one first: pkill uvicorn)
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    ```

2.  **Query the New Endpoint:**
    ```bash
    sleep 5
    curl http://localhost:8000/api/endpoints
    ```

**Expected Outcome:**

The `curl` command should now return a `200 OK` status and a JSON array containing the details of all endpoints stored in the database, including `UKBB_PROTEIN_ASSAY_ID`, `HPA_GENE_NAME`, and the critical `HPA_PROTEIN_DATA`. This will confirm that the feature is implemented correctly and the project is unblocked.
