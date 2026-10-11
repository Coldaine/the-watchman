"""
Embedding generator using Ollama's nomic-embed-text model.

Generates 768-dimensional embeddings for text chunks, with batch processing
for efficiency and connection pooling for reliability.
"""

import logging
from typing import List, Optional
import numpy as np
from ollama import Client, ResponseError
from .models import Chunk, ProcessedChunk


logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate vector embeddings using Ollama."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model_name: str = "nomic-embed-text",
        embedding_dim: int = 768,
        batch_size: int = 10
    ):
        """Initialize the embedding generator.

        Args:
            host: Ollama server URL
            model_name: Name of embedding model
            embedding_dim: Expected embedding dimensions
            batch_size: Number of texts to process in one batch
        """
        self.host = host
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self.client = Client(host=host)

    def check_connection(self) -> bool:
        """Check if Ollama server is accessible.

        Returns:
            True if server is accessible, False otherwise
        """
        try:
            # Try to list models to verify connection
            self.client.list()
            return True
        except Exception as e:
            logger.error(f"Cannot connect to Ollama at {self.host}: {e}")
            return False

    def check_model_available(self) -> bool:
        """Check if embedding model is available.

        Returns:
            True if model is available, False otherwise
        """
        try:
            response = self.client.list()

            # Handle different response formats
            if isinstance(response, dict):
                models = response.get('models', [])
            else:
                models = response

            # Extract model names
            model_names = []
            for m in models:
                if isinstance(m, dict):
                    # Try different key names
                    name = m.get('name') or m.get('model') or str(m)
                    model_names.append(name)
                else:
                    model_names.append(str(m))

            is_available = any(self.model_name in name for name in model_names)

            if not is_available:
                logger.warning(
                    f"Model {self.model_name} not found. "
                    f"Available models: {model_names}. "
                    f"Run: ollama pull {self.model_name}"
                )

            return is_available
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Numpy array with embedding vector

        Raises:
            ValueError: If embedding dimension is incorrect
            ResponseError: If Ollama API call fails
        """
        try:
            # Prepare text (truncate if necessary)
            prepared_text = self._prepare_text(text)

            # Call Ollama API
            response = self.client.embeddings(
                model=self.model_name,
                prompt=prepared_text
            )

            # Extract embedding
            embedding = np.array(response['embedding'], dtype=np.float32)

            # Validate dimensions
            if len(embedding) != self.embedding_dim:
                raise ValueError(
                    f"Expected {self.embedding_dim} dimensions, "
                    f"got {len(embedding)}"
                )

            return embedding

        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding arrays
        """
        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            logger.info(
                f"Processing batch {i // self.batch_size + 1}/"
                f"{(len(texts) + self.batch_size - 1) // self.batch_size}"
            )

            for text in batch:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)

        return embeddings

    def embed_chunks(self, chunks: List[Chunk]) -> List[ProcessedChunk]:
        """Generate embeddings for chunks and return ProcessedChunks.

        Args:
            chunks: List of chunks to embed

        Returns:
            List of ProcessedChunk objects with embeddings
        """
        # Prepare texts with metadata context
        texts = [self._prepare_chunk_text(chunk) for chunk in chunks]

        # Generate embeddings
        embeddings = self.generate_embeddings_batch(texts)

        # Create ProcessedChunk objects
        processed_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            processed_chunk = ProcessedChunk(
                content=chunk.content,
                start_index=chunk.start_index,
                end_index=chunk.end_index,
                metadata=chunk.metadata,
                parent_id=chunk.parent_id,
                section_title=chunk.section_title,
                section_level=chunk.section_level,
                embedding=embedding.tolist()
            )
            processed_chunks.append(processed_chunk)

        return processed_chunks

    def _prepare_text(self, text: str, max_length: int = 8192) -> str:
        """Prepare text for embedding.

        Args:
            text: Raw text
            max_length: Maximum character length

        Returns:
            Prepared text
        """
        # Truncate if too long
        if len(text) > max_length:
            logger.warning(f"Text truncated from {len(text)} to {max_length} chars")
            text = text[:max_length]

        return text.strip()

    def _prepare_chunk_text(self, chunk: Chunk) -> str:
        """Prepare chunk text for embedding with context.

        Adds metadata context to improve embedding quality.

        Args:
            chunk: Chunk to prepare

        Returns:
            Prepared text with context
        """
        # Add doc_type prefix for context
        doc_type = chunk.metadata.get('doc_type', '')

        if doc_type == 'architecture':
            prefix = "Architecture specification: "
        elif doc_type == 'design':
            prefix = "Design document: "
        elif doc_type == 'code':
            prefix = "Source code: "
        elif doc_type == 'research':
            prefix = "Research document: "
        else:
            prefix = ""

        # Include section title for context
        if chunk.section_title:
            text = f"{prefix}{chunk.section_title}\n{chunk.content}"
        else:
            text = f"{prefix}{chunk.content}"

        return self._prepare_text(text)

    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """Validate embedding array.

        Args:
            embedding: Embedding to validate

        Returns:
            True if valid, False otherwise
        """
        # Check dimensions
        if len(embedding) != self.embedding_dim:
            logger.error(
                f"Invalid dimensions: expected {self.embedding_dim}, "
                f"got {len(embedding)}"
            )
            return False

        # Check for NaN or Inf
        if np.isnan(embedding).any():
            logger.error("Embedding contains NaN values")
            return False

        if np.isinf(embedding).any():
            logger.error("Embedding contains Inf values")
            return False

        # Check if all zeros (unusual)
        if np.allclose(embedding, 0):
            logger.warning("Embedding is all zeros")
            return False

        return True
