#!/usr/bin/env python3
"""
OCR processing worker for Visual Timeline.

Processes screenshots to extract text using:
1. Tesseract OCR for visual text
2. Optional ATSPI for accessibility tree (future)

Generates embeddings and stores chunks in Neo4j.
"""

import sys
import time
from pathlib import Path

import pytesseract
from loguru import logger
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.config import get_settings
from app.utils.embedding import get_embedding_client
from app.utils.helpers import chunk_text, hash_text, redact_text
from app.utils.neo4j_client import get_neo4j_client


class OCRProcessor:
    """OCR processing and embedding generation."""

    def __init__(self):
        """Initialize OCR processor."""
        self.settings = get_settings()
        self.neo4j = get_neo4j_client()
        self.embedding = get_embedding_client()

        logger.info("OCR processor initialized")

    def get_pending_snapshots(self, limit: int = 10) -> list[dict]:
        """
        Get snapshots that haven't been OCR processed yet.

        Args:
            limit: Maximum number of snapshots to process

        Returns:
            List of snapshot records
        """
        query = """
        MATCH (s:Snapshot)
        WHERE NOT (s)-[:HAS_OCR]->(:Chunk)
        AND s.path IS NOT NULL
        RETURN s.id AS id, s.path AS path, s.ts AS ts
        ORDER BY s.ts DESC
        LIMIT $limit
        """

        try:
            results = self.neo4j.execute_read(query, {"limit": limit})
            logger.info(f"Found {len(results)} snapshots pending OCR")
            return results

        except Exception as e:
            logger.error(f"Failed to query pending snapshots: {e}")
            return []

    def extract_text_tesseract(self, image_path: str) -> str | None:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_path: Path to screenshot image

        Returns:
            Extracted text or None if failed
        """
        try:
            # Load image
            img = Image.open(image_path)

            # Run OCR
            text = pytesseract.image_to_string(img)

            if not text or not text.strip():
                logger.debug(f"No text found in {image_path}")
                return None

            logger.success(f"Extracted {len(text)} characters from {image_path}")
            return text.strip()

        except Exception as e:
            logger.error(f"Tesseract OCR failed for {image_path}: {e}")
            return None

    def apply_redaction(self, text: str) -> str:
        """
        Apply privacy redaction to text.

        Args:
            text: Text to redact

        Returns:
            Redacted text
        """
        patterns = self.settings.get_redact_patterns()
        return redact_text(text, patterns)

    def process_and_chunk(self, text: str) -> list[str]:
        """
        Process text and split into chunks.

        Args:
            text: Text to process

        Returns:
            List of text chunks
        """
        # Apply redaction
        redacted = self.apply_redaction(text)

        # Split into chunks
        chunks = chunk_text(redacted, max_length=500, overlap=50)

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    def create_chunk_nodes(self, snapshot_id: str, chunks: list[str]) -> int:
        """
        Create Chunk nodes with embeddings and link to Snapshot.

        Args:
            snapshot_id: Snapshot node ID
            chunks: List of text chunks

        Returns:
            Number of chunks created
        """
        created_count = 0

        for chunk_text_content in chunks:
            try:
                # Generate embedding
                embedding = self.embedding.sync_generate_embedding(chunk_text_content)

                if embedding is None:
                    logger.warning("Failed to generate embedding for chunk, skipping")
                    continue

                # Create content hash
                content_hash = hash_text(chunk_text_content)

                # Create or update Chunk node
                query = """
                MATCH (s:Snapshot {id: $snapshot_id})
                MERGE (c:Chunk {content_hash: $hash})
                ON CREATE SET
                    c.text = $text,
                    c.embedding = $embedding
                ON MATCH SET
                    c.text = $text,
                    c.embedding = $embedding
                MERGE (s)-[:HAS_OCR]->(c)
                RETURN c.content_hash AS hash
                """

                result = self.neo4j.execute_read(
                    query,
                    {
                        "snapshot_id": snapshot_id,
                        "hash": content_hash,
                        "text": chunk_text_content,
                        "embedding": embedding,
                    },
                )

                if result:
                    created_count += 1
                    logger.debug(f"Created chunk: {content_hash[:8]}...")

            except Exception as e:
                logger.error(f"Failed to create chunk node: {e}")
                continue

        logger.success(f"Created {created_count}/{len(chunks)} chunks for snapshot {snapshot_id}")
        return created_count

    def process_snapshot(self, snapshot: dict):
        """
        Process a single snapshot: extract text, chunk, embed, store.

        Args:
            snapshot: Snapshot record with id and path
        """
        snapshot_id = snapshot["id"]
        image_path = snapshot["path"]

        logger.info(f"Processing snapshot {snapshot_id}: {image_path}")

        # Check if image file exists
        if not Path(image_path).exists():
            logger.warning(f"Image file not found: {image_path}")
            return

        # Extract text using Tesseract
        text = self.extract_text_tesseract(image_path)

        if not text:
            logger.info(f"No text extracted from {snapshot_id}")
            # Still create a marker to prevent reprocessing
            self._mark_processed_empty(snapshot_id)
            return

        # Process and chunk text
        chunks = self.process_and_chunk(text)

        if not chunks:
            logger.warning(f"No chunks generated for {snapshot_id}")
            self._mark_processed_empty(snapshot_id)
            return

        # Create chunk nodes with embeddings
        created = self.create_chunk_nodes(snapshot_id, chunks)

        if created > 0:
            logger.success(f"Snapshot {snapshot_id} processed: {created} chunks")
        else:
            logger.warning(f"Snapshot {snapshot_id} processed but no chunks created")

    def _mark_processed_empty(self, snapshot_id: str):
        """
        Mark snapshot as processed even if no text was found.

        This prevents reprocessing empty screenshots.

        Args:
            snapshot_id: Snapshot node ID
        """
        query = """
        MATCH (s:Snapshot {id: $snapshot_id})
        SET s.ocr_processed = true, s.ocr_empty = true
        """

        try:
            self.neo4j.execute_write(query, {"snapshot_id": snapshot_id})
        except Exception as e:
            logger.warning(f"Failed to mark snapshot as processed: {e}")

    def process_batch(self):
        """Process a batch of pending snapshots."""
        # Get pending snapshots
        snapshots = self.get_pending_snapshots(limit=self.settings.ocr_queue_size)

        if not snapshots:
            logger.debug("No pending snapshots to process")
            return

        # Process each snapshot
        for snapshot in snapshots:
            try:
                self.process_snapshot(snapshot)
            except Exception as e:
                logger.error(f"Error processing snapshot {snapshot.get('id')}: {e}")
                continue

    def run(self):
        """Run continuous OCR processing loop."""
        logger.info("OCR processing worker started")

        while True:
            try:
                self.process_batch()
            except Exception as e:
                logger.error(f"Batch processing error: {e}")

            # Sleep between batches
            time.sleep(30)  # Check for new snapshots every 30 seconds


def main():
    """Main entry point."""
    logger.info("Visual Timeline - OCR Processing Worker")

    try:
        processor = OCRProcessor()
        processor.run()
    except KeyboardInterrupt:
        logger.info("OCR processor stopped by user")
    except Exception as e:
        logger.error(f"OCR processor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
