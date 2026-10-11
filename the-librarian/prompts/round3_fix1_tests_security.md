# Fix Agent 1: Graph Tests & Security Fixes

## Priority: CRITICAL - Fix Broken Tests and Security Issues

## Your Mission
Fix the broken graph tests and security vulnerabilities identified in the quality review.

## Critical Fixes Required

### 1. Fix Graph Module Tests (`tests/test_graph.py`)

**Current Problem**: All 3 tests failing due to async fixture issues

**What to fix**:
```python
# Current broken fixture:
@pytest.fixture
async def graph_ops():
    # This doesn't work with sync tests

# Fix to:
@pytest.fixture
def graph_ops():
    # Create sync-compatible fixture
    # OR make all tests async with @pytest.mark.asyncio
```

**Required test coverage**:
- Connection pool creation and health checks
- Node CRUD operations (create, read, update, delete)
- Vector storage and retrieval (768-dim)
- Vector similarity search
- All drift detection queries
- Error handling scenarios

### 2. Fix Security Vulnerabilities

**In `src/graph/config.py`**:
```python
# REMOVE hardcoded password:
neo4j_password: str = "librarian-pass"  # SECURITY RISK

# Change to:
neo4j_password: str  # Required from environment
```

**In `src/graph/operations.py`**:
```python
# Add Cypher injection protection:
def sanitize_cypher_params(params: dict) -> dict:
    # Validate and sanitize all parameters
    # Escape special characters
    # Type check values
```

**In `src/processing/parser.py`**:
```python
# Add path validation:
def validate_file_path(path: str) -> bool:
    # Check for path traversal attempts
    # Validate against allowed directories
    # Reject suspicious patterns
```

### 3. Add Missing Test Infrastructure

Create `tests/conftest.py`:
```python
# Shared test fixtures
# Neo4j test container setup
# Mock Ollama responses
# Test data factories
```

### 4. Fix Processing Test

**In `tests/test_processing.py`**:
- Fix the 1 skipped test (likely Ollama connection)
- Add mock for when Ollama unavailable

## Deliverables

1. **Fixed `tests/test_graph.py`** - All tests passing
2. **Security patches** applied to all identified vulnerabilities
3. **Test infrastructure** in `tests/conftest.py`
4. **Test report** showing all tests passing

## Success Criteria

Run these commands successfully:
```bash
pytest tests/test_graph.py -v     # All pass
pytest tests/test_processing.py -v # 20/20 pass
pytest tests/test_validation.py -v # 29/29 pass (maintain)
pytest --tb=short                  # All 52 tests pass
```

## Additional Security Checklist

- [ ] No hardcoded passwords
- [ ] No SQL/Cypher injection possible
- [ ] Path traversal prevented
- [ ] Input validation on all external data
- [ ] Sensitive data not logged

Start with the graph tests fix - this is the highest priority as it's blocking validation of core functionality.