"""
Pydantic models for The Watchman API.

Shared data models across the application.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# =====================================================
# System Graph Models
# =====================================================


class FileNode(BaseModel):
    """File node model."""

    path: str
    name: str
    extension: str | None = None
    size: int | None = None
    last_modified: datetime | None = None
    embedding: list[float] | None = None


class DirectoryNode(BaseModel):
    """Directory node model."""

    path: str
    name: str
    size: int | None = None


class ProjectNode(BaseModel):
    """Project node model."""

    id: str
    name: str
    type: str | None = None
    path: str
    last_scan: datetime | None = None


class SoftwareNode(BaseModel):
    """Software/package node model."""

    key: str
    name: str
    version: str | None = None
    source: str | None = None  # apt, brew, pip, etc.


class ContainerNode(BaseModel):
    """Docker container node model."""

    id: str
    name: str
    image: str
    state: str  # running, stopped, etc.
    created: datetime | None = None


# =====================================================
# Visual Timeline Models
# =====================================================


class SnapshotNode(BaseModel):
    """Screenshot snapshot node model."""

    id: str
    ts: datetime
    app: str | None = None
    window: str | None = None
    path: str


class ChunkNode(BaseModel):
    """OCR text chunk node model."""

    content_hash: str
    text: str
    embedding: list[float] | None = None


# =====================================================
# Event Models
# =====================================================


class EventNode(BaseModel):
    """Event node model."""

    id: str
    ts: datetime
    type: str  # CREATE, MODIFY, DELETE, START, STOP, etc.
    path: str | None = None
    user: str | None = None
    details: dict[str, Any] | None = None


# =====================================================
# MCP Models
# =====================================================


class ToolNode(BaseModel):
    """MCP tool node model."""

    key: str
    name: str
    schema: dict[str, Any] | None = None


class MCPServerNode(BaseModel):
    """MCP server node model."""

    name: str
    url: str | None = None
    status: str  # up, down, degraded
    compose_file: str | None = None


# =====================================================
# Query Models
# =====================================================


class QueryResult(BaseModel):
    """Generic query result."""

    nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    metadata: dict[str, Any] | None = None


class VectorSearchResult(BaseModel):
    """Vector search result."""

    node: dict[str, Any]
    score: float
    text: str | None = None


# =====================================================
# Response Models
# =====================================================


class OperationStatus(BaseModel):
    """Generic operation status."""

    status: str
    message: str
    details: dict[str, Any] | None = None
