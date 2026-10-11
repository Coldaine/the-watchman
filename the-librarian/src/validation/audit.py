"""Audit trail logging for validation events."""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .models import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Immutable audit record for validation events."""
    id: str
    timestamp: datetime
    event_type: str                          # validation|decision|drift_detection
    request_id: Optional[str] = None         # Associated request ID
    agent_id: Optional[str] = None           # Agent that triggered event
    target_id: Optional[str] = None          # Target of validation
    target_type: Optional[str] = None        # Type of target
    result: Optional[Dict[str, Any]] = None  # Validation result
    decision: Optional[str] = None           # Decision made (approved/rejected/etc)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "result": self.result,
            "decision": self.decision,
            "metadata": self.metadata
        }


class AuditLogger:
    """Logs validation events to create immutable audit trail."""

    def __init__(self, storage: Optional[Any] = None):
        """Initialize audit logger.

        Args:
            storage: Storage backend for audit records (e.g., graph database)
        """
        self.storage = storage
        self.records: List[AuditRecord] = []  # In-memory cache

    def log_validation(self, request: Dict[str, Any],
                      result: ValidationResult) -> str:
        """Log a validation event.

        Args:
            request: The agent request that was validated
            result: The validation result

        Returns:
            The audit record ID
        """
        record = AuditRecord(
            id=f"AUD-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            event_type="validation",
            request_id=request.get("id"),
            agent_id=request.get("agent_id"),
            target_id=request.get("target_id"),
            target_type=request.get("target_type"),
            result=result.to_dict(),
            decision=result.status.value,
            metadata={
                "processing_time_ms": result.processing_time_ms,
                "violations_count": len(result.violations),
                "rules_executed": result.metadata.get("rules_executed", 0)
            }
        )

        self._store_record(record)
        return record.id

    def log_decision(self, decision: Dict[str, Any]) -> str:
        """Log a decision event.

        Args:
            decision: The decision details

        Returns:
            The audit record ID
        """
        record = AuditRecord(
            id=f"AUD-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            event_type="decision",
            request_id=decision.get("request_id"),
            agent_id=decision.get("agent_id"),
            target_id=decision.get("target_id"),
            target_type=decision.get("target_type"),
            decision=decision.get("decision_type"),
            metadata={
                "rationale": decision.get("rationale"),
                "confidence": decision.get("confidence"),
                "impact_level": decision.get("impact_level")
            }
        )

        self._store_record(record)
        return record.id

    def log_drift_detection(self, violations: List[Dict[str, Any]]) -> str:
        """Log drift detection event.

        Args:
            violations: List of drift violations found

        Returns:
            The audit record ID
        """
        record = AuditRecord(
            id=f"AUD-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            event_type="drift_detection",
            metadata={
                "violations_count": len(violations),
                "violations": violations
            }
        )

        self._store_record(record)
        return record.id

    def _store_record(self, record: AuditRecord):
        """Store audit record.

        Args:
            record: The audit record to store
        """
        # Add to in-memory cache
        self.records.append(record)

        # Store in external storage if available
        if self.storage:
            try:
                self.storage.store_audit_record(record.to_dict())
            except Exception as e:
                logger.error(f"Error storing audit record: {e}", exc_info=True)

    def get_record(self, record_id: str) -> Optional[AuditRecord]:
        """Retrieve an audit record by ID.

        Args:
            record_id: The ID of the record to retrieve

        Returns:
            The audit record or None if not found
        """
        for record in self.records:
            if record.id == record_id:
                return record
        return None

    def get_records_by_request(self, request_id: str) -> List[AuditRecord]:
        """Get all audit records for a specific request.

        Args:
            request_id: The request ID to filter by

        Returns:
            List of audit records for the request
        """
        return [r for r in self.records if r.request_id == request_id]

    def get_records_by_agent(self, agent_id: str,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[AuditRecord]:
        """Get all audit records for a specific agent.

        Args:
            agent_id: The agent ID to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of audit records for the agent
        """
        records = [r for r in self.records if r.agent_id == agent_id]

        if start_time:
            records = [r for r in records if r.timestamp >= start_time]

        if end_time:
            records = [r for r in records if r.timestamp <= end_time]

        return records

    def get_recent_records(self, limit: int = 100,
                          event_type: Optional[str] = None) -> List[AuditRecord]:
        """Get recent audit records.

        Args:
            limit: Maximum number of records to return
            event_type: Optional filter by event type

        Returns:
            List of recent audit records
        """
        records = self.records

        if event_type:
            records = [r for r in records if r.event_type == event_type]

        # Sort by timestamp descending
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics.

        Returns:
            Dictionary with audit statistics
        """
        total_records = len(self.records)

        by_type = {}
        by_decision = {}

        for record in self.records:
            # Count by event type
            event_type = record.event_type
            by_type[event_type] = by_type.get(event_type, 0) + 1

            # Count by decision
            if record.decision:
                by_decision[record.decision] = by_decision.get(record.decision, 0) + 1

        return {
            "total_records": total_records,
            "by_event_type": by_type,
            "by_decision": by_decision,
            "earliest_record": min(r.timestamp for r in self.records) if self.records else None,
            "latest_record": max(r.timestamp for r in self.records) if self.records else None
        }


class AuditTrail:
    """Async wrapper for audit logging with graph database integration."""

    def __init__(self, connection=None):
        """Initialize audit trail.

        Args:
            connection: Neo4j connection instance
        """
        self.connection = connection
        self.logger = AuditLogger(storage=None)  # In-memory for now

    async def log_request(self, request, response):
        """Log an agent request and response.

        Args:
            request: AgentRequest instance
            response: AgentResponse instance

        Returns:
            Audit record ID
        """
        # Create a validation-like result for logging
        result_dict = {
            "status": response.status,
            "violations": response.violations,
            "warnings": response.warnings,
            "confidence": response.confidence,
            "processing_time_ms": response.processing_time_ms
        }

        # Log using the synchronous logger
        record_id = self.logger.log_validation(
            request.to_dict(),
            type('Result', (), {
                'to_dict': lambda: result_dict,
                'status': type('Status', (), {'value': response.status})(),
                'violations': response.violations,
                'processing_time_ms': response.processing_time_ms,
                'metadata': {}
            })()
        )

        # Optionally store in graph database
        if self.connection:
            try:
                query = """
                CREATE (a:AuditRecord {
                    id: $id,
                    timestamp: datetime($timestamp),
                    event_type: 'validation',
                    request_id: $request_id,
                    agent_id: $agent_id,
                    decision: $decision
                })
                """
                await self.connection.execute_write(query, {
                    "id": record_id,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request.id,
                    "agent_id": request.agent_id,
                    "decision": response.status
                })
            except Exception as e:
                logger.error(f"Failed to store audit record in graph: {e}", exc_info=True)

        return record_id

    async def log_decision(self, decision):
        """Log a decision.

        Args:
            decision: Decision instance

        Returns:
            Audit record ID
        """
        record_id = self.logger.log_decision(decision.to_dict())

        # Optionally store in graph database
        if self.connection:
            try:
                query = """
                CREATE (d:Decision {
                    id: $id,
                    timestamp: datetime($timestamp),
                    decision_type: $decision_type,
                    author: $author,
                    author_type: $author_type,
                    rationale: $rationale,
                    request_id: $request_id
                })
                """
                await self.connection.execute_write(query, {
                    "id": decision.id,
                    "timestamp": decision.timestamp.isoformat(),
                    "decision_type": decision.decision_type,
                    "author": decision.author,
                    "author_type": decision.author_type,
                    "rationale": decision.rationale,
                    "request_id": decision.request_id
                })
            except Exception as e:
                logger.error(f"Failed to store decision in graph: {e}", exc_info=True)

        return record_id
