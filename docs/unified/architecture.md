# Unified Architecture

**Last Updated:** 2025-10-14

The Watchman is now the canonical platform for system awareness, knowledge capture, and automation across the desktop. This document synthesizes the architecture plans and domain specifications that previously lived in the `coldwatch`, `file-watchman`, and `the-watchman` repositories.

## Guiding Principles

- **Local-first:** All data lives on the machine. No cloud dependencies for core capture or analysis.
- **Graph-centric:** Neo4j remains the system of record. Every collector writes entities and relationships into the graph so queries span domains without translation layers.
- **Modular collectors:** Each sensor runs as an independent worker with a narrow responsibility. Collectors can be enabled or disabled via configuration without impacting the rest of the system.
- **Actionable output:** The `/ask` API, automation runner, and MCP control layer turn captured knowledge into concrete answers or actions.

## The Power of Unification: Cross-Domain Queries

The primary value of The Watchman is not in any single data source, but in its ability to **correlate data across all of its collectors**. By unifying system events, user interactions, and visual context into a single, interconnected graph, the system can answer complex questions that are impossible for siloed tools to address.

This fusion of data transforms a simple log into a rich, queryable "memory" of the user's digital environment. The success of the project hinges on making these powerful graph traversals accessible through the `/ask` API.

For example, a user could ask:

> "Show me the text I was typing in my code editor right before the Docker container for my web-app started failing, and what was on my screen at that moment?"

Answering this requires combining data from three different domains in a single query:
1.  **GUI Collector (`coldwatch` lineage):** To get the text from the code editor (`:GuiEvent`).
2.  **Memory & Change:** To identify the Docker container failure event (`:Event`).
3.  **Visual Timeline:** To retrieve the corresponding screenshot (`:Snapshot`).

This capability is the central "why" behind the unified architecture.

## Domain Overview

### 1. System State Graph

Maps every entity on the machine—projects, files, containers, services, configurations, software installations, users, and network touch points. Existing seeders keep this data fresh by scanning key directories and orchestrators (Docker, systemd).

### 2. Memory & Change

Captures how the machine evolves over time. File system watchers, container event listeners, and installation trackers append `:Event` nodes with metadata and relationships to affected entities. Embedding pipelines summarize high-value documents for semantic recall.

### 3. Visual Timeline

Continuously captures screenshots, performs OCR, and generates embeddings for semantic search. Snapshots are linked to active applications, directories, and OCR chunks. Retention policies control both raw imagery and derived text.

### 4. GUI Application Collector (from ColdWatch)

ColdWatch’s AT-SPI capture loop becomes a first-class collector. It subscribes to text, state-change, and focus events, normalizes them, and writes `:GuiEvent` nodes. Relationships connect GUI events to `:Software`, `:Snapshot`, and the underlying project or container when resolvable.

### 5. File Ingestion Collector (from File Watchman)

The personal automation scripts evolve into a long-running collector. It watches the downloads directory, performs SHA-256 deduplication, and routes files into tagged destinations. Each processed item is stored as an `:IngestedDocument` node linked to its source file and target location.

### 6. Agent Interface & Orchestration

FastAPI remains the public interface. `/ask` orchestrates intent classification, Cypher query execution, and embedding search. Admin endpoints trigger rescans, screenshots, and automation flows. Connectors to MCP services allow Watchman to start, stop, and monitor auxiliary agents.

#### The Criticality of the `/ask` API
While the collectors gather a vast amount of data, this data is only as valuable as it is accessible. The `/ask` API is the most critical component of the system, serving as the bridge between the raw knowledge graph and the user. If this natural language interface is not powerful and intuitive, the entire system risks becoming a write-only database. Its successful implementation is the highest priority for delivering on the project's vision.

## Graph Schema Extensions

- `:GuiEvent { id, ts, app, role, window_title, object_id, text_hash, raw_text? }`
- `(:GuiEvent)-[:SEEN_IN]->(:Software)`
- `(:GuiEvent)-[:NEXT_EVENT]->(:GuiEvent)` (optional sequencing)
- `:IngestedDocument { hash, ts, path, mime_type, source, size }`
- `(:IngestedDocument)-[:DERIVED_FROM]->(:File)`
- `(:IngestedDocument)-[:ROUTED_TO]->(:Directory)`

These additions are implemented via idempotent Cypher migrations under `scripts/migrations/`.

## Pipelines

1. **Screenshot → OCR → Embedding**: Timer-driven capture writes snapshots, OCR workers derive text chunks, embedding service (Ollama/OpenRouter) generates vectors, relationships connect the pieces.
2. **AT-SPI Event Ingestion**: GUI collector listens to DBus, batches events, and writes to Neo4j with rate limiting and privacy-aware redaction.
3. **Downloads Ingestion**: File collector polls for new files, verifies age thresholds, deduplicates via hash, routes based on tags, and persists ingestion metadata.
4. **System Scans**: Periodic runs detect new projects, containers, and config files, updating topology relationships.
5. **Automation & MCP**: Automation runner responds to triggers or queries by invoking file operations, orchestrating Docker Compose services, and updating the graph.

## Privacy Controls

- Allow- and deny-lists for applications, paths, and window titles.
- Regex-based redaction applied uniformly to OCR text, GUI events, and ingested documents.
- Configurable retention for raw screenshots, OCR text, GUI raw text, and ingestion metadata.

## Performance & Resilience

- Each collector runs in its own container/process with resource limits.
- Loguru-based structured logging feeds centralized observability dashboards.
- Retry policies and circuit breakers isolate transient failures (DBus, Neo4j outages).
- Sampling controls prevent AT-SPI floods; ingestion collectors enforce queue depth limits.

## Documentation Map

- `docs/unified/privacy.md`: consolidated privacy and redaction policies.
- `docs/unified/testing.md`: comprehensive test strategy for collectors and API layers.
- `docs/unified/troubleshooting.md`: guidance for AT-SPI, OCR, and graph ingestion issues.
- `docs/observability/logging.md`: logging standards, sinks, and correlation guidelines.

This unified architecture replaces the stand-alone documentation from the prior repositories and serves as the source of truth going forward.

## Future Vision: Proactive Automation

Beyond serving as a reactive "memory" that answers user queries, the next evolutionary step for The Watchman is to enable **proactive assistance**.

With a complete and accurate knowledge graph of the user's environment, the system can begin to anticipate needs and automate common workflows. This transforms the tool from a passive observer into an active, intelligent assistant.

For example:
*   *"I see you've started the 'web-api' Docker container. This project is usually associated with the `~/projects/api-service` directory. Would you like me to open that folder in VS Code?"*
*   *"You just downloaded a `docker-compose.yml` file. Would you like me to scan it and add its services to the System Graph?"*