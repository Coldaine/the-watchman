# Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Librarian Agent System                       │
│                                                                       │
│  Input: Markdown Documents → Output: Searchable Knowledge Graph      │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Processing Module  │────▶│  Integration Layer  │◀────│  Validation Module  │
│                     │     │                     │     │                     │
│  - Parser           │     │  - Document Adapter │     │  - Engine           │
│  - Chunker          │     │  - Request Adapter  │     │  - Rules (5)        │
│  - Embedder         │     │  - Validation Bridge│     │  - Models           │
│  - Pipeline         │     │  - Orchestrator     │     │  - Drift Detection  │
└─────────────────────┘     │  - Async Utils      │     └─────────────────────┘
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │   Graph Module      │
                            │                     │
                            │  - Operations       │
                            │  - Vector Ops       │
                            │  - Schema Manager   │
                            │  - Connection       │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │      Neo4j DB       │
                            │  Graph + Vectors    │
                            └─────────────────────┘
```

## Data Flow Diagram

```
┌──────────────┐
│   File.md    │
└──────┬───────┘
       │
       │ (1) Read File
       ▼
┌─────────────────────────────┐
│    IngestionPipeline        │
│  ┌──────────────────────┐   │
│  │ Parser               │   │
│  │  - Extract YAML      │   │
│  │  - Parse Markdown    │   │
│  │  - Create sections   │   │
│  └──────┬───────────────┘   │
│         │ ParsedDocument    │
│         ▼                   │
│  ┌──────────────────────┐   │
│  │ Chunker              │   │
│  │  - Semantic chunks   │   │
│  │  - Preserve context  │   │
│  └──────┬───────────────┘   │
│         │ List[Chunk]       │
│         ▼                   │
│  ┌──────────────────────┐   │
│  │ Embedder (Ollama)    │   │
│  │  - nomic-embed-text  │   │
│  │  - 768 dimensions    │   │
│  └──────┬───────────────┘   │
│         │                   │
└─────────┼───────────────────┘
          │ List[ProcessedChunk]
          ▼
┌─────────────────────────────┐
│     RequestAdapter          │
│  - Map document fields      │
│  - Extract references       │
│  - Generate rationale       │
└──────┬──────────────────────┘
       │ AgentRequest
       ▼
┌─────────────────────────────┐
│    ValidationEngine         │
│  ┌──────────────────────┐   │
│  │ DocumentStandardsRule│   │ (Parallel)
│  ├──────────────────────┤   │
│  │VersionCompatibility  │   │ (Execution)
│  ├──────────────────────┤   │
│  │ ArchitectureAlignment│   │
│  ├──────────────────────┤   │
│  │ RequirementCoverage  │   │
│  ├──────────────────────┤   │
│  │ConstitutionCompliance│   │
│  └──────┬───────────────┘   │
└─────────┼───────────────────┘
          │ ValidationResult
          ▼
       ┌──────┐
       │ Pass?│
       └┬────┬┘
        │    │ No → Store audit trail only
        │    │
        │ Yes│
        ▼    ▼
┌─────────────────────────────┐
│    DocumentGraphAdapter     │
│                             │
│  (1) Create/Update Doc Node │
│      - Architecture/Design  │
│      - Properties from FM   │
│      - Content + hash       │
│                             │
│  (2) Create Chunk Nodes     │
│      - One per chunk        │
│      - Store embeddings     │
│      - Link to document     │
│                             │
│  (3) Create Relationships   │
│      - Doc→Chunks (CONTAINS)│
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   ValidationGraphBridge     │
│                             │
│  (1) Create AgentRequest    │
│  (2) Create Decision        │
│  (3) Link Request→Decision  │
│  (4) Link Decision→Document │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│          Neo4j Graph        │
│                             │
│  Nodes:                     │
│  - Architecture/Design      │
│  - Chunk (with embeddings)  │
│  - AgentRequest             │
│  - Decision                 │
│                             │
│  Relationships:             │
│  - REFERENCES (CONTAINS)    │
│  - RESULTED_IN              │
│  - APPROVES                 │
│                             │
│  Indexes:                   │
│  - Vector (embeddings)      │
│  - Unique (IDs)             │
│  - Composite (queries)      │
└─────────────────────────────┘
```

## Component Interaction

```
LibrarianOrchestrator
       │
       ├──▶ IngestionPipeline
       │         │
       │         ├──▶ DocumentParser
       │         ├──▶ TextChunker
       │         └──▶ EmbeddingGenerator
       │
       ├──▶ RequestAdapter
       │         │
       │         └──▶ AgentRequest
       │
       ├──▶ ValidationEngine
       │         │
       │         ├──▶ DocumentStandardsRule
       │         ├──▶ VersionCompatibilityRule
       │         ├──▶ ArchitectureAlignmentRule
       │         ├──▶ RequirementCoverageRule
       │         └──▶ ConstitutionComplianceRule
       │
       ├──▶ DocumentGraphAdapter
       │         │
       │         ├──▶ GraphOperations
       │         └──▶ VectorOperations
       │
       └──▶ ValidationGraphBridge
                 │
                 └──▶ GraphOperations
```

## Async/Sync Boundaries

```
┌──────────────────────────────────────────────────────────┐
│                    Async Context                         │
│                                                           │
│  ┌────────────────┐                                      │
│  │ Orchestrator   │ (async)                              │
│  └────┬───────────┘                                      │
│       │                                                   │
│       ├──▶ Pipeline.process_file()        (sync)         │
│       │                                                   │
│       ├──▶ RequestAdapter                 (sync)         │
│       │                                                   │
│       ├──▶ ValidationEngine.validate()    (async)        │
│       │         │                                         │
│       │         └──▶ Rules.validate()     (sync)         │
│       │              ▲                                    │
│       │              │ run_in_executor()                  │
│       │              └────────────────────┐               │
│       │                                   │               │
│       │         ┌─────────────────────────┘               │
│       │         │ ValidationBridge.query_sync()           │
│       │         │      │                                  │
│       │         │      └──▶ AsyncSync.run_sync()          │
│       │         │           │                             │
│       │         │           └──▶ GraphOps.query() (async) │
│       │                                                   │
│       ├──▶ DocumentAdapter.store()        (async)        │
│       │         │                                         │
│       │         ├──▶ GraphOps.create_node()  (async)     │
│       │         └──▶ VectorOps.store()       (async)     │
│       │                                                   │
│       └──▶ ValidationBridge.store()        (async)       │
│                 │                                         │
│                 └──▶ GraphOps.create_node()  (async)     │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Storage Schema

### Document Storage

```cypher
// Architecture Document
(arch:Architecture {
  id: "ARCH-001",                      // Unique ID
  title: "System Architecture",        // Human name
  doc_type: "architecture",            // Type
  subsystem: "core",                   // Subsystem
  version: "1.0.0",                    // Version
  status: "approved",                  // Status
  owners: ["user1", "user2"],          // Owners
  content: "Full markdown...",         // Content
  content_hash: "sha256...",           // Hash
  compliance_level: "strict",          // Compliance
  drift_tolerance: "none",             // Tolerance
  embedding: [0.1, 0.2, ...],          // 768-dim vector
  created_at: "2024-01-01T00:00:00Z",
  modified_at: "2024-01-01T00:00:00Z"
})

// Chunk with Embedding
(chunk:Chunk {
  id: "chunk_abc123",                  // Unique ID
  content: "Chunk text...",            // Content
  doc_type: "architecture",            // Parent type
  source_path: "/path/to/doc.md",      // Source
  section_title: "Overview",           // Section
  section_level: 2,                    // Level
  chunk_index: 0,                      // Index
  start_index: 0,                      // Start pos
  end_index: 100,                      // End pos
  embedding: [0.3, 0.4, ...],          // 768-dim vector
  created_at: "2024-01-01T00:00:00Z"
})

// Relationship
(arch)-[:REFERENCES {
  chunk_index: 0,
  relationship_type: "CONTAINS"
}]->(chunk)
```

### Audit Trail Storage

```cypher
// Agent Request
(req:AgentRequest {
  id: "req_xyz789",
  agent_id: "ingestion_pipeline",
  action: "create",
  target_type: "architecture",
  target_id: "ARCH-001",
  rationale: "Creating new architecture...",
  references: ["ARCH-000"],
  timestamp: "2024-01-01T00:00:00Z",
  content: "{...}",
  metadata: "{...}"
})

// Decision
(dec:Decision {
  id: "decision:req_xyz789",
  decision_type: "approval",
  timestamp: "2024-01-01T00:00:00Z",
  author: "validation_engine",
  author_type: "system",
  rationale: "All validation checks passed",
  confidence: 1.0,
  impact_level: "low",
  status: "approved",
  violation_count: 0,
  warning_count: 0
})

// Relationships
(req)-[:RESULTED_IN {
  processing_time_ms: 150.5,
  confidence: 1.0
}]->(dec)

(dec)-[:APPROVES {
  approved_at: "2024-01-01T00:00:00Z",
  agent_id: "ingestion_pipeline"
}]->(arch)
```

## Error Flow

```
┌──────────────┐
│ Process Doc  │
└──────┬───────┘
       │
       ▼
   ┌───────┐
   │ Error?│────No───▶ Continue
   └───┬───┘
       │ Yes
       ▼
┌──────────────────┐
│  Catch Exception │
└──────┬───────────┘
       │
       ├──▶ Log with stack trace
       │
       ├──▶ Create OrchestrationResult
       │    with error field set
       │
       └──▶ Return result (don't raise)
            │
            ▼
       ┌────────────────┐
       │ Batch mode?    │
       └────┬──────┬────┘
            │      │
         Yes│      │No
            │      └──▶ Show error to user
            │
            └──▶ Continue with next file
```

## Performance Characteristics

### Parallel Processing

```
Validation Rules (Parallel):
┌──────────────────────────┐
│ Rule 1: Standards        │ ──┐
├──────────────────────────┤   │
│ Rule 2: Versioning       │ ──┤
├──────────────────────────┤   │
│ Rule 3: Architecture     │ ──┼──▶ asyncio.gather()
├──────────────────────────┤   │
│ Rule 4: Requirements     │ ──┤
├──────────────────────────┤   │
│ Rule 5: Constitution     │ ──┘
└──────────────────────────┘
     │ All complete
     ▼
  Combined Result
```

### Batch Embeddings

```
Chunks: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            │
            │ Batch size = 10
            ▼
Batch 1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] ──▶ Ollama
Batch 2: [11, 12]                         ──▶ Ollama
            │
            ▼
    Combined Results
```

## Monitoring Points

```
┌─────────────────────────────────────────────┐
│ Orchestrator Metrics                        │
├─────────────────────────────────────────────┤
│ • Documents processed                       │
│ • Processing time per document              │
│ • Success/failure rate                      │
│ • Validation pass/fail rate                 │
│ • Chunks created per document               │
│ • Average violations per document           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Component Metrics                           │
├─────────────────────────────────────────────┤
│ • Pipeline: Parse/chunk/embed times         │
│ • Validation: Rule execution times          │
│ • Graph: Query execution times              │
│ • Embeddings: Generation time per batch     │
└─────────────────────────────────────────────┘
```

## Integration Points Summary

| From Module  | Adapter              | To Module   | Data Format        |
|--------------|----------------------|-------------|--------------------|
| Processing   | RequestAdapter       | Validation  | AgentRequest       |
| Processing   | DocumentAdapter      | Graph       | Node properties    |
| Validation   | ValidationBridge     | Graph       | Audit nodes        |
| Graph        | ValidationBridge     | Validation  | Query results      |
| Sync Code    | AsyncSync            | Async Code  | Coroutine          |
| Async Code   | AsyncSync            | Sync Code   | Run in executor    |

## Success Metrics

✓ **Zero Data Loss**: All document data preserved
✓ **100% Coverage**: All chunks have embeddings
✓ **Complete Audit**: Every validation recorded
✓ **Error Isolation**: Failures don't cascade
✓ **Type Safety**: Pydantic models throughout
✓ **Async Compatible**: No blocking operations

## Extended Integration: Portfolio Management

### External System Integration Pattern

The Librarian can serve as a **data storage layer** for external agent systems (Colossus, Watchmen) that perform repository portfolio analysis.

```
┌─────────────────────────────────────────────────┐
│      External Agent Systems                      │
│      (Colossus / Watchmen)                       │
│                                                   │
│  ┌────────────────────────────────────────┐      │
│  │  Repository Discovery                  │      │
│  │  - GitHub API calls                    │      │
│  │  - Clone/update local copies           │      │
│  └──────────┬─────────────────────────────┘      │
│             │                                     │
│             ▼                                     │
│  ┌────────────────────────────────────────┐      │
│  │  Analysis Orchestration                │      │
│  │  - Invoke Perplexity via web           │      │
│  │  - Parse analysis results              │      │
│  │  - Calculate health scores             │      │
│  └──────────┬─────────────────────────────┘      │
└─────────────┼─────────────────────────────────────┘
              │ HTTP POST
              │ (analysis results)
              ▼
┌─────────────────────────────────────────────────┐
│      The Librarian API                          │
│                                                  │
│  POST /repositories/{id}/analysis               │
│  POST /repositories/{id}/health                 │
│  POST /sprints                                  │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  API Layer (FastAPI)                   │     │
│  │  - Validate incoming data              │     │
│  │  - Transform to graph nodes            │     │
│  └──────────┬─────────────────────────────┘     │
│             │                                    │
│             ▼                                    │
│  ┌────────────────────────────────────────┐     │
│  │  Graph Operations                      │     │
│  │  - Create Repository nodes             │     │
│  │  - Create AnalysisRun nodes            │     │
│  │  - Create ProjectHealth nodes          │     │
│  │  - Link relationships                  │     │
│  └──────────┬─────────────────────────────┘     │
│             │                                    │
│             ▼                                    │
│  ┌────────────────────────────────────────┐     │
│  │  Neo4j Graph                           │     │
│  │  (Repository) → (AnalysisRun)          │     │
│  │  (Repository) → (ProjectHealth)        │     │
│  │  (Repository) → (Architecture)         │     │
│  │  (Sprint) → (Repository)               │     │
│  └────────────────────────────────────────┘     │
└──────────────────────────────────────────────────┘
              │
              │ HTTP GET (queries)
              ▼
┌─────────────────────────────────────────────────┐
│      External Systems / Users                    │
│                                                  │
│  GET /repositories?health<50                    │
│  GET /repositories/{id}/health                  │
│  POST /query/portfolio (custom Cypher)          │
└──────────────────────────────────────────────────┘
```

### Data Flow: Repository Analysis Submission

```
External Agent (Colossus)
       │
       │ (1) Analyze repository via Perplexity
       ▼
┌──────────────────────┐
│  Analysis Results    │
│  {                   │
│    repo_id: "...",   │
│    scores: {...},    │
│    findings: [...]   │
│  }                   │
└──────┬───────────────┘
       │
       │ (2) HTTP POST to Librarian API
       ▼
┌─────────────────────────────┐
│  POST /repositories/        │
│       {repo_id}/analysis    │
│                             │
│  Request Body:              │
│  {                          │
│    timestamp: "...",        │
│    tool: "perplexity",      │
│    code_quality: 85,        │
│    doc_quality: 70,         │
│    test_coverage: 65,       │
│    security_score: 90,      │
│    findings: [              │
│      {                      │
│        category: "...",     │
│        severity: "...",     │
│        message: "..."       │
│      }                      │
│    ]                        │
│  }                          │
└──────┬──────────────────────┘
       │
       │ (3) API validates and transforms
       ▼
┌─────────────────────────────┐
│  GraphOperations            │
│                             │
│  CREATE (r:Repository)      │
│  CREATE (a:AnalysisRun)     │
│  CREATE (h:ProjectHealth)   │
│  CREATE (a)-[:PRODUCED]->   │
│         (result:            │
│          AnalysisResult)    │
│  CREATE (r)-[:HAS_HEALTH]-> │
│         (h)                 │
└──────┬──────────────────────┘
       │
       │ (4) Store in Neo4j
       ▼
┌─────────────────────────────┐
│   Neo4j Graph               │
│                             │
│  (Repository)               │
│       ↓                     │
│  (AnalysisRun)              │
│       ↓                     │
│  (AnalysisResult)           │
│       ↓                     │
│  (ProjectHealth)            │
└─────────────────────────────┘
```

### API Contract for External Systems

**Submit Analysis Results**:
```python
POST /repositories/{repo_id}/analysis

Request:
{
  "timestamp": "2024-11-10T12:00:00Z",
  "tool": "perplexity",
  "status": "completed",
  "duration_seconds": 45.2,
  "scores": {
    "code_quality": 85,
    "documentation": 70,
    "test_coverage": 65,
    "security": 90,
    "maintenance_burden": "medium"
  },
  "findings": [
    {
      "category": "security",
      "severity": "warning",
      "message": "Dependency X has known vulnerabilities",
      "file_path": "requirements.txt",
      "recommendation": "Update to version Y"
    }
  ]
}

Response:
{
  "analysis_id": "analysis_abc123",
  "repository_id": "repo_xyz789",
  "stored_at": "2024-11-10T12:00:01Z",
  "nodes_created": 15,
  "relationships_created": 18
}
```

**Query Portfolio Health**:
```python
GET /portfolio/health

Response:
{
  "total_repositories": 42,
  "average_health": 78.5,
  "critical_issues": 3,
  "repositories_needing_attention": [
    {
      "id": "repo_123",
      "name": "legacy-app",
      "health_score": 45,
      "last_analyzed": "2024-11-09T00:00:00Z",
      "critical_findings": 2
    }
  ]
}
```

### Separation of Concerns

| Concern | Owner | Responsibility |
|---------|-------|----------------|
| **Repository Discovery** | External Systems | GitHub API, cloning, updates |
| **Analysis Execution** | External Systems | Perplexity invocation, result parsing |
| **Sprint Coordination** | External Systems | Planning, prioritization, notification |
| **Data Storage** | The Librarian | Neo4j graph management |
| **Query API** | The Librarian | Portfolio intelligence queries |
| **Historical Tracking** | The Librarian | Time-series health data |
| **Graph Relationships** | The Librarian | Cross-repository connections |

This separation allows:
- The Librarian to focus on its core strength: **data management**
- External systems to evolve analysis strategies independently
- Multiple external systems to share the same data store
- Clear API contracts between systems
