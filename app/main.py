"""
The Watchman - Main FastAPI Application

Computer-centric knowledge graph system that tracks:
- System state (files, projects, containers, services)
- Changes and events
- Visual timeline (screenshots + OCR)
- MCP server registry and control
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from app.utils.config import get_settings
from app.utils.neo4j_client import get_neo4j_client, close_neo4j_client
from app.api import health, ask, admin, mcp


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")

    # Initialize Neo4j connection
    try:
        client = get_neo4j_client()
        logger.success("Neo4j connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down application...")
    close_neo4j_client()
    logger.success("Application shut down complete")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Computer-centric knowledge graph and context engine",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.log_level == "DEBUG" else "An error occurred"
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(ask.router, prefix="/ask", tags=["Query"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "The Watchman",
        "version": settings.api_version,
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
