"""
Neo4j async connection management with health checks and transaction support.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from typing import Optional, Any, Dict, List, Callable
from contextlib import asynccontextmanager
import logging

from .config import get_config

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages async Neo4j driver connection with connection pooling."""

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None,
                 password: Optional[str] = None, database: Optional[str] = None):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI (defaults to config)
            user: Neo4j username (defaults to config)
            password: Neo4j password (defaults to config)
            database: Neo4j database name (defaults to config)
        """
        config = get_config()

        self.uri = uri or config.neo4j_uri
        self.user = user or config.neo4j_user
        self.password = password or config.neo4j_password
        self.database = database or config.neo4j_database

        self.driver: Optional[AsyncDriver] = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self._is_connected:
            logger.warning("Already connected to Neo4j")
            return

        try:
            config = get_config()

            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=config.max_connection_lifetime,
                max_connection_pool_size=config.max_connection_pool_size,
                connection_acquisition_timeout=config.connection_acquisition_timeout
            )

            # Verify connection
            await self.driver.verify_connectivity()
            self._is_connected = True
            logger.info(f"Connected to Neo4j at {self.uri}")

        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close connection to Neo4j database."""
        if self.driver:
            await self.driver.close()
            self._is_connected = False
            logger.info("Closed Neo4j connection")

    async def verify_connectivity(self) -> bool:
        """
        Verify database connectivity.

        Returns:
            True if connected, False otherwise
        """
        if not self.driver:
            return False

        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False

    @asynccontextmanager
    async def session(self, **kwargs) -> AsyncSession:
        """
        Get async session context manager.

        Yields:
            AsyncSession for executing queries
        """
        if not self.driver:
            await self.connect()

        async with self.driver.session(database=self.database, **kwargs) as session:
            yield session

    async def execute_read(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute read query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        parameters = parameters or {}

        async with self.session() as session:
            result = await session.run(query, parameters)
            records = await result.data()
            return records

    async def execute_write(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute write query in a transaction and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        parameters = parameters or {}

        async with self.session() as session:
            result = await session.run(query, parameters)
            records = await result.data()
            return records

    async def execute_write_transaction(self, transaction_function: Callable, *args, **kwargs) -> Any:
        """
        Execute a write transaction using a transaction function.

        Args:
            transaction_function: Async function that takes a transaction object
            *args: Positional arguments for the transaction function
            **kwargs: Keyword arguments for the transaction function

        Returns:
            Result from transaction function
        """
        async with self.session() as session:
            return await session.execute_write(transaction_function, *args, **kwargs)

    async def execute_read_transaction(self, transaction_function: Callable, *args, **kwargs) -> Any:
        """
        Execute a read transaction using a transaction function.

        Args:
            transaction_function: Async function that takes a transaction object
            *args: Positional arguments for the transaction function
            **kwargs: Keyword arguments for the transaction function

        Returns:
            Result from transaction function
        """
        async with self.session() as session:
            return await session.execute_read(transaction_function, *args, **kwargs)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary with health status information
        """
        health = {
            "connected": False,
            "database": self.database,
            "uri": self.uri,
            "node_count": None,
            "relationship_count": None,
            "error": None
        }

        try:
            if not await self.verify_connectivity():
                health["error"] = "Connection verification failed"
                return health

            health["connected"] = True

            # Get database statistics
            stats_query = """
            MATCH (n)
            WITH count(n) as nodeCount
            MATCH ()-[r]->()
            RETURN nodeCount, count(r) as relCount
            """

            results = await self.execute_read(stats_query)
            if results:
                health["node_count"] = results[0].get("nodeCount", 0)
                health["relationship_count"] = results[0].get("relCount", 0)

        except Exception as e:
            health["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return health


# Global connection instance
_connection: Optional[Neo4jConnection] = None


def get_connection() -> Neo4jConnection:
    """Get or create the global connection instance."""
    global _connection
    if _connection is None:
        _connection = Neo4jConnection()
    return _connection


async def close_connection() -> None:
    """Close the global connection instance."""
    global _connection
    if _connection:
        await _connection.close()
        _connection = None
