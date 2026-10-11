"""
Librarian orchestrator that coordinates the complete document flow.

Orchestrates the end-to-end process:
1. Document processing (parse, chunk, embed)
2. Validation against rules
3. Storage in graph database
4. Audit trail creation
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pathlib import Path

from ..processing.pipeline import IngestionPipeline
from ..processing.models import ParsedDocument, ProcessedChunk
from ..validation.engine import ValidationEngine
from ..validation.models import ValidationResult, ValidationStatus
from ..validation.agent_models import AgentRequest
from ..graph.connection import Neo4jConnection
from ..graph.operations import GraphOperations
from ..graph.vector_ops import VectorOperations

from .document_adapter import DocumentGraphAdapter
from .validation_bridge import ValidationGraphBridge
from .request_adapter import RequestAdapter
from .audit_storage import GraphAuditStorage

logger = logging.getLogger(__name__)


class OrchestrationResult:
    """Result of document orchestration."""

    def __init__(
        self,
        success: bool,
        document_id: Optional[str] = None,
        validation_result: Optional[ValidationResult] = None,
        error: Optional[str] = None,
        chunks_stored: int = 0,
        processing_time_ms: float = 0.0
    ):
        self.success = success
        self.document_id = document_id
        self.validation_result = validation_result
        self.error = error
        self.chunks_stored = chunks_stored
        self.processing_time_ms = processing_time_ms

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "document_id": self.document_id,
            "validation_status": self.validation_result.status.value if self.validation_result else None,
            "error": self.error,
            "chunks_stored": self.chunks_stored,
            "processing_time_ms": self.processing_time_ms,
            "validation_details": self.validation_result.to_dict() if self.validation_result else None
        }


class LibrarianOrchestrator:
    """Orchestrates complete document lifecycle from ingestion to storage."""

    def __init__(
        self,
        neo4j_connection: Neo4jConnection,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
        validation_engine: Optional[ValidationEngine] = None
    ):
        """
        Initialize orchestrator.

        Args:
            neo4j_connection: Neo4j connection
            ingestion_pipeline: Optional custom ingestion pipeline
            validation_engine: Optional custom validation engine
        """
        self.conn = neo4j_connection

        # Initialize components
        self.pipeline = ingestion_pipeline or IngestionPipeline()
        self.graph_ops = GraphOperations(neo4j_connection)
        self.vector_ops = VectorOperations(neo4j_connection)

        # Initialize adapters
        self.doc_adapter = DocumentGraphAdapter(self.graph_ops, self.vector_ops)
        self.val_bridge = ValidationGraphBridge(self.graph_ops)
        self.req_adapter = RequestAdapter()
        self.audit_storage = GraphAuditStorage(self.graph_ops)

        # Initialize validation engine with graph query capability
        self.validation_engine = validation_engine or ValidationEngine(
            graph_query=self.val_bridge.query_sync
        )

    async def process_document(
        self,
        file_path: str,
        skip_validation: bool = False,
        force_update: bool = False
    ) -> OrchestrationResult:
        """
        Process a document through the complete pipeline.

        Steps:
        1. Parse, chunk, and embed document
        2. Convert to validation request
        3. Validate against rules
        4. Store if approved (or force_update=True)
        5. Create audit trail

        Args:
            file_path: Path to document file
            skip_validation: Skip validation step (dangerous!)
            force_update: Store even if validation fails

        Returns:
            OrchestrationResult with outcome details
        """
        start_time = datetime.now()
        logger.info(f"Processing document: {file_path}")

        try:
            # Step 1: Process document through pipeline
            process_result = self.pipeline.process_file(file_path)

            if not process_result['success']:
                return OrchestrationResult(
                    success=False,
                    error=f"Processing failed: {process_result['error']}"
                )

            document: ParsedDocument = process_result['document']
            chunks: List[ProcessedChunk] = process_result['processed_chunks']

            logger.info(
                f"Processed document: {document.frontmatter.get('id')} "
                f"with {len(chunks)} chunks"
            )

            # Step 2: Convert to validation request
            request = self.req_adapter.document_to_request(
                document=document,
                agent_id="ingestion_pipeline",
                action="create"
            )

            # Step 3: Validate (unless skipped)
            validation_result = None
            if not skip_validation:
                logger.info(f"Validating document: {request.id}")
                validation_result = await self.validation_engine.validate_request(
                    request=request.to_dict(),
                    context={}
                )

                logger.info(
                    f"Validation result: {validation_result.status.value} "
                    f"with {len(validation_result.violations)} violations"
                )

            # Step 4: Store if approved or force_update
            should_store = (
                skip_validation or
                force_update or
                (validation_result and validation_result.passed)
            )

            document_id = None
            chunks_stored = 0

            if should_store:
                logger.info("Storing document in graph database")
                document_id = await self.doc_adapter.store_document(
                    document=document,
                    chunks=chunks
                )
                chunks_stored = len(chunks)

                logger.info(
                    f"Stored document {document_id} with {chunks_stored} chunks"
                )
            else:
                logger.warning(
                    f"Document not stored: validation status = "
                    f"{validation_result.status.value}"
                )

            # Step 5: Create audit trail (if validation occurred)
            if validation_result:
                await self.val_bridge.store_validation_result(
                    request=request,
                    result=validation_result
                )
                logger.info("Stored validation audit trail")

                # Also store in audit event system
                audit_record = {
                    "id": f"AUD-{request.id}",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "validation",
                    "request_id": request.id,
                    "agent_id": request.agent_id,
                    "target_id": document.frontmatter.get("id"),
                    "target_type": document.doc_type,
                    "decision": validation_result.status.value,
                    "result": validation_result.to_dict(),
                    "metadata": {
                        "processing_time_ms": validation_result.processing_time_ms,
                        "violations_count": len(validation_result.violations),
                        "file_path": file_path
                    }
                }
                await self.audit_storage.store_audit_record(audit_record)
                logger.debug("Stored audit event")

            # Calculate processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return OrchestrationResult(
                success=should_store,
                document_id=document_id,
                validation_result=validation_result,
                chunks_stored=chunks_stored,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return OrchestrationResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time_ms
            )

    async def process_directory(
        self,
        directory: str,
        pattern: str = "**/*.md",
        skip_validation: bool = False,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Process all documents in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for file matching
            skip_validation: Skip validation for all files
            force_update: Force storage even if validation fails

        Returns:
            Summary report with results for each file
        """
        logger.info(f"Processing directory: {directory} (pattern: {pattern})")

        # Find all matching files
        dir_path = Path(directory)
        files = list(dir_path.glob(pattern))

        logger.info(f"Found {len(files)} files to process")

        results = []
        successful = 0
        failed = 0
        skipped = 0

        for file_path in files:
            file_str = str(file_path)

            # Check if parser can handle this file
            if not self.pipeline.parser.can_parse(file_str):
                logger.info(f"Skipping unsupported file: {file_str}")
                skipped += 1
                continue

            # Process file
            result = await self.process_document(
                file_path=file_str,
                skip_validation=skip_validation,
                force_update=force_update
            )

            results.append({
                "file": file_str,
                "result": result.to_dict()
            })

            if result.success:
                successful += 1
            else:
                failed += 1

        logger.info(
            f"Directory processing complete: "
            f"{successful} successful, {failed} failed, {skipped} skipped"
        )

        return {
            "directory": directory,
            "pattern": pattern,
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "results": results
        }

    async def update_document(
        self,
        file_path: str,
        skip_validation: bool = False
    ) -> OrchestrationResult:
        """
        Update an existing document.

        Similar to process_document but marks the action as 'update'
        and performs drift detection.

        Args:
            file_path: Path to document file
            skip_validation: Skip validation step

        Returns:
            OrchestrationResult
        """
        start_time = datetime.now()
        logger.info(f"Updating document: {file_path}")

        try:
            # Process document
            process_result = self.pipeline.process_file(file_path)

            if not process_result['success']:
                return OrchestrationResult(
                    success=False,
                    error=f"Processing failed: {process_result['error']}"
                )

            document: ParsedDocument = process_result['document']
            chunks: List[ProcessedChunk] = process_result['processed_chunks']

            # Convert to validation request with 'update' action
            request = self.req_adapter.document_to_request(
                document=document,
                agent_id="ingestion_pipeline",
                action="update",
                target_id=document.frontmatter.get("id")
            )

            # Validate
            validation_result = None
            if not skip_validation:
                validation_result = await self.validation_engine.validate_request(
                    request=request.to_dict(),
                    context={}
                )

            # Store if approved
            should_store = skip_validation or (
                validation_result and validation_result.passed
            )

            document_id = None
            chunks_stored = 0

            if should_store:
                # For updates, store will use merge (create or update)
                document_id = await self.doc_adapter.store_document(
                    document=document,
                    chunks=chunks
                )
                chunks_stored = len(chunks)

                logger.info(f"Updated document {document_id}")

            # Store audit trail
            if validation_result:
                await self.val_bridge.store_validation_result(
                    request=request,
                    result=validation_result
                )

                # Also store in audit event system
                audit_record = {
                    "id": f"AUD-{request.id}",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "validation",
                    "request_id": request.id,
                    "agent_id": request.agent_id,
                    "target_id": document.frontmatter.get("id"),
                    "target_type": document.doc_type,
                    "decision": validation_result.status.value,
                    "result": validation_result.to_dict(),
                    "metadata": {
                        "processing_time_ms": validation_result.processing_time_ms,
                        "violations_count": len(validation_result.violations),
                        "file_path": file_path,
                        "action": "update"
                    }
                }
                await self.audit_storage.store_audit_record(audit_record)

            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return OrchestrationResult(
                success=should_store,
                document_id=document_id,
                validation_result=validation_result,
                chunks_stored=chunks_stored,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return OrchestrationResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time_ms
            )

    async def validate_setup(self) -> Dict[str, Any]:
        """
        Validate that all components are properly configured.

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating orchestrator setup")

        results = {
            "pipeline": {},
            "graph": {},
            "validation": {},
            "overall": False
        }

        # Check pipeline
        results["pipeline"] = self.pipeline.validate_setup()

        # Check graph connection
        try:
            await self.conn.verify_connection()
            results["graph"]["connection"] = True
        except Exception as e:
            results["graph"]["connection"] = False
            results["graph"]["error"] = str(e)

        # Check validation engine
        results["validation"]["rules_loaded"] = len(self.validation_engine.rules)
        results["validation"]["enabled_rules"] = len(
            [r for r in self.validation_engine.rules if r.enabled]
        )

        # Overall status
        results["overall"] = (
            results["pipeline"].get("success", False) and
            results["graph"].get("connection", False) and
            results["validation"]["rules_loaded"] > 0
        )

        logger.info(f"Setup validation complete: {results['overall']}")

        return results
