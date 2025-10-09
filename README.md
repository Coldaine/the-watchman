# The Watchman

A computer-centric knowledge graph system that tracks what's on your machine, what's running, what changed, and what you were looking at.

## Features

- **System State Graph**: Maps entities and topology on your machine (files, projects, containers, services, configs)
- **Memory & Change**: Event stream tracking file changes, container events, service restarts
- **Visual Timeline**: Continuous screenshots with OCR for searchable screen history
- **MCP Registry & Control**: Manage and control MCP servers via Docker Compose
- **Agent Interface**: Natural language queries powered by Ollama (local) with OpenRouter fallback

## Architecture

### Domains

- `domains/system_graph/` - Project, software, Docker, config scanners
- `domains/memory_change/` - File system watchers, event tracking
- `domains/visual_timeline/` - Screenshot capture, OCR, embeddings
- `domains/mcp_registry/` - MCP server registry and Docker control
- `domains/agent_interface/` - Query routing, LLM integration

### Tech Stack

- **Database**: Neo4j 5.x (graph + vector search)
- **API**: FastAPI + Uvicorn
- **LLM**: Ollama (local) with OpenRouter fallback
- **OCR**: Tesseract + ATSPI
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ollama running at http://192.168.1.69:11434 (or configure in .env)
- X11 display (for screenshot capture)

### Setup

1. Clone the repository
2. Copy environment template:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` with your configuration
4. Start services:
   ```bash
   docker-compose up -d
   ```
5. Initialize Neo4j schema:
   ```bash
   docker-compose exec api python -m scripts.init_schema
   ```

### Verify Installation

- Neo4j Browser: http://localhost:7474 (user: neo4j, pass: watchman123)
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

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

```
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

### Screenshot Intervals

Edit `SCREENSHOT_INTERVAL` in `.env` (in seconds):
- Fast: 10 seconds (high disk usage)
- Default: 300 seconds (5 minutes)
- Slow: 600 seconds (10 minutes)

### Privacy Controls

Configure in `.env`:
- `REDACT_PATTERNS`: Regex patterns to redact from OCR
- `EXCLUDE_APPS`: Apps to skip screenshot capture
- `IMAGE_RETENTION_DAYS`: How long to keep raw images
- `OCR_RETENTION_DAYS`: How long to keep OCR text

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

## Roadmap

- [ ] Phase 0: Foundation & Contracts ✅
- [ ] Phase 1: Domain Implementations
  - [ ] Visual Timeline
  - [ ] System Graph Seeders
  - [ ] Event & Change Tracking
  - [ ] MCP Registry & Control
- [ ] Phase 2: Integration & Orchestration
- [ ] Web UI (React + GraphQL)
- [ ] Browser extension integration
- [ ] Mobile companion app

## License

MIT

## Contributing

See CONTRIBUTING.md for development guidelines.
