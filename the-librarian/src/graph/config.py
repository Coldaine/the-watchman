"""
Graph database configuration management.

Loads configuration from environment variables using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class GraphConfig(BaseSettings):
    """Configuration for Neo4j graph database connection."""

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Neo4j Connection
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j bolt connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        ...,
        description="Neo4j password (required from environment)"
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )

    # Connection Pool Settings
    max_connection_lifetime: int = Field(
        default=3600,
        description="Maximum connection lifetime in seconds (default: 1 hour)"
    )
    max_connection_pool_size: int = Field(
        default=50,
        description="Maximum connection pool size (default: 50 connections)"
    )
    connection_acquisition_timeout: int = Field(
        default=60,
        description="Connection acquisition timeout in seconds (default: 60s)"
    )

    # Vector Configuration
    vector_dimensions: int = Field(
        default=768,
        description="Embedding vector dimensions (nomic-embed-text: 768)"
    )
    vector_similarity_function: str = Field(
        default="cosine",
        description="Vector similarity function (cosine, euclidean, dot)"
    )

    # Query Settings
    query_timeout: int = Field(
        default=30000,
        description="Query execution timeout in milliseconds (default: 30s)"
    )


# Global config instance
_config: Optional[GraphConfig] = None


def get_config() -> GraphConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = GraphConfig()
    return _config


def reload_config() -> GraphConfig:
    """Reload configuration from environment."""
    global _config
    _config = GraphConfig()
    return _config
