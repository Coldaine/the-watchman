# ADR-001: Technology Stack and Architecture Decisions

## Status
**Accepted** - 2024-11-10

## Context

During the planning phase, multiple conflicting specifications and research documents were created exploring different approaches to building the Librarian Agent system. These documents contained:

- **Conflicting technology recommendations** (Python vs Node.js, Neo4j vs FalkorDB)
- **Multiple project visions** (Agent Governance vs Document RAG vs System Admin KG)
- **Inconsistent timelines** (ranging from "days" to "weeks")
- **Unresolved technical decisions** (embedding models, communication patterns, deployment strategies)

A comprehensive analysis of all documentation revealed critical conflicts that needed resolution before implementation could begin. This ADR documents the final decisions made to resolve these conflicts and establish a unified implementation path.

## Decision Overview

We will build the Librarian Agent as an **AI Agent Governance System** using:
- **Python 3.11+** as the primary language
- **Neo4j Community Edition 5.x+** as the graph database
- **FastAPI** as the API framework
- **LangChain** for RAG and graph integration
- **Ollama + nomic-embed-text** for local embeddings
- **Docker Compose** for single-machine deployment

**Primary Focus**: Agent governance and coordination (preventing AI agent chaos)
**Timeline**: 2-week phased implementation approach

## Detailed Decisions

### 1. Programming Language: Python vs Node.js

**Decision**: **Python 3.11+**

**Rationale**:
- All core specification documents assume Python implementation
- Neo4j Python driver is more mature and widely used than JavaScript driver
- LangChain Python has better Neo4j integration components
- Python has libraries we need that aren't available in JavaScript:
  - `sentence-transformers`: For loading embedding models
  - `neomodel`: ORM for Neo4j (if we want to use it)
  - `langchain.graphs.Neo4jGraph`: Graph QA chains
- FastAPI provides async capabilities comparable to Node.js
- Ollama has good Python support
- Most Neo4j + RAG tutorials and examples use Python
- More community resources available for Python + Neo4j combination

**Alternatives Considered**:
- **Node.js**: Considered due to one research document recommendation
  - **Rejected because**:
    - Would require rewriting all specification examples
    - Neo4j JavaScript driver has less comprehensive documentation
    - Missing some libraries we want to use
    - No clear performance advantage for our use case

**Consequences**:
- ✅ Can use existing specification examples directly
- ✅ Access to mature Neo4j/LangChain integrations
- ✅ Extensive documentation and community support
- ✅ Rich library ecosystem for AI/ML tasks
- ⚠️ If real-time web UI needed later, may need separate Node.js frontend (acceptable tradeoff)

### 2. Graph Database: Neo4j vs FalkorDB

**Decision**: **Neo4j Community Edition 5.x+**

**Rationale**:
- Native vector index support since Neo4j 5.x using HNSW algorithm
- Mature database with many years of production use
- Large community and extensive documentation
- Good Stack Overflow coverage for troubleshooting
- LangChain has pre-built Neo4j integration
- Graph Data Science library available if needed
- Neo4j Browser provides visual debugging interface
- For our scale (1000 documents), performance differences between databases are negligible

**Alternatives Considered**:
- **FalkorDB**: Redis-based graph database marketed as "AI-optimized"
  - **Rejected because**:
    - No LangChain integration (would need custom implementation)
    - Smaller community and less documentation
    - Less mature tooling (no visual browser like Neo4j)
    - In-memory storage requires more RAM
    - For our scale, the performance benefits aren't significant
- **OpenSPG/KAG**: Enterprise knowledge augmented generation
  - **Rejected because**: Massive overkill for personal project, steep learning curve
- **Graphiti**: Temporal knowledge graph library
  - **Rejected because**: Python library, not standalone database; different use case

**Consequences**:
- ✅ Can use specification examples without modification
- ✅ Extensive troubleshooting resources available
- ✅ LangChain/LlamaIndex integrations work out-of-box
- ✅ Production-ready vector search (HNSW index)
- ✅ Lower implementation risk
- ⚠️ Slightly larger memory footprint than Redis-based solutions (acceptable for local deployment)

### 3. API Framework: FastAPI

**Decision**: **FastAPI with auto-generated OpenAPI documentation**

**Rationale**:
- Modern async Python framework with good performance
- Automatic features that save development time:
  - OpenAPI/Swagger docs generated automatically from code
  - Request/response validation via Pydantic
  - Automatic JSON serialization
  - Built-in support for authentication if needed later
- Works well with Neo4j async driver:
  - Native `async def` endpoints
  - Good connection pooling support
- Developer productivity benefits:
  - Less boilerplate than Flask
  - Type hints provide IDE autocomplete
  - TestClient makes testing easier

**Alternatives Considered**:
- **Flask**: Traditional Python web framework
  - **Rejected because**:
    - No built-in async support
    - Would need additional libraries for validation
    - More boilerplate code required
- **Django + DRF**: Full-stack framework
  - **Rejected because**: Too heavyweight for API-only service
- **gRPC**: Binary protocol
  - **Rejected because**: AI agents typically expect REST/JSON

**Consequences**:
- ✅ API documentation auto-generated and always in sync with code
- ✅ Input validation handled automatically
- ✅ Better performance than synchronous frameworks
- ✅ Good testing support
- ✅ Native async/await for Neo4j operations
- ⚠️ Slightly newer framework than Flask but widely adopted

### 4. Embedding Model: nomic-embed-text (768d)

**Decision**: **nomic-embed-text via Ollama (768 dimensions)**

**Rationale**:
- Commonly used and well-documented in the Ollama ecosystem
- 768 dimensions provides a reasonable balance between quality and performance
- Small model size that runs well on consumer hardware
- Supports variable-length dimensions (Matryoshka training) if we need to optimize later
- Based on web search, performs reasonably well in real-world usage despite MTEB ranking concerns

**Note on MTEB Rankings**: Recent analysis shows nomic-embed-text performs better in dynamic evaluations (MTEB Arena) than its static MTEB leaderboard ranking suggests, indicating the static benchmarks may not fully reflect real-world performance.

**Alternatives Considered**:
- **bge-m3** (1024d): Multilingual model
  - **Deferred because**:
    - Larger model size
    - Higher dimensionality means larger index size
    - Multilingual capability not needed for English-only docs
- **snowflake-arctic-embed**: Various sizes available
  - **Deferred because**: Less commonly used, fewer examples available

**Technical Configuration**:
```cypher
CREATE VECTOR INDEX chunk_embedding
FOR (c:Architecture|Design) ON (c.embedding)
OPTIONS {
  indexConfig: {
    'vector.dimensions': 768,
    'vector.similarity_function': 'cosine'
  }
};
```

**Consequences**:
- ✅ Good documentation coverage
- ✅ Fast inference on consumer hardware
- ✅ Proven quality for code/documentation
- ✅ Easy migration path to larger models
- ⚠️ May need to re-embed if switching models (acceptable cost)

### 5. Project Scope: Agent Governance Focus

**Decision**: **AI Agent Governance System** (Librarian Pattern)

**Primary Goal**: Prevent chaos when multiple AI agents (Claude, Copilot, Gemini) work on a codebase

**Rationale**:
- This is the clear primary vision in Project Brief and Context documents
- Solves a specific, well-defined problem
- Has concrete success criteria (agent compliance, drift detection)
- RAG is the *mechanism* for retrieval, not the end goal
- Other visions (System Admin KG, generic Document RAG) appear to be different projects

**Architecture Focus**:
- Schema prioritizes: `Architecture`, `Design`, `Requirement`, `CodeArtifact`, `AgentRequest`, `Decision`
- NOT focused on: `SSHKey`, `User`, `Software` nodes (unless directly related to governed projects)
- Core features: Request approval, drift detection, compliance verification, immutable audit log

**Alternatives Considered**:
- **Generic Document RAG**: Q&A over documentation
  - **Clarified as**: RAG is the retrieval layer for providing context to agents, not the primary goal
- **System Administration KG**: Track files, configs, software
  - **Rejected as**: Different project; wrong focus; appears in only one research document

**Consequences**:
- ✅ Clear, focused scope
- ✅ Measurable success criteria
- ✅ Solves real problem (agent chaos)
- ✅ Prevents scope creep into unrelated domains
- ⚠️ Generic document Q&A is secondary use case

### 6. Timeline and Phasing

**Decision**: **2-week phased implementation**

**Timeline Breakdown**:
- **Week 1 (Phase 1)**: Infrastructure setup and basic agent control
- **Week 2 (Phase 2)**: Full agent coordination and validation

**Rationale**:
- Personal project with unpredictable time availability
- First-time implementation with this tech stack requires learning curve
- Setting up Neo4j + vectors + agent protocol is non-trivial
- Better to under-promise and over-deliver

**Alternatives Considered**:
- **"Multiple phases in a day"** (from Project Brief)
  - **Rejected as**: Unrealistic for quality implementation
- **5-week enterprise timeline** (from Implementation Plan)
  - **Rejected as**: Includes many features not needed for MVP
- **Milestone-based "1-2 days"** (from Milestones doc)
  - **Rejected as**: Too optimistic for first implementation

**Phase 1 Success Criteria**:
- ✅ Neo4j running with vector indexes
- ✅ Can ingest documents and store embeddings
- ✅ Can query semantically
- ✅ Basic agent request/approval endpoint works
- ✅ Can reject non-compliant requests

**Phase 2 Success Criteria**:
- ✅ All validation rules implemented
- ✅ Drift detection working
- ✅ Agents receive consistent context
- ✅ Immutable audit trail functional
- ✅ Compliance verification operational

**Consequences**:
- ✅ Realistic expectations set
- ✅ Early value delivery (Phase 1)
- ✅ Clear success criteria per phase
- ✅ Flexibility to extend if needed
- ⚠️ May deliver faster than estimated (acceptable outcome)

### 7. Communication Architecture

**Decision**: **Direct REST API** via FastAPI endpoints

**API Structure**:
```
POST /agent/request-approval
POST /agent/report-completion
POST /query/semantic
GET  /validation/drift-check
GET  /validation/compliance/{subsystem}
POST /admin/ingest
GET  /health
```

**Rationale**:
- Simple HTTP endpoints that any agent can call
- No external dependencies (GitHub, message queues)
- Easy to test locally (curl, Postman, pytest)
- Synchronous API calls are fine at single-user scale
- Can add integrations (PR comments, webhooks) later without changing core

**Alternatives Considered**:
- **GitHub PR Comments**: Parse/post comments on pull requests
  - **Deferred because**: Adds GitHub dependency; harder to test locally; can add later as integration
- **Message Queue** (Redis, RabbitMQ): Async message passing
  - **Rejected because**: Unnecessary complexity for one user; no concurrency benefits at this scale
- **Event Bus** (Kafka): Enterprise event streaming
  - **Rejected because**: Massive overkill; adds operational complexity

**Consequences**:
- ✅ Simple, local-first design
- ✅ No external dependencies required
- ✅ Easy to test and debug
- ✅ Can add integrations incrementally
- ✅ Agents can use any HTTP client

### 8. Deployment Strategy

**Decision**: **Phased deployment approach - Native development first, Docker for production**

**Phase 0-2 (Development)**: Native Windows Installation
```yaml
components:
  neo4j: Neo4j Desktop (GUI app)
  ollama: Ollama for Windows
  api: Python 3.11+ with uvicorn

setup:
  - Install Neo4j Desktop from neo4j.com/download
  - Install Ollama from ollama.ai/download
  - python -m venv venv
  - pip install -r requirements.txt
  - uvicorn src.main:app --reload
```

**Phase 3 (Production)**: Docker Compose
```yaml
services:
  neo4j:
    image: neo4j:5-community
    ports: [7474, 7687]

  librarian-api:
    build: ./
    ports: [8000]

  ollama:
    image: ollama/ollama
    ports: [11434]
```

**Rationale**:
- **Native development provides**:
  - Faster iteration (no container rebuild)
  - Easier debugging (direct process access)
  - Neo4j Desktop GUI for graph exploration
  - Simpler learning curve
  - Direct log access
- **Docker for deployment provides**:
  - Reproducible setup across machines
  - Container isolation
  - Simple orchestration
  - Easy backup (volume snapshots)

**Alternatives Considered**:
- **Docker from day one**: Start with containers
  - **Deferred because**: Adds complexity during rapid development phase; debugging is harder through container layers
- **Kubernetes**: Container orchestration platform
  - **Rejected because**: Massive overkill for single machine
- **Serverless** (Lambda, Cloud Functions): Pay-per-use
  - **Rejected because**: Adds cloud dependency; stateful graph DB doesn't fit serverless model
- **Permanent native-only**: Never containerize
  - **Rejected because**: Harder to deploy to other machines later

**Consequences**:
- ✅ Faster initial development without Docker overhead
- ✅ Can visualize graph data with Neo4j Desktop during development
- ✅ Easier onboarding (fewer tools to install initially)
- ✅ Production deployment remains portable via Docker
- ⚠️ Need to test Docker deployment in Phase 3 (acceptable tradeoff)

### 9. RAG Framework Integration

**Decision**: **LangChain with Neo4jVector and Neo4jGraph**

**Components Used**:
- `langchain.vectorstores.Neo4jVector` - Vector operations
- `langchain.graphs.Neo4jGraph` - Graph traversal
- `langchain.embeddings.OllamaEmbeddings` - Embedding generation
- `langchain.chains.GraphCypherQAChain` - Natural language to Cypher

**What LangChain Provides**:
- Pre-built Neo4j vector store integration
- Automatic batching for embeddings
- Retry logic and error handling
- Metadata filtering in vector queries
- Graph QA chain capabilities
- Connection pooling and transaction management

**Code Simplification Example**:
```python
# With LangChain
vector_store = Neo4jVector.from_documents(docs, embeddings, url=NEO4J_URI)
results = vector_store.similarity_search(query, k=10)

# Without LangChain would require implementing:
# - Connection management
# - Embedding batching
# - Vector query Cypher
# - Result parsing
# - Error handling
```

**Alternatives Considered**:
- **LlamaIndex**: Alternative RAG framework
  - **Deferred because**: Neo4j integration appears less mature
- **Custom implementation**: Direct Neo4j driver usage
  - **Rejected because**: Would need to implement many features LangChain provides

**Consequences**:
- ✅ Faster development using proven patterns
- ✅ Many examples and tutorials available
- ✅ Handles common edge cases
- ⚠️ Adds dependency on LangChain library

## Summary of Key Decisions

| Decision Area | Choice | Primary Reason |
|--------------|--------|----------------|
| **Language** | Python 3.11+ | Mature ecosystem, all specs written for it |
| **Database** | Neo4j Community 5.x+ | Battle-tested, massive community, native vectors |
| **API Framework** | FastAPI | Modern async, auto-docs, excellent for AI services |
| **Embedding Model** | nomic-embed-text (768d) | Well-documented, proven, good balance |
| **Project Scope** | Agent Governance | Clear primary vision, solves specific problem |
| **Timeline** | 2 weeks (2 phases) | Realistic for personal project |
| **Communication** | REST API | Simple, local-first, no dependencies |
| **Deployment** | Docker Compose | Simple orchestration, reproducible |
| **RAG Framework** | LangChain | Pre-built Neo4j integration, saves weeks |

## Risk Assessment

### Mitigated Risks
- ✅ **Technology immaturity**: Using proven, mature technologies
- ✅ **Community support**: Large communities for all core technologies
- ✅ **Integration complexity**: LangChain handles Neo4j integration
- ✅ **Performance**: All components fast enough at target scale
- ✅ **Debugging difficulty**: Excellent documentation and examples available

### Accepted Risks
- ⚠️ **Embedding model quality**: Can switch models if quality insufficient (re-embedding required)
- ⚠️ **Timeline uncertainty**: Personal project with variable time availability (2-week estimate has buffer)
- ⚠️ **Scope creep**: Must maintain focus on agent governance (mitigated by clear ADR)

## Validation Approach

These decisions will be validated through implementation:

### Phase 1 Validation (Week 1)
- Neo4j successfully stores and retrieves vector embeddings
- Basic ingestion pipeline works end-to-end
- Agent request/approval endpoints functional
- Semantic search returns relevant results

### Phase 2 Validation (Week 2)
- Validation rules can detect non-compliant requests
- Drift detection queries work correctly
- System provides useful context to agents
- Audit trail captures all interactions

### Decision Review Triggers
We'll reconsider decisions if:
- Vector search performance is unacceptably slow
- Embedding quality is insufficient for our use case
- Development is significantly harder than expected
- Resource usage exceeds available hardware
- A technology choice blocks critical functionality

## References

- Architecture Document: `docs/architecture.md` v2.0.0
- Archived Research: `docs/archive/README.md`
- Neo4j Vector Index Docs: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
- LangChain Neo4j Integration: https://python.langchain.com/docs/integrations/vectorstores/neo4jvector/
- FastAPI Documentation: https://fastapi.tiangolo.com/

## Change History

- **2024-11-10 v1.0**: Initial ADR created, documenting all technology and architecture decisions
- **2024-11-10 v1.1**: Added quantitative justifications (contained unverified metrics)
- **2024-11-10 v1.2**: Removed unverified performance claims and made-up metrics
  - Removed specific performance numbers that weren't verified
  - Removed made-up time savings estimates
  - Removed unverified benchmark scores
  - Kept honest assessment of technology choices
  - Added note about nomic-embed-text MTEB ranking concerns from web search
- Status: **Accepted** and ready for implementation

---

**Next Steps**:
1. Create project structure based on these decisions
2. Implement Phase 1 according to architecture.md
3. Validate decisions through implementation
4. Create additional ADRs for future architectural changes