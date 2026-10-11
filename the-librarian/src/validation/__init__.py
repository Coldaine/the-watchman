"""Validation and compliance engine for the Librarian Agent system."""

from .models import (
    ValidationStatus,
    Severity,
    Violation,
    ValidationResult,
    DriftViolation
)

from .rules import (
    ValidationRule,
    ValidationContext,
    DocumentStandardsRule,
    VersionCompatibilityRule,
    ArchitectureAlignmentRule,
    RequirementCoverageRule,
    ConstitutionComplianceRule
)

from .engine import ValidationEngine

from .drift_detector import DriftDetector

from .audit import AuditLogger, AuditRecord

from .agent_models import (
    AgentRequest,
    AgentResponse,
    Decision,
    create_response_from_validation
)

__all__ = [
    # Models
    "ValidationStatus",
    "Severity",
    "Violation",
    "ValidationResult",
    "DriftViolation",

    # Rules
    "ValidationRule",
    "ValidationContext",
    "DocumentStandardsRule",
    "VersionCompatibilityRule",
    "ArchitectureAlignmentRule",
    "RequirementCoverageRule",
    "ConstitutionComplianceRule",

    # Engine
    "ValidationEngine",

    # Drift Detection
    "DriftDetector",

    # Audit
    "AuditLogger",
    "AuditRecord",

    # Agent Models
    "AgentRequest",
    "AgentResponse",
    "Decision",
    "create_response_from_validation"
]

__version__ = "1.0.0"
