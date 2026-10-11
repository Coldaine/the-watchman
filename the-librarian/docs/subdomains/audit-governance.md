# Audit Trail and Governance

## Overview
The Audit and Governance subdomain provides immutable tracking of all system changes, agent interactions, and decisions. It ensures accountability, enables compliance reporting, and maintains the chain of custody for all modifications to the knowledge base.

## Core Concepts

### Immutability Principles
- **No Deletions**: Audit records are never deleted, only marked as superseded
- **Cryptographic Integrity**: Optional hashing for tamper detection
- **Complete Attribution**: Every change linked to agent/user
- **Temporal Ordering**: Strict timestamp-based sequencing

### Audit Event Types
- **Agent Interactions**: All requests, responses, and decisions
- **Document Changes**: Creation, updates, supersession
- **Validation Events**: Rule execution and violations
- **System Events**: Configuration changes, deployments
- **Human Interventions**: Escalations and manual overrides

### Governance Controls
- **Access Control**: Who can do what
- **Approval Workflows**: Multi-stage decision processes
- **Compliance Tracking**: Adherence to standards
- **Performance Metrics**: Agent behavior analytics

## Implementation Details

### Audit Event Schema

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import hashlib
import json

class EventCategory(Enum):
    AGENT_REQUEST = "agent_request"
    VALIDATION = "validation"
    DECISION = "decision"
    DOCUMENT_CHANGE = "document_change"
    SYSTEM = "system"
    HUMAN_INTERVENTION = "human_intervention"

class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Immutable audit event record"""

    # Identity
    event_id: str                       # Unique event identifier
    timestamp: datetime                  # When event occurred
    category: EventCategory             # Event classification
    event_type: str                     # Specific event type

    # Actor
    actor_id: str                       # Who/what triggered event
    actor_type: str                     # agent|human|system
    session_id: Optional[str]           # Session context

    # Target
    target_id: Optional[str]            # What was affected
    target_type: Optional[str]          # Node type affected

    # Event Data
    action: str                         # What happened
    outcome: str                        # success|failure|partial
    details: Dict[str, Any]             # Event-specific data

    # Audit Metadata
    severity: EventSeverity
    tags: List[str]                     # Searchable tags
    parent_event_id: Optional[str]      # For event chains

    # Integrity
    previous_hash: Optional[str]        # Hash of previous event
    event_hash: Optional[str]           # Hash of this event

    def calculate_hash(self) -> str:
        """Calculate cryptographic hash of event"""
        event_dict = {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'category': self.category.value,
            'actor_id': self.actor_id,
            'action': self.action,
            'details': self.details,
            'previous_hash': self.previous_hash
        }

        event_json = json.dumps(event_dict, sort_keys=True)
        return hashlib.sha256(event_json.encode()).hexdigest()
```

### Audit Logger

```python
class AuditLogger:
    """Central audit logging service"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph
        self.current_hash = None
        self.event_queue = []

    async def log_event(self, event: AuditEvent) -> str:
        """Log audit event to graph"""

        # Set hash chain
        event.previous_hash = self.current_hash
        event.event_hash = event.calculate_hash()

        # Create audit node
        cypher = """
            CREATE (e:AuditEvent {
                event_id: $event_id,
                timestamp: $timestamp,
                category: $category,
                event_type: $event_type,
                actor_id: $actor_id,
                actor_type: $actor_type,
                session_id: $session_id,
                target_id: $target_id,
                target_type: $target_type,
                action: $action,
                outcome: $outcome,
                details: $details,
                severity: $severity,
                tags: $tags,
                parent_event_id: $parent_event_id,
                previous_hash: $previous_hash,
                event_hash: $event_hash
            })

            // Link to target if exists
            WITH e
            OPTIONAL MATCH (target {id: $target_id})
            FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                CREATE (e)-[:AFFECTS]->(target)
            )

            // Link to parent event if exists
            WITH e
            OPTIONAL MATCH (parent:AuditEvent {event_id: $parent_event_id})
            FOREACH (_ IN CASE WHEN parent IS NOT NULL THEN [1] ELSE [] END |
                CREATE (e)-[:FOLLOWS]->(parent)
            )

            RETURN e.event_id
        """

        result = await self.graph.query(cypher, {
            'event_id': event.event_id,
            'timestamp': event.timestamp,
            'category': event.category.value,
            'event_type': event.event_type,
            'actor_id': event.actor_id,
            'actor_type': event.actor_type,
            'session_id': event.session_id,
            'target_id': event.target_id,
            'target_type': event.target_type,
            'action': event.action,
            'outcome': event.outcome,
            'details': json.dumps(event.details),
            'severity': event.severity.value,
            'tags': event.tags,
            'parent_event_id': event.parent_event_id,
            'previous_hash': event.previous_hash,
            'event_hash': event.event_hash
        })

        # Update current hash for chain
        self.current_hash = event.event_hash

        # Trigger any compliance checks
        await self._check_compliance(event)

        return event.event_id

    async def log_agent_request(self, request: AgentRequest,
                               response: LibrarianResponse):
        """Log agent interaction"""

        event = AuditEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            category=EventCategory.AGENT_REQUEST,
            event_type="agent_request_processed",
            actor_id=request.agent_id,
            actor_type="agent",
            session_id=request.session_id,
            target_id=request.target_id,
            target_type=request.target_type,
            action=f"{request.action} {request.target_type}",
            outcome="success" if response.status == "approved" else "rejected",
            details={
                'request_type': request.request_type,
                'rationale': request.rationale,
                'response_status': response.status,
                'processing_time_ms': response.processing_time_ms,
                'violations': [v.dict() for v in response.violations]
            },
            severity=EventSeverity.INFO,
            tags=[request.agent_id, request.target_type, response.status]
        )

        return await self.log_event(event)
```

### Decision Tracking

```python
class DecisionTracker:
    """Track and analyze decisions"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph
        self.audit_logger = AuditLogger(graph)

    async def record_decision(self, decision: Decision) -> str:
        """Record a decision with full context"""

        # Create decision node
        cypher = """
            CREATE (d:Decision {
                id: $id,
                decision_type: $decision_type,
                timestamp: $timestamp,
                author: $author,
                author_type: $author_type,
                rationale: $rationale,
                confidence: $confidence,
                impact_level: $impact_level,
                reversible: $reversible
            })

            // Link to request if exists
            WITH d
            OPTIONAL MATCH (r:AgentRequest {id: $request_id})
            FOREACH (_ IN CASE WHEN r IS NOT NULL THEN [1] ELSE [] END |
                CREATE (d)-[:DECIDES]->(r)
            )

            // Link affected nodes
            WITH d
            UNWIND $affected_nodes as node_id
            MATCH (n {id: node_id})
            CREATE (d)-[:AFFECTS]->(n)

            RETURN d.id
        """

        result = await self.graph.query(cypher, {
            'id': decision.id,
            'decision_type': decision.decision_type,
            'timestamp': decision.timestamp,
            'author': decision.author,
            'author_type': decision.author_type,
            'rationale': decision.rationale,
            'confidence': decision.confidence,
            'impact_level': decision.impact_level,
            'reversible': decision.reversible,
            'request_id': decision.request_id,
            'affected_nodes': decision.affected_nodes
        })

        # Log as audit event
        await self.audit_logger.log_event(AuditEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:12]}",
            timestamp=decision.timestamp,
            category=EventCategory.DECISION,
            event_type="decision_recorded",
            actor_id=decision.author,
            actor_type=decision.author_type,
            action="make_decision",
            outcome="success",
            details={
                'decision_id': decision.id,
                'decision_type': decision.decision_type,
                'confidence': decision.confidence,
                'impact_level': decision.impact_level
            },
            severity=EventSeverity.INFO,
            tags=['decision', decision.decision_type]
        ))

        return decision.id

    async def get_decision_history(self, node_id: str) -> List[Decision]:
        """Get all decisions affecting a node"""

        cypher = """
            MATCH (d:Decision)-[:AFFECTS]->(n {id: $node_id})
            RETURN d
            ORDER BY d.timestamp DESC
        """

        results = await self.graph.query(cypher, {'node_id': node_id})
        return [Decision(**r['d']) for r in results]
```

### Compliance Monitoring

```python
class ComplianceMonitor:
    """Monitor and report on compliance"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph
        self.compliance_rules = self._load_compliance_rules()

    async def check_compliance(self, timeframe: timedelta = None) -> ComplianceReport:
        """Generate compliance report"""

        report = ComplianceReport(
            generated_at=datetime.now(),
            timeframe=timeframe
        )

        # Check agent compliance
        report.agent_compliance = await self._check_agent_compliance(timeframe)

        # Check documentation compliance
        report.doc_compliance = await self._check_doc_compliance(timeframe)

        # Check process compliance
        report.process_compliance = await self._check_process_compliance(timeframe)

        # Calculate overall score
        report.overall_score = self._calculate_overall_score(report)

        return report

    async def _check_agent_compliance(self, timeframe: timedelta) -> Dict:
        """Check agent behavior compliance"""

        cypher = """
            MATCH (e:AuditEvent)
            WHERE e.category = 'agent_request'
            AND e.timestamp > $start_time
            WITH e.actor_id as agent_id,
                 count(*) as total_requests,
                 sum(CASE WHEN e.outcome = 'success' THEN 1 ELSE 0 END) as approved,
                 sum(CASE WHEN e.outcome = 'rejected' THEN 1 ELSE 0 END) as rejected
            RETURN agent_id,
                   total_requests,
                   approved,
                   rejected,
                   toFloat(approved) / total_requests as approval_rate
        """

        start_time = datetime.now() - timeframe if timeframe else datetime.min

        results = await self.graph.query(cypher, {'start_time': start_time})

        compliance = {
            'agents': {},
            'overall_approval_rate': 0,
            'violations': []
        }

        total_approved = 0
        total_requests = 0

        for r in results:
            agent_id = r['agent_id']
            approval_rate = r['approval_rate']

            compliance['agents'][agent_id] = {
                'total_requests': r['total_requests'],
                'approved': r['approved'],
                'rejected': r['rejected'],
                'approval_rate': approval_rate
            }

            # Check for violations
            if approval_rate < 0.8:  # Threshold for concern
                compliance['violations'].append({
                    'agent_id': agent_id,
                    'issue': 'low_approval_rate',
                    'rate': approval_rate
                })

            total_approved += r['approved']
            total_requests += r['total_requests']

        compliance['overall_approval_rate'] = \
            total_approved / total_requests if total_requests > 0 else 0

        return compliance
```

### Audit Queries

```python
class AuditQueryService:
    """Query audit trail"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph

    async def get_audit_trail(self, filters: Dict = None,
                             limit: int = 100) -> List[AuditEvent]:
        """Get filtered audit trail"""

        where_clauses = []
        params = {'limit': limit}

        if filters:
            if 'category' in filters:
                where_clauses.append("e.category = $category")
                params['category'] = filters['category']

            if 'actor_id' in filters:
                where_clauses.append("e.actor_id = $actor_id")
                params['actor_id'] = filters['actor_id']

            if 'start_time' in filters:
                where_clauses.append("e.timestamp >= $start_time")
                params['start_time'] = filters['start_time']

            if 'end_time' in filters:
                where_clauses.append("e.timestamp <= $end_time")
                params['end_time'] = filters['end_time']

            if 'severity' in filters:
                where_clauses.append("e.severity = $severity")
                params['severity'] = filters['severity']

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        cypher = f"""
            MATCH (e:AuditEvent)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.timestamp DESC
            LIMIT $limit
        """

        results = await self.graph.query(cypher, params)
        return [self._parse_audit_event(r['e']) for r in results]

    async def verify_audit_chain(self, start_event_id: str = None) -> bool:
        """Verify integrity of audit chain"""

        cypher = """
            MATCH (e:AuditEvent)
            ORDER BY e.timestamp
            RETURN e.event_id, e.event_hash, e.previous_hash
        """

        results = await self.graph.query(cypher, {})

        previous_hash = None
        for r in results:
            if r['previous_hash'] != previous_hash:
                print(f"Chain broken at event {r['event_id']}")
                return False
            previous_hash = r['event_hash']

        return True

    async def get_actor_activity(self, actor_id: str,
                                timeframe: timedelta = None) -> Dict:
        """Get activity summary for an actor"""

        start_time = datetime.now() - timeframe if timeframe else datetime.min

        cypher = """
            MATCH (e:AuditEvent {actor_id: $actor_id})
            WHERE e.timestamp > $start_time
            RETURN e.category as category,
                   e.action as action,
                   count(*) as count
            ORDER BY count DESC
        """

        results = await self.graph.query(cypher, {
            'actor_id': actor_id,
            'start_time': start_time
        })

        return {
            'actor_id': actor_id,
            'timeframe': timeframe,
            'activities': [
                {
                    'category': r['category'],
                    'action': r['action'],
                    'count': r['count']
                }
                for r in results
            ]
        }
```

## Interfaces

### Audit API Endpoints

```yaml
/audit/events:
  method: GET
  description: Query audit events
  params:
    category: optional string
    actor_id: optional string
    start_time: optional datetime
    end_time: optional datetime
    limit: integer (default 100)
  response: List[AuditEvent]

/audit/compliance:
  method: GET
  description: Get compliance report
  params:
    timeframe_days: optional integer
  response: ComplianceReport

/audit/decisions:
  method: GET
  description: Query decisions
  params:
    node_id: optional string
    author: optional string
  response: List[Decision]

/audit/verify:
  method: GET
  description: Verify audit chain integrity
  response:
    valid: boolean
    last_verified: datetime
    events_checked: integer
```

## Configuration

### Audit Configuration
```yaml
# config/audit.yaml
audit:
  # Storage settings
  storage:
    enable_hashing: true
    hash_algorithm: sha256
    compression: false

  # Retention policies
  retention:
    default_days: 365
    by_category:
      agent_request: 90
      validation: 30
      decision: -1  # Never delete
      document_change: 180
      system: 365
      human_intervention: -1  # Never delete

  # Compliance thresholds
  compliance:
    min_approval_rate: 0.8
    max_rejection_rate: 0.3
    max_escalation_rate: 0.1

    reporting:
      schedule: "0 0 * * 1"  # Weekly
      recipients:
        - admin@example.com

  # Performance
  batch_size: 100
  async_logging: true
  queue_size: 1000
```

### Governance Rules
```yaml
# config/governance.yaml
governance:
  # Access control
  access:
    read_audit:
      - role: admin
      - role: auditor
      - role: agent

    write_audit:
      - role: system

    delete_audit:
      # No one can delete audit records

  # Approval workflows
  workflows:
    high_impact_change:
      approvers: 2
      timeout: 24h
      escalation: admin

    constitution_override:
      approvers: 3
      require_human: true
      timeout: 48h

  # Agent policies
  agent_policies:
    max_requests_per_hour: 100
    max_rejections_before_block: 10
    required_approval_rate: 0.7
```

## Common Operations

### 1. Audit Agent Interaction
```python
async def audit_agent_interaction(request: AgentRequest,
                                 response: LibrarianResponse):
    """Complete audit of agent interaction"""

    logger = AuditLogger(graph)

    # Log the request
    request_event = await logger.log_agent_request(request, response)

    # If decision was made, track it
    if response.status in ['approved', 'rejected']:
        decision = Decision(
            id=f"DEC-{uuid.uuid4().hex[:8]}",
            decision_type=response.status,
            timestamp=datetime.now(),
            author="librarian",
            author_type="system",
            rationale=response.feedback,
            confidence=response.confidence,
            impact_level="medium",
            request_id=request.id,
            affected_nodes=[request.target_id] if request.target_id else []
        )

        await DecisionTracker(graph).record_decision(decision)
```

### 2. Generate Compliance Report
```python
async def generate_weekly_compliance_report():
    """Generate and distribute compliance report"""

    monitor = ComplianceMonitor(graph)

    # Generate report for last 7 days
    report = await monitor.check_compliance(
        timeframe=timedelta(days=7)
    )

    # Format report
    formatted = format_compliance_report(report)

    # Store report
    await store_report(report)

    # Notify stakeholders
    await notify_compliance_status(report, formatted)

    return report
```

### 3. Investigate Incident
```python
async def investigate_incident(incident_time: datetime,
                              actor_id: str = None):
    """Investigate events around incident"""

    query_service = AuditQueryService(graph)

    # Get events around incident time
    events = await query_service.get_audit_trail(
        filters={
            'start_time': incident_time - timedelta(hours=1),
            'end_time': incident_time + timedelta(hours=1),
            'actor_id': actor_id
        },
        limit=1000
    )

    # Analyze patterns
    analysis = {
        'total_events': len(events),
        'by_category': {},
        'by_severity': {},
        'errors': [],
        'suspicious_patterns': []
    }

    for event in events:
        # Count by category
        cat = event.category.value
        analysis['by_category'][cat] = \
            analysis['by_category'].get(cat, 0) + 1

        # Track errors
        if event.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
            analysis['errors'].append(event)

        # Check for suspicious patterns
        if event.outcome == 'failure' and event.category == EventCategory.AGENT_REQUEST:
            analysis['suspicious_patterns'].append({
                'event': event,
                'reason': 'repeated_failures'
            })

    return analysis
```

## Troubleshooting

### Common Issues

#### "Audit chain verification failed"
- **Cause**: Missing or corrupted audit event
- **Solution**: Investigate gap, check for system issues
```python
# Find break in chain
async def find_chain_break():
    events = await get_all_audit_events()
    for i, event in enumerate(events[1:]):
        if event.previous_hash != events[i].event_hash:
            return f"Break between {events[i].event_id} and {event.event_id}"
```

#### "Compliance report incomplete"
- **Cause**: Missing audit data or query timeout
- **Solution**: Check data completeness, optimize queries
```cypher
-- Check audit coverage
MATCH (e:AuditEvent)
RETURN e.category, count(*) as count,
       min(e.timestamp) as earliest,
       max(e.timestamp) as latest
```

#### "High audit storage usage"
- **Cause**: Verbose logging or no retention policy
- **Solution**: Implement retention, compress old events
```python
# Archive old events
async def archive_old_events(days=90):
    cutoff = datetime.now() - timedelta(days=days)
    # Move to archive storage
```

### Performance Monitoring
```python
# Audit performance metrics
metrics = audit_service.get_metrics()
print(f"Events per second: {metrics.events_per_second}")
print(f"Avg logging latency: {metrics.avg_latency_ms}ms")
print(f"Queue depth: {metrics.queue_depth}")
print(f"Storage size: {metrics.storage_gb}GB")
```

## References

- **Architecture Document**: [`docs/architecture.md`](../architecture.md)
- **Agent Protocol**: [`docs/subdomains/agent-protocol.md`](./agent-protocol.md)
- **Validation Engine**: [`docs/subdomains/validation-engine.md`](./validation-engine.md)
- **Compliance Standards**: ISO 27001, SOC 2
- **Audit Best Practices**: NIST Cybersecurity Framework