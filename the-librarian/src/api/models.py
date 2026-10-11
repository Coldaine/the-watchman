"""Pydantic models for API request/response validation."""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AgentRequestModel(BaseModel):
    """Request model for agent approval."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "agent-001",
                "action": "create",
                "target_type": "architecture",
                "content": "New authentication architecture using JWT tokens",
                "rationale": "Required for secure API access",
                "references": ["arch-001", "arch-002"]
            }
        }
    )

    agent_id: str = Field(..., description="ID of the agent making the request")
    action: Literal["create", "modify", "delete"] = Field(..., description="Type of action")
    target_type: Literal["architecture", "design", "code"] = Field(..., description="Type of target")
    target_id: Optional[str] = Field(None, description="ID of target if modifying/deleting")
    content: str = Field(..., description="Content of the change")
    rationale: str = Field(..., description="Reason for the change")
    references: List[str] = Field(default_factory=list, description="IDs of specs consulted")


class AgentResponseModel(BaseModel):
    """Response model for agent requests."""
    request_id: str = Field(..., description="Unique request ID")
    status: Literal["approved", "revision_required", "escalated"] = Field(..., description="Decision status")
    feedback: str = Field(..., description="Explanation of decision")
    approved_location: Optional[str] = Field(None, description="Where to write if approved")
    required_changes: List[str] = Field(default_factory=list, description="Changes needed")
    next_steps: List[str] = Field(default_factory=list, description="What to do next")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="Violations found")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Warnings")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in decision")
    processing_time_ms: float = Field(0.0, description="Processing time in milliseconds")


class CompletionRequest(BaseModel):
    """Request model for reporting completion."""
    request_id: str = Field(..., description="Original request ID")
    completed: bool = Field(..., description="Whether the task was completed")
    changes_made: List[str] = Field(default_factory=list, description="List of changes made")
    deviations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Any deviations from approved plan"
    )
    test_results: Dict[str, Any] = Field(default_factory=dict, description="Test results")


class CompletionResponse(BaseModel):
    """Response model for completion reports."""
    acknowledged: bool = Field(..., description="Whether completion was acknowledged")
    decision_id: str = Field(..., description="Decision record ID")
    next_steps: List[str] = Field(default_factory=list, description="Recommended next steps")


class SemanticQueryRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query text")
    context_type: Literal["architecture", "design", "all"] = Field(
        default="all",
        description="Type of documents to search"
    )
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")


class SemanticQueryResponse(BaseModel):
    """Response model for semantic search."""
    results: List[Dict[str, Any]] = Field(..., description="Search results")


class CypherQueryResponse(BaseModel):
    """Response model for Cypher queries."""
    results: List[Dict[str, Any]] = Field(..., description="Query results")


class DriftCheckResponse(BaseModel):
    """Response model for drift detection."""
    drift_detected: bool = Field(..., description="Whether drift was detected")
    mismatches: List[Dict[str, Any]] = Field(default_factory=list, description="Drift violations")


class ComplianceCheckResponse(BaseModel):
    """Response model for compliance check."""
    compliance_rate: float = Field(..., ge=0.0, le=1.0, description="Compliance rate")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="Violations found")
    uncovered_requirements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Requirements without implementation"
    )


class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    document_path: str = Field(..., description="Path to document file")
    document_type: Literal["architecture", "design", "code", "research"] = Field(
        ...,
        description="Type of document"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    success: bool = Field(..., description="Whether ingestion succeeded")
    node_id: str = Field(..., description="Created node ID")
    relationships_created: int = Field(..., description="Number of relationships created")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: Literal["healthy", "degraded"] = Field(..., description="Overall health status")
    neo4j: bool = Field(..., description="Neo4j connection status")
    ollama: bool = Field(..., description="Ollama connection status")
    version: str = Field(..., description="API version")
    uptime_seconds: Optional[float] = Field(None, description="Application uptime in seconds")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")
