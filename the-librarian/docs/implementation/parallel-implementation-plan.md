# Parallel Implementation Plan

## Overview
This document defines how to parallelize the Librarian Agent implementation using multiple Claude instances working concurrently, with automated coordination and review phases.

## Work Division Heuristic

### Heuristic for Parallel Task Division

```markdown
PROMPT FOR SUB-AGENT ANALYSIS:
You are analyzing a codebase architecture to determine optimal parallel work division.

Given a system with:
1. Multiple modules/subdomains
2. Dependencies between modules
3. Multiple Claude instances available for parallel work

Apply this heuristic to recommend work division:

STEP 1: Identify Dependency Layers
- Layer 0: No dependencies (pure interfaces, data models, schemas)
- Layer 1: Depends only on Layer 0 (basic operations)
- Layer 2: Depends on Layer 0-1 (business logic)
- Layer 3: Depends on Layer 0-2 (API/integration)
- Layer 4: Tests and documentation

STEP 2: Identify Coupling Metrics
For each module pair, score coupling (0-10):
- Shared data structures: +3
- Function calls between: +3
- Shared configuration: +2
- Shared validation rules: +2

Modules with coupling score >5 should be assigned to SAME Claude.

STEP 3: Estimate Complexity
For each module, estimate hours needed:
- Simple (1-2 hrs): Basic CRUD, simple logic
- Medium (3-4 hrs): Complex logic, multiple integrations
- Complex (5+ hrs): Core algorithms, critical paths

STEP 4: Apply Parallelization Rules
- Rule 1: All Layer 0 work can be fully parallel
- Rule 2: Within same layer, low-coupled (<3) modules can be parallel
- Rule 3: High-coupled (>5) modules must be same Claude
- Rule 4: Balance complexity across Claudes (equal total hours)
- Rule 5: Assign related tests to same Claude as implementation

STEP 5: Output Recommendation
Recommend specific Claude assignments with reasoning.
```

## Proposed Work Division for Librarian Agent

### Analysis Results

#### Layer 0: Foundation (Fully Parallel)
**Can be done by 3 Claudes simultaneously:**

**Claude-1: Data Models & Schemas**
```
src/models/
├── base.py           # Base classes, enums
├── documents.py      # Document, Chunk, ParsedDocument
├── agents.py         # AgentRequest, AgentResponse, Decision
└── graph_schema.py   # Node and relationship definitions

src/schema/
├── neo4j_init.cypher # Graph constraints and indexes
└── vector_indexes.cypher
```

**Claude-2: Configuration & Interfaces**
```
src/config/
├── settings.py       # Pydantic settings management
└── constants.py      # System constants

src/interfaces/
├── storage.py        # Abstract storage interface
├── embedder.py       # Abstract embedder interface
├── validator.py      # Abstract validator interface
└── agent.py          # Agent communication protocol
```

**Claude-3: Utilities & Helpers**
```
src/utils/
├── logging_config.py # Logging setup
├── exceptions.py     # Custom exceptions
├── hash_utils.py     # Content hashing
└── time_utils.py     # Timestamp handling
```

#### Layer 1: Core Operations (Partially Parallel)
**Can be done by 2 Claudes with coordination:**

**Claude-4: Graph & Storage Operations**
```
src/graph/
├── connection.py     # Neo4j connection manager
├── operations.py     # Graph CRUD operations
├── vector_ops.py     # Vector index operations
└── queries.py        # Cypher query templates

src/storage/
├── document_store.py # Document storage implementation
└── audit_store.py    # Audit log storage
```

**Claude-5: Processing & Validation**
```
src/processing/
├── parser.py         # Document parsing
├── chunker.py        # Text chunking
└── embedder.py       # Embedding generation

src/validation/
├── rules.py          # Validation rule definitions
├── engine.py         # Validation engine
└── drift_detector.py # Drift detection logic
```

#### Layer 2: Business Logic (Sequential or Coupled)
**Single Claude or tightly coordinated:**

**Claude-6: Agent Orchestration**
```
src/agents/
├── coordinator.py    # Agent request coordinator
├── context.py        # Context assembly
├── approval.py       # Approval logic
└── governance.py     # Governance rules
```

#### Layer 3: API Layer
**After Layer 0-2 complete:**

**Claude-7: FastAPI Implementation**
```
src/api/
├── main.py          # FastAPI app
├── endpoints/
│   ├── agent.py     # Agent endpoints
│   ├── query.py     # Query endpoints
│   ├── validation.py # Validation endpoints
│   └── admin.py     # Admin endpoints
├── dependencies.py  # Dependency injection
└── middleware.py    # Custom middleware
```

#### Layer 4: Tests (Parallel with Implementation)
**Each Claude writes tests for their own modules**

---

## Shared Coordination File

### `coordination.json` Structure

```json
{
  "meta": {
    "started_at": "2024-11-10T10:00:00Z",
    "last_updated": "2024-11-10T10:00:00Z",
    "phase": "layer_0"
  },

  "agents": {
    "claude-1": {
      "task": "Data Models & Schemas",
      "status": "working",
      "started_at": "2024-11-10T10:00:00Z",
      "last_heartbeat": "2024-11-10T10:05:00Z",
      "outputs": []
    }
  },

  "interfaces": {
    "DocumentModel": {
      "status": "defined",
      "location": "src/models/documents.py",
      "signature": "class Document(BaseModel): ...",
      "defined_by": "claude-1",
      "timestamp": "2024-11-10T10:15:00Z"
    }
  },

  "dependencies": {
    "graph_operations": {
      "depends_on": ["DocumentModel", "neo4j_schema"],
      "status": "blocked",
      "waiting_for": ["DocumentModel"]
    }
  },

  "conflicts": {
    "naming_conflict_1": {
      "type": "duplicate_function",
      "agents": ["claude-1", "claude-3"],
      "details": "Both defined 'parse_document'",
      "resolution": "pending"
    }
  },

  "checkpoints": {
    "layer_0_complete": false,
    "layer_1_complete": false,
    "integration_ready": false,
    "tests_passing": false
  }
}
```

---

## Orchestration Scripts

### Master Orchestrator: `orchestrate.sh`

```bash
#!/bin/bash
# orchestrate.sh - Master parallel implementation orchestrator

set -e

PROJECT_ROOT="$(pwd)"
COORDINATION_FILE="$PROJECT_ROOT/coordination.json"
TASKS_DIR="$PROJECT_ROOT/tasks"
LOGS_DIR="$PROJECT_ROOT/logs/parallel"

# Initialize coordination file
init_coordination() {
    cat > "$COORDINATION_FILE" <<EOF
{
  "meta": {
    "started_at": "$(date -Iseconds)",
    "phase": "layer_0"
  },
  "agents": {},
  "interfaces": {},
  "dependencies": {},
  "conflicts": {},
  "checkpoints": {}
}
EOF
}

# Launch parallel Claude instances for Layer 0
launch_layer_0() {
    echo "=== Launching Layer 0 (Parallel Foundation) ==="

    # Claude-1: Data Models
    claude chat --continue false \
        --chat-context "$TASKS_DIR/layer0/task_models.md" \
        > "$LOGS_DIR/claude-1.log" 2>&1 &
    PIDS[1]=$!

    # Claude-2: Configuration & Interfaces
    claude chat --continue false \
        --chat-context "$TASKS_DIR/layer0/task_interfaces.md" \
        > "$LOGS_DIR/claude-2.log" 2>&1 &
    PIDS[2]=$!

    # Claude-3: Utilities
    claude chat --continue false \
        --chat-context "$TASKS_DIR/layer0/task_utils.md" \
        > "$LOGS_DIR/claude-3.log" 2>&1 &
    PIDS[3]=$!

    # Wait for all Layer 0 tasks
    for pid in ${PIDS[@]}; do
        wait $pid
    done

    echo "Layer 0 complete!"
}

# Launch Layer 1 with dependency checking
launch_layer_1() {
    echo "=== Launching Layer 1 (Core Operations) ==="

    # Update coordination file
    jq '.meta.phase = "layer_1"' "$COORDINATION_FILE" > tmp.json
    mv tmp.json "$COORDINATION_FILE"

    # Claude-4: Graph Operations
    claude chat --continue false \
        --chat-context "$TASKS_DIR/layer1/task_graph.md" \
        > "$LOGS_DIR/claude-4.log" 2>&1 &
    PIDS[4]=$!

    # Claude-5: Processing & Validation
    claude chat --continue false \
        --chat-context "$TASKS_DIR/layer1/task_processing.md" \
        > "$LOGS_DIR/claude-5.log" 2>&1 &
    PIDS[5]=$!

    # Wait for Layer 1
    wait ${PIDS[4]}
    wait ${PIDS[5]}

    echo "Layer 1 complete!"
}

# Review phase
launch_review() {
    echo "=== Launching Review Phase ==="

    # Reviewer-1: Architecture compliance
    claude chat --continue false \
        --chat-context "$TASKS_DIR/review/review_architecture.md" \
        > "$LOGS_DIR/review-1.log" 2>&1 &

    # Reviewer-2: Code quality
    claude chat --continue false \
        --chat-context "$TASKS_DIR/review/review_quality.md" \
        > "$LOGS_DIR/review-2.log" 2>&1 &

    wait

    echo "Review complete!"
}

# Main execution
main() {
    mkdir -p "$LOGS_DIR"
    init_coordination

    launch_layer_0
    launch_layer_1
    # launch_layer_2  # Add more layers

    launch_review

    echo "=== Parallel Implementation Complete ==="
    echo "Check logs in: $LOGS_DIR"
    echo "Coordination status: $COORDINATION_FILE"
}

main "$@"
```

### Individual Task File Example: `tasks/layer0/task_models.md`

```markdown
# Task: Implement Data Models and Schemas

You are Claude-1, responsible for implementing the data models layer.

## Your Assignment
Create all data models and database schemas for the Librarian Agent system.

## Coordination Protocol
1. Read `coordination.json` at start
2. Update your status every 5 minutes
3. When you define a public interface, add it to `interfaces` section
4. Mark your status as "complete" when done

## Files to Create
- `src/models/base.py` - Base classes and enums
- `src/models/documents.py` - Document, Chunk, ParsedDocument
- `src/models/agents.py` - AgentRequest, AgentResponse, Decision
- `src/models/graph_schema.py` - Node and relationship definitions
- `src/schema/neo4j_init.cypher` - Database initialization
- `src/schema/vector_indexes.cypher` - Vector index creation

## Dependencies
You have no dependencies. Other agents depend on your interfaces.

## Interface Registration
When you create a public class/function, register it:
```python
# After creating Document class, update coordination.json:
"interfaces": {
  "Document": {
    "status": "defined",
    "location": "src/models/documents.py",
    "signature": "class Document(BaseModel): path: str, content: str, ...",
    "defined_by": "claude-1"
  }
}
```

## Completion Criteria
- All model files created
- All interfaces registered in coordination.json
- Basic docstrings and type hints
- Your status marked "complete"

## Start Instruction
Begin by reading the architecture document at `docs/architecture.md` and the data model specification at `docs/subdomains/document-processing.md`. Then implement the models according to the specification.
```

### Dependency Checking Script: `check_dependencies.py`

```python
#!/usr/bin/env python3
# check_dependencies.py - Check if dependencies are met

import json
import time
import sys
from pathlib import Path

def check_dependencies(agent_id, required_deps):
    """Check if all required dependencies are available"""

    coord_file = Path("coordination.json")
    max_wait = 3600  # 1 hour max wait
    check_interval = 60  # Check every minute
    elapsed = 0

    while elapsed < max_wait:
        with open(coord_file) as f:
            coord = json.load(f)

        interfaces = coord.get("interfaces", {})

        # Check each required dependency
        missing = []
        for dep in required_deps:
            if dep not in interfaces or interfaces[dep]["status"] != "defined":
                missing.append(dep)

        if not missing:
            print(f"All dependencies met for {agent_id}")
            return True

        print(f"{agent_id} waiting for: {missing}")
        time.sleep(check_interval)
        elapsed += check_interval

    print(f"Timeout waiting for dependencies: {missing}")
    return False

if __name__ == "__main__":
    agent_id = sys.argv[1]
    deps = sys.argv[2].split(",") if len(sys.argv) > 2 else []

    if check_dependencies(agent_id, deps):
        sys.exit(0)
    else:
        sys.exit(1)
```

---

## Review and Debate Automation

### Review Orchestrator: `review.sh`

```bash
#!/bin/bash
# review.sh - Automated review and debate phase

# Phase 1: Individual Reviews
echo "=== Starting Individual Reviews ==="

# Architecture Reviewer
claude chat --continue false \
    --context "Review the implementation for architecture compliance" \
    --context "Read all files in src/ and compare against docs/architecture.md" \
    > logs/review_architecture.log &

# Quality Reviewer
claude chat --continue false \
    --context "Review code quality, patterns, and best practices" \
    --context "Check for: DRY, SOLID, error handling, type hints" \
    > logs/review_quality.log &

# Security Reviewer
claude chat --continue false \
    --context "Review for security vulnerabilities" \
    --context "Check for: injection risks, secret handling, validation" \
    > logs/review_security.log &

wait

# Phase 2: Debate Controversial Decisions
echo "=== Starting Debate Phase ==="

# Create debate context from reviews
python3 scripts/prepare_debate.py

# Debate moderator
claude chat --continue false \
    --context tasks/debate/moderate.md \
    --context "Conflicts found: $(cat conflicts.json)" \
    > logs/debate_resolution.log

# Phase 3: Final Integration
echo "=== Final Integration ==="

claude chat --continue false \
    --context "Integrate all changes based on review feedback" \
    --context "Review outputs: logs/review_*.log" \
    --context "Debate resolution: logs/debate_resolution.log" \
    > logs/final_integration.log
```

### Debate Context Generator: `prepare_debate.py`

```python
#!/usr/bin/env python3
# prepare_debate.py - Prepare debate topics from review conflicts

import json
import re
from pathlib import Path

def extract_conflicts():
    """Extract conflicting opinions from review logs"""

    conflicts = []
    review_logs = Path("logs").glob("review_*.log")

    for log_file in review_logs:
        content = log_file.read_text()

        # Look for criticism patterns
        criticism_patterns = [
            r"CONCERN: (.+)",
            r"ISSUE: (.+)",
            r"VIOLATION: (.+)",
            r"ALTERNATIVE: (.+)"
        ]

        for pattern in criticism_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                conflicts.append({
                    "reviewer": log_file.stem,
                    "type": pattern.split(":")[0],
                    "issue": match,
                    "file": log_file.name
                })

    # Group similar conflicts
    grouped = group_similar_conflicts(conflicts)

    with open("conflicts.json", "w") as f:
        json.dump(grouped, f, indent=2)

    return grouped

def group_similar_conflicts(conflicts):
    """Group similar conflicts for debate"""
    # Implementation to group by topic
    # ...
    return conflicts

if __name__ == "__main__":
    conflicts = extract_conflicts()
    print(f"Found {len(conflicts)} conflict topics for debate")
```

---

## Success Metrics

### Automated Success Validation

```python
#!/usr/bin/env python3
# validate_success.py - Check if parallel implementation succeeded

import subprocess
import json
from pathlib import Path

def validate_implementation():
    """Validate the parallel implementation succeeded"""

    checks = {
        "files_created": check_files_exist(),
        "tests_pass": run_tests(),
        "imports_work": check_imports(),
        "interfaces_match": check_interface_consistency(),
        "no_conflicts": check_merge_conflicts()
    }

    success = all(checks.values())

    report = {
        "success": success,
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }

    with open("validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    return success

def check_files_exist():
    """Verify all expected files were created"""
    expected = [
        "src/models/base.py",
        "src/models/documents.py",
        "src/graph/operations.py",
        "src/api/main.py",
        # ... full list
    ]

    return all(Path(f).exists() for f in expected)

def run_tests():
    """Run test suite"""
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/"],
        capture_output=True
    )
    return result.returncode == 0

# ... other validation functions

if __name__ == "__main__":
    if validate_implementation():
        print("✅ Implementation successful!")
    else:
        print("❌ Implementation has issues - check validation_report.json")
```

---

## Timeline

### Parallel Execution Timeline

```
Hour 0-2:   Layer 0 (3 Claudes parallel) - Models, Interfaces, Utils
Hour 2-4:   Layer 1 (2 Claudes parallel) - Graph Ops, Processing
Hour 4-5:   Layer 2 (1 Claude) - Agent Orchestration
Hour 5-6:   Layer 3 (1 Claude) - API Implementation
Hour 6-7:   Review Phase (3 Claudes parallel) - Architecture, Quality, Security
Hour 7-8:   Debate & Resolution (1 Claude moderator)
Hour 8:     Final Integration & Testing

Total: 8 hours vs 40+ hours sequential
```

---

## Conflict Resolution Protocol

### Naming Conflicts
```json
{
  "conflict_type": "naming",
  "resolution_rules": [
    "Prefer name from lower layer (foundation wins)",
    "If same layer, prefer more descriptive name",
    "Document aliases in deprecation notice"
  ]
}
```

### Interface Conflicts
```json
{
  "conflict_type": "interface",
  "resolution_rules": [
    "Most restrictive type wins (safety)",
    "Required fields override optional",
    "Document reasoning in ADR"
  ]
}
```

### Implementation Conflicts
```json
{
  "conflict_type": "implementation",
  "resolution_rules": [
    "Performance benchmarks decide",
    "Simpler solution preferred if performance equal",
    "Create A/B test if uncertain"
  ]
}
```