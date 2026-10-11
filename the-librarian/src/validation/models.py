"""Validation models and data structures."""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ValidationStatus(Enum):
    """Status of validation result."""
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    REVISION_REQUIRED = "revision_required"


class Severity(Enum):
    """Violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Violation:
    """Represents a validation rule violation."""
    rule: str                              # Rule ID (e.g., "DOC-001")
    severity: Severity                     # Severity level
    message: str                           # Human-readable message
    details: Dict[str, Any] = field(default_factory=dict)  # Additional context
    suggestion: Optional[str] = None       # How to fix the violation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationResult:
    """Result of validation operation."""
    status: ValidationStatus                    # Overall validation status
    violations: List[Violation] = field(default_factory=list)  # Rule violations
    warnings: List[Violation] = field(default_factory=list)    # Non-blocking issues
    metadata: Dict[str, Any] = field(default_factory=dict)     # Additional info
    reasoning: str = ""                         # Explanation of decision
    confidence: float = 1.0                     # Confidence in decision (0-1)
    processing_time_ms: float = 0.0            # Time taken for validation
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if validation passed without violations."""
        return self.status == ValidationStatus.APPROVED

    @property
    def critical_violations(self) -> List[Violation]:
        """Get all critical severity violations."""
        return [v for v in self.violations if v.severity == Severity.CRITICAL]

    @property
    def high_violations(self) -> List[Violation]:
        """Get all high severity violations."""
        return [v for v in self.violations if v.severity == Severity.HIGH]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "metadata": self.metadata,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DriftViolation:
    """Represents specification drift detection."""
    type: str                              # Type of drift
    severity: Severity                     # Severity level
    source: str                            # Source node ID
    target: Optional[str] = None           # Target node ID if applicable
    description: str = ""                  # Description of drift
    time_delta: Optional[float] = None     # Time difference in seconds
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "severity": self.severity.value,
            "source": self.source,
            "target": self.target,
            "description": self.description,
            "time_delta": self.time_delta,
            "detected_at": self.detected_at.isoformat()
        }
