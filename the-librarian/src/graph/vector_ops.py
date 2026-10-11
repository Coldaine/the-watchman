"""
Vector operations for semantic search using Neo4j native vector indexes.

Provides functionality for storing embeddings and performing vector similarity
searches across Architecture and Design documents.
"""

from typing import List, Dict, Optional, Any
import logging
import numpy as np

from .connection import Neo4jConnection
from .schema import NodeLabels
from .config import get_config

logger = logging.getLogger(__name__)


class VectorOperations:
    """Vector storage and search operations."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize vector operations.

        Args:
            connection: Neo4j connection instance
        """
        self.conn = connection
        self.config = get_config()

    async def store_embedding(self, node_label: str, node_id: str,
                             embedding: List[float],
                             id_property: str = "id") -> bool:
        """
        Store or update embedding vector for a node.

        Args:
            node_label: Node label (Architecture or Design)
            node_id: Node identifier
            embedding: Embedding vector (should match configured dimensions)
            id_property: Property name that holds the ID (default: "id")

        Returns:
            True if successful

        Raises:
            ValueError: If embedding dimensions don't match configuration
        """
        if len(embedding) != self.config.vector_dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.config.vector_dimensions}, "
                f"got {len(embedding)}"
            )

        query = f"""
        MATCH (n:{node_label} {{{id_property}: $node_id}})
        SET n.embedding = $embedding,
            n.embedding_model = $model,
            n.embedding_date = datetime()
        RETURN n.{id_property} as node_id
        """

        try:
            result = await self.conn.execute_write(query, {
                "node_id": node_id,
                "embedding": embedding,
                "model": "nomic-embed-text"  # Could be parameterized
            })

            if result:
                logger.info(f"Stored embedding for {node_label} node: {node_id}")
                return True
            else:
                raise ValueError(f"Node not found: {node_label} {node_id}")

        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            raise

    async def vector_search(self, query_embedding: List[float],
                           node_label: str = "Architecture",
                           limit: int = 10,
                           threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query_embedding: Query vector
            node_label: Node label to search (Architecture or Design)
            limit: Maximum number of results
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of dictionaries with 'node' and 'score' keys, sorted by score descending

        Raises:
            ValueError: If embedding dimensions don't match or invalid node label
        """
        if len(query_embedding) != self.config.vector_dimensions:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self.config.vector_dimensions}, "
                f"got {len(query_embedding)}"
            )

        # Determine index name based on label
        index_names = {
            NodeLabels.ARCHITECTURE: "arch_embedding",
            NodeLabels.DESIGN: "design_embedding"
        }

        index_name = index_names.get(node_label)
        if not index_name:
            raise ValueError(f"No vector index for node label: {node_label}")

        query = f"""
        CALL db.index.vector.queryNodes($index_name, $limit, $embedding)
        YIELD node, score
        WHERE score > $threshold
        RETURN node, score
        ORDER BY score DESC
        """

        try:
            results = await self.conn.execute_read(query, {
                "index_name": index_name,
                "limit": limit,
                "embedding": query_embedding,
                "threshold": threshold
            })

            # Convert results to a more usable format
            formatted_results = []
            for record in results:
                formatted_results.append({
                    "node": dict(record["node"]),
                    "score": record["score"]
                })

            logger.info(f"Vector search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def hybrid_search(self, query_embedding: List[float],
                           filters: Optional[Dict[str, Any]] = None,
                           node_label: str = "Architecture",
                           limit: int = 10,
                           threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity with property filters.

        Args:
            query_embedding: Query vector
            filters: Dictionary of property filters (e.g., {"status": "approved", "subsystem": "auth"})
            node_label: Node label to search
            limit: Maximum number of results
            threshold: Minimum similarity score

        Returns:
            List of dictionaries with 'node' and 'score' keys
        """
        if len(query_embedding) != self.config.vector_dimensions:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self.config.vector_dimensions}, "
                f"got {len(query_embedding)}"
            )

        filters = filters or {}

        # Determine index name
        index_names = {
            NodeLabels.ARCHITECTURE: "arch_embedding",
            NodeLabels.DESIGN: "design_embedding"
        }

        index_name = index_names.get(node_label)
        if not index_name:
            raise ValueError(f"No vector index for node label: {node_label}")

        # Build filter conditions
        filter_conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                filter_conditions.append(f"node.{key} = ${key}")
            elif isinstance(value, list):
                filter_conditions.append(f"node.{key} IN ${key}")
            else:
                filter_conditions.append(f"node.{key} = ${key}")

        where_clause = " AND ".join(filter_conditions) if filter_conditions else "TRUE"

        query = f"""
        CALL db.index.vector.queryNodes($index_name, $limit * 2, $embedding)
        YIELD node, score
        WHERE score > $threshold AND {where_clause}
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """

        params = {
            "index_name": index_name,
            "limit": limit,
            "embedding": query_embedding,
            "threshold": threshold,
            **filters
        }

        try:
            results = await self.conn.execute_read(query, params)

            formatted_results = []
            for record in results:
                formatted_results.append({
                    "node": dict(record["node"]),
                    "score": record["score"]
                })

            logger.info(f"Hybrid search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise

    async def find_similar_documents(self, document_id: str,
                                    node_label: str = "Architecture",
                                    limit: int = 5,
                                    id_property: str = "id") -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.

        Args:
            document_id: ID of the source document
            node_label: Node label of the source document
            limit: Maximum number of similar documents to return
            id_property: Property name that holds the ID

        Returns:
            List of similar documents with similarity scores
        """
        # First, get the embedding of the source document
        get_embedding_query = f"""
        MATCH (n:{node_label} {{{id_property}: $document_id}})
        RETURN n.embedding as embedding
        """

        try:
            result = await self.conn.execute_read(get_embedding_query, {
                "document_id": document_id
            })

            if not result or not result[0].get("embedding"):
                raise ValueError(f"Document not found or has no embedding: {document_id}")

            source_embedding = result[0]["embedding"]

            # Now search for similar documents (excluding the source)
            index_names = {
                NodeLabels.ARCHITECTURE: "arch_embedding",
                NodeLabels.DESIGN: "design_embedding"
            }

            index_name = index_names.get(node_label)
            if not index_name:
                raise ValueError(f"No vector index for node label: {node_label}")

            search_query = f"""
            CALL db.index.vector.queryNodes($index_name, $limit + 1, $embedding)
            YIELD node, score
            WHERE node.{id_property} <> $document_id
            RETURN node, score
            ORDER BY score DESC
            LIMIT $limit
            """

            results = await self.conn.execute_read(search_query, {
                "index_name": index_name,
                "limit": limit,
                "embedding": source_embedding,
                "document_id": document_id
            })

            formatted_results = []
            for record in results:
                formatted_results.append({
                    "node": dict(record["node"]),
                    "score": record["score"]
                })

            logger.info(f"Found {len(formatted_results)} similar documents to {document_id}")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to find similar documents: {e}")
            raise

    async def batch_store_embeddings(self, embeddings_data: List[Dict[str, Any]],
                                    node_label: str = "Architecture",
                                    id_property: str = "id") -> int:
        """
        Store embeddings for multiple nodes in batch.

        Args:
            embeddings_data: List of dicts with 'node_id' and 'embedding' keys
            node_label: Node label
            id_property: Property name that holds the ID

        Returns:
            Number of embeddings successfully stored
        """
        count = 0

        for data in embeddings_data:
            try:
                await self.store_embedding(
                    node_label=node_label,
                    node_id=data["node_id"],
                    embedding=data["embedding"],
                    id_property=id_property
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to store embedding for {data['node_id']}: {e}")
                # Continue with other embeddings

        logger.info(f"Stored {count}/{len(embeddings_data)} embeddings successfully")
        return count

    async def semantic_search(self, query_embedding: List[float],
                             limit: int = 10,
                             doc_type: Optional[str] = None,
                             threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform semantic search on chunks, returning chunk-level results with parent document context.

        This is the primary search method for production use, searching across all Chunk nodes
        and returning fine-grained results with document context.

        Args:
            query_embedding: Query embedding vector (768 dimensions)
            limit: Maximum number of chunks to return
            doc_type: Optional document type filter ("architecture", "design", etc.)
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of dictionaries containing:
                - chunk_id: Unique chunk identifier
                - chunk_content: The matching chunk text
                - chunk_index: Position within parent document
                - section_title: Section the chunk belongs to
                - doc_id: Parent document ID
                - doc_title: Parent document title
                - doc_type: Document type
                - score: Similarity score

        Raises:
            ValueError: If embedding dimensions don't match configuration
        """
        if len(query_embedding) != self.config.vector_dimensions:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self.config.vector_dimensions}, "
                f"got {len(query_embedding)}"
            )

        # Build Cypher query to search chunks and get parent document info
        query = """
        CALL db.index.vector.queryNodes('chunk_embedding', $limit * 2, $embedding)
        YIELD node, score
        WHERE score > $threshold

        // Get parent document
        MATCH (doc)-[:CONTAINS]->(node)
        WHERE $doc_type IS NULL OR node.doc_type = $doc_type

        RETURN
            node.id as chunk_id,
            node.content as chunk_content,
            node.chunk_index as chunk_index,
            node.section_title as section_title,
            node.section_level as section_level,
            doc.id as doc_id,
            doc.title as doc_title,
            doc.doc_type as doc_type,
            doc.version as doc_version,
            score
        ORDER BY score DESC
        LIMIT $limit
        """

        try:
            results = await self.conn.execute_read(query, {
                "embedding": query_embedding,
                "limit": limit,
                "threshold": threshold,
                "doc_type": doc_type
            })

            formatted_results = []
            for record in results:
                formatted_results.append({
                    "chunk_id": record["chunk_id"],
                    "chunk_content": record["chunk_content"],
                    "chunk_index": record["chunk_index"],
                    "section_title": record["section_title"],
                    "section_level": record["section_level"],
                    "doc_id": record["doc_id"],
                    "doc_title": record["doc_title"],
                    "doc_type": record["doc_type"],
                    "doc_version": record["doc_version"],
                    "score": record["score"]
                })

            logger.info(f"Semantic search returned {len(formatted_results)} chunks across documents")
            return formatted_results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (-1 to 1)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return float(dot_product / (norm_v1 * norm_v2))

    async def get_nodes_without_embeddings(self, node_label: str = "Architecture",
                                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find nodes that don't have embeddings yet.

        Args:
            node_label: Node label to check
            limit: Maximum number of nodes to return

        Returns:
            List of nodes without embeddings
        """
        query = f"""
        MATCH (n:{node_label})
        WHERE n.embedding IS NULL
        RETURN n
        LIMIT $limit
        """

        try:
            results = await self.conn.execute_read(query, {"limit": limit})
            nodes = [dict(record["n"]) for record in results]

            logger.info(f"Found {len(nodes)} {node_label} nodes without embeddings")
            return nodes

        except Exception as e:
            logger.error(f"Failed to get nodes without embeddings: {e}")
            raise
