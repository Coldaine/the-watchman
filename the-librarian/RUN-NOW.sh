#!/bin/bash
# RUN-NOW.sh - Execute this immediately to use your Claude credits!
# Time: 90 minutes max

echo "=========================================="
echo "RAPID LIBRARIAN AGENT IMPLEMENTATION"
echo "Using parallel Claude instances"
echo "Started at: $(date)"
echo "=========================================="

# Create necessary directories
mkdir -p src/models src/api src/validation tests tasks logs

# TASK 1: Models and Configuration (Simple, self-contained)
cat > tasks/task1_models.md <<'EOF'
Create the following files based on docs/architecture.md:

1. src/models/base.py:
- Pydantic BaseModel configurations
- Common enums (Status, ActionType, etc.)

2. src/models/documents.py:
- Document, Chunk, ParsedDocument models

3. src/models/agents.py:
- AgentRequest, AgentResponse, Decision models

4. src/config.py:
- Settings class using pydantic-settings
- Load from environment variables

5. requirements.txt with:
- fastapi, uvicorn, pydantic, pydantic-settings
- neo4j-driver, langchain, ollama

6. .env.template with all needed variables

Make sure all imports work. Use type hints everywhere.
EOF

# TASK 2: Core Validation Logic (Independent)
cat > tasks/task2_validation.md <<'EOF'
Create validation system based on docs/subdomains/validation-engine.md:

1. src/validation/rules.py:
- Define validation rules as classes
- DocumentStandardsRule, VersionCompatibilityRule, etc.

2. src/validation/engine.py:
- ValidationEngine class
- validate_request() method
- Returns ValidationResult with status (approved/rejected/escalated)

3. tests/test_validation.py:
- Test each validation rule
- Test the engine with various requests
- Make all tests pass

Use the models from task1 output. Mock any database calls.
EOF

# TASK 3: FastAPI Server (Integrates task 1 & 2)
cat > tasks/task3_api.md <<'EOF'
Create FastAPI server based on docs/architecture.md:

1. src/main.py:
- FastAPI app initialization
- Error handlers and middleware

2. src/api/agent_endpoints.py:
- POST /agent/request-approval
- POST /agent/report-completion
- Use validation engine from task2

3. src/api/health.py:
- GET /health endpoint
- GET /metrics endpoint (basic)

4. test_api.sh:
- curl commands to test each endpoint
- Example request/response

Server must run with: uvicorn src.main:app --reload
Mock all database operations for now.
EOF

# TASK 4: Basic Integration (Combines everything)
cat > tasks/task4_integrate.md <<'EOF'
Integrate all components and create:

1. src/coordinator.py:
- Coordinate between validation and API
- Handle the full request flow
- Return appropriate responses

2. README.md with:
- What's implemented vs mocked
- How to run the server
- Example API calls
- Next steps

3. run.sh script that:
- Checks dependencies
- Starts Neo4j (if available)
- Runs the FastAPI server

4. Run pytest and fix any failing tests

Make sure the server handles at least one full agent request flow.
EOF

echo ""
echo "TASKS CREATED! Now run these commands in SEPARATE terminals:"
echo ""
echo "Terminal 1:"
echo "  claude chat < tasks/task1_models.md"
echo ""
echo "Terminal 2:"
echo "  claude chat < tasks/task2_validation.md"
echo ""
echo "Terminal 3:"
echo "  claude chat < tasks/task3_api.md"
echo ""
echo "After all complete, run:"
echo "  claude chat < tasks/task4_integrate.md"
echo ""
echo "=========================================="
echo "GO GO GO! You have 90 minutes!"
echo "=========================================="