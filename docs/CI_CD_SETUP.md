# CI/CD and Code Quality Setup

This document explains the comprehensive CI/CD and code quality automation infrastructure for The Watchman project.

## Table of Contents

- [Overview](#overview)
- [CI/CD Pipeline](#cicd-pipeline)
- [Code Quality Tools](#code-quality-tools)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Setup Instructions](#setup-instructions)
- [Running Locally](#running-locally)
- [Troubleshooting](#troubleshooting)

## Overview

The Watchman project uses modern Python tooling to ensure code quality, consistency, and correctness:

- **GitHub Actions** for automated CI/CD
- **Black** for code formatting
- **Ruff** for fast linting
- **isort** for import sorting
- **mypy** for static type checking
- **Bandit** for security scanning
- **pytest** with coverage reporting
- **pre-commit** for local enforcement

## CI/CD Pipeline

### Workflow Structure

The CI/CD pipeline (`.github/workflows/ci.yml`) consists of four parallel jobs:

#### 1. Code Quality Checks
Runs on every push and pull request to ensure code standards:
- **Black**: Code formatting check (100 char line length)
- **Ruff**: Fast Python linting with comprehensive rules
- **mypy**: Static type checking (gradual typing approach)
- **isort**: Import statement ordering

#### 2. Test Suite
Runs unit and service tests with real Neo4j:
- **Unit Tests**: Fast, isolated component tests
- **Service Tests**: Integration tests with Neo4j (testcontainers)
- **Coverage Reports**: Uploaded to Codecov (when configured)
- Requires: Neo4j service container, Tesseract OCR

#### 3. Docker Build
Validates containerization:
- Builds Docker image without pushing
- Validates docker-compose configuration
- Uses layer caching for speed

#### 4. Security Scanning
Identifies security vulnerabilities:
- **Bandit**: Scans for common security issues
- **Safety**: Checks dependencies for known vulnerabilities
- Reports uploaded as artifacts

### Trigger Conditions

```yaml
on:
  push:
    branches: [ main, develop, 'claude/**' ]
  pull_request:
    branches: [ main, develop ]
```

## Code Quality Tools

### Black - Code Formatting

**Configuration**: `pyproject.toml`

```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

**Usage**:
```bash
# Format all code
black app/ domains/ tests/ scripts/

# Check formatting without changes
black --check --diff app/
```

### Ruff - Fast Linting

**Configuration**: `pyproject.toml`

Enabled rule sets:
- `E/W`: pycodestyle (PEP 8)
- `F`: pyflakes (undefined names, unused imports)
- `I`: isort (import ordering)
- `B`: flake8-bugbear (common bugs)
- `C4`: flake8-comprehensions (better comprehensions)
- `UP`: pyupgrade (modern Python syntax)
- `ARG`: unused arguments
- `SIM`: code simplification
- `PL`: pylint rules

**Usage**:
```bash
# Lint with auto-fix
ruff check --fix app/ domains/ tests/ scripts/

# Check only (no fixes)
ruff check app/
```

### isort - Import Sorting

**Configuration**: `pyproject.toml`

Compatible with Black profile.

**Usage**:
```bash
# Sort imports
isort app/ domains/ tests/ scripts/

# Check only
isort --check-only --diff app/
```

### mypy - Type Checking

**Configuration**: `pyproject.toml`

Gradual typing approach:
- Permissive initially (`disallow_untyped_defs = false`)
- Will tighten over time
- Ignores missing imports for third-party libraries

**Usage**:
```bash
# Type check all code
mypy app/ domains/ scripts/

# Type check specific file
mypy app/api/health.py
```

### Bandit - Security Linting

**Configuration**: `pyproject.toml`

Scans for common security issues:
- SQL injection
- Shell injection
- Insecure random usage
- Hard-coded credentials
- Insecure cryptography

**Usage**:
```bash
# Scan for security issues
bandit -r app/ domains/ scripts/

# Generate JSON report
bandit -r app/ -f json -o bandit-report.json
```

### Safety - Dependency Scanning

Checks dependencies against known vulnerability databases.

**Usage**:
```bash
# Check all dependencies
safety check

# JSON output
safety check --json
```

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` to catch issues early.

### Configuration

**File**: `.pre-commit-config.yaml`

**Hooks**:
1. **General file checks** (trailing whitespace, EOF, YAML/JSON validity)
2. **Black** - Code formatting
3. **isort** - Import sorting
4. **Ruff** - Linting with auto-fix
5. **mypy** - Type checking
6. **Bandit** - Security linting
7. **hadolint** - Dockerfile linting
8. **markdownlint** - Markdown formatting
9. **yamllint** - YAML linting

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Optional: Run on all files manually
pre-commit run --all-files
```

### Usage

Hooks run automatically on `git commit`. To bypass (not recommended):

```bash
git commit --no-verify -m "message"
```

## Setup Instructions

### Local Development Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/Coldaine/the-watchman.git
   cd the-watchman
   ```

2. **Create virtual environment**:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Initialize Neo4j schema** (with Docker Compose):
   ```bash
   docker compose up -d neo4j
   python scripts/init_schema.py
   ```

### CI/CD Setup (GitHub)

1. **Enable GitHub Actions**:
   - Actions are automatically enabled for new repositories
   - Check: Repository → Settings → Actions → Allow all actions

2. **Add secrets** (optional):
   - `CODECOV_TOKEN`: For coverage reporting to Codecov
   - Navigate to: Repository → Settings → Secrets → Actions

3. **Branch protection** (recommended):
   - Navigate to: Repository → Settings → Branches
   - Add rule for `main` branch:
     - Require status checks to pass before merging
     - Required checks: `Code Quality Checks`, `Run Tests`
     - Require branches to be up to date

## Running Locally

### Run All Quality Checks

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Or run individual tools
black --check app/ domains/ tests/ scripts/
ruff check app/ domains/ tests/ scripts/
mypy app/ domains/ scripts/
isort --check-only app/ domains/ tests/ scripts/
bandit -r app/ domains/ scripts/
```

### Run Tests

```bash
# Run all tests with coverage
pytest

# Run specific test categories
pytest tests/unit -v
pytest tests/service -v
pytest -m "not slow"

# Run with detailed coverage
pytest --cov=app --cov=domains --cov-report=html
# Open htmlcov/index.html in browser
```

### Format Code

```bash
# Auto-format with Black
black app/ domains/ tests/ scripts/

# Sort imports
isort app/ domains/ tests/ scripts/

# Auto-fix linting issues
ruff check --fix app/ domains/ tests/ scripts/
```

### Docker Build

```bash
# Build image
docker build -t the-watchman:local .

# Run full stack
docker compose up

# Run tests in container
docker compose run --rm api pytest
```

## Troubleshooting

### Pre-commit Hook Failures

**Issue**: Hook fails on commit
```bash
# See which hook failed
git commit -m "message"

# Fix the issue manually or let tools auto-fix
black app/
isort app/
ruff check --fix app/

# Retry commit
git commit -m "message"
```

**Issue**: Want to update hook versions
```bash
pre-commit autoupdate
pre-commit run --all-files
```

### Type Checking Errors

**Issue**: mypy reports errors in third-party libraries
- These are ignored by default with `ignore_missing_imports = true`
- Install type stubs if available: `pip install types-<library>`

**Issue**: mypy too strict for new code
- Add `# type: ignore` comment for specific line
- Or exclude file in `pyproject.toml`:
  ```toml
  [[tool.mypy.overrides]]
  module = "app.new_module"
  disallow_untyped_defs = false
  ```

### Test Failures

**Issue**: Neo4j connection errors in tests
```bash
# Check Neo4j is running
docker compose ps

# View Neo4j logs
docker compose logs neo4j

# Restart Neo4j
docker compose restart neo4j
```

**Issue**: Tesseract not found
```bash
# Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# Mac
brew install tesseract

# Verify installation
tesseract --version
```

### CI Pipeline Failures

**Issue**: GitHub Actions workflow fails

1. **Check workflow run**:
   - Repository → Actions → Click failed workflow
   - Expand failed step to see error

2. **Common issues**:
   - **Dependency installation**: Update `requirements.txt`
   - **Test failures**: Run `pytest` locally first
   - **Linting errors**: Run `ruff check` locally
   - **Formatting errors**: Run `black --check` locally

3. **Reproduce locally**:
   ```bash
   # Run same commands as CI
   black --check --diff app/ domains/ tests/ scripts/
   ruff check app/ domains/ tests/ scripts/
   mypy app/ domains/ scripts/
   pytest -v
   ```

### Coverage Issues

**Issue**: Coverage too low

1. **Identify untested code**:
   ```bash
   pytest --cov=app --cov=domains --cov-report=term-missing
   ```

2. **Generate HTML report**:
   ```bash
   pytest --cov=app --cov=domains --cov-report=html
   open htmlcov/index.html
   ```

3. **Write tests for missing coverage**:
   - Focus on critical paths first
   - Aim for >80% coverage on core modules

## Future Enhancements

Planned improvements to the CI/CD pipeline:

1. **Automated releases**:
   - Semantic versioning
   - Changelog generation
   - Docker image publishing

2. **Performance testing**:
   - Load testing with locust
   - Memory profiling
   - Query performance benchmarks

3. **Integration testing**:
   - End-to-end workflow tests
   - Multi-container orchestration tests

4. **Deployment automation**:
   - Staging environment deployment
   - Production deployment with approval gates
   - Rollback capabilities

5. **Advanced security**:
   - Container image scanning (Trivy)
   - SAST/DAST scanning
   - License compliance checking

## References

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Bandit Documentation](https://bandit.readthedocs.io/)

## Support

For issues or questions:
- Check existing issues: https://github.com/Coldaine/the-watchman/issues
- Create new issue with `ci/cd` label
- Reference this document when reporting CI/CD problems
