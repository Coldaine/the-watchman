# Agent 3: Validation Engine Specialist

## Your Mission
You are building the validation engine that enforces all governance rules for the Librarian Agent system. This is the core of agent control - validating requests against specifications.

## Context
You are working in parallel with:
- Agent 1: Building graph operations (you'll use their queries for validation)
- Agent 2: Building document processing (you'll validate their parsed documents)

## Required Reading
1. `docs/architecture.md` - Validation Rules section (lines 399-423)
2. `docs/subdomains/validation-engine.md` - Your primary specification
3. `docs/subdomains/audit-governance.md` - Audit trail requirements

## What to Build

### 1. Base Validation Models (`src/validation/models.py`)
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

class ValidationStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    REVISION_REQUIRED = "revision_required"

class Violation(BaseModel):
    rule: str  # Rule identifier (e.g., "DOC-001")
    severity: str  # critical | high | medium | low
    message: str
    details: Dict[str, Any]
    suggestion: Optional[str]

class ValidationResult(BaseModel):
    status: ValidationStatus
    violations: List[Violation] = []
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}
    reasoning: str
```

### 2. Validation Rules (`src/validation/rules.py`)
```python
from abc import ABC, abstractmethod
from typing import Optional

class ValidationRule(ABC):
    """Base class for all validation rules"""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def severity(self) -> str:
        pass

    @abstractmethod
    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        pass

class DocumentStandardsRule(ValidationRule):
    rule_id = "DOC-001"
    severity = "high"

    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        # Check frontmatter requirements
        # Verify document structure
        # Validate required fields based on doc_type
        required_fields = {
            "architecture": ["doc", "subsystem", "id", "version", "status", "owners", "compliance_level", "drift_tolerance"],
            "design": ["doc", "component", "id", "version", "status", "owners"],
            "tasks": ["doc", "sprint", "status", "assignee"]
        }

class VersionCompatibilityRule(ValidationRule):
    rule_id = "VER-001"
    severity = "critical"

    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        # Check version consistency
        # Ensure no version conflicts
        # Validate semantic versioning

class ArchitectureAlignmentRule(ValidationRule):
    rule_id = "ARCH-001"
    severity = "critical"

    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        # Verify changes align with architecture
        # Check against approved designs
        # Ensure no unauthorized architectural changes

class RequirementCoverageRule(ValidationRule):
    rule_id = "REQ-001"
    severity = "high"

    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        # Check if requirements are satisfied
        # Verify traceability
        # Ensure no uncovered requirements

class ConstitutionComplianceRule(ValidationRule):
    rule_id = "CONST-001"
    severity = "critical"

    async def validate(self, request: dict, context: dict) -> Optional[Violation]:
        # Enforce project constitution
        # Check governance rules
        # Validate against project principles
```

### 3. Validation Engine (`src/validation/engine.py`)
```python
from typing import List, Dict, Any
import asyncio

class ValidationEngine:
    def __init__(self):
        self.rules: List[ValidationRule] = [
            DocumentStandardsRule(),
            VersionCompatibilityRule(),
            ArchitectureAlignmentRule(),
            RequirementCoverageRule(),
            ConstitutionComplianceRule()
        ]
        self.critical_threshold = 1  # One critical violation triggers escalation
        self.high_threshold = 3  # Three high violations trigger revision

    async def validate_request(self, request: Dict[str, Any], context: Dict[str, Any] = None) -> ValidationResult:
        """Main validation entry point from docs/architecture.md lines 403-423"""

        # Gather context if not provided
        if context is None:
            context = await self.gather_context(request)

        # Run all rules in parallel
        violations = await self.run_rules(request, context)

        # Determine status based on violations
        status = self.determine_status(violations)

        # Create detailed reasoning
        reasoning = self.generate_reasoning(violations)

        return ValidationResult(
            status=status,
            violations=violations,
            reasoning=reasoning
        )

    async def run_rules(self, request: dict, context: dict) -> List[Violation]:
        """Execute all rules in parallel"""
        tasks = [
            rule.validate(request, context)
            for rule in self.rules
        ]

        results = await asyncio.gather(*tasks)

        # Filter out None results
        return [v for v in results if v is not None]

    def determine_status(self, violations: List[Violation]) -> ValidationStatus:
        """Logic from docs/architecture.md lines 416-423"""

        if not violations:
            return ValidationStatus.APPROVED

        critical_violations = [v for v in violations if v.severity == "critical"]
        high_violations = [v for v in violations if v.severity == "high"]

        if critical_violations:
            return ValidationStatus.ESCALATED

        if len(high_violations) >= self.high_threshold:
            return ValidationStatus.REVISION_REQUIRED

        if violations:
            return ValidationStatus.REVISION_REQUIRED

        return ValidationStatus.APPROVED

    async def gather_context(self, request: dict) -> dict:
        """Gather relevant context for validation"""
        # This would query the graph for related documents
        # For now, return mock context
        return {
            "existing_architecture": [],
            "related_designs": [],
            "requirements": [],
            "previous_decisions": []
        }
```

### 4. Drift Detection (`src/validation/drift_detector.py`)
```python
class DriftDetector:
    """Detects drift between code and documentation"""

    async def detect_all_drift(self) -> List[Dict]:
        """Run all drift detection queries"""
        drift_types = []

        # Design ahead of architecture
        design_drift = await self.detect_design_drift()
        drift_types.extend(design_drift)

        # Undocumented code
        undocumented = await self.detect_undocumented_code()
        drift_types.extend(undocumented)

        # Uncovered requirements
        uncovered = await self.detect_uncovered_requirements()
        drift_types.extend(uncovered)

        return drift_types

    async def detect_design_drift(self) -> List[Dict]:
        """Design version ahead of architecture version"""
        # Would use GraphOperations.query() with DETECT_DESIGN_DRIFT
        return []

    async def detect_undocumented_code(self) -> List[Dict]:
        """Code without corresponding documentation"""
        # Would query for CodeArtifact nodes without relationships
        return []

    async def detect_uncovered_requirements(self) -> List[Dict]:
        """Requirements not satisfied by any design"""
        # Would use FIND_UNCOVERED_REQUIREMENTS query
        return []
```

### 5. Audit Logger (`src/validation/audit.py`)
```python
from datetime import datetime
import json

class AuditLogger:
    """Creates immutable audit trail of all validations"""

    async def log_validation(self, request: dict, result: ValidationResult) -> str:
        """Log validation event to graph"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request": request,
            "result": result.dict(),
            "type": "VALIDATION"
        }

        # Would create AuditEvent node in graph
        # For now, log to file
        audit_id = f"audit_{datetime.utcnow().timestamp()}"

        with open(f"audit/{audit_id}.json", "w") as f:
            json.dump(audit_entry, f, indent=2)

        return audit_id

    async def log_decision(self, decision: dict) -> str:
        """Log approval/rejection decision"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "type": "DECISION"
        }

        # Would create Decision node in graph
        return "decision_id"
```

### 6. Agent Request Models (`src/validation/agent_models.py`)
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AgentRequest(BaseModel):
    agent_id: str = Field(..., description="ID of requesting agent")
    session_id: Optional[str] = None
    request_type: str = Field(..., pattern="^(APPROVAL|VALIDATION|QUERY)$")
    action: str = Field(..., pattern="^(create|modify|delete)$")
    target_type: str = Field(..., pattern="^(architecture|design|code|requirement)$")
    target_id: Optional[str] = None
    content: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=10)
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    request_id: str
    status: ValidationStatus
    feedback: str
    approved_location: Optional[str] = None
    required_changes: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## Interface Contract for Other Agents

Create `src/validation/__init__.py`:
```python
from .engine import ValidationEngine
from .models import ValidationResult, ValidationStatus, Violation
from .drift_detector import DriftDetector
from .audit import AuditLogger
from .agent_models import AgentRequest, AgentResponse

__all__ = [
    'ValidationEngine',
    'ValidationResult',
    'ValidationStatus',
    'Violation',
    'DriftDetector',
    'AuditLogger',
    'AgentRequest',
    'AgentResponse'
]
```

## Testing Requirements

Create `tests/test_validation.py`:
1. Test each validation rule with valid/invalid requests
2. Test escalation logic for critical violations
3. Test drift detection queries
4. Test audit logging creates immutable records
5. Test full validation flow with various scenarios

## Success Criteria

1. **All Rules Implemented**: All 5 validation rules work correctly
2. **Escalation Logic Works**: Critical violations trigger escalation
3. **Drift Detection Functions**: Can identify all drift types
4. **Audit Trail Created**: Immutable logs of all validations
5. **Real Validation**: Not mocked - actual rule checking

## Dependencies to Add to requirements.txt
```
pydantic==2.5.0
asyncio
```

## Coordination File

Write your status to `coordination.json`:
```json
{
  "agent3_validation": {
    "status": "working|complete",
    "interfaces_ready": ["ValidationEngine", "AgentRequest", "AgentResponse"],
    "blockers": []
  }
}
```

## Start Now
Begin by implementing the validation models and base rule structure. Then implement each rule according to the specification. Test with sample agent requests to ensure the validation logic works correctly.