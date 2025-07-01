import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import files, mapping, health, strategies, endpoints
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
app.include_router(endpoints.router, prefix="/api/endpoints", tags=["endpoints"])



@app.on_event("startup")
async def startup_event():
    """Initializes the mapper service on application startup."""
    logger.info("API starting up...")
    try:
        app.state.mapper_service = MapperService()
        logger.info("MapperService initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize MapperService during startup: {e}", exc_info=True)
        raise


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


