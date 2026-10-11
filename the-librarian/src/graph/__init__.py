"""
Graph Operations Module for Librarian Agent System.

This module provides complete Neo4j graph database functionality including:
- Connection management with pooling and health checks
- Schema creation and management
- CRUD operations for nodes and relationships
- Vector operations for semantic search
- Predefined queries for drift detection and validation

Usage:
    from src.graph import (
        GraphConfig,
        Neo4jConnection,
        SchemaManager,
        GraphOperations,
        VectorOperations,
        QueryExecutor,
        NodeLabels,
        RelationshipTypes
    )

    # Initialize connection
    conn = Neo4jConnection()
    await conn.connect()

    # Create schema
    schema = SchemaManager(conn)
    await schema.create_all_indexes()

    # Perform operations
    ops = GraphOperations(conn)
    node_id = await ops.create_node("Architecture", {...})

    # Vector search
    vector_ops = VectorOperations(conn)
    results = await vector_ops.vector_search(query_embedding)

    # Run queries
    queries = QueryExecutor(conn)
    drift = await queries.detect_design_drift()
"""

from .config import GraphConfig, get_config, reload_config
from .connection import Neo4jConnection, get_connection, close_connection
from .schema import (
    SchemaManager,
    NodeLabels,
    RelationshipTypes
)
from .operations import GraphOperations
from .vector_ops import VectorOperations
from .queries import QueryExecutor

__all__ = [
    # Configuration
    "GraphConfig",
    "get_config",
    "reload_config",

    # Connection
    "Neo4jConnection",
    "get_connection",
    "close_connection",

    # Schema
    "SchemaManager",
    "NodeLabels",
    "RelationshipTypes",

    # Operations
    "GraphOperations",
    "VectorOperations",
    "QueryExecutor",
]

__version__ = "1.0.0"
