# Librarian Agent API - Quick Start Guide

## Prerequisites

1. **Python 3.11+** installed
2. **Neo4j** database (optional but recommended)
3. **Ollama** with nomic-embed-text model (optional but recommended)

## Installation

```bash
# Navigate to project directory
cd E:\_projectsGithub\the-Librarian

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

## Configuration

Create or update `.env` file:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

# Vector Configuration
VECTOR_DIMENSIONS=768
```

## Start Services

### 1. Start Neo4j (Optional)
```bash
# If using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Access Neo4j Browser at http://localhost:7474
```

### 2. Start Ollama (Optional)
```bash
# Start Ollama server
ollama serve

# Pull embedding model (in another terminal)
ollama pull nomic-embed-text
```

### 3. Initialize Database Schema (First time only)
```bash
# Run the Cypher queries from docs/architecture.md
# Lines 237-287 to create constraints and vector indexes
```

## Run the API Server

### Development Mode (with auto-reload)
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Background Mode
```bash
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

## Verify Installation

### Check Health
```bash
curl http://localhost:8000/health
```

Expected response (with services running):
```json
{
  "status": "healthy",
  "neo4j": true,
  "ollama": true,
  "version": "0.1.0"
}
```

### Access Documentation
Open in browser:
- **Interactive API Docs**: http://localhost:8000/docs
- **API Info**: http://localhost:8000/

## Quick Test Examples

### 1. Request Agent Approval
```bash
curl -X POST http://localhost:8000/agent/request-approval \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent-001",
    "action": "create",
    "target_type": "architecture",
    "content": "# Authentication Architecture\n\nJWT-based authentication system...",
    "rationale": "Required for secure API access",
    "references": []
  }'
```

### 2. Semantic Search
```bash
curl -X POST http://localhost:8000/query/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How should authentication be implemented?",
    "context_type": "architecture",
    "limit": 5
  }'
```

### 3. Check for Drift
```bash
curl http://localhost:8000/validation/drift-check
```

### 4. Check Compliance
```bash
curl http://localhost:8000/validation/compliance/auth
```

### 5. List Documents
```bash
curl http://localhost:8000/admin/documents?limit=10
```

## Using the Interactive Docs

1. Navigate to http://localhost:8000/docs
2. Click on any endpoint to expand
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"
6. View the response

## Common Issues

### Issue: "degraded" status with neo4j: false

**Solution**: Neo4j is not running or not accessible.
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Or check the port
netstat -an | grep 7687
```

### Issue: "degraded" status with ollama: false

**Solution**: Ollama server is not running or model not available.
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull the model
ollama pull nomic-embed-text
```

### Issue: Connection refused errors

**Solution**: Check your .env file has correct URIs.
```bash
# Verify .env file exists
cat .env

# Test Neo4j connection
cypher-shell -u neo4j -p your_password "RETURN 1"
```

### Issue: Module import errors

**Solution**: Ensure you're in the project root and modules are importable.
```bash
# Set PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:E:\_projectsGithub\the-Librarian"

# Or use python -m
python -m uvicorn src.main:app --reload
```

## Development Workflow

### 1. Make Changes
Edit files in `src/api/` or other modules.

### 2. Server Auto-Reloads
If running with `--reload`, changes are picked up automatically.

### 3. Test Changes
```bash
# Run tests
pytest tests/test_api.py -v

# Or test manually with curl/browser
curl http://localhost:8000/health
```

### 4. View Logs
Server logs appear in terminal or in `api.log` if running in background.

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | System health check |
| POST | `/agent/request-approval` | Request approval for changes |
| POST | `/agent/report-completion` | Report task completion |
| POST | `/query/semantic` | Semantic search |
| GET | `/query/cypher` | Execute Cypher queries |
| GET | `/query/similar/{id}` | Find similar documents |
| GET | `/validation/drift-check` | Check for drift |
| GET | `/validation/compliance/{subsystem}` | Check compliance |
| GET | `/validation/drift-summary` | Drift statistics |
| POST | `/admin/ingest` | Ingest document from path |
| POST | `/admin/ingest-file` | Upload and ingest file |
| DELETE | `/admin/document/{id}` | Delete document |
| GET | `/admin/documents` | List all documents |

## Production Deployment Checklist

- [ ] Configure authentication (API keys/JWT)
- [ ] Set up HTTPS/TLS
- [ ] Configure CORS for specific origins
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure logging (structured logs)
- [ ] Set up rate limiting
- [ ] Configure connection pooling
- [ ] Set up backup for Neo4j
- [ ] Document API for consumers
- [ ] Set up CI/CD pipeline
- [ ] Load testing
- [ ] Security audit

## Support

For issues or questions:
1. Check `API_IMPLEMENTATION_COMPLETE.md` for detailed documentation
2. Review `docs/architecture.md` for system architecture
3. Check logs in terminal or `api.log`
4. Verify all services are running (Neo4j, Ollama)

## Next Steps

1. **Ingest Documents**: Use `/admin/ingest` to load your specifications
2. **Test Validation**: Submit test requests via `/agent/request-approval`
3. **Query Knowledge**: Use `/query/semantic` to search specifications
4. **Monitor Drift**: Regularly check `/validation/drift-check`
5. **Build Agents**: Integrate your AI agents with the API endpoints
