"""
Health check endpoint.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from app.utils.neo4j_client import get_neo4j_client
from app.utils.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    neo4j_connected: bool
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Verifies:
    - API is running
    - Neo4j is connected
    """
    settings = get_settings()
    neo4j_connected = False

    try:
        client = get_neo4j_client()
        # Simple query to verify connection
        result = client.execute_read("RETURN 1 AS test")
        neo4j_connected = len(result) > 0
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if neo4j_connected else "degraded",
        timestamp=datetime.now(),
        neo4j_connected=neo4j_connected,
        version=settings.api_version
    )
