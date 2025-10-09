"""
Pydantic models for The Watchman API.

Shared data models across the application.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =====================================================
# System Graph Models
# =====================================================

class FileNode(BaseModel):
    """File node model."""
    path: str
    name: str
    extension: Optional[str] = None
    size: Optional[int] = None
    last_modified: Optional[datetime] = None
    embedding: Optional[List[float]] = None


class DirectoryNode(BaseModel):
    """Directory node model."""
    path: str
    name: str
    size: Optional[int] = None


class ProjectNode(BaseModel):
    """Project node model."""
    id: str
    name: str
    type: Optional[str] = None
    path: str
    last_scan: Optional[datetime] = None


class SoftwareNode(BaseModel):
    """Software/package node model."""
    key: str
    name: str
    version: Optional[str] = None
    source: Optional[str] = None  # apt, brew, pip, etc.


class ContainerNode(BaseModel):
    """Docker container node model."""
    id: str
    name: str
    image: str
    state: str  # running, stopped, etc.
    created: Optional[datetime] = None


# =====================================================
# Visual Timeline Models
# =====================================================

class SnapshotNode(BaseModel):
    """Screenshot snapshot node model."""
    id: str
    ts: datetime
    app: Optional[str] = None
    window: Optional[str] = None
    path: str


class ChunkNode(BaseModel):
    """OCR text chunk node model."""
    content_hash: str
    text: str
    embedding: Optional[List[float]] = None


# =====================================================
# Event Models
# =====================================================

class EventNode(BaseModel):
    """Event node model."""
    id: str
    ts: datetime
    type: str  # CREATE, MODIFY, DELETE, START, STOP, etc.
    path: Optional[str] = None
    user: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# =====================================================
# MCP Models
# =====================================================

class ToolNode(BaseModel):
    """MCP tool node model."""
    key: str
    name: str
    schema: Optional[Dict[str, Any]] = None


class MCPServerNode(BaseModel):
    """MCP server node model."""
    name: str
    url: Optional[str] = None
    status: str  # up, down, degraded
    compose_file: Optional[str] = None


# =====================================================
# Query Models
# =====================================================

class QueryResult(BaseModel):
    """Generic query result."""
    nodes: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
    metadata: Optional[Dict[str, Any]] = None


class VectorSearchResult(BaseModel):
    """Vector search result."""
    node: Dict[str, Any]
    score: float
    text: Optional[str] = None


# =====================================================
# Response Models
# =====================================================

class OperationStatus(BaseModel):
    """Generic operation status."""
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
