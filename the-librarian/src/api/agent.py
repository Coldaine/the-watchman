"""Agent interaction endpoints."""

from fastapi import APIRouter, HTTPException
import logging
import uuid
from datetime import datetime

from src.api.models import (
    AgentRequestModel,
    AgentResponseModel,
    CompletionRequest,
    CompletionResponse
)
from src.validation.engine import ValidationEngine
from src.validation.agent_models import AgentRequest, create_response_from_validation, Decision
from src.validation.audit import AuditTrail
from src.graph.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize validation engine (will be properly initialized with graph connection)
validation_engine = None
audit_trail = None


def get_validation_engine() -> ValidationEngine:
    """Get or create validation engine instance."""
    global validation_engine
    if validation_engine is None:
        conn = get_connection()

        async def graph_query(query: str, params: dict = None):
            return await conn.execute_read(query, params or {})

        validation_engine = ValidationEngine(graph_query=graph_query)
    return validation_engine


def get_audit_trail() -> AuditTrail:
    """Get or create audit trail instance."""
    global audit_trail
    if audit_trail is None:
        conn = get_connection()
        audit_trail = AuditTrail(connection=conn)
    return audit_trail


@router.post("/request-approval", response_model=AgentResponseModel)
async def request_approval(request: AgentRequestModel):
    """
    Request approval for an agent action.

    The agent submits a proposed change for validation against specifications.
    Returns approval, revision requirements, or escalation to human review.

    Args:
        request: Agent request with action details

    Returns:
        AgentResponseModel with decision and feedback
    """
    try:
        # Generate unique request ID
        request_id = f"req-{uuid.uuid4().hex[:12]}"

        # Convert API model to internal model
        agent_request = AgentRequest(
            id=request_id,
            agent_id=request.agent_id,
            action=request.action,
            target_type=request.target_type,
            target_id=request.target_id,
            content={"text": request.content},  # Wrap content
            rationale=request.rationale,
            references=request.references,
            timestamp=datetime.now()
        )

        logger.info(f"Processing approval request {request_id} from agent {request.agent_id}")

        # Validate the request
        engine = get_validation_engine()
        validation_result = await engine.validate_request(
            agent_request.to_dict(),
            context={}  # Could load current specs from graph
        )

        # Determine approved location if approved
        approved_location = None
        if validation_result.status.value == "approved":
            # Generate location based on target type
            approved_location = f"docs/{request.target_type}/{request_id}.md"

        # Create response
        response = create_response_from_validation(
            validation_result,
            agent_request,
            approved_location
        )

        # Log to audit trail
        audit = get_audit_trail()
        await audit.log_request(agent_request, response)

        logger.info(
            f"Request {request_id} {response.status}: "
            f"{len(response.violations)} violations, "
            f"{len(response.warnings)} warnings"
        )

        # Convert to API response model
        return AgentResponseModel(
            request_id=request_id,
            status=response.status,
            feedback=response.feedback,
            approved_location=response.approved_location,
            required_changes=response.required_changes,
            next_steps=response.next_steps,
            violations=response.violations,
            warnings=response.warnings,
            confidence=response.confidence,
            processing_time_ms=response.processing_time_ms
        )

    except Exception as e:
        logger.error(f"Error processing approval request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Request processing failed: {str(e)}")


@router.post("/report-completion", response_model=CompletionResponse)
async def report_completion(completion: CompletionRequest):
    """
    Report completion of an approved action.

    The agent reports back after completing (or failing) an approved action.
    This updates the audit trail and graph database.

    Args:
        completion: Completion report with results

    Returns:
        CompletionResponse with acknowledgment
    """
    try:
        logger.info(f"Processing completion report for request {completion.request_id}")

        # Create decision record
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        decision = Decision(
            id=decision_id,
            decision_type="completion_report",
            timestamp=datetime.now(),
            author=completion.request_id,  # Reference to original request
            author_type="agent",
            rationale=f"Task {'completed' if completion.completed else 'failed'}",
            confidence=1.0 if completion.completed else 0.5,
            impact_level="medium",
            request_id=completion.request_id,
            metadata={
                "completed": completion.completed,
                "changes_made": completion.changes_made,
                "deviations": completion.deviations,
                "test_results": completion.test_results
            }
        )

        # Log to audit trail
        audit = get_audit_trail()
        await audit.log_decision(decision)

        # Determine next steps
        next_steps = []
        if completion.completed:
            next_steps = [
                "Changes have been recorded in audit trail",
                "Graph database will be updated with new relationships",
                "Drift detection will monitor for consistency"
            ]
        else:
            next_steps = [
                "Review failure reasons",
                "Submit revised request if needed",
                "Consult additional specifications"
            ]

        logger.info(f"Completion report {decision_id} acknowledged for request {completion.request_id}")

        return CompletionResponse(
            acknowledged=True,
            decision_id=decision_id,
            next_steps=next_steps
        )

    except Exception as e:
        logger.error(f"Error processing completion report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Completion processing failed: {str(e)}")
