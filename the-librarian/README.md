# The Librarian

AI-powered knowledge graph and document processing system with RAG (Retrieval-Augmented Generation) capabilities.

## Overview

The Librarian is a comprehensive system for managing, processing, and querying documents using:
- **Neo4j** knowledge graph for storing relationships and metadata
- **Ollama** for local embeddings generation
- **FastAPI** for REST API
- **Validation Engine** for drift detection and audit trails
- **Processing Pipeline** for document chunking and embedding

## Quick Start

### Prerequisites
- Python 3.10+
- UV package manager
- Neo4j database instance
- Ollama (for embeddings)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Coldaine/the-Librarian.git
cd the-Librarian
```

2. Set up UV virtual environment:
```bash
uv venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/Mac
```

3. Install dependencies:
```bash
uv sync --all-extras
```

4. Configure environment:
```bash
cp .env.template .env
# Edit .env with your configuration
```

5. Start the server:
```bash
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

## Documentation

See the following guides:
- [Graph Setup Guide](docs/graph/SETUP.md)
- [API Documentation](docs/api/QUICK_START.md)
- [Integration Architecture](docs/integration_architecture.md)

## Development

### Running Tests
```bash
uv run pytest
```

### Code Quality
```bash
uv run black src/ tests/
uv run isort src/ tests/
uv run mypy src/
```

## License

[Add your license here]
