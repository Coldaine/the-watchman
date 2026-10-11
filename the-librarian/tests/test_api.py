"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Librarian Agent API"
    assert data["version"] == "0.1.0"
    assert "docs" in data


@pytest.mark.asyncio
async def test_health_check_success():
    """Test health check endpoint when services are healthy."""
    with patch('src.api.health.get_connection') as mock_conn, \
         patch('src.api.health.EmbeddingGenerator') as mock_emb:

        # Mock Neo4j health check
        mock_conn_instance = AsyncMock()
        mock_conn_instance.health_check = AsyncMock(return_value={
            "connected": True,
            "node_count": 10,
            "relationship_count": 20
        })
        mock_conn.return_value = mock_conn_instance

        # Mock Ollama health check
        mock_emb_instance = Mock()
        mock_emb_instance.check_connection.return_value = True
        mock_emb_instance.check_model_available.return_value = True
        mock_emb_instance.model_name = "nomic-embed-text"
        mock_emb.return_value = mock_emb_instance

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["neo4j"] is True
        assert data["ollama"] is True
        assert data["version"] == "0.1.0"


def test_health_check_degraded():
    """Test health check when services are unavailable."""
    with patch('src.api.health.get_connection') as mock_conn, \
         patch('src.api.health.EmbeddingGenerator') as mock_emb:

        # Mock Neo4j failure
        mock_conn_instance = AsyncMock()
        mock_conn_instance.health_check = AsyncMock(return_value={
            "connected": False,
            "error": "Connection refused"
        })
        mock_conn.return_value = mock_conn_instance

        # Mock Ollama failure
        mock_emb_instance = Mock()
        mock_emb_instance.check_connection.return_value = False
        mock_emb.return_value = mock_emb_instance

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["neo4j"] is False
        assert data["ollama"] is False


def test_agent_request_approval():
    """Test agent request approval endpoint."""
    with patch('src.api.agent.get_validation_engine') as mock_engine, \
         patch('src.api.agent.get_audit_trail') as mock_audit:

        # Mock validation engine
        mock_validation_result = Mock()
        mock_validation_result.status.value = "approved"
        mock_validation_result.violations = []
        mock_validation_result.warnings = []
        mock_validation_result.reasoning = "All validation rules passed"
        mock_validation_result.confidence = 1.0
        mock_validation_result.processing_time_ms = 100.0
        mock_validation_result.metadata = {}

        mock_engine_instance = AsyncMock()
        mock_engine_instance.validate_request = AsyncMock(return_value=mock_validation_result)
        mock_engine.return_value = mock_engine_instance

        # Mock audit trail
        mock_audit_instance = AsyncMock()
        mock_audit_instance.log_request = AsyncMock()
        mock_audit.return_value = mock_audit_instance

        # Make request
        request_data = {
            "agent_id": "test-agent",
            "action": "create",
            "target_type": "architecture",
            "content": "New authentication system",
            "rationale": "Required for security",
            "references": []
        }

        response = client.post("/agent/request-approval", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "request_id" in data
        assert data["status"] == "approved"
        assert data["feedback"] == "All validation rules passed"
        assert data["approved_location"] is not None


def test_agent_request_revision_required():
    """Test agent request that requires revision."""
    with patch('src.api.agent.get_validation_engine') as mock_engine, \
         patch('src.api.agent.get_audit_trail') as mock_audit:

        # Mock validation with violations
        from src.validation.models import Violation, Severity

        mock_validation_result = Mock()
        mock_validation_result.status.value = "revision_required"
        mock_validation_result.violations = [
            Violation(
                rule="document_standards",
                severity=Severity.HIGH,
                message="Missing required field: version",
                suggestion="Add version field"
            )
        ]
        mock_validation_result.warnings = []
        mock_validation_result.reasoning = "Request has violations"
        mock_validation_result.confidence = 0.8
        mock_validation_result.processing_time_ms = 150.0
        mock_validation_result.metadata = {}

        mock_engine_instance = AsyncMock()
        mock_engine_instance.validate_request = AsyncMock(return_value=mock_validation_result)
        mock_engine.return_value = mock_engine_instance

        mock_audit_instance = AsyncMock()
        mock_audit_instance.log_request = AsyncMock()
        mock_audit.return_value = mock_audit_instance

        request_data = {
            "agent_id": "test-agent",
            "action": "create",
            "target_type": "design",
            "content": "Incomplete design document",
            "rationale": "New feature",
            "references": []
        }

        response = client.post("/agent/request-approval", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "revision_required"
        assert len(data["violations"]) == 1
        assert data["approved_location"] is None


def test_report_completion():
    """Test completion reporting endpoint."""
    with patch('src.api.agent.get_audit_trail') as mock_audit:

        mock_audit_instance = AsyncMock()
        mock_audit_instance.log_decision = AsyncMock()
        mock_audit.return_value = mock_audit_instance

        completion_data = {
            "request_id": "req-test123",
            "completed": True,
            "changes_made": ["Created new file", "Updated graph"],
            "deviations": [],
            "test_results": {"passed": True}
        }

        response = client.post("/agent/report-completion", json=completion_data)
        assert response.status_code == 200

        data = response.json()
        assert data["acknowledged"] is True
        assert "decision_id" in data
        assert len(data["next_steps"]) > 0


def test_cypher_query_read_only():
    """Test Cypher query endpoint allows read queries."""
    with patch('src.api.query.get_connection') as mock_conn:

        mock_conn_instance = AsyncMock()
        mock_conn_instance.execute_read = AsyncMock(return_value=[
            {"n.id": "arch-001", "n.title": "Authentication"}
        ])
        mock_conn.return_value = mock_conn_instance

        response = client.get("/query/cypher?q=MATCH (n:Architecture) RETURN n.id, n.title LIMIT 1")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0


def test_cypher_query_blocks_writes():
    """Test Cypher query endpoint blocks write operations."""
    # Test CREATE
    response = client.get("/query/cypher?q=CREATE (n:Test) RETURN n")
    assert response.status_code == 403
    assert "Write operations not allowed" in response.json()["detail"]

    # Test DELETE
    response = client.get("/query/cypher?q=MATCH (n) DELETE n")
    assert response.status_code == 403

    # Test SET
    response = client.get("/query/cypher?q=MATCH (n) SET n.prop = 'value'")
    assert response.status_code == 403


def test_drift_check():
    """Test drift detection endpoint."""
    with patch('src.api.validation.get_drift_detector') as mock_detector:

        from src.validation.models import DriftViolation, Severity

        mock_detector_instance = Mock()
        mock_detector_instance.detect_all_drift.return_value = [
            DriftViolation(
                type="design_ahead_of_architecture",
                severity=Severity.HIGH,
                source="design-001",
                target="arch-001",
                description="Design modified after architecture"
            )
        ]
        mock_detector.return_value = mock_detector_instance

        response = client.get("/validation/drift-check")
        assert response.status_code == 200

        data = response.json()
        assert data["drift_detected"] is True
        assert len(data["mismatches"]) == 1


def test_openapi_docs_available():
    """Test that OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Librarian Agent API"
    assert data["info"]["version"] == "0.1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
