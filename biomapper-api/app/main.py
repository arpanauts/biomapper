from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import files, mapping, health
from app.core.config import settings

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


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
