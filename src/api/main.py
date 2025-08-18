import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    health,
    strategies_v2_simple,
)
from src.api.core.config import settings
from src.api.core.logging_config import configure_logging
from src.api.services.mapper_service import MapperService

# Import actions to ensure registration
# This ensures all actions are registered before the API starts
try:
    # Protein actions
    from actions.entities.proteins.annotation import (  # noqa: F401
        extract_uniprot_from_xrefs,
        normalize_accessions,
    )
    from actions.entities.proteins.matching import multi_bridge, historical_resolution  # noqa: F401
    
    # Data processing actions - import the class to trigger registration
    from actions.utils.data_processing.parse_composite_identifiers import ParseCompositeIdentifiersAction  # noqa: F401
    
    # Report actions - import the classes to trigger registration
    from actions.reports.generate_html_report import GenerateHtmlReportAction  # noqa: F401
    from actions.reports.generate_visualizations import GenerateMappingVisualizationsAction  # noqa: F401
    
    # IO actions
    from actions.io import sync_to_google_drive_v2  # noqa: F401
    
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
# app.include_router(strategies.router)  # Disabled - conflicts with v2
app.include_router(strategies_v2_simple.router)  # Add v2 strategies endpoint


@app.on_event("startup")
async def startup_event():
    """Initializes services on application startup."""
    logger.info("API starting up...")


    # Initialize mapper service
    try:
        app.state.mapper_service = MapperService()
        logger.info("MapperService initialized successfully.")
    except Exception as e:
        logger.critical(
            f"Failed to initialize MapperService during startup: {e}", exc_info=True
        )
        raise



@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("API shutting down...")




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
