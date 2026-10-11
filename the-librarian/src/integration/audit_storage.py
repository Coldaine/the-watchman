"""
Graph-based audit storage backend for persisting audit records in Neo4j.

Stores audit events as AuditEvent nodes with relationships to related entities,
enabling immutable audit trail queries and compliance reporting.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..graph.operations import GraphOperations
from ..graph.schema import NodeLabels, RelationshipTypes

logger = logging.getLogger(__name__)


class GraphAuditStorage:
    """Stores audit records in Neo4j as AuditEvent nodes."""

    def __init__(self, graph_ops: GraphOperations):
        """
        Initialize with graph operations.

        Args:
            graph_ops: Graph operations instance
        """
        self.graph_ops = graph_ops

    async def store_audit_record(self, record: Dict[str, Any]) -> str:
        """
        Store audit record as AuditEvent node.

        Args:
            record: Audit record dictionary with keys:
                - id: Unique audit record ID
                - timestamp: ISO 8601 timestamp
                - event_type: Type of event (validation, decision, drift_detection)
                - request_id: Associated request ID (optional)
                - agent_id: Agent that triggered event (optional)
                - target_id: Target of validation (optional)
                - target_type: Type of target (optional)
                - decision: Decision made (optional)
                - result: Validation result (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Created audit event node ID

        Raises:
            RuntimeError: If storage fails
        """
        try:
            # Prepare properties for AuditEvent node
            properties = {
                "id": record["id"],
                "timestamp": record["timestamp"],
                "event_type": record["event_type"],
            }

            # Add optional fields
            if "request_id" in record and record["request_id"]:
                properties["request_id"] = record["request_id"]

            if "agent_id" in record and record["agent_id"]:
                properties["agent_id"] = record["agent_id"]

            if "target_id" in record and record["target_id"]:
                properties["target_id"] = record["target_id"]

            if "target_type" in record and record["target_type"]:
                properties["target_type"] = record["target_type"]

            if "decision" in record and record["decision"]:
                properties["decision"] = record["decision"]

            # Store result and metadata as JSON strings
            if "result" in record and record["result"]:
                properties["result"] = json.dumps(record["result"])

            if "metadata" in record and record["metadata"]:
                properties["metadata"] = json.dumps(record["metadata"])

            # Create AuditEvent node
            audit_id = await self.graph_ops.create_node(
                label=NodeLabels.AUDIT_EVENT,
                properties=properties
            )

            logger.info(f"Stored audit record: {audit_id} (type: {record['event_type']})")

            # Create relationships to related nodes if present
            if "target_id" in record and record["target_id"]:
                await self._link_to_target(audit_id, record)

            if "request_id" in record and record["request_id"]:
                await self._link_to_request(audit_id, record)

            return audit_id

        except Exception as e:
            logger.error(f"Failed to store audit record: {e}")
            raise RuntimeError(f"Audit storage failed: {e}")

    async def _link_to_target(self, audit_id: str, record: Dict[str, Any]):
        """
        Create AUDITS relationship from audit event to target node.

        Args:
            audit_id: AuditEvent node ID
            record: Audit record with target information
        """
        try:
            # Determine target label from target_type
            target_type = record.get("target_type", "Architecture")
            label_mapping = {
                "architecture": NodeLabels.ARCHITECTURE,
                "design": NodeLabels.DESIGN,
                "requirement": NodeLabels.REQUIREMENT,
                "code": NodeLabels.CODE_ARTIFACT,
            }
            target_label = label_mapping.get(target_type.lower(), NodeLabels.ARCHITECTURE)

            # Create relationship if target node exists
            await self.graph_ops.create_relationship(
                from_label=NodeLabels.AUDIT_EVENT,
                from_id=audit_id,
                rel_type=RelationshipTypes.AUDITS,
                to_label=target_label,
                to_id=record["target_id"],
                properties={
                    "event_type": record["event_type"],
                    "timestamp": record["timestamp"]
                },
                from_id_prop="id",
                to_id_prop="id"
            )

            logger.debug(f"Linked audit {audit_id} to target {record['target_id']}")

        except Exception as e:
            logger.warning(f"Failed to link audit to target: {e}")
            # Don't fail the entire storage operation if linking fails

    async def _link_to_request(self, audit_id: str, record: Dict[str, Any]):
        """
        Create RECORDS relationship from audit event to request node.

        Args:
            audit_id: AuditEvent node ID
            record: Audit record with request information
        """
        try:
            await self.graph_ops.create_relationship(
                from_label=NodeLabels.AUDIT_EVENT,
                from_id=audit_id,
                rel_type=RelationshipTypes.RECORDS,
                to_label=NodeLabels.AGENT_REQUEST,
                to_id=record["request_id"],
                properties={
                    "timestamp": record["timestamp"]
                },
                from_id_prop="id",
                to_id_prop="id"
            )

            logger.debug(f"Linked audit {audit_id} to request {record['request_id']}")

        except Exception as e:
            logger.warning(f"Failed to link audit to request: {e}")
            # Don't fail the entire storage operation if linking fails

    async def get_audit_trail(
        self,
        target_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for a target node.

        Args:
            target_id: Target node ID
            limit: Maximum records to return

        Returns:
            List of audit records sorted by timestamp (newest first)
        """
        query = """
        MATCH (audit:AuditEvent)-[:AUDITS]->(target)
        WHERE target.id = $target_id
        RETURN audit
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        try:
            results = await self.graph_ops.query(query, {
                "target_id": target_id,
                "limit": limit
            })

            audit_records = []
            for record in results:
                audit_node = dict(record["audit"])

                # Parse JSON fields
                if "result" in audit_node and audit_node["result"]:
                    audit_node["result"] = json.loads(audit_node["result"])

                if "metadata" in audit_node and audit_node["metadata"]:
                    audit_node["metadata"] = json.loads(audit_node["metadata"])

                audit_records.append(audit_node)

            logger.debug(f"Retrieved {len(audit_records)} audit records for {target_id}")
            return audit_records

        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []

    async def get_validation_history(
        self,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get validation event history.

        Args:
            agent_id: Filter by agent ID (optional)
            since: Filter events after this timestamp (optional)
            limit: Maximum records

        Returns:
            List of validation events sorted by timestamp (newest first)
        """
        # Build filter conditions
        filters = ["audit.event_type = 'validation'"]
        params = {"limit": limit}

        if agent_id:
            filters.append("audit.agent_id = $agent_id")
            params["agent_id"] = agent_id

        if since:
            filters.append("audit.timestamp >= $since")
            params["since"] = since.isoformat()

        where_clause = " AND ".join(filters)

        query = f"""
        MATCH (audit:AuditEvent)
        WHERE {where_clause}
        RETURN audit
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        try:
            results = await self.graph_ops.query(query, params)

            validation_events = []
            for record in results:
                audit_node = dict(record["audit"])

                # Parse JSON fields
                if "result" in audit_node and audit_node["result"]:
                    audit_node["result"] = json.loads(audit_node["result"])

                if "metadata" in audit_node and audit_node["metadata"]:
                    audit_node["metadata"] = json.loads(audit_node["metadata"])

                validation_events.append(audit_node)

            logger.debug(f"Retrieved {len(validation_events)} validation events")
            return validation_events

        except Exception as e:
            logger.error(f"Failed to retrieve validation history: {e}")
            return []

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit events by type.

        Args:
            event_type: Event type to filter (validation, decision, drift_detection)
            limit: Maximum records
            since: Filter events after this timestamp (optional)

        Returns:
            List of audit events
        """
        params = {
            "event_type": event_type,
            "limit": limit
        }

        where_conditions = ["audit.event_type = $event_type"]

        if since:
            where_conditions.append("audit.timestamp >= $since")
            params["since"] = since.isoformat()

        where_clause = " AND ".join(where_conditions)

        query = f"""
        MATCH (audit:AuditEvent)
        WHERE {where_clause}
        RETURN audit
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        try:
            results = await self.graph_ops.query(query, params)

            events = []
            for record in results:
                audit_node = dict(record["audit"])

                # Parse JSON fields
                if "result" in audit_node and audit_node["result"]:
                    audit_node["result"] = json.loads(audit_node["result"])

                if "metadata" in audit_node and audit_node["metadata"]:
                    audit_node["metadata"] = json.loads(audit_node["metadata"])

                events.append(audit_node)

            logger.debug(f"Retrieved {len(events)} events of type {event_type}")
            return events

        except Exception as e:
            logger.error(f"Failed to retrieve events by type: {e}")
            return []

    async def get_statistics(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit trail statistics.

        Args:
            since: Calculate statistics for events after this timestamp (optional)

        Returns:
            Dictionary with statistics:
                - total_events: Total number of events
                - by_type: Count by event type
                - by_decision: Count by decision type
                - by_agent: Count by agent
        """
        params = {}
        where_clause = ""

        if since:
            where_clause = "WHERE audit.timestamp >= $since"
            params["since"] = since.isoformat()

        query = f"""
        MATCH (audit:AuditEvent)
        {where_clause}
        RETURN
            count(audit) as total,
            collect(DISTINCT audit.event_type) as event_types,
            collect(DISTINCT audit.decision) as decisions,
            collect(DISTINCT audit.agent_id) as agents
        """

        try:
            results = await self.graph_ops.query(query, params)

            if not results:
                return {
                    "total_events": 0,
                    "by_type": {},
                    "by_decision": {},
                    "by_agent": {}
                }

            record = results[0]

            # Get counts by type
            by_type_query = f"""
            MATCH (audit:AuditEvent)
            {where_clause}
            RETURN audit.event_type as type, count(*) as count
            """

            type_results = await self.graph_ops.query(by_type_query, params)
            by_type = {r["type"]: r["count"] for r in type_results}

            # Get counts by decision
            by_decision_query = f"""
            MATCH (audit:AuditEvent)
            {where_clause}
            WHERE audit.decision IS NOT NULL
            RETURN audit.decision as decision, count(*) as count
            """

            decision_results = await self.graph_ops.query(by_decision_query, params)
            by_decision = {r["decision"]: r["count"] for r in decision_results}

            # Get counts by agent
            by_agent_query = f"""
            MATCH (audit:AuditEvent)
            {where_clause}
            WHERE audit.agent_id IS NOT NULL
            RETURN audit.agent_id as agent, count(*) as count
            """

            agent_results = await self.graph_ops.query(by_agent_query, params)
            by_agent = {r["agent"]: r["count"] for r in agent_results}

            return {
                "total_events": record["total"],
                "by_type": by_type,
                "by_decision": by_decision,
                "by_agent": by_agent
            }

        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {
                "total_events": 0,
                "by_type": {},
                "by_decision": {},
                "by_agent": {},
                "error": str(e)
            }
