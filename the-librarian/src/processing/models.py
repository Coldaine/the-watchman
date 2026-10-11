"""
Data models for the document processing pipeline.

These Pydantic models define the structure of documents, chunks, and processed data
as they flow through the parsing, chunking, and embedding stages.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import hashlib


class Document(BaseModel):
    """Base document model."""

    path: str = Field(..., description="Absolute file path")
    doc_type: str = Field(..., description="Document type: architecture, design, tasks, research, code")
    content: str = Field(..., description="Raw document content")
    frontmatter: Dict[str, Any] = Field(default_factory=dict, description="YAML frontmatter metadata")
    hash: str = Field(..., description="SHA256 content hash")

    @classmethod
    def from_file(cls, path: str, content: str, doc_type: str, frontmatter: Dict[str, Any]):
        """Create Document from file content."""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return cls(
            path=path,
            doc_type=doc_type,
            content=content,
            frontmatter=frontmatter,
            hash=content_hash
        )


class ParsedDocument(Document):
    """Parsed document with extracted metadata and structure."""

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted metadata")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Document sections")
    modified_at: Optional[datetime] = Field(None, description="File modification time")
    size_bytes: int = Field(0, description="Content size in bytes")

    @field_validator('frontmatter')
    @classmethod
    def validate_frontmatter(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        """Validate required frontmatter fields based on doc_type."""
        doc_type = info.data.get('doc_type')

        # Required fields for all documents
        required_fields = ['doc', 'subsystem', 'id', 'version', 'status', 'owners']

        # Additional required fields for architecture documents
        if doc_type == 'architecture':
            required_fields.extend(['compliance_level', 'drift_tolerance'])

        missing = [field for field in required_fields if field not in v]
        if missing:
            raise ValueError(f"Missing required frontmatter fields: {missing}")

        return v


class Chunk(BaseModel):
    """Text chunk with metadata."""

    content: str = Field(..., description="Chunk content")
    start_index: int = Field(0, description="Start position in original document")
    end_index: int = Field(0, description="End position in original document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    parent_id: Optional[str] = Field(None, description="Parent chunk ID for hierarchical relationships")
    section_title: Optional[str] = Field(None, description="Section title if chunk is from a section")
    section_level: Optional[int] = Field(None, description="Header level (1-6)")

    def __hash__(self):
        """Generate hash for chunk content."""
        return int(hashlib.md5(self.content.encode('utf-8')).hexdigest(), 16)


class ProcessedChunk(Chunk):
    """Chunk with embedding vector."""

    embedding: List[float] = Field(..., description="768-dimensional embedding vector")

    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v: List[float]) -> List[float]:
        """Validate embedding has correct dimensions."""
        if len(v) != 768:
            raise ValueError(f"Embedding must be 768 dimensions, got {len(v)}")
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    path: str
    status: str = Field(..., description="success, error, or skipped")
    doc_id: Optional[str] = None
    chunks_created: int = 0
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class IngestionReport(BaseModel):
    """Report of batch ingestion operation."""

    total_files: int
    updated_files: int
    results: List[IngestionResult]
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def success_count(self) -> int:
        """Count of successful ingestions."""
        return sum(1 for r in self.results if r.status == 'success')

    @property
    def error_count(self) -> int:
        """Count of failed ingestions."""
        return sum(1 for r in self.results if r.status == 'error')

    @property
    def skipped_count(self) -> int:
        """Count of skipped files."""
        return sum(1 for r in self.results if r.status == 'skipped')


class UpdateInfo(BaseModel):
    """Information about a file that needs updating."""

    path: str
    action: str = Field(..., description="create, update, or refresh")
    reason: str = Field(..., description="Why this file needs updating")
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
