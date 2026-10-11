# .gitignore Guide

## Overview
This document explains what files are excluded from version control in the Librarian Agent project and why. Understanding `.gitignore` is critical for maintaining a clean repository and avoiding security issues.

## Core Principle

**Commit code, not artifacts. Commit configuration structure, not secrets.**

The `.gitignore` file prevents:
1. **Generated files** that can be rebuilt from source
2. **Secret data** that would compromise security
3. **Large binary files** that bloat repository size
4. **Local environment files** that vary per developer
5. **Temporary files** that have no lasting value

---

## Category Breakdown

### 1. Python Artifacts

#### What's Excluded:
```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
```

#### Why:
- **`__pycache__/`**: Python bytecode cache, regenerated automatically
- **`*.pyc`**: Compiled Python files, machine-specific
- **`dist/` and `build/`**: Package build artifacts, reproducible from source
- **`*.egg-info/`**: Package metadata, generated during installation

**Impact if committed**:
- Repository bloat (MB of unnecessary files)
- Merge conflicts on every Python version change
- Cross-platform compatibility issues (bytecode isn't portable)

---

### 2. Virtual Environments

#### What's Excluded:
```gitignore
venv/
env/
.venv/
ENV/
```

#### Why:
Virtual environments contain:
- Installed packages (can be recreated from `requirements.txt`)
- Python interpreter symlinks (machine-specific paths)
- Binary dependencies (OS-specific)

**Size impact**: Virtual environments can be 100-500 MB
**Recreateable**: `python -m venv venv && pip install -r requirements.txt`

**What IS committed**: `requirements.txt` (the recipe, not the ingredients)

---

### 3. Environment Variables and Secrets

#### What's Excluded:
```gitignore
.env
.env.local
config/secrets.yml
config/credentials.json
*.pem
*.key
```

#### Why:
**CRITICAL SECURITY**: These files contain:
- Database passwords (`NEO4J_PASSWORD`)
- API keys (`OPENROUTER_API_KEY`)
- SSL certificates and private keys
- OAuth tokens
- Connection strings with credentials

**Impact if committed**:
- 🔴 **Security breach**: Anyone with repo access sees secrets
- 🔴 **Git history**: Even if deleted later, secrets remain in history
- 🔴 **Compliance violation**: PII/secrets in version control

**What IS committed**:
- `.env.template` (structure with placeholder values)
- `config/schema.yml` (configuration schema, no actual values)

**Example template**:
```bash
# .env.template
NEO4J_PASSWORD=your-secure-password-here
OLLAMA_HOST=http://localhost:11434
LOG_LEVEL=INFO
```

---

### 4. Neo4j Database Files

#### What's Excluded:
```gitignore
neo4j/data/
neo4j/logs/
neo4j/plugins/
*.dump
```

#### Why:
- **`neo4j/data/`**: Binary database files, machine-specific format
- **`neo4j/logs/`**: Runtime logs, contain timestamps and debugging info
- **`*.dump`**: Database backups (can be multi-GB)

**Size impact**: Neo4j data directory can grow to GB/TB depending on usage
**Recreateable**: Database schema is in `src/init_db.py`, data can be re-ingested

**What IS committed**:
- `neo4j/conf/neo4j.conf.template` (configuration template)
- `src/schema/` (Cypher scripts defining schema)
- `tests/fixtures/` (small test data)

**Why not commit data?**
- Binary format (not diffable, not reviewable)
- Massive size (slows clone/pull)
- Contains runtime state (not source code)
- Security: may contain user data or PII

---

### 5. Ollama Models

#### What's Excluded:
```gitignore
ollama/models/
ollama/blobs/
```

#### Why:
**Size**: Embedding models are 100MB - 10GB each
- `nomic-embed-text`: ~275 MB
- `llama3`: ~4.7 GB
- `mistral`: ~4.1 GB

**Downloadable**: `ollama pull nomic-embed-text` fetches from registry
**Not source code**: Binary model weights, not modifiable

**Impact if committed**:
- Repository becomes multi-GB
- Clone times go from seconds to hours
- GitHub has 100 MB file size limit (push will fail)

**Alternative**: Document required models in README:
```bash
ollama pull nomic-embed-text
```

---

### 6. IDE and Editor Files

#### What's Excluded:
```gitignore
.vscode/
.idea/
*.sublime-workspace
```

#### Why:
- **Personal preference**: Each developer uses different IDE
- **Machine-specific paths**: Workspace files contain absolute paths
- **Frequent changes**: Workspace state changes constantly (not meaningful)

**Exceptions** (what IS committed):
```gitignore
!.vscode/settings.json
!.vscode/launch.json
```
Shared team settings for consistent debugging configuration.

---

### 7. Logs and Temporary Files

#### What's Excluded:
```gitignore
logs/
*.log
*.tmp
.cache/
```

#### Why:
- **Runtime artifacts**: Generated during execution, not source
- **High churn**: Change constantly, pollute git history
- **Size**: Log files can grow to GB in production
- **Privacy**: Logs may contain user data, stack traces, secrets

**What IS committed**:
- Log configuration: `config/logging.yml`
- Log format specification: `src/logging_config.py`

---

### 8. Test and Coverage Reports

#### What's Excluded:
```gitignore
htmlcov/
.coverage
.pytest_cache/
test-results/
*.prof
```

#### Why:
- **Generated reports**: Created by test runners, reproducible
- **Machine-specific**: Paths and timestamps vary per run
- **Size**: HTML coverage reports can be 10+ MB

**What IS committed**:
- Test source code: `tests/`
- Test configuration: `pytest.ini`, `.coveragerc`
- CI configuration: `.github/workflows/test.yml`

**How to regenerate**:
```bash
pytest --cov=src --cov-report=html
# Creates htmlcov/ (not committed)
```

---

### 9. Docker Volumes and State

#### What's Excluded:
```gitignore
docker-volumes/
docker-compose.override.yml
```

#### Why:
- **`docker-volumes/`**: Persistent storage for containers (DB data, logs)
- **`docker-compose.override.yml`**: Personal local overrides

**What IS committed**:
- `docker-compose.yml` (base configuration)
- `Dockerfile` (image build instructions)
- `.dockerignore` (files to exclude from image)

---

### 10. Application-Specific Data

#### What's Excluded:
```gitignore
backups/
data/
embeddings_cache/
audit_logs/
```

#### Why:
- **`backups/`**: Database dumps, potentially GB-sized
- **`data/`**: Runtime data storage (document processing, temp files)
- **`embeddings_cache/`**: Pre-computed embeddings, regenerable
- **`audit_logs/`**: Application audit trail (production goes to external storage)

**Exceptions**:
```gitignore
!tests/fixtures/
```
Small test data IS committed for reproducible tests.

---

### 11. OS-Specific Files

#### What's Excluded:
```gitignore
.DS_Store       # macOS
Thumbs.db       # Windows
desktop.ini     # Windows
```

#### Why:
- **OS artifacts**: Not related to project code
- **Cross-platform noise**: Different OS generates different files
- **No value**: Contain UI metadata (icon positions, folder views)

---

### 12. Personal Notes and Experiments

#### What's Excluded:
```gitignore
NOTES.md
TODO.local.md
scratch/
experiments/
playground/
```

#### Why:
- **Personal workflow**: Individual developer notes
- **Unfinished work**: Experimental code not ready for review
- **Context-free**: Notes only make sense to author

**What IS committed**:
- Project-wide TODO: `docs/TODO.md` (coordinated tasks)
- Architecture notes: `docs/ADR/` (decided, documented)

---

## What Should NEVER Be in .gitignore

### 1. Source Code
```
❌ src/
❌ *.py
```
**Why**: Source code is the reason the repository exists!

### 2. Configuration Templates
```
❌ .env.template
❌ config/*.example.yml
```
**Why**: Templates show structure without secrets. Developers need these.

### 3. Documentation
```
❌ docs/
❌ README.md
```
**Why**: Documentation is critical for onboarding and understanding.

### 4. Test Code
```
❌ tests/
```
**Why**: Tests ARE source code. They verify correctness.

### 5. Dependency Manifests
```
❌ requirements.txt
❌ pyproject.toml
❌ package.json
```
**Why**: These define what to install. Needed to recreate environment.

### 6. CI/CD Configuration
```
❌ .github/workflows/
```
**Why**: Defines how to build, test, deploy. Critical infrastructure.

---

## How to Check if Something Should Be Ignored

Ask these questions:

1. **Can it be regenerated from source?**
   - YES → Ignore it (e.g., `__pycache__`, `htmlcov/`)
   - NO → Consider committing

2. **Does it contain secrets?**
   - YES → MUST ignore (e.g., `.env`, `*.key`)
   - NO → Safe to evaluate

3. **Is it larger than 10 MB?**
   - YES → Probably should ignore (e.g., models, data)
   - NO → Size not a concern

4. **Is it machine-specific?**
   - YES → Ignore (e.g., `venv/`, `.vscode/`)
   - NO → May be shareable

5. **Is it source code or documentation?**
   - YES → Commit it
   - NO → Probably ignore

---

## Common Mistakes

### ❌ Committing .env file
```bash
git add .env  # NEVER DO THIS
```
**Fix**:
```bash
git rm --cached .env
echo ".env" >> .gitignore
git commit -m "Remove .env from tracking"
```

### ❌ Ignoring all YAML files
```gitignore
*.yml  # TOO BROAD
```
**Better**:
```gitignore
config/local.yml
config/secrets.yml
```

### ❌ Committing database dumps
```bash
git add neo4j/backup.dump  # 2GB file
git push  # FAILS (file too large)
```
**Fix**: Use `.gitignore` and external storage (S3, Dropbox)

---

## Verification Commands

### Check what's being ignored:
```bash
git status --ignored
```

### Test if file would be ignored:
```bash
git check-ignore -v path/to/file
```

### Find large files in repo:
```bash
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '/^blob/ {print substr($0,6)}' |
  sort --numeric-sort --key=2 |
  tail -20
```

### Remove accidentally committed file:
```bash
git rm --cached path/to/file
git commit -m "Remove file from tracking"
```

---

## .gitignore Hierarchy

Git checks ignore rules in this order:
1. `.gitignore` in current directory
2. `.gitignore` in parent directories
3. `.git/info/exclude` (local, not shared)
4. `~/.gitconfig` (global, all repos)

**Project structure**:
```
.gitignore              # Root rules (most restrictive)
src/.gitignore          # Source-specific rules (if needed)
tests/.gitignore        # Test-specific rules (if needed)
```

---

## Template Management

### Creating .env from template:
```bash
cp .env.template .env
# Edit .env with real values (NOT committed)
```

### Validating template has all keys:
```python
# validate_config.py
import os
from pathlib import Path

template_keys = set(Path('.env.template').read_text().split('\n'))
env_keys = set(os.environ.keys())

missing = template_keys - env_keys
if missing:
    print(f"Missing environment variables: {missing}")
```

---

## Security Best Practices

### 1. Never commit secrets
Even if you delete them later, they remain in git history.

### 2. Use environment variables
```python
# ✅ GOOD
password = os.getenv('NEO4J_PASSWORD')

# ❌ BAD
password = "librarian-pass"
```

### 3. Scan for exposed secrets
```bash
# Install truffleHog
pip install truffleHog

# Scan repository
trufflehog git file://. --json
```

### 4. Rotate compromised secrets
If secrets are committed:
1. Remove from git history: `git filter-branch` or BFG Repo-Cleaner
2. Rotate all exposed credentials
3. Review access logs for unauthorized access
4. Update `.gitignore` to prevent recurrence

---

## Project-Specific Decisions

### Why we DON'T ignore certain files:

#### `requirements.txt` (0.5 KB)
**Why commit**: Defines exact dependencies for reproducible builds
**Why not ignore**: Essential for `pip install -r requirements.txt`

#### `tests/fixtures/` (~10 KB)
**Why commit**: Small test data needed for reproducible tests
**Why not ignore**: Tests would fail without these fixtures

#### `.env.template` (0.2 KB)
**Why commit**: Shows developers what environment variables are needed
**Why not ignore**: New developers need configuration structure

#### `docker-compose.yml` (2 KB)
**Why commit**: Defines how to deploy application
**Why not ignore**: Part of infrastructure as code

---

## Maintenance

### Review .gitignore quarterly:
- Remove obsolete patterns
- Add new artifact types
- Check for over-broad rules
- Validate security exclusions

### When adding new tools:
1. Check tool's `.gitignore` recommendations
2. Test locally before committing
3. Document rationale in this guide
4. Add category comment in `.gitignore`

---

## References

- **GitHub .gitignore templates**: https://github.com/github/gitignore
- **Python .gitignore**: https://github.com/github/gitignore/blob/main/Python.gitignore
- **Git documentation**: https://git-scm.com/docs/gitignore
- **BFG Repo-Cleaner**: https://rtyley.github.io/bfg-repo-cleaner/

---

## Quick Reference

| File Type | Ignore? | Why |
|-----------|---------|-----|
| `*.py` | ❌ NO | Source code |
| `__pycache__/` | ✅ YES | Generated bytecode |
| `requirements.txt` | ❌ NO | Dependency manifest |
| `venv/` | ✅ YES | Virtual environment (regenerable) |
| `.env` | ✅ YES | Contains secrets |
| `.env.template` | ❌ NO | Configuration structure |
| `neo4j/data/` | ✅ YES | Binary DB files (large) |
| `src/schema/` | ❌ NO | Database schema (source) |
| `ollama/models/` | ✅ YES | Large binary models (downloadable) |
| `tests/` | ❌ NO | Test source code |
| `htmlcov/` | ✅ YES | Generated coverage report |
| `logs/` | ✅ YES | Runtime logs |
| `docs/` | ❌ NO | Documentation |
| `*.log` | ✅ YES | Log files |
| `Dockerfile` | ❌ NO | Infrastructure as code |

---

**Last Updated**: 2024-11-10
**Maintainer**: Project Owner
**Related**: `.gitignore` (root), `docs/dev/deployment-operations.md`
