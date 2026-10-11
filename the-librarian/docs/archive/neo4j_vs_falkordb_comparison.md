### **Complete Minimal Viable Test Setup for Each Solution (Node.js Focus)**

#### 1. **Neo4j Community + Custom Pipeline - MOST NODE.JS NATIVE**
**Setup Steps:**
1. `docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest`
2. `mkdir neo4j-unity-docs && cd neo4j-unity-docs`
3. `npm init -y && npm install neo4j-driver express cors dotenv`
4. Create `server.js`:
```javascript
const express = require('express');
const neo4j = require('neo4j-driver');
const app = express();

const driver = neo4j.driver('bolt://localhost:7687', neo4j.auth.basic('neo4j', 'password'));

app.use(express.json());

// Ingest endpoint
app.post('/ingest', async (req, res) => {
  const session = driver.session();
  try {
    const { title, content, type, parent } = req.body;
    await session.run(
      'CREATE (doc:Document {title: $title, content: $content, type: $type, timestamp: datetime()})',
      { title, content, type }
    );
    res.json({ success: true });
  } finally {
    await session.close();
  }
});

app.listen(3000, () => console.log('Server running on port 3000'));
```
5. Create vector index via Neo4j browser: `CREATE VECTOR INDEX doc_embeddings FOR (n:Document) ON n.embedding OPTIONS {indexConfig: {'vector.dimensions': 384, 'vector.similarity_function': 'cosine'}}`

**Out-of-the-Box Capabilities:**
- ✅ **Database**: Robust graph DB with Cypher queries
- ✅ **Node.js Native**: Full control with neo4j-driver

**Custom Build Required:**
- 🔨 **Ingestion Pipeline**: Document parsing, entity extraction, embedding generation
- 🔨 **Auto-Updates**: Change detection, propagation logic, conflict resolution  
- 🔨 **Entity Resolution**: Deduplication algorithms, similarity matching
- 🔨 **Vector Search**: Embedding integration with OpenAI/sentence-transformers

**What You'd Have:** A Node.js Express API with full control over graph operations, but requires building ALL the KG logic yourself.[1][2][3][4]

**Effort Estimate:** 16-24 hours (2 hours setup, 14-22 hours building ingestion/update/resolution pipeline)

#### 2. **FalkorDB with Node.js - AI-OPTIMIZED WITH SOME NODE.JS SUPPORT**
**Setup Steps:**
1. `docker run -p 6379:6379 -it falkordb/falkordb:latest`
2. `mkdir falkor-unity-docs && cd falkor-unity-docs`  
3. `npm init -y && npm install @falkordb/falkordb express`
4. Create `server.js`:
```javascript
const express = require('express');
const { FalkorDB } = require(' @falkordb/falkordb');
const app = express();

const client = new FalkorDB({ host: 'localhost', port: 6379 });
const graph = client.graph('unity-docs');

app.use(express.json());

app.post('/ingest', async (req, res) => {
  const { title, content, type } = req.body;
  try {
    await graph.query(
      'CREATE (:Document {title: $title, content: $content, type: $type, timestamp: timestamp()})',
      { title, content, type }
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000);
```

**Out-of-the-Box Capabilities:**
- ✅ **Database**: Fast, AI-optimized graph DB
- ✅ **Node.js Client**: Official TypeScript client (falkordb-ts)
- ✅ **Vector Operations**: Built-in vector search optimized for LLMs

**Custom Build Required:**
- 🔨 **Auto-Updates**: Change propagation (though simpler than Neo4j)  
- 🔨 **Entity Resolution**: Custom deduplication logic
- 🔨 **File Monitoring**: Webhook/watcher for doc changes

**What You'd Have:** Fast graph DB with better AI integration than Neo4j, official Node.js support, but still need custom update logic.[5][6][7][8][9][10]

**Effort Estimate:** 8-12 hours (3 hours setup/learning FalkorDB, 5-9 hours custom update/resolution logic)

#### 3. **OpenSPG/KAG - LIMITED NODE.JS SUPPORT**
**Setup Steps:**
1. `curl -sSL https://raw.githubusercontent.com/OpenSPG/openspg/refs/heads/master/dev/release/docker-compose-west.yml -o docker-compose.yml`
2. `docker compose up -d` (starts services on ports 8887, 7687, etc.)
3. **Problem**: No official Node.js SDK - only Python/Java clients available
4. **Workaround**: Create Node.js wrapper around REST API:
```javascript
const express = require('express');
const axios = require('axios');
const app = express();

const KAG_API = 'http://localhost:8887/api'; // OpenSPG API endpoint

app.post('/ingest', async (req, res) => {
  try {
    const response = await axios.post(`${KAG_API}/knowledge/add`, req.body);
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000);
```

**Out-of-the-Box Capabilities:**
- ✅ **Ingestion**: Built-in document processors
- ✅ **Auto-Updates**: Schema evolution, incremental updates
- ✅ **Entity Resolution**: Built-in deduplication
- ✅ **Web UI**: Management interface

**Custom Build Required:**
- 🔨 **Node.js Integration**: HTTP API wrapper (no native SDK)
- 🔨 **Schema Setup**: Define Unity doc hierarchy in UI
- 🔨 **Authentication**: API key management for REST calls

**What You'd Have:** Most comprehensive KG features but poor Node.js integration - you're essentially making HTTP calls to Python services.[11][12][13]

**Effort Estimate:** 10-14 hours (4 hours setup/config, 6-10 hours building Node.js wrapper and schema)

#### 4. **Graphiti - PYTHON-ONLY (No Node.js Support)**
**Setup Steps:**
1. Graphiti is Python-only - no Node.js SDK available
2. **Workaround Options:**
   - Run Graphiti as separate Python service, call via HTTP
   - Use child_process to shell out to Python scripts
   - Abandon Node.js for this component

**Example HTTP Wrapper Approach:**
```javascript
// Node.js wrapper calling Python Graphiti service
const express = require('express');
const { spawn } = require('child_process');

app.post('/ingest', (req, res) => {
  const python = spawn('python', ['graphiti_wrapper.py', JSON.stringify(req.body)]);
  // Handle python process output...
});
```

**Out-of-the-Box Capabilities:**
- ✅ **Everything**: Best-in-class for temporal KGs
- ❌ **Node.js**: Zero native support

**What You'd Have:** Either abandon Node.js requirement or build complex polyglot architecture.[14][15][16][17]

**Effort Estimate:** 12-16 hours (if building HTTP wrapper) or switch to Python

### **Node.js Recommendation: FalkorDB**

**Why FalkorDB for Node.js:**
- Official Node.js/TypeScript client with good documentation
- AI-optimized (better for LLM integration than Neo4j)  
- Simpler setup than Neo4j for vector operations
- Active development specifically for LLM use cases
- Docker-friendly setup

**Missing Pieces You'll Build:**
- File watcher: Use `chokidar` npm package to monitor Unity docs
- Entity resolution: Custom logic using embeddings + similarity thresholds  
- Update propagation: OpenCypher queries to cascade changes

**Sample Complete Setup (FalkorDB + Node.js):**
```javascript
const express = require('express');
const chokidar = require('chokidar');
const { FalkorDB } = require(' @falkordb/falkordb');
const { encode } = require(' @sentence-transformers/transformers'); // hypothetical

const app = express();
const client = new FalkorDB();
const graph = client.graph('unity-docs');

// Auto-update watcher  
chokidar.watch('./unity-docs/**/*.md').on('change', async (path) => {
  // Read file, generate embedding, update graph
  const content = fs.readFileSync(path, 'utf8');
  const embedding = await encode(content);
  
  await graph.query(
    'MATCH (d:Document {path: $path}) SET d.content = $content, d.embedding = $embedding, d.updated = timestamp()',
    { path, content, embedding }
  );
});

app.listen(3000);
```

**Total Effort:** 8-12 hours for production-ready solution with auto-updates and entity resolution.

[1](https://neo4j.com/docs/javascript-manual/current/install/)
[2](https://akirkeby.dk/connecting-to-neo4j-from-a-nodejs-ap)
[3](https://neo4j.com/docs/javascript-manual/current/)
[4](https://cloudiff.co.uk/blog/posts/building-a-neo4j-powered-api-with-node-js-and-express)
[5](https://github.com/FalkorDB/node-falkordb)
[6](https://docs.falkordb.com)
[7](https://mcp.aibase.com/server/1916341243413766146)
[8](https://docs.falkordb.com/clients.html)
[9](https://docs.falkordb.com/getting-started.html)
[10](https://github.com/FalkorDB/FalkorDB)
[11](https://github.com/OpenSPG/openspg)
[12](https://github.com/openspg)
[13](https://github.com/OpenSPG/KAG)
[14](https://github.com/getzep/graphiti)
[15](https://help.getzep.com/graphiti/getting-started/welcome)
[16](https://help.getzep.com/graphiti/getting-started/overview)
[17](https://www.reddit.com/r/LocalLLaMA/comments/1hft9va/graphiti_temporal_knowledge_graph_with_local_llms/)
[18](https://www.youtube.com/watch?v=5aryMKiBEKY)
[19](https://www.youtube.com/watch?v=snjnJCZhXUM)
[20](https://community.tradovate.com/t/quickly-convert-tradovate-api-docs-into-a-javascript-api/2872)
[21](https://www.reddit.com/r/node/comments/17mm2fk/pretty_open_source_api_documentation_generators/)
[22](https://www.youtube.com/watch?v=KrWBv3JTF18)
[23](https://openapi-generator.tech/docs/generators/javascript/)
[24](https://graphacademy.neo4j.com/courses/app-nodejs/)
[25](https://lobehub.com/mcp/falkordb-falkordb-mcpserver)9

### Minimal Viable Test Setup for Each Solution

Based on the research, here are the detailed setup steps, effort estimates, and what you'd have at the end for each solution:

#### 1. **Graphiti (Zep AI) - BEST FIT**
**Setup Steps:**
1. `git clone https://github.com/getzep/graphiti && cd graphiti`
2. Start Neo4j: `docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest`
3. Set environment variables in `.env`: Neo4j credentials, OpenAI API key
4. `pip install -e .` (installs graphiti-core)
5. Run example: `python examples/quickstart.py` (ingests sample episodes, performs searches)

**Out-of-the-Box Capabilities:**
- ✅ **Ingestion**: `graphiti.add_episode()` function takes raw text/JSON and automatically extracts entities/relationships
- ✅ **Auto-Updates**: Temporal awareness built-in—new episodes automatically resolve against existing entities and update relationships with timestamps
- ✅ **API**: REST endpoints for search (`graphiti.search()`), add episodes, query by time ranges
- ✅ **Vector Search**: Built-in semantic search combining embeddings + graph structure

**Custom Build Required:**
- File monitoring (webhook/file watcher to detect doc changes and trigger `add_episode()`)
- Batch ingestion script for your 1000 Unity docs

**What You'd Have:** A Neo4j graph that auto-deduplicates entities, maintains version history, exposes search APIs, and handles incremental updates. Your LLM can call `search()` and `add_episode()` directly.[1][2][3][4][5]

**Effort Estimate:** 4-6 hours (2 hours setup, 2-4 hours scripting batch ingest + file monitoring)

#### 2. **OpenSPG/KAG - MOST COMPREHENSIVE**
**Setup Steps:**
1. `curl -sSL https://raw.githubusercontent.com/OpenSPG/openspg/refs/heads/master/dev/release/docker-compose-west.yml -o docker-compose.yml`
2. `docker compose -f docker-compose.yml up -d` (starts Neo4j, OpenSPG server, web UI)
3. Navigate to http://127.0.0.1:8887, login (openspg/openspg@kag)
4. Create knowledge base via web UI, configure Neo4j connection and embedding model
5. Install KAG: `pip install -e .` from cloned repo
6. Configure `example_config.yaml` with your LLM API keys (OpenAI compatible)

**Out-of-the-Box Capabilities:**
- ✅ **Ingestion**: Built-in document processors for various formats, automatic entity/relationship extraction
- ✅ **Auto-Updates**: Schema evolution and incremental updates via web UI or API
- ✅ **API**: RESTful APIs for CRUD operations, reasoning queries, vector search
- ✅ **Entity Resolution**: Built-in deduplication and linking algorithms

**Custom Build Required:**
- Scripting to connect your doc repo to KAG's ingestion pipeline
- Custom schema definition for Unity game hierarchy (vision→architecture→design→code)

**What You'd Have:** Full enterprise-grade KG with web UI, reasoning capabilities, automatic schema evolution, and comprehensive APIs. Supports complex logical queries beyond simple vector search.[6][7][8][9][10][11]

**Effort Estimate:** 6-8 hours (3 hours setup/config, 3-5 hours schema design + ingestion scripting)

#### 3. **Neo4j Community + Custom Pipeline - MOST FLEXIBLE**
**Setup Steps:**
1. `docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest`
2. Install Python driver: `pip install neo4j langchain-neo4j sentence-transformers`
3. Create vector index: Connect via browser (localhost:7474), run Cypher: `CREATE VECTOR INDEX doc_embeddings FOR (n:Document) ON n.embedding OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}`
4. Write ingestion script using LangChain's Neo4jGraph connector
5. Set up basic entity resolution with fuzzy matching or embedding similarity

**Out-of-the-Box Capabilities:**
- ✅ **Database**: Robust graph DB with vector search
- ✅ **API**: Bolt protocol, HTTP API, LangChain integration

**Custom Build Required:**
- 🔨 **Ingestion Pipeline**: Full ETL scripts for document parsing, entity extraction, relationship mapping
- 🔨 **Auto-Updates**: Change detection, propagation logic, conflict resolution
- 🔨 **Entity Resolution**: Deduplication algorithms, similarity thresholds
- 🔨 **API Layer**: REST wrapper around Cypher queries

**What You'd Have:** Maximum flexibility but requires building most functionality yourself. Good for custom requirements but significant development overhead.[12][13][14][15][16]

**Effort Estimate:** 12-20 hours (2 hours setup, 10-18 hours building ingestion/update/resolution pipeline)

#### 4. **FalkorDB - AI-OPTIMIZED**
**Setup Steps:**
1. `docker run -p 6379:6379 falkordb/falkordb:latest`
2. Connect via Python: `pip install falkordb-py`
3. Use OpenCypher queries to create schema and ingest data
4. Enable vector search with built-in embedding functions

**Out-of-the-Box Capabilities:**
- ✅ **Ingestion**: Built-in LLM integration for automatic entity extraction
- ✅ **Vector Search**: Native vector operations optimized for AI workloads
- ✅ **API**: OpenCypher + REST APIs

**Custom Build Required:**
- 🔨 **Auto-Updates**: Change propagation logic (though simpler than Neo4j due to AI-first design)
- File monitoring and batch processing scripts

**What You'd Have:** Fast, AI-optimized graph DB with easier LLM integration than Neo4j, but less mature ecosystem.[17][18]

**Effort Estimate:** 5-8 hours (2 hours setup, 3-6 hours custom update logic)

### **Recommendation: Go with Graphiti**

**Why:** It's the only solution that provides true out-of-the-box ingestion AND auto-updates for your scale. The temporal awareness handles "superseding" documents naturally, and the API is designed for LLM integration. OpenSPG/KAG is more comprehensive but overkill for 1000 docs and requires more custom schema work.

**Missing Pieces in Graphiti:** You'll need to build:
- File watcher to detect Unity doc changes and call `add_episode()`
- Batch script to initial-load your existing 1000 docs
- Simple API wrapper if you need custom endpoints beyond the built-in search/add functions

**Total Effort for Production-Ready Solution:** 6-8 hours including monitoring and batch processing.

[1](https://www.youtube.com/watch?v=PxcOIINgiaA)
[2](https://www.youtube.com/watch?v=H2Cb5wbcRzo)
[3](https://help.getzep.com/graphiti/getting-started/welcome)
[4](https://help.getzep.com/graphiti/getting-started/overview)
[5](https://www.reddit.com/r/LocalLLaMA/comments/1hft9va/graphiti_temporal_knowledge_graph_with_local_llms/)
[6](https://gaodalie.substack.com/p/kag-graph-multimodal-rag-llm-agents)
[7](https://thakicloud.github.io/en/tutorials/kag-knowledge-augmented-generation-tutorial/)
[8](https://plainenglish.io/blog/kag-knowledge-augmented-generation-a-pratical-guide-better-than-rag)
[9](https://github.com/OpenSPG/KAG)
[10](https://www.linkedin.com/pulse/openspg-kag-pratices-sharing-can-we-use-franco-lemos-4thhf)
[11](https://atalupadhyay.wordpress.com/2025/01/01/knowledge-augmented-generation-kag-a-deep-dive-with-hands-on-implementation/)
[12](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)
[13](https://neo4j.com/blog/developer/vectors-graphs-better-together/)
[14](https://neo4j.com/blog/developer/advanced-rag-strategies-neo4j/)
[15](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)
[16](https://python.langchain.com/docs/integrations/vectorstores/neo4jvector/)
[17](https://www.falkordb.com/blog/how-to-build-a-knowledge-graph/)
[18](https://www.falkordb.com/blog/how-to-use-knowledge-graph-tools-for-ai/)
[19](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
[20](https://neo4j.com/docs/graph-data-science/current/machine-learning/node-property-prediction/noderegression-pipelines/config/)
[21](https://github.com/getzep/graphiti)
[22](https://github.com/OpenSPG/openspg)
[23](https://neo4j.com/docs/graph-data-science/current/machine-learning/linkprediction-pipelines/config/)

### Understanding Your Concern with Knowledge Graphs

You're spot on in highlighting a common frustration with knowledge graphs (KGs): they're often optimized for ingestion (building from sources like your Unity game docs) and querying (e.g., via semantic search or vector embeddings), but bidirectional editing—where changes in the graph propagate back to sources or handle superseding updates—isn't always seamless or built-in. This "one-way" feel stems from KGs being designed as derived representations of data, not primary sources, so updates require deliberate mechanisms to maintain consistency without breaking relationships or introducing errors. However, it's not impossible; with the right tools and workflows, you can make KGs more dynamic, including propagation of changes using semantic methods. I'll break this down and tie it to your Unity documentation use case.[1][2][3]

### Key Challenges in Editing and Updating Knowledge Graphs

The core issues arise from the graph's interconnected nature, making changes more complex than in a simple database:
- **Cascading Effects and Consistency**: If you update one node (e.g., a design spec in your architecture), it could affect linked entities (like related code snippets or vision goals), potentially creating conflicts or orphans. Without proper handling, this leads to outdated or inconsistent data.[3][4][1]
- **Lack of Native Propagation**: Most KG systems (like Neo4j) don't automatically "push" changes back to original sources or auto-update embeddings; you often need custom scripts or integrations for this, as graphs prioritize read efficiency over write-heavy operations.[2][5][6]
- **Detection of Changes**: Identifying what's "superseded" isn't trivial—semantic search or vectors can help spot similarities, but they don't inherently resolve conflicts (e.g., deciding which version wins) or propagate updates across the graph.[7][1][2]
- **Scalability and Quality**: Frequent updates risk introducing low-quality data (e.g., duplicates or outdated info), especially in dynamic setups like evolving game docs, where manual oversight is often needed to avoid noise.[8][2][3]

These challenges explain why KGs feel one-way, but they're addressable through structured approaches.

### Methods for Editing, Propagation, and Dynamic Updates

While no out-of-the-box "excellent" method exists for every scenario, you can build robust update workflows combining automation, versioning, and semantic tools. Here's how:

- **Versioning for Tracking and Rollbacks**: Treat your KG like code with version control. Tools like Git-adapted systems or ontology versioning track changes to nodes/edges, allowing you to query historical states, compare versions, or rollback. For example, if a design doc supersedes an old architecture node, version it as a new state with metadata (e.g., timestamps, reasons), and use queries to propagate updates to dependent parts of the graph. This prevents loss of history and enables "diffs" for conflicts.[5][9][10][11][7]

- **Automated Pipelines for Change Detection and Propagation**: Set up event-driven systems to monitor source changes (e.g., a doc update) and push them to the KG:
  - Use tools like Apache Kafka or NiFi for real-time ingestion, triggering incremental updates.[1]
  - For propagation, implement rules or ML models to cascade changes: e.g., if a vision goal changes, auto-update linked design nodes via Cypher queries in Neo4j.[12][13][1]
  - Semantic search and vectors can aid detection—embed new/updated docs, compare similarities to existing nodes (using cosine distance), and flag/merge superseding info. Tools like Milvus or Neo4j's vector indexes can automate this, ensuring embeddings are refreshed post-update.[6][2][1]

- **Conflict Resolution and Bidirectional Editing**: To make editing feel two-way:
  - **Manual Oversight with Automation**: Combine bots for initial propagation (e.g., flagging outdated nodes via ML predictions) with human review interfaces (e.g., Neo4j Bloom for visualization).[2][5][1]
  - **Schema-Aware Updates**: Define a meta-schema with rules (e.g., "if X changes, update all Y relations") to semi-autonomously reorganize the graph.[4][6][2]
  - **Full Bidirectionality**: For true two-way flow, integrate with your doc repo (e.g., via APIs to GitHub or a CMS). Changes in the KG could trigger writes back to docs, though this requires custom scripting to avoid loops.[3][12][1]

In practice, communities like Reddit's r/KnowledgeGraph discuss hybrid approaches: update a vector DB (for easy, frequent changes) continuously, while syncing to the KG periodically for structured accuracy. For enterprise tools, ArcGIS or ServiceNow offer managed editing for KGs, including add/update/delete operations with propagation.[13][14][12][2]

### Application to Your Unity Game Documentation Plan

In your setup—building a Neo4j ERKG from hierarchical docs (vision → architecture → design → code)—this means shifting from a static ingest to a maintainable system:
- **Handling Superseding Changes**: If a design doc updates (e.g., new sample code supersedes old), use versioning to mark the old node as "deprecated" and propagate via rules: update embeddings for semantic search, relink to code nodes, and flag affected hierarchy levels. Neo4j supports direct edits (add/update/delete entities/relationships), so you could build a script to auto-propagate based on vector similarity thresholds.[9][12][13][1]
- **Making It Bidirectional**: Extend your plan with a feedback loop—e.g., edit the graph via a UI, then use APIs to push changes back to your doc repo. For vectors, re-embed affected subgraphs after updates to keep searches accurate.[6][1]
- **Practical Steps**: Start with Neo4j's applyEdits for graph-side changes, add Git for versioning, and script detection with Python (using libraries like sentence-transformers for semantic checks). This won't make it perfectly "excellent" out-of-the-box but can get close to automated propagation without major rework.[9][13][2]

If you describe your tech stack (e.g., how docs are stored), I can suggest specific tools or code snippets to implement this.

[1](https://milvus.io/ai-quick-reference/how-do-you-keep-a-knowledge-graph-updated)
[2](https://www.reddit.com/r/KnowledgeGraph/comments/1e81izl/knowledge_graph_continuous_learning/)
[3](https://www.lettria.com/lettria-lab/knowledge-graph-definition)
[4](https://www.sciencedirect.com/science/article/pii/S2352220820300444)
[5](https://enterprise-knowledge.com/how-do-i-update-and-scale-my-knowledge-graph/)
[6](https://dbs.uni-leipzig.de/files/research/publications/2024-8/pdf/information-15-00509-with-cover.pdf)
[7](https://semantic-web-journal.net/content/dynamic-knowledge-graph-evaluation)
[8](https://pmc.ncbi.nlm.nih.gov/articles/PMC10068207/)
[9](https://www.meegle.com/en_us/topics/knowledge-graphs/knowledge-graph-versioning)
[10](https://arxiv.org/html/2409.04499v1)
[11](https://www.sciencedirect.com/science/article/pii/S0098300420305987)
[12](https://enterprise.arcgis.com/en/portal/11.1/use/manage-editing-knowledge-graphs.htm)
[13](https://developers.arcgis.com/javascript/latest/knowledge-graph/apply-edits/)
[14](https://www.servicenow.com/docs/bundle/yokohama-intelligent-experiences/page/administer/knowledge-graph/concept/knowledge-graph-landing.html)
[15](https://arxiv.org/abs/2402.11302)
[16](https://dl.acm.org/doi/10.1145/3580305.3599404)
[17](https://stackoverflow.com/questions/4060645/graphs-and-version-control)
[18](https://github.com/yinboc/DGP)
[19](https://predict-idlab.github.io/ADDKG/)
[20](https://www.sciencedirect.com/science/article/pii/S095070512400306X)