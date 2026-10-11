# Document Processing Pipeline

Complete document ingestion pipeline for the Librarian Agent system. Parses markdown documents, chunks text intelligently, and generates embeddings using Ollama.

## Components

### 1. DocumentParser (`parser.py`)

Parses markdown files with YAML frontmatter.

**Features:**
- Extracts and validates frontmatter based on `doc_type`
- Parses markdown structure (headers, sections)
- Extracts code blocks and links
- Validates required fields for different document types

**Required Frontmatter Fields:**

All documents:
- `doc`: Document type (architecture, design, tasks, research, code)
- `subsystem`: Component area
- `id`: Unique identifier
- `version`: Semantic version
- `status`: draft | review | approved | deprecated
- `owners`: List of owner handles

Architecture documents also require:
- `compliance_level`: strict | flexible | advisory
- `drift_tolerance`: none | minor | moderate

**Usage:**
```python
from src.processing import DocumentParser

parser = DocumentParser()
doc = parser.parse('docs/architecture.md')

print(f"Type: {doc.doc_type}")
print(f"ID: {doc.frontmatter['id']}")
print(f"Sections: {len(doc.sections)}")
```

### 2. TextChunker (`chunker.py`)

Chunks documents intelligently while preserving semantic boundaries.

**Features:**
- Multiple chunking strategies based on document type
- Preserves paragraph boundaries and code blocks
- Maintains header hierarchy
- Uses tiktoken for accurate token counting
- Configurable chunk size and overlap

**Chunking Strategies:**
- **Architecture/Design**: By sections
- **Code**: By components (functions/classes)
- **Other**: Sliding window with overlap

**Usage:**
```python
from src.processing import TextChunker

chunker = TextChunker(
    chunk_size=1000,      # Target tokens per chunk
    chunk_overlap=200,    # Overlapping tokens
    min_chunk_size=100    # Minimum chunk size
)

chunks = chunker.chunk_document(parsed_doc)

for chunk in chunks:
    print(f"Section: {chunk.section_title}")
    print(f"Tokens: {chunker.count_tokens(chunk.content)}")
```

### 3. EmbeddingGenerator (`embedder.py`)

Generates 768-dimensional embeddings using Ollama's nomic-embed-text model.

**Features:**
- Connects to local Ollama instance
- Batch processing for efficiency
- Embedding validation
- Context-aware text preparation

**Requirements:**
- Ollama running at http://localhost:11434
- nomic-embed-text model pulled

**Setup:**
```bash
# Install Ollama
# Windows: Download from ollama.ai/download

# Start Ollama
ollama serve

# Pull embedding model
ollama pull nomic-embed-text
```

**Usage:**
```python
from src.processing import EmbeddingGenerator

embedder = EmbeddingGenerator()

# Check setup
if embedder.check_connection():
    if embedder.check_model_available():
        # Generate embedding
        embedding = embedder.generate_embedding("Test text")
        print(f"Dimensions: {len(embedding)}")  # 768
```

### 4. IngestionPipeline (`pipeline.py`)

Complete pipeline combining parser, chunker, and embedder.

**Features:**
- Process single files or entire directories
- Error handling and recovery
- Validation and setup checking
- Batch processing with reports

**Usage:**
```python
from src.processing import IngestionPipeline

pipeline = IngestionPipeline()

# Validate setup
validation = pipeline.validate_setup()
if not validation['success']:
    print(f"Errors: {validation['errors']}")

# Process single file
result = pipeline.process_file('docs/architecture.md')

if result['success']:
    document = result['document']
    chunks = result['processed_chunks']  # With embeddings

    print(f"Created {len(chunks)} chunks")

# Process directory
report = pipeline.process_directory(
    'docs',
    pattern='**/*.md',
    recursive=True
)

print(f"Processed: {report.success_count}/{report.total_files}")
```

## Data Models

All data models are defined in `models.py`:

- **Document**: Base document with path, content, frontmatter, hash
- **ParsedDocument**: Extends Document with metadata and sections
- **Chunk**: Text chunk with position, metadata, section info
- **ProcessedChunk**: Chunk with 768-dim embedding vector
- **IngestionResult**: Result of processing a single file
- **IngestionReport**: Report of batch processing operation

## Installation

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Testing

```bash
# Run all tests
pytest tests/test_processing.py -v

# Run specific test
pytest tests/test_processing.py::TestDocumentParser::test_parse_architecture_document -v

# Skip Ollama-dependent tests
pytest tests/test_processing.py -v -m "not ollama"
```

## Demo

```bash
# Run demo script
python demo_processing.py
```

The demo will:
1. Parse the architecture document
2. Chunk it into semantic units
3. Generate embeddings (if Ollama is running)
4. Show processing statistics

## Configuration

Default configuration:

```python
# Chunking
chunk_size = 1000        # tokens
chunk_overlap = 200      # tokens
min_chunk_size = 100     # tokens

# Embedding
host = "http://localhost:11434"
model_name = "nomic-embed-text"
embedding_dim = 768
batch_size = 10
```

## Error Handling

The pipeline handles common errors:

**Missing frontmatter:**
```
ValueError: Missing required frontmatter fields: ['id', 'version']
```

**Ollama not running:**
```
Cannot connect to Ollama at http://localhost:11434
```

**Model not available:**
```
Model nomic-embed-text not found. Run: ollama pull nomic-embed-text
```

**Invalid embedding dimensions:**
```
ValueError: Expected 768 dimensions, got 384
```

## Next Steps

Once documents are processed, the processed chunks should be:
1. Stored in Neo4j as nodes with embeddings
2. Indexed for vector similarity search
3. Linked to related documents and requirements
4. Made available for agent context retrieval

See `docs/subdomains/graph-operations.md` for storage implementation.

## Reference

- **Specification**: `docs/subdomains/document-processing.md`
- **Architecture**: `docs/architecture.md`
- **ADR**: `docs/ADR/001-technology-stack-and-architecture-decisions.md`
