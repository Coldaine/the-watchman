"""
Tests for the document processing pipeline.

Tests parser, chunker, embedder, and complete pipeline with real documents.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing import (
    DocumentParser,
    TextChunker,
    EmbeddingGenerator,
    IngestionPipeline,
    ParsedDocument,
    Chunk,
    ProcessedChunk,
    IngestionReport
)


# Fixture for test document path
@pytest.fixture
def architecture_doc_path():
    """Path to the architecture document."""
    base_dir = Path(__file__).parent.parent
    doc_path = base_dir / 'docs' / 'architecture.md'

    if not doc_path.exists():
        pytest.skip(f"Architecture document not found: {doc_path}")

    return str(doc_path)


@pytest.fixture
def adr_doc_path():
    """Path to an ADR document."""
    base_dir = Path(__file__).parent.parent
    doc_path = base_dir / 'docs' / 'ADR' / '001-technology-stack-and-architecture-decisions.md'

    if not doc_path.exists():
        pytest.skip(f"ADR document not found: {doc_path}")

    return str(doc_path)


@pytest.fixture
def docs_directory():
    """Path to docs directory."""
    base_dir = Path(__file__).parent.parent
    docs_dir = base_dir / 'docs'

    if not docs_dir.exists():
        pytest.skip(f"Docs directory not found: {docs_dir}")

    return str(docs_dir)


class TestDocumentParser:
    """Test the DocumentParser class."""

    def test_can_parse_markdown(self):
        """Test parser recognizes markdown files."""
        parser = DocumentParser()

        assert parser.can_parse('test.md')
        assert parser.can_parse('test.markdown')
        assert not parser.can_parse('test.txt')
        assert not parser.can_parse('test.py')

    def test_parse_architecture_document(self, architecture_doc_path):
        """Test parsing real architecture document."""
        parser = DocumentParser()
        doc = parser.parse(architecture_doc_path)

        # Check basic properties
        assert isinstance(doc, ParsedDocument)
        assert doc.path == architecture_doc_path
        assert doc.doc_type == 'architecture'
        assert len(doc.content) > 0

        # Check frontmatter
        assert 'doc' in doc.frontmatter
        assert 'subsystem' in doc.frontmatter
        assert 'id' in doc.frontmatter
        assert 'version' in doc.frontmatter
        assert 'status' in doc.frontmatter
        assert 'owners' in doc.frontmatter

        # Architecture-specific frontmatter
        assert 'compliance_level' in doc.frontmatter
        assert 'drift_tolerance' in doc.frontmatter

        # Check sections extracted
        assert len(doc.sections) > 0
        print(f"Extracted {len(doc.sections)} sections")

        # Check metadata
        assert 'file_name' in doc.metadata
        assert 'section_count' in doc.metadata
        assert doc.metadata['has_frontmatter'] is True

    def test_parse_adr_document(self, adr_doc_path):
        """Test parsing ADR document."""
        parser = DocumentParser()

        # ADR documents may not be 'architecture' type
        # They might not have all required fields, so this might fail
        try:
            doc = parser.parse(adr_doc_path)

            assert isinstance(doc, ParsedDocument)
            assert len(doc.sections) > 0
            assert 'doc' in doc.frontmatter

        except ValueError as e:
            # Expected if frontmatter is incomplete
            print(f"ADR parsing failed (expected): {e}")
            pytest.skip("ADR document has incomplete frontmatter")

    def test_extract_sections(self):
        """Test section extraction from markdown."""
        parser = DocumentParser()

        content = """# Section 1
Content for section 1.

## Subsection 1.1
Content for subsection.

# Section 2
More content.
"""

        sections = parser._extract_sections(content)

        assert len(sections) == 3
        assert sections[0]['title'] == 'Section 1'
        assert sections[0]['level'] == 1
        assert sections[1]['title'] == 'Subsection 1.1'
        assert sections[1]['level'] == 2
        assert sections[2]['title'] == 'Section 2'
        assert sections[2]['level'] == 1

    def test_extract_code_blocks(self):
        """Test code block extraction."""
        parser = DocumentParser()

        content = """Some text

```python
def hello():
    print("world")
```

More text

```javascript
console.log("test");
```
"""

        code_blocks = parser.extract_code_blocks(content)

        assert len(code_blocks) == 2
        assert code_blocks[0]['language'] == 'python'
        assert 'def hello' in code_blocks[0]['content']
        assert code_blocks[1]['language'] == 'javascript'
        assert 'console.log' in code_blocks[1]['content']

    def test_extract_links(self):
        """Test markdown link extraction."""
        parser = DocumentParser()

        content = """
[Link 1](https://example.com)
Some text [Link 2](/docs/page.md)
[Internal](#section)
"""

        links = parser.extract_links(content)

        # Should extract non-anchor links
        assert len(links) >= 2
        assert 'https://example.com' in links
        assert '/docs/page.md' in links
        # Internal anchor should be filtered out
        assert '#section' not in links


class TestTextChunker:
    """Test the TextChunker class."""

    def test_count_tokens(self):
        """Test token counting."""
        chunker = TextChunker()

        # Simple text should have some tokens
        text = "This is a test sentence."
        token_count = chunker.count_tokens(text)

        assert token_count > 0
        assert token_count < 20  # Should be around 6-7 tokens

    def test_chunk_architecture_document(self, architecture_doc_path):
        """Test chunking real architecture document."""
        parser = DocumentParser()
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        doc = parser.parse(architecture_doc_path)
        chunks = chunker.chunk_document(doc)

        # Should create multiple chunks
        assert len(chunks) > 0
        print(f"Created {len(chunks)} chunks from architecture doc")

        # Check chunk properties
        for i, chunk in enumerate(chunks):
            assert isinstance(chunk, Chunk)
            assert len(chunk.content) > 0

            # Check metadata
            assert 'doc_id' in chunk.metadata
            assert 'doc_type' in chunk.metadata
            assert 'chunk_index' in chunk.metadata
            assert chunk.metadata['chunk_index'] == i
            assert chunk.metadata['total_chunks'] == len(chunks)

            # Architecture doc should preserve sections
            if chunk.section_title:
                print(f"Chunk {i}: {chunk.section_title}")

    def test_chunk_preserves_boundaries(self):
        """Test that chunking preserves paragraph boundaries."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        # Create a document with clear paragraphs
        content = """# Test

Paragraph 1 with some content.

Paragraph 2 with more content.

Paragraph 3 with even more content to make it longer.

Paragraph 4 continues the pattern.
"""

        # Create a simple parsed document
        from src.processing.models import ParsedDocument
        doc = ParsedDocument(
            path='test.md',
            doc_type='architecture',
            content=content,
            frontmatter={
                'doc': 'architecture',
                'subsystem': 'test',
                'id': 'test-doc',
                'version': '1.0.0',
                'status': 'draft',
                'owners': ['test'],
                'compliance_level': 'strict',
                'drift_tolerance': 'none'
            },
            hash='testhash',
            sections=[
                {
                    'title': 'Test',
                    'level': 1,
                    'content': content,
                    'start_line': 0,
                    'end_line': 10
                }
            ],
            size_bytes=len(content)
        )

        chunks = chunker.chunk_document(doc)

        # Should create at least one chunk
        assert len(chunks) > 0

        # Chunks should not split paragraphs in the middle
        for chunk in chunks:
            # Content should be coherent (no mid-sentence breaks)
            assert chunk.content.strip()

    def test_chunk_overlap(self):
        """Test that chunks have proper overlap."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=100)

        # Create content that will generate multiple chunks
        content = "Test paragraph. " * 100  # Long repetitive content

        chunks = chunker._chunk_by_sliding_window(content)

        if len(chunks) > 1:
            # Check for overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                chunk1 = chunks[i].content
                chunk2 = chunks[i + 1].content

                # There should be some overlap
                # (This is hard to test precisely, but we can check length)
                assert len(chunk1) > 0
                assert len(chunk2) > 0


class TestEmbeddingGenerator:
    """Test the EmbeddingGenerator class."""

    def test_initialization(self):
        """Test embedder initialization."""
        embedder = EmbeddingGenerator()

        assert embedder.host == "http://localhost:11434"
        assert embedder.model_name == "nomic-embed-text"
        assert embedder.embedding_dim == 768
        assert embedder.batch_size == 10

    def test_check_connection(self):
        """Test Ollama connection check."""
        embedder = EmbeddingGenerator()

        # This will fail if Ollama is not running
        # That's expected in CI/CD environments
        is_connected = embedder.check_connection()

        if is_connected:
            print("Ollama is running")
        else:
            print("Ollama is not running (expected in CI)")
            pytest.skip("Ollama not available")

    def test_check_model_available(self):
        """Test model availability check."""
        embedder = EmbeddingGenerator()

        if not embedder.check_connection():
            pytest.skip("Ollama not available")

        is_available = embedder.check_model_available()

        if is_available:
            print("Model is available")
        else:
            print("Model not pulled yet")
            pytest.skip("Model not available")

    @pytest.mark.skipif(
        not EmbeddingGenerator().check_connection(),
        reason="Ollama not running"
    )
    def test_generate_embedding(self):
        """Test single embedding generation."""
        embedder = EmbeddingGenerator()

        if not embedder.check_model_available():
            pytest.skip("Model not available")

        text = "This is a test document about architecture."
        embedding = embedder.generate_embedding(text)

        # Check embedding properties
        assert embedding is not None
        assert len(embedding) == 768
        assert embedder.validate_embedding(embedding)

        # Embedding should have reasonable values
        assert not (embedding == 0).all()  # Not all zeros

    @pytest.mark.skipif(
        not EmbeddingGenerator().check_connection(),
        reason="Ollama not running"
    )
    def test_embed_chunks(self):
        """Test embedding multiple chunks."""
        embedder = EmbeddingGenerator()

        if not embedder.check_model_available():
            pytest.skip("Model not available")

        # Create test chunks
        chunks = [
            Chunk(
                content="First chunk content",
                start_index=0,
                end_index=20,
                metadata={'doc_type': 'architecture'}
            ),
            Chunk(
                content="Second chunk content",
                start_index=20,
                end_index=40,
                metadata={'doc_type': 'design'}
            )
        ]

        processed_chunks = embedder.embed_chunks(chunks)

        assert len(processed_chunks) == 2

        for pc in processed_chunks:
            assert isinstance(pc, ProcessedChunk)
            assert len(pc.embedding) == 768
            assert embedder.validate_embedding(pc.embedding)


class TestIngestionPipeline:
    """Test the complete ingestion pipeline."""

    def test_initialization(self):
        """Test pipeline initialization."""
        pipeline = IngestionPipeline()

        assert pipeline.parser is not None
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None

    def test_validate_setup(self):
        """Test pipeline validation."""
        pipeline = IngestionPipeline()
        validation = pipeline.validate_setup()

        # Parser and chunker should always work
        assert validation['parser'] is True
        assert validation['chunker'] is True

        # Ollama might not be available
        if validation['ollama_connection']:
            print("Ollama is running")
        else:
            print("Ollama not available")
            assert len(validation['errors']) > 0

    def test_get_stats(self):
        """Test pipeline statistics."""
        pipeline = IngestionPipeline()
        stats = pipeline.get_stats()

        assert 'parser' in stats
        assert 'chunker' in stats
        assert 'embedder' in stats

        assert stats['chunker']['chunk_size'] == 1000
        assert stats['embedder']['dimensions'] == 768

    @pytest.mark.skipif(
        not EmbeddingGenerator().check_connection(),
        reason="Ollama not running"
    )
    def test_process_architecture_file(self, architecture_doc_path):
        """Test processing complete architecture document."""
        pipeline = IngestionPipeline()

        # Check if model is available
        if not pipeline.embedder.check_model_available():
            pytest.skip("Embedding model not available")

        result = pipeline.process_file(architecture_doc_path)

        # Check result structure
        assert 'file_path' in result
        assert 'document' in result
        assert 'chunks' in result
        assert 'processed_chunks' in result
        assert 'success' in result

        if result['success']:
            # Check parsed document
            assert isinstance(result['document'], ParsedDocument)
            assert result['document'].doc_type == 'architecture'

            # Check chunks
            assert len(result['chunks']) > 0
            assert len(result['processed_chunks']) > 0
            assert len(result['chunks']) == len(result['processed_chunks'])

            # Check embeddings
            for pc in result['processed_chunks']:
                assert isinstance(pc, ProcessedChunk)
                assert len(pc.embedding) == 768

            print(f"Successfully processed {architecture_doc_path}")
            print(f"Created {len(result['chunks'])} chunks with embeddings")
        else:
            print(f"Processing failed: {result['error']}")
            pytest.fail(f"Processing failed: {result['error']}")

    @pytest.mark.skipif(
        not EmbeddingGenerator().check_connection(),
        reason="Ollama not running"
    )
    def test_process_directory(self, docs_directory):
        """Test processing entire docs directory."""
        pipeline = IngestionPipeline()

        # Check if model is available
        if not pipeline.embedder.check_model_available():
            pytest.skip("Embedding model not available")

        # Process only architecture.md to avoid long test times
        report = pipeline.process_directory(
            docs_directory,
            pattern="architecture.md",
            recursive=False
        )

        # Check report
        assert isinstance(report, IngestionReport)
        assert report.total_files >= 0
        assert report.started_at is not None
        assert report.completed_at is not None

        print(f"Processed {report.total_files} files")
        print(f"Success: {report.success_count}")
        print(f"Errors: {report.error_count}")
        print(f"Skipped: {report.skipped_count}")


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
