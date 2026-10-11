# Agent 1: Graph Operations Specialist

## Your Mission
You are building the Neo4j graph operations module for the Librarian Agent system. This module handles all database interactions, vector operations, and graph queries.

## Context
You are working in parallel with:
- Agent 2: Building document processing (will produce embeddings for you to store)
- Agent 3: Building validation engine (will use your queries)

## Required Reading
1. `docs/architecture.md` - Focus on Data Model section (lines 147-262)
2. `docs/subdomains/graph-operations.md` - Your primary specification
3. `docs/ADR/001-technology-stack-and-architecture-decisions.md` - Neo4j configuration

## What to Build

### 1. Connection Management (`src/graph/connection.py`)
```python
from neo4j import AsyncGraphDatabase
from contextlib import asynccontextmanager

class GraphConnection:
    def __init__(self, uri: str, user: str, password: str):
        # Connection pool with proper settings
        # Health check method
        # Async context manager for transactions
```

### 2. Schema Creation (`src/graph/schema.py`)
```python
# Create all node types from docs/architecture.md:
# - Architecture, Design, Requirement, CodeArtifact
# - Decision, AgentRequest
# All relationships: IMPLEMENTS, SATISFIES, DEFINES, etc.

async def create_schema(driver):
    # Create constraints
    # Create vector indexes (768 dimensions, cosine similarity)
    # Use exact Cypher from docs lines 234-260
```

### 3. Core Operations (`src/graph/operations.py`)
```python
class GraphOperations:
    async def create_node(self, label: str, properties: dict) -> str:
        # Return node ID

    async def create_relationship(self, from_id: str, rel_type: str, to_id: str):
        # Create with properties

    async def update_node(self, node_id: str, properties: dict):
        # Partial update

    async def get_node(self, node_id: str) -> dict:
        # Fetch with relationships
```

### 4. Vector Operations (`src/graph/vector_ops.py`)
```python
class VectorOperations:
    async def store_embedding(self, node_id: str, embedding: List[float]):
        # Store 768-dim vector on node

    async def vector_search(self, query_embedding: List[float], limit: int = 10):
        # Use Neo4j vector index for similarity search
        # Return nodes with similarity scores

    async def hybrid_search(self, query_embedding: List[float], filters: dict):
        # Combine vector similarity with graph traversal
```

### 5. Query Templates (`src/graph/queries.py`)
```python
# All queries from docs/architecture.md lines 469-501
FIND_UNCOVERED_REQUIREMENTS = """
MATCH (a:Architecture)-[:DEFINES]->(req:Requirement)
WHERE NOT exists((req)<-[:SATISFIES]-(:Design))
  AND req.status = 'active'
RETURN req.rid, req.text, req.priority, a.id as source
ORDER BY req.priority DESC
"""

DETECT_DESIGN_DRIFT = """
MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
WHERE d.version > a.version
  AND NOT exists((:Decision)-[:SUPERSEDES]->(d))
RETURN d.id, d.version, a.id, a.version
"""

# Add all other queries from spec
```

### 6. Configuration (`src/graph/config.py`)
```python
from pydantic import BaseSettings

class GraphConfig(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str
    max_connection_pool_size: int = 50
    connection_timeout: int = 30

    class Config:
        env_file = ".env"
```

## Interface Contract for Other Agents

Create `src/graph/__init__.py`:
```python
# Export these for other agents to use
from .connection import GraphConnection
from .operations import GraphOperations
from .vector_ops import VectorOperations
from .queries import FIND_UNCOVERED_REQUIREMENTS, DETECT_DESIGN_DRIFT

__all__ = [
    'GraphConnection',
    'GraphOperations',
    'VectorOperations',
    'FIND_UNCOVERED_REQUIREMENTS',
    'DETECT_DESIGN_DRIFT'
]
```

## Testing Requirements

Create `tests/test_graph.py`:
1. Test connection to Neo4j (use real instance)
2. Test schema creation
3. Test node/relationship CRUD
4. Test vector storage and search
5. Test each query template

## Success Criteria

1. **Real Neo4j Connection**: Actually connects to Neo4j at localhost:7687
2. **Schema Created**: All node types and indexes exist in database
3. **Vector Search Works**: Can store and retrieve 768-dim embeddings
4. **Queries Execute**: All query templates run without errors
5. **Async Operations**: All operations are properly async

## Dependencies to Add to requirements.txt
```
neo4j==5.14.0
numpy==1.24.3
```

## Coordination File

Write your status to `coordination.json`:
```json
{
  "agent1_graph": {
    "status": "working|complete",
    "interfaces_ready": ["GraphConnection", "GraphOperations"],
    "blockers": []
  }
}
```

## Start Now
Begin by reading the documentation, then create the connection module. Test with a real Neo4j instance. Make sure vector operations actually work with 768-dimensional embeddings.