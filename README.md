# The Watchman

A computer-centric knowledge graph system that tracks what's on your machine, what's running, what changed, what you were looking at, and what you were typing.

## Features

- **System State Graph**: Maps entities and topology on your machine (files, projects, containers, services, configs)
- **Memory & Change**: Event stream tracking file changes, container events, service restarts
- **Visual Timeline**: Continuous screenshots with OCR for searchable screen history
- **GUI Event Capture**: AT-SPI collector (ColdWatch lineage) records focused text and accessibility events
- **MCP Registry & Control**: Manage and control MCP servers via Docker Compose
- **Agent Interface**: Natural language queries powered by Ollama (local) with OpenRouter fallback

## Architecture

### Domains

- `domains/system_graph/` - Project, software, Docker, config scanners
- `domains/memory_change/` - File system watchers, event tracking
- `domains/visual_timeline/` - Screenshot capture, OCR, embeddings
- `domains/mcp_registry/` - MCP server registry and Docker control
- `domains/agent_interface/` - Query routing, LLM integration
- `domains/gui_collector/` - AT-SPI ingestion and normalization
- `domains/file_ingest/` - Downloads dedupe, routing, and ingestion metadata
  - **Media Deduplication:** SHA-256 hash-based duplicate detection with tag routing
  - **Document Ingestion:** Automatic RAG system feeding with age-based stale management
  - **Export Processing:** Zip extraction and categorization for knowledge artifacts

### Tech Stack

- **Database**: Neo4j 5.x (graph + vector search)
- **API**: FastAPI + Uvicorn
- **LLM**: Ollama (local) with OpenRouter fallback
- **OCR**: Tesseract + ATSPI
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ollama running at [http://192.168.1.69:11434](http://192.168.1.69:11434) (or configure in `.env`)
- X11 display (for screenshot capture)

### Setup

1. Clone the repository

2. Copy configuration template:

   ```bash
   cp config.toml.example config.toml
   ```

   Or use environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `config.toml` (or `.env`) with your configuration

4. Start services:

   ```bash
   docker-compose up -d
   ```

5. Initialize Neo4j schema:

   ```bash
   docker-compose exec api python -m scripts.init_schema
   ```

### Verify Installation

- Neo4j Browser: [http://localhost:7474](http://localhost:7474) (user: `neo4j`, pass: `watchman123`)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

## Usage

### MVP Queries

**Locate files/projects:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is my docker-compose.yml for the dashboard?"}'
```

**Recent changes:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What changed in /etc since 10:00?"}'
```

**Screen recall:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Find OCR text about TLS cert from this morning"}'
```

**MCP status:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Which MCP servers are running?"}'
```

### Admin Operations

**Trigger system scan:**

```bash
curl -X POST http://localhost:8000/admin/scan
```

**Force screenshot capture:**

```bash
curl -X POST http://localhost:8000/admin/screenshot
```

**Start MCP server:**

```bash
curl -X POST http://localhost:8000/mcp/start/bookmarks
```

## Development

### Structure

```text
.
├── app/              # FastAPI application
│   ├── api/         # API routes
│   ├── models/      # Pydantic models
│   └── utils/       # Shared utilities
├── domains/         # Domain implementations
├── schemas/         # Neo4j schemas
├── config/          # Configuration files
└── tests/           # Tests
```

### Testing

```bash
# Run all tests
docker-compose exec api pytest

# Run specific domain tests
docker-compose exec api pytest tests/unit/test_visual_timeline.py

# Integration tests
docker-compose exec api pytest tests/integration/
```

### Adding New Scanners

1. Create scanner in appropriate domain (e.g., `domains/system_graph/scanners/`)
2. Implement scanner interface
3. Register in scanner registry
4. Add tests

## Configuration

The Watchman supports **TOML configuration files** (recommended) or environment variables (legacy).

**Priority order:** `config.toml` > environment variables > `.env` file > defaults

### TOML Configuration (Recommended)

Copy `config.toml.example` to `config.toml` and customize:

```toml
[screenshot]
interval = 300  # seconds
enable_diffing = true  # Only capture when screen changes
diff_threshold = 0.10  # 10% change required

[screenshot.smart_capture]
enable_smart_capture = true
capture_on_app_switch = true  # Capture when changing apps
capture_on_idle_return = true  # Capture when returning from idle

[ocr]
enable_lazy_processing = false  # Process immediately vs. on-demand

[privacy]
redact_patterns = [".*@.*\\.com", "sk-.*", "ghp_.*"]
exclude_apps = ["keepassxc", "1password"]

[features]
visual_timeline = true
system_graph = true
gui_collector = false  # AT-SPI event capture
```

See `config.toml.example` for all available options.

### Legacy Environment Variables

Still supported for backward compatibility:

- `SCREENSHOT_INTERVAL`: Capture interval in seconds (default: 300)
- `REDACT_PATTERNS`: Regex patterns to redact from OCR
- `EXCLUDE_APPS`: Apps to skip screenshot or GUI capture
- `IMAGE_RETENTION_DAYS`: How long to keep raw images (default: 14)
- `OCR_RETENTION_DAYS`: How long to keep OCR text (default: 90)

## Troubleshooting

### Neo4j connection fails

Check health: `docker-compose ps`
View logs: `docker-compose logs neo4j`

### Screenshot capture not working

Ensure X11 forwarding: `xhost +local:docker`
Check DISPLAY variable is set

### OCR not detecting text

Verify Tesseract is installed in container
Check OCR worker logs: `docker-compose logs ocr-worker`

### GUI collector emitting no events

Ensure the container runs under a desktop user, verify `GTK_MODULES` configuration, and confirm AT-SPI packages are installed. See `docs/unified/troubleshooting.md` for deeper diagnostics.

### Downloads ingestion skipped files

Verify minimum file age, destination permissions, and lockfile status. See `docs/unified/troubleshooting.md` for the full checklist.

## Documentation

### Core Architecture
- **Unified architecture**: `docs/unified/architecture.md` - Complete system overview
- **System management**: `docs/unified/system_management.md` - Tool installs, backups, network, monitoring
- **MCP management**: `docs/unified/mcp_management.md` - MCP server orchestration strategy
- **Smart capture**: `docs/unified/smart_capture.md` - Screenshot diffing, lazy OCR, smart triggers

### Operations
- **Privacy & data handling**: `docs/unified/privacy.md`
- **Testing plan**: `docs/unified/testing.md`
- **Troubleshooting**: `docs/unified/troubleshooting.md`
- **Logging standards**: `docs/observability/logging.md`

## Roadmap

- [x] Phase 0: Foundation & Contracts ✅
- [ ] Phase 1: Domain Implementations (70% complete)
  - [x] Visual Timeline (Basic) ✅
  - [ ] Visual Timeline (Smart Features) - Planned
    - [ ] Screenshot diffing/hashing
    - [ ] Smart capture triggers
    - [ ] Similarity clustering
    - [ ] Lazy OCR processing
  - [x] System Graph Seeders ✅
  - [x] Event & Change Tracking ✅
  - [x] File Ingest Domain ✅
- [ ] Phase 2: System Management & MCP
  - [ ] MCP Registry & Control (25% - stubs)
    - [ ] Complete MCP server lifecycle management
    - [ ] Docker Hub integration
    - [ ] Local tool installation strategy
  - [ ] System Management Domain
    - [x] Software install monitoring (documented)
    - [ ] Backup management (orchestrator, verification, S3)
    - [ ] Network monitoring (topology, firewall, VPN)
    - [ ] Resource monitoring (CPU, memory, disk, I/O)
    - [ ] Configuration management (validation, rollback)
- [ ] Phase 3: Integration & Orchestration
  - [ ] Agent Interface completion
  - [ ] Review API (/review endpoint)
  - [ ] MCP orchestration & assignment
- [ ] Phase 4: Advanced Features
  - [ ] Web UI (React + GraphQL)
  - [ ] Browser extension integration
  - [ ] Mobile companion app
  - [ ] Proactive automation triggers
  - [ ] Security monitoring (CVE tracking, audit trail)

## License

MIT

## Contributing

See CONTRIBUTING.md for development guidelines.
