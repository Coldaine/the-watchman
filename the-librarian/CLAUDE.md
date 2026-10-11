# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Librarian is an **AI Agent Governance System** that manages document ingestion, validation, and semantic search using Neo4j knowledge graphs and local LLM embeddings. It implements a specification-driven development approach with immutable audit trails for all governance decisions.

### Extended Capabilities: Repository Portfolio Management

The Librarian's graph database also supports **portfolio-wide repository tracking**, where external agent systems (Colossus, Watchmen) submit repository analysis results for storage and querying.

**The Librarian's Role**:
- **Data storage layer only** - Provides Neo4j graph schema and API endpoints
- Stores repository metadata, analysis results, health scores, and sprint assignments
- Provides query capabilities for portfolio intelligence
- **Does NOT run analysis** - External systems handle that

**External Systems' Role** (Colossus/Watchmen):
- Run repository analysis via Perplexity (using MCP stealth-browser)
- Orchestrate analysis scheduling and coordination
- Submit results to the Librarian's API

**Key Principle**: The Librarian is a **passive data store with query capabilities**, not an analysis orchestrator.

See [`docs/subdomains/repository-portfolio-management.md`](docs/subdomains/repository-portfolio-management.md) for full details.

## Development Commands

### Environment Setup
```bash
# Install dependencies (including dev tools)
uv sync --all-extras

# Production dependencies only
uv sync
```

### Running the Application
```bash
# Development mode with auto-reload
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Production mode
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_api.py

# Run specific test
uv run pytest tests/test_api.py::test_health_endpoint

# Run tests matching pattern
uv run pytest -k "validation"

# With coverage report
uv run pytest --cov=src --cov-report=html

# Verbose output with print statements
uv run pytest -v -s

# Stop on first failure
uv run pytest -x

# Run only failed tests from last run
uv run pytest --lf
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/ tests/

# All quality checks in sequence
uv run black src/ tests/ && uv run isort src/ tests/ && uv run mypy src/ && uv run flake8 src/ tests/
```

### Dependency Management
```bash
# Add production dependency
uv add <package-name>

# Add development dependency
uv add --dev <package-name>

# Update all dependencies
uv sync --upgrade

# Reinstall all dependencies
uv sync --reinstall
```

## Architecture Overview

### Core Pattern: Orchestration with Adapters

The system uses a **layered architecture with adapter pattern** to decouple modules:

```
API Layer (FastAPI)
    ↓
Integration Layer (Orchestrator + Adapters)
    ↓ ↓ ↓
Processing ← → Validation ← → Graph (Neo4j)
```

### Module Responsibilities

- **src/api/**: FastAPI REST endpoints for agent workflow, queries, validation, and admin
- **src/integration/**: Orchestrator and adapters that bridge between modules
- **src/processing/**: Document parsing, chunking, and embedding generation (via Ollama)
- **src/validation/**: Rule engine with 5 parallel validation rules + drift detection
- **src/graph/**: Neo4j operations, vector search, and schema management
- **tests/**: Unit and integration tests mirroring source structure

### Key Architectural Patterns

#### 1. Adapter Pattern (src/integration/)
Three adapters handle module boundaries without tight coupling:
- **DocumentGraphAdapter**: Transforms processed documents → Neo4j nodes
- **RequestAdapter**: Transforms documents → validation requests
- **ValidationGraphBridge**: Provides sync wrapper for async Neo4j queries used by validation rules

#### 2. Orchestrator Pattern (LibrarianOrchestrator)
Coordinates complete document lifecycle:
```python
process_document() → parse → chunk → embed → validate → store (if approved) → audit
```

#### 3. Async/Sync Bridge
**Critical non-obvious pattern**: Validation rules are synchronous (for simplicity), but need to query Neo4j (async). The system uses `AsyncSync` utility with `nest_asyncio` to enable sync functions to call async operations without blocking.

```python
# Validation rules run in thread pool but can still query Neo4j
class ValidationRule:
    def validate(self, request, context):
        # Uses ValidationGraphBridge.query_sync() which wraps async calls
        results = context.graph_query(cypher, params)
```

#### 4. Immutable Audit Trail
**Never deletes validation decisions**. Every request, decision, and approval is preserved in Neo4j:
```cypher
(req:AgentRequest)-[:RESULTED_IN]->(dec:Decision)-[:APPROVES]->(doc:Architecture)
```

The system includes a `force_update` flag that can bypass validation while **still recording the violation** in the audit trail.

### Data Flow: Document Ingestion to Query

**Write Path**:
1. `DocumentParser` extracts YAML frontmatter + markdown sections
2. `TextChunker` performs semantic chunking (1000 chars, 200 overlap)
3. `EmbeddingGenerator` calls Ollama (nomic-embed-text, 768-dim vectors)
4. `RequestAdapter` converts document → AgentRequest for validation
5. `ValidationEngine` runs 5 rules in parallel using `asyncio.gather()`
6. If approved: `DocumentAdapter` stores document + chunks with embeddings in Neo4j
7. Always: `ValidationBridge` stores audit trail (Request → Decision nodes)

**Read Path**:
1. Generate query embedding via Ollama
2. `VectorOperations.semantic_search()` queries Neo4j vector indexes
3. Return top-K similar documents with relevance scores

### Critical Design Decisions

#### Embeddings Stored on Nodes
Embeddings are stored **directly on Neo4j nodes** (not separate vector store):
```cypher
(chunk:Chunk {embedding: [0.1, 0.2, ..., 0.768]})
```
**Benefit**: Single source of truth, no sync issues. Neo4j 5.x handles this efficiently with native vector indexes.

#### Chunks as First-Class Nodes
Chunks are full nodes, not properties:
```cypher
(doc:Architecture)-[:CONTAINS]->(chunk:Chunk)
```
**Benefit**: Fine-grained search, chunk-level annotations, enables future chunk versioning.

#### Parallel Rule Execution
The 5 validation rules execute concurrently:
- DocumentStandardsRule
- VersionCompatibilityRule
- ArchitectureAlignmentRule
- RequirementCoverageRule
- ConstitutionComplianceRule

Use `asyncio.gather()` for performance; failures in one rule don't block others.

#### Drift Detection via Graph Queries
Temporal inconsistencies detected through Cypher traversal:
```cypher
MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
WHERE d.modified_at > a.modified_at
  AND NOT exists((:Decision)-[:APPROVES]->(:AgentRequest)-[:TARGETS]->(d))
```
Violations are **graph-structural**, not code-based.

## Testing Strategy

### Test Structure
```
tests/
  ├── conftest.py          # Shared fixtures (session/function scoped)
  ├── test_processing.py   # Pipeline, parser, chunker, embedder
  ├── test_validation.py   # Rules, engine, drift detection
  ├── test_graph.py        # Operations, vector ops, queries
  ├── test_integration.py  # Adapters, orchestrator, end-to-end
  └── test_api.py          # API endpoints
```

### Key Testing Fixtures (conftest.py)

- **Session-scoped**: `event_loop`, `test_data_dir`
- **Function-scoped**: `neo4j_connection`, `graph_operations`, `vector_operations`
- **Factories**: `architecture_node_factory`, `design_node_factory`, `test_embedding`
- **Cleanup**: `cleanup_test_nodes` - registers nodes for automatic deletion after tests

### Test Markers
```python
@pytest.mark.requires_neo4j    # Tests requiring Neo4j connection
@pytest.mark.requires_ollama   # Tests requiring Ollama service
@pytest.mark.slow              # Long-running tests
```

### Mock Strategy
- Use `mock_ollama_response` to mock embeddings without Ollama service
- Sample markdown fixtures: `sample_architecture_markdown`, `sample_design_markdown`
- Mock Neo4j responses for unit tests of validation rules

## Critical Dependencies

- **Neo4j (5.14.0)**: Graph database with native vector indexes for semantic search
- **Ollama (0.1.6)**: Local LLM inference for embeddings (nomic-embed-text model, 768 dims)
- **FastAPI (0.104.1)**: Async REST API framework
- **Pydantic (2.5.0)**: Type-safe data models throughout system
- **nest-asyncio (1.5.8)**: Critical for async/sync bridging in validation rules

## Code Style

- **Line length**: 100 characters (black configuration)
- **Import sorting**: isort with black-compatible profile
- **Type hints**: Required for function signatures
- **Docstrings**: Required for public functions/classes
- **Async/await**: Prefer async for I/O operations; use AsyncSync bridge when sync is required

## Common Development Tasks

### Adding New Document Types
1. Update `NodeLabels` enum in `src/graph/schema.py`
2. Add label mapping in `DocumentGraphAdapter._get_node_label()`
3. Create vector index in Neo4j
4. Add validation rules if needed in `src/validation/rules.py`

### Adding New Validation Rules
1. Create class inheriting from `ValidationRule` in `src/validation/rules.py`
2. Implement `validate(request, context) -> List[Violation]` method
3. Add to `ValidationEngine.__init__()` rules list
4. Rules execute in parallel automatically via `asyncio.gather()`

### Extending API Endpoints
1. Create new router module in `src/api/`
2. Import and register in `src/main.py` with `app.include_router()`
3. Use lazy initialization pattern for services (see `get_vector_ops()` example)
4. Add Pydantic models for request/response in `src/api/models.py`

### Writing Tests for New Features
1. Add reusable fixtures to `tests/conftest.py` if needed
2. Use `cleanup_test_nodes` fixture for tests creating Neo4j nodes
3. Mark tests with appropriate pytest markers (`@pytest.mark.requires_neo4j`, etc.)
4. Mock Ollama unless specifically testing embedding generation
5. Use factory fixtures for creating test data with sensible defaults

## Environment Configuration

Required `.env` variables (see `.env.template`):

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text

# API
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=INFO

# Validation
DRIFT_THRESHOLD=0.1
VALIDATION_ENABLED=true
```

## Security Considerations

### Cypher Injection Prevention
`GraphOperations.sanitize_cypher_params()` provides defense-in-depth against injection attacks, even though parameterized queries are used. Do not bypass this validation.

### Audit Trail Integrity
Never delete `AgentRequest` or `Decision` nodes in production. Use deprecation flags instead to maintain immutable audit trail.

### Force Update Flag
`LibrarianOrchestrator.process_document(force_update=True)` bypasses validation but **still records the violation**. Use only for emergency fixes and document rationale.

## Troubleshooting

### Import Errors
```bash
# Verify installation
uv run python -c "import src; print('OK')"

# Reinstall if needed
uv sync --reinstall
```

### Test Database Cleanup
If tests leave orphaned nodes:
```cypher
MATCH (n) WHERE n.id STARTS WITH 'TEST-' DETACH DELETE n
```

### Async/Sync Issues
If validation rules fail with event loop errors, check that `nest_asyncio.apply()` is called in `AsyncSync` initialization.

### Vector Search Not Working
Verify vector indexes exist in Neo4j:
```cypher
SHOW INDEXES
```
Create missing indexes via `VectorOperations.create_vector_index()`.

## Additional Documentation

- **UV_SETUP.md**: Comprehensive UV package manager guide
- **AGENTS.md**: Agent coordination and parallel development workflows
- **docs/api/QUICK_START.md**: API endpoint documentation
- **docs/graph/SETUP.md**: Neo4j setup and graph module guide
- **docs/integration_architecture.md**: Detailed integration patterns
