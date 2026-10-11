# Research_Decisions.md

## Pending Technical Decisions

These are the key technical choices we need to make for our MVP implementation.

### Database Technology Selection

For our graph database with vector search capabilities, we have several options to consider. See detailed analysis in [[LLM/KnowledgeAgents/Project_Library_Agent/research/neo4j_vs_falkordb_comparison]] for a comparison of Node.js-focused solutions.

**Options to evaluate:**
- Neo4j Community Edition with vector index
- FalkorDB with AI optimization
- OpenSPG/KAG for comprehensive KG features
- Graphiti for temporal knowledge graphs

**Decision criteria:**
- Native Node.js support and integration
- Vector search capabilities
- Ease of setup and deployment
- Community support and documentation
- Performance for our use case

**Action:** Evaluate Neo4j and FalkorDB first, as they have the best Node.js support.

### 1. Embedding Model Selection

**Options to evaluate:**
- `nomic-embed-text` (recommended in original plan)
- `all-minilm` series from SentenceTransformers
- `bge-m3` for multilingual support
- `snowflake-arctic-embed` for newer architecture

**Decision criteria:**
- Local inference speed
- Embedding dimensionality (affects Neo4j vector index)
- Quality for code/document similarity
- Model size (disk/RAM usage)

**Action:** Test 2-3 models with sample code/documentation

### 2. Chunking Strategy

**Parameters to decide:**
- Chunk size (512, 768, 1024 tokens?)
- Overlap strategy (10%, fixed tokens, sentence boundary?)
- Chunking per document type (code vs. markdown vs. specs)

**Action:** Experiment with different strategies on sample documents

### 3. Retrieval Algorithm

**Hybrid approaches to consider:**
- Pure vector similarity
- Vector + lexical (BM25) re-ranking
- Graph-enhanced retrieval (using Neo4j relationships)

**Action:** Start with pure vector, add complexity later

### 4. LLM Integration

**Options:**
- Local Ollama models (Llama3, Mistral, Gemma)
- Cloud APIs (OpenRouter, OpenAI) for comparison
- Different models for different tasks?

**Action:** Start with one local model, add cloud option as backup

### 5. Code Parsing Strategy

**How to parse different file types:**
- Python: `ast` module or tree-sitter
- JavaScript/TypeScript: tree-sitter or esprima
- Markdown: markdown-it or similar
- Configuration files: appropriate parsers

**Action:** Focus on Python first, add others incrementally

### 6. Graph Schema Refinements

**Current minimal schema:**
- `:Doc {id, title, source}`
- `:Chunk {id, text, embedding: Vector<Float>, docId}`

**Potential additions:**
- File type, programming language
- Creation/modification dates
- Author information
- Tags/categories

**Action:** Start minimal, add as needed for features

### 7. Frontend Interface (if any)

**UI approaches:**
- Command line only (simplest)
- Simple web UI with FastAPI templates
- Streamlit/Gradio for rapid prototyping
- Jupyter notebook interface

**Action:** CLI first, add UI when core is working

### 8. Document Processing Pipeline

**Ingestion steps:**
1. File discovery (recursive directory walk)
2. File type detection
3. Content extraction
4. Metadata extraction
5. Chunking
6. Embedding
7. Database insertion

**Action:** Build incrementally, test each step

### 9. Query Processing Pipeline

**Query steps:**
1. Query embedding
2. Vector search
3. Result ranking/re-scoring
4. Context assembly
5. LLM response generation
6. Result formatting

**Action:** Start with basic vector search, enhance progressively

### 10. Development Tooling

**Project structure decisions:**
- Virtual environment setup (venv, conda, poetry?)
- Dependency management approach
- Testing strategy (unit, integration, end-to-end?)
- Development workflow tools

**Action:** Keep it simple - venv + requirements.txt to start