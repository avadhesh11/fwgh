"""
FastAPI Main Application Entrypoint for Wind Forecast Decision Portal.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Elexon BMRS Wind Generation Forecast vs Outturn Verification and Decision Portal.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend applications with explicit origins
cors_origins = settings.CORS_ORIGINS
allow_creds = False if "*" in cors_origins else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Root"])
def root_info():
    """Root metadata endpoint."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": f"{settings.API_PREFIX}/health"
    }
