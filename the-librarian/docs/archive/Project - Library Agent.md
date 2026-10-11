# 🚀 Project - Library Agent

This project outlines the development of a RAG (Retrieval-Augmented Generation) system using a graph database for advanced context management.

**Related Note:** [[LLM/KnowledgeAgents/Project_Library_Agent/Librarian_Pattern_Implementation_Plan]]

---

## Phase 1 — Stand up the graph + vectors + Python agent (very detailed)

### Goals
- Neo4j running locally with **native vector index**.
- Minimal graph schema for `Doc`/`Chunk` and embeddings stored **in Neo4j**.
- **FastAPI** service with two endpoints:
    - `POST /ingest` (load → chunk → embed via Ollama → upsert to Neo4j)
    - `POST /ask` (embed query → vector search in Neo4j → optional LLM answer)
- Optional GraphQL (Python) for structured access, but keep it lean.

### Step-by-step
1.  **Repo scaffold:** `neo4j-rag-python/` with `app/`, `data/`, `.env`, and `requirements.txt`.
2.  **Run Neo4j (Docker) & connect from Python.**
3.  **Define minimal graph schema + vector index** for `:Doc` and `:Chunk` nodes.
4.  **Choose local embeddings model** (e.g., `nomic-embed-text` via Ollama).
5.  **Implement Ingestion (`POST /ingest`):** Load files, split into chunks, embed, and upsert to Neo4j.
6.  **Implement Retrieval (`POST /ask`):** Embed query, perform vector search in Neo4j, assemble context, and optionally send to an LLM for a final answer.
7.  **Smoke tests (pytest):** Verify connectivity, ingestion, and retrieval.

---

## Phase 2 — Small “feature → test” sprints (Python-centric)
- **Sprint A: Retrieval quality:** Add hybrid retrieval and a reranker.
- **Sprint B: System-level graph entities:** Introduce `:Project`, `:Software` nodes.
- **Sprint C: Ingestion utilities:** Build a CLI for ingestion.
- **Sprint D: Monitoring (lightweight):** Use `watchdog` to monitor directories for changes.
- **Sprint E: Cache + health:** Implement caching and a `/health` endpoint.
- **Sprint F: Graph Data Science (optional):** Use GDS for importance scoring.

---

## Phase 3 — Conceptual roadmap (only if you need it)
- **CDC eventing:** Use Neo4j's Change Data Capture for reactive updates.
- **eBPF monitoring:** Advanced, low-overhead file system monitoring.
- **RAG upgrades:** Multi-vector pipelines and stronger rerankers.
- **Security awareness:** Model secrets and key locations as nodes in the graph.
