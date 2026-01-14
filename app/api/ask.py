"""
Query endpoint for natural language questions.

This endpoint will route to different query types:
- Locate: Find files, projects, services
- Changed: Recent changes and events
- Find text: Vector search over OCR/docs
- Status: MCP/container/service status
"""

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

router = APIRouter()


class AskRequest(BaseModel):
    """Ask endpoint request model."""

    query: str
    context: str | None = None
    limit: int = 10


class Source(BaseModel):
    """Source reference in response."""

    type: str
    path: str | None = None
    timestamp: str | None = None
    entity_id: str | None = None


class AskResponse(BaseModel):
    """Ask endpoint response model."""

    answer: str
    sources: list[Source]
    query_type: str
    cypher_query: str | None = None


@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a natural language question.

    The system will:
    1. Classify the intent (locate, changed, find_text, status)
    2. Build appropriate query (Cypher or vector search)
    3. Execute query against Neo4j
    4. Format response with sources

    Examples:
        - "Where is my docker-compose.yml?"
        - "What changed in /etc today?"
        - "Find OCR text about TLS cert"
        - "Which MCP servers are running?"
    """
    logger.info(f"Received question: {request.query}")

    # TODO: Implement in Phase 2
    # For now, return stub response

    return AskResponse(
        answer=f"Query '{request.query}' received. Full implementation coming in Phase 2.",
        sources=[],
        query_type="unknown",
        cypher_query=None,
    )


@router.post("/ingest")
async def ingest_document(path: str, doc_type: str | None = None):
    """
    Manually ingest a document into the knowledge graph.

    Args:
        path: Path to document
        doc_type: Optional document type hint

    Returns:
        Ingestion status
    """
    logger.info(f"Manual ingestion requested for: {path}")

    # TODO: Implement in Phase 1 (System Graph)

    return {"status": "queued", "path": path, "message": "Document queued for ingestion"}
