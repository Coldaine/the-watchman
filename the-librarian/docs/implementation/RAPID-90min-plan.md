# ⚡ RAPID 90-MINUTE IMPLEMENTATION PLAN

## STOP! Don't Build - Use Existing Tools

### Option A: Use LangChain Template (30 minutes to working RAG)

```bash
# 1. Install LangChain CLI (2 min)
pip install -U "langchain-cli[serve]"

# 2. Create app from template (1 min)
langchain app new librarian-agent --package neo4j-advanced-rag

# 3. Configure (2 min)
cd librarian-agent
cat > .env <<EOF
OPENAI_API_KEY=your-key
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
EOF

# 4. Run (1 min)
langchain serve

# DONE! You have a working RAG system at http://localhost:8000
```

### Option B: Simple Parallel Claude Script (Use Your 90 Minutes NOW)

```bash
#!/bin/bash
# parallel-claude.sh - Dead simple parallel execution

# Create 3 git worktrees
git worktree add -b models ../librarian-models
git worktree add -b api ../librarian-api
git worktree add -b graph ../librarian-graph

# Launch 3 Claude instances in parallel
cat > task1.txt <<'EOF'
cd ../librarian-models
Create src/models/ with Document, Agent, and Decision models.
Use Pydantic. Follow docs/architecture.md.
Commit when done.
EOF

cat > task2.txt <<'EOF'
cd ../librarian-api
Create src/api/ with FastAPI endpoints.
Mock the database calls for now.
Follow docs/architecture.md.
Commit when done.
EOF

cat > task3.txt <<'EOF'
cd ../librarian-graph
Create src/graph/ with Neo4j operations.
Use neo4j-driver.
Follow docs/architecture.md.
Commit when done.
EOF

# Run all three in parallel
claude chat < task1.txt &
claude chat < task2.txt &
claude chat < task3.txt &

wait
echo "All parallel tasks complete!"
```

---

## 🎯 WHAT TO ACTUALLY DO RIGHT NOW (90 Minutes)

### Minute 0-15: Setup
```bash
# 1. Install Neo4j Desktop (already done?)
# 2. Install Ollama (already done?)
# 3. Clone the LangChain template
langchain app new librarian-agent --package neo4j-advanced-rag
cd librarian-agent

# 4. Install dependencies
pip install -r requirements.txt
pip install neo4j-driver fastapi uvicorn
```

### Minute 15-30: Use ONE Claude to Create Core Structure
```bash
claude chat

> Create the following structure based on docs/architecture.md:
> - src/models/ (Pydantic models for Document, Agent, Decision)
> - src/config.py (Settings using pydantic-settings)
> - requirements.txt (all dependencies)
> - .env.template
>
> Use the existing langchain template but add our specific models.
```

### Minute 30-60: Use Parallel Claudes for Modules
```bash
# Terminal 1
claude chat
> Implement src/validation/engine.py based on docs/subdomains/validation-engine.md
> Use the models from src/models/
> Create working validation rules

# Terminal 2
claude chat
> Implement src/agents/coordinator.py based on docs/subdomains/agent-protocol.md
> Create the approval logic
> Mock the database calls

# Terminal 3
claude chat
> Create tests/test_integration.py
> Write tests for the validation engine and agent coordinator
> Make sure they pass
```

### Minute 60-75: Integration
```bash
claude chat
> Integrate all the modules into the FastAPI app
> Wire up the endpoints to use the validation and agent modules
> Make sure the server starts
```

### Minute 75-90: Test & Document
```bash
# Run the app
uvicorn app.server:app --reload

# Test with curl
curl -X POST http://localhost:8000/agent/request \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test", "action": "create", "content": "test"}'

# Create README
claude chat
> Create a README.md explaining:
> - What we built
> - How to run it
> - What's working vs mocked
> - Next steps
```

---

## 🚫 WHAT NOT TO DO

1. **DON'T** build a complex orchestration system
2. **DON'T** implement everything from scratch
3. **DON'T** worry about Docker right now
4. **DON'T** implement all 6 subdomains
5. **DON'T** write comprehensive tests

## ✅ WHAT TO DO

1. **USE** the LangChain template as base
2. **FOCUS** on core validation + agent approval only
3. **MOCK** the database operations
4. **RUN** 3 Claudes max in parallel
5. **GET** something working end-to-end

---

## Alternative: Use MCP Server (If You Have Time Later)

```bash
# Install MCP
npm install -g @modelcontextprotocol/cli

# Create MCP server for your project
mcp create librarian-server

# This gives you:
# - Automatic tool discovery
# - Built-in parallelization
# - Works with Claude Code directly
```

---

## The Truth About Your Project

With 90 minutes, you can realistically get:
1. ✅ Basic FastAPI server running (using template)
2. ✅ Core models defined
3. ✅ One or two key endpoints working
4. ❌ Not the full system
5. ❌ Not production-ready

**Recommendation**: Use the LangChain template, add your custom models, get ONE flow working (agent approval), then iterate from there.

---

## Simplified Parallel Script (Copy & Run NOW)

```bash
#!/bin/bash
# quick-parallel.sh - Run this RIGHT NOW

# Create tasks directory
mkdir -p tasks

# Task 1: Core models and config
cat > tasks/task1.md <<'EOF'
Based on docs/architecture.md, create:
1. src/models.py with all Pydantic models
2. src/config.py with settings
3. requirements.txt
Test that imports work.
EOF

# Task 2: Basic API
cat > tasks/task2.md <<'EOF'
Create src/main.py with FastAPI:
1. POST /agent/request endpoint
2. GET /health endpoint
3. Use models from src/models.py
4. Mock all database calls
Make sure server runs.
EOF

# Task 3: One key feature
cat > tasks/task3.md <<'EOF'
Create src/validator.py:
1. Simple validation rules from docs
2. Function to validate agent requests
3. Return approved/rejected
Write 3 tests that pass.
EOF

echo "Starting 3 parallel Claude instances..."
echo "You have 90 minutes - GO!"

# Open 3 new terminals and run:
# Terminal 1: claude chat < tasks/task1.md
# Terminal 2: claude chat < tasks/task2.md
# Terminal 3: claude chat < tasks/task3.md
```

**RUN THIS NOW!** Don't overthink it!