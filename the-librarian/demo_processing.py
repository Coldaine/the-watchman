"""
Demo script for the document processing pipeline.

This script demonstrates how to use the document processing pipeline to:
1. Parse markdown documents with frontmatter
2. Chunk documents intelligently
3. Generate embeddings using Ollama
4. Process entire directories

Usage:
    python demo_processing.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.processing import (
    DocumentParser,
    TextChunker,
    EmbeddingGenerator,
    IngestionPipeline
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_parser():
    """Demo document parsing."""
    print("\n" + "=" * 60)
    print("DEMO: Document Parser")
    print("=" * 60)

    parser = DocumentParser()

    # Find architecture document
    doc_path = Path(__file__).parent / 'docs' / 'architecture.md'

    if not doc_path.exists():
        print(f"Architecture document not found: {doc_path}")
        return

    print(f"\nParsing: {doc_path}")

    # Parse document
    doc = parser.parse(str(doc_path))

    print(f"\nDocument Type: {doc.doc_type}")
    print(f"Document ID: {doc.frontmatter.get('id')}")
    print(f"Version: {doc.frontmatter.get('version')}")
    print(f"Status: {doc.frontmatter.get('status')}")
    print(f"Owners: {doc.frontmatter.get('owners')}")
    print(f"Content Size: {doc.size_bytes} bytes")
    print(f"Sections: {len(doc.sections)}")

    # Show first few sections
    print("\nFirst 5 sections:")
    for i, section in enumerate(doc.sections[:5]):
        print(f"  {i+1}. {section['title']} (Level {section['level']})")


def demo_chunker():
    """Demo text chunking."""
    print("\n" + "=" * 60)
    print("DEMO: Text Chunker")
    print("=" * 60)

    parser = DocumentParser()
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

    # Parse architecture document
    doc_path = Path(__file__).parent / 'docs' / 'architecture.md'

    if not doc_path.exists():
        print(f"Architecture document not found: {doc_path}")
        return

    doc = parser.parse(str(doc_path))

    print(f"\nChunking document: {doc.frontmatter.get('id')}")

    # Create chunks
    chunks = chunker.chunk_document(doc)

    print(f"\nCreated {len(chunks)} chunks")

    # Show chunk statistics
    chunk_sizes = [len(chunk.content) for chunk in chunks]
    token_counts = [chunker.count_tokens(chunk.content) for chunk in chunks]

    print(f"\nChunk Statistics:")
    print(f"  Min size: {min(chunk_sizes)} chars, {min(token_counts)} tokens")
    print(f"  Max size: {max(chunk_sizes)} chars, {max(token_counts)} tokens")
    print(f"  Avg size: {sum(chunk_sizes)//len(chunks)} chars, {sum(token_counts)//len(chunks)} tokens")

    # Show first few chunks
    print("\nFirst 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n  Chunk {i+1}:")
        print(f"    Section: {chunk.section_title or 'N/A'}")
        print(f"    Size: {len(chunk.content)} chars, {chunker.count_tokens(chunk.content)} tokens")
        print(f"    Preview: {chunk.content[:100]}...")


def demo_embedder():
    """Demo embedding generation."""
    print("\n" + "=" * 60)
    print("DEMO: Embedding Generator")
    print("=" * 60)

    embedder = EmbeddingGenerator()

    print(f"\nEmbedder Configuration:")
    print(f"  Host: {embedder.host}")
    print(f"  Model: {embedder.model_name}")
    print(f"  Dimensions: {embedder.embedding_dim}")
    print(f"  Batch Size: {embedder.batch_size}")

    # Check connection
    print("\nChecking Ollama connection...")
    if not embedder.check_connection():
        print("ERROR: Cannot connect to Ollama")
        print("Make sure Ollama is running: ollama serve")
        return

    print("Connected to Ollama!")

    # Check model availability
    print(f"\nChecking if model '{embedder.model_name}' is available...")
    if not embedder.check_model_available():
        print(f"ERROR: Model not available")
        print(f"Pull the model: ollama pull {embedder.model_name}")
        return

    print("Model is available!")

    # Generate test embedding
    print("\nGenerating test embedding...")
    test_text = "This is a test document about the Librarian Agent architecture."

    embedding = embedder.generate_embedding(test_text)

    print(f"Generated embedding:")
    print(f"  Dimensions: {len(embedding)}")
    print(f"  First 10 values: {embedding[:10]}")
    print(f"  Valid: {embedder.validate_embedding(embedding)}")


def demo_pipeline():
    """Demo complete ingestion pipeline."""
    print("\n" + "=" * 60)
    print("DEMO: Complete Ingestion Pipeline")
    print("=" * 60)

    pipeline = IngestionPipeline()

    # Validate setup
    print("\nValidating pipeline setup...")
    validation = pipeline.validate_setup()

    print(f"\nValidation Results:")
    print(f"  Parser: {'OK' if validation['parser'] else 'FAIL'}")
    print(f"  Chunker: {'OK' if validation['chunker'] else 'FAIL'}")
    print(f"  Embedder: {'OK' if validation['embedder'] else 'FAIL'}")
    print(f"  Ollama Connection: {'OK' if validation['ollama_connection'] else 'FAIL'}")
    print(f"  Ollama Model: {'OK' if validation['ollama_model'] else 'FAIL'}")

    if validation['errors']:
        print(f"\nErrors:")
        for error in validation['errors']:
            print(f"  - {error}")

    if not validation['success']:
        print("\nPipeline validation failed. Please fix errors above.")
        return

    # Process architecture document
    doc_path = Path(__file__).parent / 'docs' / 'architecture.md'

    if not doc_path.exists():
        print(f"\nArchitecture document not found: {doc_path}")
        return

    print(f"\nProcessing: {doc_path}")

    result = pipeline.process_file(str(doc_path))

    if result['success']:
        print("\n[SUCCESS] Processing successful!")
        print(f"\nResults:")
        print(f"  Document ID: {result['document'].frontmatter.get('id')}")
        print(f"  Document Type: {result['document'].doc_type}")
        print(f"  Chunks Created: {len(result['chunks'])}")
        print(f"  Embeddings Generated: {len(result['processed_chunks'])}")

        # Show sample processed chunk
        if result['processed_chunks']:
            pc = result['processed_chunks'][0]
            print(f"\nSample Processed Chunk:")
            print(f"  Section: {pc.section_title or 'N/A'}")
            print(f"  Content Length: {len(pc.content)} chars")
            print(f"  Embedding Dimensions: {len(pc.embedding)}")
            print(f"  Content Preview: {pc.content[:150]}...")
    else:
        print(f"\n[FAILED] Processing failed: {result['error']}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("DOCUMENT PROCESSING PIPELINE DEMO")
    print("=" * 60)

    try:
        # Run demos in sequence
        demo_parser()
        demo_chunker()
        demo_embedder()
        demo_pipeline()

        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


if __name__ == '__main__':
    main()
