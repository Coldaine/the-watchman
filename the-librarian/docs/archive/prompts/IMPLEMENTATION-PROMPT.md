# Implementation Prompt for Librarian Agent MVP

## What You're Building

The **Librarian Agent** is an AI agent governance system that acts as a gatekeeper for all AI agents (Claude, Copilot, etc.) working on a codebase. It prevents chaos by validating agent requests against specifications before allowing changes.

**Core Concept**: When an AI agent wants to modify code or documentation, it must first ask the Librarian for approval. The Librarian checks if the request follows standards and approves/rejects it.

## Priority: Build an MVP in 90 Minutes

**Focus on ONE working flow**: Agent requests approval → Librarian validates → Returns approved/rejected

## Technology Stack (Already Decided)

- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **Database**: Neo4j (MOCK IT for MVP)
- **Models**: Pydantic
- **Embeddings**: Ollama (SKIP for MVP)
- **Environment**: Windows (native, no Docker)

## What to Build (IN THIS ORDER)

### 1. Core Data Models (`src/models/`)

Create Pydantic models based on `docs/architecture.md` (lines 150-210):

```python
# src/models/base.py
- Enums: Status, ActionType, RequestType, TargetType
- Base configuration classes

# src/models/documents.py
- Document(BaseModel): path, content, doc_type, frontmatter
- ParsedDocument: Adds metadata parsing

# src/models/agents.py
- AgentRequest: agent_id, action, target_type, content, rationale
- AgentResponse: status (approved/rejected/escalated), feedback, assigned_location
- Decision: id, rationale, kind, impact
```

### 2. Validation Engine (`src/validation/`)

Based on `docs/subdomains/validation-engine.md`:

```python
# src/validation/engine.py
class ValidationEngine:
    def validate_request(self, request: AgentRequest) -> ValidationResult:
        # Check these rules (just implement basic checks):
        # 1. Has required frontmatter fields?
        # 2. Has rationale?
        # 3. References valid specs?
        # Return ValidationResult(status="approved"/"rejected", reasons=[])
```

**MOCK the database** - just return hardcoded responses for now.

### 3. FastAPI Server (`src/`)

Based on `docs/architecture.md` (lines 264-364):

```python
# src/main.py
app = FastAPI(title="Librarian Agent")

# src/api/agent.py
@app.post("/agent/request-approval")
async def request_approval(request: AgentRequest) -> AgentResponse:
    # Use ValidationEngine
    # Return approval/rejection

@app.post("/agent/report-completion")
async def report_completion(request: CompletionReport) -> dict:
    # Just acknowledge for MVP

# src/api/health.py
@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "neo4j": "mocked", "version": "0.1.0"}
```

### 4. Configuration (`src/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"  # Not used in MVP
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
```

### 5. Requirements & Setup Files

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
# neo4j-driver==5.14.0  # Skip for MVP
# langchain==0.1.0  # Skip for MVP
# ollama==0.1.0  # Skip for MVP
```

```bash
# .env.template
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here
LOG_LEVEL=INFO
```

### 6. Basic Test

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_agent_request():
    request = {
        "agent_id": "test-claude",
        "action": "create",
        "target_type": "design",
        "content": "# Test Design\nContent here",
        "rationale": "Testing the system"
    }
    response = client.post("/agent/request-approval", json=request)
    assert response.status_code == 200
    assert response.json()["status"] in ["approved", "rejected", "escalated"]
```

### 7. README.md

```markdown
# Librarian Agent MVP

## What Works
- ✅ Agent approval endpoint
- ✅ Basic validation rules
- ✅ Health check

## What's Mocked
- ❌ Neo4j database (using in-memory dict)
- ❌ Embeddings (not implemented)
- ❌ Semantic search (not implemented)

## Running
\`\`\`bash
pip install -r requirements.txt
uvicorn src.main:app --reload
\`\`\`

## Test
\`\`\`bash
curl -X POST http://localhost:8000/agent/request-approval \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test", "action": "create", "target_type": "design", "content": "test", "rationale": "test"}'
\`\`\`

## Next Steps
1. Connect real Neo4j
2. Add embedding generation
3. Implement semantic search
```

## Success Criteria

1. **Server starts**: `uvicorn src.main:app --reload` runs without errors
2. **Health check works**: `GET /health` returns 200
3. **Agent endpoint works**: `POST /agent/request-approval` returns valid response
4. **Validation runs**: At least one validation rule is checked

## What to SKIP (Not needed for MVP)

- ❌ Neo4j connection (mock it)
- ❌ Embeddings/Ollama (skip entirely)
- ❌ Semantic search (not needed)
- ❌ File monitoring (Phase 3)
- ❌ Complex validation rules (just basic checks)
- ❌ Authentication (not needed yet)
- ❌ Docker (use native Python)

## Tools/Access Needed

The agent implementing this needs:
- **File creation**: Write Python files to `src/` directory
- **Read access**: Read documentation in `docs/` directory
- **Command execution**: Run `pip install` and `uvicorn`
- **Testing**: Run `pytest` or `python -m pytest`

## Key Documentation References

1. **Architecture**: `docs/architecture.md` (lines 150-500 most relevant)
2. **Validation Rules**: `docs/subdomains/validation-engine.md`
3. **Agent Protocol**: `docs/subdomains/agent-protocol.md`
4. **Technology Stack**: `docs/ADR/001-technology-stack-and-architecture-decisions.md`

## Order of Implementation

1. Create directory structure
2. Write models (no external dependencies)
3. Write validation engine (uses models)
4. Write API endpoints (uses validation)
5. Create requirements.txt and .env.template
6. Test that server starts
7. Write basic tests
8. Create README

## Expected File Structure

```
the-Librarian/
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── config.py         # Settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py       # Base classes
│   │   ├── documents.py  # Document models
│   │   └── agents.py     # Agent models
│   ├── validation/
│   │   ├── __init__.py
│   │   └── engine.py     # Validation logic
│   └── api/
│       ├── __init__.py
│       ├── agent.py      # Agent endpoints
│       └── health.py     # Health check
├── tests/
│   ├── __init__.py
│   └── test_api.py       # Basic tests
├── requirements.txt
├── .env.template
└── README.md
```

## Time Estimate

- Models: 15 minutes
- Validation: 15 minutes
- API: 20 minutes
- Testing/debugging: 20 minutes
- Documentation: 10 minutes
- Buffer: 10 minutes

**Total: 90 minutes**

## Final Note

**Goal**: Get a working API server that can receive agent requests and return approval/rejection based on simple validation rules. Everything else can be added later. Focus on the core flow working end-to-end.