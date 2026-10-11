# Graph Module Quick Start Guide

## Prerequisites

1. Neo4j Desktop installed
2. Python 3.11+
3. Dependencies installed (already done)

## Setup Steps

### 1. Start Neo4j

- Open Neo4j Desktop
- Create new database: "librarian"
- Set password: librarian-pass
- Start database on bolt://localhost:7687

### 2. Configure Environment

```bash
cp .env.template .env
# Edit .env if needed (defaults should work)
```

### 3. Test the Module

```bash
cd E:\_projectsGithub\the-Librarian
pytest tests/test_graph.py -v
```

## Usage Example

```python
import asyncio
from src.graph import Neo4jConnection, SchemaManager, GraphOperations

async def main():
    # Connect
    conn = Neo4jConnection()
    await conn.connect()
    
    # Create schema
    schema = SchemaManager(conn)
    await schema.create_all_indexes()
    
    # Create a node
    ops = GraphOperations(conn)
    arch_id = await ops.create_node("Architecture", {
        "id": "arch-001",
        "title": "Test Architecture",
        "version": "1.0.0",
        "status": "draft",
        "subsystem": "test"
    })
    
    print(f"Created node: {arch_id}")
    
    # Cleanup
    await conn.close()

asyncio.run(main())
```

## What's Included

- **Connection**: Async Neo4j driver with pooling
- **Schema**: All node types and vector indexes
- **CRUD**: Create, read, update, delete operations
- **Vectors**: 768-dim embedding storage and search
- **Queries**: Drift detection and validation

## Module Structure

```
src/graph/
├── config.py          # Pydantic configuration
├── connection.py      # Neo4j connection management
├── schema.py          # Node types and indexes
├── operations.py      # CRUD operations
├── vector_ops.py      # Vector search
├── queries.py         # Predefined queries
└── __init__.py        # Exports

tests/
└── test_graph.py      # Test suite
```

## Next Steps After Testing

1. Integrate Ollama for embeddings
2. Build FastAPI endpoints
3. Create document ingestion pipeline
4. Implement agent approval workflow

## Troubleshooting

**Connection failed**: Verify Neo4j is running on bolt://localhost:7687
**Test failures**: Check password matches .env file
**Import errors**: Ensure you're in project root directory
