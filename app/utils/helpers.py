"""
Helper utilities for The Watchman.

Common functions used across domains.
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def generate_uuid() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


def hash_text(text: str) -> str:
    """Generate SHA256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()


def chunk_text(text: str, max_length: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into chunks with optional overlap.

    Args:
        text: Text to chunk
        max_length: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= max_length:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_length
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            # Look for last period, question mark, or exclamation
            last_break = max(
                chunk.rfind('. '),
                chunk.rfind('? '),
                chunk.rfind('! ')
            )
            if last_break > max_length // 2:  # Only break if reasonably far in
                end = start + last_break + 2
                chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap

    return chunks


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized


def get_file_extension(path: Path) -> str:
    """Get file extension without dot."""
    return path.suffix.lstrip('.')


def detect_project_type(project_path: Path) -> Optional[str]:
    """
    Detect project type based on files present.

    Returns:
        Project type string or None if unknown
    """
    files = {f.name for f in project_path.iterdir() if f.is_file()}

    if 'package.json' in files:
        return 'node'
    elif 'Cargo.toml' in files:
        return 'rust'
    elif 'go.mod' in files:
        return 'go'
    elif 'requirements.txt' in files or 'pyproject.toml' in files:
        return 'python'
    elif 'pom.xml' in files or 'build.gradle' in files:
        return 'java'
    elif 'Gemfile' in files:
        return 'ruby'
    elif 'composer.json' in files:
        return 'php'
    elif 'docker-compose.yml' in files or 'docker-compose.yaml' in files:
        return 'docker-compose'

    return None


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime."""
    return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))


def now_iso() -> str:
    """Get current timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def redact_text(text: str, patterns: List[str]) -> str:
    """
    Redact sensitive information from text using regex patterns.

    Args:
        text: Text to redact
        patterns: List of regex patterns to redact

    Returns:
        Redacted text
    """
    redacted = text

    for pattern in patterns:
        try:
            redacted = re.sub(pattern, '[REDACTED]', redacted)
        except re.error as e:
            # Invalid regex pattern, skip it
            continue

    return redacted


def format_bytes(bytes_count: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def safe_path(path: str) -> Path:
    """
    Convert string to Path, handling edge cases.

    Args:
        path: Path string

    Returns:
        Path object
    """
    return Path(path).expanduser().resolve()


def is_hidden(path: Path) -> bool:
    """Check if path is hidden (starts with dot)."""
    return path.name.startswith('.')


def should_exclude_path(path: Path, exclude_patterns: List[str] = None) -> bool:
    """
    Check if path should be excluded based on patterns.

    Args:
        path: Path to check
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if should exclude, False otherwise
    """
    if exclude_patterns is None:
        exclude_patterns = [
            '*.pyc',
            '__pycache__',
            'node_modules',
            '.git',
            '.venv',
            'venv',
            '.DS_Store'
        ]

    path_str = str(path)

    for pattern in exclude_patterns:
        if path.match(pattern) or pattern in path_str:
            return True

    return False


def create_network_endpoint_key(host: str, port: int, protocol: str = "tcp") -> str:
    """Create unique key for network endpoint."""
    return f"{protocol}://{host}:{port}"


def parse_docker_image_tag(image: str) -> Dict[str, str]:
    """
    Parse Docker image string into components.

    Args:
        image: Docker image string (e.g., "nginx:latest", "myregistry.com/app:1.2.3")

    Returns:
        Dict with 'registry', 'repository', 'tag'
    """
    parts = image.split('/')
    registry = None
    repository = image
    tag = 'latest'

    # Has registry
    if len(parts) > 1 and ('.' in parts[0] or ':' in parts[0]):
        registry = parts[0]
        repository = '/'.join(parts[1:])

    # Has tag
    if ':' in repository:
        repository, tag = repository.rsplit(':', 1)

    return {
        'registry': registry,
        'repository': repository,
        'tag': tag
    }
