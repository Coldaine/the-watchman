"""Query endpoints for semantic search and Cypher queries."""

from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional

from src.api.models import SemanticQueryRequest, SemanticQueryResponse, CypherQueryResponse
from src.graph.connection import get_connection
from src.graph.vector_ops import VectorOperations
from src.processing.embedder import EmbeddingGenerator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
vector_ops = None
embedder = None


def get_vector_ops() -> VectorOperations:
    """Get or create vector operations instance."""
    global vector_ops
    if vector_ops is None:
        conn = get_connection()
        vector_ops = VectorOperations(connection=conn)
    return vector_ops


def get_embedder() -> EmbeddingGenerator:
    """Get or create embedder instance."""
    global embedder
    if embedder is None:
        embedder = EmbeddingGenerator()
    return embedder


@router.post("/semantic", response_model=SemanticQueryResponse)
async def semantic_search(request: SemanticQueryRequest):
    """
    Perform semantic search across specifications.

    Generates an embedding for the query and searches for similar documents
    using vector similarity in Neo4j.

    Args:
        request: Search query with context type and limit

    Returns:
        SemanticQueryResponse with ranked results
    """
    try:
        logger.info(f"Semantic search query: '{request.query[:50]}...' type={request.context_type}")

        # Generate embedding for query
        emb = get_embedder()
        query_embedding = emb.generate_embedding(request.query)

        # Determine which node labels to search
        if request.context_type == "architecture":
            node_labels = ["Architecture"]
        elif request.context_type == "design":
            node_labels = ["Design"]
        else:  # all
            node_labels = ["Architecture", "Design"]

        # Search across specified node types
        ops = get_vector_ops()
        all_results = []

        for label in node_labels:
            try:
                results = await ops.vector_search(
                    query_embedding=query_embedding.tolist(),
                    node_label=label,
                    limit=request.limit,
                    threshold=0.3  # Minimum similarity score
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for {label}: {e}")
                continue

        # Sort by score and limit
        all_results.sort(key=lambda x: x['score'], reverse=True)
        all_results = all_results[:request.limit]

        # Format results
        formatted_results = []
        for result in all_results:
            node = result['node']
            formatted_results.append({
                "id": node.get('id', 'unknown'),
                "type": node.get('doc_type', 'unknown'),
                "content": node.get('content', '')[:500],  # Truncate for response
                "relevance_score": result['score'],
                "metadata": {
                    "title": node.get('title'),
                    "version": node.get('version'),
                    "status": node.get('status'),
                    "subsystem": node.get('subsystem')
                }
            })

        logger.info(f"Semantic search returned {len(formatted_results)} results")

        return SemanticQueryResponse(results=formatted_results)

    except Exception as e:
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/cypher", response_model=CypherQueryResponse)
async def cypher_query(q: str = Query(..., description="Cypher query to execute")):
    """
    Execute a read-only Cypher query against the graph database.

    For security, only SELECT/MATCH queries are allowed. No mutations.

    Args:
        q: Cypher query string (must be read-only)

    Returns:
        CypherQueryResponse with query results
    """
    try:
        # Security check: only allow read queries
        query_upper = q.strip().upper()
        disallowed_keywords = [
            'CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE',
            'DROP', 'DETACH', 'FOREACH'
        ]

        for keyword in disallowed_keywords:
            if keyword in query_upper:
                raise HTTPException(
                    status_code=403,
                    detail=f"Write operations not allowed. Found: {keyword}"
                )

        logger.info(f"Executing Cypher query: {q[:100]}...")

        # Execute query
        conn = get_connection()
        results = await conn.execute_read(q)

        logger.info(f"Cypher query returned {len(results)} results")

        return CypherQueryResponse(results=results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cypher query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.get("/similar/{node_id}", response_model=SemanticQueryResponse)
async def find_similar(
    node_id: str,
    node_type: str = Query("Architecture", description="Node type (Architecture or Design)"),
    limit: int = Query(5, ge=1, le=20, description="Number of similar documents")
):
    """
    Find documents similar to a specific document.

    Uses the document's embedding to find semantically similar documents.

    Args:
        node_id: ID of the source document
        node_type: Type of the source document
        limit: Maximum number of results

    Returns:
        SemanticQueryResponse with similar documents
    """
    try:
        logger.info(f"Finding documents similar to {node_type}:{node_id}")

        ops = get_vector_ops()
        results = await ops.find_similar_documents(
            document_id=node_id,
            node_label=node_type,
            limit=limit
        )

        # Format results
        formatted_results = []
        for result in results:
            node = result['node']
            formatted_results.append({
                "id": node.get('id', 'unknown'),
                "type": node.get('doc_type', 'unknown'),
                "content": node.get('content', '')[:500],
                "relevance_score": result['score'],
                "metadata": {
                    "title": node.get('title'),
                    "version": node.get('version'),
                    "status": node.get('status')
                }
            })

        logger.info(f"Found {len(formatted_results)} similar documents")

        return SemanticQueryResponse(results=formatted_results)

    except Exception as e:
        logger.error(f"Similar document search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
