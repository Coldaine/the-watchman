"""
Configuration management for The Watchman.

Supports both TOML configuration files and environment variables.
Priority: config.toml > environment variables > .env file > defaults
"""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Try to import tomllib (Python 3.11+) or tomli (backport)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def load_toml_config(toml_path: Path = Path("config.toml")) -> dict[str, Any]:
    """
    Load configuration from TOML file.

    Args:
        toml_path: Path to TOML config file

    Returns:
        Flattened configuration dict
    """
    if not tomllib:
        return {}

    if not toml_path.exists():
        return {}

    try:
        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)

        # Flatten nested TOML structure for pydantic
        flat_config = {}
        for section, values in toml_data.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    # Convert list to comma-separated string for compatibility
                    if isinstance(value, list):
                        if all(isinstance(x, str) for x in value):
                            value = ",".join(value)
                    flat_config[f"{section}_{key}"] = value
            else:
                flat_config[section] = values

        return flat_config
    except Exception as e:
        print(f"Warning: Failed to load config.toml: {e}")
        return {}


class Settings(BaseSettings):
    """Application settings loaded from TOML, environment, or .env files."""

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "watchman123"

    # API Configuration
    api_port: int = 8000
    api_log_level: str = "INFO"
    api_title: str = "The Watchman API"
    api_version: str = "1.0.0"

    # Ollama Configuration
    ollama_url: str = "http://192.168.1.69:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"

    # OpenRouter Configuration (fallback)
    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Screenshot Configuration
    screenshot_interval: int = 300  # seconds
    screenshot_dir: Path = Path("/var/lib/watchman/shots")

    # Screenshot Diffing
    screenshot_enable_diffing: bool = True
    screenshot_diff_threshold: float = 0.10
    screenshot_diff_algorithm: str = "phash"  # phash, dhash, pixel

    # Smart Capture
    screenshot_enable_smart_capture: bool = True
    screenshot_capture_on_app_switch: bool = True
    screenshot_capture_on_idle_return: bool = True
    screenshot_idle_threshold: int = 300

    # Similarity Clustering
    screenshot_enable_similarity_clustering: bool = True
    screenshot_similarity_threshold: float = 0.95
    screenshot_cluster_window: int = 3600

    # OCR Configuration
    ocr_dir: Path = Path("/var/lib/watchman/ocr")
    ocr_chunk_dir: Path = Path("/var/lib/watchman/chunks")
    ocr_queue_size: int = 100
    ocr_worker_threads: int = 2

    # Lazy OCR Processing
    ocr_enable_lazy_processing: bool = False
    ocr_auto_process_recent: bool = True
    ocr_recent_threshold: int = 3600

    # Embedding Configuration
    embedding_batch_size: int = 10

    # Retention Configuration
    retention_image_retention_days: int = 14
    retention_ocr_retention_days: int = 90
    retention_auto_delete_duplicates: bool = False

    # Privacy Configuration
    privacy_redact_patterns: str = r".*@.*\.com,sk-.*,ghp_.*,AWS.*,\d{3}-\d{2}-\d{4}"
    privacy_exclude_apps: str = "keepassxc,gnome-keyring,1password"
    privacy_exclude_window_patterns: str = ".*password.*,.*private.*"

    # System Paths
    system_project_roots: str = "/home/user/projects,/home/user/code,/home/user/dev"
    system_config_roots: str = "/etc,~/.config,~/.ssh"

    # MCP Configuration
    mcp_registry_path: Path = Path("/opt/mcp")
    mcp_registry_file: Path = Path("config/mcp_registry.yaml")

    # Redis Configuration (optional, for queue management)
    redis_url: str | None = None

    # Review Features
    review_enable_lazy_review: bool = True
    review_summarization_model: str = "llama3.2"
    review_auto_generate_summaries: bool = False
    review_summary_interval: int = 3600

    # Feature Flags
    features_visual_timeline: bool = True
    features_system_graph: bool = True
    features_event_tracking: bool = True
    features_gui_collector: bool = False
    features_file_ingest: bool = True
    features_mcp_registry: bool = True
    features_agent_interface: bool = True

    # Performance Tuning
    performance_screenshot_compression_quality: int = 85
    performance_screenshot_max_dimension: int = 1920
    performance_enable_incremental_hashing: bool = True
    performance_hash_grid_size: int = 16

    # Legacy environment variable support (backward compatibility)
    log_level: str | None = None
    chunk_dir: Path | None = None
    image_retention_days: int | None = None
    ocr_retention_days: int | None = None
    redact_patterns: str | None = None
    exclude_apps: str | None = None
    project_roots: str | None = None
    config_roots: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @model_validator(mode="after")
    def handle_legacy_vars(self):
        """Map legacy environment variables to new structure."""
        # Map legacy log_level to api_log_level
        if self.log_level:
            self.api_log_level = self.log_level

        # Map legacy chunk_dir to ocr_chunk_dir
        if self.chunk_dir:
            self.ocr_chunk_dir = self.chunk_dir

        # Map legacy retention settings
        if self.image_retention_days is not None:
            self.retention_image_retention_days = self.image_retention_days
        if self.ocr_retention_days is not None:
            self.retention_ocr_retention_days = self.ocr_retention_days

        # Map legacy privacy settings
        if self.redact_patterns:
            self.privacy_redact_patterns = self.redact_patterns
        if self.exclude_apps:
            self.privacy_exclude_apps = self.exclude_apps

        # Map legacy system paths
        if self.project_roots:
            self.system_project_roots = self.project_roots
        if self.config_roots:
            self.system_config_roots = self.config_roots

        return self

    def get_project_roots(self) -> list[Path]:
        """Parse project roots into list of Paths."""
        return [Path(p.strip()).expanduser() for p in self.system_project_roots.split(",")]

    def get_config_roots(self) -> list[Path]:
        """Parse config roots into list of Paths."""
        return [Path(p.strip()).expanduser() for p in self.system_config_roots.split(",")]

    def get_redact_patterns(self) -> list[str]:
        """Parse redact patterns into list."""
        return [p.strip() for p in self.privacy_redact_patterns.split(",")]

    def get_exclude_apps(self) -> list[str]:
        """Parse excluded apps into list."""
        return [a.strip() for a in self.privacy_exclude_apps.split(",")]

    def get_exclude_window_patterns(self) -> list[str]:
        """Parse excluded window patterns into list."""
        return [p.strip() for p in self.privacy_exclude_window_patterns.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Priority order:
    1. config.toml (if exists)
    2. Environment variables
    3. .env file
    4. Default values
    """
    # Load TOML config first
    toml_config = load_toml_config()

    # Create settings with TOML values taking precedence
    if toml_config:
        settings = Settings(**toml_config)
    else:
        settings = Settings()

    return settings
