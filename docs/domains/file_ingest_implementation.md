# File Ingest Domain - Implementation Plan

**Domain:** `domains/file_ingest/`
**Status:** Not Started
**Priority:** Medium
**Estimated Effort:** 2-3 weeks
**Source:** Evolved from standalone file-watchman project

---

## Overview

The File Ingest domain monitors the downloads directory for files requiring processing, performing deduplication, categorization, and routing while tracking everything in the Neo4j knowledge graph.

### Evolution from file-watchman

This domain integrates functionality from the standalone **file-watchman** project, evolving from cron-based scripts into long-running collectors that integrate with The Watchman's graph database and event system.

**Key Changes:**
- Cron scripts → Long-running collectors
- Standalone SQLite → Neo4j integration
- Isolated processing → Graph-aware with relationships
- File-only tracking → Full provenance with `:IngestedDocument`, `:ProcessedFile` nodes

---

## Architecture Overview

### Components

```
domains/file_ingest/
├── __init__.py
├── collectors/
│   ├── __init__.py
│   ├── dedupe_collector.py      # Media deduplication + tag routing
│   ├── document_collector.py    # RAG system document feeding
│   └── export_collector.py      # Knowledge export extraction
├── processors/
│   ├── __init__.py
│   ├── hasher.py                # Content-based hashing
│   ├── router.py                # Tag/type-based routing
│   └── graph_writer.py          # Neo4j integration
└── models/
    ├── __init__.py
    └── schemas.py               # Pydantic models
```

### Neo4j Schema Extensions

**New Node Types:**
```cypher
(:IngestedDocument {
    file_hash: string,
    original_filename: string,
    original_path: string,
    dest_path: string,
    file_size: integer,
    mime_type: string,
    ingested_at: datetime,
    tags: list<string>
})

(:ProcessedExport {
    zip_hash: string,
    original_filename: string,
    processed_at: datetime,
    file_count: integer,
    categories: list<string>
})

(:MediaFile {
    file_hash: string,
    filename: string,
    original_path: string,
    dest_path: string,
    duplicate: boolean,
    tag: string,
    processed_at: datetime
})
```

**New Relationships:**
```cypher
(:IngestedDocument)-[:SOURCED_FROM]->(:File)
(:IngestedDocument)-[:INGESTED_TO]->(:Directory)
(:IngestedDocument)-[:HAS_TAG]->(:Tag)
(:ProcessedExport)-[:EXTRACTED]->(:IngestedDocument)
(:ProcessedExport)-[:EXTRACTED]->(:MediaFile)
(:MediaFile)-[:DUPLICATE_OF]->(:MediaFile)
(:MediaFile)-[:TAGGED_AS]->(:Tag)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Set up shared processors and graph integration

#### Tasks

1. **Implement hasher.py**
   ```python
   # domains/file_ingest/processors/hasher.py
   from pathlib import Path
   import hashlib

   def calculate_hash(file_path: Path) -> str:
       """Calculate SHA-256 hash of file content."""
       sha256 = hashlib.sha256()
       with open(file_path, 'rb') as f:
           for chunk in iter(lambda: f.read(8192), b''):
               sha256.update(chunk)
       return sha256.hexdigest()
   ```

2. **Implement graph_writer.py**
   ```python
   # domains/file_ingest/processors/graph_writer.py
   from neo4j import Driver
   from typing import Optional

   class GraphWriter:
       def __init__(self, driver: Driver):
           self.driver = driver

       def create_ingested_document(
           self,
           file_hash: str,
           original_path: str,
           dest_path: str,
           metadata: dict
       ) -> str:
           """Create :IngestedDocument node and relationships."""
           # Implementation with Neo4j MERGE

       def create_processed_export(
           self,
           zip_hash: str,
           metadata: dict
       ) -> str:
           """Create :ProcessedExport node."""
           # Implementation
   ```

3. **Implement router.py**
   ```python
   # domains/file_ingest/processors/router.py
   from pathlib import Path
   from typing import Optional

   class FileRouter:
       def __init__(self, config: dict):
           self.tags = config.get('tags', {})
           self.extensions = config.get('extensions', {})

       def match_tag(self, filename: str) -> Optional[str]:
           """Match filename against tag rules (priority order)."""
           # Port from dedupe_downloads.py

       def categorize_file(self, file_path: Path) -> str:
           """Categorize file by extension."""
           # Port from process_exports.py
   ```

4. **Create Pydantic models**
   ```python
   # domains/file_ingest/models/schemas.py
   from pydantic import BaseModel
   from datetime import datetime
   from pathlib import Path

   class IngestedDocument(BaseModel):
       file_hash: str
       original_path: Path
       dest_path: Path
       tags: list[str]
       ingested_at: datetime
   ```

**Acceptance Criteria:**
- [ ] Hasher produces consistent SHA-256 hashes
- [ ] GraphWriter creates nodes in Neo4j correctly
- [ ] Router matches tags with correct priority
- [ ] Pydantic models validate input data
- [ ] Unit tests for all processors pass

---

### Phase 2: Media Deduplication Collector (Week 1-2)

**Goal:** Port dedupe_downloads.py functionality to a long-running collector

#### Source Material
- **Original:** `file-watchman/dedupe_downloads.py`
- **Tests:** `file-watchman/tests/test_dedupe.py`
- **Config:** `~/.config/photo_dedupe/config.toml`

#### Tasks

1. **Create dedupe_collector.py**
   ```python
   # domains/file_ingest/collectors/dedupe_collector.py
   from watchdog.observers import Observer
   from watchdog.events import FileSystemEventHandler
   from ..processors.hasher import calculate_hash
   from ..processors.router import FileRouter
   from ..processors.graph_writer import GraphWriter

   class DedupeCollector(FileSystemEventHandler):
       """Watch downloads directory for media files."""

       def __init__(self, config: dict, graph: GraphWriter):
           self.config = config
           self.graph = graph
           self.router = FileRouter(config)

       def on_created(self, event):
           """Handle new file created in downloads."""
           if event.is_directory:
               return

           file_path = Path(event.src_path)
           if not self.is_media_file(file_path):
               return

           # Process: hash, check duplicate, route, create graph node
   ```

2. **Port tag-based routing logic**
   - Order-dependent tag matching (first match wins)
   - Case-insensitive substring matching
   - Priority: favorite > scrolller > default

3. **Integrate with Neo4j**
   - Create `:MediaFile` nodes for processed files
   - Link duplicates with `:DUPLICATE_OF` relationships
   - Track tags with `:TAGGED_AS` relationships

4. **Migrate configuration**
   - Move from `~/.config/photo_dedupe/config.toml` to The Watchman's config system
   - Support environment variable substitution
   - Add to main `docker-compose.yml` as environment config

**Acceptance Criteria:**
- [ ] Collector runs as long-running service
- [ ] Detects new media files within 5 seconds
- [ ] Correctly identifies duplicates by content hash
- [ ] Routes files according to tag priority
- [ ] Creates Neo4j nodes with all metadata
- [ ] Tests verify tag priority and duplicate detection
- [ ] Dry-run mode works for testing

**Migration Path:**
```bash
# Existing cron job (disable after migration):
# 0 * * * * /home/coldaine/scripts/dedupe_downloads.py --quiet

# New service in docker-compose.yml:
# dedupe-collector:
#   build: .
#   command: python -m domains.file_ingest.collectors.dedupe_collector
#   volumes:
#     - ~/Downloads:/mnt/downloads
#     - ~/Pictures:/mnt/pictures
```

---

### Phase 3: Document Ingestion Collector (Week 2)

**Goal:** Port ingest_documents.py functionality (planned script)

#### Source Material
- **Spec:** `file-watchman/docs/features/document-ingestion.md`
- **Cron schedule:** Every 15 minutes (offset +2 from exports)

#### Tasks

1. **Create document_collector.py**
   ```python
   # domains/file_ingest/collectors/document_collector.py
   class DocumentCollector(FileSystemEventHandler):
       """Watch downloads directory for documents (.md, .pdf)."""

       SUPPORTED_EXTENSIONS = ['.md', '.pdf']
       AGE_THRESHOLD_DAYS = 14

       def on_created(self, event):
           """Handle new document in downloads."""
           file_path = Path(event.src_path)

           if not self.is_document(file_path):
               return

           # Process: hash, check if ingested, copy to RAG dir, create node
   ```

2. **Implement stale file management**
   - Track file age from mtime
   - Move files older than 14 days to `~/Downloads/Stale/`
   - Log stale movements for user review

3. **Integrate with RAG system**
   - Copy files to `$INGESTION_DIR`
   - Handle filename collisions with `_counter` suffix
   - Preserve original files in Downloads until stale

4. **Neo4j integration**
   - Create `:IngestedDocument` nodes
   - Link to source `:File` nodes with `:SOURCED_FROM`
   - Link to destination `:Directory` with `:INGESTED_TO`

**Acceptance Criteria:**
- [ ] Collector detects new documents within 5 seconds
- [ ] Skips already-ingested files (by content hash)
- [ ] Copies files to $INGESTION_DIR correctly
- [ ] Moves files to Stale/ after 14 days
- [ ] Creates complete Neo4j graph representation
- [ ] No deletion of files (move-only workflow)

---

### Phase 4: Export Processing Collector (Week 2-3)

**Goal:** Port process_exports.py functionality (planned script)

#### Source Material
- **Spec:** `file-watchman/docs/features/knowledge-export-processor.md`
- **Pattern:** `*exported*.zip` files in Downloads

#### Tasks

1. **Create export_collector.py**
   ```python
   # domains/file_ingest/collectors/export_collector.py
   import zipfile
   import tempfile

   class ExportCollector(FileSystemEventHandler):
       """Watch downloads directory for export archives."""

       CATEGORIES = {
           'documents': ['.md', '.pdf', '.txt'],
           'code': ['.py', '.js', '.ts', '.sh'],
           'assets': ['.png', '.jpg', '.webp', '.gif'],
           'data': ['.csv', '.json', '.toml', '.yaml']
       }

       def on_created(self, event):
           """Handle new export zip file."""
           if not self.is_export_zip(event.src_path):
               return

           # Process: hash, check if processed, extract, categorize, route
   ```

2. **Implement multi-destination routing**
   - Documents → `$INGESTION_DIR` (RAG system)
   - Code → `~/Code-Exports/{export_name}/`
   - Assets → `~/Export-Assets/{export_name}/`
   - Data → `~/Export-Data/{export_name}/`

3. **Extraction and staging**
   - Extract to temporary directory (`/tmp/export_processing_*`)
   - Move original zip to `~/Downloads/Processed-Exports/`
   - Clean up temp directory after processing

4. **Neo4j integration**
   - Create `:ProcessedExport` node for each zip
   - Create `:IngestedDocument` or `:MediaFile` nodes for extracted files
   - Link with `:EXTRACTED` relationships
   - Track categories as list property

**Acceptance Criteria:**
- [ ] Collector detects new export zips within 5 seconds
- [ ] Correctly extracts all files from zip
- [ ] Routes files to correct destinations by category
- [ ] Creates subdirectories per export name
- [ ] Skips already-processed exports (by zip hash)
- [ ] Creates complete graph of extraction provenance
- [ ] Handles corrupted zips gracefully

---

### Phase 5: Configuration & Integration (Week 3)

**Goal:** Integrate collectors into The Watchman's orchestration system

#### Tasks

1. **Update docker-compose.yml**
   ```yaml
   file-ingest-dedupe:
     build: .
     command: python -m domains.file_ingest.collectors.dedupe_collector
     environment:
       - NEO4J_URI=bolt://neo4j:7687
       - NEO4J_USER=neo4j
       - NEO4J_PASSWORD=watchman123
       - WATCHED_DIR=/mnt/downloads
     volumes:
       - ~/Downloads:/mnt/downloads:ro
       - ~/Pictures:/mnt/pictures

   file-ingest-documents:
     build: .
     command: python -m domains.file_ingest.collectors.document_collector
     environment:
       - NEO4J_URI=bolt://neo4j:7687
       - INGESTION_DIR=/mnt/ingestion
     volumes:
       - ~/Downloads:/mnt/downloads
       - ${INGESTION_DIR}:/mnt/ingestion

   file-ingest-exports:
     build: .
     command: python -m domains.file_ingest.collectors.export_collector
     environment:
       - NEO4J_URI=bolt://neo4j:7687
       - INGESTION_DIR=/mnt/ingestion
     volumes:
       - ~/Downloads:/mnt/downloads
       - ~/Code-Exports:/mnt/code-exports
       - ~/Export-Assets:/mnt/export-assets
       - ~/Export-Data:/mnt/export-data
   ```

2. **Create unified configuration**
   ```toml
   # config/file_ingest.toml
   [dedupe]
   enabled = true
   watched_dir = "~/Downloads"
   extensions = [".jpg", ".jpeg", ".webp", ".gif", ".png", ".mp4", ".webm"]

   [[dedupe.tags]]
   name = "favorite"
   substrings = ["favorite"]
   dest = "~/Pictures/ScrolllerMedia/favorite/"
   priority = 1

   [[dedupe.tags]]
   name = "scrolller"
   substrings = ["scrolller"]
   dest = "~/Pictures/ScrolllerMedia/"
   priority = 2

   [documents]
   enabled = true
   watched_dir = "~/Downloads"
   extensions = [".md", ".pdf"]
   ingestion_dir = "${INGESTION_DIR}"
   stale_days = 14

   [exports]
   enabled = true
   watched_dir = "~/Downloads"
   pattern = "*exported*.zip"
   staging_dir = "~/Downloads/Processed-Exports"

   [exports.destinations]
   documents = "${INGESTION_DIR}"
   code = "~/Code-Exports"
   assets = "~/Export-Assets"
   data = "~/Export-Data"
   ```

3. **Add API endpoints**
   ```python
   # app/api/routes/file_ingest.py
   @router.get("/file-ingest/stats")
   async def get_ingestion_stats():
       """Get statistics for file ingestion collectors."""
       return {
           "dedupe": {"processed": 1234, "duplicates": 456},
           "documents": {"ingested": 89, "stale": 23},
           "exports": {"processed": 12, "extracted": 456}
       }

   @router.post("/file-ingest/scan")
   async def trigger_manual_scan():
       """Trigger manual scan of downloads directory."""
       # Force immediate scan across all collectors
   ```

4. **Update README.md and documentation**
   - Add file_ingest domain to architecture overview
   - Document configuration options
   - Migration guide from file-watchman cron jobs
   - Query examples for ingested files

**Acceptance Criteria:**
- [ ] All collectors start via docker-compose
- [ ] Configuration loads from unified TOML file
- [ ] API endpoints return correct statistics
- [ ] Health checks pass for all collectors
- [ ] Documentation updated with integration details
- [ ] Migration path from cron jobs documented

---

## Neo4j Query Examples

### Find all ingested documents from today
```cypher
MATCH (d:IngestedDocument)
WHERE date(d.ingested_at) = date()
RETURN d.original_filename, d.dest_path, d.tags
ORDER BY d.ingested_at DESC
```

### Find duplicates detected by dedupe collector
```cypher
MATCH (m1:MediaFile)-[:DUPLICATE_OF]->(m2:MediaFile)
RETURN m1.filename, m2.filename, m1.file_hash
```

### Find all files extracted from an export
```cypher
MATCH (e:ProcessedExport {original_filename: "exported-assets (4).zip"})
      -[:EXTRACTED]->(f)
RETURN e.processed_at, labels(f), f.filename, f.dest_path
```

### Find stale documents that should be moved
```cypher
MATCH (d:IngestedDocument)
WHERE duration.between(d.ingested_at, datetime()).days >= 14
  AND d.stale_moved = false
RETURN d.original_filename, d.original_path
```

### Get ingestion statistics by category
```cypher
MATCH (e:ProcessedExport)-[:EXTRACTED]->(f)
RETURN e.original_filename,
       count(f) as total_files,
       e.categories
ORDER BY e.processed_at DESC
LIMIT 10
```

---

## Migration Strategy

### Transition from file-watchman cron jobs

**Step 1: Parallel operation (1 week)**
- Deploy The Watchman collectors
- Keep existing cron jobs running
- Monitor both systems for consistency
- Verify Neo4j graph creation

**Step 2: Gradual cutover**
- Disable dedupe cron job first (stable functionality)
- Monitor for 2-3 days
- Disable document ingestion cron job
- Monitor for 2-3 days
- Disable export processing cron job

**Step 3: Cleanup**
- Remove cron jobs from crontab
- Archive file-watchman repo (don't delete)
- Migrate SQLite history to Neo4j (optional)
- Update documentation

### SQLite to Neo4j Migration (Optional)

```python
# scripts/migrate_sqlite_to_neo4j.py
import sqlite3
from neo4j import GraphDatabase

def migrate_photos_db():
    """Migrate photo_dedupe history to Neo4j."""
    conn = sqlite3.connect('~/.local/share/photo_dedupe/photos.sqlite3')
    # Read all processed photos
    # Create corresponding :MediaFile nodes in Neo4j

def migrate_ingestion_db():
    """Migrate document ingestion history."""
    # Similar pattern for document_ingestion/ingested.sqlite3

# Run once during migration, then delete SQLite databases
```

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_file_ingest_hasher.py
def test_hasher_consistency():
    """Verify hash calculation is deterministic."""

# tests/unit/test_file_ingest_router.py
def test_tag_matching_priority():
    """Verify tags match in correct order (first wins)."""

# tests/unit/test_file_ingest_graph.py
def test_graph_writer_creates_nodes():
    """Verify Neo4j nodes created correctly."""
```

### Integration Tests
```python
# tests/integration/test_file_ingest_dedupe.py
def test_dedupe_collector_end_to_end():
    """Test full dedupe workflow: detect, hash, route, graph."""

# tests/integration/test_file_ingest_documents.py
def test_document_collector_rag_integration():
    """Verify documents copied to RAG dir and tracked in graph."""

# tests/integration/test_file_ingest_exports.py
def test_export_collector_extraction():
    """Verify zip extraction, categorization, and routing."""
```

### Manual Testing Checklist
- [ ] Create test files in Downloads, verify processing
- [ ] Test duplicate detection across multiple runs
- [ ] Verify tag priority with conflicting matches
- [ ] Test export zip with mixed file types
- [ ] Verify Neo4j graph relationships created
- [ ] Test stale file movement after 14 days
- [ ] Verify collectors restart after crash
- [ ] Test with large files (500MB+)

---

## Deployment Considerations

### Resource Requirements
- **CPU:** +0.5 core per collector (3 collectors = +1.5 cores)
- **Memory:** +200MB per collector (3 collectors = +600MB)
- **Disk:** Same as current (files are copied/moved, not duplicated)
- **Network:** Minimal (local file operations + Neo4j queries)

### Performance Expectations
- **File detection latency:** < 5 seconds from file creation
- **Processing time:**
  - Media file: 50-200ms (hash + move)
  - Document: 100-300ms (hash + copy + graph)
  - Export zip: 500ms-5s (extraction + routing + graph)
- **Neo4j query time:** < 50ms per file processed

### Monitoring
- Health check endpoints for each collector
- Prometheus metrics for:
  - Files processed per minute
  - Duplicate detection rate
  - Processing errors
  - Queue depth (if async processing added)
- Log aggregation in Watchman's logging system

---

## Known Limitations & Future Work

### Current Limitations
1. **No cross-collector coordination:** Each collector operates independently
2. **No priority queue:** Files processed in detection order
3. **Limited retry logic:** Failed operations logged but not retried
4. **Synchronous processing:** May block on large files

### Future Enhancements
- Async file processing with queue
- Cross-collector coordination (e.g., exports might contain media)
- ML-based file categorization (beyond extension matching)
- Integration with visual timeline (screenshots of file operations)
- Web UI for ingestion management
- Configurable retention policies in graph database

---

## References

### Source Projects
- **file-watchman repo:** `E:\_projectsGithub\file-watchman\`
  - ⚠️ **STILL ACTIVE - DO NOT DELETE YET**
  - See [`file_ingest_migration.md`](./file_ingest_migration.md) for safe archival timeline
- **dedupe_downloads.py:** Working implementation (518 files processed, running in production)
- **Feature specs:** `file-watchman/docs/features/*.md`
- **Implementation plan:** `file-watchman/docs/plans/repository-refactor-and-implementation.md`

### The Watchman Integration Points
- **Neo4j schema:** `schemas/graph_schema.cypher`
- **Unified architecture:** `docs/unified/architecture.md`
- **Docker orchestration:** `docker-compose.yml`
- **Config management:** `app/utils/config.py`

---

**Document Version:** 1.0
**Created:** 2025-11-10
**Status:** Ready for Implementation
**Estimated Start:** After Phase 1 (Visual Timeline, System Graph, Memory) complete
