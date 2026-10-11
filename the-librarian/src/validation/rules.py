"""Validation rules implementation."""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .models import Violation, Severity


@dataclass
class ValidationContext:
    """Context for validation rules."""
    graph_query: Optional[callable] = None  # Function to query graph
    current_specs: Dict[str, Any] = None    # Current specifications

    def __post_init__(self):
        if self.current_specs is None:
            self.current_specs = {}


class ValidationRule(ABC):
    """Base class for validation rules."""

    def __init__(self):
        self.id: str = ""
        self.name: str = ""
        self.severity: Severity = Severity.MEDIUM
        self.enabled: bool = True

    @abstractmethod
    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Execute validation rule."""
        pass


class DocumentStandardsRule(ValidationRule):
    """DOC-001: Validates document structure and frontmatter."""

    REQUIRED_FRONTMATTER = {
        "architecture": ["doc", "subsystem", "id", "version", "status", "owners"],
        "design": ["doc", "component", "id", "version", "status", "owners"],
        "tasks": ["doc", "sprint", "status", "assignee"],
        "requirement": ["doc", "id", "version", "status"]
    }

    EXPECTED_PATHS = {
        "architecture": r"docs/architecture/.*\.md",
        "design": r"docs/design/.*\.md",
        "tasks": r"docs/tasks/.*\.md",
        "requirement": r"docs/requirements/.*\.md"
    }

    def __init__(self):
        super().__init__()
        self.id = "DOC-001"
        self.name = "Document Standards"
        self.severity = Severity.HIGH

    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Validate document standards."""
        violations = []

        # Get document type and content
        doc_type = request.get("target_type")
        content = request.get("content", {})
        frontmatter = content.get("frontmatter", {})
        path = content.get("path", "")

        # Check frontmatter requirements
        if doc_type in self.REQUIRED_FRONTMATTER:
            required_fields = self.REQUIRED_FRONTMATTER[doc_type]
            missing_fields = [f for f in required_fields if f not in frontmatter]

            if missing_fields:
                violations.append(Violation(
                    rule=self.id,
                    severity=self.severity,
                    message=f"Missing required frontmatter fields for {doc_type}",
                    details={"missing_fields": missing_fields},
                    suggestion=f"Add the following fields to frontmatter: {', '.join(missing_fields)}"
                ))

        # Check version format if present
        version = frontmatter.get("version")
        if version and not self._valid_version(version):
            violations.append(Violation(
                rule=self.id,
                severity=Severity.MEDIUM,
                message="Version must use semantic versioning (x.y.z)",
                details={"version": version},
                suggestion="Use semantic versioning format like 1.0.0"
            ))

        # Check document location
        if doc_type in self.EXPECTED_PATHS:
            pattern = self.EXPECTED_PATHS[doc_type]
            if path and not re.match(pattern, path.replace("\\", "/")):
                violations.append(Violation(
                    rule=self.id,
                    severity=Severity.MEDIUM,
                    message=f"Document type '{doc_type}' should be in correct location",
                    details={"path": path, "expected_pattern": pattern},
                    suggestion=f"Move document to match pattern: {pattern}"
                ))

        return violations

    @staticmethod
    def _valid_version(version: str) -> bool:
        """Check if version follows semantic versioning."""
        pattern = r'^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$'
        return bool(re.match(pattern, str(version)))


class VersionCompatibilityRule(ValidationRule):
    """VER-001: Validates version consistency and compatibility."""

    def __init__(self):
        super().__init__()
        self.id = "VER-001"
        self.name = "Version Compatibility"
        self.severity = Severity.CRITICAL

    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Validate version compatibility."""
        violations = []

        content = request.get("content", {})
        frontmatter = content.get("frontmatter", {})
        version = frontmatter.get("version")
        implements = frontmatter.get("implements")

        # Check if version is specified
        if not version:
            violations.append(Violation(
                rule=self.id,
                severity=Severity.HIGH,
                message="Version is required for all specifications",
                suggestion="Add a 'version' field to frontmatter"
            ))
            return violations

        # Check version format
        if not self._valid_semantic_version(version):
            violations.append(Violation(
                rule=self.id,
                severity=self.severity,
                message="Invalid semantic version format",
                details={"version": version},
                suggestion="Use semantic versioning format: major.minor.patch"
            ))

        # Check compatibility with implemented spec if present
        if implements and context.graph_query:
            # Check if the implemented architecture exists and is approved
            parent_version = self._get_parent_version(implements, context)
            if parent_version and not self._versions_compatible(version, parent_version):
                violations.append(Violation(
                    rule=self.id,
                    severity=Severity.HIGH,
                    message="Version incompatible with parent specification",
                    details={
                        "version": version,
                        "parent_version": parent_version,
                        "implements": implements
                    },
                    suggestion="Ensure version is compatible with parent specification"
                ))

        return violations

    @staticmethod
    def _valid_semantic_version(version: str) -> bool:
        """Check if version follows semantic versioning."""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, str(version)))

    @staticmethod
    def _get_parent_version(parent_id: str, context: ValidationContext) -> Optional[str]:
        """Get version of parent specification."""
        specs = context.current_specs
        if parent_id in specs:
            return specs[parent_id].get("version")
        return None

    @staticmethod
    def _versions_compatible(child_version: str, parent_version: str) -> bool:
        """Check if child version is compatible with parent."""
        try:
            child_parts = [int(x) for x in child_version.split('.')]
            parent_parts = [int(x) for x in parent_version.split('.')]

            # Major version must match
            if child_parts[0] != parent_parts[0]:
                return False

            # Child minor version should be >= parent minor version
            if child_parts[1] < parent_parts[1]:
                return False

            return True
        except (ValueError, IndexError):
            return False


class ArchitectureAlignmentRule(ValidationRule):
    """ARCH-001: Validates changes align with approved architecture."""

    def __init__(self):
        super().__init__()
        self.id = "ARCH-001"
        self.name = "Architecture Alignment"
        self.severity = Severity.CRITICAL

    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Validate architecture alignment."""
        violations = []

        content = request.get("content", {})
        frontmatter = content.get("frontmatter", {})
        doc_type = request.get("target_type")
        implements = frontmatter.get("implements")

        # Design must implement an approved architecture
        if doc_type == "design":
            if not implements:
                violations.append(Violation(
                    rule=self.id,
                    severity=self.severity,
                    message="Design must reference an approved architecture",
                    suggestion="Add 'implements' field to frontmatter referencing architecture ID"
                ))
            else:
                # Check if referenced architecture exists and is approved
                arch = self._get_architecture(implements, context)
                if not arch:
                    violations.append(Violation(
                        rule=self.id,
                        severity=self.severity,
                        message=f"Referenced architecture '{implements}' not found",
                        details={"implements": implements},
                        suggestion="Ensure the architecture ID is correct and exists"
                    ))
                elif arch.get("status") != "approved":
                    violations.append(Violation(
                        rule=self.id,
                        severity=self.severity,
                        message=f"Referenced architecture '{implements}' is not approved",
                        details={"implements": implements, "status": arch.get("status")},
                        suggestion="Reference an approved architecture or get current architecture approved"
                    ))

        # Code must implement a design
        if doc_type == "code":
            if not implements:
                violations.append(Violation(
                    rule=self.id,
                    severity=Severity.HIGH,
                    message="Code must reference an approved design",
                    suggestion="Add 'implements' field referencing design ID"
                ))

        # Check for circular dependencies
        if implements:
            if self._has_circular_dependency(request.get("id"), implements, context):
                violations.append(Violation(
                    rule=self.id,
                    severity=self.severity,
                    message="Circular dependency detected",
                    details={"id": request.get("id"), "implements": implements},
                    suggestion="Remove circular dependency in specification hierarchy"
                ))

        return violations

    @staticmethod
    def _get_architecture(arch_id: str, context: ValidationContext) -> Optional[Dict[str, Any]]:
        """Get architecture specification."""
        specs = context.current_specs
        return specs.get(arch_id)

    @staticmethod
    def _has_circular_dependency(node_id: str, parent_id: str,
                                 context: ValidationContext) -> bool:
        """Check for circular dependencies."""
        # Simple check: if parent implements node_id, it's circular
        specs = context.current_specs
        parent = specs.get(parent_id, {})
        parent_implements = parent.get("implements")

        if parent_implements == node_id:
            return True

        # Could be extended to check deeper chains
        return False


class RequirementCoverageRule(ValidationRule):
    """REQ-001: Validates requirements are satisfied."""

    def __init__(self):
        super().__init__()
        self.id = "REQ-001"
        self.name = "Requirement Coverage"
        self.severity = Severity.HIGH

    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Validate requirement coverage."""
        violations = []

        content = request.get("content", {})
        frontmatter = content.get("frontmatter", {})
        satisfies = frontmatter.get("satisfies", [])
        doc_type = request.get("target_type")

        # Designs and implementations should reference requirements
        if doc_type in ["design", "code"]:
            if not satisfies:
                violations.append(Violation(
                    rule=self.id,
                    severity=Severity.MEDIUM,
                    message=f"{doc_type.capitalize()} should reference requirements it satisfies",
                    suggestion="Add 'satisfies' field to frontmatter with requirement IDs"
                ))
            else:
                # Check if requirements exist and are active
                for req_id in satisfies:
                    req = self._get_requirement(req_id, context)
                    if not req:
                        violations.append(Violation(
                            rule=self.id,
                            severity=Severity.HIGH,
                            message=f"Referenced requirement '{req_id}' not found",
                            details={"requirement_id": req_id},
                            suggestion="Ensure requirement ID is correct"
                        ))
                    elif req.get("status") != "active":
                        violations.append(Violation(
                            rule=self.id,
                            severity=Severity.MEDIUM,
                            message=f"Referenced requirement '{req_id}' is not active",
                            details={"requirement_id": req_id, "status": req.get("status")},
                            suggestion="Reference only active requirements"
                        ))

        return violations

    @staticmethod
    def _get_requirement(req_id: str, context: ValidationContext) -> Optional[Dict[str, Any]]:
        """Get requirement specification."""
        specs = context.current_specs
        return specs.get(req_id)


class ConstitutionComplianceRule(ValidationRule):
    """CONST-001: Enforces project constitution and governance rules."""

    IMMUTABLE_PROPERTIES = ["id", "created_at", "creator"]
    PROTECTED_STATUSES = ["approved", "published"]

    def __init__(self):
        super().__init__()
        self.id = "CONST-001"
        self.name = "Constitution Compliance"
        self.severity = Severity.CRITICAL

    def validate(self, request: Dict[str, Any], context: ValidationContext) -> List[Violation]:
        """Validate constitution compliance."""
        violations = []

        action = request.get("action")
        target_type = request.get("target_type")
        content = request.get("content", {})
        frontmatter = content.get("frontmatter", {})
        target_id = request.get("target_id")

        # Check for illegal deletions
        if action == "delete":
            if target_type in ["decision", "audit_event", "agent_request"]:
                violations.append(Violation(
                    rule=self.id,
                    severity=self.severity,
                    message=f"Cannot delete {target_type} - audit trail is immutable",
                    suggestion="Audit records cannot be deleted, only marked as superseded"
                ))

        # Check for modification of immutable properties
        if action == "update":
            existing = self._get_existing_spec(target_id, context)
            if existing:
                for prop in self.IMMUTABLE_PROPERTIES:
                    if prop in frontmatter and prop in existing:
                        if frontmatter[prop] != existing[prop]:
                            violations.append(Violation(
                                rule=self.id,
                                severity=self.severity,
                                message=f"Cannot modify immutable property '{prop}'",
                                details={"property": prop},
                                suggestion="Immutable properties cannot be changed after creation"
                            ))

                # Check for modification of published versions
                if existing.get("status") in self.PROTECTED_STATUSES:
                    violations.append(Violation(
                        rule=self.id,
                        severity=self.severity,
                        message=f"Cannot modify {existing.get('status')} specification",
                        details={"status": existing.get("status")},
                        suggestion="Create a new version with SUPERSEDES relationship instead"
                    ))

        # Validate hierarchy: Architecture -> Design -> Code
        if action in ["create", "update"]:
            doc_type = target_type
            implements = frontmatter.get("implements")

            if doc_type == "architecture" and implements:
                parent = self._get_existing_spec(implements, context)
                if parent and parent.get("doc_type") in ["design", "code"]:
                    violations.append(Violation(
                        rule=self.id,
                        severity=self.severity,
                        message="Architecture cannot implement lower-level specifications",
                        details={"implements": implements, "parent_type": parent.get("doc_type")},
                        suggestion="Architecture is top-level and should not implement other specs"
                    ))

            if doc_type == "design" and implements:
                parent = self._get_existing_spec(implements, context)
                if parent and parent.get("doc_type") == "code":
                    violations.append(Violation(
                        rule=self.id,
                        severity=self.severity,
                        message="Design cannot implement code",
                        details={"implements": implements},
                        suggestion="Design should implement architecture, not code"
                    ))

        return violations

    @staticmethod
    def _get_existing_spec(spec_id: str, context: ValidationContext) -> Optional[Dict[str, Any]]:
        """Get existing specification."""
        if not spec_id:
            return None
        specs = context.current_specs
        return specs.get(spec_id)
