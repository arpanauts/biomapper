import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import files, mapping, health, strategies
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.services.mapper_service import MapperService

# Configure logging before creating the FastAPI app
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Biomapper Web UI",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(mapping.router, prefix="/api/mapping", tags=["mapping"])
app.include_router(strategies.router)



@app.on_event("startup")
async def startup_event():
    """Initializes the mapper service on application startup."""
    import traceback
    import sys
    
    logger.info("API starting up...")
    
    try:
        # Add detailed logging before initialization
        logger.info("Attempting to initialize MapperService...")
        print("DEBUG: About to create MapperService instance", flush=True)
        
        app.state.mapper_service = MapperService()
        
        logger.info("MapperService initialized successfully")
        print("DEBUG: MapperService created successfully", flush=True)
        
    except Exception as e:
        # Log the full exception details
        error_msg = f"Failed to initialize MapperService: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        print(f"CRITICAL ERROR: {error_msg}", flush=True)
        
        # Print the full traceback to console
        traceback.print_exc()
        
        # Log the traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        # Exit with error code to make the failure visible
        print("EXITING DUE TO STARTUP FAILURE", flush=True)
        sys.exit(1)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception occurred", exc_info=exc, path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "detail": str(exc),
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


@app.get("/")
async def root():
    return {"message": "Welcome to Biomapper API. Visit /api/docs for documentation."}


