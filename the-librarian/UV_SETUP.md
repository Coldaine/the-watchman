# UV Virtual Environment Setup

This project uses **UV** for fast, reliable Python dependency management and virtual environment handling.

## What is UV?

UV is a modern, blazing-fast Python package installer and resolver written in Rust. It's designed to be a drop-in replacement for pip and pip-tools, offering:
- **10-100x faster** than pip
- **Deterministic** dependency resolution
- **Built-in** virtual environment management
- **Compatible** with existing Python tools

## Installation

If you don't have UV installed:

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Project Setup

### 1. Create Virtual Environment

```bash
uv venv
```

This creates a `.venv` directory with an isolated Python environment.

### 2. Activate Virtual Environment

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies

Install all dependencies including development tools:

```bash
uv sync --all-extras
```

Or install only production dependencies:

```bash
uv sync
```

## Common UV Commands

### Adding Dependencies

Add a new production dependency:
```bash
uv add <package-name>
```

Add a development dependency:
```bash
uv add --dev <package-name>
```

### Running Commands

Run a command in the virtual environment without activating:
```bash
uv run <command>
```

Examples:
```bash
uv run uvicorn src.main:app --reload
uv run pytest
uv run python verify_processing.py
```

### Updating Dependencies

Update all dependencies to latest compatible versions:
```bash
uv sync --upgrade
```

Update a specific package:
```bash
uv add <package-name> --upgrade
```

### Locking Dependencies

UV automatically maintains a lock file (`uv.lock`) that pins exact versions for reproducible installations.

To regenerate the lock file:
```bash
uv lock
```

## Project Dependencies

### Production Dependencies
- **neo4j** - Graph database driver
- **fastapi** - Modern web framework
- **uvicorn** - ASGI server
- **pydantic** - Data validation
- **ollama** - Local embedding generation
- **numpy** - Numerical operations

### Development Dependencies (via `--all-extras`)
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage
- **mypy** - Type checking
- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting

## Environment Variables

Copy the template and configure:
```bash
cp .env.template .env
```

Edit `.env` with your settings:
- Neo4j connection details
- Ollama configuration
- API settings

## Running the Application

### Development Mode (with auto-reload)
```bash
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### Production Mode
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py

# Run tests matching a pattern
uv run pytest -k "test_validation"
```

## Code Quality Tools

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/ tests/
```

## Troubleshooting

### UV Command Not Found
Ensure UV is installed and in your PATH. Restart your terminal after installation.

### Virtual Environment Not Activating
On Windows, you may need to adjust PowerShell execution policy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Dependency Conflicts
UV's resolver is very strict. If you encounter conflicts:
```bash
uv lock --upgrade
uv sync --reinstall
```

### Clear UV Cache
```bash
uv cache clean
```

## Migration from pip/requirements.txt

The old `requirements.txt` has been migrated to `pyproject.toml`. All dependencies are now managed through UV.

To add dependencies that were in requirements.txt:
```bash
uv add <package-name>@<version>
```

## Benefits of UV

1. **Speed**: 10-100x faster than pip
2. **Reproducibility**: Lock file ensures identical installations
3. **Simplicity**: One tool for venv, pip, and pip-tools
4. **Modern**: Built with Rust, actively maintained
5. **Compatible**: Works with existing Python ecosystem

## Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub](https://github.com/astral-sh/uv)
- [pyproject.toml specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/)
