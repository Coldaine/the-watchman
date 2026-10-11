"""
Neo4j schema definitions including node types, relationships, and indexes.

Defines the complete graph schema for the Librarian Agent system based on
the architecture specification.
"""

from typing import Optional
import logging

from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


# Node label constants
class NodeLabels:
    """Node label constants for type safety."""
    ARCHITECTURE = "Architecture"
    DESIGN = "Design"
    REQUIREMENT = "Requirement"
    CODE_ARTIFACT = "CodeArtifact"
    DECISION = "Decision"
    AGENT_REQUEST = "AgentRequest"
    PERSON = "Person"
    CHUNK = "Chunk"
    AUDIT_EVENT = "AuditEvent"


# Allowed node labels whitelist (for security - prevent Cypher injection)
ALLOWED_NODE_LABELS = {
    NodeLabels.ARCHITECTURE,
    NodeLabels.DESIGN,
    NodeLabels.REQUIREMENT,
    NodeLabels.CODE_ARTIFACT,
    NodeLabels.DECISION,
    NodeLabels.AGENT_REQUEST,
    NodeLabels.PERSON,
    NodeLabels.CHUNK,
    NodeLabels.AUDIT_EVENT,
}


# Relationship type constants
class RelationshipTypes:
    """Relationship type constants for type safety."""
    DEFINES = "DEFINES"
    IMPLEMENTS = "IMPLEMENTS"
    SATISFIES = "SATISFIES"
    SUPERSEDES = "SUPERSEDES"
    DERIVED_FROM = "DERIVED_FROM"
    INVALIDATES = "INVALIDATES"
    TARGETS = "TARGETS"
    REFERENCES = "REFERENCES"
    RESULTED_IN = "RESULTED_IN"
    APPROVES = "APPROVES"
    REJECTS = "REJECTS"
    OWNS = "OWNS"
    REVIEWED = "REVIEWED"
    AUTHORED = "AUTHORED"
    CREATED_FROM = "CREATED_FROM"
    CONTAINS = "CONTAINS"
    AUDITS = "AUDITS"
    RECORDS = "RECORDS"


# Allowed relationship types whitelist (for security - prevent Cypher injection)
ALLOWED_RELATIONSHIP_TYPES = {
    RelationshipTypes.DEFINES,
    RelationshipTypes.IMPLEMENTS,
    RelationshipTypes.SATISFIES,
    RelationshipTypes.SUPERSEDES,
    RelationshipTypes.DERIVED_FROM,
    RelationshipTypes.INVALIDATES,
    RelationshipTypes.TARGETS,
    RelationshipTypes.REFERENCES,
    RelationshipTypes.RESULTED_IN,
    RelationshipTypes.APPROVES,
    RelationshipTypes.REJECTS,
    RelationshipTypes.OWNS,
    RelationshipTypes.REVIEWED,
    RelationshipTypes.AUTHORED,
    RelationshipTypes.CREATED_FROM,
    RelationshipTypes.CONTAINS,
    RelationshipTypes.AUDITS,
    RelationshipTypes.RECORDS,
}


def validate_node_label(label: str) -> None:
    """
    Validate that node label is in the allowed whitelist.

    Prevents Cypher injection by ensuring only known labels are used in queries.

    Args:
        label: Node label to validate

    Raises:
        ValueError: If label is not in whitelist
    """
    if label not in ALLOWED_NODE_LABELS:
        raise ValueError(
            f"Invalid node label: '{label}'. "
            f"Allowed labels: {', '.join(sorted(ALLOWED_NODE_LABELS))}"
        )


def validate_relationship_type(rel_type: str) -> None:
    """
    Validate that relationship type is in the allowed whitelist.

    Prevents Cypher injection by ensuring only known relationship types are used in queries.

    Args:
        rel_type: Relationship type to validate

    Raises:
        ValueError: If relationship type is not in whitelist
    """
    if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
        raise ValueError(
            f"Invalid relationship type: '{rel_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_RELATIONSHIP_TYPES))}"
        )


# Schema creation queries
CONSTRAINT_QUERIES = [
    # Unique constraints (automatically create indexes)
    """
    CREATE CONSTRAINT arch_id_unique IF NOT EXISTS
    FOR (a:Architecture) REQUIRE a.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT design_id_unique IF NOT EXISTS
    FOR (d:Design) REQUIRE d.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT req_id_unique IF NOT EXISTS
    FOR (r:Requirement) REQUIRE r.rid IS UNIQUE
    """,
    """
    CREATE CONSTRAINT code_path_unique IF NOT EXISTS
    FOR (c:CodeArtifact) REQUIRE c.path IS UNIQUE
    """,
    """
    CREATE CONSTRAINT request_id_unique IF NOT EXISTS
    FOR (ar:AgentRequest) REQUIRE ar.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
    FOR (d:Decision) REQUIRE d.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
    FOR (c:Chunk) REQUIRE c.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT audit_id_unique IF NOT EXISTS
    FOR (a:AuditEvent) REQUIRE a.id IS UNIQUE
    """
]


def get_vector_index_query(index_name: str, node_label: str, property_name: str,
                           dimensions: int = 768, similarity: str = "cosine") -> str:
    """
    Generate vector index creation query.

    Args:
        index_name: Name of the index
        node_label: Node label to index
        property_name: Property containing the vector
        dimensions: Vector dimensions (default 768)
        similarity: Similarity function (cosine, euclidean, dot)

    Returns:
        Cypher query string
    """
    return f"""
    CREATE VECTOR INDEX {index_name} IF NOT EXISTS
    FOR (n:{node_label}) ON (n.{property_name})
    OPTIONS {{
        indexConfig: {{
            'vector.dimensions': {dimensions},
            'vector.similarity_function': '{similarity}'
        }}
    }}
    """


VECTOR_INDEX_QUERIES = [
    get_vector_index_query("arch_embedding", "Architecture", "embedding"),
    get_vector_index_query("design_embedding", "Design", "embedding"),
    get_vector_index_query("chunk_embedding", "Chunk", "embedding")
]


COMPOSITE_INDEX_QUERIES = [
    # Composite indexes for common query patterns
    """
    CREATE INDEX arch_status_subsystem IF NOT EXISTS
    FOR (a:Architecture) ON (a.status, a.subsystem)
    """,
    """
    CREATE INDEX design_status_component IF NOT EXISTS
    FOR (d:Design) ON (d.status, d.component)
    """,
    """
    CREATE INDEX req_status_priority IF NOT EXISTS
    FOR (r:Requirement) ON (r.status, r.priority)
    """,
    """
    CREATE INDEX request_agent_time IF NOT EXISTS
    FOR (ar:AgentRequest) ON (ar.agent_id, ar.timestamp)
    """,
    """
    CREATE INDEX audit_timestamp IF NOT EXISTS
    FOR (a:AuditEvent) ON (a.timestamp)
    """,
    """
    CREATE INDEX audit_agent IF NOT EXISTS
    FOR (a:AuditEvent) ON (a.agent_id)
    """,
    """
    CREATE INDEX audit_event_type IF NOT EXISTS
    FOR (a:AuditEvent) ON (a.event_type)
    """
]


FULLTEXT_INDEX_QUERIES = [
    # Full-text search indexes
    """
    CREATE FULLTEXT INDEX doc_content_search IF NOT EXISTS
    FOR (n:Architecture|Design) ON EACH [n.content, n.title]
    """
]


class SchemaManager:
    """Manages Neo4j schema creation and verification."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize schema manager.

        Args:
            connection: Neo4j connection instance
        """
        self.conn = connection

    async def create_constraints(self) -> None:
        """Create all unique constraints."""
        logger.info("Creating constraints...")

        for query in CONSTRAINT_QUERIES:
            try:
                await self.conn.execute_write(query.strip())
                logger.debug(f"Constraint created/verified")
            except Exception as e:
                logger.error(f"Failed to create constraint: {e}")
                raise

        logger.info("All constraints created successfully")

    async def create_vector_indexes(self, dimensions: int = 768,
                                   similarity: str = "cosine") -> None:
        """
        Create vector indexes for semantic search.

        Args:
            dimensions: Vector dimensions (default 768)
            similarity: Similarity function (default cosine)
        """
        logger.info(f"Creating vector indexes ({dimensions}d, {similarity})...")

        vector_queries = [
            get_vector_index_query("arch_embedding", "Architecture", "embedding",
                                 dimensions, similarity),
            get_vector_index_query("design_embedding", "Design", "embedding",
                                 dimensions, similarity)
        ]

        for query in vector_queries:
            try:
                await self.conn.execute_write(query.strip())
                logger.debug("Vector index created/verified")
            except Exception as e:
                logger.error(f"Failed to create vector index: {e}")
                raise

        logger.info("All vector indexes created successfully")

    async def create_composite_indexes(self) -> None:
        """Create composite indexes for query optimization."""
        logger.info("Creating composite indexes...")

        for query in COMPOSITE_INDEX_QUERIES:
            try:
                await self.conn.execute_write(query.strip())
                logger.debug("Composite index created/verified")
            except Exception as e:
                logger.error(f"Failed to create composite index: {e}")
                raise

        logger.info("All composite indexes created successfully")

    async def create_fulltext_indexes(self) -> None:
        """Create full-text search indexes."""
        logger.info("Creating full-text indexes...")

        for query in FULLTEXT_INDEX_QUERIES:
            try:
                await self.conn.execute_write(query.strip())
                logger.debug("Full-text index created/verified")
            except Exception as e:
                logger.error(f"Failed to create full-text index: {e}")
                raise

        logger.info("All full-text indexes created successfully")

    async def create_all_indexes(self, vector_dimensions: int = 768,
                                vector_similarity: str = "cosine") -> None:
        """
        Create all schema elements: constraints, vector indexes, composite indexes, and full-text indexes.

        Args:
            vector_dimensions: Vector dimensions for embedding indexes
            vector_similarity: Similarity function for vector search
        """
        logger.info("Creating complete schema...")

        await self.create_constraints()
        await self.create_vector_indexes(vector_dimensions, vector_similarity)
        await self.create_composite_indexes()
        await self.create_fulltext_indexes()

        logger.info("Schema creation completed successfully")

    async def verify_schema(self) -> dict:
        """
        Verify schema elements exist.

        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying schema...")

        results = {
            "constraints": [],
            "indexes": [],
            "errors": []
        }

        try:
            # Check constraints
            constraint_query = "SHOW CONSTRAINTS"
            constraints = await self.conn.execute_read(constraint_query)
            results["constraints"] = [c.get("name") for c in constraints]

            # Check indexes
            index_query = "SHOW INDEXES"
            indexes = await self.conn.execute_read(index_query)
            results["indexes"] = [i.get("name") for i in indexes]

            logger.info(f"Found {len(results['constraints'])} constraints and {len(results['indexes'])} indexes")

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            results["errors"].append(str(e))

        return results

    async def drop_all_constraints(self) -> None:
        """Drop all constraints. Use with caution!"""
        logger.warning("Dropping all constraints...")

        query = "SHOW CONSTRAINTS"
        constraints = await self.conn.execute_read(query)

        for constraint in constraints:
            name = constraint.get("name")
            drop_query = f"DROP CONSTRAINT {name} IF EXISTS"
            await self.conn.execute_write(drop_query)
            logger.debug(f"Dropped constraint: {name}")

        logger.info("All constraints dropped")

    async def drop_all_indexes(self) -> None:
        """Drop all indexes. Use with caution!"""
        logger.warning("Dropping all indexes...")

        query = "SHOW INDEXES"
        indexes = await self.conn.execute_read(query)

        for index in indexes:
            name = index.get("name")
            # Skip constraint-backed indexes (they'll be dropped with constraints)
            if not index.get("type", "").endswith("UNIQUE"):
                drop_query = f"DROP INDEX {name} IF EXISTS"
                await self.conn.execute_write(drop_query)
                logger.debug(f"Dropped index: {name}")

        logger.info("All indexes dropped")

    async def reset_schema(self, vector_dimensions: int = 768,
                          vector_similarity: str = "cosine") -> None:
        """
        Drop and recreate entire schema. Use with caution!

        Args:
            vector_dimensions: Vector dimensions for embedding indexes
            vector_similarity: Similarity function for vector search
        """
        logger.warning("Resetting schema (dropping and recreating)...")

        await self.drop_all_indexes()
        await self.drop_all_constraints()
        await self.create_all_indexes(vector_dimensions, vector_similarity)

        logger.info("Schema reset completed")
