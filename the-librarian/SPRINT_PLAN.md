# Sprint Plan: Production Readiness & Integration Completion

**Sprint Period**: Next 4 weeks
**Current Commit**: `5c7ef55` - "docs: Clean up root directory and reorganize documentation"
**Branch**: `claude/sprint-planning-review-011CUzzF1H4x1v5hLcp8CRqt`

---

## Executive Summary

Based on comprehensive review of the codebase (Architecture Review: 92%, Integration Review: 62%, Quality Review: 65%), this sprint focuses on closing critical gaps to achieve production readiness.

### Current State
- ✅ All core modules implemented (graph, processing, validation, integration, API)
- ✅ 48/52 tests passing (92.3%)
- ✅ FastAPI application with all endpoints
- ⚠️ Graph tests failing (fixture issues)
- ⚠️ Integration gaps (chunk storage, audit persistence)
- ❌ Security vulnerabilities (hardcoded credentials)
- ❌ Missing production features (monitoring incomplete)

### Sprint Objectives
1. **100% Test Pass Rate** - Fix all test failures
2. **Zero Critical Security Issues** - Remove hardcoded credentials, fix injection risks
3. **Complete Integration Layer** - Define chunk storage, implement audit persistence
4. **Production Ready** - Add monitoring, improve observability
5. **Code Quality** - Remove duplication, fix deprecations

---

## Week 1: Critical Fixes

### Task 1.1: Fix Graph Module Tests [CRITICAL]
**Priority**: P0 - BLOCKING
**Estimated Effort**: 2 days
**Owner**: Backend Team

**Problem**: All 3 graph tests fail with `AttributeError: 'async_generator' object has no attribute '_is_connected'`

**Root Cause**: Async fixture pattern incorrect in `tests/test_graph.py:31-36`

**Solution**:
```python
# Current (BROKEN):
@pytest.fixture
async def connection():
    conn = Neo4jConnection()
    await conn.connect()
    yield conn  # Creates async generator

# Fixed:
@pytest.fixture(scope="function")
async def connection():
    conn = Neo4jConnection()
    await conn.connect()
    try:
        yield conn
    finally:
        await conn.close()
```

**Acceptance Criteria**:
- [ ] All 3 graph tests pass
- [ ] Add 10+ new vector operation tests
- [ ] Graph module coverage >95%
- [ ] Tests run reliably in CI/CD

**Files to Modify**:
- `tests/test_graph.py` - Fix fixtures
- `tests/conftest.py` - Add proper async fixture factories
- `tests/test_vector_ops.py` - NEW FILE for vector tests

---

### Task 1.2: Security Hardening [CRITICAL]
**Priority**: P0 - CRITICAL SECURITY
**Estimated Effort**: 1 day
**Owner**: Security Team

**Vulnerabilities Identified**:
1. **CWE-798**: Hardcoded credentials in `src/graph/config.py:24-27`
2. **CWE-89**: Cypher injection risk in `src/graph/operations.py:73-77`
3. **CWE-22**: Path traversal risk in `src/processing/parser.py:48-49`

**Solution**:

**1. Remove Hardcoded Credentials**:
```python
# src/graph/config.py - BEFORE
NEO4J_PASSWORD: str = Field(default="librarian-pass")  # ❌ VULNERABLE

# src/graph/config.py - AFTER
NEO4J_PASSWORD: str = Field(...)  # ✅ REQUIRED, no default
```

**2. Fix Cypher Injection**:
```python
# src/graph/operations.py - BEFORE
query = f"MATCH (n:{label}) WHERE n.id = $id"  # ❌ Injectable

# src/graph/operations.py - AFTER
ALLOWED_LABELS = {"Architecture", "Design", "Requirement", "CodeArtifact", "Decision", "AgentRequest"}
if label not in ALLOWED_LABELS:
    raise ValueError(f"Invalid node label: {label}")
query = f"MATCH (n:{label}) WHERE n.id = $id"  # ✅ Whitelisted
```

**3. Add Path Validation**:
```python
# src/processing/parser.py - NEW
import os
from pathlib import Path

def validate_file_path(file_path: str, allowed_base: str) -> Path:
    """Validate file path to prevent directory traversal."""
    path = Path(file_path).resolve()
    base = Path(allowed_base).resolve()

    if not path.is_relative_to(base):
        raise ValueError(f"Path {file_path} is outside allowed directory")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    return path
```

**Acceptance Criteria**:
- [ ] No hardcoded credentials in source code
- [ ] All node labels validated against whitelist
- [ ] File path validation prevents traversal attacks
- [ ] `.env.template` updated with required variables
- [ ] Security scan passes (bandit, safety)

**Files to Modify**:
- `src/graph/config.py` - Remove default password
- `src/graph/operations.py` - Add label whitelist
- `src/graph/schema.py` - Export ALLOWED_LABELS constant
- `src/processing/parser.py` - Add path validation
- `.env.template` - Document all required vars

---

### Task 1.3: Integration Layer Validation [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 2 days
**Owner**: Backend Team

**Problem**: Integration review identified potential adapter issues, but adapters exist - need validation

**Adapters to Test**:
1. **DocumentGraphAdapter** (`src/integration/document_adapter.py`)
   - Converts `ParsedDocument` → Neo4j node properties
   - Maps document types to node labels
   - Handles all document types (Architecture, Design, Code)

2. **RequestAdapter** (`src/integration/request_adapter.py`)
   - Converts `ParsedDocument` → `AgentRequest` for validation
   - Extracts references and metadata
   - Generates rationale

3. **ValidationBridge** (`src/integration/validation_bridge.py`)
   - Provides sync wrapper for async Neo4j queries
   - Stores validation results in graph
   - Creates Decision nodes

4. **AsyncSync Utility** (`src/integration/async_utils.py`)
   - Bridges async/sync boundary
   - Used by validation rules to query graph

**Test Plan**:
```python
# tests/test_integration.py

async def test_complete_document_flow():
    """Test document ingestion end-to-end."""
    # Given: Valid markdown document
    doc_path = "test_data/sample_architecture.md"

    # When: Process through orchestrator
    orchestrator = LibrarianOrchestrator(...)
    result = await orchestrator.process_document(doc_path)

    # Then: All steps succeed
    assert result["success"] is True
    assert result["node_id"] is not None
    assert result["validation"]["status"] == "approved"
    assert result["audit_id"] is not None

    # And: Data stored correctly in graph
    node = await graph_ops.get_node("Architecture", result["node_id"])
    assert node["id"] == expected_doc_id
    assert node["embedding"] is not None
    assert len(node["embedding"]) == 768

async def test_validation_bridge_async_sync():
    """Test async/sync bridge for validation rules."""
    # Given: Async graph operations
    graph_ops = GraphOperations(connection)

    # And: Sync validation rule
    bridge = ValidationGraphBridge(graph_ops)

    # When: Rule queries graph synchronously
    result = bridge.query_sync(
        "MATCH (a:Architecture) WHERE a.id = $id RETURN a",
        {"id": "test-001"}
    )

    # Then: Query executes without blocking
    assert isinstance(result, list)
    assert len(result) > 0

async def test_document_adapter_node_creation():
    """Test DocumentGraphAdapter creates correct nodes."""
    # Given: ParsedDocument
    doc = ParsedDocument(
        path="docs/test.md",
        doc_type="architecture",
        frontmatter={"id": "ARCH-001", "version": "1.0.0", ...},
        content="# Test Architecture",
        sections=[...],
        hash="abc123"
    )

    # When: Convert to node properties
    adapter = DocumentGraphAdapter()
    props = adapter.to_node_properties(doc)

    # Then: Properties match schema
    assert props["id"] == "ARCH-001"
    assert props["version"] == "1.0.0"
    assert props["content"] == "# Test Architecture"
    assert props["content_hash"] == "abc123"

    # And: Node label correctly mapped
    label = adapter.get_node_label("architecture")
    assert label == NodeLabels.ARCHITECTURE
```

**Acceptance Criteria**:
- [ ] Complete document flow test passes
- [ ] All adapters unit tested
- [ ] Async/sync bridge validated
- [ ] Integration test coverage >80%
- [ ] No data loss in conversion steps

**Files to Test**:
- `src/integration/document_adapter.py`
- `src/integration/request_adapter.py`
- `src/integration/validation_bridge.py`
- `src/integration/async_utils.py`
- `src/integration/orchestrator.py`

---

## Week 2: Missing Features

### Task 2.1: Define & Implement Chunk Storage [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 2 days
**Owner**: Backend Team

**Problem**: No defined strategy for storing chunks with embeddings

**Decision**: Store chunks as separate `Chunk` nodes (recommended for flexibility)

**Rationale**:
- ✅ Fine-grained search (return specific chunks)
- ✅ Chunk-level annotations possible
- ✅ Enables future chunk versioning
- ✅ Clear separation of concerns
- ⚠️ More relationships to manage (acceptable)

**Schema Addition**:
```cypher
// Add Chunk node type
CREATE CONSTRAINT chunk_id IF NOT EXISTS
  FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Create vector index for chunks
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS {
    indexConfig: {
      'vector.dimensions': 768,
      'vector.similarity_function': 'cosine'
    }
  };

// Chunk node structure
(chunk:Chunk {
  id: "chunk_abc123",                  // Unique ID
  content: "Chunk text...",            // Content
  doc_type: "architecture",            // Parent type
  source_path: "/path/to/doc.md",      // Source
  section_title: "Overview",           // Section
  section_level: 2,                    // Level
  chunk_index: 0,                      // Index within doc
  start_index: 0,                      // Start position
  end_index: 100,                      // End position
  embedding: [0.3, 0.4, ...],          // 768-dim vector
  created_at: datetime()
})

// Relationships
(doc:Architecture|Design)-[:CONTAINS {
  chunk_index: 0,
  relationship_type: "chunk"
}]->(chunk:Chunk)
```

**Implementation**:
```python
# src/graph/schema.py
class NodeLabels:
    ARCHITECTURE = "Architecture"
    DESIGN = "Design"
    CHUNK = "Chunk"  # NEW
    # ...

# src/integration/document_adapter.py
class DocumentGraphAdapter:
    async def store_document_with_chunks(
        self,
        doc: ParsedDocument,
        chunks: List[ProcessedChunk],
        graph_ops: GraphOperations,
        vector_ops: VectorOperations
    ) -> Dict[str, Any]:
        """Store document and chunks in graph."""
        # 1. Create/update document node
        doc_props = self.to_node_properties(doc)
        doc_label = self.get_node_label(doc.doc_type)
        doc_id = await graph_ops.create_node(doc_label, doc_props)

        # 2. Create chunk nodes
        chunk_ids = []
        for idx, chunk in enumerate(chunks):
            chunk_props = {
                "id": f"chunk_{doc_id}_{idx}",
                "content": chunk.content,
                "doc_type": doc.doc_type,
                "source_path": doc.path,
                "section_title": chunk.metadata.get("section_title"),
                "section_level": chunk.metadata.get("section_level"),
                "chunk_index": idx,
                "start_index": chunk.metadata.get("start_index"),
                "end_index": chunk.metadata.get("end_index"),
                "embedding": chunk.embedding,
                "created_at": datetime.utcnow().isoformat()
            }
            chunk_id = await graph_ops.create_node("Chunk", chunk_props)
            chunk_ids.append(chunk_id)

            # 3. Create CONTAINS relationship
            await graph_ops.create_relationship(
                doc_id, chunk_id, "CONTAINS",
                {"chunk_index": idx, "relationship_type": "chunk"}
            )

        return {
            "document_id": doc_id,
            "chunk_count": len(chunk_ids),
            "chunk_ids": chunk_ids
        }
```

**Vector Search Update**:
```python
# src/graph/vector_ops.py
async def semantic_search(
    self,
    query_embedding: List[float],
    limit: int = 10,
    doc_type: Optional[str] = None
) -> List[Dict]:
    """Search chunks by semantic similarity."""

    # Search CHUNK nodes, not document nodes
    cypher = """
    CALL db.index.vector.queryNodes(
        'chunk_embedding',
        $limit,
        $embedding
    ) YIELD node, score

    // Get parent document
    MATCH (doc)-[:CONTAINS]->(node)

    WHERE $doc_type IS NULL OR node.doc_type = $doc_type

    RETURN
        node.id as chunk_id,
        node.content as chunk_content,
        node.section_title as section,
        doc.id as doc_id,
        doc.title as doc_title,
        score
    ORDER BY score DESC
    LIMIT $limit
    """

    results = await self.graph_ops.query(cypher, {
        "embedding": query_embedding,
        "limit": limit,
        "doc_type": doc_type
    })

    return results
```

**Acceptance Criteria**:
- [ ] Chunk node type added to schema
- [ ] Vector index created for chunks
- [ ] DocumentGraphAdapter stores chunks correctly
- [ ] Semantic search returns chunk-level results
- [ ] CONTAINS relationships created
- [ ] Chunk storage documented in ADR
- [ ] Tests cover chunk storage and retrieval

**Files to Modify**:
- `src/graph/schema.py` - Add Chunk node type
- `src/integration/document_adapter.py` - Implement chunk storage
- `src/graph/vector_ops.py` - Update semantic search
- `docs/ADR/002-chunk-storage-strategy.md` - NEW FILE
- `tests/test_chunk_storage.py` - NEW FILE

---

### Task 2.2: Complete Audit Storage [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 1.5 days
**Owner**: Backend Team

**Problem**: Audit records logged but not persisted to graph

**Current State**:
- `AuditLogger` in `src/validation/audit.py` accepts optional `storage` parameter
- No storage backend implementation
- Audit trail lost on restart

**Solution**: Implement `GraphAuditStorage` backend

```python
# src/integration/audit_storage.py - NEW FILE

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.graph.operations import GraphOperations
from src.graph.schema import NodeLabels


class GraphAuditStorage:
    """Stores audit records in Neo4j as AuditEvent nodes."""

    def __init__(self, graph_ops: GraphOperations):
        """Initialize with graph operations.

        Args:
            graph_ops: Graph operations instance
        """
        self.graph_ops = graph_ops

    async def store_audit_record(self, record: Dict[str, Any]) -> str:
        """Store audit record as AuditEvent node.

        Args:
            record: Audit record dictionary

        Returns:
            Created audit event node ID
        """
        properties = {
            "id": record["id"],
            "timestamp": record["timestamp"],
            "event_type": record["event_type"],
            "request_id": record.get("request_id"),
            "agent_id": record.get("agent_id"),
            "decision": record.get("decision"),
            "metadata": json.dumps(record.get("metadata", {}))
        }

        # Store result as JSON if present
        if "result" in record:
            properties["result"] = json.dumps(record["result"])

        # Create AuditEvent node
        audit_id = await self.graph_ops.create_node("AuditEvent", properties)

        # Link to related nodes if present
        if "target_id" in record:
            await self._link_to_target(audit_id, record)

        return audit_id

    async def _link_to_target(self, audit_id: str, record: Dict[str, Any]):
        """Create relationships from audit event to target nodes."""
        target_id = record["target_id"]
        target_type = record.get("target_type", "Architecture")

        # Link AuditEvent to target document
        await self.graph_ops.create_relationship(
            audit_id, target_id, "AUDITS",
            {
                "event_type": record["event_type"],
                "timestamp": record["timestamp"]
            }
        )

        # If validation event, link to Decision
        if record["event_type"] == "validation" and "decision_id" in record:
            await self.graph_ops.create_relationship(
                audit_id, record["decision_id"], "RECORDS",
                {"timestamp": record["timestamp"]}
            )

    async def get_audit_trail(
        self,
        target_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a target node.

        Args:
            target_id: Target node ID
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        cypher = """
        MATCH (audit:AuditEvent)-[:AUDITS]->(target)
        WHERE target.id = $target_id
        RETURN audit
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        results = await self.graph_ops.query(cypher, {
            "target_id": target_id,
            "limit": limit
        })

        return [
            {
                "id": r["audit"]["id"],
                "timestamp": r["audit"]["timestamp"],
                "event_type": r["audit"]["event_type"],
                "agent_id": r["audit"].get("agent_id"),
                "decision": r["audit"].get("decision"),
                "metadata": json.loads(r["audit"].get("metadata", "{}"))
            }
            for r in results
        ]

    async def get_validation_history(
        self,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get validation event history.

        Args:
            agent_id: Filter by agent ID
            since: Filter events after this timestamp
            limit: Maximum records

        Returns:
            List of validation events
        """
        filters = []
        params = {"limit": limit}

        if agent_id:
            filters.append("audit.agent_id = $agent_id")
            params["agent_id"] = agent_id

        if since:
            filters.append("audit.timestamp >= $since")
            params["since"] = since.isoformat()

        where_clause = "AND " + " AND ".join(filters) if filters else ""

        cypher = f"""
        MATCH (audit:AuditEvent)
        WHERE audit.event_type = 'validation' {where_clause}
        RETURN audit
        ORDER BY audit.timestamp DESC
        LIMIT $limit
        """

        results = await self.graph_ops.query(cypher, params)

        return [
            {
                "id": r["audit"]["id"],
                "timestamp": r["audit"]["timestamp"],
                "agent_id": r["audit"]["agent_id"],
                "decision": r["audit"]["decision"],
                "result": json.loads(r["audit"].get("result", "{}")),
                "metadata": json.loads(r["audit"].get("metadata", "{}"))
            }
            for r in results
        ]
```

**Schema Update**:
```cypher
-- Add AuditEvent node type
CREATE CONSTRAINT audit_id IF NOT EXISTS
  FOR (a:AuditEvent) REQUIRE a.id IS UNIQUE;

-- Add index for timestamp queries
CREATE INDEX audit_timestamp IF NOT EXISTS
  FOR (a:AuditEvent) ON (a.timestamp);

-- Add index for agent_id queries
CREATE INDEX audit_agent IF NOT EXISTS
  FOR (a:AuditEvent) ON (a.agent_id);
```

**Integration with AuditLogger**:
```python
# src/validation/audit.py - UPDATE

class AuditLogger:
    def __init__(
        self,
        storage: Optional[Any] = None,
        enable_console: bool = True
    ):
        """Initialize audit logger.

        Args:
            storage: Storage backend (e.g., GraphAuditStorage)
            enable_console: Whether to log to console
        """
        self.storage = storage
        self.enable_console = enable_console
        self.logger = logging.getLogger(__name__)

    async def log_validation(
        self,
        request: Dict[str, Any],
        result: "ValidationResult"
    ) -> str:
        """Log validation event."""
        record = AuditRecord(
            event_type="validation",
            request_id=request["id"],
            agent_id=request["agent_id"],
            result={
                "status": result.status,
                "violations": [v.dict() for v in result.violations],
                "passed": result.passed
            },
            decision=result.status,
            metadata={
                "target_type": request["target_type"],
                "target_id": request.get("target_id"),
                "confidence": result.confidence
            }
        )

        # Log to console
        if self.enable_console:
            self.logger.info(f"Validation {result.status}: {request['id']}")

        # Persist to storage if available
        if self.storage:
            await self.storage.store_audit_record(record.dict())  # ✅ NOW WORKS

        return record.id
```

**Acceptance Criteria**:
- [ ] GraphAuditStorage implemented
- [ ] AuditEvent node type in schema
- [ ] AuditLogger wired to GraphAuditStorage
- [ ] Audit records persisted on validation
- [ ] get_audit_trail() query works
- [ ] get_validation_history() query works
- [ ] Tests cover audit storage and retrieval

**Files to Create/Modify**:
- `src/integration/audit_storage.py` - NEW FILE
- `src/graph/schema.py` - Add AuditEvent node type
- `src/validation/audit.py` - Update to use async storage
- `src/integration/orchestrator.py` - Wire GraphAuditStorage
- `tests/test_audit_storage.py` - NEW FILE

---

### Task 2.3: Production Observability [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 1.5 days
**Owner**: DevOps Team

**Problem**: Health checks exist but monitoring incomplete

**Current State**:
- `src/api/health.py` has basic health endpoint
- No structured logging
- No metrics collection
- No request/response timing

**Enhancements**:

**1. Enhanced Health Checks**:
```python
# src/api/health.py - ENHANCE

from typing import Dict, Any
from fastapi import APIRouter, status
from datetime import datetime
import psutil  # Add to requirements

router = APIRouter()

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe."""
    checks = {
        "neo4j": await check_neo4j(),
        "ollama": await check_ollama(),
        "disk": check_disk_space(),
        "memory": check_memory()
    }

    all_ready = all(checks.values())
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }, status_code

@router.get("/health")
async def health_detailed():
    """Detailed health status."""
    neo4j_health = await check_neo4j_detailed()
    ollama_health = await check_ollama_detailed()

    return {
        "status": "healthy" if neo4j_health["available"] and ollama_health["available"] else "degraded",
        "version": "0.1.0",
        "uptime_seconds": get_uptime(),
        "components": {
            "neo4j": neo4j_health,
            "ollama": ollama_health
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_neo4j_detailed() -> Dict[str, Any]:
    """Check Neo4j with details."""
    try:
        conn = get_connection()
        health = await conn.health_check()

        # Get database stats
        stats = await conn.query("CALL dbms.queryJmx('org.neo4j:*') YIELD attributes RETURN attributes")

        return {
            "available": health,
            "version": stats.get("version"),
            "node_count": await get_node_count(),
            "relationship_count": await get_relationship_count()
        }
    except Exception as e:
        return {"available": False, "error": str(e)}

async def check_ollama_detailed() -> Dict[str, Any]:
    """Check Ollama with details."""
    try:
        from src.processing.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        # Test with small text
        result = await embedder.embed_text("test")

        return {
            "available": True,
            "model": embedder.model,
            "embedding_dim": len(result)
        }
    except Exception as e:
        return {"available": False, "error": str(e)}

def check_disk_space() -> bool:
    """Check if disk space available."""
    usage = psutil.disk_usage('/')
    return usage.percent < 90  # 90% threshold

def check_memory() -> bool:
    """Check if memory available."""
    memory = psutil.virtual_memory()
    return memory.percent < 90  # 90% threshold
```

**2. Structured JSON Logging**:
```python
# src/main.py - ADD

import logging
import json
from datetime import datetime
from typing import Any

class JSONFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)

# Configure JSON logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
```

**3. Request/Response Timing Middleware**:
```python
# src/api/middleware.py - NEW FILE

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request/response times."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Log request
        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host
            }
        )

        return response

# src/main.py - ADD
from src.api.middleware import TimingMiddleware

app.add_middleware(TimingMiddleware)
```

**4. Basic Metrics Collection**:
```python
# src/api/metrics.py - NEW FILE

from typing import Dict
from collections import defaultdict, Counter
import time

class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self.request_count = Counter()
        self.request_duration = defaultdict(list)
        self.validation_results = Counter()
        self.start_time = time.time()

    def record_request(self, method: str, path: str, duration_ms: float, status: int):
        """Record API request metrics."""
        self.request_count[f"{method}:{path}:{status}"] += 1
        self.request_duration[f"{method}:{path}"].append(duration_ms)

    def record_validation(self, status: str):
        """Record validation result."""
        self.validation_results[status] += 1

    def get_metrics(self) -> Dict:
        """Get current metrics snapshot."""
        return {
            "uptime_seconds": time.time() - self.start_time,
            "requests": dict(self.request_count),
            "avg_duration_ms": {
                k: sum(v) / len(v) if v else 0
                for k, v in self.request_duration.items()
            },
            "validations": dict(self.validation_results)
        }

# src/main.py - ADD
from src.api.metrics import MetricsCollector

metrics = MetricsCollector()

@app.get("/metrics")
async def get_metrics():
    """Get application metrics."""
    return metrics.get_metrics()
```

**Acceptance Criteria**:
- [ ] `/health/live` endpoint for liveness
- [ ] `/health/ready` endpoint for readiness
- [ ] `/health` detailed health with component status
- [ ] JSON structured logging
- [ ] Request timing middleware
- [ ] `/metrics` endpoint with basic metrics
- [ ] CPU/memory/disk monitoring

**Files to Create/Modify**:
- `src/api/health.py` - Enhance health checks
- `src/api/middleware.py` - NEW FILE for timing
- `src/api/metrics.py` - NEW FILE for metrics
- `src/main.py` - Add middleware and logging
- `requirements.txt` - Add psutil dependency

---

## Week 3: Code Quality & Optimization

### Task 3.1: Remove Code Duplication [MEDIUM]
**Priority**: P2 - MEDIUM
**Estimated Effort**: 2 days
**Owner**: Backend Team

**Duplication Issues**:

**1. Frontmatter Validation (Parser vs Validation)**:
```python
# src/processing/parser.py - Line 188-206
def validate_frontmatter(self, frontmatter: Dict, doc_type: str):
    """Validate required frontmatter fields."""
    if doc_type == "architecture":
        required = ["doc", "subsystem", "id", "version", "status", "owners",
                   "compliance_level", "drift_tolerance"]
    # ...checks...

# src/validation/rules.py - Line 37-113
class DocumentStandardsRule(ValidationRule):
    def validate(self, request: Dict, context: ValidationContext):
        """Validate document standards."""
        frontmatter = request["content"]["frontmatter"]

        if target_type == "architecture":
            required = ["doc", "subsystem", "id", "version", "status", "owners",
                       "compliance_level", "drift_tolerance"]
        # ...same checks...
```

**Solution**: Extract to shared validator
```python
# src/validation/frontmatter_validator.py - NEW FILE

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator

class ArchitectureFrontmatter(BaseModel):
    """Frontmatter schema for architecture documents."""
    doc: str = Field(..., regex="^architecture$")
    subsystem: str
    id: str
    version: str = Field(..., regex=r"^\d+\.\d+\.\d+$")
    status: str = Field(..., regex="^(draft|review|approved|deprecated)$")
    owners: List[str]
    compliance_level: str = Field(..., regex="^(strict|flexible|advisory)$")
    drift_tolerance: str = Field(..., regex="^(none|minor|moderate)$")
    last_reviewed: Optional[str] = None

class DesignFrontmatter(BaseModel):
    """Frontmatter schema for design documents."""
    doc: str = Field(..., regex="^design$")
    component: str
    id: str
    version: str = Field(..., regex=r"^\d+\.\d+\.\d+$")
    status: str = Field(..., regex="^(draft|review|approved|deprecated)$")
    owners: List[str]
    last_reviewed: Optional[str] = None

FRONTMATTER_SCHEMAS = {
    "architecture": ArchitectureFrontmatter,
    "design": DesignFrontmatter
}

def validate_frontmatter(frontmatter: Dict, doc_type: str) -> List[str]:
    """Validate frontmatter against schema.

    Args:
        frontmatter: Frontmatter dictionary
        doc_type: Document type

    Returns:
        List of validation error messages (empty if valid)
    """
    schema = FRONTMATTER_SCHEMAS.get(doc_type)
    if not schema:
        return [f"Unknown document type: {doc_type}"]

    try:
        schema(**frontmatter)
        return []  # Valid
    except Exception as e:
        return [str(e)]
```

**Update Parser**:
```python
# src/processing/parser.py
from src.validation.frontmatter_validator import validate_frontmatter

def parse_file(self, file_path: str) -> ParsedDocument:
    # ...existing code...

    # Validate using shared validator
    errors = validate_frontmatter(frontmatter, doc_type)
    if errors:
        raise ValueError(f"Invalid frontmatter: {errors}")
```

**Update Validation Rule**:
```python
# src/validation/rules.py
from src.validation.frontmatter_validator import validate_frontmatter, FRONTMATTER_SCHEMAS

class DocumentStandardsRule(ValidationRule):
    def validate(self, request: Dict, context: ValidationContext):
        frontmatter = request["content"]["frontmatter"]
        target_type = request["target_type"]

        # Use shared validator
        errors = validate_frontmatter(frontmatter, target_type)

        violations = [
            Violation(
                code="DOC-001",
                message=error,
                severity="critical",
                field="frontmatter"
            )
            for error in errors
        ]

        return violations
```

**2. ID Property Mapping (Graph Operations)**:
```python
# src/graph/operations.py - Extract to constant

ID_PROPERTY_MAP = {
    NodeLabels.ARCHITECTURE: "id",
    NodeLabels.DESIGN: "id",
    NodeLabels.REQUIREMENT: "rid",
    NodeLabels.CODE_ARTIFACT: "path",
    NodeLabels.DECISION: "id",
    NodeLabels.AGENT_REQUEST: "id",
    NodeLabels.CHUNK: "id"
}

def get_id_property(label: str) -> str:
    """Get ID property name for node label."""
    return ID_PROPERTY_MAP.get(label, "id")
```

**Acceptance Criteria**:
- [ ] Shared frontmatter validator created
- [ ] Parser uses shared validator
- [ ] Validation rules use shared validator
- [ ] ID property mapping extracted
- [ ] Tests updated for shared code
- [ ] No duplication in validation logic

**Files to Create/Modify**:
- `src/validation/frontmatter_validator.py` - NEW FILE
- `src/processing/parser.py` - Use shared validator
- `src/validation/rules.py` - Use shared validator
- `src/graph/operations.py` - Extract ID mapping

---

### Task 3.2: Fix Deprecation Warnings [MEDIUM]
**Priority**: P2 - MEDIUM
**Estimated Effort**: 1 day
**Owner**: Backend Team

**Issues**:
1. Pydantic V2 deprecation warnings (Config → ConfigDict)
2. Print statements instead of logging
3. Incomplete type annotations

**1. Fix Pydantic Deprecations**:
```python
# BEFORE - src/processing/models.py
class ParsedDocument(BaseModel):
    path: str
    doc_type: str
    # ...

    class Config:  # ❌ DEPRECATED
        arbitrary_types_allowed = True

# AFTER
from pydantic import BaseModel, ConfigDict

class ParsedDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # ✅ Pydantic V2

    path: str
    doc_type: str
    # ...
```

**2. Replace Print Statements**:
```python
# BEFORE - src/validation/drift_detector.py:58
print(f"Error detecting design drift: {e}")

# AFTER
import logging
logger = logging.getLogger(__name__)

logger.error(f"Error detecting design drift: {e}", exc_info=True)
```

**Files with print() statements**:
- `src/validation/drift_detector.py:58,101,141`
- `src/validation/engine.py:106`
- `src/validation/audit.py:148`

**3. Fix Type Annotations**:
```python
# BEFORE - src/validation/engine.py:22
def __init__(self, graph_query: callable):  # ❌ Vague

# AFTER
from typing import Callable, List, Dict, Any

def __init__(self, graph_query: Callable[[str, Dict], List[Dict[str, Any]]]):  # ✅ Precise
```

**Acceptance Criteria**:
- [ ] All Pydantic models use ConfigDict
- [ ] No print() statements in production code
- [ ] All callables properly typed
- [ ] No deprecation warnings when running tests
- [ ] Linter (mypy) passes

**Files to Modify**:
- `src/processing/models.py` - Fix Config
- `src/graph/config.py` - Fix Config
- `src/validation/drift_detector.py` - Replace prints
- `src/validation/engine.py` - Replace prints, fix types
- `src/validation/audit.py` - Replace prints

---

### Task 3.3: Add Missing Documentation [MEDIUM]
**Priority**: P2 - MEDIUM
**Estimated Effort**: 1 day
**Owner**: Documentation Team

**Missing Documentation**:

**1. Magic Number Comments**:
```python
# src/processing/chunker.py
# BEFORE
chunk_size = 1000
chunk_overlap = 200
min_chunk_size = 100

# AFTER
# Chunk size optimized for:
# - nomic-embed-text context window (2048 tokens)
# - Semantic coherence (complete paragraphs)
# - Search granularity (not too small/large)
chunk_size = 1000  # tokens, ~750 words

# Overlap ensures context continuity between chunks
# - Prevents information loss at boundaries
# - Enables better semantic search
chunk_overlap = 200  # tokens, 20% of chunk_size

# Minimum chunk size to avoid tiny fragments
# - Ensures embeddings have enough context
# - Filters out headings/short sections
min_chunk_size = 100  # tokens, ~75 words
```

**2. Create ADR for Chunk Storage**:
```markdown
# docs/ADR/002-chunk-storage-strategy.md

# ADR-002: Chunk Storage Strategy

## Status
**Accepted** - 2024-11-10

## Context
Documents are split into chunks for semantic search. Decision needed on how to store chunks with embeddings in Neo4j.

## Decision
Store chunks as separate `Chunk` nodes with `CONTAINS` relationships from documents.

## Alternatives Considered
1. **Store embeddings as array properties on document nodes**
   - Rejected: Limits search granularity, can't return specific chunks
2. **Store chunks in separate vector database (Qdrant)**
   - Rejected: Adds complexity, sync issues between databases

## Consequences
- ✅ Fine-grained search results
- ✅ Chunk-level annotations possible
- ✅ Enables future chunk versioning
- ⚠️ More relationships to manage (acceptable)

## Implementation
See `src/integration/document_adapter.py` for chunk storage implementation.
```

**3. Production Runbook**:
```markdown
# docs/RUNBOOK.md - NEW FILE

# Librarian Agent Production Runbook

## Starting the System

### Prerequisites
1. Neo4j running on port 7687
2. Ollama running on port 11434
3. Environment variables configured (.env)

### Start API Server
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Verify Health
```bash
curl http://localhost:8000/health
# Should return {"status": "healthy", ...}
```

## Monitoring

### Health Checks
- **Liveness**: `GET /health/live` - Returns 200 if process alive
- **Readiness**: `GET /health/ready` - Returns 200 if all dependencies healthy
- **Detailed**: `GET /health` - Returns component status, system metrics

### Metrics
- **Application Metrics**: `GET /metrics`
- **Request Timing**: Check `X-Process-Time` response header

### Logs
Logs are JSON-formatted to stdout. Key fields:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (INFO, ERROR, etc.)
- `message`: Log message
- `duration_ms`: Request duration (if request log)

## Common Issues

### Neo4j Connection Failed
**Symptoms**: Health check shows neo4j: false
**Fix**:
1. Check Neo4j is running: `docker ps` or Neo4j Desktop
2. Verify connection string in `.env`
3. Check credentials

### Ollama Not Responding
**Symptoms**: Health check shows ollama: false
**Fix**:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Pull model if missing: `ollama pull nomic-embed-text`

### Vector Search Returns No Results
**Symptoms**: Semantic search returns empty results
**Fix**:
1. Check vector index exists in Neo4j
2. Verify chunks have embeddings
3. Check embedding dimensionality (768)

### Validation Always Fails
**Symptoms**: All documents rejected by validation
**Fix**:
1. Check frontmatter has all required fields
2. Verify document type mapping
3. Check validation rule configuration

## Backup & Recovery

### Backup Neo4j Database
```bash
# Stop Neo4j
# Copy data directory
cp -r /path/to/neo4j/data /backup/location/

# Or use Neo4j dump
neo4j-admin dump --database=neo4j --to=/backup/neo4j-backup.dump
```

### Restore Neo4j Database
```bash
# Stop Neo4j
# Restore data
neo4j-admin load --from=/backup/neo4j-backup.dump --database=neo4j --force
# Start Neo4j
```

## Performance Tuning

### Slow Validation
- Check graph query performance
- Add indexes for common queries
- Reduce validation rules if needed

### High Memory Usage
- Reduce chunk batch size in embedder
- Check for memory leaks in validation
- Monitor Neo4j memory settings

### Slow Embeddings
- Check Ollama is using GPU
- Reduce batch size if OOM
- Consider smaller embedding model
```

**Acceptance Criteria**:
- [ ] All magic numbers have comments
- [ ] ADR-002 created for chunk storage
- [ ] Production runbook created
- [ ] Deployment guide updated
- [ ] README links to new docs

**Files to Create/Modify**:
- `src/processing/chunker.py` - Add comments
- `src/graph/config.py` - Add comments
- `docs/ADR/002-chunk-storage-strategy.md` - NEW FILE
- `docs/RUNBOOK.md` - NEW FILE
- `docs/DEPLOYMENT.md` - Update
- `README.md` - Add links

---

## Week 4: Enhanced Testing

### Task 4.1: Comprehensive Test Coverage [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 2 days
**Owner**: QA Team

**Testing Gaps**:
1. Vector search integration tests (0 coverage)
2. Error recovery scenarios (minimal coverage)
3. Edge cases (large documents, malformed input)
4. Concurrent operations (0 coverage)

**Test Suites to Add**:

**1. Vector Search Tests**:
```python
# tests/test_vector_search.py - NEW FILE

import pytest
from src.graph.vector_ops import VectorOperations
from src.processing.embedder import EmbeddingGenerator

@pytest.mark.requires_neo4j
@pytest.mark.requires_ollama
class TestVectorSearch:
    async def test_store_and_retrieve_chunks(self, graph_ops, vector_ops):
        """Test storing chunks and retrieving via vector search."""
        # Given: Document with chunks
        chunks = [
            {"id": "chunk_1", "content": "Neo4j is a graph database", "embedding": [...]},
            {"id": "chunk_2", "content": "Vector search enables semantic similarity", "embedding": [...]},
            {"id": "chunk_3", "content": "Python is a programming language", "embedding": [...]}
        ]

        for chunk in chunks:
            await vector_ops.store_embedding("Chunk", chunk["id"], chunk["embedding"], "id")

        # When: Search for "graph database"
        embedder = EmbeddingGenerator()
        query_embedding = await embedder.embed_text("graph database")
        results = await vector_ops.semantic_search(query_embedding, limit=2)

        # Then: Should find chunk_1 first
        assert len(results) == 2
        assert results[0]["chunk_id"] == "chunk_1"
        assert results[0]["score"] > 0.7  # High similarity

    async def test_semantic_search_with_filter(self, vector_ops, embedder):
        """Test semantic search with document type filter."""
        # Given: Chunks from different document types
        # ...

        # When: Search with doc_type filter
        results = await vector_ops.semantic_search(
            query_embedding,
            limit=10,
            doc_type="architecture"
        )

        # Then: Only architecture chunks returned
        assert all(r["doc_type"] == "architecture" for r in results)

    async def test_search_no_results(self, vector_ops, embedder):
        """Test search when no similar documents exist."""
        # Given: Empty database
        # When: Search for something
        results = await vector_ops.semantic_search(
            query_embedding,
            limit=10
        )

        # Then: Returns empty list
        assert results == []

    async def test_embedding_dimensionality_validation(self, vector_ops):
        """Test that wrong dimensionality is rejected."""
        # Given: 384-dim embedding (wrong size)
        wrong_embedding = [0.1] * 384

        # When/Then: Should raise error
        with pytest.raises(ValueError, match="768 dimensions"):
            await vector_ops.store_embedding("Chunk", "test", wrong_embedding)
```

**2. Error Recovery Tests**:
```python
# tests/test_error_recovery.py - NEW FILE

@pytest.mark.asyncio
class TestErrorRecovery:
    async def test_neo4j_connection_failure(self, orchestrator):
        """Test handling when Neo4j is unavailable."""
        # Given: Neo4j connection closed
        await orchestrator.graph_ops.connection.close()

        # When: Try to process document
        result = await orchestrator.process_document("test.md")

        # Then: Returns error, doesn't crash
        assert result["success"] is False
        assert "neo4j" in result["error"].lower()

    async def test_ollama_failure_graceful_degradation(self, pipeline):
        """Test handling when Ollama is unavailable."""
        # Given: Ollama not running
        # When: Try to generate embeddings
        result = pipeline.process_file("test.md")

        # Then: Parsing succeeds, embedding fails gracefully
        assert "document" in result
        assert "processed_chunks" not in result
        assert result["error"] is not None

    async def test_validation_rule_exception_isolation(self, validator):
        """Test that one rule failure doesn't break others."""
        # Given: Validation rule that throws exception
        class BrokenRule(ValidationRule):
            def validate(self, request, context):
                raise RuntimeError("Rule broke!")

        validator.rules.append(BrokenRule())

        # When: Validate request
        result = await validator.validate_request(request, context)

        # Then: Other rules still execute
        assert len(result.violations) > 0  # Other rules ran
        # And: Broken rule logged but didn't crash
```

**3. Edge Case Tests**:
```python
# tests/test_edge_cases.py - NEW FILE

class TestEdgeCases:
    def test_very_large_document(self, parser, chunker):
        """Test processing document >1MB."""
        # Given: Large document (100K+ words)
        large_doc = "# Title\n" + ("word " * 100000)

        # When: Parse and chunk
        parsed = parser.parse_content(large_doc, "test.md")
        chunks = chunker.chunk_document(parsed)

        # Then: Successfully chunks without OOM
        assert len(chunks) > 100
        assert all(len(c.content) <= 1200 for c in chunks)  # Respects chunk size

    def test_document_with_no_sections(self, parser):
        """Test document without markdown sections."""
        # Given: Plain text, no headers
        content = "Just some plain text without any structure."

        # When: Parse
        parsed = parser.parse_content(content, "plain.md")

        # Then: Creates default section
        assert len(parsed.sections) == 1
        assert parsed.sections[0].title is None

    def test_malformed_frontmatter(self, parser):
        """Test document with invalid YAML."""
        # Given: Broken YAML
        content = """---
        invalid: yaml:
        missing: quotes "
        ---
        # Content
        """

        # When/Then: Raises clear error
        with pytest.raises(ValueError, match="frontmatter"):
            parser.parse_content(content, "test.md")

    def test_unicode_and_special_chars(self, parser, embedder):
        """Test handling of unicode and special characters."""
        # Given: Content with unicode
        content = "# 测试\n这是中文内容。émojis: 🔥 ✅"

        # When: Parse and embed
        parsed = parser.parse_content(content, "test.md")
        embedding = await embedder.embed_text(content)

        # Then: Handles correctly
        assert parsed.content == content
        assert len(embedding) == 768
```

**4. Concurrent Operation Tests**:
```python
# tests/test_concurrent.py - NEW FILE

import asyncio

@pytest.mark.asyncio
class TestConcurrent:
    async def test_concurrent_validations(self, validator):
        """Test validating multiple documents concurrently."""
        # Given: 10 validation requests
        requests = [create_request(i) for i in range(10)]

        # When: Validate concurrently
        results = await asyncio.gather(*[
            validator.validate_request(req, context)
            for req in requests
        ])

        # Then: All succeed
        assert len(results) == 10
        assert all(r.passed for r in results)

    async def test_concurrent_graph_writes(self, graph_ops):
        """Test concurrent node creation."""
        # Given: 20 nodes to create
        nodes = [{"id": f"node_{i}", "data": f"data_{i}"} for i in range(20)]

        # When: Create concurrently
        ids = await asyncio.gather(*[
            graph_ops.create_node("TestNode", node)
            for node in nodes
        ])

        # Then: All created with unique IDs
        assert len(ids) == 20
        assert len(set(ids)) == 20  # All unique

    async def test_connection_pool_under_load(self, graph_ops):
        """Test connection pool doesn't exhaust under load."""
        # Given: 100 concurrent queries
        # When: Execute all at once
        results = await asyncio.gather(*[
            graph_ops.query("MATCH (n) RETURN count(n) as count", {})
            for _ in range(100)
        ])

        # Then: All succeed
        assert len(results) == 100
        # And: Connection pool recovers
        assert await graph_ops.connection.health_check()
```

**Acceptance Criteria**:
- [ ] 20+ new vector search tests
- [ ] 10+ error recovery tests
- [ ] 15+ edge case tests
- [ ] 10+ concurrency tests
- [ ] Overall test coverage >90%
- [ ] All tests passing

**Files to Create**:
- `tests/test_vector_search.py` - NEW FILE
- `tests/test_error_recovery.py` - NEW FILE
- `tests/test_edge_cases.py` - NEW FILE
- `tests/test_concurrent.py` - NEW FILE

---

### Task 4.2: Performance Testing [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 2 days
**Owner**: Performance Team

**Performance Test Suite**:

**1. Load Testing**:
```python
# tests/performance/test_load.py - NEW FILE

import pytest
import time
import asyncio
from statistics import mean, median, stdev

@pytest.mark.performance
class TestLoad:
    async def test_validation_throughput(self, orchestrator):
        """Test validation throughput under load."""
        # Given: 100 documents to validate
        documents = [f"test_data/doc_{i}.md" for i in range(100)]

        # When: Process all documents
        start = time.time()
        results = await asyncio.gather(*[
            orchestrator.process_document(doc)
            for doc in documents
        ])
        duration = time.time() - start

        # Then: Measure performance
        throughput = len(documents) / duration

        print(f"\nValidation Throughput: {throughput:.2f} docs/sec")
        print(f"Total Time: {duration:.2f}s")
        print(f"Avg Time per Doc: {duration/len(documents):.2f}s")

        # Assert minimum throughput
        assert throughput >= 5  # At least 5 docs/sec

    async def test_semantic_search_latency(self, vector_ops, embedder):
        """Test semantic search latency."""
        # Given: 1000 chunks in database
        # ...populate database...

        # When: Execute 100 searches
        latencies = []
        for i in range(100):
            query_embedding = await embedder.embed_text(f"query {i}")

            start = time.time()
            results = await vector_ops.semantic_search(query_embedding, limit=10)
            latency = (time.time() - start) * 1000  # ms

            latencies.append(latency)

        # Then: Measure latency
        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[95]
        p99_latency = sorted(latencies)[99]

        print(f"\nSearch Latency:")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        # Assert acceptable latency
        assert avg_latency < 100  # <100ms average
        assert p95_latency < 200   # <200ms p95
```

**2. Stress Testing**:
```python
# tests/performance/test_stress.py - NEW FILE

@pytest.mark.stress
class TestStress:
    async def test_connection_pool_exhaustion(self, graph_ops):
        """Test behavior when connection pool exhausted."""
        # Given: Connection pool size = 50
        # When: Create 200 concurrent connections
        tasks = [
            graph_ops.query("MATCH (n) RETURN count(n)", {})
            for _ in range(200)
        ]

        # Then: All complete eventually (may queue)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # And: No permanent failures
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0

    async def test_large_batch_embedding(self, embedder):
        """Test embedding generation with large batches."""
        # Given: 1000 chunks to embed
        chunks = [f"Chunk {i} with some text content" for i in range(1000)]

        # When: Generate embeddings
        start = time.time()
        embeddings = await embedder.embed_texts(chunks)
        duration = time.time() - start

        # Then: All succeed
        assert len(embeddings) == 1000
        throughput = len(chunks) / duration

        print(f"\nEmbedding Throughput: {throughput:.2f} chunks/sec")

        # Should process at least 10 chunks/sec
        assert throughput >= 10

    async def test_memory_usage_large_documents(self, pipeline):
        """Test memory usage doesn't grow unbounded."""
        import psutil
        process = psutil.Process()

        # Given: 50 large documents (1MB each)
        # When: Process all sequentially
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        for i in range(50):
            large_doc = create_large_document(1024 * 1024)  # 1MB
            result = pipeline.process_file(large_doc)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print(f"\nMemory Growth: {memory_growth:.2f}MB")

        # Should not grow more than 500MB
        assert memory_growth < 500
```

**3. Profiling**:
```python
# tests/performance/test_profiling.py - NEW FILE

import cProfile
import pstats

@pytest.mark.profile
class TestProfiling:
    def test_profile_validation_engine(self, validator):
        """Profile validation engine to identify bottlenecks."""
        profiler = cProfile.Profile()

        # Profile validation
        profiler.enable()
        for i in range(100):
            result = await validator.validate_request(request, context)
        profiler.disable()

        # Print stats
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions

    def test_profile_graph_operations(self, graph_ops):
        """Profile graph operations."""
        profiler = cProfile.Profile()

        profiler.enable()
        for i in range(100):
            await graph_ops.create_node("Test", {"id": f"test_{i}"})
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
```

**Acceptance Criteria**:
- [ ] Load tests validate throughput targets
- [ ] Stress tests identify breaking points
- [ ] Memory profiling shows no leaks
- [ ] Performance baseline documented
- [ ] Bottlenecks identified and documented

**Files to Create**:
- `tests/performance/test_load.py` - NEW FILE
- `tests/performance/test_stress.py` - NEW FILE
- `tests/performance/test_profiling.py` - NEW FILE
- `docs/PERFORMANCE_BASELINE.md` - NEW FILE

---

### Task 4.3: End-to-End Testing [HIGH]
**Priority**: P1 - HIGH
**Estimated Effort**: 1 day
**Owner**: QA Team

**E2E Test Scenarios**:

```python
# tests/e2e/test_complete_flows.py - NEW FILE

@pytest.mark.e2e
class TestCompleteFlows:
    async def test_complete_document_ingestion_flow(self):
        """Test complete flow from file to searchable graph."""
        # Given: Fresh database and all services running
        # And: Sample architecture document
        doc_path = "test_data/sample_architecture.md"

        # When: Ingest document
        orchestrator = LibrarianOrchestrator(...)
        result = await orchestrator.process_document(doc_path)

        # Then: Document stored successfully
        assert result["success"] is True
        doc_id = result["node_id"]

        # And: Chunks created and stored
        assert result["chunk_count"] > 0

        # And: Document searchable by semantic query
        query = "system architecture overview"
        embedder = EmbeddingGenerator()
        query_embedding = await embedder.embed_text(query)

        vector_ops = VectorOperations(...)
        search_results = await vector_ops.semantic_search(query_embedding)

        assert len(search_results) > 0
        # Should find the document we just ingested
        found_doc_ids = [r["doc_id"] for r in search_results]
        assert doc_id in found_doc_ids

        # And: Audit trail created
        audit_storage = GraphAuditStorage(...)
        audit_trail = await audit_storage.get_audit_trail(doc_id)
        assert len(audit_trail) > 0
        assert any(a["event_type"] == "validation" for a in audit_trail)

    async def test_validation_rejection_flow(self):
        """Test flow when document fails validation."""
        # Given: Document with invalid frontmatter
        invalid_doc = """---
        doc: architecture
        # Missing required fields: id, version, etc.
        ---
        # Content
        """

        # When: Try to ingest
        result = await orchestrator.process_document(invalid_doc)

        # Then: Validation fails
        assert result["success"] is False
        assert "validation" in result
        assert result["validation"]["status"] == "revision_required"

        # And: No document node created
        # (verify no node in graph with this content)

        # And: Audit trail shows rejection
        # ...verify audit record...

    async def test_drift_detection_flow(self):
        """Test detecting drift between documents."""
        # Given: Architecture document ingested
        arch_result = await orchestrator.process_document("arch_v1.md")

        # And: Design document referencing old architecture version
        design_doc = """---
        doc: design
        id: DESIGN-001
        version: 1.0.0
        implements: ARCH-001@0.9.0  # Old version
        ---
        # Design
        """

        # When: Ingest design document
        design_result = await orchestrator.process_document(design_doc)

        # Then: Drift detected in validation
        assert "drift" in design_result.get("warnings", [])

        # When: Run drift detection
        drift_detector = DriftDetector(...)
        drift_report = await drift_detector.detect_all_drift()

        # Then: Design drift identified
        assert len(drift_report["design_drift"]) > 0

    async def test_concurrent_ingestion_no_conflicts(self):
        """Test concurrent document ingestion doesn't cause conflicts."""
        # Given: 10 different documents
        documents = [f"test_data/doc_{i}.md" for i in range(10)]

        # When: Ingest concurrently
        results = await asyncio.gather(*[
            orchestrator.process_document(doc)
            for doc in documents
        ])

        # Then: All succeed
        assert all(r["success"] for r in results)

        # And: All have unique IDs
        doc_ids = [r["node_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids))

        # And: All are searchable
        for doc_id in doc_ids:
            node = await graph_ops.get_node("Architecture", doc_id)
            assert node is not None
```

**Acceptance Criteria**:
- [ ] Complete ingestion flow tested
- [ ] Validation rejection flow tested
- [ ] Drift detection flow tested
- [ ] Concurrent ingestion tested
- [ ] All E2E tests passing

**Files to Create**:
- `tests/e2e/test_complete_flows.py` - NEW FILE
- `test_data/` - Add sample test documents

---

## Success Metrics

At the end of this sprint, success is measured by:

### Quality Metrics
- ✅ **100% Test Pass Rate** (currently 92.3%)
- ✅ **>90% Code Coverage** (estimated 85%)
- ✅ **0 Critical Security Issues** (currently 3)
- ✅ **0 Deprecation Warnings**

### Integration Metrics
- ✅ **Complete Document Flow** works end-to-end
- ✅ **Chunk Storage** implemented and tested
- ✅ **Audit Trail** persisted to graph
- ✅ **Vector Search** returns accurate results

### Production Readiness
- ✅ **Health Endpoints** comprehensive
- ✅ **Monitoring** in place (metrics, logging)
- ✅ **Documentation** complete (runbook, ADRs)
- ✅ **Performance** baseline established

---

## Risk Mitigation

### High-Risk Items
1. **Test Fixture Issues** may reveal deeper async problems
   - *Mitigation*: Fix incrementally, add async tests to CI

2. **Chunk Storage Decision** impacts future architecture
   - *Mitigation*: Document in ADR, make reversible if needed

3. **Performance** may not meet targets
   - *Mitigation*: Establish baseline first, optimize iteratively

### Dependencies
- **Neo4j availability** for graph tests
- **Ollama availability** for embedding tests
- **Hardware resources** for performance tests

---

## Timeline Summary

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **Week 1** | Critical Fixes | Test failures fixed, Security hardened, Integration validated |
| **Week 2** | Missing Features | Chunk storage implemented, Audit persistence complete, Monitoring added |
| **Week 3** | Code Quality | Duplication removed, Deprecations fixed, Documentation complete |
| **Week 4** | Enhanced Testing | Comprehensive tests, Performance baseline, E2E validation |

**Total Estimated Effort**: ~20 days (1 developer) or ~10 days (2 developers in parallel)

---

## Next Steps After Sprint

After completing this sprint, the system will be production-ready. Next priorities:

1. **Production Deployment**
   - Create Docker images
   - Setup CI/CD pipeline
   - Deploy to staging environment

2. **Operational Excellence**
   - Implement alerting (Prometheus/Grafana)
   - Add distributed tracing (OpenTelemetry)
   - Setup log aggregation (ELK/Loki)

3. **Feature Enhancements**
   - Code file parsers (Python, JavaScript)
   - Update detection system
   - Enhanced search (filters, facets)

4. **Scale Testing**
   - Test with 10K+ documents
   - Multi-tenant support
   - Horizontal scaling

---

## References
- Architecture Review: `reviews/architecture_compliance_review.md`
- Integration Review: `reviews/integration_review.md`
- Quality Review: `reviews/quality_review.md`
- Architecture Spec: `docs/architecture.md`
- CLAUDE Instructions: `CLAUDE.md`
