# Fix Agent 3: FastAPI Implementation

## Priority: HIGH - Build the API Layer

## Your Mission
Implement the complete FastAPI server with all endpoints from the architecture specification.

## Required Implementation

### 1. Main Application (`src/main.py`)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api import agent, query, validation, admin, health
from src.integration.orchestrator import LibrarianOrchestrator

app = FastAPI(
    title="Librarian Agent API",
    description="AI Agent Governance System",
    version="0.1.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(validation.router, prefix="/validation", tags=["Validation"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(health.router, tags=["Health"])

@app.on_event("startup")
async def startup_event():
    # Initialize connections
    # Verify Neo4j
    # Check Ollama
```

### 2. Agent Endpoints (`src/api/agent.py`)

```python
from fastapi import APIRouter, HTTPException
from src.validation.agent_models import AgentRequest, AgentResponse

router = APIRouter()

@router.post("/request-approval", response_model=AgentResponse)
async def request_approval(request: AgentRequest):
    """
    Main endpoint: Agent requests approval for action
    From docs/architecture.md lines 274-285
    """
    # Validate request
    # Check against specifications
    # Return approval/rejection with location

@router.post("/report-completion")
async def report_completion(request_id: str, completed: bool, changes: List[str]):
    """
    Agent reports completion of approved task
    From docs/architecture.md lines 287-302
    """
    # Update audit trail
    # Verify changes
    # Return acknowledgment
```

### 3. Query Endpoints (`src/api/query.py`)

```python
from fastapi import APIRouter, Query

router = APIRouter()

@router.post("/semantic")
async def semantic_search(
    query: str,
    context_type: str = "all",
    limit: int = 10
):
    """
    Semantic search across documents
    From docs/architecture.md lines 305-319
    """
    # Generate embedding for query
    # Search vector index
    # Return ranked results

@router.get("/cypher")
async def cypher_query(q: str = Query(..., description="Cypher query")):
    """
    Direct Cypher query execution (admin only)
    From docs/architecture.md lines 321-327
    """
    # Validate query (read-only)
    # Execute
    # Return results
```

### 4. Validation Endpoints (`src/api/validation.py`)

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/drift-check")
async def drift_check():
    """
    Check for drift between code and docs
    From docs/architecture.md lines 330-340
    """
    # Run all drift queries
    # Return violations

@router.get("/compliance/{subsystem}")
async def compliance_check(subsystem: str):
    """
    Check compliance for subsystem
    From docs/architecture.md lines 342-349
    """
    # Calculate compliance rate
    # Find violations
    # Return report
```

### 5. Admin Endpoints (`src/api/admin.py`)

```python
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    document_type: str = "auto"
):
    """
    Ingest new document into system
    From docs/architecture.md lines 352-361
    """
    # Process document
    # Store in graph
    # Return node ID

@router.get("/metrics")
async def get_metrics():
    """System metrics and statistics"""
    # Node counts
    # Processing stats
    # Performance metrics
```

### 6. Health Check (`src/api/health.py`)

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    System health check
    From docs/architecture.md lines 363-370
    """
    return {
        "status": "healthy",
        "checks": {
            "neo4j": await check_neo4j(),
            "ollama": await check_ollama(),
            "disk": check_disk_space()
        },
        "version": "0.1.0"
    }
```

### 7. WebSocket Support (`src/api/websocket.py`)

```python
from fastapi import WebSocket

@app.websocket("/ws/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """Real-time agent communication"""
    await websocket.accept()
    # Handle bidirectional communication
```

## Configuration

Update `.env`:
```
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
API_RELOAD=true
LOG_LEVEL=INFO
```

## Testing

Create `tests/test_api.py`:
```python
from fastapi.testclient import TestClient

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_agent_request():
    response = client.post("/agent/request-approval", json={...})
    assert response.status_code == 200
```

## Success Criteria

1. Server starts: `uvicorn src.main:app --reload`
2. Health check returns 200
3. Agent approval endpoint works
4. Semantic search returns results
5. OpenAPI docs at `/docs`

## Run Instructions

```bash
cd E:\_projectsGithub\the-Librarian
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Then test:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/agent/request-approval -H "Content-Type: application/json" -d "{...}"
```

Start with main.py and health endpoint to get server running, then add other endpoints incrementally.