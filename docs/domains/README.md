# Domain Implementation Documentation

This directory contains detailed implementation plans and specifications for each domain in The Watchman system.

## Available Documentation

### File Ingest Domain (from file-watchman)

**Implementation Plan:** [`file_ingest_implementation.md`](./file_ingest_implementation.md)
- Complete 3-week implementation timeline
- Neo4j schema extensions
- Docker Compose integration
- Migration strategy from standalone cron scripts

**Feature Specifications:**
- [`file_ingest_documents.md`](./file_ingest_documents.md) - Document ingestion for RAG system
- [`file_ingest_exports.md`](./file_ingest_exports.md) - Knowledge export processing

### Status

| Domain | Status | Directory | Documentation |
|--------|--------|-----------|---------------|
| System Graph | ✅ Complete | `domains/system_graph/` | N/A (implemented) |
| Memory & Change | ✅ Complete | `domains/memory_change/` | N/A (implemented) |
| Visual Timeline | ✅ Complete | `domains/visual_timeline/` | N/A (implemented) |
| GUI Collector | ⏳ Planned | `domains/gui_collector/` | Coming soon |
| File Ingest | ⏳ Planned | `domains/file_ingest/` | This directory |
| MCP Registry | ⏳ Stub | `domains/mcp_registry/` | Coming soon |
| Agent Interface | ⏳ Stub | `domains/agent_interface/` | Coming soon |

## Domain Overview

### Implemented Domains

**System Graph** - Maps entities on the machine (projects, files, containers, services)
**Memory & Change** - Tracks file system events and modifications
**Visual Timeline** - Screenshot capture, OCR, and embeddings

### Planned Domains

**GUI Collector** - AT-SPI event capture from ColdWatch
**File Ingest** - Download directory automation from file-watchman
**MCP Registry** - MCP server management and control
**Agent Interface** - Natural language query routing and LLM integration

## Integration Architecture

All domains write to the unified Neo4j graph database, enabling powerful cross-domain queries:

```cypher
// Example: Find what I was working on when a file was downloaded
MATCH (snapshot:Snapshot)-[:HAS_OCR]->(chunk:Chunk),
      (media:MediaFile {filename: "downloaded-image.jpg"})
WHERE abs(duration.between(snapshot.ts, media.processed_at).seconds) < 300
RETURN snapshot.ts, chunk.text, snapshot.app
```

See [`docs/unified/architecture.md`](../unified/architecture.md) for the complete unified architecture.
