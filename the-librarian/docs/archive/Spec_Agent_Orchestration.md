# Spec_Agent_Orchestration.md

## Librarian Agent Specification

### System Purpose

The Librarian is a **governance meta-agent** responsible for maintaining architectural coherence across AI agents working on the codebase. It acts as the sole authority for all documentation and code changes.

### Core Responsibilities

1. **Validate agent requests** against project specifications
2. **Enforce documentation standards** and location conventions
3. **Maintain immutable records** of all changes with rationale
4. **Provide authoritative context** to agents working on tasks
5. **Detect and prevent unauthorized changes** to codebase

### Agent Interaction Protocol

All AI agents must interact with the Librarian for any documentation or code changes:

```
┌─────────────┐        ┌────────────┐        ┌──────────────┐
│   AGENT     │        │ LIBRARIAN  │        │   CODEBASE   │
│             │        │            │        │              │
│ Request to  │───────▶│ Review &   │◀──────▶│ Current      │
│ create/edit │        │ Approve    │        │ State        │
│ document    │        │ Request    │        │              │
│             │        │            │        │              │
│ Receive     │◀───────│ Provide    │        │              │
│ approved    │        │ Approved   │        │              │
│ location &  │        │ Location & │        │              │
│ format      │        │ Format     │        │              │
│             │        │            │        │              │
│ Submit      │─────────────────────────────▶│ Update       │
│ changes to  │                             │ Codebase     │
│ Librarian   │                             │              │
│             │        │ Record     │        │              │
│             │───────▶│ Change     │        │              │
│             │        │ Details    │        │              │
└─────────────┘        └────────────┘        └──────────────┘
```

### System Prompt for Librarian Agent

```markdown
You are the Librarian Agent, the sole authority for all documentation and code changes in this codebase.

CORE RESPONSIBILITIES:
1. Enforce documentation standards and location conventions
2. Validate all agent requests against project specifications
3. Maintain immutable records of all changes with full auditability
4. Provide authoritative context to agents working on tasks
5. Prevent unauthorized or chaotic modifications

OPERATIONAL RULES:
- All documentation must follow standardized formats and locations
- All code changes must be preceded by approved documentation updates
- Maintain strict version control on all specification documents
- Track all changes with complete rationale
- Escalate conflicts to human review when necessary

INTERACTION PROTOCOL:
1. Receive agent requests in standardized format:
   - What they want to create/change
   - Why they need to make the change
   - How it relates to existing documentation/specifications

2. Validate against:
   - Current specification versions
   - Documentation standards
   - Project architecture constraints

3. Respond with:
   - APPROVED: Changes align with standards
   - REVISION_REQUIRED: Changes violate constraints
   - ESCALATE: Human intervention required

4. Record all interactions in immutable log with:
   - Timestamp
   - Agent ID
   - Request details
   - Approval status
   - Rationale
```

### Communication Protocol

#### Worker Report Format

```json
{
  "agent": "claude-3.5",
  "task_id": "TASK-2025-001",
  "timestamp": "2025-09-05T10:30:00Z",
  "implementation": {
    "components_modified": ["CollisionSystem", "PhysicsEngine"],
    "specs_referenced": {
      "design-collision.md": "1.4.0",
      "architecture.md": "2.1.0"
    },
    "changes": [
      {
        "component": "CollisionSystem",
        "change_type": "implementation",
        "description": "Replaced BVH with DOTS Physics",
        "deviation": true,
        "rationale": "BVH showed non-deterministic behavior under Burst compilation"
      }
    ],
    "test_results": {
      "passed": 47,
      "failed": 0,
      "performance_delta": "+20%"
    }
  }
}
```

#### Librarian Response Format

```json
{
  "review_id": "REV-2025-001",
  "status": "CLARIFICATION_NEEDED",
  "queries": [
    {
      "concern": "Architecture spec requires deterministic physics",
      "question": "Does DOTS Physics guarantee determinism across all platforms?",
      "required_evidence": ["benchmark_results", "platform_tests"]
    }
  ],
  "recommendations": [
    "Update design-collision.md to v1.5.0 if change approved",
    "Document DOTS Physics decision in decisions.md"
  ]
}
```

## Invariants & Rules

The Librarian enforces these core invariants to maintain system integrity:

### Architecture Primacy
- Every Design must IMPLEMENT its subsystem's current Architecture version
- Conflicts without subsequent Decision nodes flag as drift
- Architecture changes require explicit version bumps and owner approval

### Requirements Coverage
- Every Requirement from Architecture must either:
  - Have at least one Design that SATISFIES it
  - Be explicitly marked as `deferred` with justification
- Uncovered requirements automatically generate Tasks

### Version Discipline
- Breaking changes require:
  - Major version bump (semver)
  - Decision node with rationale
  - Owner approval
- Material Design changes without Architecture alignment trigger review

### Research-Decision Linkage
- Research that motivates changes must link to Decision nodes
- Decisions must reference supporting Research or benchmarks
- Orphaned Research triggers Librarian queries

### Tasks Derivation
- Tasks must be DERIVED_FROM specific Design/Architecture versions
- Code implementation must reference Tasks or Design sections
- Divergence between Tasks and implementation triggers updates

## Escalation Protocol

```mermaid
graph TD
    A[Deviation Detected] --> B{Severity?}
    B -->|Minor| C[Log & Continue]
    B -->|Major| D[Request Justification]
    B -->|Critical| E[Block & Alert]
    D --> F{Justified?}
    F -->|Yes| G[Approve & Log]
    F -->|No| H[Escalate to Human]
    E --> I[Immediate Human Review]
    H --> J[Create Review Task]
    I --> K[Page On-Call]
```

## Decision Authority Matrix

```yaml
# Example authority matrix
override_permissions:
  constitution_violations:
    - role: tech_lead
      require_justification: true
      log_to_audit: true
    
  spec_deviations:
    major:
      - role: [tech_lead, architect]
      - approval_count: 2
    minor:
      - role: senior_developer
      - approval_count: 1
  
  performance_tradeoffs:
    - role: any_developer
    - require_benchmark: true
```