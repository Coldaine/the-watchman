# Document Processing Pipeline

## Overview
The Document Processing subdomain handles the ingestion, parsing, chunking, embedding, and storage of all documentation types. It transforms raw documents into graph nodes with embeddings, maintaining relationships and metadata for efficient retrieval and governance.

## Core Concepts

### Document Types
- **Architecture Documents**: High-level system design specifications
- **Design Documents**: Component-level implementation details
- **Code Files**: Source code with annotations and docstrings
- **Task Documents**: Sprint plans and work items
- **Research Documents**: Analysis and decision records

### Processing Stages
1. **Discovery**: Find new or modified documents
2. **Extraction**: Parse content and metadata
3. **Chunking**: Split into semantic units
4. **Embedding**: Generate vector representations
5. **Storage**: Create/update graph nodes
6. **Indexing**: Update search indexes

### Update Strategies
- **Full Ingestion**: Complete document processing
- **Incremental Update**: Process only changes
- **Selective Refresh**: Update specific sections
- **Bulk Migration**: Mass document import

## Implementation Details

### Document Parser Architecture

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import frontmatter
import markdown
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    """Unified document representation"""
    # Identity
    path: str
    doc_type: str
    format: str  # markdown|python|yaml|json

    # Content
    raw_content: str
    frontmatter: Dict
    sections: List['DocumentSection']
    code_blocks: List['CodeBlock']

    # Metadata
    hash: str
    size_bytes: int
    modified_at: datetime
    encoding: str

    # Relationships
    references: List[str]  # Other doc IDs referenced
    links: List[str]       # External URLs

class DocumentParser(ABC):
    """Base parser interface"""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if parser handles this file type"""
        pass

    @abstractmethod
    def parse(self, content: str, path: str) -> ParsedDocument:
        """Parse document into structured format"""
        pass

    @abstractmethod
    def extract_metadata(self, content: str) -> Dict:
        """Extract document metadata"""
        pass
```

### Markdown Document Parser

```python
class MarkdownParser(DocumentParser):
    """Parser for markdown documents with frontmatter"""

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith('.md')

    def parse(self, content: str, path: str) -> ParsedDocument:
        # Parse frontmatter and content
        post = frontmatter.loads(content)

        # Extract sections based on headers
        sections = self._extract_sections(post.content)

        # Extract code blocks
        code_blocks = self._extract_code_blocks(post.content)

        # Extract references
        references = self._extract_references(post.content)

        return ParsedDocument(
            path=path,
            doc_type=post.metadata.get('doc', 'unknown'),
            format='markdown',
            raw_content=content,
            frontmatter=post.metadata,
            sections=sections,
            code_blocks=code_blocks,
            hash=hashlib.sha256(content.encode()).hexdigest(),
            size_bytes=len(content.encode()),
            modified_at=datetime.fromtimestamp(os.path.getmtime(path)),
            encoding='utf-8',
            references=references,
            links=self._extract_links(post.content)
        )

    def _extract_sections(self, content: str) -> List[DocumentSection]:
        """Split document into semantic sections"""

        sections = []
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    sections.append(DocumentSection(
                        level=current_section['level'],
                        title=current_section['title'],
                        content='\n'.join(current_content).strip()
                    ))

                # Start new section
                level = len(line) - len(line.lstrip('#'))
                title = line.strip('#').strip()
                current_section = {'level': level, 'title': title}
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append(DocumentSection(
                level=current_section['level'],
                title=current_section['title'],
                content='\n'.join(current_content).strip()
            ))

        return sections
```

### Code File Parser

```python
class PythonParser(DocumentParser):
    """Parser for Python source files"""

    def can_parse(self, file_path: str) -> bool:
        return file_path.endswith('.py')

    def parse(self, content: str, path: str) -> ParsedDocument:
        import ast

        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return self._create_error_document(path, content, str(e))

        # Extract components
        classes = self._extract_classes(tree)
        functions = self._extract_functions(tree)
        imports = self._extract_imports(tree)
        docstrings = self._extract_docstrings(tree)

        # Create sections from components
        sections = []
        if imports:
            sections.append(DocumentSection(
                level=1,
                title="Imports",
                content='\n'.join(imports)
            ))

        for cls in classes:
            sections.append(DocumentSection(
                level=1,
                title=f"Class: {cls.name}",
                content=cls.docstring or "No documentation"
            ))

        for func in functions:
            sections.append(DocumentSection(
                level=1,
                title=f"Function: {func.name}",
                content=func.docstring or "No documentation"
            ))

        return ParsedDocument(
            path=path,
            doc_type='code',
            format='python',
            raw_content=content,
            frontmatter={'language': 'python', 'type': 'source'},
            sections=sections,
            code_blocks=[CodeBlock(
                language='python',
                content=content,
                line_start=1,
                line_end=len(content.split('\n'))
            )],
            hash=hashlib.sha256(content.encode()).hexdigest(),
            size_bytes=len(content.encode()),
            modified_at=datetime.fromtimestamp(os.path.getmtime(path)),
            encoding='utf-8',
            references=self._extract_module_references(imports),
            links=[]
        )
```

### Chunking Strategy

```python
class DocumentChunker:
    """Split documents into embedding-ready chunks"""

    def __init__(self,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, doc: ParsedDocument) -> List[Chunk]:
        """Create chunks with metadata"""

        chunks = []

        if doc.doc_type in ['architecture', 'design']:
            # Chunk by sections for structured docs
            chunks = self._chunk_by_sections(doc)

        elif doc.doc_type == 'code':
            # Chunk by functions/classes for code
            chunks = self._chunk_by_components(doc)

        else:
            # Default: sliding window chunking
            chunks = self._chunk_by_sliding_window(doc)

        # Add document metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata = {
                'doc_id': doc.frontmatter.get('id'),
                'doc_type': doc.doc_type,
                'doc_path': doc.path,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'version': doc.frontmatter.get('version'),
                'subsystem': doc.frontmatter.get('subsystem'),
                'hash': hashlib.md5(chunk.content.encode()).hexdigest()
            }

        return chunks

    def _chunk_by_sections(self, doc: ParsedDocument) -> List[Chunk]:
        """Chunk structured documents by sections"""

        chunks = []

        for section in doc.sections:
            # Skip empty sections
            if not section.content.strip():
                continue

            # If section is too large, split it
            if len(section.content) > self.chunk_size:
                sub_chunks = self._split_text(
                    section.content,
                    self.chunk_size,
                    self.chunk_overlap
                )

                for sub_content in sub_chunks:
                    chunks.append(Chunk(
                        content=f"# {section.title}\n\n{sub_content}",
                        section_title=section.title,
                        section_level=section.level
                    ))
            else:
                # Keep section as single chunk
                chunks.append(Chunk(
                    content=f"# {section.title}\n\n{section.content}",
                    section_title=section.title,
                    section_level=section.level
                ))

        return chunks

    def _chunk_by_components(self, doc: ParsedDocument) -> List[Chunk]:
        """Chunk code by logical components"""

        chunks = []

        for section in doc.sections:
            # Each function/class becomes a chunk
            chunks.append(Chunk(
                content=section.content,
                section_title=section.title,
                section_level=section.level,
                is_code=True
            ))

        return chunks
```

### Embedding Generator

```python
class EmbeddingGenerator:
    """Generate vector embeddings for chunks"""

    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
        self.embedding_dim = 768
        self.ollama_client = OllamaClient()

    async def generate_embeddings(self, chunks: List[Chunk]) -> List[np.ndarray]:
        """Generate embeddings for all chunks"""

        embeddings = []

        # Batch process for efficiency
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Prepare texts
            texts = [self._prepare_text(chunk) for chunk in batch]

            # Generate embeddings
            batch_embeddings = await self.ollama_client.embed_batch(
                model=self.model_name,
                texts=texts
            )

            embeddings.extend(batch_embeddings)

        return embeddings

    def _prepare_text(self, chunk: Chunk) -> str:
        """Prepare chunk text for embedding"""

        # Add metadata context to improve embedding quality
        if chunk.metadata.get('doc_type') == 'architecture':
            prefix = "Architecture specification: "
        elif chunk.metadata.get('doc_type') == 'design':
            prefix = "Design document: "
        elif chunk.metadata.get('doc_type') == 'code':
            prefix = "Source code: "
        else:
            prefix = ""

        # Include section title for context
        if chunk.section_title:
            text = f"{prefix}{chunk.section_title}\n{chunk.content}"
        else:
            text = f"{prefix}{chunk.content}"

        # Truncate if too long
        max_length = 8192  # Model's max context
        if len(text) > max_length:
            text = text[:max_length]

        return text
```

### Storage Pipeline

```python
class DocumentStorage:
    """Store documents and chunks in Neo4j"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph

    async def store_document(self, doc: ParsedDocument,
                           chunks: List[Chunk],
                           embeddings: List[np.ndarray]):
        """Store document with chunks and embeddings"""

        # Start transaction
        async with self.graph.transaction() as tx:
            # Create or update document node
            doc_node_id = await self._upsert_document_node(tx, doc)

            # Store chunks with embeddings
            chunk_ids = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = await self._create_chunk_node(
                    tx, chunk, embedding, doc_node_id
                )
                chunk_ids.append(chunk_id)

            # Create relationships
            await self._create_chunk_relationships(tx, doc_node_id, chunk_ids)

            # Update indexes
            await self._update_indexes(tx, doc_node_id)

            # Commit transaction
            await tx.commit()

        return doc_node_id

    async def _upsert_document_node(self, tx, doc: ParsedDocument) -> str:
        """Create or update document node"""

        query = """
            MERGE (d:{label} {{id: $id}})
            SET d += $properties
            RETURN d.id
        """.format(label=self._get_node_label(doc.doc_type))

        properties = {
            'id': doc.frontmatter.get('id', self._generate_id(doc)),
            'path': doc.path,
            'title': doc.frontmatter.get('title', os.path.basename(doc.path)),
            'version': doc.frontmatter.get('version', '0.0.0'),
            'content': doc.raw_content,
            'content_hash': doc.hash,
            'status': doc.frontmatter.get('status', 'draft'),
            'modified_at': doc.modified_at,
            'doc_type': doc.doc_type,
            'subsystem': doc.frontmatter.get('subsystem'),
            'owners': doc.frontmatter.get('owners', [])
        }

        result = await tx.run(query, {'id': properties['id'], 'properties': properties})
        return result.single()['d.id']

    async def _create_chunk_node(self, tx, chunk: Chunk,
                                embedding: np.ndarray,
                                doc_id: str) -> str:
        """Create chunk node with embedding"""

        chunk_id = f"{doc_id}-chunk-{chunk.metadata['chunk_index']}"

        query = """
            CREATE (c:Chunk {
                id: $id,
                content: $content,
                embedding: $embedding,
                metadata: $metadata,
                doc_id: $doc_id,
                created_at: datetime()
            })
            RETURN c.id
        """

        result = await tx.run(query, {
            'id': chunk_id,
            'content': chunk.content,
            'embedding': embedding.tolist(),
            'metadata': json.dumps(chunk.metadata),
            'doc_id': doc_id
        })

        return result.single()['c.id']
```

### Update Detection

```python
class UpdateDetector:
    """Detect changes in documents"""

    def __init__(self, graph: GraphOperations):
        self.graph = graph

    async def check_for_updates(self, file_paths: List[str]) -> List[UpdateInfo]:
        """Check which files need updating"""

        updates = []

        for path in file_paths:
            # Get file info
            file_hash = self._calculate_file_hash(path)
            modified_time = os.path.getmtime(path)

            # Check against stored version
            stored = await self._get_stored_info(path)

            if not stored:
                # New file
                updates.append(UpdateInfo(
                    path=path,
                    action='create',
                    reason='new_file'
                ))

            elif stored['content_hash'] != file_hash:
                # Content changed
                updates.append(UpdateInfo(
                    path=path,
                    action='update',
                    reason='content_changed',
                    old_hash=stored['content_hash'],
                    new_hash=file_hash
                ))

            elif modified_time > stored['processed_at']:
                # Metadata might have changed
                updates.append(UpdateInfo(
                    path=path,
                    action='refresh',
                    reason='metadata_changed'
                ))

        return updates

    async def _get_stored_info(self, path: str) -> Optional[Dict]:
        """Get stored document info"""

        query = """
            MATCH (d {path: $path})
            RETURN d.content_hash as content_hash,
                   d.modified_at as processed_at,
                   d.id as doc_id
        """

        result = await self.graph.query(query, {'path': path})
        return result[0] if result else None
```

## Interfaces

### Ingestion API

```python
class DocumentIngestionService:
    """Main ingestion interface"""

    def __init__(self):
        self.parsers = [
            MarkdownParser(),
            PythonParser(),
            YamlParser(),
            JsonParser()
        ]
        self.chunker = DocumentChunker()
        self.embedder = EmbeddingGenerator()
        self.storage = DocumentStorage()
        self.detector = UpdateDetector()

    async def ingest_directory(self, directory: str,
                              recursive: bool = True,
                              pattern: str = "**/*.md"):
        """Ingest all matching documents in directory"""

        # Find files
        files = glob.glob(
            os.path.join(directory, pattern),
            recursive=recursive
        )

        # Check for updates
        updates = await self.detector.check_for_updates(files)

        # Process updates
        results = []
        for update in updates:
            result = await self.ingest_file(update.path)
            results.append(result)

        return IngestionReport(
            total_files=len(files),
            updated_files=len(updates),
            results=results
        )

    async def ingest_file(self, file_path: str) -> IngestionResult:
        """Process single document"""

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find appropriate parser
            parser = self._get_parser(file_path)
            if not parser:
                return IngestionResult(
                    path=file_path,
                    status='skipped',
                    reason='no_parser'
                )

            # Parse document
            doc = parser.parse(content, file_path)

            # Create chunks
            chunks = self.chunker.chunk_document(doc)

            # Generate embeddings
            embeddings = await self.embedder.generate_embeddings(chunks)

            # Store in graph
            doc_id = await self.storage.store_document(doc, chunks, embeddings)

            return IngestionResult(
                path=file_path,
                status='success',
                doc_id=doc_id,
                chunks_created=len(chunks)
            )

        except Exception as e:
            return IngestionResult(
                path=file_path,
                status='error',
                error=str(e)
            )
```

## Configuration

### Ingestion Configuration
```yaml
# config/ingestion.yaml
ingestion:
  # File discovery
  patterns:
    architecture: "docs/architecture/**/*.md"
    design: "docs/design/**/*.md"
    code: "src/**/*.py"
    tests: "tests/**/*.py"

  # Parser settings
  parsers:
    markdown:
      extract_code_blocks: true
      parse_frontmatter: true
      process_links: true

    python:
      extract_docstrings: true
      parse_imports: true
      analyze_complexity: false

  # Chunking strategy
  chunking:
    default_size: 1000
    default_overlap: 200
    min_chunk_size: 100

    by_type:
      architecture:
        strategy: sections
        size: 1500

      design:
        strategy: sections
        size: 1000

      code:
        strategy: components
        size: 500

  # Embedding configuration
  embeddings:
    model: nomic-embed-text
    dimension: 768
    batch_size: 10
    cache_embeddings: true

  # Update detection
  updates:
    check_content_hash: true
    check_metadata: true
    force_reindex_after_days: 30
```

## Common Operations

### 1. Initial Bulk Ingestion
```python
async def initial_ingestion():
    """First-time document ingestion"""

    service = DocumentIngestionService()

    # Ingest all document types
    patterns = [
        ("docs/architecture", "**/*.md"),
        ("docs/design", "**/*.md"),
        ("src", "**/*.py"),
    ]

    for directory, pattern in patterns:
        print(f"Ingesting {directory} with pattern {pattern}")
        report = await service.ingest_directory(
            directory=directory,
            pattern=pattern
        )
        print(f"Processed {report.updated_files}/{report.total_files} files")
```

### 2. Incremental Updates
```python
async def incremental_update():
    """Update only changed documents"""

    service = DocumentIngestionService()
    detector = UpdateDetector()

    # Find changed files
    all_files = glob.glob("docs/**/*.md", recursive=True)
    updates = await detector.check_for_updates(all_files)

    print(f"Found {len(updates)} files needing update")

    # Process updates
    for update in updates:
        result = await service.ingest_file(update.path)
        print(f"{update.path}: {result.status}")
```

### 3. Selective Re-embedding
```python
async def reembed_subsystem(subsystem: str):
    """Re-generate embeddings for specific subsystem"""

    query = """
        MATCH (d:Architecture {subsystem: $subsystem})
        MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
        RETURN d.id as doc_id, collect(c) as chunks
    """

    results = await graph.query(query, {'subsystem': subsystem})

    embedder = EmbeddingGenerator()

    for result in results:
        chunks = result['chunks']

        # Generate new embeddings
        new_embeddings = await embedder.generate_embeddings(chunks)

        # Update chunks
        for chunk, embedding in zip(chunks, new_embeddings):
            await graph.query("""
                MATCH (c:Chunk {id: $chunk_id})
                SET c.embedding = $embedding,
                    c.embedding_updated = datetime()
            """, {
                'chunk_id': chunk['id'],
                'embedding': embedding.tolist()
            })
```

## Troubleshooting

### Common Issues

#### "Parser not found for file type"
- **Cause**: No parser registered for file extension
- **Solution**: Add parser or skip file type
```python
# Register custom parser
service.parsers.append(CustomParser())
```

#### "Embedding dimension mismatch"
- **Cause**: Model changed or index misconfigured
- **Solution**: Recreate index with correct dimensions
```cypher
DROP INDEX chunk_embedding;
CREATE VECTOR INDEX chunk_embedding...
```

#### "Chunking creates too many/few chunks"
- **Cause**: Inappropriate chunk size for content
- **Solution**: Adjust chunking parameters
```python
chunker = DocumentChunker(
    chunk_size=1500,  # Increase size
    chunk_overlap=300  # Increase overlap
)
```

#### "Duplicate document IDs"
- **Cause**: ID generation collision
- **Solution**: Use path-based IDs or UUIDs
```python
def _generate_id(self, doc):
    return f"{doc.doc_type}-{hashlib.md5(doc.path.encode()).hexdigest()[:8]}"
```

### Performance Monitoring
```python
# Ingestion metrics
metrics = service.get_metrics()
print(f"Files processed: {metrics.files_processed}")
print(f"Chunks created: {metrics.chunks_created}")
print(f"Avg processing time: {metrics.avg_time_per_file}s")
print(f"Embedding generation: {metrics.embedding_time}s")
print(f"Storage time: {metrics.storage_time}s")
```

## References

- **Architecture Document**: [`docs/architecture.md`](../architecture.md)
- **Graph Operations**: [`docs/subdomains/graph-operations.md`](./graph-operations.md)
- **Parser Implementations**: [`src/parsers/`](../../src/parsers/)
- **Chunking Strategies**: [`src/chunking/`](../../src/chunking/)
- **Embedding Models**: [`models/embeddings/`](../../models/embeddings/)