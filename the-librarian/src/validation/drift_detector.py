"""Drift detection for specification compliance."""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from .models import DriftViolation, Severity


class DriftDetector:
    """Detects specification drift in the knowledge base."""

    def __init__(self, graph_query: Optional[Callable] = None):
        """Initialize drift detector.

        Args:
            graph_query: Function to execute graph database queries
        """
        self.graph_query = graph_query

    def detect_all_drift(self) -> List[DriftViolation]:
        """Run all drift detection queries.

        Returns:
            List of all drift violations found
        """
        violations = []
        violations.extend(self.detect_design_drift())
        violations.extend(self.detect_undocumented_code())
        violations.extend(self.detect_uncovered_requirements())

        return violations

    def detect_design_drift(self) -> List[DriftViolation]:
        """Find designs that are ahead of their architecture.

        This detects when a design has been modified more recently than
        the architecture it implements, without proper approval.

        Returns:
            List of design drift violations
        """
        if not self.graph_query:
            return []

        query = """
            MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
            WHERE d.modified_at > a.modified_at
              AND NOT exists((:Decision)-[:APPROVES]->(:AgentRequest)-[:TARGETS]->(d))
            RETURN d.id as design_id,
                   a.id as arch_id,
                   d.modified_at as design_modified,
                   a.modified_at as arch_modified
        """

        try:
            results = self.graph_query(query)
        except Exception as e:
            print(f"Error querying for design drift: {e}")
            return []

        violations = []
        for r in results:
            time_delta = None
            if isinstance(r.get("design_modified"), datetime) and \
               isinstance(r.get("arch_modified"), datetime):
                time_delta = (r["design_modified"] - r["arch_modified"]).total_seconds()

            violations.append(DriftViolation(
                type="design_ahead_of_architecture",
                severity=Severity.HIGH,
                source=r["design_id"],
                target=r["arch_id"],
                description=f"Design '{r['design_id']}' modified after architecture "
                           f"'{r['arch_id']}' without approval",
                time_delta=time_delta
            ))

        return violations

    def detect_undocumented_code(self) -> List[DriftViolation]:
        """Find code implementations without corresponding documentation.

        Returns:
            List of undocumented code violations
        """
        if not self.graph_query:
            return []

        query = """
            MATCH (c:Code)
            WHERE NOT exists((c)-[:IMPLEMENTS]->(:Design))
              AND c.status = 'active'
            RETURN c.id as code_id,
                   c.path as code_path,
                   c.created_at as created_at
        """

        try:
            results = self.graph_query(query)
        except Exception as e:
            print(f"Error querying for undocumented code: {e}")
            return []

        violations = []
        for r in results:
            time_delta = None
            if isinstance(r.get("created_at"), datetime):
                time_delta = (datetime.now() - r["created_at"]).total_seconds()

            violations.append(DriftViolation(
                type="undocumented_code",
                severity=Severity.MEDIUM,
                source=r.get("code_id", "unknown"),
                description=f"Code at '{r.get('code_path', 'unknown')}' has no corresponding design documentation",
                time_delta=time_delta
            ))

        return violations

    def detect_uncovered_requirements(self) -> List[DriftViolation]:
        """Find active requirements with no implementation.

        Returns:
            List of uncovered requirement violations
        """
        if not self.graph_query:
            return []

        query = """
            MATCH (r:Requirement {status: 'active'})
            WHERE NOT exists((r)<-[:SATISFIES]-())
            RETURN r.id as req_id,
                   r.priority as priority,
                   r.text as text,
                   r.created_at as created_at
        """

        try:
            results = self.graph_query(query)
        except Exception as e:
            print(f"Error querying for uncovered requirements: {e}")
            return []

        violations = []
        for r in results:
            # Higher priority requirements are more severe
            severity = Severity.HIGH if r.get("priority") == "high" else Severity.MEDIUM

            time_delta = None
            if isinstance(r.get("created_at"), datetime):
                time_delta = (datetime.now() - r["created_at"]).total_seconds()

            req_text = r.get("text", "")
            description = f"Requirement '{r['req_id']}' not satisfied: {req_text[:100]}"
            if len(req_text) > 100:
                description += "..."

            violations.append(DriftViolation(
                type="uncovered_requirement",
                severity=severity,
                source=r["req_id"],
                description=description,
                time_delta=time_delta
            ))

        return violations

    def detect_version_mismatches(self) -> List[DriftViolation]:
        """Find version inconsistencies in specification hierarchy.

        Returns:
            List of version mismatch violations
        """
        if not self.graph_query:
            return []

        query = """
            MATCH (child)-[:IMPLEMENTS]->(parent)
            WHERE child.version IS NOT NULL
              AND parent.version IS NOT NULL
              AND NOT (child.version STARTS WITH split(parent.version, '.')[0])
            RETURN child.id as child_id,
                   parent.id as parent_id,
                   child.version as child_version,
                   parent.version as parent_version
        """

        try:
            results = self.graph_query(query)
        except Exception as e:
            print(f"Error querying for version mismatches: {e}")
            return []

        violations = []
        for r in results:
            violations.append(DriftViolation(
                type="version_mismatch",
                severity=Severity.HIGH,
                source=r["child_id"],
                target=r["parent_id"],
                description=f"Version mismatch: {r['child_id']} (v{r['child_version']}) "
                           f"implements {r['parent_id']} (v{r['parent_version']})"
            ))

        return violations

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of all drift violations.

        Returns:
            Dictionary with drift statistics
        """
        all_violations = self.detect_all_drift()

        summary = {
            "total_violations": len(all_violations),
            "by_type": {},
            "by_severity": {},
            "critical_violations": []
        }

        for v in all_violations:
            # Count by type
            v_type = v.type
            summary["by_type"][v_type] = summary["by_type"].get(v_type, 0) + 1

            # Count by severity
            severity = v.severity.value
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            # Collect critical violations
            if v.severity == Severity.CRITICAL:
                summary["critical_violations"].append(v.to_dict())

        return summary
