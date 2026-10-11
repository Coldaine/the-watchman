"""
Validation-Graph bridge for connecting sync validation with async graph operations.

Provides synchronous wrappers for graph queries used by validation rules,
and async methods for storing validation results as audit trail.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import asyncio

from ..validation.models import ValidationResult
from ..validation.agent_models import AgentRequest, Decision
from ..graph.operations import GraphOperations
from ..graph.schema import NodeLabels, RelationshipTypes
from .async_utils import AsyncSync

logger = logging.getLogger(__name__)


class ValidationGraphBridge:
    """Bridge between synchronous validation and async graph operations."""

    def __init__(self, graph_ops: GraphOperations):
        """
        Initialize validation bridge.

        Args:
            graph_ops: Graph operations instance
        """
        self.graph_ops = graph_ops

    def query_sync(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a graph query synchronously.

        Wraps async graph queries for use in synchronous validation rules.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result records

        Raises:
            RuntimeError: If query execution fails
        """
        params = params or {}

        try:
            # Run async query in sync context
            result = AsyncSync.run_sync(
                self.graph_ops.query(cypher, params)
            )
            return result

        except Exception as e:
            logger.error(f"Sync query execution failed: {e}")
            raise RuntimeError(f"Graph query failed: {e}")

    async def store_validation_result(
        self,
        request: AgentRequest,
        result: ValidationResult
    ) -> str:
        """
        Store validation result in graph as audit trail.

        Creates:
        - AgentRequest node
        - Decision node
        - RESULTED_IN relationship

        Args:
            request: The agent request that was validated
            result: Validation result

        Returns:
            Decision ID

        Raises:
            RuntimeError: If storage fails
        """
        logger.info(f"Storing validation result for request {request.id}")

        try:
            # Store agent request node
            request_props = self._request_to_properties(request)
            await self.graph_ops.create_node(
                label=NodeLabels.AGENT_REQUEST,
                properties=request_props
            )

            # Create decision from validation result
            decision_id = f"decision:{request.id}"
            decision_props = self._result_to_decision_properties(
                decision_id, request, result
            )

            # Store decision node
            await self.graph_ops.create_node(
                label=NodeLabels.DECISION,
                properties=decision_props
            )

            # Create relationship: AgentRequest -[RESULTED_IN]-> Decision
            await self.graph_ops.create_relationship(
                from_label=NodeLabels.AGENT_REQUEST,
                from_id=request.id,
                rel_type=RelationshipTypes.RESULTED_IN,
                to_label=NodeLabels.DECISION,
                to_id=decision_id,
                properties={
                    "processing_time_ms": result.processing_time_ms,
                    "confidence": result.confidence
                }
            )

            # If approved and has target, create appropriate relationships
            if result.passed and request.target_id:
                await self._create_approval_relationships(
                    request, decision_id
                )

            logger.info(f"Stored validation result: {decision_id}")
            return decision_id

        except Exception as e:
            logger.error(f"Failed to store validation result: {e}")
            raise RuntimeError(f"Validation storage failed: {e}")

    async def get_validation_history(
        self,
        target_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get validation history for a target document.

        Args:
            target_id: Target document ID
            limit: Maximum number of results

        Returns:
            List of validation records
        """
        query = """
        MATCH (req:AgentRequest {target_id: $target_id})-[r:RESULTED_IN]->(dec:Decision)
        RETURN req, dec, r
        ORDER BY req.timestamp DESC
        LIMIT $limit
        """

        try:
            results = await self.graph_ops.query(
                query,
                {"target_id": target_id, "limit": limit}
            )

            history = []
            for record in results:
                history.append({
                    "request": dict(record["req"]),
                    "decision": dict(record["dec"]),
                    "relationship": dict(record["r"])
                })

            return history

        except Exception as e:
            logger.error(f"Failed to retrieve validation history: {e}")
            return []

    async def get_recent_approvals(
        self,
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent approved requests.

        Args:
            agent_id: Optional filter by agent ID
            limit: Maximum number of results

        Returns:
            List of approved requests
        """
        if agent_id:
            query = """
            MATCH (req:AgentRequest {agent_id: $agent_id})-[:RESULTED_IN]->(dec:Decision)
            WHERE dec.decision_type = 'approval'
            RETURN req, dec
            ORDER BY req.timestamp DESC
            LIMIT $limit
            """
            params = {"agent_id": agent_id, "limit": limit}
        else:
            query = """
            MATCH (req:AgentRequest)-[:RESULTED_IN]->(dec:Decision)
            WHERE dec.decision_type = 'approval'
            RETURN req, dec
            ORDER BY req.timestamp DESC
            LIMIT $limit
            """
            params = {"limit": limit}

        try:
            results = await self.graph_ops.query(query, params)

            approvals = []
            for record in results:
                approvals.append({
                    "request": dict(record["req"]),
                    "decision": dict(record["dec"])
                })

            return approvals

        except Exception as e:
            logger.error(f"Failed to retrieve approvals: {e}")
            return []

    async def _create_approval_relationships(
        self,
        request: AgentRequest,
        decision_id: str
    ) -> None:
        """
        Create relationships for approved requests.

        Links the decision to the target document it approved.

        Args:
            request: Approved request
            decision_id: Decision node ID
        """
        if not request.target_id or not request.target_type:
            return

        # Determine target node label
        type_mapping = {
            "architecture": NodeLabels.ARCHITECTURE,
            "design": NodeLabels.DESIGN,
            "code": NodeLabels.CODE_ARTIFACT,
        }

        target_label = type_mapping.get(request.target_type.lower())
        if not target_label:
            logger.warning(f"Unknown target type: {request.target_type}")
            return

        try:
            # Create APPROVES relationship: Decision -[APPROVES]-> Target
            await self.graph_ops.create_relationship(
                from_label=NodeLabels.DECISION,
                from_id=decision_id,
                rel_type=RelationshipTypes.APPROVES,
                to_label=target_label,
                to_id=request.target_id,
                properties={
                    "approved_at": datetime.utcnow().isoformat(),
                    "agent_id": request.agent_id
                }
            )

            logger.debug(
                f"Created APPROVES relationship: {decision_id} -> {request.target_id}"
            )

        except Exception as e:
            logger.error(f"Failed to create approval relationship: {e}")
            # Don't raise - this is supplementary information

    def _request_to_properties(self, request: AgentRequest) -> Dict[str, Any]:
        """
        Convert AgentRequest to node properties.

        Args:
            request: Agent request

        Returns:
            Dictionary of node properties
        """
        return {
            "id": request.id,
            "agent_id": request.agent_id,
            "action": request.action,
            "target_type": request.target_type,
            "target_id": request.target_id,
            "rationale": request.rationale,
            "references": request.references,
            "session_id": request.session_id,
            "timestamp": request.timestamp.isoformat(),
            "content": str(request.content),  # Store as string
            "metadata": str(request.metadata)  # Store as string
        }

    def _result_to_decision_properties(
        self,
        decision_id: str,
        request: AgentRequest,
        result: ValidationResult
    ) -> Dict[str, Any]:
        """
        Convert ValidationResult to Decision node properties.

        Args:
            decision_id: Decision ID
            request: Original request
            result: Validation result

        Returns:
            Dictionary of decision properties
        """
        # Determine decision type from validation status
        decision_type_mapping = {
            "approved": "approval",
            "rejected": "rejection",
            "escalated": "escalation",
            "revision_required": "revision_request"
        }

        decision_type = decision_type_mapping.get(
            result.status.value,
            "unknown"
        )

        # Determine impact level from violations
        impact_level = "low"
        if result.critical_violations:
            impact_level = "high"
        elif result.high_violations:
            impact_level = "medium"

        return {
            "id": decision_id,
            "decision_type": decision_type,
            "timestamp": result.timestamp.isoformat(),
            "author": "validation_engine",
            "author_type": "system",
            "rationale": result.reasoning,
            "confidence": result.confidence,
            "impact_level": impact_level,
            "reversible": True,
            "request_id": request.id,
            "status": result.status.value,
            "violation_count": len(result.violations),
            "warning_count": len(result.warnings),
            "processing_time_ms": result.processing_time_ms,
            "metadata": str(result.metadata)
        }

    def get_node_sync(
        self,
        label: str,
        node_id: str,
        id_property: str = "id"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a node synchronously.

        Args:
            label: Node label
            node_id: Node ID
            id_property: ID property name

        Returns:
            Node properties or None
        """
        try:
            result = AsyncSync.run_sync(
                self.graph_ops.get_node(label, node_id, id_property)
            )
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve node: {e}")
            return None
