# Spec_System_Architecture.md

## The 8 Pillars of Librarian Agent Governance

1. **Centralized Authority** - All AI agents must route documentation and code changes through the Librarian
2. **Immutable Records** - Every change is permanently logged with full audit trail
3. **Standardized Documentation** - All documents follow enforced templates and locations
4. **Contextual Intelligence** - Agents receive authoritative project context for decisions
5. **Behavioral Control** - Unauthorized changes are detected and prevented automatically
6. **Documentation Authority** - Official documentation is the single source of truth for all implementation
7. **Drift Detection** - Mismatches between code and documentation identify either incomplete work or errors
8. **Compliance Verification** - Requirements can be traced and verified against actual implementation

## Pillar Implementation Strategies

### Centralized Authority + Behavioral Control + Immutable Records
**Implementation:** File system permissions will restrict direct access to documentation and critical code areas. Only humans and the Librarian service will have write permissions. Agents must interact through the Librarian API for all changes. All interactions are logged to an append-only database with timestamps, agent IDs, and rationales. File system monitoring and periodic audits will detect unauthorized changes. Git hooks and pre-commit filters will prevent direct commits to protected branches. Logs will be stored in a separate, highly-permissioned location to prevent tampering.

*Development Consideration: We need to review this permission model to ensure it doesn't hinder Librarian development. We may need a development mode that allows easier iteration while maintaining security for actual agent interactions.*

### Standardized Documentation + Documentation Authority + Contextual Intelligence
**Implementation:** The Librarian will enforce documentation templates through validation APIs. Agents requesting to create or modify documents must use approved formats. Templates will be versioned and centrally managed in a protected repository. Official documentation serves as the single source of truth for all agent tasks. The Librarian maintains a graph database linking requirements, design documents, code artifacts, and implementation details. Agents query this graph to receive relevant context for their tasks. All documentation updates require explicit approval workflows, ensuring only authoritative versions are used for context.

### Drift Detection + Compliance Verification + Behavioral Control
**Implementation:** Automated monitoring agents will periodically scan the codebase and compare it against documentation. Scheduled tasks will run compliance checks, while parallel monitoring agents watch for changes in real-time. Discrepancies between code and documentation trigger immediate verification processes. Traceability matrices link requirements to design documents to code implementations. Automated verification tools check that implemented features match documented specifications. When mismatches are detected, the system can either block further changes or require explicit review and approval before proceeding. This creates a feedback loop where drift is not just detected but actively prevented.

### Immutable Records + Compliance Verification + Documentation Authority
**Implementation:** All changes are logged with complete audit trails that include the relationship between requirements, design decisions, and implementation. The append-only logging system ensures that the evolution of documentation and code can be traced over time. Compliance verification processes can reference historical records to understand why certain decisions were made. When reviewers question implementation against requirements, they can trace the complete history of both the requirement and the implementation. Official documentation versions are cryptographically signed to prevent tampering, and all changes require approval with recorded rationale.

## System Architecture

### Core Architecture (Agent Coordination Focus)

The Librarian acts as the central authority for all AI agent interactions:

```
┌─────────────────────────────────────────────────────┐
│              SPECIFICATION LAYER                    │
│  ┌──────────────────────────────────────────────┐   │
│  │  • Architecture Docs    • Design Specs       │   │
│  │  • API Contracts        • Constitution Rules │   │
│  │  • Decision Log         • Task Backlogs      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │  LIBRARIAN  │
                    │    AGENT    │
                    └─────┬──────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
   │ AGENT 1 │      │ AGENT 2 │      │ AGENT 3 │
   │ Claude  │      │ Copilot │      │ Gemini  │
   └─────────┘      └─────────┘      └─────────┘
                          │
                    ┌─────▼──────┐
                    │  CODEBASE  │
                    │            │
                    └────────────┘
```

### Communication Architecture (Agent Control)

All agent communication must go through the Librarian:

| Channel | Purpose | Security |
|---------|---------|----------|
| **Structured API** | Agent requests for documentation changes | High - All requests validated |
| **Standardized Formats** | All documentation follows templates | High - Enforced by Librarian |
| **Immutable Logging** | All interactions recorded permanently | High - Audit trail maintained |

### Librarian Deployment Model (Personal Project)

For this personal project controlling AI agents:

| Option | Control | Best For |
|--------|---------|----------|
| **Local Service** | Full | Personal agent control |
| **File-based Storage** | High | Immutable documentation |
| **Simple Authentication** | Basic | Agent identification |

The Librarian runs locally as the sole authority, with all agents required to request permissions before making changes.

### Ingestion Pipeline

The ingestion pipeline processes documents and code to maintain the graph and vector databases:

```python
class IngestionPipeline:
    def __init__(self, graph_db, vector_db):
        self.graph = graph_db
        self.vector = vector_db
        self.parsers = {
            'architecture': ArchitectureParser(),
            'design': DesignParser(),
            'research': ResearchParser(),
            # ... other parsers
        }
    
    def ingest_document(self, file_path: str):
        """Process a document through the full ingestion pipeline"""
        
        # 1. Parse front-matter
        metadata = self._parse_frontmatter(file_path)
        doc_type = metadata['doc']
        
        # 2. Create/update graph node
        node = self._upsert_graph_node(metadata)
        
        # 3. Extract sections and requirements
        if doc_type == 'architecture':
            requirements = self._extract_requirements(file_path)
            self._create_requirement_nodes(node, requirements)
        
        # 4. Chunk and embed content
        chunks = self._chunk_document(file_path)
        for chunk in chunks:
            embedding = self.vector.embed(chunk.text)
            self.vector.upsert({
                'id': chunk.id,
                'embedding': embedding,
                'metadata': {**metadata, **chunk.metadata}
            })
        
        # 5. Process cross-references
        refs = self._extract_references(file_path)
        self._create_relationships(node, refs)
    
    def ingest_code(self, file_path: str):
        """Extract and link code artifacts"""
        
        # Look for design references in comments
        refs = self._extract_code_refs(file_path)
        
        # Create CodeArtifact node
        artifact = CodeArtifact(
            path=file_path,
            lang=self._detect_language(file_path),
            repo_rel_path=self._relative_path(file_path)
        )
        
        # Link to referenced designs/requirements
        for ref in refs:
            self.graph.create_relationship(
                artifact, "IMPLEMENTS", ref
            )
```

### Phase 1 Implementation Details

#### Goals
- Neo4j running locally with **native vector index**.
- Minimal graph schema for `Doc`/`Chunk` and embeddings stored **in Neo4j**.
- **FastAPI** service with two endpoints:
    - `POST /ingest` (load → chunk → embed via Ollama → upsert to Neo4j)
    - `POST /ask` (embed query → vector search in Neo4j → optional LLM answer)
- Optional GraphQL (Python) for structured access, but keep it lean.

For database technology selection research, see [[LLM/KnowledgeAgents/Project_Library_Agent/research/neo4j_vs_falkordb_comparison]].

#### Step-by-step
1.  **Repo scaffold:** `neo4j-rag-python/` with `app/`, `data/`, `.env`, and `requirements.txt`.
2.  **Run Neo4j (Docker) & connect from Python.**
3.  **Define minimal graph schema + vector index** for `:Doc` and `:Chunk` nodes.
4.  **Choose local embeddings model** (e.g., `nomic-embed-text` via Ollama).
5.  **Implement Ingestion (`POST /ingest`):** Load files, split into chunks, embed, and upsert to Neo4j.
6.  **Implement Retrieval (`POST /ask`):** Embed query, perform vector search in Neo4j, assemble context, and optionally send to an LLM for a final answer.
7.  **Smoke tests (pytest):** Verify connectivity, ingestion, and retrieval.