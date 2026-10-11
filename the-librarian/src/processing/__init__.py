"""
Document Processing Pipeline

This module provides complete document ingestion capabilities for the Librarian Agent.
It parses markdown documents, chunks them intelligently, and generates embeddings.

Main Components:
    - DocumentParser: Parse markdown files with YAML frontmatter
    - TextChunker: Split documents into semantic chunks
    - EmbeddingGenerator: Generate 768-dim embeddings via Ollama
    - IngestionPipeline: Complete processing pipeline

Example:
    from src.processing import IngestionPipeline

    pipeline = IngestionPipeline()
    result = pipeline.process_file('docs/architecture.md')

    if result['success']:
        document = result['document']
        chunks = result['processed_chunks']  # With embeddings
"""

from .models import (
    Document,
    ParsedDocument,
    Chunk,
    ProcessedChunk,
    IngestionResult,
    IngestionReport,
    UpdateInfo
)

from .parser import DocumentParser
from .chunker import TextChunker
from .embedder import EmbeddingGenerator
from .pipeline import IngestionPipeline


__all__ = [
    # Models
    'Document',
    'ParsedDocument',
    'Chunk',
    'ProcessedChunk',
    'IngestionResult',
    'IngestionReport',
    'UpdateInfo',

    # Processing Components
    'DocumentParser',
    'TextChunker',
    'EmbeddingGenerator',
    'IngestionPipeline'
]

__version__ = '0.1.0'
