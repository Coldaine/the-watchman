"""
Librarian Agent FastAPI Application.

Main entry point for the AI Agent Governance System API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json
from datetime import datetime

from src.graph.connection import get_connection, close_connection
from src.api import agent, query, validation, admin, health
from src.api.middleware import TimingMiddleware, JSONLoggingMiddleware
from src.api.metrics import get_metrics_collector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting Librarian Agent API...")

    # Initialize Neo4j connection
    try:
        conn = get_connection()
        await conn.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Librarian Agent API...")
    await close_connection()
    logger.info("Connections closed")


# Create FastAPI application
app = FastAPI(
    title="Librarian Agent API",
    description="AI Agent Governance System - Specification-driven development oversight",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add timing and logging middleware
app.add_middleware(TimingMiddleware)
app.add_middleware(JSONLoggingMiddleware)


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(validation.router, prefix="/validation", tags=["Validation"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Librarian Agent API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


@app.get("/metrics")
async def metrics():
    """
    Get application metrics.

    Returns basic metrics about request processing,
    validation results, and system performance.

    Returns:
        Dictionary with current metrics
    """
    collector = get_metrics_collector()
    return collector.get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
