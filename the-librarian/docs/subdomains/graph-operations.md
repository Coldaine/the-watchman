# Knowledge Graph Operations

## Overview
The Graph Operations subdomain manages all interactions with the Neo4j knowledge graph, including schema management, query patterns, data integrity, and performance optimization. This is the persistence layer that maintains relationships between architecture, design, code, and agent interactions.

## Core Concepts

### Graph Structure
The knowledge graph uses a property graph model with:
- **Nodes**: Entities (documents, requirements, decisions, agents)
- **Relationships**: Typed connections between entities
- **Properties**: Key-value pairs on nodes and relationships
- **Labels**: Node categorization for efficient querying
- **Indexes**: Vector and traditional indexes for fast lookups

### Consistency Model
- **ACID Transactions**: All modifications are transactional
- **Immutable Audit Trail**: Historical nodes never deleted, only marked superseded
- **Referential Integrity**: Enforced through constraints and validation
- **Version Tracking**: Temporal properties track entity evolution

## Implementation Details

### Node Schemas

#### Document Nodes
```cypher
// Architecture Node
(:Architecture {
    id: String UNIQUE,           // e.g., "arch-auth-001"
    version: String,             // Semantic version "1.2.0"
    title: String,
    subsystem: String,           // e.g., "authentication"
    content: String,             // Full document content
    content_hash: String,        // SHA-256 for change detection

    // Metadata
    status: String,              // draft|review|approved|deprecated
    owners: [String],            // List of owner IDs
    created_at: DateTime,
    modified_at: DateTime,
    last_reviewed: Date,

    // Compliance
    compliance_level: String,    // strict|flexible|advisory
    drift_tolerance: String,     // none|minor|moderate

    // Vector embedding
    embedding: [Float],          // 768-dimensional vector
    embedding_model: String,     // Model used for embedding
    embedding_date: DateTime
})

// Design Node
(:Design {
    id: String UNIQUE,
    version: String,
    title: String,
    component: String,           // Specific component/module
    content: String,
    content_hash: String,

    // Hierarchy
    parent_design_id: String?,   // For nested designs
    abstraction_level: String,   // high|mid|low

    // Status
    status: String,
    owners: [String],
    created_at: DateTime,
    modified_at: DateTime,

    // Embedding
    embedding: [Float],
    embedding_model: String
})

// Requirement Node
(:Requirement {
    rid: String UNIQUE,          // e.g., "REQ-FUNC-001"
    text: String,
    category: String,            // functional|performance|security
    priority: String,            // high|medium|low
    source: String,              // Source document ID

    // Status
    status: String,              // active|deferred|deprecated|satisfied
    created_at: DateTime,
    satisfied_at: DateTime?,

    // Validation
    testable: Boolean,
    acceptance_criteria: String
})

// Code Artifact Node
(:CodeArtifact {
    path: String UNIQUE,         // File path in repository
    filename: String,
    extension: String,
    language: String,            // python|javascript|etc

    // Content tracking
    last_hash: String,           // Git commit hash
    last_modified: DateTime,
    lines_of_code: Integer,
    complexity: Float?,          // Cyclomatic complexity

    // Metadata
    module: String,              // Logical module/package
    artifact_type: String        // source|test|config|build
})
```

#### Governance Nodes
```cypher
// Agent Request Node
(:AgentRequest {
    id: String UNIQUE,
    agent_id: String,
    session_id: String,
    timestamp: DateTime,

    // Request details
    request_type: String,        // APPROVAL|QUERY|VALIDATE|REPORT
    action: String,              // create|modify|delete|read
    target_type: String,
    target_id: String?,

    // Content
    content: String,
    rationale: String,

    // Decision
    status: String,              // pending|approved|rejected|escalated
    response: String,
    response_time: DateTime,
    processing_ms: Integer
})

// Decision Node
(:Decision {
    id: String UNIQUE,
    decision_type: String,       // approval|rejection|deferral
    timestamp: DateTime,

    // Context
    author: String,              // Agent or human ID
    rationale: String,
    confidence: Float,

    // Impact
    impact_level: String,        // low|medium|high|critical
    affected_nodes: [String],

    // Audit
    reversible: Boolean,
    reversed_at: DateTime?,
    reversal_reason: String?
})
```

### Relationship Schemas

```cypher
// Document Hierarchy
(:Architecture)-[:DEFINES {priority: Integer}]->(:Requirement)
(:Design)-[:IMPLEMENTS {version: String}]->(:Architecture)
(:Design)-[:SATISFIES {method: String}]->(:Requirement)
(:CodeArtifact)-[:IMPLEMENTS {verified: Boolean}]->(:Design)
(:CodeArtifact)-[:SATISFIES {test_id: String}]->(:Requirement)

// Evolution Relationships
(:Architecture)-[:SUPERSEDES {date: DateTime, reason: String}]->(:Architecture)
(:Design)-[:DERIVED_FROM {changes: String}]->(:Design)
(:Decision)-[:INVALIDATES {reason: String}]->(:Design|:Architecture)

// Agent Interactions
(:AgentRequest)-[:TARGETS]->(:Architecture|:Design|:CodeArtifact)
(:AgentRequest)-[:REFERENCES {section: String}]->(:Architecture|:Design)
(:AgentRequest)-[:RESULTED_IN]->(:Decision)
(:Decision)-[:APPROVES|:REJECTS]->(:AgentRequest)

// Ownership and Review
(:Person)-[:OWNS {since: Date}]->(:Architecture|:Design)
(:Person)-[:REVIEWED {date: Date, outcome: String}]->(:Architecture|:Design)
(:Person)-[:AUTHORED {timestamp: DateTime}]->(:Decision)
```

### Index Definitions

```cypher
-- Unique Constraints (automatically create indexes)
CREATE CONSTRAINT arch_id_unique IF NOT EXISTS
  FOR (a:Architecture) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT design_id_unique IF NOT EXISTS
  FOR (d:Design) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT req_id_unique IF NOT EXISTS
  FOR (r:Requirement) REQUIRE r.rid IS UNIQUE;

CREATE CONSTRAINT code_path_unique IF NOT EXISTS
  FOR (c:CodeArtifact) REQUIRE c.path IS UNIQUE;

-- Vector Indexes for Semantic Search
CREATE VECTOR INDEX arch_embedding IF NOT EXISTS
  FOR (a:Architecture) ON (a.embedding)
  OPTIONS {
    indexConfig: {
      'vector.dimensions': 768,
      'vector.similarity_function': 'cosine'
    }
  };

CREATE VECTOR INDEX design_embedding IF NOT EXISTS
  FOR (d:Design) ON (d.embedding)
  OPTIONS {
    indexConfig: {
      'vector.dimensions': 768,
      'vector.similarity_function': 'cosine'
    }
  };

-- Composite Indexes for Common Queries
CREATE INDEX arch_status_subsystem IF NOT EXISTS
  FOR (a:Architecture) ON (a.status, a.subsystem);

CREATE INDEX design_status_component IF NOT EXISTS
  FOR (d:Design) ON (d.status, d.component);

CREATE INDEX req_status_priority IF NOT EXISTS
  FOR (r:Requirement) ON (r.status, r.priority);

CREATE INDEX request_agent_time IF NOT EXISTS
  FOR (ar:AgentRequest) ON (ar.agent_id, ar.timestamp);

-- Full-text Search Index
CREATE FULLTEXT INDEX doc_content_search IF NOT EXISTS
  FOR (a:Architecture|d:Design) ON EACH [a.content, d.content];
```

## Interfaces

### Python Driver Interface
```python
from neo4j import GraphDatabase
from typing import List, Dict, Any

class GraphOperations:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    # Transaction Management
    def execute_write(self, query: str, params: Dict) -> Any:
        with self.driver.session() as session:
            return session.execute_write(
                lambda tx: tx.run(query, params).single()
            )

    def execute_read(self, query: str, params: Dict) -> List[Dict]:
        with self.driver.session() as session:
            return session.execute_read(
                lambda tx: tx.run(query, params).data()
            )

    # Bulk Operations
    def batch_insert(self, queries: List[tuple[str, Dict]],
                     batch_size: int = 1000):
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                for i, (query, params) in enumerate(queries):
                    tx.run(query, params)
                    if i % batch_size == 0:
                        tx.commit()
                        tx = session.begin_transaction()
                tx.commit()
```

### Query Templates
```python
# Common query patterns as templates
QUERIES = {
    # Find superseded documents
    "find_superseded": """
        MATCH (new:Architecture)-[:SUPERSEDES]->(old:Architecture)
        WHERE old.id = $doc_id
        RETURN new
    """,

    # Get document with all relationships
    "get_document_graph": """
        MATCH (d:Design {id: $design_id})
        OPTIONAL MATCH (d)-[:IMPLEMENTS]->(a:Architecture)
        OPTIONAL MATCH (d)-[:SATISFIES]->(r:Requirement)
        OPTIONAL MATCH (c:CodeArtifact)-[:IMPLEMENTS]->(d)
        RETURN d, a, collect(DISTINCT r) as requirements,
               collect(DISTINCT c) as code_artifacts
    """,

    # Vector similarity search
    "vector_search": """
        CALL db.index.vector.queryNodes(
            'arch_embedding', $k, $embedding
        ) YIELD node, score
        WHERE score > $threshold
        RETURN node, score
        ORDER BY score DESC
    """,

    # Drift detection
    "detect_drift": """
        MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
        WHERE d.modified_at > a.modified_at
          AND NOT exists((decision:Decision)-[:APPROVES]->
                        (req:AgentRequest)-[:TARGETS]->(d))
        RETURN d.id as design, a.id as architecture,
               d.modified_at as design_modified,
               a.modified_at as arch_modified
    """
}
```

## Configuration

### Connection Configuration
```yaml
# config/neo4j.yaml
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: ${NEO4J_PASSWORD}

  pool:
    max_connection_lifetime: 3600  # seconds
    max_connection_pool_size: 50
    connection_acquisition_timeout: 60  # seconds

  database: neo4j  # default database

  encryption: false  # for local development
```

### Performance Tuning
```yaml
# config/neo4j-performance.yaml
performance:
  # Query settings
  query:
    execution_timeout: 30000  # ms
    result_cache_size: 1000
    planner: COST  # or RULE

  # Memory settings
  memory:
    page_cache_size: 512m
    heap_initial_size: 512m
    heap_max_size: 2g

  # Vector index settings
  vector:
    similarity_threshold: 0.7
    max_neighbors: 100
    ef_construction: 200  # HNSW parameter
```

## Common Operations

### 1. Document Ingestion
```python
def ingest_architecture_doc(doc: Dict) -> str:
    """Create or update an architecture document node"""
    query = """
        MERGE (a:Architecture {id: $id})
        SET a += $properties
        WITH a
        UNWIND $requirements as req_text
        MERGE (r:Requirement {text: req_text})
        MERGE (a)-[:DEFINES]->(r)
        RETURN a.id
    """

    params = {
        "id": doc["id"],
        "properties": {
            "version": doc["version"],
            "title": doc["title"],
            "content": doc["content"],
            "embedding": doc["embedding"],
            "modified_at": datetime.now()
        },
        "requirements": doc.get("requirements", [])
    }

    return graph.execute_write(query, params)
```

### 2. Relationship Creation
```python
def link_design_to_architecture(design_id: str, arch_id: str):
    """Create IMPLEMENTS relationship with validation"""
    query = """
        MATCH (d:Design {id: $design_id})
        MATCH (a:Architecture {id: $arch_id})
        WHERE a.status = 'approved'
        MERGE (d)-[r:IMPLEMENTS {version: a.version}]->(a)
        SET r.created_at = datetime()
        RETURN d.id, a.id, r.version
    """

    return graph.execute_write(query, {
        "design_id": design_id,
        "arch_id": arch_id
    })
```

### 3. Drift Detection Query
```python
def find_drifted_designs(subsystem: str = None) -> List[Dict]:
    """Find designs that have drifted from architecture"""
    query = """
        MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
        WHERE d.modified_at > a.modified_at
        AND ($subsystem IS NULL OR a.subsystem = $subsystem)
        AND NOT exists((:Decision)-[:APPROVES]->
                      (:AgentRequest)-[:TARGETS]->(d))
        RETURN d.id as design_id,
               a.id as arch_id,
               duration.between(a.modified_at, d.modified_at) as drift_duration,
               d.owners as design_owners
        ORDER BY drift_duration DESC
    """

    return graph.execute_read(query, {"subsystem": subsystem})
```

### 4. Impact Analysis
```python
def analyze_change_impact(node_id: str) -> Dict:
    """Analyze what would be affected by changing a node"""
    query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)<-[:IMPLEMENTS]-(impl)
        OPTIONAL MATCH (n)<-[:SATISFIES]-(sat)
        OPTIONAL MATCH (n)<-[:REFERENCES]-(ref)
        OPTIONAL MATCH (n)-[:SUPERSEDES]->(old)
        RETURN n,
               collect(DISTINCT impl) as implementations,
               collect(DISTINCT sat) as satisfiers,
               collect(DISTINCT ref) as references,
               collect(DISTINCT old) as superseded
    """

    result = graph.execute_read(query, {"node_id": node_id})
    return {
        "direct_implementations": len(result[0]["implementations"]),
        "requirement_satisfiers": len(result[0]["satisfiers"]),
        "agent_references": len(result[0]["references"]),
        "superseded_versions": len(result[0]["superseded"])
    }
```

### 5. Graph Health Check
```python
def check_graph_health() -> Dict:
    """Verify graph integrity"""
    checks = {}

    # Check for orphaned requirements
    orphan_query = """
        MATCH (r:Requirement)
        WHERE NOT exists((:Architecture)-[:DEFINES]->(r))
        RETURN count(r) as orphaned_requirements
    """
    checks["orphaned_requirements"] = graph.execute_read(orphan_query, {})[0]

    # Check for circular dependencies
    circular_query = """
        MATCH p=(n)-[:SUPERSEDES*]->(n)
        RETURN count(p) as circular_supersedes
    """
    checks["circular_supersedes"] = graph.execute_read(circular_query, {})[0]

    # Check for missing embeddings
    missing_embed_query = """
        MATCH (n:Architecture|Design)
        WHERE n.embedding IS NULL
        RETURN count(n) as missing_embeddings
    """
    checks["missing_embeddings"] = graph.execute_read(missing_embed_query, {})[0]

    return checks
```

## Troubleshooting

### Common Issues

#### "Index not found" Error
- **Cause**: Vector index not created or wrong name
- **Solution**: Run index creation scripts from schema section
```cypher
SHOW INDEXES;  -- List all indexes
```

#### Slow Query Performance
- **Cause**: Missing indexes or inefficient query patterns
- **Solution**: Use `EXPLAIN` and `PROFILE` to analyze
```cypher
PROFILE MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
WHERE d.status = 'approved'
RETURN d, a
```

#### Transaction Deadlocks
- **Cause**: Concurrent writes to same nodes
- **Solution**: Implement retry logic with exponential backoff
```python
from neo4j.exceptions import TransientError
import time

def retry_transaction(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except TransientError:
            time.sleep(2 ** i)  # Exponential backoff
    raise
```

#### Memory Issues
- **Cause**: Large result sets or inefficient queries
- **Solution**: Use pagination and streaming
```cypher
MATCH (n:Architecture)
RETURN n
SKIP $skip LIMIT $limit
```

### Performance Monitoring
```cypher
-- Query execution statistics
CALL dbms.listQueries() YIELD query, elapsedTimeMillis, cpuTimeMillis
WHERE elapsedTimeMillis > 1000
RETURN query, elapsedTimeMillis;

-- Database statistics
CALL apoc.meta.stats() YIELD nodeCount, relCount, indexCount;

-- Index usage
CALL db.indexes() YIELD name, state, populationPercent;
```

## References

- **Neo4j Documentation**: https://neo4j.com/docs/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/current/
- **Python Driver**: https://neo4j.com/docs/python-manual/current/
- **APOC Procedures**: https://neo4j.com/labs/apoc/
- **Graph Data Science**: https://neo4j.com/docs/graph-data-science/current/
- **Architecture Document**: [`docs/architecture.md`](../architecture.md)