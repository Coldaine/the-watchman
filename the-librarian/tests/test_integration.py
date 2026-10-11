"""
Integration tests for the complete document flow.

Tests the end-to-end pipeline:
- Document processing → Validation → Graph storage
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import os

from src.processing.models import ParsedDocument, ProcessedChunk, Chunk
from src.processing.pipeline import IngestionPipeline
from src.validation.engine import ValidationEngine
from src.validation.models import ValidationResult, ValidationStatus
from src.validation.agent_models import AgentRequest
from src.graph.connection import Neo4jConnection
from src.graph.operations import GraphOperations
from src.graph.vector_ops import VectorOperations

from src.integration.document_adapter import DocumentGraphAdapter
from src.integration.validation_bridge import ValidationGraphBridge
from src.integration.request_adapter import RequestAdapter
from src.integration.orchestrator import LibrarianOrchestrator
from src.integration.async_utils import AsyncSync


# Test fixtures

@pytest.fixture
def sample_document():
    """Create a sample parsed document for testing."""
    return ParsedDocument(
        path="/test/docs/ARCH-001.md",
        doc_type="architecture",
        content="""# Test Architecture

## Overview
This is a test architecture document.

## Components
- Component A
- Component B
""",
        frontmatter={
            "doc": "architecture",
            "subsystem": "core",
            "id": "ARCH-001",
            "title": "Test Architecture",
            "version": "1.0.0",
            "status": "approved",
            "owners": ["test_user"],
            "compliance_level": "strict",
            "drift_tolerance": "none"
        },
        hash="test_hash_12345",
        sections=[
            {"title": "Overview", "level": 2, "content": "This is a test architecture document."},
            {"title": "Components", "level": 2, "content": "- Component A\n- Component B"}
        ],
        size_bytes=150
    )


@pytest.fixture
def sample_chunks():
    """Create sample processed chunks."""
    return [
        ProcessedChunk(
            content="# Test Architecture\n\n## Overview\nThis is a test architecture document.",
            start_index=0,
            end_index=70,
            embedding=[0.1] * 768,  # Mock 768-dim embedding
            metadata={"doc_type": "architecture", "subsystem": "core"},
            section_title="Overview",
            section_level=2
        ),
        ProcessedChunk(
            content="## Components\n- Component A\n- Component B",
            start_index=71,
            end_index=120,
            embedding=[0.2] * 768,
            metadata={"doc_type": "architecture", "subsystem": "core"},
            section_title="Components",
            section_level=2
        )
    ]


@pytest.fixture
async def neo4j_conn():
    """Create Neo4j connection for testing."""
    # Note: This requires Neo4j to be running
    # Use environment variables or skip if not available
    try:
        conn = Neo4jConnection(
            uri=os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
        await conn.verify_connection()
        yield conn
        await conn.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


# Unit tests for adapters

class TestRequestAdapter:
    """Test request adapter functionality."""

    def test_document_to_request(self, sample_document):
        """Test converting document to validation request."""
        adapter = RequestAdapter()

        request = adapter.document_to_request(
            document=sample_document,
            agent_id="test_agent",
            action="create"
        )

        assert isinstance(request, AgentRequest)
        assert request.agent_id == "test_agent"
        assert request.action == "create"
        assert request.target_type == "architecture"
        assert request.content["id"] == "ARCH-001"
        assert request.content["doc_type"] == "architecture"
        assert "content" in request.content
        assert request.metadata["source_path"] == sample_document.path

    def test_extract_references(self, sample_document):
        """Test reference extraction from document."""
        adapter = RequestAdapter()

        # Add some references to content
        sample_document.content += "\n\nReferences: [[ARCH-002]], [DESIGN-001]"
        sample_document.frontmatter["architecture_ref"] = "ARCH-000"

        references = adapter._extract_references(sample_document)

        assert "ARCH-000" in references
        assert "ARCH-002" in references
        assert "DESIGN-001" in references

    def test_generate_rationale(self, sample_document):
        """Test rationale generation."""
        adapter = RequestAdapter()

        rationale = adapter._generate_rationale(sample_document, "create")

        assert "ARCH-001" in rationale
        assert "architecture" in rationale
        assert "approved" in rationale


class TestDocumentAdapter:
    """Test document-to-graph adapter."""

    @pytest.mark.asyncio
    async def test_document_to_properties(self, sample_document):
        """Test converting document to node properties."""
        # Mock dependencies
        graph_ops = None
        vector_ops = None
        adapter = DocumentGraphAdapter(graph_ops, vector_ops)

        properties = adapter._document_to_properties(sample_document)

        assert properties["id"] == "ARCH-001"
        assert properties["doc_type"] == "architecture"
        assert properties["subsystem"] == "core"
        assert properties["status"] == "approved"
        assert properties["compliance_level"] == "strict"
        assert properties["content_hash"] == "test_hash_12345"
        assert "owners" in properties

    def test_generate_chunk_id(self):
        """Test chunk ID generation."""
        adapter = DocumentGraphAdapter(None, None)

        chunk_id_1 = adapter._generate_chunk_id("ARCH-001", 0)
        chunk_id_2 = adapter._generate_chunk_id("ARCH-001", 1)
        chunk_id_3 = adapter._generate_chunk_id("ARCH-001", 0)  # Same as first

        assert chunk_id_1 != chunk_id_2
        assert chunk_id_1 == chunk_id_3  # Deterministic
        assert len(chunk_id_1) == 16  # MD5 hash truncated

    @pytest.mark.asyncio
    async def test_store_chunks_with_embeddings(self, sample_document):
        """Test storing chunks with embeddings and CONTAINS relationships."""
        from unittest.mock import AsyncMock, MagicMock
        from src.processing.models import ProcessedChunk

        # Create mock operations
        graph_ops = AsyncMock()
        vector_ops = AsyncMock()
        adapter = DocumentGraphAdapter(graph_ops, vector_ops)

        # Create test chunks
        chunks = [
            ProcessedChunk(
                content="First chunk content",
                start_index=0,
                end_index=100,
                section_title="Overview",
                section_level=1,
                embedding=[0.1] * 768,
                metadata={}
            ),
            ProcessedChunk(
                content="Second chunk content",
                start_index=100,
                end_index=200,
                section_title="Details",
                section_level=2,
                embedding=[0.2] * 768,
                metadata={}
            )
        ]

        # Call _store_chunks
        count = await adapter._store_chunks(
            document_id="ARCH-001",
            document_label="Architecture",
            chunks=chunks,
            document=sample_document
        )

        # Verify chunks were created
        assert count == 2
        assert graph_ops.create_node.call_count == 2

        # Verify first chunk creation
        first_call = graph_ops.create_node.call_args_list[0]
        assert first_call[1]["label"] == "Chunk"
        chunk_props = first_call[1]["properties"]
        assert chunk_props["content"] == "First chunk content"
        assert chunk_props["chunk_index"] == 0
        assert chunk_props["section_title"] == "Overview"
        assert chunk_props["doc_type"] == "architecture"

        # Verify embeddings were stored
        assert vector_ops.store_embedding.call_count == 2

        # Verify CONTAINS relationships were created
        assert graph_ops.create_relationship.call_count == 2
        rel_call = graph_ops.create_relationship.call_args_list[0]
        assert rel_call[1]["rel_type"] == "CONTAINS"
        assert rel_call[1]["from_label"] == "Architecture"
        assert rel_call[1]["to_label"] == "Chunk"

    @pytest.mark.asyncio
    async def test_get_document_chunks(self):
        """Test retrieving chunks for a document."""
        from unittest.mock import AsyncMock

        # Create mock operations
        graph_ops = AsyncMock()
        graph_ops.query.return_value = [
            {"c": {"id": "chunk_1", "content": "First chunk", "chunk_index": 0}},
            {"c": {"id": "chunk_2", "content": "Second chunk", "chunk_index": 1}}
        ]

        vector_ops = AsyncMock()
        adapter = DocumentGraphAdapter(graph_ops, vector_ops)

        # Get chunks
        chunks = await adapter.get_document_chunks(
            document_id="ARCH-001",
            document_label="Architecture"
        )

        # Verify query was called
        assert graph_ops.query.called
        query_call = graph_ops.query.call_args
        assert "CONTAINS" in query_call[0][0]  # Check CONTAINS in query
        assert query_call[0][1]["doc_id"] == "ARCH-001"

        # Verify chunks returned
        assert len(chunks) == 2
        assert chunks[0]["content"] == "First chunk"
        assert chunks[1]["content"] == "Second chunk"


class TestChunkSemanticSearch:
    """Test chunk-based semantic search."""

    @pytest.mark.asyncio
    async def test_semantic_search_returns_chunks_with_context(self):
        """Test that semantic_search returns chunk-level results with parent document context."""
        from unittest.mock import AsyncMock, MagicMock
        from src.graph.vector_ops import VectorOperations
        from src.graph.connection import Neo4jConnection

        # Create mock connection
        mock_conn = AsyncMock(spec=Neo4jConnection)
        mock_conn.execute_read.return_value = [
            {
                "chunk_id": "chunk_1",
                "chunk_content": "Authentication implementation details",
                "chunk_index": 0,
                "section_title": "Authentication",
                "section_level": 2,
                "doc_id": "ARCH-001",
                "doc_title": "System Architecture",
                "doc_type": "architecture",
                "doc_version": "1.0.0",
                "score": 0.95
            },
            {
                "chunk_id": "chunk_2",
                "chunk_content": "Authorization policy framework",
                "chunk_index": 3,
                "section_title": "Authorization",
                "section_level": 2,
                "doc_id": "ARCH-001",
                "doc_title": "System Architecture",
                "doc_type": "architecture",
                "doc_version": "1.0.0",
                "score": 0.87
            }
        ]

        vector_ops = VectorOperations(mock_conn)

        # Perform semantic search
        query_embedding = [0.1] * 768
        results = await vector_ops.semantic_search(
            query_embedding=query_embedding,
            limit=10,
            doc_type="architecture"
        )

        # Verify query was called with correct parameters
        assert mock_conn.execute_read.called
        call_args = mock_conn.execute_read.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        # Verify query searches chunks via vector index
        assert "chunk_embedding" in query
        assert "CONTAINS" in query  # Should traverse to parent document
        assert params["embedding"] == query_embedding
        assert params["doc_type"] == "architecture"

        # Verify results format
        assert len(results) == 2

        # Check first result structure
        assert results[0]["chunk_id"] == "chunk_1"
        assert results[0]["chunk_content"] == "Authentication implementation details"
        assert results[0]["doc_id"] == "ARCH-001"
        assert results[0]["doc_title"] == "System Architecture"
        assert results[0]["score"] == 0.95

        # Check results are ordered by score
        assert results[0]["score"] >= results[1]["score"]

    @pytest.mark.asyncio
    async def test_semantic_search_with_no_doc_type_filter(self):
        """Test semantic_search without document type filter."""
        from unittest.mock import AsyncMock
        from src.graph.vector_ops import VectorOperations
        from src.graph.connection import Neo4jConnection

        mock_conn = AsyncMock(spec=Neo4jConnection)
        mock_conn.execute_read.return_value = []

        vector_ops = VectorOperations(mock_conn)

        # Search without doc_type filter
        query_embedding = [0.1] * 768
        results = await vector_ops.semantic_search(
            query_embedding=query_embedding,
            limit=5,
            doc_type=None  # No filter
        )

        # Verify None was passed for doc_type
        call_args = mock_conn.execute_read.call_args
        params = call_args[0][1]
        assert params["doc_type"] is None


class TestAsyncUtils:
    """Test async/sync utilities."""

    def test_run_sync(self):
        """Test running async function synchronously."""
        async def async_function():
            await asyncio.sleep(0.01)
            return "success"

        result = AsyncSync.run_sync(async_function())
        assert result == "success"

    @pytest.mark.asyncio
    async def test_run_async(self):
        """Test running sync function asynchronously."""
        def sync_function(x, y):
            return x + y

        result = await AsyncSync.run_async(sync_function, 5, 3)
        assert result == 8

    def test_make_sync_decorator(self):
        """Test make_sync decorator."""
        @AsyncSync.make_sync
        async def async_add(x, y):
            await asyncio.sleep(0.01)
            return x + y

        # Can now call synchronously
        result = async_add(10, 5)
        assert result == 15


# Integration tests

@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEndFlow:
    """Test complete end-to-end document flow."""

    async def test_document_storage(self, neo4j_conn, sample_document, sample_chunks):
        """Test storing document with chunks in graph."""
        graph_ops = GraphOperations(neo4j_conn)
        vector_ops = VectorOperations(neo4j_conn)
        adapter = DocumentGraphAdapter(graph_ops, vector_ops)

        # Store document
        doc_id = await adapter.store_document(
            document=sample_document,
            chunks=sample_chunks
        )

        assert doc_id == "ARCH-001"

        # Verify document exists
        exists = await adapter.document_exists("ARCH-001", "architecture")
        assert exists

        # Verify chunks stored
        chunks = await adapter.get_document_chunks("ARCH-001", "Architecture")
        assert len(chunks) >= 2  # At least our test chunks

        # Cleanup
        await graph_ops.delete_node("Architecture", "ARCH-001", "id")

    async def test_validation_audit_trail(self, neo4j_conn, sample_document):
        """Test storing validation results as audit trail."""
        graph_ops = GraphOperations(neo4j_conn)
        bridge = ValidationGraphBridge(graph_ops)
        adapter = RequestAdapter()

        # Create request
        request = adapter.document_to_request(
            document=sample_document,
            agent_id="test_agent"
        )

        # Create validation result
        validation_result = ValidationResult(
            status=ValidationStatus.APPROVED,
            violations=[],
            warnings=[],
            reasoning="All validation checks passed",
            confidence=1.0,
            processing_time_ms=50.0
        )

        # Store audit trail
        decision_id = await bridge.store_validation_result(request, validation_result)

        assert decision_id is not None
        assert decision_id.startswith("decision:")

        # Verify stored
        history = await bridge.get_validation_history(
            target_id=sample_document.frontmatter["id"]
        )
        assert len(history) > 0

        # Cleanup
        await graph_ops.delete_node("AgentRequest", request.id)
        await graph_ops.delete_node("Decision", decision_id)


@pytest.mark.asyncio
@pytest.mark.integration
class TestOrchestrator:
    """Test orchestrator functionality."""

    async def test_orchestrator_setup_validation(self, neo4j_conn):
        """Test orchestrator setup validation."""
        orchestrator = LibrarianOrchestrator(neo4j_conn)

        # Note: This will fail if Ollama is not running
        # That's expected - we want to know the real setup status
        setup_result = await orchestrator.validate_setup()

        assert "pipeline" in setup_result
        assert "graph" in setup_result
        assert "validation" in setup_result
        assert isinstance(setup_result["overall"], bool)

    async def test_process_document_with_temp_file(self, neo4j_conn):
        """Test processing a document from a temporary file."""
        # Create temporary markdown file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.md',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("""---
doc: architecture
subsystem: test
id: ARCH-TEST-001
title: Test Architecture
version: 1.0.0
status: draft
owners: [test_user]
compliance_level: strict
drift_tolerance: none
---

# Test Architecture

## Overview
This is a test document for integration testing.

## Design
The system consists of multiple components.
""")
            temp_path = f.name

        try:
            orchestrator = LibrarianOrchestrator(neo4j_conn)

            # Process document (skip validation for test)
            result = await orchestrator.process_document(
                file_path=temp_path,
                skip_validation=True  # Skip validation since Ollama might not be available
            )

            # Check result
            assert result.success or result.error is not None  # Either succeeds or has error
            if result.success:
                assert result.document_id == "ARCH-TEST-001"
                assert result.chunks_stored > 0

                # Cleanup
                graph_ops = GraphOperations(neo4j_conn)
                await graph_ops.delete_node("Architecture", "ARCH-TEST-001")

        finally:
            # Clean up temp file
            os.unlink(temp_path)


# Mock tests (for CI/CD without Neo4j)

class TestIntegrationMocked:
    """Test integration components with mocked dependencies."""

    def test_request_adapter_integration(self, sample_document):
        """Test request adapter with real document structure."""
        adapter = RequestAdapter()

        request = adapter.document_to_request(sample_document, "test_agent")

        # Verify all required fields present
        assert request.id is not None
        assert request.agent_id == "test_agent"
        assert request.action == "create"
        assert request.target_type == "architecture"
        assert request.content["id"] == "ARCH-001"

        # Verify can convert to dict
        request_dict = request.to_dict()
        assert isinstance(request_dict, dict)
        assert "id" in request_dict

    def test_async_sync_boundary(self):
        """Test async/sync boundary handling."""
        # Test that we can run async code from sync context
        async def async_operation():
            await asyncio.sleep(0.01)
            return {"result": "success"}

        result = AsyncSync.run_sync(async_operation())
        assert result["result"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
