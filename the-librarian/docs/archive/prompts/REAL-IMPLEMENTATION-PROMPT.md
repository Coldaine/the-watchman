# REAL Librarian Agent Implementation - Full System

## Stop - This is the ACTUAL System We're Building

We have 600+ lines of architecture documentation and 6 detailed subdomain specifications. We're building a **real AI agent governance system** that uses Neo4j for graph storage, vector embeddings for semantic search, and enforces actual validation rules. Not a mock, not a toy - the real thing.

## The Vision (From Our Architecture Doc)

The Librarian Agent is a **meta-agent governance system** that:
- Stores all documentation and specs in a Neo4j graph database with vector embeddings
- Validates every AI agent request against the actual specifications
- Maintains an immutable audit trail of all agent actions
- Detects drift between code and documentation
- Provides semantic search across all project knowledge

## What We're ACTUALLY Building (Phase 1)

### 1. Real Neo4j Integration (`src/graph/`)

From `docs/subdomains/graph-operations.md`:

```python
# src/graph/connection.py
- Real Neo4j driver connection pool
- Async operations with proper error handling
- Connection health checks

# src/graph/operations.py
- Create nodes: Architecture, Design, Requirement, AgentRequest, Decision
- Create relationships: IMPLEMENTS, SATISFIES, APPROVES
- Cypher queries for drift detection
- Transaction management

# src/graph/vector_ops.py
- Create vector indexes (768 dimensions)
- Store embeddings with documents
- Semantic similarity search using Neo4j's vector index
```

### 2. Real Document Processing (`src/processing/`)

From `docs/subdomains/document-processing.md`:

```python
# src/processing/parser.py
- Parse markdown files with YAML frontmatter
- Extract document structure and metadata
- Validate document format

# src/processing/chunker.py
- Intelligent text chunking (1000 tokens with 200 overlap)
- Preserve semantic boundaries
- Parent-child chunk relationships

# src/processing/embedder.py
- Generate embeddings using Ollama (nomic-embed-text)
- Batch processing for efficiency
- 768-dimension vectors
```

### 3. Real Validation Engine (`src/validation/`)

From `docs/subdomains/validation-engine.md`:

```python
# src/validation/rules.py
- DocumentStandardsRule: Check frontmatter requirements
- VersionCompatibilityRule: Validate version consistency
- ArchitectureAlignmentRule: Ensure changes align with architecture
- RequirementCoverageRule: Check requirements are satisfied
- ConstitutionComplianceRule: Enforce project constitution

# src/validation/engine.py
- Run all rules against requests
- Return detailed violation reports
- Escalation logic for critical violations

# src/validation/drift_detector.py
- Query for design ahead of architecture
- Find undocumented code
- Detect uncovered requirements
```

### 4. Real Agent Protocol (`src/agents/`)

From `docs/subdomains/agent-protocol.md`:

```python
# src/agents/coordinator.py
- Receive agent requests
- Validate against all rules
- Store in graph with full audit trail
- Return structured responses with reasons

# src/agents/context.py
- Assemble relevant context for agents
- Query graph for related documents
- Semantic search for similar content
- Return ranked, relevant context
```

### 5. Real RAG Implementation (`src/retrieval/`)

From `docs/subdomains/retrieval-context.md`:

```python
# src/retrieval/vector_store.py
- Neo4j vector store implementation
- Store and retrieve embeddings
- Similarity search with metadata filtering

# src/retrieval/rag_chain.py
- Query expansion
- Hybrid search (vector + graph traversal)
- Context ranking and assembly
- LLM integration for answers
```

### 6. Complete FastAPI Implementation (`src/api/`)

From `docs/architecture.md` lines 264-364:

```python
# All endpoints from the spec:
POST /agent/request-approval     # Full validation flow
POST /agent/report-completion    # Update graph with results
POST /query/semantic             # Real semantic search
GET  /query/cypher              # Direct graph queries
GET  /validation/drift-check    # Real drift detection
GET  /validation/compliance/{subsystem}  # Compliance metrics
POST /admin/ingest              # Ingest new documents
GET  /health                    # Real health checks
```

## Implementation Phases for Parallel Execution

### Phase 1: Foundation (3 Parallel Agents)

**Agent 1: Graph Foundation**
- Set up Neo4j connection
- Create schema (all node types and relationships)
- Create vector indexes
- Implement basic CRUD operations
- Test connection and operations

**Agent 2: Document Processing**
- Document parser with frontmatter
- Text chunking logic
- Ollama integration for embeddings
- Batch processing pipeline
- Test with sample documents

**Agent 3: Data Models**
- All Pydantic models from spec
- Validation logic in models
- Configuration management
- Type definitions
- Test model validation

### Phase 2: Core Logic (2 Parallel Agents)

**Agent 4: Validation & Governance**
- All validation rules
- Validation engine
- Drift detection queries
- Audit logging
- Test with various scenarios

**Agent 5: RAG & Retrieval**
- Vector store implementation
- Semantic search
- Context assembly
- Hybrid search
- Test retrieval accuracy

### Phase 3: Integration (1 Agent)

**Agent 6: API & Integration**
- All FastAPI endpoints
- Wire up all components
- Error handling
- Integration tests
- End-to-end flow testing

## Required Setup

```bash
# 1. Install Neo4j Desktop (Windows)
# Download from: https://neo4j.com/download/
# Create new project with database

# 2. Install Ollama
# Download from: https://ollama.ai/download
ollama pull nomic-embed-text

# 3. Python environment
python -m venv venv
venv\Scripts\activate
```

## Dependencies (requirements.txt)

```txt
# Core
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Neo4j
neo4j==5.14.0

# Embeddings & RAG
langchain==0.1.0
langchain-community==0.0.10
ollama==0.1.7
numpy==1.24.3

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
```

## Environment Configuration (.env)

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Validation
ESCALATION_THRESHOLD=3
DRIFT_CHECK_INTERVAL=300
```

## Test Data to Include

Create `tests/fixtures/` with:
- Sample architecture.md with proper frontmatter
- Sample design documents
- Valid and invalid agent requests
- Test embeddings

## Success Criteria

The system MUST:
1. **Connect to real Neo4j** and create/query nodes
2. **Generate real embeddings** via Ollama
3. **Perform real semantic search** using vector similarity
4. **Validate against real rules** from the specification
5. **Detect real drift** between documents
6. **Maintain real audit trail** in the graph
7. **Return real, actionable responses** to agents

## What NOT to Mock

- ❌ Do NOT mock Neo4j - use real connection
- ❌ Do NOT mock embeddings - use real Ollama
- ❌ Do NOT mock validation - implement real rules
- ❌ Do NOT mock search - use real vector similarity

## Parallel Task Division

### Terminal 1: Graph Expert
```
Build everything in src/graph/:
- Real Neo4j connection and operations
- Vector index creation and search
- All Cypher queries from specs
Read: docs/subdomains/graph-operations.md
```

### Terminal 2: Processing Expert
```
Build everything in src/processing/:
- Document parsing and chunking
- Ollama embedding generation
- Ingestion pipeline
Read: docs/subdomains/document-processing.md
```

### Terminal 3: Validation Expert
```
Build everything in src/validation/:
- All validation rules
- Drift detection
- Compliance checking
Read: docs/subdomains/validation-engine.md
```

### Terminal 4: Integration Expert
```
After 1-3 complete:
- Wire everything together
- Create all API endpoints
- Make the full flow work
Read: docs/architecture.md API section
```

## The Key Difference

We're building the REAL system from our specifications:
- Real graph database with real queries
- Real embeddings with real semantic search
- Real validation with real rules
- Real audit trail with real immutability
- Real drift detection with real alerts

Not a mock. Not a toy. The actual Librarian Agent that will govern AI agents working on codebases.

## Time Reality Check

This is 2-3 days of work, not 90 minutes. But with 4 parallel agents:
- Each agent gets ~6-8 hours of work
- Running in parallel = done in one day
- Focus on core flow first, enhance later

## Next Steps After Implementation

1. Deploy with Docker (Phase 3 from our plan)
2. Add monitoring and alerting
3. Implement advanced RAG strategies
4. Add file watching for real-time updates
5. Build admin UI

This is the system we designed. This is what we should build.