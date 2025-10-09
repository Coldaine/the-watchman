"""
Configuration management for The Watchman.

Uses pydantic-settings to load configuration from environment variables
and .env files.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "watchman123"

    # API Configuration
    api_port: int = 8000
    log_level: str = "INFO"
    api_title: str = "The Watchman API"
    api_version: str = "1.0.0"

    # Ollama Configuration
    ollama_url: str = "http://192.168.1.69:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"

    # OpenRouter Configuration (fallback)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Screenshot Configuration
    screenshot_interval: int = 300  # seconds
    screenshot_dir: Path = Path("/var/lib/watchman/shots")
    ocr_dir: Path = Path("/var/lib/watchman/ocr")
    chunk_dir: Path = Path("/var/lib/watchman/chunks")

    # Retention Configuration
    image_retention_days: int = 14
    ocr_retention_days: int = 90

    # Privacy Configuration
    redact_patterns: str = r".*@.*\.com,sk-.*,ghp_.*,AWS.*"
    exclude_apps: str = "keepassxc,gnome-keyring"

    # System Paths
    project_roots: str = "/home/user/projects,/home/user/code,/home/user/dev"
    config_roots: str = "/etc,~/.config,~/.ssh"

    # MCP Configuration
    mcp_registry_path: Path = Path("/opt/mcp")
    mcp_registry_file: Path = Path("config/mcp_registry.yaml")

    # Worker Configuration
    ocr_queue_size: int = 100
    ocr_worker_threads: int = 2
    embedding_batch_size: int = 10

    # Redis Configuration (optional, for queue management)
    redis_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_project_roots(self) -> list[Path]:
        """Parse project roots into list of Paths."""
        return [
            Path(p.strip()).expanduser()
            for p in self.project_roots.split(',')
        ]

    def get_config_roots(self) -> list[Path]:
        """Parse config roots into list of Paths."""
        return [
            Path(p.strip()).expanduser()
            for p in self.config_roots.split(',')
        ]

    def get_redact_patterns(self) -> list[str]:
        """Parse redact patterns into list."""
        return [p.strip() for p in self.redact_patterns.split(',')]

    def get_exclude_apps(self) -> list[str]:
        """Parse excluded apps into list."""
        return [a.strip() for a in self.exclude_apps.split(',')]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
