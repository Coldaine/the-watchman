"""
Shared pytest fixtures for all test modules.

Provides common test infrastructure including:
- Neo4j connection fixtures
- Mock Ollama responses
- Test data factories
- Environment setup
"""

import os
import pytest
import asyncio
from typing import Dict, Any, List
from pathlib import Path

# Set test environment variables before any imports
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI", "bolt://localhost:7687")
os.environ["NEO4J_USER"] = os.getenv("NEO4J_USER", "neo4j")
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD", "librarian-pass")


# Import after environment setup
from src.graph import Neo4jConnection, GraphOperations, VectorOperations, QueryExecutor
from src.processing import DocumentParser, TextChunker, EmbeddingGenerator


# ============================================================================
# Session-scoped fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def docs_dir():
    """Path to docs directory."""
    return Path(__file__).parent.parent / "docs"


# ============================================================================
# Neo4j Connection Fixtures
# ============================================================================

@pytest.fixture(scope="function")
async def neo4j_connection():
    """Fixture providing a Neo4j connection."""
    conn = Neo4jConnection()
    await conn.connect()
    yield conn
    await conn.close()


@pytest.fixture(scope="function")
async def graph_operations(neo4j_connection):
    """Fixture providing GraphOperations instance."""
    return GraphOperations(neo4j_connection)


@pytest.fixture(scope="function")
async def vector_operations(neo4j_connection):
    """Fixture providing VectorOperations instance."""
    return VectorOperations(neo4j_connection)


@pytest.fixture(scope="function")
async def query_executor(neo4j_connection):
    """Fixture providing QueryExecutor instance."""
    return QueryExecutor(neo4j_connection)


# ============================================================================
# Processing Fixtures
# ============================================================================

@pytest.fixture
def document_parser():
    """Fixture providing DocumentParser instance."""
    return DocumentParser()


@pytest.fixture
def text_chunker():
    """Fixture providing TextChunker instance."""
    return TextChunker(chunk_size=1000, chunk_overlap=200)


@pytest.fixture
def embedding_generator():
    """Fixture providing EmbeddingGenerator instance."""
    return EmbeddingGenerator()


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def architecture_node_factory():
    """Factory for creating test architecture node data."""
    def _create(node_id: str = "test-arch-001", **overrides) -> Dict[str, Any]:
        data = {
            "id": node_id,
            "title": "Test Architecture",
            "version": "1.0.0",
            "status": "draft",
            "subsystem": "test",
            "compliance_level": "strict",
            "drift_tolerance": "none"
        }
        data.update(overrides)
        return data
    return _create


@pytest.fixture
def design_node_factory():
    """Factory for creating test design node data."""
    def _create(node_id: str = "test-design-001", **overrides) -> Dict[str, Any]:
        data = {
            "id": node_id,
            "title": "Test Design",
            "version": "1.0.0",
            "status": "draft",
            "subsystem": "test",
            "design_type": "component"
        }
        data.update(overrides)
        return data
    return _create


@pytest.fixture
def requirement_node_factory():
    """Factory for creating test requirement node data."""
    def _create(req_id: str = "REQ-001", **overrides) -> Dict[str, Any]:
        data = {
            "rid": req_id,
            "title": "Test Requirement",
            "description": "Test requirement description",
            "priority": "high",
            "status": "draft"
        }
        data.update(overrides)
        return data
    return _create


@pytest.fixture
def test_embedding():
    """Factory for creating test embeddings."""
    def _create(dimensions: int = 768) -> List[float]:
        import numpy as np
        return np.random.rand(dimensions).tolist()
    return _create


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    def _create(embedding_dim: int = 768) -> Dict[str, Any]:
        import numpy as np
        return {
            "model": "nomic-embed-text",
            "embedding": np.random.rand(embedding_dim).tolist()
        }
    return _create


# ============================================================================
# Test File Fixtures
# ============================================================================

@pytest.fixture
def sample_architecture_markdown():
    """Sample architecture document content."""
    return """---
doc: architecture
subsystem: test
id: test-arch-001
version: 1.0.0
status: draft
owners:
  - test-team
compliance_level: strict
drift_tolerance: none
---

# Test Architecture

## Overview

This is a test architecture document.

## Components

### Component A

Component A handles processing.

### Component B

Component B handles storage.

## Integration

Components integrate via REST API.
"""


@pytest.fixture
def sample_design_markdown():
    """Sample design document content."""
    return """---
doc: design
subsystem: test
id: test-design-001
version: 1.0.0
status: draft
owners:
  - test-team
---

# Test Design

## Purpose

This design implements the test architecture.

## Implementation

Uses Python and FastAPI.
"""


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture
async def cleanup_test_nodes(neo4j_connection):
    """Fixture to clean up test nodes after tests."""
    created_nodes = []

    def register(label: str, node_id: str):
        """Register a node for cleanup."""
        created_nodes.append((label, node_id))

    yield register

    # Cleanup
    graph_ops = GraphOperations(neo4j_connection)
    for label, node_id in created_nodes:
        try:
            await graph_ops.delete_node(label, node_id)
        except Exception as e:
            print(f"Warning: Failed to cleanup node {label}:{node_id}: {e}")


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "requires_neo4j: mark test as requiring Neo4j connection"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: mark test as requiring Ollama service"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Test Collection Hooks
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add requires_neo4j marker to graph tests
        if "test_graph" in str(item.fspath):
            item.add_marker(pytest.mark.requires_neo4j)

        # Add requires_ollama marker to embedding tests
        if "embedding" in item.name.lower() or "ollama" in item.name.lower():
            item.add_marker(pytest.mark.requires_ollama)

        # Add slow marker to processing tests
        if "process_directory" in item.name:
            item.add_marker(pytest.mark.slow)
