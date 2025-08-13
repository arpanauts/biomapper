import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    files,
    mapping,
    health,
    endpoints,
    resources,
    jobs,
    strategies_v2_simple,
)
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging_config import configure_logging
from app.services.mapper_service import MapperService
from app.services.resource_manager import ResourceManager
from app.config.resources import RESOURCE_CONFIGURATION

# Import actions to ensure registration
# This ensures all actions are registered before the API starts
try:
    # Protein actions
    from biomapper.core.strategy_actions.entities.proteins.annotation import (
        extract_uniprot_from_xrefs,
        normalize_accessions,
    )
    from biomapper.core.strategy_actions.entities.proteins.matching import multi_bridge
    
    # IO actions
    from biomapper.core.strategy_actions.io import sync_to_google_drive_v2
    
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Strategy actions imported successfully")
except ImportError as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Some strategy actions could not be imported: {e}")

# Configure logging before creating the FastAPI app
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Biomapper Web UI with Resource Management",
    version="0.2.0",
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
# app.include_router(strategies.router)  # Disabled - conflicts with v2
app.include_router(strategies_v2_simple.router)  # Add v2 strategies endpoint
app.include_router(endpoints.router, prefix="/api/endpoints", tags=["endpoints"])
app.include_router(resources.router, prefix="/api", tags=["resources"])
app.include_router(jobs.router, tags=["jobs"])


@app.on_event("startup")
async def startup_event():
    """Initializes services on application startup."""
    logger.info("API starting up...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        # Don't raise - allow API to start even if database fails

    # Initialize mapper service
    try:
        app.state.mapper_service = MapperService()
        logger.info("MapperService initialized successfully.")
    except Exception as e:
        logger.critical(
            f"Failed to initialize MapperService during startup: {e}", exc_info=True
        )
        raise

    # Initialize resource manager
    try:
        app.state.resource_manager = ResourceManager(RESOURCE_CONFIGURATION)
        await app.state.resource_manager.initialize()
        logger.info("ResourceManager initialized successfully.")

        # Log resource status
        resources = await app.state.resource_manager.get_resource_status()
        logger.info(f"Resource status: {len(resources)} resources registered")
        for name, resource in resources.items():
            logger.info(f"  - {name}: {resource.status.value}")

    except Exception as e:
        logger.error(f"Failed to initialize ResourceManager: {e}", exc_info=True)
        # Don't raise - allow API to start even if resource manager fails
        app.state.resource_manager = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("API shutting down...")

    # Cleanup database
    try:
        await close_db()
        logger.info("Database connections closed successfully.")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}", exc_info=True)

    # Cleanup resource manager
    if hasattr(app.state, "resource_manager") and app.state.resource_manager:
        try:
            await app.state.resource_manager.cleanup()
            logger.info("ResourceManager cleaned up successfully.")
        except Exception as e:
            logger.error(f"Error cleaning up ResourceManager: {e}", exc_info=True)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception occurred",
        exc_info=exc,
        path=request.url.path,
        method=request.method,
    )
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
