# Validation and Compliance Engine

## Overview
The Validation Engine subdomain enforces governance rules, detects specification drift, validates agent requests against constraints, and determines when human escalation is required. It acts as the quality gate that ensures all changes maintain system integrity and comply with architectural standards.

## Core Concepts

### Validation Layers
1. **Syntactic Validation**: Structure and format checks
2. **Semantic Validation**: Meaning and consistency checks
3. **Compliance Validation**: Standards and policy adherence
4. **Impact Validation**: Change consequence analysis

### Rule Categories
- **Constitution Rules**: Inviolable system constraints
- **Architecture Rules**: Design pattern enforcement
- **Documentation Rules**: Format and location standards
- **Process Rules**: Workflow and approval requirements
- **Quality Rules**: Code and documentation quality metrics

### Decision Types
- **APPROVED**: Change meets all requirements
- **REVISION_REQUIRED**: Fixable violations detected
- **ESCALATED**: Human judgment needed
- **REJECTED**: Fundamental constraint violation

## Implementation Details

### Rule Definition Schema

```python
@dataclass
class ValidationRule:
    """Base validation rule structure"""
    id: str                              # Unique rule identifier
    name: str                            # Human-readable name
    category: RuleCategory               # Constitution|Architecture|Documentation|Process|Quality
    severity: Severity                   # Critical|High|Medium|Low

    # Rule logic
    condition: str                       # Expression or query to evaluate
    validator: Callable                  # Python function for complex logic

    # Configuration
    enabled: bool = True
    escalate_on_violation: bool = False
    allow_override: bool = False
    override_requires: List[str] = []    # Required approvals for override

    # Metadata
    description: str
    rationale: str                      # Why this rule exists
    examples: List[Example]
    remediation: str                    # How to fix violations
```

### Constitution Rules (Inviolable)

```python
CONSTITUTION_RULES = [
    ValidationRule(
        id="CONST-001",
        name="Immutable Audit Trail",
        category=RuleCategory.CONSTITUTION,
        severity=Severity.CRITICAL,
        condition="""
            No DELETE operations on:
            - AgentRequest nodes
            - Decision nodes
            - Audit relationships
        """,
        allow_override=False,
        description="Audit trail must never be modified or deleted"
    ),

    ValidationRule(
        id="CONST-002",
        name="Specification Hierarchy",
        category=RuleCategory.CONSTITUTION,
        severity=Severity.CRITICAL,
        condition="""
            Architecture -> Design -> Code
            Never: Code -> Architecture
        """,
        description="Lower levels cannot define higher level specs"
    ),

    ValidationRule(
        id="CONST-003",
        name="Version Immutability",
        category=RuleCategory.CONSTITUTION,
        severity=Severity.CRITICAL,
        condition="""
            Published versions cannot be modified.
            Changes require new version with SUPERSEDES relationship.
        """,
        description="Published specifications are immutable"
    )
]
```

### Architecture Validation Rules

```python
class ArchitectureValidator:
    """Validates architectural compliance"""

    def validate_design_implements_architecture(self, design: Design) -> ValidationResult:
        """Ensure design properly implements architecture"""

        # Check that design references valid architecture
        query = """
            MATCH (d:Design {id: $design_id})
            MATCH (a:Architecture {id: $arch_id})
            WHERE a.status = 'approved'
            RETURN a
        """

        arch = self.graph.query(query, {
            "design_id": design.id,
            "arch_id": design.implements
        })

        if not arch:
            return ValidationResult(
                passed=False,
                rule="ARCH-001",
                message="Design must implement approved architecture",
                severity=Severity.HIGH
            )

        # Check version compatibility
        if not self._versions_compatible(design.version, arch.version):
            return ValidationResult(
                passed=False,
                rule="ARCH-002",
                message="Design version incompatible with architecture",
                severity=Severity.MEDIUM
            )

        return ValidationResult(passed=True)

    def validate_no_circular_dependencies(self, node_id: str) -> ValidationResult:
        """Check for circular dependency chains"""

        query = """
            MATCH path=(n {id: $node_id})-[:DEPENDS_ON|:IMPLEMENTS|:DERIVED_FROM*]->(n)
            RETURN path
        """

        circular = self.graph.query(query, {"node_id": node_id})

        if circular:
            return ValidationResult(
                passed=False,
                rule="ARCH-003",
                message="Circular dependency detected",
                severity=Severity.CRITICAL,
                details={"path": circular[0]}
            )

        return ValidationResult(passed=True)
```

### Document Validation Rules

```python
class DocumentValidator:
    """Validates document structure and content"""

    REQUIRED_FRONTMATTER = {
        "architecture": ["doc", "subsystem", "id", "version", "status", "owners"],
        "design": ["doc", "component", "id", "version", "status", "owners"],
        "tasks": ["doc", "sprint", "status", "assignee"]
    }

    def validate_frontmatter(self, doc_type: str, frontmatter: Dict) -> ValidationResult:
        """Validate document has required frontmatter"""

        required = self.REQUIRED_FRONTMATTER.get(doc_type, [])
        missing = [field for field in required if field not in frontmatter]

        if missing:
            return ValidationResult(
                passed=False,
                rule="DOC-001",
                message=f"Missing required frontmatter fields: {missing}",
                severity=Severity.MEDIUM,
                remediation="Add missing fields to document frontmatter"
            )

        # Validate field formats
        if not self._valid_version(frontmatter.get("version")):
            return ValidationResult(
                passed=False,
                rule="DOC-002",
                message="Version must use semantic versioning (x.y.z)",
                severity=Severity.LOW
            )

        return ValidationResult(passed=True)

    def validate_document_location(self, doc_type: str, path: str) -> ValidationResult:
        """Ensure document is in correct location"""

        EXPECTED_PATHS = {
            "architecture": r"docs/architecture/.*\.md",
            "design": r"docs/design/.*\.md",
            "tasks": r"docs/tasks/.*\.md"
        }

        pattern = EXPECTED_PATHS.get(doc_type)
        if pattern and not re.match(pattern, path):
            return ValidationResult(
                passed=False,
                rule="DOC-003",
                message=f"Document type '{doc_type}' must be in {pattern}",
                severity=Severity.MEDIUM,
                remediation=f"Move document to correct directory"
            )

        return ValidationResult(passed=True)
```

### Drift Detection Engine

```python
class DriftDetector:
    """Detects specification drift"""

    def detect_all_drift(self) -> List[DriftViolation]:
        """Run all drift detection queries"""

        violations = []
        violations.extend(self.detect_design_drift())
        violations.extend(self.detect_uncovered_requirements())
        violations.extend(self.detect_undocumented_code())
        violations.extend(self.detect_version_mismatches())

        return violations

    def detect_design_drift(self) -> List[DriftViolation]:
        """Find designs ahead of architecture"""

        query = """
            MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
            WHERE d.modified_at > a.modified_at
              AND NOT exists((:Decision)-[:APPROVES]->(:AgentRequest)-[:TARGETS]->(d))
            RETURN d.id as design_id,
                   a.id as arch_id,
                   d.modified_at as design_modified,
                   a.modified_at as arch_modified
        """

        results = self.graph.query(query)

        return [
            DriftViolation(
                type="design_ahead_of_architecture",
                severity=Severity.HIGH,
                source=r["design_id"],
                target=r["arch_id"],
                description=f"Design modified after architecture without approval",
                time_delta=r["design_modified"] - r["arch_modified"]
            )
            for r in results
        ]

    def detect_uncovered_requirements(self) -> List[DriftViolation]:
        """Find requirements with no implementation"""

        query = """
            MATCH (r:Requirement {status: 'active'})
            WHERE NOT exists((r)<-[:SATISFIES]-())
            RETURN r.rid as req_id,
                   r.priority as priority,
                   r.text as text
        """

        results = self.graph.query(query)

        return [
            DriftViolation(
                type="uncovered_requirement",
                severity=Severity.HIGH if r["priority"] == "high" else Severity.MEDIUM,
                source=r["req_id"],
                description=f"Requirement not satisfied: {r['text'][:100]}..."
            )
            for r in results
        ]
```

### Escalation Engine

```python
class EscalationEngine:
    """Determines when human intervention is required"""

    ESCALATION_TRIGGERS = [
        # Critical violations always escalate
        lambda v: v.severity == Severity.CRITICAL,

        # Multiple high severity violations
        lambda violations: len([v for v in violations if v.severity == Severity.HIGH]) > 3,

        # Constitution rule violations
        lambda v: v.rule_category == RuleCategory.CONSTITUTION,

        # Conflicts between approved specifications
        lambda v: v.type == "specification_conflict",

        # Agent requesting override
        lambda request: request.override_requested and not request.agent_can_override,

        # Uncertainty in decision
        lambda result: result.confidence < 0.7
    ]

    def should_escalate(self, validation_result: ValidationResult,
                       request: AgentRequest) -> EscalationDecision:
        """Determine if request should be escalated"""

        violations = validation_result.violations

        for trigger in self.ESCALATION_TRIGGERS:
            if any(trigger(v) for v in violations):
                return EscalationDecision(
                    escalate=True,
                    reason=self._get_escalation_reason(violations),
                    suggested_reviewers=self._get_reviewers(request),
                    priority=self._calculate_priority(violations)
                )

        return EscalationDecision(escalate=False)

    def create_escalation(self, request: AgentRequest,
                         decision: EscalationDecision) -> str:
        """Create escalation record"""

        escalation_id = f"ESC-{uuid.uuid4().hex[:8]}"

        # Create escalation node in graph
        query = """
            CREATE (e:Escalation {
                id: $id,
                request_id: $request_id,
                created_at: datetime(),
                reason: $reason,
                priority: $priority,
                reviewers: $reviewers,
                status: 'pending'
            })
            WITH e
            MATCH (r:AgentRequest {id: $request_id})
            CREATE (e)-[:ESCALATES]->(r)
            RETURN e.id
        """

        self.graph.query(query, {
            "id": escalation_id,
            "request_id": request.id,
            "reason": decision.reason,
            "priority": decision.priority,
            "reviewers": decision.suggested_reviewers
        })

        # Notify reviewers (webhook, email, etc)
        self._notify_reviewers(escalation_id, decision.suggested_reviewers)

        return escalation_id
```

## Interfaces

### Validation Pipeline

```python
class ValidationPipeline:
    """Main validation orchestrator"""

    def __init__(self):
        self.validators = [
            SyntaxValidator(),
            DocumentValidator(),
            ArchitectureValidator(),
            DriftDetector(),
            ComplianceValidator()
        ]
        self.escalation_engine = EscalationEngine()

    async def validate_request(self, request: AgentRequest) -> ValidationResponse:
        """Run full validation pipeline"""

        start_time = time.time()
        violations = []

        # Run all validators
        for validator in self.validators:
            result = await validator.validate(request)
            if not result.passed:
                violations.extend(result.violations)

        # Check escalation
        if violations:
            escalation = self.escalation_engine.should_escalate(
                ValidationResult(violations=violations),
                request
            )

            if escalation.escalate:
                escalation_id = self.escalation_engine.create_escalation(
                    request, escalation
                )
                return ValidationResponse(
                    status="escalated",
                    escalation_id=escalation_id,
                    reason=escalation.reason,
                    processing_time=time.time() - start_time
                )

        # Determine final status
        if not violations:
            status = "approved"
        elif any(v.severity == Severity.CRITICAL for v in violations):
            status = "rejected"
        else:
            status = "revision_required"

        return ValidationResponse(
            status=status,
            violations=violations,
            suggestions=self._generate_suggestions(violations),
            processing_time=time.time() - start_time
        )
```

### REST API Endpoints

```yaml
/validation/check:
  method: POST
  description: Validate a proposed change
  body: ValidationRequest
  response: ValidationResponse

/validation/drift:
  method: GET
  description: Get current drift violations
  params:
    subsystem: optional string
    severity: optional string
  response: List[DriftViolation]

/validation/rules:
  method: GET
  description: Get all validation rules
  params:
    category: optional string
    enabled: optional boolean
  response: List[ValidationRule]

/validation/escalations:
  method: GET
  description: Get pending escalations
  params:
    status: pending|resolved|all
  response: List[Escalation]
```

## Configuration

### Rule Configuration
```yaml
# config/validation-rules.yaml
rules:
  constitution:
    enabled: true
    allow_override: false

  architecture:
    enabled: true
    version_compatibility:
      mode: strict  # strict|flexible|loose
      allow_major_mismatch: false

  documentation:
    enabled: true
    required_sections:
      - overview
      - implementation
      - interfaces
      - testing

  quality:
    enabled: true
    thresholds:
      min_test_coverage: 80
      max_complexity: 10
      max_file_size: 1000  # lines

escalation:
  triggers:
    critical_violations: true
    multiple_high: 3
    confidence_threshold: 0.7

  notification:
    webhook_url: ${ESCALATION_WEBHOOK}
    email_enabled: false
    slack_channel: "#librarian-escalations"
```

### Drift Detection Configuration
```yaml
# config/drift-detection.yaml
drift:
  scan_interval: 300  # seconds

  thresholds:
    design_drift_hours: 24
    requirement_coverage_days: 7
    code_documentation_lag_days: 3

  severity_mapping:
    design_ahead: high
    uncovered_requirement_high_priority: critical
    uncovered_requirement_medium_priority: medium
    undocumented_code: low
```

## Common Operations

### 1. Validating Agent Request
```python
async def handle_agent_request(request: AgentRequest):
    """Full validation flow for agent request"""

    # Run validation pipeline
    validation_result = await validation_pipeline.validate_request(request)

    # Handle result based on status
    if validation_result.status == "approved":
        # Proceed with change
        await apply_change(request)

    elif validation_result.status == "revision_required":
        # Return violations and suggestions
        return {
            "status": "revision_required",
            "violations": validation_result.violations,
            "suggestions": validation_result.suggestions
        }

    elif validation_result.status == "escalated":
        # Notify agent of escalation
        return {
            "status": "escalated",
            "escalation_id": validation_result.escalation_id,
            "estimated_review_time": "24 hours"
        }

    else:  # rejected
        # Log rejection and notify
        await log_rejection(request, validation_result)
        return {
            "status": "rejected",
            "reason": validation_result.violations[0].description
        }
```

### 2. Running Drift Detection
```python
async def scheduled_drift_scan():
    """Periodic drift detection"""

    detector = DriftDetector()
    violations = detector.detect_all_drift()

    # Group by severity
    critical = [v for v in violations if v.severity == Severity.CRITICAL]
    high = [v for v in violations if v.severity == Severity.HIGH]

    # Handle critical violations
    if critical:
        await create_urgent_tasks(critical)
        await notify_owners(critical)

    # Log all violations
    await store_drift_report(violations)

    # Update metrics
    metrics.record_drift_count(len(violations))
    metrics.record_drift_by_type(violations)
```

### 3. Updating Validation Rules
```python
def update_rule(rule_id: str, updates: Dict):
    """Update validation rule configuration"""

    # Load current rule
    rule = load_rule(rule_id)

    # Validate updates
    if "severity" in updates and updates["severity"] == "LOW":
        if rule.category == RuleCategory.CONSTITUTION:
            raise ValueError("Cannot lower constitution rule severity")

    # Apply updates
    rule.update(updates)

    # Save and reload
    save_rule(rule)
    validation_pipeline.reload_rules()

    # Log change
    audit_log.record_rule_change(rule_id, updates)
```

## Troubleshooting

### Common Issues

#### "Validation timeout"
- **Cause**: Complex graph queries taking too long
- **Solution**: Add indexes, optimize queries, increase timeout
```python
# Add timeout to validator
@timeout(30)  # seconds
def validate_complex_rule(request):
    # validation logic
```

#### "Inconsistent validation results"
- **Cause**: Race condition in concurrent validations
- **Solution**: Add locking for critical sections
```python
with validation_lock:
    result = await validate_request(request)
```

#### "Escalation not triggering"
- **Cause**: Incorrect trigger configuration
- **Solution**: Check escalation rules and thresholds
```python
# Debug escalation decision
decision = escalation_engine.should_escalate(result, request, debug=True)
print(decision.debug_info)
```

#### "False positive violations"
- **Cause**: Overly strict rules or incorrect patterns
- **Solution**: Review and tune rule conditions
```python
# Test rule in isolation
rule = load_rule("DOC-003")
test_cases = load_test_cases()
for case in test_cases:
    result = rule.validate(case)
    print(f"{case.name}: {result.passed}")
```

### Performance Monitoring

```python
# Validation metrics
metrics = validation_pipeline.get_metrics()
print(f"Avg validation time: {metrics.avg_time_ms}ms")
print(f"Rules executed: {metrics.rules_executed}")
print(f"Cache hit rate: {metrics.cache_hit_rate}%")

# Rule performance
for rule_id, stats in metrics.rule_stats.items():
    if stats.avg_time_ms > 100:
        print(f"Slow rule: {rule_id} - {stats.avg_time_ms}ms")
```

## References

- **Architecture Document**: [`docs/architecture.md`](../architecture.md)
- **Validation Rules Schema**: [`src/models/validation.py`](../../src/models/validation.py)
- **Graph Operations**: [`docs/subdomains/graph-operations.md`](./graph-operations.md)
- **Agent Protocol**: [`docs/subdomains/agent-protocol.md`](./agent-protocol.md)
- **Rule Templates**: [`templates/validation-rules/`](../../templates/validation-rules/)