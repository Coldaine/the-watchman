"""
Document ingestion pipeline.

Combines parser, chunker, and embedder into a complete pipeline for processing
documents. Handles single files, directories, and error recovery.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .parser import DocumentParser
from .chunker import TextChunker
from .embedder import EmbeddingGenerator
from .models import (
    ParsedDocument,
    Chunk,
    ProcessedChunk,
    IngestionResult,
    IngestionReport
)


logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Complete document ingestion pipeline."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        chunker: Optional[TextChunker] = None,
        embedder: Optional[EmbeddingGenerator] = None
    ):
        """Initialize the pipeline.

        Args:
            parser: Document parser (creates default if None)
            chunker: Text chunker (creates default if None)
            embedder: Embedding generator (creates default if None)
        """
        self.parser = parser or DocumentParser()
        self.chunker = chunker or TextChunker()
        self.embedder = embedder or EmbeddingGenerator()

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single document through the complete pipeline.

        Args:
            file_path: Path to the document

        Returns:
            Dictionary with:
                - document: ParsedDocument
                - chunks: List[Chunk]
                - processed_chunks: List[ProcessedChunk] (with embeddings)
                - success: bool
                - error: Optional[str]
        """
        result = {
            'file_path': file_path,
            'document': None,
            'chunks': [],
            'processed_chunks': [],
            'success': False,
            'error': None
        }

        try:
            # Step 1: Parse document
            logger.info(f"Parsing: {file_path}")
            document = self.parser.parse(file_path)
            result['document'] = document

            # Step 2: Create chunks
            logger.info(f"Chunking: {file_path}")
            chunks = self.chunker.chunk_document(document)
            result['chunks'] = chunks
            logger.info(f"Created {len(chunks)} chunks")

            # Step 3: Generate embeddings
            logger.info(f"Generating embeddings: {file_path}")
            processed_chunks = self.embedder.embed_chunks(chunks)
            result['processed_chunks'] = processed_chunks
            logger.info(f"Generated {len(processed_chunks)} embeddings")

            result['success'] = True

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def process_directory(
        self,
        directory: str,
        pattern: str = "**/*.md",
        recursive: bool = True
    ) -> IngestionReport:
        """Process all matching files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for file matching
            recursive: Whether to search recursively

        Returns:
            IngestionReport with results
        """
        started_at = datetime.now()

        # Find all matching files
        dir_path = Path(directory)
        if recursive:
            files = list(dir_path.glob(pattern))
        else:
            files = list(dir_path.glob(pattern.replace('**/', '')))

        logger.info(f"Found {len(files)} files matching pattern '{pattern}'")

        results = []

        for file_path in files:
            file_str = str(file_path)

            # Check if parser can handle this file
            if not self.parser.can_parse(file_str):
                logger.info(f"Skipping (no parser): {file_str}")
                results.append(IngestionResult(
                    path=file_str,
                    status='skipped',
                    error='No parser available'
                ))
                continue

            # Process file
            logger.info(f"Processing: {file_str}")
            process_result = self.process_file(file_str)

            if process_result['success']:
                doc_id = process_result['document'].frontmatter.get('id', 'unknown')
                chunk_count = len(process_result['processed_chunks'])

                results.append(IngestionResult(
                    path=file_str,
                    status='success',
                    doc_id=doc_id,
                    chunks_created=chunk_count
                ))
            else:
                results.append(IngestionResult(
                    path=file_str,
                    status='error',
                    error=process_result['error']
                ))

        completed_at = datetime.now()

        report = IngestionReport(
            total_files=len(files),
            updated_files=len([r for r in results if r.status == 'success']),
            results=results,
            started_at=started_at,
            completed_at=completed_at
        )

        return report

    def validate_setup(self) -> Dict[str, Any]:
        """Validate that the pipeline is properly configured.

        Returns:
            Dictionary with validation results
        """
        validation = {
            'parser': False,
            'chunker': False,
            'embedder': False,
            'ollama_connection': False,
            'ollama_model': False,
            'errors': []
        }

        # Check parser
        try:
            self.parser.can_parse('test.md')
            validation['parser'] = True
        except Exception as e:
            validation['errors'].append(f"Parser error: {e}")

        # Check chunker
        try:
            from .models import ParsedDocument
            test_doc = ParsedDocument(
                path='test.md',
                doc_type='architecture',
                content='# Test\nContent',
                frontmatter={
                    'doc': 'architecture',
                    'subsystem': 'test',
                    'id': 'test',
                    'version': '1.0.0',
                    'status': 'draft',
                    'owners': ['test'],
                    'compliance_level': 'strict',
                    'drift_tolerance': 'none'
                },
                hash='test',
                sections=[],
                size_bytes=0
            )
            self.chunker.chunk_document(test_doc)
            validation['chunker'] = True
        except Exception as e:
            validation['errors'].append(f"Chunker error: {e}")

        # Check embedder connection
        try:
            if self.embedder.check_connection():
                validation['ollama_connection'] = True
            else:
                validation['errors'].append("Cannot connect to Ollama")
        except Exception as e:
            validation['errors'].append(f"Ollama connection error: {e}")

        # Check model availability
        try:
            if validation['ollama_connection']:
                if self.embedder.check_model_available():
                    validation['ollama_model'] = True
                else:
                    validation['errors'].append(
                        f"Model {self.embedder.model_name} not available. "
                        f"Run: ollama pull {self.embedder.model_name}"
                    )
        except Exception as e:
            validation['errors'].append(f"Model check error: {e}")

        # Overall success
        validation['success'] = all([
            validation['parser'],
            validation['chunker'],
            validation['embedder'],
            validation['ollama_connection'],
            validation['ollama_model']
        ])

        return validation

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics and configuration.

        Returns:
            Dictionary with pipeline configuration
        """
        return {
            'parser': {
                'type': type(self.parser).__name__,
                'supported_extensions': self.parser.supported_extensions
            },
            'chunker': {
                'chunk_size': self.chunker.chunk_size,
                'chunk_overlap': self.chunker.chunk_overlap,
                'min_chunk_size': self.chunker.min_chunk_size
            },
            'embedder': {
                'host': self.embedder.host,
                'model': self.embedder.model_name,
                'dimensions': self.embedder.embedding_dim,
                'batch_size': self.embedder.batch_size
            }
        }
