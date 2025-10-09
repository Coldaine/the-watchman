"""
Embedding generation using Ollama with OpenRouter fallback.

Provides:
- Text embeddings via Ollama (local)
- Fallback to OpenRouter if Ollama unavailable
- Batch processing
- Caching
"""

import hashlib
from typing import List, Optional
import httpx
from loguru import logger

from app.utils.config import get_settings


class EmbeddingClient:
    """Client for generating text embeddings."""

    def __init__(self):
        """Initialize embedding client."""
        self.settings = get_settings()
        self.ollama_url = self.settings.ollama_url
        self.ollama_model = self.settings.ollama_embedding_model
        self.cache = {}  # Simple in-memory cache

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    async def generate_embedding_ollama(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={
                        "model": self.ollama_model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")

        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}")
            return None

    async def generate_embedding_openrouter(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenRouter (fallback)."""
        if not self.settings.openrouter_api_key:
            logger.warning("OpenRouter API key not configured")
            return None

        try:
            # OpenRouter doesn't provide embeddings directly
            # This is a placeholder - you'd need to use OpenAI API format
            # or another compatible embedding service
            logger.warning("OpenRouter embedding not implemented, using dummy fallback")
            return None

        except Exception as e:
            logger.error(f"OpenRouter embedding failed: {e}")
            return None

    async def generate_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Tries Ollama first, falls back to OpenRouter if unavailable.

        Args:
            text: Text to embed
            use_cache: Whether to use cache

        Returns:
            Embedding vector or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return self.cache[cache_key]

        # Try Ollama first
        embedding = await self.generate_embedding_ollama(text)

        # Fallback to OpenRouter
        if embedding is None:
            logger.info("Falling back to OpenRouter for embedding")
            embedding = await self.generate_embedding_openrouter(text)

        # Cache result
        if embedding and use_cache:
            cache_key = self._get_cache_key(text)
            self.cache[cache_key] = embedding

        return embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once

        Returns:
            List of embeddings (None for failed items)
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

            # Process batch items sequentially (Ollama doesn't support batch API)
            batch_embeddings = []
            for text in batch:
                embedding = await self.generate_embedding(text)
                batch_embeddings.append(embedding)

            embeddings.extend(batch_embeddings)

        return embeddings

    def sync_generate_embedding(self, text: str) -> Optional[List[float]]:
        """Synchronous wrapper for generate_embedding."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate_embedding(text))

    def sync_generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Synchronous wrapper for generate_embeddings_batch."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate_embeddings_batch(texts))


# Global client instance
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """Get global embedding client instance."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client
