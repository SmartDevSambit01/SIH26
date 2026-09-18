"""
SIH 2026 Landslide Early Warning System - FastAPI Application Entrypoint
Serves Kohima and Aizawl 500m risk grid data, baseline terrain susceptibility,
historical landslide evidence, and truthful dynamic sensor status.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import CORS_ORIGINS
from .routes import api_router
from .services import data_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ner_safe.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and caches project spatial and tabular datasets upon startup."""
    logger.info("Starting up SIH 2026 Landslide Risk API server...")
    data_service.load_all()
    yield
    logger.info("Shutting down SIH 2026 Landslide Risk API server.")


app = FastAPI(
    title="NER Safe - AI-Based Landslide Early Warning API",
    description=(
        "Backend data API for SIH 2026 pilot districts (Kohima, Nagaland and Aizawl, Mizoram). "
        "Provides 500m analysis grids, baseline terrain susceptibility (TSI), verified historical "
        "landslide records, and transparent status for dynamic meteorological/satellite sensors."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Include core API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
def read_root():
    """Service overview and API documentation entry point."""
    return {
        "service": "NER Safe - Landslide Early Warning System API",
        "pilot_districts": ["Kohima (Nagaland)", "Aizawl (Mizoram)"],
        "analysis_grid": "500m x 500m (16,961 cells)",
        "version": "0.1.0",
        "documentation": "/docs",
        "health_check": "/api/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors gracefully without leaking sensitive stack traces."""
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred while processing the request."},
    )
