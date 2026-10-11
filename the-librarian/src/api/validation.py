"""Validation endpoints for drift detection and compliance checking."""

from fastapi import APIRouter, HTTPException, Path
import logging

from src.api.models import DriftCheckResponse, ComplianceCheckResponse
from src.validation.drift_detector import DriftDetector
from src.graph.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize drift detector
drift_detector = None


def get_drift_detector() -> DriftDetector:
    """Get or create drift detector instance."""
    global drift_detector
    if drift_detector is None:
        conn = get_connection()

        def sync_graph_query(query: str, params: dict = None):
            """Synchronous wrapper for graph queries."""
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(conn.execute_read(query, params or {}))

        drift_detector = DriftDetector(graph_query=sync_graph_query)
    return drift_detector


@router.get("/drift-check", response_model=DriftCheckResponse)
async def drift_check():
    """
    Check for specification drift.

    Detects inconsistencies between architecture, design, and code:
    - Designs modified after their architecture
    - Code without corresponding documentation
    - Requirements without implementation

    Returns:
        DriftCheckResponse with drift violations
    """
    try:
        logger.info("Running drift detection...")

        detector = get_drift_detector()
        violations = detector.detect_all_drift()

        # Convert violations to response format
        mismatches = [v.to_dict() for v in violations]

        drift_detected = len(violations) > 0

        logger.info(f"Drift detection complete: {len(violations)} violations found")

        return DriftCheckResponse(
            drift_detected=drift_detected,
            mismatches=mismatches
        )

    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Drift detection failed: {str(e)}")


@router.get("/compliance/{subsystem}", response_model=ComplianceCheckResponse)
async def compliance_check(
    subsystem: str = Path(..., description="Subsystem to check compliance for")
):
    """
    Check compliance rate for a specific subsystem.

    Calculates what percentage of architecture specifications have corresponding
    implementations and identifies violations.

    Args:
        subsystem: Name of the subsystem to check

    Returns:
        ComplianceCheckResponse with compliance metrics
    """
    try:
        logger.info(f"Checking compliance for subsystem: {subsystem}")

        conn = get_connection()

        # Query for architecture specs in this subsystem
        arch_query = """
        MATCH (a:Architecture {subsystem: $subsystem})
        RETURN count(a) as total
        """
        arch_result = await conn.execute_read(arch_query, {"subsystem": subsystem})
        total_specs = arch_result[0].get("total", 0) if arch_result else 0

        # Query for implemented specs
        impl_query = """
        MATCH (a:Architecture {subsystem: $subsystem})
        WHERE exists((a)<-[:IMPLEMENTS]-(:Design))
        RETURN count(a) as implemented
        """
        impl_result = await conn.execute_read(impl_query, {"subsystem": subsystem})
        implemented = impl_result[0].get("implemented", 0) if impl_result else 0

        # Calculate compliance rate
        compliance_rate = (implemented / total_specs) if total_specs > 0 else 1.0

        # Query for violations (unapproved changes)
        violation_query = """
        MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture {subsystem: $subsystem})
        WHERE d.modified_at > a.modified_at
          AND NOT exists((:Decision)-[:APPROVES]->(:AgentRequest)-[:TARGETS]->(d))
        RETURN d.id as design_id, d.modified_at as modified, a.id as arch_id
        LIMIT 50
        """
        violation_results = await conn.execute_read(violation_query, {"subsystem": subsystem})

        violations = []
        for v in violation_results:
            violations.append({
                "type": "unapproved_modification",
                "design_id": v.get("design_id"),
                "architecture_id": v.get("arch_id"),
                "modified_at": str(v.get("modified"))
            })

        # Query for uncovered requirements
        uncovered_query = """
        MATCH (r:Requirement {subsystem: $subsystem, status: 'active'})
        WHERE NOT exists((r)<-[:SATISFIES]-())
        RETURN r.id as req_id, r.text as text, r.priority as priority
        LIMIT 50
        """
        uncovered_results = await conn.execute_read(uncovered_query, {"subsystem": subsystem})

        uncovered_requirements = []
        for r in uncovered_results:
            uncovered_requirements.append({
                "id": r.get("req_id"),
                "text": r.get("text", "")[:200],
                "priority": r.get("priority", "medium")
            })

        logger.info(
            f"Compliance check for {subsystem}: "
            f"{compliance_rate:.2%} ({implemented}/{total_specs}), "
            f"{len(violations)} violations, "
            f"{len(uncovered_requirements)} uncovered requirements"
        )

        return ComplianceCheckResponse(
            compliance_rate=compliance_rate,
            violations=violations,
            uncovered_requirements=uncovered_requirements
        )

    except Exception as e:
        logger.error(f"Compliance check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")


@router.get("/drift-summary")
async def drift_summary():
    """
    Get summary statistics for all drift violations.

    Returns aggregated drift metrics by type and severity.

    Returns:
        Dictionary with drift statistics
    """
    try:
        logger.info("Generating drift summary...")

        detector = get_drift_detector()
        summary = detector.get_drift_summary()

        logger.info(f"Drift summary: {summary['total_violations']} total violations")

        return summary

    except Exception as e:
        logger.error(f"Drift summary generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
