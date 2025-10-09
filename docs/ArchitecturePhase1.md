Got it. Refocusing **The Watchman** to “what’s happening on *my* machine” + “where everything lives,” and adding continuous screenshots+OCR. Here’s the *tight* domain set and exactly how they fit together.

# The Watchman — Tight Domain Map (Computer-Centric)

## 1) System State Graph

**What it owns:** Truth about *entities & topology* on your machine.

* **Entities:** `Directory`, `File/Doc`, `Project`, `Software`, `Service/Container`, `ConfigFile`, `User`, `MCPServer`, `Dataset` (e.g., Neo4j DB), `NetworkEndpoint`.
* **Rels:** `CONTAINS`, `DEPENDS_ON`, `USES_CONFIG`, `RUNS_ON` (service→host), `EXPOSES` (service→port), `PROVIDES_TOOL` (MCP server→tool), `LOCATED_IN` (project→dir), `BACKED_BY` (service→dataset).
* **Why:** This is the “map”: *where* things are, *how* they connect.

**MVP checks**

* “Where is my Neo4j data dir?” → returns absolute path(s).
* “List all MCP servers and the tools they expose.”
* “Which Docker containers are up, and what ports do they expose?”

---

## 2) Memory & Change

**What it owns:** *Time* and *meaning*.

* **Event stream:** File changes (watchdog/fanotify), container up/down, service restarts, package installs/updates.
* **Embeddings:** Vectorized summaries for docs/configs and OCR’d text (see Domain 3).
* **Change views:** “What changed in `/etc` since 8am?”, “Which containers restarted today?”

**MVP checks**

* Edit `/etc/nginx/nginx.conf` → event captured → “Show config changes today” returns it.
* Ask “find configs mentioning 5432” → vector hits + hydrated paths.

---

## 3) Visual Timeline (Screenshots → OCR → Context)

**What it owns:** Continuous **screen captures** turned into searchable context.

* **Capture:** Periodic screenshots (e.g., every 1-10 sec; hotkey for “now”).
* **OCR:** Local OCR (e.g., Tesseract or PaddleOCR) → text blocks with bounding boxes. (more likely to be a tandem of local model review and ATSPI OCR.)
* **Vision tags (optional idle-time):** App/window titles; lightweight vision labels (UI keywords, logos, app icons).
* **Graph model:** `:Snapshot {ts, app, window, path}`
  `(:Snapshot)-[:HAS_OCR]->(:Chunk {text, embedding})`
  `(:Snapshot)-[:IN_DIR]->(:Directory)`; `(:Snapshot)-[:SEEN_APP]->(:Software)`
* **Privacy:** Local-only; configurable redaction (domains/regex), auto-delete images after N days while keeping OCR text if desired.

**MVP checks**

* “What window was I using at 2:15pm?” → last `:Snapshot` by ts.
* “Find the shell command I copy-pasted earlier” → OCR text vector search.
* “When did Docker Desktop pop errors today?” → OCR text “Docker” + app/window filter.

---

## 4) Agent Interface & Orchestration

**What it owns:** The API, tool routing, and answer assembly.

* **Endpoints:**

  * `POST /ask` → routes to graph queries, event queries, screenshot/OCR search, formats answer w/ sources (paths, timestamps).
  * `POST /ingest` → sources/docs; `POST /admin/scan` → rescan software/projects; `POST /admin/screenshot` → force capture.
* **Routing:** Keyword/intent heuristics (and later LLM classifier) choose: Cypher/GraphQL vs. vector search vs. timeline search.
* **LLM backends:** Ollama local (primary) with OpenRouter fallback.
* **Outputs:** Always include **paths + timestamps + entity IDs** (so you can click/jump).

**MVP checks**

* “Where’s the Docker Compose for my web dashboard?” → path + linked project + service.
* “What was I working on right before lunch?” → last 3 snapshots + app names.

---

## 5) MCP Registry & Control (Infra-as-Context)

**What it owns:** MCP service catalog **and** local runtime control hooks.

* **Registry:** `:MCPServer {name, url, status}` + `(:MCPServer)-[:PROVIDES_TOOL]->(:Tool {name, schema})`.
* **Control:** Start/stop **local** MCP servers via Docker/Compose; health checks; version tags.
* **Graph links:** `(:MCPServer)-[:RUNS_ON]->(:Container)`; `(:Container)-[:EXPOSES]->(:NetworkEndpoint)`; `(:Container)-[:USES_VOLUME]->(:Directory)`.
* **Why:** Watchman knows *which MCPs exist*, *where they live*, and can spin them up.

**MVP checks**

* “Start the bookmarks MCP and register it.” → container up, registry updated.
* “Which MCPs are down?” → status list + last health check.

---

## Out of scope (explicitly)

* **Personal data bridges** (email/notes/calendar) — *not Watchman’s job*.
* Cloud sync/remote user data.
* Anything beyond “what’s on my machine” + “what’s running here.”

---

# Minimal schemas (additive)

**Snapshots (screens)**

```cypher
CREATE CONSTRAINT snapshot_id IF NOT EXISTS
FOR (s:Snapshot) REQUIRE s.id IS UNIQUE;

CREATE (s:Snapshot {
  id: $uuid, ts: datetime($iso), app: $app, window: $title, path: $imgPath
});
```

**OCR chunks + vectors**

```cypher
CREATE CONSTRAINT chunk_hash IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.content_hash IS UNIQUE;

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: { 'vector.dimensions': 1024, 'vector.similarity_function': 'cosine' }};

MERGE (c:Chunk {content_hash:$hash})
ON CREATE SET c.text=$text, c.embedding=$vec
WITH c MATCH (s:Snapshot {id:$sid}) MERGE (s)-[:HAS_OCR]->(c);
```

**Runtime/MCP/Containers**

```cypher
MERGE (m:MCPServer {name:$name})
SET m.url=$url, m.status=$status
WITH m
UNWIND $tools AS t
  MERGE (tool:Tool {name:t.name})
  MERGE (m)-[:PROVIDES_TOOL]->(tool);
```

---

# Concrete pipelines

**A) Screenshot → OCR → Vector**

1. `cron/systemd` timer triggers `capture.py` → saves PNG + creates `:Snapshot`.
2. `ocr.py` (queue/worker) extracts text (redact patterns), chunks → embeddings (Ollama) → `:Chunk` + vector index.
3. Optional idle-time vision tags: detect known app chrome/keywords → set `app`, `window`, `tags`.

**B) System scan (seed/refresh)**

* Projects in `~/projects` → `:Project` + `LOCATED_IN`.
* Software: `apt|brew list` → `:Software{name,version}`; running containers → `:Service/:Container`.
* Config roots: `/etc`, `.env`, `~/.ssh`.
* Link `:Service` ↔ `:ConfigFile` where detectable.

**C) MCP lifecycle**

* YAML registry → `mcp_registry.py` loads → `docker compose up serviceX` → probe health → write `:MCPServer` & links.

---

# Query patterns you can use Day 1

* **Locate:**
  “Where is `docker-compose.yml` for *dashboard*?”
  `MATCH (p:Project)-[:CONTAINS]->(f:File) WHERE p.name CONTAINS 'dashboard' AND f.name='docker-compose.yml' RETURN f.path;`

* **Recent changes:**
  “What changed in `/etc` since 10:00?”
  `MATCH (e:Event)-[:ACTED_ON]->(f:File) WHERE f.path STARTS WITH '/etc' AND e.ts > datetime('2025-10-09T10:00:00-05:00') RETURN f.path, e.ts ORDER BY e.ts DESC;`

* **Screen recall (semantic):**
  “Find OCR text about *TLS cert* from this morning.”
  `CALL db.index.vector.queryNodes('chunk_embedding', 8, $qvec) YIELD node AS c, score MATCH (s:Snapshot)-[:HAS_OCR]->(c) WHERE date(s.ts)=date() RETURN s{.ts,.app,.window,.path}, c.text, score LIMIT 8;`

* **Infra status:**
  “List MCP servers and health.”
  `MATCH (m:MCPServer) OPTIONAL MATCH (m)-[:RUNS_ON]->(ctr:Container) RETURN m.name, m.status, ctr.name, ctr.state;`

---

# Practical defaults (single-user, local-first)

* **Screenshot cadence:** 1–3 min; on-demand hotkey; auto-pause in full-screen apps if desired.
* **Retention:** Keep raw images 7–14 days; OCR text 90 days (or until disk threshold).
* **Redaction:** Domains, emails, tokens via regex; allow per-app allow/deny list.
* **Storage:** `/var/lib/watchman/{shots,ocr,chunks}` (paths also in Neo4j).
* **CPU control:** OCR + embeddings queue with nice/ionice; run heavy vision only on idle.

---

# What to ship next (no more planning, just do)

1. **Create `watchman/` repo skeleton** with domains:
   `domains/system_graph/`, `domains/memory_change/`, `domains/visual_timeline/`, `domains/mcp_registry/`, `app/` (FastAPI).
2. **Implement Visual Timeline MVP:** `capture.py`, `ocr.py`, Cypher upserts, vector index.
3. **Add 3–4 System Graph seeders:** projects scan, software list, docker ps, config roots.
4. **Expose `/ask` with three intents:** *locate*, *changed_since*, *find_text* (OCR vector).
5. **Wire MCP registry:** YAML → graph + basic `docker compose` start/stop.

That set delivers the “computer steward” you described: knows **where** things are, **what’s running**, **what changed**, and **what you were looking at**—and can spin up MCP servers on demand.
