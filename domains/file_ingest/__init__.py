"""
File Ingestion Domain

Monitors downloads directory for files requiring processing:
- Media files (images/videos) → Deduplicate and route by tags
- Documents (markdown/PDF) → Copy to RAG ingestion directory
- Export archives (zip files) → Extract and categorize by type

Evolved from the standalone file-watchman project into a first-class
Watchman collector domain with Neo4j integration.
"""

__all__ = ["collectors", "processors"]
