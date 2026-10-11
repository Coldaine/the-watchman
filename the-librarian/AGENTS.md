# Agent Development Guide

This guide covers development workflows, agent coordination, and best practices for working on the Librarian project.

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [UV Workflow](#uv-workflow)
3. [Agent Coordination](#agent-coordination)
4. [Development Workflow](#development-workflow)
5. [Testing Strategy](#testing-strategy)
6. [Code Quality](#code-quality)

---

## Environment Setup

### Prerequisites
- **Python**: 3.10 or higher
- **UV**: Modern Python package manager ([installation guide](UV_SETUP.md))
- **Neo4j**: Graph database instance (local or remote)
- **Ollama**: For local embedding generation

### Initial Setup

1. **Clone the repository**:
```bash
git clone https://github.com/Coldaine/the-Librarian.git
cd the-Librarian
```

2. **Create and activate UV virtual environment**:
```bash
# Create virtual environment
uv venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
# Install all dependencies (including dev tools)
uv sync --all-extras

# Or production only
uv sync
```

4. **Configure environment**:
```bash
# Copy template
cp .env.template .env

# Edit with your settings
notepad .env  # Windows
nano .env     # Linux/Mac
```

5. **Verify installation**:
```bash
# Run health check
uv run python -c "import src; print('Import successful')"

# Start server
uv run uvicorn src.main:app --reload
```

---

## UV Workflow

### Why UV?

UV is 10-100x faster than pip and provides:
- **Deterministic** dependency resolution via lock files
- **Built-in** virtual environment management
- **Fast** package installation using Rust
- **Compatible** with existing Python tools

See [UV_SETUP.md](UV_SETUP.md) for comprehensive UV documentation.

### Common UV Commands

#### Running Applications
```bash
# Start API server (development)
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Start API server (production)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Run verification script
uv run python verify_processing.py

# Run demo
uv run python demo_processing.py
```

#### Managing Dependencies

```bash
# Add production dependency
uv add <package-name>

# Add development dependency
uv add --dev <package-name>

# Update all dependencies
uv sync --upgrade

# Reinstall everything
uv sync --reinstall
```

#### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py

# Run tests matching pattern
uv run pytest -k "validation"
```

#### Code Quality

```bash
# Format code (black)
uv run black src/ tests/

# Sort imports (isort)
uv run isort src/ tests/

# Type checking (mypy)
uv run mypy src/

# Linting (flake8)
uv run flake8 src/ tests/

# All quality checks
uv run black src/ tests/ && uv run isort src/ tests/ && uv run mypy src/ && uv run flake8 src/ tests/
```

---

## Agent Coordination

### Project Architecture

```
the-Librarian/
├── src/
│   ├── api/            # FastAPI endpoints
│   ├── graph/          # Neo4j operations
│   ├── processing/     # Document processing pipeline
│   ├── validation/     # Validation engine
│   └── integration/    # Integration orchestrator
├── tests/              # Test suite
├── docs/               # Documentation
├── prompts/            # Agent coordination prompts
└── examples/           # Example implementations
```

### Agent Responsibilities

#### API Agent
- **Focus**: REST API endpoints
- **Files**: `src/api/*.py`
- **Tasks**:
  - Implement FastAPI routes
  - Request/response validation
  - Error handling
  - API documentation

#### Processing Agent
- **Focus**: Document processing pipeline
- **Files**: `src/processing/*.py`
- **Tasks**:
  - Document parsing
  - Chunking strategies
  - Embedding generation
  - Pipeline orchestration

#### Validation Agent
- **Focus**: Data validation and drift detection
- **Files**: `src/validation/*.py`
- **Tasks**:
  - Schema validation
  - Drift detection
  - Audit trail management
  - Rule engine

#### Integration Agent
- **Focus**: Component integration
- **Files**: `src/integration/*.py`
- **Tasks**:
  - Adapter patterns
  - Orchestration
  - Error handling
  - Async coordination

#### Testing Agent
- **Focus**: Test coverage and quality
- **Files**: `tests/*.py`
- **Tasks**:
  - Unit tests
  - Integration tests
  - Mocking strategies
  - Coverage analysis

### Parallel Development

For parallel agent execution (multiple Claude instances):

1. **Use coordinated prompts** in `prompts/` directory
2. **Follow branch naming**: `feature/<agent-name>/<feature>`
3. **Communicate via**: Git commits and PR descriptions
4. **Avoid conflicts**: Each agent owns specific files
5. **Integration points**: Defined in `src/integration/`

Example parallel workflow:
```bash
# Agent 1: API development
git checkout -b feature/api/query-endpoints
# Work on src/api/query.py
git commit -m "feat(api): Add query endpoints"

# Agent 2: Processing development
git checkout -b feature/processing/chunking
# Work on src/processing/chunker.py
git commit -m "feat(processing): Implement semantic chunking"
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/<component>/<feature-name>

# Make changes
# ...

# Run tests
uv run pytest

# Check code quality
uv run black src/ tests/
uv run mypy src/

# Commit
git add .
git commit -m "feat(<component>): <description>"

# Push
git push origin feature/<component>/<feature-name>
```

### 2. Testing Workflow

Before committing:
```bash
# 1. Format code
uv run black src/ tests/
uv run isort src/ tests/

# 2. Run tests
uv run pytest -v

# 3. Check coverage
uv run pytest --cov=src --cov-report=term-missing

# 4. Type check
uv run mypy src/

# 5. Lint
uv run flake8 src/ tests/
```

### 3. Integration Testing

```bash
# Start Neo4j (if using Docker)
docker-compose up -d neo4j

# Start Ollama
ollama serve

# Run integration tests
uv run pytest tests/test_integration.py -v

# Verify end-to-end
uv run python verify_processing.py
```

---

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures
├── test_api.py           # API endpoint tests
├── test_graph.py         # Neo4j operation tests
├── test_processing.py    # Processing pipeline tests
├── test_validation.py    # Validation engine tests
└── test_integration.py   # Integration tests
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/test_api.py

# Specific test
uv run pytest tests/test_api.py::test_health_endpoint

# With coverage
uv run pytest --cov=src --cov-report=html

# Verbose output
uv run pytest -v -s

# Failed tests only
uv run pytest --lf

# Stop on first failure
uv run pytest -x
```

### Writing Tests

Example test structure:
```python
import pytest
from src.api.models import QueryRequest

@pytest.mark.asyncio
async def test_query_endpoint(client, mock_neo4j):
    """Test query endpoint with mocked Neo4j."""
    # Arrange
    request = QueryRequest(query="test query", limit=10)

    # Act
    response = await client.post("/api/v1/query", json=request.dict())

    # Assert
    assert response.status_code == 200
    assert "results" in response.json()
```

---

## Code Quality

### Style Guidelines

- **Black**: Automatic code formatting (line length: 100)
- **isort**: Import sorting (black-compatible profile)
- **Type hints**: Use for function signatures
- **Docstrings**: Required for public functions/classes

### Pre-commit Checklist

- [ ] Code formatted with `black`
- [ ] Imports sorted with `isort`
- [ ] All tests pass (`pytest`)
- [ ] Type checking passes (`mypy`)
- [ ] No linting errors (`flake8`)
- [ ] Coverage maintained or improved

### Automation

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
uv run black src/ tests/
uv run isort src/ tests/
uv run pytest
uv run mypy src/
uv run flake8 src/ tests/
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Environment Configuration

### .env File

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=INFO

# Validation
DRIFT_THRESHOLD=0.1
VALIDATION_ENABLED=true
```

### Multiple Environments

```bash
# Development
cp .env.template .env.dev

# Testing
cp .env.template .env.test

# Production
cp .env.template .env.prod
```

Load specific environment:
```bash
# Using UV
uv run --env-file .env.dev uvicorn src.main:app
```

---

## Troubleshooting

### UV Issues

```bash
# Clear cache
uv cache clean

# Reinstall dependencies
uv sync --reinstall

# Update UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Import Errors

```bash
# Verify installation
uv run python -c "import src; print('OK')"

# Check PYTHONPATH
uv run python -c "import sys; print(sys.path)"

# Reinstall package
uv sync --reinstall
```

### Test Failures

```bash
# Run with verbose output
uv run pytest -vv -s

# Show local variables on failure
uv run pytest --showlocals

# Enter debugger on failure
uv run pytest --pdb
```

---

## Additional Resources

- [UV Setup Guide](UV_SETUP.md)
- [API Documentation](docs/api/QUICK_START.md)
- [Graph Setup Guide](docs/graph/SETUP.md)
- [Integration Architecture](docs/integration_architecture.md)
- [UV Official Docs](https://docs.astral.sh/uv/)
