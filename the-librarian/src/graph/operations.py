"""
Core graph operations for CRUD operations on nodes and relationships.

Provides a high-level interface for creating, reading, updating, and deleting
nodes and relationships in the Neo4j graph database.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import hashlib
import json
import re

from .connection import Neo4jConnection
from .schema import (
    NodeLabels,
    RelationshipTypes,
    validate_node_label,
    validate_relationship_type,
    ALLOWED_NODE_LABELS,
)

logger = logging.getLogger(__name__)


def sanitize_cypher_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize Cypher query parameters to prevent injection attacks.

    Args:
        params: Dictionary of query parameters

    Returns:
        Sanitized parameters

    Raises:
        ValueError: If parameters contain suspicious patterns
    """
    sanitized = {}

    # Patterns that might indicate injection attempts
    dangerous_patterns = [
        r'MATCH\s+\(',  # MATCH clause
        r'CREATE\s+\(', # CREATE clause
        r'MERGE\s+\(',  # MERGE clause
        r'DELETE\s+',   # DELETE clause
        r'SET\s+',      # SET clause
        r'REMOVE\s+',   # REMOVE clause
        r'DROP\s+',     # DROP clause
        r'DETACH\s+',   # DETACH clause
        r'CALL\s+',     # CALL clause (procedures)
        r'RETURN\s+',   # RETURN clause
        r'WHERE\s+',    # WHERE clause
        r'WITH\s+',     # WITH clause
        r'UNION\s+',    # UNION clause
    ]

    for key, value in params.items():
        if isinstance(value, str):
            # Check for suspicious patterns in string values
            for pattern in dangerous_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    raise ValueError(
                        f"Potentially dangerous pattern detected in parameter '{key}': {pattern}"
                    )

            # Check for common injection techniques
            if '/*' in value or '*/' in value:
                raise ValueError(f"SQL-style comments not allowed in parameter '{key}'")

            if '--' in value:
                raise ValueError(f"Comment syntax not allowed in parameter '{key}'")

            sanitized[key] = value
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_cypher_params(value)
        else:
            # Numbers, booleans, None are safe
            sanitized[key] = value

    return sanitized


def validate_label(label: str) -> bool:
    """
    Validate that a label is from the allowed set.

    DEPRECATED: Use validate_node_label() from schema module instead.

    Args:
        label: Node label to validate

    Returns:
        True if valid, False otherwise
    """
    return label in ALLOWED_NODE_LABELS


class GraphOperations:
    """High-level graph database operations."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize graph operations.

        Args:
            connection: Neo4j connection instance
        """
        self.conn = connection

    async def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """
        Create a new node with the given label and properties.

        Args:
            label: Node label (e.g., "Architecture", "Design")
            properties: Dictionary of node properties

        Returns:
            Node ID (value of 'id', 'rid', or 'path' property depending on node type)

        Raises:
            ValueError: If node already exists or required properties missing
        """
        # Validate label (prevents Cypher injection)
        validate_node_label(label)

        # Sanitize properties
        properties = sanitize_cypher_params(properties)

        # Determine the unique identifier property based on label
        id_props = {
            NodeLabels.ARCHITECTURE: "id",
            NodeLabels.DESIGN: "id",
            NodeLabels.REQUIREMENT: "rid",
            NodeLabels.CODE_ARTIFACT: "path",
            NodeLabels.DECISION: "id",
            NodeLabels.AGENT_REQUEST: "id"
        }

        id_prop = id_props.get(label)
        if not id_prop:
            raise ValueError(f"Unknown node label: {label}")

        if id_prop not in properties:
            raise ValueError(f"Missing required property '{id_prop}' for {label} node")

        node_id = properties[id_prop]

        # Add timestamps if not present
        if "created_at" not in properties and label in [NodeLabels.ARCHITECTURE, NodeLabels.DESIGN]:
            properties["created_at"] = datetime.utcnow().isoformat()

        if "modified_at" not in properties and label in [NodeLabels.ARCHITECTURE, NodeLabels.DESIGN]:
            properties["modified_at"] = datetime.utcnow().isoformat()

        # Create node query
        query = f"""
        CREATE (n:{label})
        SET n = $properties
        RETURN n.{id_prop} as node_id
        """

        try:
            result = await self.conn.execute_write(query, {"properties": properties})
            if result:
                logger.info(f"Created {label} node: {node_id}")
                return result[0]["node_id"]
            else:
                raise RuntimeError(f"Failed to create {label} node")

        except Exception as e:
            logger.error(f"Failed to create {label} node: {e}")
            raise

    async def get_node(self, label: str, node_id: str, id_property: str = "id") -> Optional[Dict[str, Any]]:
        """
        Retrieve a node by its ID.

        Args:
            label: Node label
            node_id: Node identifier value
            id_property: Property name that holds the ID (default: "id")

        Returns:
            Dictionary of node properties, or None if not found
        """
        # Validate label (prevents Cypher injection)
        validate_node_label(label)

        query = f"""
        MATCH (n:{label} {{{id_property}: $node_id}})
        RETURN n
        """

        try:
            result = await self.conn.execute_read(query, {"node_id": node_id})
            if result and "n" in result[0]:
                logger.debug(f"Retrieved {label} node: {node_id}")
                return dict(result[0]["n"])
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve {label} node {node_id}: {e}")
            raise

    async def update_node(self, label: str, node_id: str, properties: Dict[str, Any],
                         id_property: str = "id") -> bool:
        """
        Update properties of an existing node.

        Args:
            label: Node label
            node_id: Node identifier value
            properties: Dictionary of properties to update
            id_property: Property name that holds the ID (default: "id")

        Returns:
            True if updated successfully, False if node not found
        """
        # Validate label (prevents Cypher injection)
        validate_node_label(label)

        # Update modified_at timestamp
        if label in [NodeLabels.ARCHITECTURE, NodeLabels.DESIGN]:
            properties["modified_at"] = datetime.utcnow().isoformat()

        query = f"""
        MATCH (n:{label} {{{id_property}: $node_id}})
        SET n += $properties
        RETURN n.{id_property} as node_id
        """

        try:
            result = await self.conn.execute_write(query, {
                "node_id": node_id,
                "properties": properties
            })

            if result:
                logger.info(f"Updated {label} node: {node_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to update {label} node {node_id}: {e}")
            raise

    async def delete_node(self, label: str, node_id: str, id_property: str = "id",
                         detach: bool = True) -> bool:
        """
        Delete a node.

        Args:
            label: Node label
            node_id: Node identifier value
            id_property: Property name that holds the ID (default: "id")
            detach: If True, also delete all relationships (default: True)

        Returns:
            True if deleted successfully, False if node not found

        Note:
            In production, consider marking nodes as deprecated instead of deleting
            to maintain immutable audit trail.
        """
        # Validate label (prevents Cypher injection)
        validate_node_label(label)

        detach_clause = "DETACH" if detach else ""

        query = f"""
        MATCH (n:{label} {{{id_property}: $node_id}})
        {detach_clause} DELETE n
        RETURN count(n) as deleted_count
        """

        try:
            result = await self.conn.execute_write(query, {"node_id": node_id})

            if result and result[0]["deleted_count"] > 0:
                logger.warning(f"Deleted {label} node: {node_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete {label} node {node_id}: {e}")
            raise

    async def create_relationship(self, from_label: str, from_id: str, rel_type: str,
                                 to_label: str, to_id: str,
                                 properties: Optional[Dict[str, Any]] = None,
                                 from_id_prop: str = "id", to_id_prop: str = "id") -> bool:
        """
        Create a relationship between two nodes.

        Args:
            from_label: Source node label
            from_id: Source node ID
            rel_type: Relationship type (e.g., "IMPLEMENTS", "DEFINES")
            to_label: Target node label
            to_id: Target node ID
            properties: Optional relationship properties
            from_id_prop: Source node ID property name (default: "id")
            to_id_prop: Target node ID property name (default: "id")

        Returns:
            True if relationship created successfully

        Raises:
            ValueError: If either node doesn't exist
        """
        # Validate labels and relationship type (raises ValueError if invalid)
        validate_node_label(from_label)
        validate_node_label(to_label)
        validate_relationship_type(rel_type)

        properties = properties or {}

        # Sanitize properties
        properties = sanitize_cypher_params(properties)

        # Add timestamp to relationship
        properties["created_at"] = datetime.utcnow().isoformat()

        query = f"""
        MATCH (from:{from_label} {{{from_id_prop}: $from_id}})
        MATCH (to:{to_label} {{{to_id_prop}: $to_id}})
        CREATE (from)-[r:{rel_type}]->(to)
        SET r = $properties
        RETURN id(r) as rel_id
        """

        try:
            result = await self.conn.execute_write(query, {
                "from_id": from_id,
                "to_id": to_id,
                "properties": properties
            })

            if result:
                logger.info(f"Created {rel_type} relationship: {from_id} -> {to_id}")
                return True
            else:
                raise ValueError(f"Failed to create relationship: nodes may not exist")

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            raise

    async def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Execute a custom Cypher query.

        Args:
            cypher: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        parameters = parameters or {}

        try:
            # Determine if it's a read or write query
            is_write = any(keyword in cypher.upper() for keyword in
                          ["CREATE", "MERGE", "SET", "DELETE", "REMOVE"])

            if is_write:
                result = await self.conn.execute_write(cypher, parameters)
            else:
                result = await self.conn.execute_read(cypher, parameters)

            logger.debug(f"Query executed, returned {len(result)} records")
            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def merge_node(self, label: str, match_properties: Dict[str, Any],
                        set_properties: Optional[Dict[str, Any]] = None) -> str:
        """
        Create node if it doesn't exist, or update if it does (MERGE operation).

        Args:
            label: Node label
            match_properties: Properties to match on (typically the unique identifier)
            set_properties: Properties to set on creation or update

        Returns:
            Node ID
        """
        set_properties = set_properties or {}

        # Determine ID property
        id_props = {
            NodeLabels.ARCHITECTURE: "id",
            NodeLabels.DESIGN: "id",
            NodeLabels.REQUIREMENT: "rid",
            NodeLabels.CODE_ARTIFACT: "path",
            NodeLabels.DECISION: "id",
            NodeLabels.AGENT_REQUEST: "id"
        }

        id_prop = id_props.get(label, "id")

        # Build match clause
        match_parts = [f"{k}: ${k}" for k in match_properties.keys()]
        match_clause = ", ".join(match_parts)

        # Combine parameters
        all_params = {**match_properties, **set_properties}
        set_properties["modified_at"] = datetime.utcnow().isoformat()

        query = f"""
        MERGE (n:{label} {{{match_clause}}})
        ON CREATE SET n += $set_properties, n.created_at = datetime()
        ON MATCH SET n += $set_properties
        RETURN n.{id_prop} as node_id
        """

        try:
            result = await self.conn.execute_write(query, {
                **match_properties,
                "set_properties": set_properties
            })

            if result:
                node_id = result[0]["node_id"]
                logger.info(f"Merged {label} node: {node_id}")
                return node_id
            else:
                raise RuntimeError(f"Failed to merge {label} node")

        except Exception as e:
            logger.error(f"Failed to merge {label} node: {e}")
            raise

    async def count_nodes(self, label: Optional[str] = None) -> int:
        """
        Count nodes with optional label filter.

        Args:
            label: Optional node label to filter by

        Returns:
            Number of nodes
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"

        result = await self.conn.execute_read(query)
        return result[0]["count"] if result else 0

    async def count_relationships(self, rel_type: Optional[str] = None) -> int:
        """
        Count relationships with optional type filter.

        Args:
            rel_type: Optional relationship type to filter by

        Returns:
            Number of relationships
        """
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"

        result = await self.conn.execute_read(query)
        return result[0]["count"] if result else 0

    def compute_content_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content for change detection.

        Args:
            content: Content to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
