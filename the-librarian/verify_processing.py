#!/usr/bin/env python
"""
Verification script for the document processing module.

This script runs a quick verification of all processing components
without requiring Ollama to be running.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def verify_imports():
    """Verify all modules can be imported."""
    print("Verifying imports...")

    try:
        from src.processing import (
            Document,
            ParsedDocument,
            Chunk,
            ProcessedChunk,
            IngestionResult,
            IngestionReport,
            UpdateInfo,
            DocumentParser,
            TextChunker,
            EmbeddingGenerator,
            IngestionPipeline
        )
        print("  [OK] All modules imported successfully")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def verify_parser():
    """Verify parser works with real document."""
    print("\nVerifying parser...")

    try:
        from src.processing import DocumentParser

        parser = DocumentParser()
        doc_path = Path(__file__).parent / 'docs' / 'architecture.md'

        if not doc_path.exists():
            print(f"  [SKIP] Document not found: {doc_path}")
            return True

        doc = parser.parse(str(doc_path))

        assert doc.doc_type == 'architecture'
        assert len(doc.sections) > 0
        assert 'id' in doc.frontmatter

        print(f"  [OK] Parsed {len(doc.sections)} sections from architecture.md")
        return True
    except Exception as e:
        print(f"  [FAIL] Parser error: {e}")
        return False


def verify_chunker():
    """Verify chunker works with real document."""
    print("\nVerifying chunker...")

    try:
        from src.processing import DocumentParser, TextChunker

        parser = DocumentParser()
        chunker = TextChunker()

        doc_path = Path(__file__).parent / 'docs' / 'architecture.md'

        if not doc_path.exists():
            print(f"  [SKIP] Document not found: {doc_path}")
            return True

        doc = parser.parse(str(doc_path))
        chunks = chunker.chunk_document(doc)

        assert len(chunks) > 0
        assert all(chunk.content for chunk in chunks)
        assert all('doc_id' in chunk.metadata for chunk in chunks)

        print(f"  [OK] Created {len(chunks)} chunks")
        return True
    except Exception as e:
        print(f"  [FAIL] Chunker error: {e}")
        return False


def verify_embedder():
    """Verify embedder initializes correctly."""
    print("\nVerifying embedder...")

    try:
        from src.processing import EmbeddingGenerator

        embedder = EmbeddingGenerator()

        assert embedder.embedding_dim == 768
        assert embedder.model_name == "nomic-embed-text"

        # Check connection (may fail if Ollama not running)
        connected = embedder.check_connection()

        if connected:
            print("  [OK] Embedder initialized and connected to Ollama")
        else:
            print("  [OK] Embedder initialized (Ollama not running)")

        return True
    except Exception as e:
        print(f"  [FAIL] Embedder error: {e}")
        return False


def verify_pipeline():
    """Verify pipeline integrates all components."""
    print("\nVerifying pipeline...")

    try:
        from src.processing import IngestionPipeline

        pipeline = IngestionPipeline()

        # Check components
        assert pipeline.parser is not None
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None

        # Get stats
        stats = pipeline.get_stats()
        assert 'parser' in stats
        assert 'chunker' in stats
        assert 'embedder' in stats

        print("  [OK] Pipeline initialized with all components")
        return True
    except Exception as e:
        print(f"  [FAIL] Pipeline error: {e}")
        return False


def verify_models():
    """Verify data models work correctly."""
    print("\nVerifying data models...")

    try:
        from src.processing import Chunk, ProcessedChunk
        import hashlib

        # Create a test chunk
        chunk = Chunk(
            content="Test content",
            start_index=0,
            end_index=12,
            metadata={'test': True}
        )

        assert chunk.content == "Test content"
        assert chunk.metadata['test'] is True

        # Create a processed chunk with embedding
        processed = ProcessedChunk(
            content="Test content",
            start_index=0,
            end_index=12,
            metadata={'test': True},
            embedding=[0.1] * 768  # 768 dimensions
        )

        assert len(processed.embedding) == 768

        print("  [OK] Data models validate correctly")
        return True
    except Exception as e:
        print(f"  [FAIL] Model error: {e}")
        return False


def main():
    """Run all verifications."""
    print("=" * 60)
    print("DOCUMENT PROCESSING MODULE VERIFICATION")
    print("=" * 60)

    results = []

    results.append(("Imports", verify_imports()))
    results.append(("Models", verify_models()))
    results.append(("Parser", verify_parser()))
    results.append(("Chunker", verify_chunker()))
    results.append(("Embedder", verify_embedder()))
    results.append(("Pipeline", verify_pipeline()))

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL VERIFICATIONS PASSED")
        print("=" * 60)
        print("\nThe document processing module is working correctly!")
        print("\nNext steps:")
        print("1. Install Ollama: https://ollama.ai/download")
        print("2. Pull embedding model: ollama pull nomic-embed-text")
        print("3. Run demo: python demo_processing.py")
        print("4. Run full tests: pytest tests/test_processing.py -v")
        return 0
    else:
        print("SOME VERIFICATIONS FAILED")
        print("=" * 60)
        print("\nPlease check the errors above and fix them.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
