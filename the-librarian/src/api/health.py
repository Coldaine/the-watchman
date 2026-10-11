"""Health check endpoints for Kubernetes and monitoring."""

from fastapi import APIRouter, HTTPException, status
import logging
import time
from datetime import datetime
from typing import Dict, Any
import psutil

from src.graph.connection import get_connection
from src.processing.embedder import EmbeddingGenerator
from src.api.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Track application start time for uptime calculation
START_TIME = time.time()


@router.get("/health/live")
async def liveness():
    """
    Kubernetes liveness probe.

    Returns 200 if the application process is alive.
    This endpoint should not depend on external services.

    Returns:
        Basic liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
async def readiness():
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to serve traffic.
    Checks that all critical dependencies are available.

    Returns:
        Readiness status with dependency checks
    """
    checks = {
        "neo4j": await check_neo4j(),
        "ollama": await check_ollama(),
        "disk": check_disk_space(),
        "memory": check_memory()
    }

    all_ready = all(checks.values())
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Detailed health check with system metrics.

    Provides comprehensive health status including:
    - Service connectivity (Neo4j, Ollama)
    - System resources (CPU, memory, disk)
    - Application uptime
    - Component versions

    Returns:
        HealthResponse with detailed status
    """
    # Check Neo4j
    neo4j_healthy = False
    neo4j_details = {}

    try:
        conn = get_connection()
        health_data = await conn.health_check()
        neo4j_healthy = health_data.get("connected", False)

        # Get additional Neo4j details
        neo4j_details = {
            "available": neo4j_healthy,
            "version": health_data.get("version", "unknown"),
            "server_info": health_data.get("server_info", {})
        }

        logger.info(f"Neo4j health check: {neo4j_healthy}")
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        neo4j_details = {
            "available": False,
            "error": str(e)
        }

    # Check Ollama
    ollama_healthy = False
    ollama_details = {}

    try:
        embedder = EmbeddingGenerator()
        ollama_healthy = embedder.check_connection()

        if ollama_healthy:
            model_available = embedder.check_model_available()
            ollama_details = {
                "available": True,
                "model_available": model_available,
                "model": embedder.model_name,
                "embedding_dim": 768
            }
        else:
            ollama_details = {
                "available": False
            }

        logger.info(f"Ollama health check: {ollama_healthy}")
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        ollama_details = {
            "available": False,
            "error": str(e)
        }

    # Get system metrics
    system_metrics = get_system_metrics()

    # Determine overall status
    overall_status = "healthy" if (neo4j_healthy and ollama_healthy) else "degraded"

    return HealthResponse(
        status=overall_status,
        neo4j=neo4j_healthy,
        ollama=ollama_healthy,
        version="0.1.0",
        uptime_seconds=get_uptime(),
        details={
            "components": {
                "neo4j": neo4j_details,
                "ollama": ollama_details
            },
            "system": system_metrics
        }
    )


async def check_neo4j() -> bool:
    """
    Check if Neo4j is available.

    Returns:
        True if Neo4j is reachable and healthy
    """
    try:
        conn = get_connection()
        health_data = await conn.health_check()
        return health_data.get("connected", False)
    except Exception as e:
        logger.error(f"Neo4j check failed: {e}")
        return False


async def check_ollama() -> bool:
    """
    Check if Ollama is available.

    Returns:
        True if Ollama is reachable
    """
    try:
        embedder = EmbeddingGenerator()
        return embedder.check_connection()
    except Exception as e:
        logger.error(f"Ollama check failed: {e}")
        return False


def check_disk_space(threshold: float = 90.0) -> bool:
    """
    Check if sufficient disk space is available.

    Args:
        threshold: Maximum disk usage percentage before failing check

    Returns:
        True if disk usage is below threshold
    """
    try:
        usage = psutil.disk_usage('/')
        return usage.percent < threshold
    except Exception as e:
        logger.error(f"Disk check failed: {e}")
        return False


def check_memory(threshold: float = 90.0) -> bool:
    """
    Check if sufficient memory is available.

    Args:
        threshold: Maximum memory usage percentage before failing check

    Returns:
        True if memory usage is below threshold
    """
    try:
        memory = psutil.virtual_memory()
        return memory.percent < threshold
    except Exception as e:
        logger.error(f"Memory check failed: {e}")
        return False


def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system resource metrics.

    Returns:
        Dictionary with CPU, memory, and disk metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_available_gb": disk.free / (1024 * 1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "error": str(e)
        }


def get_uptime() -> float:
    """
    Get application uptime in seconds.

    Returns:
        Uptime in seconds since application start
    """
    return time.time() - START_TIME
