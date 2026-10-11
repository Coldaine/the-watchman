# Testing Strategy

## Overview
Comprehensive testing approach for the Librarian Agent system, covering unit tests, integration tests, end-to-end scenarios, and performance benchmarks. This document defines test patterns, mock strategies, and quality gates for each subdomain.

## Testing Philosophy

### Testing Principles
1. **Test Behavior, Not Implementation**: Focus on what the system does, not how
2. **Fast Feedback**: Unit tests run in seconds, integration in minutes
3. **Isolated Testing**: Each test independent and repeatable
4. **Realistic Scenarios**: Test with production-like data and conditions
5. **Continuous Validation**: Tests run on every commit

### Test Pyramid
```
         /\        E2E Tests (10%)
        /  \       - Full system scenarios
       /    \      - Agent workflows
      /------\
     /        \    Integration Tests (30%)
    /          \   - API endpoints
   /            \  - Graph operations
  /              \ - Service interactions
 /________________\
                    Unit Tests (60%)
                    - Business logic
                    - Validators
                    - Parsers
```

## Unit Testing

### Test Structure
```python
# Standard test structure
class TestValidationEngine:
    """Unit tests for validation engine"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return ValidationEngine(mock_graph())

    def test_validate_architecture_document(self, validator):
        """Test architecture document validation"""
        # Arrange
        doc = create_test_document(doc_type="architecture")

        # Act
        result = validator.validate(doc)

        # Assert
        assert result.passed
        assert len(result.violations) == 0

    def test_reject_missing_frontmatter(self, validator):
        """Test rejection of document without frontmatter"""
        # Arrange
        doc = create_test_document(frontmatter={})

        # Act
        result = validator.validate(doc)

        # Assert
        assert not result.passed
        assert any(v.rule == "DOC-001" for v in result.violations)
```

### Mock Strategies

```python
# Mock factories for common objects
class MockFactory:
    """Factory for creating test objects"""

    @staticmethod
    def agent_request(**kwargs) -> AgentRequest:
        """Create mock agent request"""
        defaults = {
            'agent_id': 'test-agent',
            'session_id': 'sess-123',
            'request_type': 'APPROVAL',
            'action': 'create',
            'target_type': 'design',
            'content': 'Test content',
            'rationale': 'Test rationale'
        }
        defaults.update(kwargs)
        return AgentRequest(**defaults)

    @staticmethod
    def graph_node(**kwargs) -> Dict:
        """Create mock graph node"""
        defaults = {
            'id': f'node-{uuid.uuid4().hex[:8]}',
            'content': 'Test node content',
            'status': 'approved',
            'version': '1.0.0'
        }
        defaults.update(kwargs)
        return defaults

# Mock Neo4j operations
@pytest.fixture
def mock_graph():
    """Mock graph operations"""
    graph = Mock(spec=GraphOperations)
    graph.query = AsyncMock(return_value=[])
    graph.execute_write = AsyncMock()
    return graph
```

### Parameterized Tests

```python
@pytest.mark.parametrize("doc_type,expected_fields", [
    ("architecture", ["doc", "subsystem", "id", "version"]),
    ("design", ["doc", "component", "id", "version"]),
    ("tasks", ["doc", "sprint", "status", "assignee"])
])
def test_required_frontmatter_fields(doc_type, expected_fields):
    """Test required fields for each document type"""
    validator = DocumentValidator()

    # Test with complete frontmatter
    complete = {field: "value" for field in expected_fields}
    result = validator.validate_frontmatter(doc_type, complete)
    assert result.passed

    # Test with missing field
    for field in expected_fields:
        incomplete = complete.copy()
        del incomplete[field]
        result = validator.validate_frontmatter(doc_type, incomplete)
        assert not result.passed
        assert field in result.message
```

## Integration Testing

### API Integration Tests

```python
class TestAgentAPI:
    """Integration tests for agent API"""

    @pytest.fixture
    async def client(self):
        """Create test client"""
        from main import app
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def test_db(self):
        """Create test database"""
        # Start test Neo4j container
        async with TestNeo4j() as neo4j:
            await neo4j.setup_schema()
            yield neo4j

    async def test_agent_request_approval_flow(self, client, test_db):
        """Test complete agent approval flow"""
        # Create agent request
        request = {
            "agent_id": "test-agent",
            "request_type": "APPROVAL",
            "action": "create",
            "target_type": "design",
            "content": "# Test Design\nContent here",
            "rationale": "Implementing feature X"
        }

        # Submit request
        response = await client.post("/agent/request", json=request)
        assert response.status_code == 200

        result = response.json()
        assert result["status"] in ["approved", "revision_required", "escalated"]

        if result["status"] == "approved":
            # Verify node created in graph
            node = await test_db.get_node(result["assigned_id"])
            assert node is not None
            assert node["content"] == request["content"]

    async def test_rate_limiting(self, client):
        """Test agent rate limiting"""
        request = MockFactory.agent_request()

        # Send multiple requests
        responses = []
        for _ in range(65):  # Exceeds 60/minute limit
            response = await client.post("/agent/request", json=request)
            responses.append(response.status_code)

        # Should have some 429 responses
        assert 429 in responses
```

### Graph Integration Tests

```python
class TestGraphOperations:
    """Integration tests for Neo4j operations"""

    @pytest.fixture
    async def graph(self):
        """Create graph connection"""
        graph = GraphOperations(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test"
        )
        await graph.clear_test_data()
        yield graph
        await graph.close()

    async def test_document_ingestion_and_retrieval(self, graph):
        """Test document storage and vector search"""
        # Ingest document
        doc = ParsedDocument(
            path="/test/doc.md",
            doc_type="architecture",
            content="Test architecture content",
            frontmatter={"id": "test-001", "version": "1.0.0"}
        )

        chunks = [
            Chunk(content="Chunk 1 content"),
            Chunk(content="Chunk 2 content")
        ]

        embeddings = [np.random.rand(768), np.random.rand(768)]

        storage = DocumentStorage(graph)
        doc_id = await storage.store_document(doc, chunks, embeddings)

        # Verify storage
        stored_doc = await graph.get_node(doc_id)
        assert stored_doc["content"] == doc.content

        # Test vector search
        query_embedding = np.random.rand(768)
        results = await graph.vector_search(query_embedding, limit=5)
        assert len(results) > 0

    async def test_relationship_creation(self, graph):
        """Test creating and traversing relationships"""
        # Create nodes
        arch_id = await graph.create_node("Architecture", {"id": "arch-001"})
        design_id = await graph.create_node("Design", {"id": "design-001"})

        # Create relationship
        await graph.create_relationship(
            design_id, "IMPLEMENTS", arch_id,
            properties={"version": "1.0.0"}
        )

        # Verify traversal
        query = """
            MATCH (d:Design {id: $design_id})-[:IMPLEMENTS]->(a:Architecture)
            RETURN a.id
        """
        results = await graph.query(query, {"design_id": "design-001"})
        assert results[0]["a.id"] == "arch-001"
```

## End-to-End Testing

### Agent Workflow Tests

```python
class TestAgentWorkflows:
    """End-to-end agent workflow tests"""

    async def test_complete_feature_implementation_workflow(self):
        """Test agent implementing a complete feature"""
        # Setup
        system = await setup_test_system()
        agent = TestAgent("claude-test")

        # Step 1: Agent requests context
        context = await agent.query_context("authentication requirements")
        assert len(context.sections) > 0

        # Step 2: Agent creates design document
        design_request = agent.create_design_request(
            title="OAuth2 Implementation",
            content="Design content here",
            references=context.referenced_ids
        )

        response = await system.process_request(design_request)
        assert response.status == "approved"
        design_id = response.assigned_id

        # Step 3: Agent implements code
        code_request = agent.create_code_request(
            files=["auth/oauth2.py", "auth/tokens.py"],
            implements=design_id
        )

        response = await system.process_request(code_request)
        assert response.status == "approved"

        # Step 4: Verify compliance
        compliance = await system.check_compliance()
        assert compliance.requirement_coverage > 0.8

    async def test_multi_agent_coordination(self):
        """Test multiple agents working together"""
        system = await setup_test_system()

        # Create multiple agents
        designer = TestAgent("designer-agent")
        coder = TestAgent("coder-agent")
        reviewer = TestAgent("reviewer-agent")

        # Designer creates architecture
        arch_request = designer.create_architecture_request(
            title="System Architecture",
            subsystem="auth"
        )
        arch_response = await system.process_request(arch_request)

        # Coder queries architecture
        context = await coder.query_context(f"architecture {arch_response.assigned_id}")

        # Coder implements based on architecture
        impl_request = coder.create_implementation_request(
            implements=arch_response.assigned_id
        )
        impl_response = await system.process_request(impl_request)

        # Reviewer validates implementation
        review_request = reviewer.create_validation_request(
            target=impl_response.assigned_id
        )
        review_response = await system.process_request(review_request)

        assert review_response.status == "approved"
```

### Scenario-Based Tests

```python
class TestScenarios:
    """Scenario-based testing"""

    @pytest.mark.scenario
    async def test_drift_detection_scenario(self):
        """Test drift detection and resolution"""
        system = await setup_test_system()

        # Create approved architecture
        arch_id = await system.create_architecture(
            content="Original architecture",
            status="approved"
        )

        # Create design implementing architecture
        design_id = await system.create_design(
            content="Design implementation",
            implements=arch_id
        )

        # Modify design without updating architecture
        await system.update_node(design_id, {
            "content": "Modified design",
            "modified_at": datetime.now()
        })

        # Run drift detection
        drift_detector = DriftDetector(system.graph)
        violations = await drift_detector.detect_all_drift()

        # Should detect drift
        assert any(v.type == "design_ahead_of_architecture" for v in violations)

        # Agent requests approval for change
        agent = TestAgent("agent-001")
        request = agent.create_approval_request(
            target_id=design_id,
            rationale="Design improvement"
        )

        response = await system.process_request(request)

        # After approval, drift should be resolved
        violations = await drift_detector.detect_all_drift()
        assert not any(
            v.type == "design_ahead_of_architecture" and v.source == design_id
            for v in violations
        )
```

## Performance Testing

### Load Testing

```python
class TestPerformance:
    """Performance and load tests"""

    @pytest.mark.performance
    async def test_concurrent_agent_requests(self):
        """Test system under concurrent load"""
        system = await setup_test_system()

        # Create multiple agents
        agents = [TestAgent(f"agent-{i}") for i in range(10)]

        # Generate requests
        requests = []
        for agent in agents:
            for _ in range(10):  # 100 total requests
                requests.append(agent.create_random_request())

        # Submit concurrently
        start_time = time.time()

        responses = await asyncio.gather(*[
            system.process_request(req) for req in requests
        ])

        elapsed = time.time() - start_time

        # Performance assertions
        assert elapsed < 30  # Should handle 100 requests in 30 seconds
        assert sum(1 for r in responses if r.status == "approved") > 70

        # Check system health
        metrics = await system.get_metrics()
        assert metrics.error_rate < 0.05
        assert metrics.avg_response_time < 1000  # ms

    @pytest.mark.benchmark
    def test_vector_search_performance(self, benchmark):
        """Benchmark vector search"""
        graph = setup_graph_with_data(num_documents=1000)

        def search():
            query_embedding = np.random.rand(768)
            results = graph.vector_search(query_embedding, limit=10)
            return results

        results = benchmark(search)
        assert len(results) == 10
        assert benchmark.stats['mean'] < 0.1  # 100ms average
```

### Memory Testing

```python
@pytest.mark.memory
async def test_memory_usage():
    """Test memory consumption"""
    import tracemalloc
    tracemalloc.start()

    system = await setup_test_system()

    # Ingest large dataset
    for i in range(100):
        doc = create_large_document(size_mb=1)
        await system.ingest_document(doc)

    # Check memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Should not exceed 1GB for 100 documents
    assert peak / 1024 / 1024 < 1024
```

## Test Data Management

### Test Fixtures

```python
# conftest.py - Shared fixtures
@pytest.fixture(scope="session")
async def neo4j_container():
    """Start Neo4j test container"""
    container = TestContainer("neo4j:5")
    container.start()
    yield container
    container.stop()

@pytest.fixture
async def test_data():
    """Load test data"""
    return {
        "architecture": load_json("test_data/architecture.json"),
        "design": load_json("test_data/design.json"),
        "requirements": load_json("test_data/requirements.json")
    }

@pytest.fixture
def mock_ollama():
    """Mock Ollama embedding service"""
    mock = Mock()
    mock.embed = Mock(return_value=np.random.rand(768))
    return mock
```

### Test Data Generation

```python
class TestDataGenerator:
    """Generate realistic test data"""

    @staticmethod
    def create_document_hierarchy(depth=3, breadth=3):
        """Create hierarchical test documents"""
        documents = []

        def create_level(parent_id, level):
            if level >= depth:
                return

            for i in range(breadth):
                doc_id = f"{parent_id}-{i}" if parent_id else f"doc-{i}"
                doc = {
                    'id': doc_id,
                    'type': ['architecture', 'design', 'code'][level],
                    'content': f"Test content for {doc_id}",
                    'parent': parent_id
                }
                documents.append(doc)
                create_level(doc_id, level + 1)

        create_level(None, 0)
        return documents

    @staticmethod
    def create_agent_requests(count=100):
        """Generate random agent requests"""
        requests = []
        for _ in range(count):
            requests.append({
                'agent_id': random.choice(['agent-1', 'agent-2', 'agent-3']),
                'action': random.choice(['create', 'modify', 'delete']),
                'target_type': random.choice(['architecture', 'design', 'code']),
                'content': fake.text(),
                'rationale': fake.sentence()
            })
        return requests
```

## Quality Gates

### Coverage Requirements
```yaml
# .coveragerc
[run]
source = src
omit =
    */tests/*
    */migrations/*

[report]
precision = 2
fail_under = 80

[html]
directory = htmlcov
```

### Test Execution Strategy
```yaml
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast)
    integration: Integration tests (requires services)
    e2e: End-to-end tests (slow)
    performance: Performance tests
    scenario: Scenario-based tests

addopts =
    --verbose
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html
```

### CI/CD Integration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest -m unit --cov

  integration-tests:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/test
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest -m integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E tests
        run: pytest -m e2e
```

## Test Reporting

### Test Results Dashboard
```python
# generate_test_report.py
def generate_test_report():
    """Generate HTML test report"""
    results = parse_junit_xml("test-results.xml")

    report = {
        'total': results.total,
        'passed': results.passed,
        'failed': results.failed,
        'skipped': results.skipped,
        'duration': results.duration,
        'coverage': get_coverage_percentage(),
        'timestamp': datetime.now()
    }

    # Generate HTML
    with open('test-report.html', 'w') as f:
        f.write(render_template('test_report.html', **report))
```

## Troubleshooting Tests

### Common Test Issues

#### "Test database not clean"
```python
# Reset test database between tests
@pytest.fixture(autouse=True)
async def clean_database(test_db):
    yield
    await test_db.clear_all()
```

#### "Async test timeout"
```python
# Increase timeout for slow tests
@pytest.mark.timeout(30)
async def test_slow_operation():
    # test code
```

#### "Mock not working"
```python
# Ensure proper async mock
from unittest.mock import AsyncMock
mock_service.method = AsyncMock(return_value=expected)
```

## References

- **pytest Documentation**: https://docs.pytest.org/
- **Test Pyramid**: https://martinfowler.com/articles/practical-test-pyramid.html
- **Property-Based Testing**: https://hypothesis.readthedocs.io/
- **Neo4j Test Containers**: https://www.testcontainers.org/
- **Coverage.py**: https://coverage.readthedocs.io/