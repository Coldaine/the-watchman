# Fix Agent 2: Integration Adapters

## Priority: HIGH - Build Adapters to Connect Modules

## Your Mission
Create the missing adapter layer that allows the three modules to work together.

## Required Adapters

### 1. Document-to-Graph Adapter (`src/integration/document_adapter.py`)

```python
from src.processing.models import ParsedDocument, ProcessedChunk
from src.graph.operations import GraphOperations

class DocumentGraphAdapter:
    """Converts processing output to graph storage"""

    async def store_document(self,
                            document: ParsedDocument,
                            chunks: List[ProcessedChunk]) -> str:
        """
        1. Create document node from ParsedDocument
        2. Create chunk nodes with embeddings
        3. Create CONTAINS relationships
        4. Return document node ID
        """

    async def store_chunk_embeddings(self,
                                    chunks: List[ProcessedChunk],
                                    doc_id: str):
        """Store chunk nodes with vector embeddings"""
```

### 2. Validation-Graph Bridge (`src/integration/validation_bridge.py`)

```python
class ValidationGraphBridge:
    """Bridges async graph with validation engine"""

    def __init__(self, graph_ops: GraphOperations):
        self.graph = graph_ops

    def query_sync(self, cypher: str, params: dict = None) -> List[dict]:
        """Synchronous wrapper for async graph queries"""
        # Use asyncio.run() or loop.run_until_complete()

    async def store_validation_result(self,
                                     request: AgentRequest,
                                     result: ValidationResult):
        """Store validation in graph as audit trail"""
```

### 3. Processing-to-Validation Adapter (`src/integration/request_adapter.py`)

```python
from src.processing.models import ParsedDocument
from src.validation.agent_models import AgentRequest

class RequestAdapter:
    """Converts documents to validation requests"""

    def document_to_request(self,
                           document: ParsedDocument,
                           agent_id: str,
                           action: str = "create") -> AgentRequest:
        """
        Convert ParsedDocument to AgentRequest format
        Map frontmatter to request metadata
        """

    def extract_context(self, document: ParsedDocument) -> dict:
        """Extract validation context from document"""
```

### 4. Main Orchestrator (`src/integration/orchestrator.py`)

```python
class LibrarianOrchestrator:
    """Orchestrates the complete flow"""

    def __init__(self):
        self.graph = GraphOperations()
        self.processor = IngestionPipeline()
        self.validator = ValidationEngine()
        self.doc_adapter = DocumentGraphAdapter()
        self.val_bridge = ValidationGraphBridge()

    async def process_document(self, file_path: str):
        """Complete flow: parse → chunk → embed → validate → store"""

        # 1. Process document
        result = await self.processor.process_file(file_path)

        # 2. Validate
        request = self.request_adapter.document_to_request(result['document'])
        validation = await self.validator.validate_request(request)

        # 3. Store if approved
        if validation.status == "approved":
            doc_id = await self.doc_adapter.store_document(
                result['document'],
                result['processed_chunks']
            )

        # 4. Audit trail
        await self.val_bridge.store_validation_result(request, validation)

        return doc_id
```

### 5. Sync/Async Utilities (`src/integration/async_utils.py`)

```python
import asyncio
from typing import Coroutine, Any

class AsyncSync:
    """Utilities for async/sync interop"""

    @staticmethod
    def run_sync(coro: Coroutine) -> Any:
        """Run async function synchronously"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Handle nested event loop
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(coro)
```

## Testing

Create `tests/test_integration.py`:
```python
# Test complete flow
async def test_end_to_end_flow():
    orchestrator = LibrarianOrchestrator()
    doc_id = await orchestrator.process_document("docs/architecture.md")
    assert doc_id is not None
    # Verify in graph
    # Verify audit trail
```

## Success Criteria

1. Can process document end-to-end
2. Embeddings stored in graph
3. Validation results in audit trail
4. All async/sync boundaries handled
5. No data loss between modules

## Dependencies to Add
```
nest-asyncio==1.5.8  # For async/sync interop
```

Start with the DocumentGraphAdapter as it's needed for basic storage functionality.