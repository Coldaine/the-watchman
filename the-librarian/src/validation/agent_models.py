"""Agent interaction models for validation."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class AgentRequest:
    """Request from an agent for validation."""
    id: str                                  # Unique request ID
    agent_id: str                            # ID of the agent making request
    action: str                              # Action to perform (create/update/delete)
    target_type: str                         # Type of target (architecture/design/code)
    content: Dict[str, Any]                  # Content of the request
    rationale: str                           # Why this change is needed
    references: List[str] = field(default_factory=list)  # Referenced specs
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None         # Session context
    target_id: Optional[str] = None          # ID of target if updating/deleting
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "action": self.action,
            "target_type": self.target_type,
            "content": self.content,
            "rationale": self.rationale,
            "references": self.references,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "target_id": self.target_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRequest':
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            action=data["action"],
            target_type=data["target_type"],
            content=data["content"],
            rationale=data["rationale"],
            references=data.get("references", []),
            timestamp=timestamp or datetime.now(),
            session_id=data.get("session_id"),
            target_id=data.get("target_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentResponse:
    """Response to an agent request."""
    status: str                              # approved/rejected/escalated/revision_required
    feedback: str                            # Explanation of decision
    approved_location: Optional[str] = None  # Where to write if approved
    required_changes: List[str] = field(default_factory=list)  # Changes needed
    next_steps: List[str] = field(default_factory=list)  # What to do next
    violations: List[Dict[str, Any]] = field(default_factory=list)  # Violations found
    warnings: List[Dict[str, Any]] = field(default_factory=list)   # Warnings
    confidence: float = 1.0                  # Confidence in decision (0-1)
    processing_time_ms: float = 0.0         # Time taken to process
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "feedback": self.feedback,
            "approved_location": self.approved_location,
            "required_changes": self.required_changes,
            "next_steps": self.next_steps,
            "violations": self.violations,
            "warnings": self.warnings,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            status=data["status"],
            feedback=data["feedback"],
            approved_location=data.get("approved_location"),
            required_changes=data.get("required_changes", []),
            next_steps=data.get("next_steps", []),
            violations=data.get("violations", []),
            warnings=data.get("warnings", []),
            confidence=data.get("confidence", 1.0),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            timestamp=timestamp or datetime.now(),
            metadata=data.get("metadata", {})
        )


@dataclass
class Decision:
    """Represents a decision made by the validation system."""
    id: str                                  # Unique decision ID
    decision_type: str                       # Type of decision
    timestamp: datetime                      # When decision was made
    author: str                              # Who made the decision
    author_type: str                         # agent|human|system
    rationale: str                           # Why this decision was made
    confidence: float                        # Confidence in decision (0-1)
    impact_level: str                        # low|medium|high
    reversible: bool = True                  # Can this decision be reversed
    request_id: Optional[str] = None         # Associated request ID
    affected_nodes: List[str] = field(default_factory=list)  # Nodes affected
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "decision_type": self.decision_type,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "author_type": self.author_type,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "impact_level": self.impact_level,
            "reversible": self.reversible,
            "request_id": self.request_id,
            "affected_nodes": self.affected_nodes,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Decision':
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            id=data["id"],
            decision_type=data["decision_type"],
            timestamp=timestamp or datetime.now(),
            author=data["author"],
            author_type=data["author_type"],
            rationale=data["rationale"],
            confidence=data.get("confidence", 1.0),
            impact_level=data.get("impact_level", "medium"),
            reversible=data.get("reversible", True),
            request_id=data.get("request_id"),
            affected_nodes=data.get("affected_nodes", []),
            metadata=data.get("metadata", {})
        )


def create_response_from_validation(
    validation_result: Any,
    request: AgentRequest,
    approved_location: Optional[str] = None
) -> AgentResponse:
    """Create agent response from validation result.

    Args:
        validation_result: The validation result
        request: The original agent request
        approved_location: Location to write if approved

    Returns:
        AgentResponse
    """
    status = validation_result.status.value
    violations_dict = [v.to_dict() for v in validation_result.violations]
    warnings_dict = [w.to_dict() for w in validation_result.warnings]

    # Generate required changes from violations
    required_changes = []
    for v in validation_result.violations:
        if v.suggestion:
            required_changes.append(v.suggestion)

    # Generate next steps based on status
    next_steps = []
    if status == "approved":
        next_steps = [
            f"Write content to {approved_location}",
            "Update graph database with new node",
            "Create relationships to referenced specs"
        ]
    elif status == "revision_required":
        next_steps = [
            "Address the violations listed above",
            "Resubmit request with corrections",
            "Ensure all required fields are present"
        ]
    elif status == "escalated":
        next_steps = [
            "Wait for human review",
            "Review critical violations",
            "Prepare additional context if needed"
        ]

    return AgentResponse(
        status=status,
        feedback=validation_result.reasoning,
        approved_location=approved_location if status == "approved" else None,
        required_changes=required_changes,
        next_steps=next_steps,
        violations=violations_dict,
        warnings=warnings_dict,
        confidence=validation_result.confidence,
        processing_time_ms=validation_result.processing_time_ms,
        metadata=validation_result.metadata
    )
