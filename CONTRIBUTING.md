# Contributing to The Watchman

Thank you for your interest in contributing to The Watchman!

## Current Status

**⚠️ This project is in early development** - the initial implementation is untested and incomplete.
**⚠️ This project has a complete MVP core, but is still in active development.**

The core data collection domains (Visual Timeline, System Graph, Event Tracking) are implemented. The remaining work for the full MVP is focused on the Agent Interface (query routing) and MCP Registry (control). The implementation is not yet covered by a full automated test suite.

## How to Help

### 1. Code Review

The most valuable contribution right now is **reviewing the initial implementation**:

- Check architecture and design decisions
- Identify bugs and issues
- Suggest improvements
- Point out security concerns
- Help with Docker/Neo4j configuration

### 2. Testing

Help verify the code actually works:

- Try running `docker-compose up`
- Test screenshot capture
- Test OCR processing
- Test project scanning
- Test Docker scanning
- Report any issues found

### 3. Documentation

- Improve setup instructions
- Add troubleshooting guides
- Create example queries
- Document edge cases

### 4. Implementation

Missing pieces that need work:

- MCP Registry YAML parser
- Query routing and intent classification
- LLM integration (Ollama + OpenRouter)
- **Agent Interface**: Query routing, intent classification, and LLM integration.
- **MCP Registry**: YAML registry parsing and Docker Compose control logic.
- Integration tests
- Docker event watcher
- Health check monitoring

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Coldaine/the-watchman.git
cd the-watchman

# Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Start services
docker-compose up -d

# Initialize schema
docker-compose exec api python scripts/init_schema.py
```

## Testing Before PR

Before submitting a PR, please:

1. ✅ Test your changes locally
2. ✅ Ensure Docker containers build
3. ✅ Verify no syntax errors
4. ✅ Update documentation if needed
5. ✅ Run any existing tests (once we have them!)

## Code Style

- Python: Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Use meaningful variable names
- Keep functions focused and small

## Commit Messages

Follow the format:
```
Brief description of change

Longer explanation if needed:
- What changed
- Why it changed
- Any breaking changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Your Name <your.email@example.com>
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Test thoroughly
4. Create PR with detailed description
5. Address review feedback
6. Wait for approval and merge

## Questions?

Open an issue or start a discussion!

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
