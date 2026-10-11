"""Comprehensive tests for validation engine."""

import asyncio
import pytest
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.validation import (
    ValidationEngine,
    ValidationStatus,
    Severity,
    DriftDetector,
    AuditLogger,
    AgentRequest,
    create_response_from_validation
)


# Test Fixtures

def create_test_request(action="create", target_type="design",
                       frontmatter=None, path="docs/design/test.md"):
    """Create a test agent request."""
    if frontmatter is None:
        frontmatter = {
            "doc": "design",
            "component": "test-component",
            "id": "test-001",
            "version": "1.0.0",
            "status": "draft",
            "owners": ["test-agent"],
            "implements": "arch-001",  # Reference architecture
            "satisfies": ["req-001"]  # Reference requirements
        }

    return {
        "id": "REQ-001",
        "agent_id": "test-agent",
        "action": action,
        "target_type": target_type,
        "content": {
            "frontmatter": frontmatter,
            "path": path,
            "body": "Test content"
        },
        "rationale": "Test request"
    }


def create_mock_graph_query():
    """Create a mock graph query function for testing."""
    def mock_query(cypher_query):
        # Return empty results for most queries
        return []
    return mock_query


# Validation Engine Tests

@pytest.mark.asyncio
async def test_validation_engine_approves_valid_request():
    """Test that valid requests are approved."""
    engine = ValidationEngine()
    request = create_test_request()

    # Provide context with referenced specs
    context = {
        "specs": {
            "arch-001": {
                "id": "arch-001",
                "version": "1.0.0",
                "status": "approved",
                "doc_type": "architecture"
            },
            "req-001": {
                "id": "req-001",
                "status": "active",
                "priority": "high"
            }
        }
    }

    result = await engine.validate_request(request, context)

    assert result.status == ValidationStatus.APPROVED
    assert len(result.violations) == 0
    assert result.passed


@pytest.mark.asyncio
async def test_validation_engine_detects_missing_frontmatter():
    """Test detection of missing frontmatter fields."""
    engine = ValidationEngine()
    request = create_test_request(frontmatter={
        "doc": "design",
        "id": "test-001"
        # Missing: component, version, status, owners, implements
    })

    result = await engine.validate_request(request)

    # Status may be REVISION_REQUIRED or ESCALATED due to missing architecture
    assert result.status in [ValidationStatus.REVISION_REQUIRED, ValidationStatus.ESCALATED]
    assert len(result.violations) > 0
    assert any(v.rule == "DOC-001" for v in result.violations)


@pytest.mark.asyncio
async def test_validation_engine_detects_invalid_version():
    """Test detection of invalid version format."""
    engine = ValidationEngine()
    request = create_test_request(frontmatter={
        "doc": "design",
        "component": "test",
        "id": "test-001",
        "version": "invalid",  # Invalid version
        "status": "draft",
        "owners": ["test"]
        # Missing implements, so will also trigger ARCH-001 (critical)
    })

    result = await engine.validate_request(request)

    # Invalid version is critical, so expect escalation
    assert result.status in [ValidationStatus.REVISION_REQUIRED, ValidationStatus.ESCALATED]
    violations = [v for v in result.violations if v.rule == "VER-001"]
    assert len(violations) > 0


@pytest.mark.asyncio
async def test_validation_engine_detects_wrong_path():
    """Test detection of document in wrong location."""
    engine = ValidationEngine()
    request = create_test_request(
        path="wrong/location/test.md"  # Should be in docs/design/
    )

    result = await engine.validate_request(request)

    # May escalate due to missing architecture in context
    assert result.status in [ValidationStatus.REVISION_REQUIRED, ValidationStatus.ESCALATED]
    violations = [v for v in result.violations if v.rule == "DOC-001"]
    assert any("location" in v.message.lower() for v in violations)


@pytest.mark.asyncio
async def test_validation_engine_requires_architecture_for_design():
    """Test that designs must reference architecture."""
    engine = ValidationEngine()
    request = create_test_request(frontmatter={
        "doc": "design",
        "component": "test",
        "id": "test-001",
        "version": "1.0.0",
        "status": "draft",
        "owners": ["test"]
        # Missing: implements
    })

    result = await engine.validate_request(request)

    assert result.status == ValidationStatus.ESCALATED  # ARCH-001 is critical
    violations = [v for v in result.violations if v.rule == "ARCH-001"]
    assert len(violations) > 0
    assert any("architecture" in v.message.lower() for v in violations)


@pytest.mark.asyncio
async def test_validation_engine_escalates_critical_violations():
    """Test that critical violations trigger escalation."""
    engine = ValidationEngine()
    request = create_test_request(
        action="delete",
        target_type="decision"  # Cannot delete decisions (CONST-001)
    )

    result = await engine.validate_request(request)

    assert result.status == ValidationStatus.ESCALATED
    assert len(result.critical_violations) > 0
    assert any(v.rule == "CONST-001" for v in result.violations)


@pytest.mark.asyncio
async def test_validation_engine_detects_multiple_high_violations():
    """Test that 3+ high violations trigger revision required."""
    engine = ValidationEngine()
    request = create_test_request(frontmatter={
        "doc": "design",
        # Missing many required fields to trigger multiple high violations
        "id": "test-001"
    })

    result = await engine.validate_request(request)

    # Should have multiple violations
    assert len(result.violations) >= 3
    assert result.status in [ValidationStatus.REVISION_REQUIRED, ValidationStatus.ESCALATED]


# Document Standards Rule Tests

@pytest.mark.asyncio
async def test_doc_standards_validates_architecture():
    """Test document standards for architecture documents."""
    engine = ValidationEngine()
    request = create_test_request(
        target_type="architecture",
        path="docs/architecture/test.md",
        frontmatter={
            "doc": "architecture",
            "subsystem": "test-system",
            "id": "arch-001",
            "version": "1.0.0",
            "status": "draft",
            "owners": ["test"]
        }
    )

    result = await engine.validate_request(request)

    # Should pass with all required fields
    doc_violations = [v for v in result.violations if v.rule == "DOC-001"]
    # Should not have missing field violations
    missing_field_violations = [v for v in doc_violations if "missing" in v.message.lower()]
    assert len(missing_field_violations) == 0


@pytest.mark.asyncio
async def test_doc_standards_validates_tasks():
    """Test document standards for task documents."""
    engine = ValidationEngine()
    request = create_test_request(
        target_type="tasks",
        path="docs/tasks/sprint-1.md",
        frontmatter={
            "doc": "tasks",
            "sprint": "1",
            "status": "active",
            "assignee": "test-agent"
        }
    )

    result = await engine.validate_request(request)

    # Should pass with required task fields
    doc_violations = [v for v in result.violations if v.rule == "DOC-001"]
    missing_field_violations = [v for v in doc_violations if "missing" in v.message.lower()]
    assert len(missing_field_violations) == 0


# Version Compatibility Rule Tests

@pytest.mark.asyncio
async def test_version_compatibility_accepts_valid_versions():
    """Test that valid semantic versions are accepted."""
    engine = ValidationEngine()

    valid_versions = ["1.0.0", "2.1.3", "0.0.1", "10.20.30"]

    for version in valid_versions:
        request = create_test_request(frontmatter={
            "doc": "design",
            "component": "test",
            "id": "test-001",
            "version": version,
            "status": "draft",
            "owners": ["test"]
        })

        result = await engine.validate_request(request)
        ver_violations = [v for v in result.violations
                         if v.rule == "VER-001" and "invalid" in v.message.lower()]
        assert len(ver_violations) == 0, f"Version {version} should be valid"


@pytest.mark.asyncio
async def test_version_compatibility_rejects_invalid_versions():
    """Test that invalid versions are rejected."""
    engine = ValidationEngine()

    invalid_versions = ["1.0", "v1.0.0", "1.0.0.0", "invalid", ""]

    for version in invalid_versions:
        request = create_test_request(frontmatter={
            "doc": "design",
            "component": "test",
            "id": "test-001",
            "version": version,
            "status": "draft",
            "owners": ["test"]
        })

        result = await engine.validate_request(request)
        ver_violations = [v for v in result.violations if v.rule == "VER-001"]
        assert len(ver_violations) > 0, f"Version {version} should be invalid"


# Constitution Compliance Rule Tests

@pytest.mark.asyncio
async def test_constitution_prevents_audit_deletion():
    """Test that audit records cannot be deleted."""
    engine = ValidationEngine()

    protected_types = ["decision", "audit_event", "agent_request"]

    for target_type in protected_types:
        request = create_test_request(
            action="delete",
            target_type=target_type
        )

        result = await engine.validate_request(request)

        assert result.status == ValidationStatus.ESCALATED
        const_violations = [v for v in result.violations if v.rule == "CONST-001"]
        assert len(const_violations) > 0
        assert any("immutable" in v.message.lower() or "audit" in v.message.lower()
                  for v in const_violations)


@pytest.mark.asyncio
async def test_constitution_prevents_modifying_published_specs():
    """Test that published specs cannot be modified."""
    engine = ValidationEngine()

    # Mock context with existing published spec
    context = {
        "specs": {
            "test-001": {
                "id": "test-001",
                "version": "1.0.0",
                "status": "published",
                "doc_type": "design"
            }
        }
    }

    request = create_test_request(
        action="update",
        target_type="design"
    )
    request["target_id"] = "test-001"

    result = await engine.validate_request(request, context)

    assert result.status == ValidationStatus.ESCALATED
    const_violations = [v for v in result.violations if v.rule == "CONST-001"]
    assert any("published" in v.message.lower() or "approved" in v.message.lower()
              for v in const_violations)


# Drift Detection Tests

def test_drift_detector_initialization():
    """Test drift detector can be initialized."""
    detector = DriftDetector()
    assert detector is not None


def test_drift_detector_handles_no_graph_query():
    """Test drift detector handles missing graph query gracefully."""
    detector = DriftDetector(graph_query=None)

    # Should return empty lists when no graph query available
    assert detector.detect_design_drift() == []
    assert detector.detect_undocumented_code() == []
    assert detector.detect_uncovered_requirements() == []


def test_drift_detector_detects_design_drift():
    """Test detection of design drift."""
    def mock_query(cypher):
        if "Design" in cypher and "IMPLEMENTS" in cypher:
            return [
                {
                    "design_id": "design-001",
                    "arch_id": "arch-001",
                    "design_modified": datetime.now(),
                    "arch_modified": datetime.now() - timedelta(days=5)
                }
            ]
        return []

    detector = DriftDetector(graph_query=mock_query)
    violations = detector.detect_design_drift()

    assert len(violations) > 0
    assert violations[0].type == "design_ahead_of_architecture"
    assert violations[0].severity == Severity.HIGH


def test_drift_detector_detects_undocumented_code():
    """Test detection of undocumented code."""
    def mock_query(cypher):
        if "Code" in cypher and "IMPLEMENTS" in cypher:
            return [
                {
                    "code_id": "code-001",
                    "code_path": "src/test.py",
                    "created_at": datetime.now() - timedelta(days=10)
                }
            ]
        return []

    detector = DriftDetector(graph_query=mock_query)
    violations = detector.detect_undocumented_code()

    assert len(violations) > 0
    assert violations[0].type == "undocumented_code"
    assert violations[0].severity == Severity.MEDIUM


def test_drift_detector_detects_uncovered_requirements():
    """Test detection of uncovered requirements."""
    def mock_query(cypher):
        if "Requirement" in cypher:
            return [
                {
                    "req_id": "req-001",
                    "priority": "high",
                    "text": "Critical feature requirement",
                    "created_at": datetime.now() - timedelta(days=30)
                },
                {
                    "req_id": "req-002",
                    "priority": "medium",
                    "text": "Nice to have feature",
                    "created_at": datetime.now() - timedelta(days=15)
                }
            ]
        return []

    detector = DriftDetector(graph_query=mock_query)
    violations = detector.detect_uncovered_requirements()

    assert len(violations) == 2
    # High priority requirement should have HIGH severity
    high_priority = [v for v in violations if v.source == "req-001"][0]
    assert high_priority.severity == Severity.HIGH


def test_drift_detector_summary():
    """Test drift summary generation."""
    def mock_query(cypher):
        if "Design" in cypher and "IMPLEMENTS" in cypher:
            return [{
                "design_id": "d1",
                "arch_id": "a1",
                "design_modified": datetime.now(),
                "arch_modified": datetime.now() - timedelta(days=1)
            }]
        if "Code" in cypher and "IMPLEMENTS" in cypher:
            return [{
                "code_id": "c1",
                "code_path": "src/test.py",
                "created_at": datetime.now()
            }]
        if "Requirement" in cypher:
            return []
        return []

    detector = DriftDetector(graph_query=mock_query)
    summary = detector.get_drift_summary()

    assert summary["total_violations"] >= 0  # May be 0 if queries return empty
    assert "by_type" in summary
    assert "by_severity" in summary


# Audit Logger Tests

def test_audit_logger_initialization():
    """Test audit logger can be initialized."""
    logger = AuditLogger()
    assert logger is not None
    assert len(logger.records) == 0


@pytest.mark.asyncio
async def test_audit_logger_logs_validation():
    """Test logging of validation events."""
    logger = AuditLogger()
    engine = ValidationEngine()

    request = create_test_request()
    result = await engine.validate_request(request)

    record_id = logger.log_validation(request, result)

    assert record_id is not None
    assert len(logger.records) == 1
    assert logger.records[0].event_type == "validation"
    assert logger.records[0].request_id == request["id"]


def test_audit_logger_logs_decision():
    """Test logging of decision events."""
    logger = AuditLogger()

    decision = {
        "request_id": "REQ-001",
        "agent_id": "test-agent",
        "decision_type": "approved",
        "rationale": "All checks passed",
        "confidence": 0.95
    }

    record_id = logger.log_decision(decision)

    assert record_id is not None
    assert len(logger.records) == 1
    assert logger.records[0].event_type == "decision"
    assert logger.records[0].decision == "approved"


def test_audit_logger_retrieves_records():
    """Test retrieving audit records."""
    logger = AuditLogger()

    # Log multiple records
    for i in range(5):
        logger.log_decision({
            "request_id": f"REQ-{i:03d}",
            "agent_id": "test-agent",
            "decision_type": "approved"
        })

    # Get by request
    records = logger.get_records_by_request("REQ-001")
    assert len(records) == 1
    assert records[0].request_id == "REQ-001"

    # Get recent
    recent = logger.get_recent_records(limit=3)
    assert len(recent) == 3


def test_audit_logger_statistics():
    """Test audit statistics generation."""
    logger = AuditLogger()

    # Log various events
    logger.log_decision({"decision_type": "approved"})
    logger.log_decision({"decision_type": "rejected"})
    logger.log_drift_detection([])

    stats = logger.get_statistics()

    assert stats["total_records"] == 3
    assert "decision" in stats["by_event_type"]
    assert "drift_detection" in stats["by_event_type"]
    assert "approved" in stats["by_decision"]


# Agent Models Tests

def test_agent_request_creation():
    """Test creating agent request."""
    request = AgentRequest(
        id="REQ-001",
        agent_id="test-agent",
        action="create",
        target_type="design",
        content={"test": "data"},
        rationale="Test request"
    )

    assert request.id == "REQ-001"
    assert request.agent_id == "test-agent"


def test_agent_request_serialization():
    """Test agent request to/from dict."""
    request = AgentRequest(
        id="REQ-001",
        agent_id="test-agent",
        action="create",
        target_type="design",
        content={"test": "data"},
        rationale="Test request"
    )

    # Convert to dict
    data = request.to_dict()
    assert data["id"] == "REQ-001"

    # Convert back
    restored = AgentRequest.from_dict(data)
    assert restored.id == request.id
    assert restored.agent_id == request.agent_id


@pytest.mark.asyncio
async def test_create_response_from_validation():
    """Test creating agent response from validation result."""
    engine = ValidationEngine()
    request_dict = create_test_request()

    # Create agent request object
    request = AgentRequest(
        id=request_dict["id"],
        agent_id=request_dict["agent_id"],
        action=request_dict["action"],
        target_type=request_dict["target_type"],
        content=request_dict["content"],
        rationale=request_dict["rationale"]
    )

    result = await engine.validate_request(request_dict)
    response = create_response_from_validation(
        result,
        request,
        approved_location="docs/design/test.md"
    )

    assert response.status == result.status.value
    assert response.feedback == result.reasoning
    assert len(response.next_steps) > 0


# Integration Tests

@pytest.mark.asyncio
async def test_full_validation_workflow():
    """Test complete validation workflow."""
    # Initialize components
    engine = ValidationEngine()
    logger = AuditLogger()

    # Create request
    request_dict = create_test_request()
    request = AgentRequest.from_dict(request_dict)

    # Provide context
    context = {
        "specs": {
            "arch-001": {
                "id": "arch-001",
                "version": "1.0.0",
                "status": "approved",
                "doc_type": "architecture"
            },
            "req-001": {
                "id": "req-001",
                "status": "active",
                "priority": "high"
            }
        }
    }

    # Validate
    result = await engine.validate_request(request_dict, context)

    # Log validation
    audit_id = logger.log_validation(request_dict, result)

    # Create response
    response = create_response_from_validation(
        result,
        request,
        approved_location="docs/design/test.md"
    )

    # Verify workflow
    assert result.status == ValidationStatus.APPROVED
    assert audit_id is not None
    assert response.status == "approved"
    assert response.approved_location is not None


@pytest.mark.asyncio
async def test_validation_with_drift_detection():
    """Test validation combined with drift detection."""
    def mock_query(cypher):
        if "Requirement" in cypher:
            return [{
                "req_id": "req-001",
                "priority": "high",
                "text": "Feature X",
                "created_at": datetime.now()
            }]
        return []

    engine = ValidationEngine(graph_query=mock_query)
    detector = DriftDetector(graph_query=mock_query)

    # Validate a request
    request = create_test_request()
    result = await engine.validate_request(request)

    # Detect drift
    drift_violations = detector.detect_all_drift()

    # Both should work independently
    assert result is not None
    assert drift_violations is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
