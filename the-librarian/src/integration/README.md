# Integration Layer

The integration layer connects the three core modules of the Librarian system:
- **Processing** (`src/processing/`) - Document parsing, chunking, and embedding
- **Validation** (`src/validation/`) - Rule-based document validation
- **Graph** (`src/graph/`) - Neo4j graph database operations

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LibrarianOrchestrator                │
│                                                          │
│  Coordinates complete document lifecycle:               │
│  Process → Validate → Store → Audit                     │
└────────────┬──────────────┬──────────────┬──────────────┘
             │              │              │
     ┌───────▼──────┐  ┌────▼─────┐  ┌────▼──────────┐
     │RequestAdapter│  │ValidationBridge│DocumentAdapter│
     │              │  │              │  │              │
     │ Doc→Request  │  │ Sync/Async  │  │ Doc→Graph    │
     └──────────────┘  └──────────────┘  └──────────────┘
```

## Components

### 1. DocumentGraphAdapter

Converts processing outputs to graph storage format.

**Key Methods:**
- `store_document(document, chunks)` - Store document with chunks and embeddings
- `update_document_embedding(document_id, embedding)` - Update document embedding
- `get_document_chunks(document_id)` - Retrieve all chunks for a document
- `document_exists(document_id, doc_type)` - Check if document exists

**Example:**
```python
from src.graph.connection import Neo4jConnection
from src.graph.operations import GraphOperations
from src.graph.vector_ops import VectorOperations
from src.integration.document_adapter import DocumentGraphAdapter

conn = Neo4jConnection(uri="neo4j://localhost:7687", user="neo4j", password="password")
graph_ops = GraphOperations(conn)
vector_ops = VectorOperations(conn)

adapter = DocumentGraphAdapter(graph_ops, vector_ops)

# Store document
doc_id = await adapter.store_document(
    document=parsed_document,
    chunks=processed_chunks
)
```

### 2. ValidationGraphBridge

Bridges synchronous validation with async graph operations.

**Key Methods:**
- `query_sync(cypher, params)` - Execute graph query synchronously
- `store_validation_result(request, result)` - Store validation as audit trail
- `get_validation_history(target_id)` - Get validation history for document
- `get_recent_approvals(agent_id)` - Get recent approved requests

**Example:**
```python
from src.integration.validation_bridge import ValidationGraphBridge

bridge = ValidationGraphBridge(graph_ops)

# Query from sync validation rule
result = bridge.query_sync(
    "MATCH (a:Architecture {id: $id}) RETURN a",
    {"id": "ARCH-001"}
)

# Store validation result
decision_id = await bridge.store_validation_result(
    request=agent_request,
    result=validation_result
)
```

### 3. RequestAdapter

Converts documents to validation request format.

**Key Methods:**
- `document_to_request(document, agent_id, action)` - Convert document to AgentRequest
- `extract_validation_metadata(document)` - Extract validation-relevant metadata

**Example:**
```python
from src.integration.request_adapter import RequestAdapter

adapter = RequestAdapter()

# Convert document to validation request
request = adapter.document_to_request(
    document=parsed_document,
    agent_id="ingestion_pipeline",
    action="create"
)

# Now validate the request
validation_result = await validation_engine.validate_request(
    request=request.to_dict(),
    context={}
)
```

### 4. LibrarianOrchestrator

Main orchestrator for end-to-end document processing.

**Key Methods:**
- `process_document(file_path, skip_validation, force_update)` - Process single document
- `process_directory(directory, pattern)` - Process all documents in directory
- `update_document(file_path)` - Update existing document
- `validate_setup()` - Validate all components are configured

**Example:**
```python
from src.integration.orchestrator import LibrarianOrchestrator

orchestrator = LibrarianOrchestrator(neo4j_connection)

# Process single document
result = await orchestrator.process_document(
    file_path="docs/ARCH-001.md",
    skip_validation=False,
    force_update=False
)

if result.success:
    print(f"Document stored: {result.document_id}")
    print(f"Chunks: {result.chunks_stored}")
else:
    print(f"Failed: {result.error}")
```

### 5. AsyncSync Utilities

Handles async/sync boundaries for cross-module compatibility.

**Key Methods:**
- `AsyncSync.run_sync(coro)` - Run coroutine synchronously
- `AsyncSync.run_async(func, *args)` - Run sync function asynchronously
- `AsyncSync.make_sync(async_func)` - Decorator to make async function callable synchronously
- `AsyncSync.make_async(sync_func)` - Decorator to make sync function awaitable

**Example:**
```python
from src.integration.async_utils import AsyncSync

# Run async code from sync context
result = AsyncSync.run_sync(some_async_function())

# Use decorator
@AsyncSync.make_sync
async def process_data(data):
    return await async_operation(data)

# Can now call synchronously
result = process_data(my_data)
```

## Complete Flow Example

Here's how a document flows through the system:

```python
import asyncio
from src.graph.connection import Neo4jConnection
from src.integration.orchestrator import LibrarianOrchestrator

async def main():
    # 1. Connect to Neo4j
    conn = Neo4jConnection(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="password"
    )

    # 2. Create orchestrator
    orchestrator = LibrarianOrchestrator(conn)

    # 3. Validate setup
    setup = await orchestrator.validate_setup()
    if not setup['overall']:
        print("Setup validation failed!")
        return

    # 4. Process document
    result = await orchestrator.process_document(
        file_path="docs/ARCH-001.md",
        skip_validation=False
    )

    # 5. Check result
    if result.success:
        print(f"✓ Success: {result.document_id}")
        print(f"  Chunks: {result.chunks_stored}")
        print(f"  Status: {result.validation_result.status.value}")
    else:
        print(f"✗ Failed: {result.error}")
        if result.validation_result:
            for v in result.validation_result.violations:
                print(f"  - {v.severity.value}: {v.message}")

    # 6. Cleanup
    await conn.close()

asyncio.run(main())
```

## Data Flow

### Document Processing Flow

```
1. File → IngestionPipeline
   ├─ Parser: Markdown → ParsedDocument
   ├─ Chunker: ParsedDocument → List[Chunk]
   └─ Embedder: List[Chunk] → List[ProcessedChunk]

2. ParsedDocument → RequestAdapter → AgentRequest

3. AgentRequest → ValidationEngine → ValidationResult
   └─ Runs validation rules in parallel

4. If approved:
   ├─ DocumentGraphAdapter stores document + chunks
   └─ ValidationGraphBridge stores audit trail

5. Returns OrchestrationResult with status
```

### Graph Storage Format

**Document Node (Architecture/Design):**
```cypher
(doc:Architecture {
  id: "ARCH-001",
  title: "System Architecture",
  content: "...",
  content_hash: "abc123...",
  status: "approved",
  version: "1.0.0",
  embedding: [0.1, 0.2, ...],  // 768 dimensions
  created_at: "2024-01-01T00:00:00Z"
})
```

**Chunk Node:**
```cypher
(chunk:Chunk {
  id: "chunk_abc123",
  content: "...",
  doc_type: "architecture",
  section_title: "Overview",
  chunk_index: 0,
  embedding: [0.3, 0.4, ...],  // 768 dimensions
  created_at: "2024-01-01T00:00:00Z"
})
```

**Relationships:**
```cypher
(doc)-[:REFERENCES {chunk_index: 0, relationship_type: "CONTAINS"}]->(chunk)
```

**Audit Trail:**
```cypher
(request:AgentRequest)-[:RESULTED_IN]->(decision:Decision)
(decision)-[:APPROVES]->(doc:Architecture)
```

## Testing

Run integration tests:

```bash
# Unit tests (no dependencies)
pytest tests/test_integration.py -k "not integration" -v

# Integration tests (requires Neo4j)
pytest tests/test_integration.py -k "integration" -v

# All tests
pytest tests/test_integration.py -v
```

## Dependencies

- `nest-asyncio==1.5.8` - Handles nested event loops
- `ollama==0.1.6` - Embedding generation
- `neo4j==5.14.0` - Graph database driver
- `pydantic==2.5.0` - Data validation

## Configuration

The integration layer uses the same configuration as individual modules:

**Environment Variables:**
- `NEO4J_URI` - Neo4j connection URI
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)

**Neo4j Setup:**

The integration layer requires these Neo4j indexes:
- Unique constraints on `id` properties
- Vector indexes on `embedding` properties
- Composite indexes for common queries

Run schema setup:
```python
from src.graph.connection import Neo4jConnection
from src.graph.schema import SchemaManager

conn = Neo4jConnection(uri="neo4j://localhost:7687", user="neo4j", password="password")
schema = SchemaManager(conn)
await schema.create_all_indexes(vector_dimensions=768)
```

## Error Handling

The integration layer provides comprehensive error handling:

1. **Processing Errors**: Caught in `process_file()`, returned in result
2. **Validation Errors**: Returned as `ValidationResult` with violations
3. **Storage Errors**: Caught and logged, returned in `OrchestrationResult`
4. **Async/Sync Errors**: Handled by `AsyncSync` utilities

All errors are logged with full stack traces for debugging.

## Performance Considerations

- **Parallel Validation**: Rules run concurrently using `asyncio.gather()`
- **Batch Embeddings**: Embeddings processed in batches (default: 10)
- **Connection Pooling**: Neo4j driver uses connection pooling
- **Lazy Loading**: Components initialized on first use

## Future Enhancements

Planned improvements:
1. Retry logic for transient failures
2. Progress callbacks for long-running operations
3. Parallel document processing
4. Caching layer for frequently accessed data
5. Metrics collection and monitoring

## See Also

- [Processing Module](../processing/README.md)
- [Validation Module](../validation/README.md)
- [Graph Module](../graph/README.md)
- [Integration Example](../../examples/integration_example.py)
