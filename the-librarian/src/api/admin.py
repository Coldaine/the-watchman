"""Administrative endpoints for document ingestion and management."""

from fastapi import APIRouter, HTTPException, UploadFile, File
import logging
from pathlib import Path
import tempfile
import os

from src.api.models import IngestRequest, IngestResponse
from src.processing.pipeline import IngestionPipeline
from src.graph.connection import get_connection
from src.graph.operations import GraphOperations

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
doc_processor = None
graph_ops = None


def get_doc_processor() -> IngestionPipeline:
    """Get or create document processor instance."""
    global doc_processor
    if doc_processor is None:
        doc_processor = IngestionPipeline()
    return doc_processor


def get_graph_ops() -> GraphOperations:
    """Get or create graph operations instance."""
    global graph_ops
    if graph_ops is None:
        conn = get_connection()
        graph_ops = GraphOperations(connection=conn)
    return graph_ops


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """
    Ingest a document into the knowledge graph.

    Processes the document (parsing, chunking, embedding) and stores it
    in Neo4j with appropriate relationships.

    Args:
        request: Document path, type, and metadata

    Returns:
        IngestResponse with node ID and relationship count
    """
    try:
        logger.info(f"Ingesting document: {request.document_path} ({request.document_type})")

        # Verify file exists
        doc_path = Path(request.document_path)
        if not doc_path.exists():
            raise HTTPException(status_code=404, detail=f"Document not found: {request.document_path}")

        # Process document through pipeline
        processor = get_doc_processor()

        # Process the file
        processed = processor.process_file(str(doc_path))

        if not processed.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {processed.get('error', 'Unknown error')}"
            )

        # Store in graph database
        ops = get_graph_ops()

        # Get processed document
        document = processed.get('document')

        # Create main document node
        node_id = document.frontmatter.get('id', f"{request.document_type}-{doc_path.stem}")

        # Build node properties from document metadata
        node_props = {
            "id": node_id,
            "title": document.frontmatter.get("title", doc_path.stem),
            "doc_type": request.document_type,
            "content": document.content[:1000] if document.content else "",  # Store truncated content
            "source_path": str(doc_path),
            "status": "active",
            "version": document.frontmatter.get("version", "1.0.0"),
            "subsystem": document.frontmatter.get("subsystem", "general"),
            **request.metadata
        }

        # Determine node label based on document type
        label_map = {
            "architecture": "Architecture",
            "design": "Design",
            "code": "Code",
            "research": "Research"
        }
        node_label = label_map.get(request.document_type, "Document")

        # Create node
        await ops.create_node(
            label=node_label,
            properties=node_props
        )

        # Store chunks as related nodes
        relationships_created = 0
        processed_chunks = processed.get("processed_chunks", [])

        for i, chunk in enumerate(processed_chunks):
            chunk_id = f"{node_id}-chunk-{i}"
            chunk_props = {
                "id": chunk_id,
                "content": chunk.content,
                "start_index": chunk.start_index,
                "end_index": chunk.end_index,
                "section_title": chunk.section_title,
                "embedding": chunk.embedding
            }

            # Create chunk node
            await ops.create_node(
                label="Chunk",
                properties=chunk_props
            )

            # Create relationship
            await ops.create_relationship(
                from_label=node_label,
                from_id=node_id,
                to_label="Chunk",
                to_id=chunk_id,
                rel_type="HAS_CHUNK",
                properties={"chunk_index": i}
            )
            relationships_created += 1

        logger.info(
            f"Document ingested successfully: {node_id}, "
            f"{len(processed_chunks)} chunks, {relationships_created} relationships"
        )

        return IngestResponse(
            success=True,
            node_id=node_id,
            relationships_created=relationships_created
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest-file", response_model=IngestResponse)
async def ingest_file_upload(
    file: UploadFile = File(...),
    document_type: str = "architecture",
    subsystem: str = "general"
):
    """
    Ingest a document via file upload.

    Alternative to path-based ingestion. Uploads the file and processes it.

    Args:
        file: Uploaded file
        document_type: Type of document
        subsystem: Subsystem this document belongs to

    Returns:
        IngestResponse with node ID and relationship count
    """
    try:
        logger.info(f"Ingesting uploaded file: {file.filename} ({document_type})")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Use the ingest_document logic with the temp file
            request = IngestRequest(
                document_path=tmp_path,
                document_type=document_type,
                metadata={
                    "filename": file.filename,
                    "subsystem": subsystem,
                    "uploaded": True
                }
            )

            response = await ingest_document(request)
            return response

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload ingestion failed: {str(e)}")


@router.delete("/document/{node_id}")
async def delete_document(node_id: str):
    """
    Delete a document and its associated chunks from the graph.

    Args:
        node_id: ID of the document to delete

    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting document: {node_id}")

        conn = get_connection()

        # Delete document and all its chunks
        delete_query = """
        MATCH (d {id: $node_id})
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
        DETACH DELETE d, c
        RETURN count(d) + count(c) as deleted_count
        """

        result = await conn.execute_write(delete_query, {"node_id": node_id})
        deleted_count = result[0].get("deleted_count", 0) if result else 0

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Document not found: {node_id}")

        logger.info(f"Deleted document {node_id} and {deleted_count} related nodes")

        return {"success": True, "deleted_count": deleted_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/documents")
async def list_documents(doc_type: str = None, subsystem: str = None, limit: int = 50):
    """
    List all documents in the knowledge graph.

    Args:
        doc_type: Filter by document type (optional)
        subsystem: Filter by subsystem (optional)
        limit: Maximum number of results

    Returns:
        List of documents with metadata
    """
    try:
        logger.info(f"Listing documents (type={doc_type}, subsystem={subsystem}, limit={limit})")

        conn = get_connection()

        # Build query with optional filters
        where_clauses = []
        params = {"limit": limit}

        if doc_type:
            where_clauses.append("d.doc_type = $doc_type")
            params["doc_type"] = doc_type

        if subsystem:
            where_clauses.append("d.subsystem = $subsystem")
            params["subsystem"] = subsystem

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
        MATCH (d)
        {where_clause}
        RETURN d.id as id, d.title as title, d.doc_type as doc_type,
               d.subsystem as subsystem, d.version as version,
               d.status as status, d.created_at as created_at
        ORDER BY d.created_at DESC
        LIMIT $limit
        """

        results = await conn.execute_read(query, params)

        documents = []
        for r in results:
            documents.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "doc_type": r.get("doc_type"),
                "subsystem": r.get("subsystem"),
                "version": r.get("version"),
                "status": r.get("status"),
                "created_at": str(r.get("created_at")) if r.get("created_at") else None
            })

        logger.info(f"Found {len(documents)} documents")

        return {"documents": documents, "count": len(documents)}

    except Exception as e:
        logger.error(f"Document listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")
