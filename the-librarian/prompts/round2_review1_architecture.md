# Review Agent 1: Architecture Compliance Reviewer

## Your Mission
Review all three modules built by Round 1 agents and verify they comply with the architecture specifications. Check for specification violations, missing features, and architectural drift.

## What to Review

### Module 1: Graph Operations (`src/graph/`)
Files to check:
- connection.py, operations.py, vector_ops.py, queries.py, schema.py, config.py

Compare against:
- `docs/architecture.md` lines 147-262 (Data Model)
- `docs/architecture.md` lines 469-501 (Validation Queries)
- `docs/subdomains/graph-operations.md`

Verify:
1. All node types from spec are implemented (Architecture, Design, Requirement, etc.)
2. All relationships are defined (IMPLEMENTS, SATISFIES, DEFINES, etc.)
3. Vector indexes are 768 dimensions with cosine similarity
4. All drift detection queries are present and correct
5. Async operations are properly implemented

### Module 2: Document Processing (`src/processing/`)
Files to check:
- parser.py, chunker.py, embedder.py, pipeline.py, models.py

Compare against:
- `docs/subdomains/document-processing.md`
- `docs/architecture.md` frontmatter requirements

Verify:
1. Parser handles YAML frontmatter correctly
2. Required fields validated based on doc_type
3. Chunking is 1000 tokens with 200 overlap
4. Embeddings are 768 dimensions via Ollama
5. Parent-child chunk relationships implemented

### Module 3: Validation Engine (`src/validation/`)
Files to check:
- rules.py, engine.py, drift_detector.py, audit.py, agent_models.py

Compare against:
- `docs/architecture.md` lines 399-423 (Validation Rules)
- `docs/subdomains/validation-engine.md`
- `docs/subdomains/audit-governance.md`

Verify:
1. All 5 validation rules implemented (DOC-001, VER-001, ARCH-001, REQ-001, CONST-001)
2. Escalation logic matches spec (critical → escalated)
3. Drift detection has all types from spec
4. Audit trail is immutable
5. Agent request/response models match API spec

## Review Output Format

Create `reviews/architecture_compliance_review.md` with:

```markdown
# Architecture Compliance Review

## Summary
[Overall compliance percentage and grade]

## Module Reviews

### Graph Operations
- Compliance: [X]%
- Missing Features: [list]
- Spec Violations: [list]
- Recommendations: [list]

### Document Processing
- Compliance: [X]%
- Missing Features: [list]
- Spec Violations: [list]
- Recommendations: [list]

### Validation Engine
- Compliance: [X]%
- Missing Features: [list]
- Spec Violations: [list]
- Recommendations: [list]

## Critical Issues
[List any MUST-FIX issues]

## Minor Issues
[List nice-to-have improvements]

## Overall Assessment
[PASS/FAIL with reasoning]
```

Be thorough and critical. Check actual implementation against specifications line by line.