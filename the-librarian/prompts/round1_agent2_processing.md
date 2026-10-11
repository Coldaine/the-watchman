# Agent 2: Document Processing Specialist

## Your Mission
You are building the document processing pipeline for the Librarian Agent system. This module parses documents, chunks text intelligently, and generates embeddings using Ollama.

## Context
You are working in parallel with:
- Agent 1: Building graph operations (will store your embeddings)
- Agent 3: Building validation engine (will validate your parsed documents)

## Required Reading
1. `docs/architecture.md` - Focus on Data Model section
2. `docs/subdomains/document-processing.md` - Your primary specification
3. `docs/ADR/001-technology-stack-and-architecture-decisions.md` - Embedding model details

## What to Build

### 1. Document Parser (`src/processing/parser.py`)
```python
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ParsedDocument(BaseModel):
    path: str
    doc_type: str  # architecture | design | tasks | research
    content: str
    frontmatter: Dict[str, Any]
    metadata: Dict[str, Any]

class DocumentParser:
    def parse_markdown(self, file_path: Path) -> ParsedDocument:
        # Extract YAML frontmatter (between --- markers)
        # Parse markdown content
        # Detect document type from frontmatter
        # Validate required fields based on doc_type

    def extract_frontmatter(self, content: str) -> tuple[dict, str]:
        # Split frontmatter from content
        # Parse YAML safely
        # Return (frontmatter_dict, remaining_content)

    def validate_frontmatter(self, doc_type: str, frontmatter: dict) -> bool:
        # Check required fields from spec:
        # All docs need: doc, subsystem, id, version, status, owners
        # Architecture needs: compliance_level, drift_tolerance
```

### 2. Text Chunker (`src/processing/chunker.py`)
```python
from typing import List, Tuple
import tiktoken

class Chunk(BaseModel):
    content: str
    start_index: int
    end_index: int
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None

class TextChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")

    def chunk_document(self, document: ParsedDocument) -> List[Chunk]:
        # Smart chunking that preserves:
        # - Paragraph boundaries
        # - Code block integrity
        # - Header hierarchy
        # Return chunks with parent-child relationships

    def chunk_by_tokens(self, text: str) -> List[Chunk]:
        # Chunk by token count with overlap
        # Preserve semantic boundaries

    def create_parent_child_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        # Create hierarchical chunks
        # Parent chunks = larger context
        # Child chunks = detailed segments
```

### 3. Embedding Generator (`src/processing/embedder.py`)
```python
import ollama
import numpy as np
from typing import List, Dict
import asyncio

class EmbeddingGenerator:
    def __init__(self, model: str = "nomic-embed-text", dimension: int = 768):
        self.model = model
        self.dimension = dimension
        self.client = ollama.Client(host="http://localhost:11434")

    async def generate_embedding(self, text: str) -> List[float]:
        # Call Ollama API
        # Return 768-dimensional vector
        response = await self.client.embeddings(
            model=self.model,
            prompt=text
        )
        return response['embedding']

    async def batch_embed(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        # Process in batches for efficiency
        # Handle rate limiting
        # Return list of embeddings

    def validate_embedding(self, embedding: List[float]) -> bool:
        # Check dimension = 768
        # Check all values are floats
        # Check reasonable magnitude
```

### 4. Ingestion Pipeline (`src/processing/pipeline.py`)
```python
class IngestionPipeline:
    def __init__(self, parser: DocumentParser, chunker: TextChunker, embedder: EmbeddingGenerator):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder

    async def ingest_document(self, file_path: Path) -> Dict:
        # 1. Parse document
        # 2. Chunk text
        # 3. Generate embeddings
        # 4. Return structured data ready for storage

        parsed = self.parser.parse_markdown(file_path)
        chunks = self.chunker.chunk_document(parsed)

        # Generate embeddings for each chunk
        embeddings = await self.embedder.batch_embed(
            [chunk.content for chunk in chunks]
        )

        return {
            "document": parsed,
            "chunks": chunks,
            "embeddings": embeddings
        }

    async def ingest_directory(self, directory: Path, pattern: str = "**/*.md"):
        # Process all matching files
        # Handle errors gracefully
        # Return ingestion report
```

### 5. Models (`src/processing/models.py`)
```python
# Define all processing-related models
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Document(BaseModel):
    path: str
    doc_type: str
    content: str
    frontmatter: Dict[str, Any]
    hash: str  # Content hash for change detection

class ProcessedChunk(BaseModel):
    id: str
    document_id: str
    content: str
    embedding: List[float] = Field(..., min_items=768, max_items=768)
    metadata: Dict[str, Any]
    position: int
```

## Interface Contract for Other Agents

Create `src/processing/__init__.py`:
```python
from .parser import DocumentParser, ParsedDocument
from .chunker import TextChunker, Chunk
from .embedder import EmbeddingGenerator
from .pipeline import IngestionPipeline

__all__ = [
    'DocumentParser',
    'ParsedDocument',
    'TextChunker',
    'Chunk',
    'EmbeddingGenerator',
    'IngestionPipeline'
]
```

## Testing Requirements

Create `tests/test_processing.py`:
1. Test frontmatter extraction from real markdown files
2. Test chunking preserves boundaries
3. Test embedding generation with Ollama (must be running)
4. Test full pipeline with sample document
5. Test error handling for invalid documents

## Success Criteria

1. **Parses Real Documents**: Can parse docs/architecture.md successfully
2. **Generates Real Embeddings**: Ollama produces 768-dim vectors
3. **Smart Chunking**: Respects paragraph/code boundaries
4. **Batch Processing**: Can process multiple documents efficiently
5. **Full Pipeline Works**: End-to-end ingestion produces valid output

## Dependencies to Add to requirements.txt
```
ollama==0.1.7
tiktoken==0.5.1
pyyaml==6.0.1
numpy==1.24.3
```

## Coordination File

Write your status to `coordination.json`:
```json
{
  "agent2_processing": {
    "status": "working|complete",
    "interfaces_ready": ["DocumentParser", "IngestionPipeline"],
    "blockers": []
  }
}
```

## Start Now
Begin by setting up Ollama connection and verifying you can generate embeddings. Then build the parser for markdown files with YAML frontmatter. Test with actual files from the docs/ directory.