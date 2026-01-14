#!/usr/bin/env python3
"""
Initialize Neo4j schema with constraints and indexes.

This script reads the Cypher schema file and executes each statement
to set up the Watchman database schema.

Usage:
    python scripts/init_schema.py
"""

import sys
from pathlib import Path

from loguru import logger
from neo4j import GraphDatabase

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.config import get_settings


def read_schema_file(filepath: Path) -> list[str]:
    """
    Read Cypher schema file and split into individual statements.

    Ignores comments and empty lines.
    """
    with open(filepath) as f:
        content = f.read()

    # Split by semicolons, filter out comments and empty lines
    statements = []
    for stmt in content.split(";"):
        # Remove comment lines
        lines = [line for line in stmt.split("\n") if not line.strip().startswith("//")]
        stmt_clean = "\n".join(lines).strip()

        if stmt_clean:
            statements.append(stmt_clean)

    return statements


def execute_schema_statements(driver, statements: list[str]):
    """Execute schema statements one by one."""
    success_count = 0
    failed_count = 0

    with driver.session() as session:
        for i, statement in enumerate(statements, 1):
            try:
                logger.info(f"Executing statement {i}/{len(statements)}...")
                logger.debug(f"Statement: {statement[:100]}...")

                result = session.run(statement)
                result.consume()

                logger.success(f"Statement {i} executed successfully")
                success_count += 1

            except Exception as e:
                # Some statements may fail if already exist - that's okay
                if "already exists" in str(e) or "equivalent" in str(e):
                    logger.warning(f"Statement {i} already applied: {e}")
                    success_count += 1
                else:
                    logger.error(f"Statement {i} failed: {e}")
                    failed_count += 1

    return success_count, failed_count


def verify_schema(driver):
    """Verify schema setup by listing constraints and indexes."""
    with driver.session() as session:
        logger.info("\n=== Constraints ===")
        constraints = session.run("SHOW CONSTRAINTS")
        for record in constraints:
            logger.info(f"  {record.get('name', 'N/A')}: {record.get('type', 'N/A')}")

        logger.info("\n=== Indexes ===")
        indexes = session.run("SHOW INDEXES")
        for record in indexes:
            logger.info(f"  {record.get('name', 'N/A')}: {record.get('type', 'N/A')}")


def main():
    """Main initialization function."""
    logger.info("Starting Neo4j schema initialization...")

    # Load settings
    settings = get_settings()

    # Connect to Neo4j
    logger.info(f"Connecting to Neo4j at {settings.neo4j_uri}...")
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        # Verify connection
        driver.verify_connectivity()
        logger.success("Connected to Neo4j successfully")

        # Read schema file
        schema_path = Path(__file__).parent.parent / "schemas" / "contracts.cypher"
        logger.info(f"Reading schema from {schema_path}...")
        statements = read_schema_file(schema_path)
        logger.info(f"Found {len(statements)} statements to execute")

        # Execute statements
        success, failed = execute_schema_statements(driver, statements)

        logger.info("\n=== Results ===")
        logger.info(f"  Success: {success}")
        logger.info(f"  Failed: {failed}")

        # Verify schema
        verify_schema(driver)

        if failed == 0:
            logger.success("\n✓ Schema initialization completed successfully!")
            return 0
        else:
            logger.warning(f"\n⚠ Schema initialization completed with {failed} failures")
            return 1

    except Exception as e:
        logger.error(f"Schema initialization failed: {e}")
        return 1

    finally:
        driver.close()
        logger.info("Disconnected from Neo4j")


if __name__ == "__main__":
    sys.exit(main())
