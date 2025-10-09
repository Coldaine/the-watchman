"""
Neo4j client with connection pooling and helper functions.

Provides:
- Connection pool management
- Transaction helpers
- Common query patterns
- Error handling
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Session, Transaction, Result
from loguru import logger

from app.utils.config import get_settings


class Neo4jClient:
    """Neo4j database client with connection pooling."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize Neo4j client."""
        settings = get_settings()
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password

        self._driver = None

    def connect(self):
        """Establish connection to Neo4j."""
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self.uri}...")
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=120
            )
            self._driver.verify_connectivity()
            logger.success("Connected to Neo4j successfully")

    def close(self):
        """Close Neo4j connection."""
        if self._driver:
            logger.info("Closing Neo4j connection...")
            self._driver.close()
            self._driver = None

    @property
    def driver(self):
        """Get driver, connecting if necessary."""
        if self._driver is None:
            self.connect()
        return self._driver

    @contextmanager
    def session(self) -> Session:
        """Context manager for Neo4j session."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def execute_write(self, query: str, parameters: Dict[str, Any] = None) -> Result:
        """Execute write query with automatic transaction management."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            return result

    def execute_read(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute read query and return results as list of dicts."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a node with given label and properties."""
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        with self.session() as session:
            result = session.run(query, {"props": properties})
            record = result.single()
            return dict(record["n"]) if record else None

    def merge_node(self, label: str, merge_key: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Merge node (create or update) based on merge key."""
        # Extract merge property
        merge_value = properties.get(merge_key)
        if not merge_value:
            raise ValueError(f"Merge key '{merge_key}' not found in properties")

        query = f"""
        MERGE (n:{label} {{{merge_key}: $merge_value}})
        ON CREATE SET n = $props
        ON MATCH SET n += $props
        RETURN n
        """
        with self.session() as session:
            result = session.run(query, {"merge_value": merge_value, "props": properties})
            record = result.single()
            return dict(record["n"]) if record else None

    def find_node(self, label: str, property_name: str, property_value: Any) -> Optional[Dict[str, Any]]:
        """Find a single node by property."""
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
        RETURN n
        LIMIT 1
        """
        with self.session() as session:
            result = session.run(query, {"value": property_value})
            record = result.single()
            return dict(record["n"]) if record else None

    def find_nodes(self, label: str, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Find nodes matching filters."""
        where_clause = ""
        if filters:
            conditions = [f"n.{k} = ${k}" for k in filters.keys()]
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
        MATCH (n:{label})
        {where_clause}
        RETURN n
        LIMIT $limit
        """
        with self.session() as session:
            params = (filters or {}).copy()
            params["limit"] = limit
            result = session.run(query, params)
            return [dict(record["n"]) for record in result]

    def create_relationship(
        self,
        from_label: str,
        from_key: str,
        from_value: Any,
        rel_type: str,
        to_label: str,
        to_key: str,
        to_value: Any,
        rel_props: Dict[str, Any] = None
    ) -> bool:
        """Create relationship between two nodes."""
        query = f"""
        MATCH (a:{from_label} {{{from_key}: $from_value}})
        MATCH (b:{to_label} {{{to_key}: $to_value}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r = $rel_props
        RETURN r
        """
        with self.session() as session:
            result = session.run(query, {
                "from_value": from_value,
                "to_value": to_value,
                "rel_props": rel_props or {}
            })
            return result.single() is not None

    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        query = """
        CALL db.index.vector.queryNodes($index_name, $limit, $query_vector)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        """
        with self.session() as session:
            result = session.run(query, {
                "index_name": index_name,
                "limit": limit,
                "query_vector": query_vector
            })
            return [
                {
                    "node": dict(record["node"]),
                    "score": record["score"]
                }
                for record in result
            ]

    def batch_create_nodes(self, label: str, nodes: List[Dict[str, Any]]) -> int:
        """Batch create nodes using UNWIND."""
        query = f"""
        UNWIND $nodes AS node
        CREATE (n:{label})
        SET n = node
        RETURN count(n) AS created
        """
        with self.session() as session:
            result = session.run(query, {"nodes": nodes})
            record = result.single()
            return record["created"] if record else 0

    def batch_merge_nodes(
        self,
        label: str,
        merge_key: str,
        nodes: List[Dict[str, Any]]
    ) -> int:
        """Batch merge nodes using UNWIND."""
        query = f"""
        UNWIND $nodes AS node
        MERGE (n:{label} {{{merge_key}: node.{merge_key}}})
        ON CREATE SET n = node
        ON MATCH SET n += node
        RETURN count(n) AS processed
        """
        with self.session() as session:
            result = session.run(query, {"nodes": nodes})
            record = result.single()
            return record["processed"] if record else 0


# Global client instance
_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get global Neo4j client instance."""
    global _client
    if _client is None:
        _client = Neo4jClient()
        _client.connect()
    return _client


def close_neo4j_client():
    """Close global Neo4j client."""
    global _client
    if _client:
        _client.close()
        _client = None
