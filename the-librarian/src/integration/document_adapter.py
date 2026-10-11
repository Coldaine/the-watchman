"""
Document-to-Graph adapter for storing processed documents in Neo4j.

Converts processing pipeline outputs (ParsedDocument, ProcessedChunk) into
graph database nodes and relationships with proper embedding storage.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import hashlib

from ..processing.models import ParsedDocument, ProcessedChunk
from ..graph.operations import GraphOperations
from ..graph.vector_ops import VectorOperations
from ..graph.schema import NodeLabels, RelationshipTypes

logger = logging.getLogger(__name__)


class DocumentGraphAdapter:
    """Adapter for storing documents and chunks in graph database."""

    def __init__(self, graph_ops: GraphOperations, vector_ops: VectorOperations):
        """
        Initialize document adapter.

        Args:
            graph_ops: Graph operations instance
            vector_ops: Vector operations instance
        """
        self.graph_ops = graph_ops
        self.vector_ops = vector_ops

    async def store_document(
        self,
        document: ParsedDocument,
        chunks: List[ProcessedChunk]
    ) -> str:
        """
        Store a parsed document with its chunks in the graph.

        Creates:
        - Document node (Architecture/Design based on doc_type)
        - Chunk nodes with embeddings
        - CONTAINS relationships from document to chunks

        Args:
            document: Parsed document to store
            chunks: Processed chunks with embeddings

        Returns:
            Document ID

        Raises:
            ValueError: If document type is unsupported
            RuntimeError: If storage fails
        """
        logger.info(f"Storing document: {document.path}")

        # Determine node label based on doc_type
        node_label = self._get_node_label(document.doc_type)

        # Prepare document properties
        doc_properties = self._document_to_properties(document)

        # Store or update document node
        try:
            doc_id = await self.graph_ops.merge_node(
                label=node_label,
                match_properties={"id": doc_properties["id"]},
                set_properties=doc_properties
            )

            logger.info(f"Created/updated {node_label} node: {doc_id}")

        except Exception as e:
            logger.error(f"Failed to store document node: {e}")
            raise RuntimeError(f"Document storage failed: {e}")

        # Store chunks with embeddings
        chunk_count = await self._store_chunks(
            document_id=doc_id,
            document_label=node_label,
            chunks=chunks,
            document=document
        )

        logger.info(
            f"Successfully stored document {doc_id} with {chunk_count} chunks"
        )

        return doc_id

    async def _store_chunks(
        self,
        document_id: str,
        document_label: str,
        chunks: List[ProcessedChunk],
        document: ParsedDocument
    ) -> int:
        """
        Store chunks with embeddings and create relationships to document.

        Args:
            document_id: Parent document ID
            document_label: Parent document node label
            chunks: Chunks to store
            document: Original document (for metadata)

        Returns:
            Number of chunks stored
        """
        stored_count = 0

        for idx, chunk in enumerate(chunks):
            try:
                # Create unique chunk ID
                chunk_id = self._generate_chunk_id(document_id, idx)

                # Prepare chunk properties
                chunk_props = {
                    "id": chunk_id,
                    "content": chunk.content,
                    "start_index": chunk.start_index,
                    "end_index": chunk.end_index,
                    "chunk_index": idx,
                    "doc_type": document.doc_type,
                    "source_path": document.path,
                    "section_title": chunk.section_title,
                    "section_level": chunk.section_level,
                    "created_at": datetime.utcnow().isoformat(),
                    **chunk.metadata
                }

                # Create chunk node
                await self.graph_ops.create_node(
                    label="Chunk",
                    properties=chunk_props
                )

                # Store embedding
                await self.vector_ops.store_embedding(
                    node_label="Chunk",
                    node_id=chunk_id,
                    embedding=chunk.embedding,
                    id_property="id"
                )

                # Create CONTAINS relationship
                await self.graph_ops.create_relationship(
                    from_label=document_label,
                    from_id=document_id,
                    rel_type=RelationshipTypes.CONTAINS,
                    to_label="Chunk",
                    to_id=chunk_id,
                    properties={
                        "chunk_index": idx
                    },
                    from_id_prop="id",
                    to_id_prop="id"
                )

                stored_count += 1

            except Exception as e:
                logger.error(f"Failed to store chunk {idx}: {e}")
                # Continue with other chunks

        return stored_count

    async def update_document_embedding(
        self,
        document_id: str,
        embedding: List[float],
        node_label: str
    ) -> bool:
        """
        Store or update embedding for a document node.

        Args:
            document_id: Document ID
            embedding: Embedding vector
            node_label: Node label (Architecture/Design)

        Returns:
            True if successful
        """
        try:
            await self.vector_ops.store_embedding(
                node_label=node_label,
                node_id=document_id,
                embedding=embedding,
                id_property="id"
            )
            logger.info(f"Updated embedding for {node_label} {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update document embedding: {e}")
            return False

    async def get_document_chunks(
        self,
        document_id: str,
        document_label: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a document.

        Args:
            document_id: Document ID
            document_label: Document node label

        Returns:
            List of chunk properties
        """
        query = f"""
        MATCH (d:{document_label} {{id: $doc_id}})-[r:CONTAINS]->(c:Chunk)
        RETURN c
        ORDER BY r.chunk_index
        """

        try:
            results = await self.graph_ops.query(query, {"doc_id": document_id})
            chunks = [dict(record["c"]) for record in results]
            logger.debug(f"Retrieved {len(chunks)} chunks for document {document_id}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {e}")
            return []

    async def document_exists(self, document_id: str, doc_type: str) -> bool:
        """
        Check if a document already exists in the graph.

        Args:
            document_id: Document ID to check
            doc_type: Document type (architecture/design)

        Returns:
            True if document exists
        """
        node_label = self._get_node_label(doc_type)

        try:
            node = await self.graph_ops.get_node(
                label=node_label,
                node_id=document_id,
                id_property="id"
            )
            return node is not None

        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False

    def _get_node_label(self, doc_type: str) -> str:
        """
        Map document type to node label.

        Args:
            doc_type: Document type string

        Returns:
            Node label constant

        Raises:
            ValueError: If doc_type is unsupported
        """
        type_mapping = {
            "architecture": NodeLabels.ARCHITECTURE,
            "design": NodeLabels.DESIGN,
            "code": NodeLabels.CODE_ARTIFACT,
        }

        label = type_mapping.get(doc_type.lower())
        if not label:
            raise ValueError(
                f"Unsupported document type: {doc_type}. "
                f"Supported types: {list(type_mapping.keys())}"
            )

        return label

    def _document_to_properties(self, document: ParsedDocument) -> Dict[str, Any]:
        """
        Convert ParsedDocument to graph node properties.

        Args:
            document: Parsed document

        Returns:
            Dictionary of node properties
        """
        # Base properties
        properties = {
            "id": document.frontmatter.get("id"),
            "title": document.frontmatter.get("title", ""),
            "doc_type": document.doc_type,
            "subsystem": document.frontmatter.get("subsystem", ""),
            "version": document.frontmatter.get("version", "1.0.0"),
            "status": document.frontmatter.get("status", "draft"),
            "content": document.content,
            "content_hash": document.hash,
            "path": document.path,
            "size_bytes": document.size_bytes,
            "modified_at": document.modified_at.isoformat() if document.modified_at else None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Add owners as JSON string (Neo4j handles lists)
        owners = document.frontmatter.get("owners", [])
        if isinstance(owners, list):
            properties["owners"] = owners
        else:
            properties["owners"] = [str(owners)]

        # Add architecture-specific fields
        if document.doc_type == "architecture":
            properties["compliance_level"] = document.frontmatter.get(
                "compliance_level", "strict"
            )
            properties["drift_tolerance"] = document.frontmatter.get(
                "drift_tolerance", "none"
            )

        # Add design-specific fields
        if document.doc_type == "design":
            properties["component"] = document.frontmatter.get("component", "")
            properties["architecture_ref"] = document.frontmatter.get(
                "architecture_ref", ""
            )

        # Add all other frontmatter as metadata
        # Filter out already included fields
        excluded_keys = {
            "id", "title", "doc", "subsystem", "version", "status",
            "owners", "compliance_level", "drift_tolerance", "component",
            "architecture_ref"
        }

        for key, value in document.frontmatter.items():
            if key not in excluded_keys:
                properties[f"meta_{key}"] = str(value)

        return properties

    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """
        Generate unique chunk ID.

        Args:
            document_id: Parent document ID
            chunk_index: Chunk index

        Returns:
            Unique chunk identifier
        """
        chunk_string = f"{document_id}:chunk:{chunk_index}"
        # Use hash for consistent ID format
        return hashlib.md5(chunk_string.encode()).hexdigest()[:16]
