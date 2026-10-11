# Review Agent 2: Integration Points Reviewer

## Your Mission
Review how the three modules will work together. Check interfaces, data flow, and identify integration gaps or incompatibilities.

## Integration Points to Review

### 1. Graph ↔ Processing Integration
Check how embeddings flow from processing to graph storage:

**Processing produces:**
- `ProcessedChunk` with 768-dim embedding
- `ParsedDocument` with metadata

**Graph expects:**
- `store_embedding(node_id, embedding)`
- Node creation with properties

**Verify:**
- Data structures are compatible
- Embedding dimensions match (768)
- Document → Node mapping is clear
- Chunk → Node + embedding storage works

### 2. Validation ↔ Graph Integration
Check how validation queries the graph:

**Validation needs:**
- Query existing architecture/design nodes
- Check for drift
- Store audit records

**Graph provides:**
- `query()` method for Cypher
- Node CRUD operations
- Drift detection queries

**Verify:**
- Validation can access graph queries
- Drift detector can use graph operations
- Audit logger can create nodes
- Context gathering works

### 3. Processing ↔ Validation Integration
Check how parsed documents are validated:

**Processing produces:**
- ParsedDocument with frontmatter
- Document metadata

**Validation expects:**
- AgentRequest with content
- Context with specs

**Verify:**
- ParsedDocument can become AgentRequest
- Frontmatter validation works
- Document type detection aligns

### 4. Complete Data Flow
Trace the full flow:
1. Document ingested (Processing)
2. Embeddings generated (Processing)
3. Stored in graph (Graph)
4. Agent makes request (Validation)
5. Validation queries graph (Graph)
6. Decision logged (Graph via Validation)

## Review Output Format

Create `reviews/integration_review.md` with:

```markdown
# Integration Points Review

## Summary
[Overall integration readiness]

## Interface Compatibility

### Graph ↔ Processing
- Status: [Ready/Needs Work]
- Issues: [list]
- Required Changes: [list]

### Validation ↔ Graph
- Status: [Ready/Needs Work]
- Issues: [list]
- Required Changes: [list]

### Processing ↔ Validation
- Status: [Ready/Needs Work]
- Issues: [list]
- Required Changes: [list]

## Data Flow Analysis
[Trace complete flow with any breaks]

## Missing Glue Code
[List integration code that needs to be written]

## Recommended Integration Order
1. [First integration]
2. [Second integration]
3. [etc.]

## Risk Assessment
- High Risk: [list]
- Medium Risk: [list]
- Low Risk: [list]
```

Focus on finding integration gaps that would prevent the modules from working together.