# Spec_Data_Model.md

## Document Storage Strategy

### Directory Structure
```
project/
├── docs/
│   ├── constitution.md          # Project-wide constraints & guardrails
│   ├── decisions.md             # Versioned decision log
│   └── [subsystem]/
│       ├── architecture.md      # High-level requirements & strategic decisions
│       ├── design-[component].md # Detailed implementation specs
│       ├── tasks.md             # Generated task backlog
│       ├── research.md          # Performance analysis & tradeoffs
│       ├── data-model.md        # Domain models and schemas
│       ├── quickstart.md        # Getting started guides
│       └── contracts/
│           └── api-[name].json  # API contracts (OpenAPI, GraphQL, etc.)
```

### Document Front-Matter Contract

Every document must include standardized YAML front-matter for versioning, dependency tracking, and graph ingestion:

```yaml
---
# Document classification
doc: architecture | design | tasks | research | data-model | quickstart | api-contract | decision | changelog
subsystem: physics-system          # Umbrella area
id: physics-architecture          # Stable slug for references
component: [optional]             # Component within subsystem

# Versioning
version: 1.7.0                    # Semantic versioning
status: draft | review | approved | deprecated | superseded

# Ownership & review
owners: ["@username1", "@username2"]
last_reviewed: YYYY-MM-DD

# Dependencies & lineage
requires: ["physics-collision-design@>=1.4.0"]  # Dependencies by id@semver
supersedes: ["physics-architecture@1.6.x"]      # Document lineage

# Governance controls
compliance_level: strict | flexible | advisory
drift_tolerance: none | minor | moderate
---
```

Key aspects:
- **`id`** provides stable reference across renames
- **`requires`** enables dependency version constraints
- **`supersedes`** tracks document evolution
- **`compliance_level`** determines enforcement strictness
- **`drift_tolerance`** sets acceptable deviation bounds

## Graph Database Schema (Neo4j)

### Node Types
```cypher
// Document nodes
Subsystem {slug, name}
Architecture {id, path, version, status, owners[], last_reviewed}
Requirement {rid, text, priority, source}
Design {id, path, area, version, status, owners[], last_reviewed}
DataModel {id, path, version}
Quickstart {id, path, version}
ApiContract {id, path, version, format}
Research {id, path, version}
Tasks {id, path, version}
Decision {id, date, rationale, author, kind}
ChangeLog {id, path}

// Implementation nodes
CodeArtifact {path, lang, repo_rel_path}
Benchmark {scene, metric, value, unit, date}
Run {id, worker, started_at, finished_at, summary}
Person {handle}
PR {number, title, state}
```

### Relationships
```cypher
// Document hierarchy
(:Subsystem)<-[:OF_SUBSYSTEM]-(:Architecture)
(:Architecture)-[:DEFINES]->(:Requirement)
(:Design)-[:IMPLEMENTS]->(:Architecture)
(:Design)-[:SATISFIES]->(:Requirement)

// Supporting relationships
(:DataModel|:Quickstart|:ApiContract)-[:SUPPORTS]->(:Design|:Architecture)
(:Research)-[:INFORMS]->(:Design|:Architecture|:Decision)
(:Tasks)-[:DERIVED_FROM]->(:Design|:Architecture)

// Implementation tracking
(:CodeArtifact)-[:IMPLEMENTS]->(:Design|:Requirement)
(:Benchmark)-[:EVIDENCES]->(:Design|:Decision)
(:Run)-[:UPDATED]->(:CodeArtifact|:Tasks|:Design|:Architecture)

// Decision flow
(:Decision)-[:SUPERSEDES]->(:Architecture|:Design|:Requirement)
(:Decision)-[:APPROVES|:REJECTS]->(:Run|:PR|:Design)
(:Decision)-[:CREATED_FROM]->(:Research)
```

## Vector Index Schema

Store document chunks with rich metadata for hybrid retrieval:

```json
{
  "chunk_id": "design-collision.md#broadphase",
  "doc_type": "design",
  "subsystem": "physics-system",
  "doc_id": "physics-collision-design",
  "version": "1.5.0",
  "owners": ["@pmaclyman"],
  "path": "docs/physics-system/design-collision.md",
  "hash": "sha256:…",
  "heading": "Broadphase: Sweep-and-Prune",
  "requires": ["physics-architecture@>=1.7.0"],
  "embedding": [0.123, -0.456, ...] // 1536-dim vector
}
```

### Retrieval Strategy
- Vector search for semantic similarity across all document types
- Graph traversal for lineage, dependencies, and approval chains
- Hybrid queries combining both for complex validation

### Phase 1 Implementation Details

#### Minimal Graph Schema
Nodes:
- `:Doc {id, title, source}`
- `:Chunk {id, text, embedding: Vector<Float>, docId}`  
Rel: `(:Doc)-[:HAS_CHUNK]->(:Chunk)`

#### Vector Index Creation
```cypher
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Doc) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS FOR (c:Chunk) ON (c.embedding) OPTIONS { 
  indexConfig: {
    'vector.dimensions': 1024,
    'vector.similarity_function': 'cosine' 
  }
};
```

Vector-index creation/query syntax is straight from the Neo4j Cypher manual. Choose `vector.dimensions` to match your model (e.g., **BGE-M3 is 1024-d; Nomic v2 supports matryoshka dims; Snowflake Arctic variants are documented on HF**).