# The Watchman — Implementation Plan

## Executive Summary

**Optimal Parallel Agent Count: 4-5 agents**

- **Phase 0 (Foundation):** 1 agent, sequential (~2-3 days)
- **Phase 1 (Parallel Build):** 4 agents, simultaneous (~5-7 days per agent)
- **Phase 2 (Integration):** 1 agent, sequential (~2-3 days)

This plan maximizes parallelization while respecting hard dependencies. After Phase 0 establishes contracts and infrastructure, 4 independent streams can proceed simultaneously with minimal coordination overhead.

---

## Dependency Analysis

### Critical Path Dependencies

```
Phase 0: Infrastructure & Contracts (BLOCKING)
    ├─→ Neo4j setup + base schema
    ├─→ FastAPI skeleton
    ├─→ Node/relationship type definitions
    └─→ API contract definitions

Phase 1: Parallel Implementation (INDEPENDENT)
    ├─→ Stream A: Visual Timeline
    ├─→ Stream B: System Graph Seeders
    ├─→ Stream C: Event & Change Tracking
    └─→ Stream D: MCP Registry & Control

Phase 2: Integration & Orchestration (BLOCKING)
    ├─→ Query routing & intent classification
    ├─→ Agent interface implementation
    └─→ End-to-end testing
```

### Why This Parallelization Works

1. **Phase 0 eliminates interface ambiguity** — All agents get clear Neo4j schemas and API contracts
2. **Domain isolation** — Each stream operates on distinct graph nodes and relationships
3. **Minimal cross-stream communication** — Agents only need to honor the schema contracts
4. **Natural boundaries** — File watchers don't care about OCR; MCP registry doesn't care about screenshots

---

## Phase 0: Foundation & Contracts (Agent 0 — Infrastructure)

**Duration:** Sequential, ~2-3 days
**Agent:** Infrastructure specialist

### Deliverables

1. **Repository structure**
   ```
   watchman/
   ├── domains/
   │   ├── system_graph/
   │   ├── memory_change/
   │   ├── visual_timeline/
   │   ├── mcp_registry/
   │   └── agent_interface/
   ├── app/
   │   ├── api/
   │   ├── models/
   │   └── utils/
   ├── tests/
   ├── config/
   ├── docker-compose.yml
   └── requirements.txt
   ```

2. **Neo4j setup**
   - Docker Compose with Neo4j 5.x
   - Initial database creation
   - Health check endpoint
   - Connection pooling config

3. **Core schema definitions** (`schemas/contracts.cypher`)
   ```cypher
   # Node types with constraints
   CREATE CONSTRAINT snapshot_id IF NOT EXISTS
   FOR (s:Snapshot) REQUIRE s.id IS UNIQUE;

   CREATE CONSTRAINT chunk_hash IF NOT EXISTS
   FOR (c:Chunk) REQUIRE c.content_hash IS UNIQUE;

   CREATE CONSTRAINT file_path IF NOT EXISTS
   FOR (f:File) REQUIRE f.path IS UNIQUE;

   CREATE CONSTRAINT dir_path IF NOT EXISTS
   FOR (d:Directory) REQUIRE d.path IS UNIQUE;

   CREATE CONSTRAINT project_id IF NOT EXISTS
   FOR (p:Project) REQUIRE p.id IS UNIQUE;

   CREATE CONSTRAINT software_key IF NOT EXISTS
   FOR (sw:Software) REQUIRE sw.key IS UNIQUE;

   CREATE CONSTRAINT mcp_name IF NOT EXISTS
   FOR (m:MCPServer) REQUIRE m.name IS UNIQUE;

   # Vector indexes
   CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
   FOR (c:Chunk) ON (c.embedding)
   OPTIONS { indexConfig: {
     'vector.dimensions': 1024,
     'vector.similarity_function': 'cosine'
   }};

   # Relationship types (documented, not enforced)
   # :CONTAINS, :DEPENDS_ON, :USES_CONFIG, :RUNS_ON, :EXPOSES,
   # :PROVIDES_TOOL, :LOCATED_IN, :BACKED_BY, :HAS_OCR,
   # :IN_DIR, :SEEN_APP, :ACTED_ON
   ```

4. **FastAPI skeleton** (`app/main.py`)
   - Basic ASGI app with CORS
   - Health check at `/health`
   - Neo4j connection middleware
   - Stub routes: `/ask`, `/ingest`, `/admin/scan`, `/admin/screenshot`
   - Logging configuration

5. **Shared utilities** (`app/utils/`)
   - `neo4j_client.py` — Connection pool, transaction helpers
   - `embedding.py` — Ollama embedding wrapper (generic interface)
   - `config.py` — Environment-based config (DB URL, Ollama URL, etc.)

6. **API contract documentation** (`docs/api_contracts.md`)
   - Request/response schemas for each endpoint
   - Graph query patterns each domain must support
   - Event schema for change tracking

### Success Criteria

- [ ] `docker-compose up` starts Neo4j and FastAPI
- [ ] `curl localhost:8000/health` returns 200
- [ ] Neo4j constraints and indexes exist
- [ ] All 4 stream agents can clone repo and start independent work

---

## Phase 1: Parallel Implementation (4 Agents)

**Duration:** Simultaneous, ~5-7 days per agent
**Coordination:** Minimal — agents commit to separate domain directories

### Stream A: Visual Timeline (Agent 1)

**Domain:** `domains/visual_timeline/`
**Dependencies:** Phase 0 contracts only

#### Responsibilities

1. **Screenshot capture** (`capture.py`)
   - Configurable interval (default 5min, supports 1-10sec via config)
   - Hotkey trigger (use `pynput` or similar)
   - Active window detection via `xdotool` (Linux) or `pygetwindow` (cross-platform)
   - Save to `/var/lib/watchman/shots/{uuid}.png`
   - Create `:Snapshot` node in Neo4j with `{id, ts, app, window, path}`

2. **OCR pipeline** (`ocr.py`)
   - Queue-based worker (consume from Redis/filesystem queue)
   - Primary: ATSPI OCR for accessibility tree text
   - Fallback: Tesseract/PaddleOCR for visual text extraction
   - Local vision model (optional): Extract app/window/UI keywords
   - Text chunking (max 500 chars per chunk)
   - Redaction patterns (regex for emails, tokens, configurable domains)

3. **Embedding generation** (`embedder.py`)
   - Ollama API client (`http://192.168.1.69:11434`)
   - Generate embeddings for each OCR chunk
   - Create `:Chunk` nodes with `{content_hash, text, embedding}`
   - Link `(:Snapshot)-[:HAS_OCR]->(:Chunk)`

4. **Graph integration** (`graph_writer.py`)
   - Batch upsert chunks (use UNWIND for efficiency)
   - Link snapshots to `:Directory` (via `path` parent dir)
   - Link snapshots to `:Software` (via `app` name matching)

5. **Retention & privacy** (`cleanup.py`)
   - Configurable image retention (default 14 days)
   - OCR text retention (default 90 days)
   - Privacy rules: allowlist/denylist apps
   - Manual purge endpoint

#### Deliverables

- [ ] `capture.py` runs as systemd timer (every 5min) and captures screenshots
- [ ] `ocr.py` processes queue and extracts text (ATSPI + Tesseract)
- [ ] Embeddings generated via Ollama and stored in Neo4j
- [ ] Query: "Find OCR text about 'docker' from this morning" returns results
- [ ] Privacy redaction working (test with fake token in screenshot)

#### Testing

- Screenshot capture with known window title
- OCR extraction of known text (e.g., terminal output)
- Vector search for known phrase
- Retention cleanup (mock old snapshots)

---

### Stream B: System Graph Seeders (Agent 2)

**Domain:** `domains/system_graph/`
**Dependencies:** Phase 0 contracts only

#### Responsibilities

1. **Project scanner** (`scanners/projects.py`)
   - Scan `~/projects`, `~/code`, `~/dev` (configurable roots)
   - Detect project types: `package.json` → Node, `Cargo.toml` → Rust, etc.
   - Create `:Project {id, name, type, path, last_scan}`
   - Create `:Directory` tree up to project root
   - Link `(:Project)-[:LOCATED_IN]->(:Directory)`
   - Link `(:Project)-[:CONTAINS]->(:File)` for key files (compose, configs)

2. **Software inventory** (`scanners/software.py`)
   - Linux: `rpm -qa` (Fedora), `dpkg -l` (Ubuntu), `brew list` (macOS)
   - Create `:Software {key, name, version, source}`
   - Detect running processes (`ps aux`) and link to `:Software`
   - Identify system services (`systemctl list-units`)

3. **Docker discovery** (`scanners/docker.py`)
   - `docker ps -a --format json` → running/stopped containers
   - Create `:Container {name, id, image, state, created}`
   - Extract exposed ports → create `:NetworkEndpoint {host, port, protocol}`
   - Link `(:Container)-[:EXPOSES]->(:NetworkEndpoint)`
   - Parse `docker inspect` for volumes → link to `:Directory`
   - Detect Compose projects via labels → link to `:Project`

4. **Config mapping** (`scanners/configs.py`)
   - Scan `/etc`, `~/.config`, `~/.ssh`, `.env` files in projects
   - Create `:ConfigFile {path, type, last_modified}`
   - Link `(:Service)-[:USES_CONFIG]->(:ConfigFile)` where detectable
   - Example: nginx.conf → nginx service, `.env` → Docker Compose project

5. **Dependency detection** (`scanners/dependencies.py`)
   - Parse `package.json`, `Cargo.toml`, `requirements.txt`, etc.
   - Create `(:Project)-[:DEPENDS_ON]->(:Software)` links
   - Detect system library usage (ldd output for binaries)

#### Deliverables

- [ ] `POST /admin/scan` triggers all scanners
- [ ] Query: "Where is my Neo4j data dir?" returns path from Docker volume scan
- [ ] Query: "List projects using Docker Compose" returns linked projects
- [ ] Query: "Which containers are running?" returns container list with ports
- [ ] Config files linked to services (at least nginx, Docker examples)

#### Testing

- Scan known project directory with Compose file
- Verify `:Project → :File → docker-compose.yml` link
- Scan Docker containers and verify port mappings
- Config detection for known service (nginx, postgres)

---

### Stream C: Event & Change Tracking (Agent 3)

**Domain:** `domains/memory_change/`
**Dependencies:** Phase 0 contracts only

#### Responsibilities

1. **File system watcher** (`watchers/filesystem.py`)
   - Use `watchdog` library (or `inotify` directly on Linux)
   - Monitor: `/etc`, `~/projects`, `~/.config`, Docker volumes
   - Capture events: `CREATE`, `MODIFY`, `DELETE`, `MOVE`
   - Create `:Event {id, ts, type, path, user}`
   - Link `(:Event)-[:ACTED_ON]->(:File|Directory)`

2. **Container events** (`watchers/docker.py`)
   - Subscribe to Docker events API (`docker events --format json`)
   - Track: `start`, `stop`, `die`, `restart`, `create`, `destroy`
   - Create `:Event {id, ts, type, container_name}`
   - Link `(:Event)-[:ACTED_ON]->(:Container)`

3. **Service monitoring** (`watchers/services.py`)
   - Poll `systemctl status` for watched services (configurable list)
   - Detect state changes (active → failed)
   - Create `:Event` for service state transitions

4. **Package changes** (`watchers/packages.py`)
   - Monitor package manager logs (`/var/log/dnf.log`, `/var/log/apt/history.log`)
   - Detect installs, updates, removals
   - Create `:Event {id, ts, type, package}`
   - Link `(:Event)-[:ACTED_ON]->(:Software)`

5. **Change views** (`queries/changes.py`)
   - Implement timeline queries:
     - "What changed in `/etc` since 8am?"
     - "Which containers restarted today?"
     - "Show package installs this week"
   - Return sorted event lists with paths and timestamps

6. **Embedding updates** (`embedder.py`)
   - On file MODIFY events, regenerate embeddings for docs/configs
   - Debounce rapid changes (wait 5 min after last change)
   - Update existing `:Chunk` embeddings or create new versions

#### Deliverables

- [ ] File watcher running and capturing events in `/etc`
- [ ] Docker event stream tracked
- [ ] Query: "What changed in `/etc` since 10:00?" returns event list
- [ ] Query: "Which containers restarted today?" returns container events
- [ ] Modified config file triggers embedding regeneration

#### Testing

- Create/edit/delete test file and verify events
- Start/stop Docker container and verify events
- Time-range queries return correct results
- Embedding update triggered by file modification

---

### Stream D: MCP Registry & Control (Agent 4)

**Domain:** `domains/mcp_registry/`
**Dependencies:** Phase 0 contracts only

#### Responsibilities

1. **YAML registry** (`config/mcp_registry.yaml`)
   ```yaml
   servers:
     - name: bookmarks
       compose_file: /opt/mcp/bookmarks/docker-compose.yml
       service: bookmarks-mcp
       health_check: http://localhost:3100/health
       tools:
         - name: add_bookmark
           schema: {...}
         - name: search_bookmarks
           schema: {...}
     - name: neo4j-mcp
       compose_file: /opt/mcp/neo4j-mcp/docker-compose.yml
       service: neo4j-mcp
       health_check: http://localhost:3200/health
   ```

2. **Registry loader** (`registry.py`)
   - Parse YAML on startup
   - Create `:MCPServer {name, url, status, compose_file}`
   - Create `:Tool {name, schema}` for each exposed tool
   - Link `(:MCPServer)-[:PROVIDES_TOOL]->(:Tool)`

3. **Docker Compose control** (`control.py`)
   - `start_server(name)` → `docker-compose -f {file} up -d {service}`
   - `stop_server(name)` → `docker-compose -f {file} down`
   - `restart_server(name)` → stop + start
   - Update `:MCPServer.status` in Neo4j

4. **Health checks** (`health.py`)
   - Periodic polling (every 5min) of health endpoints
   - Update `:MCPServer.status` → `up`, `down`, `degraded`
   - Link `:MCPServer` → `:Container` via name matching (Docker PS)

5. **Graph integration** (`graph_writer.py`)
   - Link `(:MCPServer)-[:RUNS_ON]->(:Container)`
   - Link `(:Container)-[:EXPOSES]->(:NetworkEndpoint)` for MCP ports
   - Link `(:Container)-[:USES_VOLUME]->(:Directory)` for MCP data

6. **API endpoints** (`api/mcp.py`)
   - `POST /mcp/start/{name}` → start MCP server
   - `POST /mcp/stop/{name}` → stop MCP server
   - `GET /mcp/list` → list all servers with status
   - `GET /mcp/{name}/tools` → list tools for a server

#### Deliverables

- [ ] YAML registry parsed and loaded into Neo4j
- [ ] Query: "List MCP servers and their status" returns registry
- [ ] `POST /mcp/start/bookmarks` starts container and updates status
- [ ] Health checks run periodically and update Neo4j
- [ ] Query: "Which MCPs are down?" returns filtered list

#### Testing

- Load test registry YAML with 2 servers
- Start MCP server via API and verify Docker container running
- Health check detects down server
- Tool listing query returns correct tools

---

## Phase 2: Integration & Orchestration (Agent 0 — Return)

**Duration:** Sequential, ~2-3 days
**Agent:** Same infrastructure agent from Phase 0

### Responsibilities

1. **Query routing** (`domains/agent_interface/router.py`)
   - Intent classification (keyword heuristics initially, LLM later)
   - Route types:
     - **Locate:** Cypher queries for paths/entities (`WHERE`, `MATCH`)
     - **Changed:** Event timeline queries (`Event.ts >`, `ORDER BY ts DESC`)
     - **Find text:** Vector search on OCR/embeddings
     - **Status:** MCP/container/service status queries
   - Examples:
     - "Where is docker-compose.yml?" → Locate
     - "What changed in /etc today?" → Changed
     - "Find OCR text about TLS" → Find text
     - "Which MCPs are running?" → Status

2. **Query assembly** (`domains/agent_interface/query_builder.py`)
   - Generate Cypher queries from intent + parameters
   - Vector search queries via `db.index.vector.queryNodes`
   - Event timeline filters (time ranges, paths, types)
   - Result hydration (expand paths, timestamps, related entities)

3. **LLM integration** (`domains/agent_interface/llm.py`)
   - Primary: Ollama local (`http://192.168.1.69:11434`)
   - Fallback: OpenRouter (use `OPENROUTER_API_KEY` from `~/.secrets`)
   - Context assembly: query results + user question
   - Response formatting: always include sources (paths, timestamps, entity IDs)

4. **Answer formatting** (`domains/agent_interface/formatter.py`)
   - Structured responses with:
     - **Answer:** Natural language response
     - **Sources:** List of `{type, path, timestamp, entity_id}`
     - **Query used:** Show Cypher/vector query for transparency
   - Markdown formatting for CLI/web display

5. **API implementation** (`app/api/ask.py`)
   - `POST /ask {query: string, context?: string}` → full pipeline
   - `POST /ingest {path: string, type?: string}` → manual doc ingestion
   - Error handling: fallback queries if intent classification fails

6. **End-to-end testing** (`tests/integration/`)
   - Test all MVP check queries from architecture doc
   - Verify cross-domain queries work (e.g., snapshot → app → software)
   - Performance checks (query latency < 500ms for simple queries)

### Deliverables

- [ ] `/ask` endpoint functional with all 4 route types
- [ ] Query: "Where is my Neo4j data dir?" returns correct path
- [ ] Query: "What changed in /etc since 10:00?" returns events
- [ ] Query: "Find OCR text about docker" returns snapshots
- [ ] Query: "Which MCPs are running?" returns status list
- [ ] All Phase 1 MVP checks pass end-to-end

### Success Criteria

- [ ] All 5 domains integrated and functional
- [ ] MVP queries from architecture doc return correct results
- [ ] Documentation updated with deployment instructions
- [ ] Docker Compose brings up entire stack (Neo4j + API + workers)

---

## Coordination & Handoff Protocol

### Agent Communication

- **Slack channel or shared doc** for blockers and interface changes
- **Daily async updates:** "Completed X, working on Y, blocked on Z"
- **No synchronous meetings required** — contracts defined in Phase 0

### Git Workflow

```
main
├── phase0-foundation (Agent 0)
├── phase1-visual-timeline (Agent 1)
├── phase1-system-graph (Agent 2)
├── phase1-events (Agent 3)
└── phase1-mcp-registry (Agent 4)
```

- Each agent works in isolated domain directory
- Merge to `main` when domain MVP is complete
- Schema changes require PR review (rare after Phase 0)

### Testing Strategy

- **Unit tests:** Each agent writes tests for their domain
- **Integration tests:** Agent 0 writes in Phase 2 after merges
- **Manual smoke tests:** Run MVP check queries after each merge

### Rollout Sequence

1. Phase 0 complete → Tag `v0.1-foundation`
2. Each Phase 1 stream merges independently → Tag `v0.2-{domain}`
3. Phase 2 complete → Tag `v1.0-mvp`

---

## Risk Mitigation

### Potential Blockers

1. **Neo4j schema conflicts**
   - Mitigation: Phase 0 defines ALL node types upfront
   - Each agent validates against `schemas/contracts.cypher`

2. **Embedding model changes**
   - Mitigation: `embedding.py` abstraction layer
   - Agents call `generate_embedding(text)`, don't care about model

3. **Docker environment differences**
   - Mitigation: `.env.example` with all required vars
   - Health checks fail fast with clear error messages

4. **Cross-domain query dependencies**
   - Mitigation: Phase 2 handles all cross-domain joins
   - Phase 1 agents only write to their own nodes

### Performance Considerations

- **Screenshot storage:** Plan for ~500MB/day at 5min intervals
- **OCR queue:** Use Redis or filesystem queue to prevent memory bloat
- **Vector search:** Neo4j 5.x vector indexes handle 100K+ chunks
- **Event volume:** Partition events by month if >1M events

---

## Post-MVP Enhancements (Future Agents)

After v1.0-mvp, additional parallel work streams can spin up:

- **Agent 5:** Web UI (React + GraphQL over Neo4j)
- **Agent 6:** Browser extension (history + bookmark sync)
- **Agent 7:** LLM intent classifier (replace keyword heuristics)
- **Agent 8:** Mobile companion app (query interface)
- **Agent 9:** Export/backup system (graph snapshots to S3)

These can proceed independently as long as they consume the Phase 2 API.

---

## Summary

**4-5 agents can work effectively in parallel** with this plan:

- **1 agent** builds foundation (Phase 0: ~2-3 days)
- **4 agents** build domains simultaneously (Phase 1: ~5-7 days)
- **1 agent** integrates everything (Phase 2: ~2-3 days)

**Total calendar time:** ~10-13 days (vs. 25-30 days sequential)

**Key success factors:**
1. Rigorous contract definition in Phase 0
2. Domain isolation in Phase 1 (minimal cross-talk)
3. Comprehensive integration testing in Phase 2
4. Clear Git workflow and communication protocol

This architecture supports **The Watchman's core mission:** know where everything is, what's running, what changed, and what you were looking at—delivered in 2 weeks instead of 1 month.
