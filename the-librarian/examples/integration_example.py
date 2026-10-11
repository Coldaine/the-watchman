"""
Example of using the integration layer to process documents.

This demonstrates the complete flow:
1. Process a document through the pipeline
2. Validate it
3. Store it in the graph database
4. Create an audit trail
"""

import asyncio
import logging
from pathlib import Path

from src.graph.connection import Neo4jConnection
from src.integration.orchestrator import LibrarianOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main example function."""

    # Configuration
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"

    # Document to process
    DOCS_DIR = Path("docs")
    SAMPLE_DOC = DOCS_DIR / "Spec_System_Architecture.md"

    logger.info("Starting integration example")

    # Step 1: Connect to Neo4j
    logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
    conn = Neo4jConnection(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD
    )

    try:
        await conn.verify_connection()
        logger.info("Connected to Neo4j successfully")

        # Step 2: Create orchestrator
        orchestrator = LibrarianOrchestrator(conn)

        # Step 3: Validate setup
        logger.info("Validating setup...")
        setup_result = await orchestrator.validate_setup()

        logger.info(f"Pipeline status: {setup_result['pipeline'].get('success', False)}")
        logger.info(f"Graph connection: {setup_result['graph'].get('connection', False)}")
        logger.info(f"Validation rules: {setup_result['validation'].get('enabled_rules', 0)} enabled")

        if not setup_result['overall']:
            logger.error("Setup validation failed!")
            logger.error(f"Pipeline errors: {setup_result['pipeline'].get('errors', [])}")
            return

        logger.info("Setup validation passed!")

        # Step 4: Process a single document
        if SAMPLE_DOC.exists():
            logger.info(f"Processing document: {SAMPLE_DOC}")

            result = await orchestrator.process_document(
                file_path=str(SAMPLE_DOC),
                skip_validation=False,  # Enable validation
                force_update=False       # Don't force if validation fails
            )

            logger.info(f"Processing result: {result.to_dict()}")

            if result.success:
                logger.info(f"✓ Document stored successfully: {result.document_id}")
                logger.info(f"  - Chunks stored: {result.chunks_stored}")
                logger.info(f"  - Processing time: {result.processing_time_ms:.2f}ms")

                if result.validation_result:
                    logger.info(f"  - Validation status: {result.validation_result.status.value}")
                    logger.info(f"  - Violations: {len(result.validation_result.violations)}")
                    logger.info(f"  - Warnings: {len(result.validation_result.warnings)}")
            else:
                logger.error(f"✗ Processing failed: {result.error}")

                if result.validation_result:
                    logger.error(f"  - Validation status: {result.validation_result.status.value}")
                    for violation in result.validation_result.violations:
                        logger.error(f"  - {violation.severity.value}: {violation.message}")

        else:
            logger.warning(f"Sample document not found: {SAMPLE_DOC}")
            logger.info("Processing entire docs directory instead...")

            # Step 5: Process entire directory
            if DOCS_DIR.exists():
                result = await orchestrator.process_directory(
                    directory=str(DOCS_DIR),
                    pattern="**/*.md",
                    skip_validation=False,
                    force_update=False
                )

                logger.info(f"Directory processing complete:")
                logger.info(f"  - Total files: {result['total_files']}")
                logger.info(f"  - Successful: {result['successful']}")
                logger.info(f"  - Failed: {result['failed']}")
                logger.info(f"  - Skipped: {result['skipped']}")

                # Show details for each file
                for file_result in result['results']:
                    file_path = file_result['file']
                    file_status = file_result['result']

                    if file_status['success']:
                        logger.info(f"  ✓ {Path(file_path).name}: {file_status['document_id']}")
                    else:
                        logger.error(f"  ✗ {Path(file_path).name}: {file_status['error']}")

            else:
                logger.error(f"Docs directory not found: {DOCS_DIR}")

        logger.info("Example completed successfully!")

    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)

    finally:
        # Step 6: Cleanup
        await conn.close()
        logger.info("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
