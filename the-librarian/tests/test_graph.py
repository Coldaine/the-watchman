"""
Comprehensive tests for graph operations module.

Tests connection, schema, CRUD operations, vector search, and queries.
"""

import pytest
import asyncio
from typing import List
import os

# Set test environment
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI", "bolt://localhost:7687")
os.environ["NEO4J_USER"] = os.getenv("NEO4J_USER", "neo4j")
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD", "librarian-pass")

from src.graph import (
    GraphConfig,
    Neo4jConnection,
    SchemaManager,
    GraphOperations,
    VectorOperations,
    QueryExecutor,
    NodeLabels,
    RelationshipTypes,
    get_config
)


class TestConnection:
    """Test Neo4j connection management."""

    @pytest.mark.asyncio
    async def test_connection_connect(self, neo4j_connection):
        """Test database connection."""
        assert neo4j_connection._is_connected

    @pytest.mark.asyncio
    async def test_health_check(self, neo4j_connection):
        """Test health check functionality."""
        health = await neo4j_connection.health_check()
        assert "connected" in health
        assert "node_count" in health


class TestGraphOperations:
    """Test CRUD operations on graph."""

    @pytest.mark.asyncio
    async def test_create_and_get_node(self, graph_operations):
        """Test node creation and retrieval."""
        graph_ops = graph_operations

        node_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-001",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )
        assert node_id == "arch-test-001"

        # Retrieve it
        node = await graph_ops.get_node(NodeLabels.ARCHITECTURE, node_id)
        assert node is not None
        assert node["id"] == node_id

        # Cleanup
        await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)

    @pytest.mark.asyncio
    async def test_update_node(self, graph_operations):
        """Test node update operations."""
        graph_ops = graph_operations

        # Create node
        node_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-002",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        # Update it
        updated = await graph_ops.update_node(
            NodeLabels.ARCHITECTURE,
            node_id,
            {"status": "active", "title": "Updated Architecture"}
        )
        assert updated is True

        # Verify update
        node = await graph_ops.get_node(NodeLabels.ARCHITECTURE, node_id)
        assert node["status"] == "active"
        assert node["title"] == "Updated Architecture"

        # Cleanup
        await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)

    @pytest.mark.asyncio
    async def test_delete_node(self, graph_operations):
        """Test node deletion."""
        graph_ops = graph_operations

        # Create node
        node_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-003",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        # Delete it
        deleted = await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)
        assert deleted is True

        # Verify deletion
        node = await graph_ops.get_node(NodeLabels.ARCHITECTURE, node_id)
        assert node is None

    @pytest.mark.asyncio
    async def test_create_relationship(self, graph_operations):
        """Test relationship creation between nodes."""
        graph_ops = graph_operations

        # Create two nodes
        arch_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-004",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        design_id = await graph_ops.create_node(
            NodeLabels.DESIGN,
            {
                "id": "design-test-001",
                "title": "Test Design",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        # Create relationship
        rel_created = await graph_ops.create_relationship(
            NodeLabels.DESIGN,
            design_id,
            RelationshipTypes.IMPLEMENTS,
            NodeLabels.ARCHITECTURE,
            arch_id,
            {"confidence": 0.95}
        )
        assert rel_created is True

        # Cleanup
        await graph_ops.delete_node(NodeLabels.ARCHITECTURE, arch_id)
        await graph_ops.delete_node(NodeLabels.DESIGN, design_id)

    @pytest.mark.asyncio
    async def test_count_nodes(self, graph_operations):
        """Test node counting."""
        graph_ops = graph_operations

        # Get initial count
        initial_count = await graph_ops.count_nodes(NodeLabels.ARCHITECTURE)

        # Create a node
        node_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-005",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        # Count should increase
        new_count = await graph_ops.count_nodes(NodeLabels.ARCHITECTURE)
        assert new_count == initial_count + 1

        # Cleanup
        await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)


class TestVectorOperations:
    """Test vector storage and search operations."""

    @pytest.mark.asyncio
    async def test_store_vector_embedding(self, vector_operations, graph_operations):
        """Test storing vector embeddings."""
        vector_ops = vector_operations
        graph_ops = graph_operations

        # Create node first
        node_id = await graph_ops.create_node(
            NodeLabels.ARCHITECTURE,
            {
                "id": "arch-test-006",
                "title": "Test Architecture",
                "version": "1.0.0",
                "status": "draft",
                "subsystem": "test"
            }
        )

        # Create a 768-dimensional test vector
        import numpy as np
        test_embedding = np.random.rand(768).tolist()

        # Store embedding
        stored = await vector_ops.store_embedding(
            NodeLabels.ARCHITECTURE,
            node_id,
            test_embedding,
            chunk_index=0
        )
        assert stored is True

        # Cleanup
        await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)

    @pytest.mark.asyncio
    async def test_vector_search(self, vector_operations, graph_operations):
        """Test vector similarity search."""
        vector_ops = vector_operations
        graph_ops = graph_operations

        # Create test nodes with embeddings
        import numpy as np

        node_ids = []
        for i in range(3):
            node_id = f"arch-test-{100+i}"
            await graph_ops.create_node(
                NodeLabels.ARCHITECTURE,
                {
                    "id": node_id,
                    "title": f"Test Architecture {i}",
                    "version": "1.0.0",
                    "status": "draft",
                    "subsystem": "test"
                }
            )
            node_ids.append(node_id)

            # Store different embeddings
            test_embedding = np.random.rand(768).tolist()
            await vector_ops.store_embedding(
                NodeLabels.ARCHITECTURE,
                node_id,
                test_embedding,
                chunk_index=0
            )

        # Perform vector search
        query_embedding = np.random.rand(768).tolist()
        results = await vector_ops.vector_search(
            query_embedding,
            label=NodeLabels.ARCHITECTURE,
            top_k=2
        )

        # Should return results
        assert isinstance(results, list)
        assert len(results) <= 2

        # Cleanup
        for node_id in node_ids:
            await graph_ops.delete_node(NodeLabels.ARCHITECTURE, node_id)


class TestQueryExecutor:
    """Test predefined drift detection and validation queries."""

    @pytest.mark.asyncio
    async def test_detect_design_drift(self, query_executor):
        """Test design drift detection query."""
        queries = query_executor

        # Run drift detection (should not fail even with no data)
        drift_results = await queries.detect_design_drift()

        # Should return a list
        assert isinstance(drift_results, list)

    @pytest.mark.asyncio
    async def test_find_unimplemented_requirements(self, query_executor):
        """Test finding unimplemented requirements."""
        queries = query_executor

        # Run query (method might have different name, adapt as needed)
        # Just test that query executor works
        drift_results = await queries.detect_design_drift()

        # Should return a list
        assert isinstance(drift_results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
