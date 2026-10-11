"""Validation engine orchestrator."""

import asyncio
import time
from typing import Dict, Any, List

from .models import ValidationResult, ValidationStatus, Violation, Severity
from .rules import (
    ValidationRule,
    ValidationContext,
    DocumentStandardsRule,
    VersionCompatibilityRule,
    ArchitectureAlignmentRule,
    RequirementCoverageRule,
    ConstitutionComplianceRule
)


class ValidationEngine:
    """Main validation engine that orchestrates all validation rules."""

    def __init__(self, graph_query: callable = None):
        """Initialize validation engine.

        Args:
            graph_query: Optional function to query the graph database
        """
        self.graph_query = graph_query
        self.rules: List[ValidationRule] = [
            DocumentStandardsRule(),
            VersionCompatibilityRule(),
            ArchitectureAlignmentRule(),
            RequirementCoverageRule(),
            ConstitutionComplianceRule()
        ]

    async def validate_request(self, request: Dict[str, Any],
                               context: Dict[str, Any] = None) -> ValidationResult:
        """Validate an agent request against all rules.

        Args:
            request: The agent request to validate
            context: Optional context with current specifications

        Returns:
            ValidationResult with status and violations
        """
        start_time = time.time()

        # Create validation context
        val_context = ValidationContext(
            graph_query=self.graph_query,
            current_specs=context.get("specs", {}) if context else {}
        )

        # Run all rules in parallel
        violations = await self._run_all_rules(request, val_context)

        # Determine status based on violations
        status = self._determine_status(violations)

        # Generate reasoning
        reasoning = self._generate_reasoning(status, violations)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return ValidationResult(
            status=status,
            violations=violations,
            reasoning=reasoning,
            processing_time_ms=processing_time_ms,
            metadata={
                "rules_executed": len(self.rules),
                "request_id": request.get("id"),
                "agent_id": request.get("agent_id")
            }
        )

    async def _run_all_rules(self, request: Dict[str, Any],
                            context: ValidationContext) -> List[Violation]:
        """Run all validation rules in parallel.

        Args:
            request: The request to validate
            context: Validation context

        Returns:
            List of all violations found
        """
        # Create tasks for all enabled rules
        tasks = [
            self._run_rule_async(rule, request, context)
            for rule in self.rules
            if rule.enabled
        ]

        # Run all rules concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all violations
        all_violations = []
        for result in results:
            if isinstance(result, Exception):
                # Log rule execution error
                print(f"Rule execution error: {result}")
                continue
            all_violations.extend(result)

        return all_violations

    async def _run_rule_async(self, rule: ValidationRule, request: Dict[str, Any],
                             context: ValidationContext) -> List[Violation]:
        """Run a single rule asynchronously.

        Args:
            rule: The rule to execute
            request: The request to validate
            context: Validation context

        Returns:
            List of violations from this rule
        """
        # Run rule in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        violations = await loop.run_in_executor(
            None,
            rule.validate,
            request,
            context
        )
        return violations

    def _determine_status(self, violations: List[Violation]) -> ValidationStatus:
        """Determine overall validation status based on violations.

        Rules:
        - No violations → APPROVED
        - Any critical violations → ESCALATED
        - 3+ high severity violations → REVISION_REQUIRED
        - Any other violations → REVISION_REQUIRED

        Args:
            violations: List of violations found

        Returns:
            ValidationStatus
        """
        if not violations:
            return ValidationStatus.APPROVED

        # Check for critical violations
        critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL)
        if critical_count > 0:
            return ValidationStatus.ESCALATED

        # Check for multiple high severity violations
        high_count = sum(1 for v in violations if v.severity == Severity.HIGH)
        if high_count >= 3:
            return ValidationStatus.REVISION_REQUIRED

        # Any violations require revision
        return ValidationStatus.REVISION_REQUIRED

    def _generate_reasoning(self, status: ValidationStatus,
                           violations: List[Violation]) -> str:
        """Generate human-readable reasoning for the validation decision.

        Args:
            status: The validation status
            violations: List of violations

        Returns:
            Reasoning string
        """
        if status == ValidationStatus.APPROVED:
            return "All validation rules passed. Request is approved for processing."

        if status == ValidationStatus.ESCALATED:
            critical_violations = [v for v in violations if v.severity == Severity.CRITICAL]
            rules = ", ".join(set(v.rule for v in critical_violations))
            return (f"Request requires human review due to {len(critical_violations)} "
                   f"critical violation(s) in rules: {rules}. "
                   "These violations cannot be auto-resolved.")

        if status == ValidationStatus.REVISION_REQUIRED:
            # Group violations by severity
            by_severity = {}
            for v in violations:
                severity = v.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1

            severity_summary = ", ".join(
                f"{count} {severity}"
                for severity, count in sorted(by_severity.items())
            )

            return (f"Request has {len(violations)} violation(s): {severity_summary}. "
                   "Please address the violations and resubmit.")

        return "Validation completed with unknown status."

    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule.

        Args:
            rule: The validation rule to add
        """
        self.rules.append(rule)

    def remove_rule(self, rule_id: str):
        """Remove a validation rule by ID.

        Args:
            rule_id: The ID of the rule to remove
        """
        self.rules = [r for r in self.rules if r.id != rule_id]

    def get_rule(self, rule_id: str) -> ValidationRule:
        """Get a validation rule by ID.

        Args:
            rule_id: The ID of the rule to get

        Returns:
            The validation rule or None
        """
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
