# Agent Communication Protocol

## Overview
The Agent Protocol subdomain defines how AI agents (Claude, Copilot, Gemini, etc.) communicate with the Librarian system. It establishes the contract for requests, responses, and the governance workflow that ensures all agents comply with documentation and code standards.

## Core Concepts

### Agent Identity
Every agent must identify itself with:
- `agent_id`: Unique identifier (e.g., "claude-3", "copilot-2.1", "gemini-pro")
- `agent_type`: Classification (e.g., "code-generator", "reviewer", "documenter")
- `session_id`: Unique session identifier for tracking conversations
- `capabilities`: List of what the agent can do (e.g., ["read", "write", "analyze"])

### Request Types
Agents can make four types of requests:
- **APPROVAL**: Request permission to make changes
- **QUERY**: Ask for information from the knowledge graph
- **VALIDATE**: Check if a proposed change would be compliant
- **REPORT**: Submit completion status or encountered issues

### Governance States
Every agent request moves through states:
1. **PENDING**: Initial submission
2. **VALIDATING**: Librarian checking compliance
3. **APPROVED**: Change authorized
4. **REJECTED**: Change violates constraints
5. **ESCALATED**: Requires human intervention
6. **COMPLETED**: Change successfully applied

## Implementation Details

### Request Message Format
```python
@dataclass
class AgentRequest:
    # Identity
    agent_id: str
    session_id: str
    timestamp: datetime

    # Request Details
    request_type: Literal["APPROVAL", "QUERY", "VALIDATE", "REPORT"]
    action: Literal["create", "modify", "delete", "read"]

    # Target Information
    target_type: Literal["architecture", "design", "code", "test", "docs"]
    target_path: Optional[str]  # For existing items
    target_id: Optional[str]    # Graph node ID if known

    # Content
    content: str                 # Proposed change or query
    rationale: str              # Why this change is needed

    # References
    references: List[str]       # IDs of specs consulted
    context_used: List[str]     # What information informed this request

    # Compliance
    deviations: List[Dict[str, str]]  # Any departures from standards
    risk_assessment: Optional[str]     # Agent's assessment of impact
```

### Response Message Format
```python
@dataclass
class LibrarianResponse:
    # Identity
    request_id: str
    timestamp: datetime
    processing_time_ms: int

    # Decision
    status: Literal["approved", "rejected", "escalated", "clarification_needed"]
    confidence: float  # 0.0 to 1.0

    # Feedback
    feedback: str                      # Explanation of decision
    violations: List[ViolationDetail]  # Specific issues found
    suggestions: List[str]             # How to fix issues

    # For Approvals
    approved_location: Optional[str]   # Where to place the content
    assigned_id: Optional[str]         # Graph node ID assigned
    constraints: List[str]             # Additional constraints to follow

    # For Escalations
    escalation_reason: Optional[str]
    human_review_url: Optional[str]
    estimated_review_time: Optional[int]  # minutes

    # Context Provided (for QUERY requests)
    context: Optional[Dict[str, Any]]
    relevant_nodes: Optional[List[NodeSummary]]
```

### Validation Rules
```python
class ProtocolValidator:
    """Core validation rules for agent requests"""

    REQUIRED_FIELDS = {
        "APPROVAL": ["content", "rationale", "target_type"],
        "QUERY": ["content"],
        "VALIDATE": ["content", "target_type"],
        "REPORT": ["request_id", "completed", "changes_made"]
    }

    def validate_request(self, request: AgentRequest) -> ValidationResult:
        rules = [
            self._check_required_fields,
            self._check_agent_authorization,
            self._check_rate_limits,
            self._check_content_format,
            self._validate_references,
            self._check_target_exists
        ]

        for rule in rules:
            result = rule(request)
            if not result.passed:
                return result

        return ValidationResult(passed=True)
```

## Interfaces

### REST API Endpoints
```yaml
/agent/request:
  method: POST
  auth: Bearer token (agent-specific)
  rate_limit: 60/minute per agent
  body: AgentRequest
  response: LibrarianResponse

/agent/status/{request_id}:
  method: GET
  auth: Bearer token
  response: RequestStatus

/agent/context:
  method: POST
  auth: Bearer token
  body: ContextQuery
  response: ContextResponse

/agent/capabilities:
  method: GET
  auth: Bearer token
  response: AgentCapabilities
```

### WebSocket Events (Future)
```yaml
events:
  - request.submitted
  - request.approved
  - request.rejected
  - request.escalated
  - context.updated
  - specification.changed
```

## Configuration

### Agent Registry
```yaml
# config/agents.yaml
agents:
  claude-3:
    type: code-generator
    capabilities: [read, write, analyze]
    rate_limit: 100/hour
    max_request_size: 50KB
    allowed_targets: [architecture, design, code]

  copilot-2:
    type: code-completer
    capabilities: [read, suggest]
    rate_limit: 200/hour
    max_request_size: 10KB
    allowed_targets: [code]

  gemini-pro:
    type: reviewer
    capabilities: [read, analyze, validate]
    rate_limit: 50/hour
    allowed_targets: [all]
```

### Protocol Settings
```yaml
# config/protocol.yaml
protocol:
  version: "1.0"

  timeouts:
    validation: 5000ms
    response: 10000ms
    escalation: 86400000ms  # 24 hours

  limits:
    max_content_size: 100KB
    max_references: 20
    max_deviations: 5
    max_retry_attempts: 3

  compliance:
    strict_mode: true
    allow_deviations: false
    require_rationale: true
    enforce_references: true
```

## Common Operations

### 1. Agent Requesting Approval
```python
# Agent wants to create a new design document
request = AgentRequest(
    agent_id="claude-3",
    session_id="sess-123",
    request_type="APPROVAL",
    action="create",
    target_type="design",
    target_path="docs/design/new-feature.md",
    content="# New Feature Design\n...",
    rationale="Implementing user story US-123",
    references=["arch-001", "req-045"],
    deviations=[]
)

response = librarian.process_request(request)

if response.status == "approved":
    # Agent proceeds with creation at approved_location
    create_file(response.approved_location, request.content)
    report_completion(response.request_id)
```

### 2. Agent Querying for Context
```python
# Agent needs information before making changes
query = AgentRequest(
    agent_id="copilot-2",
    request_type="QUERY",
    content="What are the current authentication requirements?"
)

response = librarian.process_request(query)
# Response contains relevant documentation and specifications
```

### 3. Handling Rejection
```python
if response.status == "rejected":
    print(f"Request rejected: {response.feedback}")
    for violation in response.violations:
        print(f"- {violation.rule}: {violation.description}")

    # Agent can attempt to fix and resubmit
    fixed_request = fix_violations(request, response.suggestions)
    retry_response = librarian.process_request(fixed_request)
```

### 4. Escalation Handling
```python
if response.status == "escalated":
    print(f"Human review required: {response.escalation_reason}")
    print(f"Review URL: {response.human_review_url}")

    # Agent must wait for human decision
    # Can poll status endpoint or wait for webhook
    status = poll_status(response.request_id)
```

## Troubleshooting

### Common Issues

#### "Agent not authorized"
- **Cause**: Agent ID not in registry or lacks required capability
- **Solution**: Register agent in `config/agents.yaml` with appropriate capabilities

#### "Rate limit exceeded"
- **Cause**: Agent sending too many requests
- **Solution**: Implement exponential backoff, check rate limit headers

#### "Invalid reference"
- **Cause**: Referenced specification doesn't exist
- **Solution**: Query available specifications first, ensure IDs are correct

#### "Content format violation"
- **Cause**: Document doesn't match required template
- **Solution**: Check `TEMPLATES.md` for required format, use validation endpoint first

#### "Circular dependency detected"
- **Cause**: Proposed change creates circular reference in graph
- **Solution**: Review dependency chain, restructure to avoid cycle

### Debug Mode
Enable detailed protocol logging:
```python
# Enable debug logging
import logging
logging.getLogger("librarian.protocol").setLevel(logging.DEBUG)

# Protocol will log:
# - Raw request/response payloads
# - Validation rule execution
# - Graph queries performed
# - Decision reasoning
```

### Performance Metrics
Monitor protocol performance:
```python
metrics = librarian.get_protocol_metrics()
print(f"Avg validation time: {metrics.avg_validation_ms}ms")
print(f"Approval rate: {metrics.approval_rate}%")
print(f"Escalation rate: {metrics.escalation_rate}%")
```

## References

- **Main Architecture**: [`docs/architecture.md`](../architecture.md)
- **API Specification**: OpenAPI available at `/docs` when server running
- **Graph Schema**: [`docs/subdomains/graph-operations.md`](./graph-operations.md)
- **Validation Rules**: [`docs/subdomains/validation-engine.md`](./validation-engine.md)
- **Message Schemas**: [`src/models/protocol.py`](../../src/models/protocol.py)
- **Agent Examples**: [`examples/agent-integration/`](../../examples/agent-integration/)