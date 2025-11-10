# Document Ingestion System

## Overview

Automated document ingestion script that monitors `~/Downloads` for Markdown and PDF files, copies them to a RAG system ingestion directory, and manages stale files.

**Script:** `ingest_documents.py`
**Purpose:** Feed documents into RAG system while maintaining clean Downloads folder
**Execution:** Every 15 minutes via cron

---

## Core Requirements

### Functional Requirements
1. **Discovery:** Scan `~/Downloads` for `.md` and `.pdf` files
2. **Ingestion:** Copy eligible files to `$INGESTION_DIR`
3. **Deduplication:** Skip files already ingested (by content hash, not filename)
4. **Stale Management:** Move original files older than 14 days to `~/Downloads/Stale/`
5. **No Deletion:** Never delete files (move-only for stale files)

### Non-Functional Requirements
- **Idempotency:** Safe to run multiple times on same files
- **Concurrency Safety:** Lockfile prevents overlapping executions
- **Minimal Overhead:** Fast scanning suitable for 15-minute intervals
- **Logging:** Structured logging for debugging and monitoring
- **Cron-Friendly:** `--quiet` mode for automated execution

---

## Architecture

### Design Principles
Follows established patterns from `dedupe_downloads.py`:
- Single-file executable
- SQLite for persistent state
- TOML configuration
- Dataclass-based design
- Stdlib logging (no custom logging)

### Key Differences from Dedupe Script

| Aspect | dedupe_downloads.py | ingest_documents.py |
|--------|---------------------|---------------------|
| **Action** | Move (with tag routing) | Copy then age-based move |
| **Duplicates** | Delete | Skip (leave original) |
| **Destinations** | Multiple (tag-based) | Single (flat ingestion dir) |
| **Original Files** | Removed immediately | Kept for 14 days, then → Stale |
| **File Types** | Images/videos | Documents (.md, .pdf) |
| **Purpose** | Media organization | RAG system feeding |

### File Structure
```
/home/coldaine/scripts/
├── ingest_documents.py          # Main executable
├── test_ingest.py               # Comprehensive test suite
└── docs/features/
    └── document-ingestion.md    # This specification

~/.config/document_ingestion/
└── config.toml                  # User configuration

~/.local/share/document_ingestion/
└── ingested.sqlite3             # Ingestion tracking database

/tmp/
└── ingest_documents.lock        # Execution lockfile
```

---

## Workflow Logic

### Processing Flow
```
For each file in ~/Downloads matching [.md, .pdf]:

  1. HASH: Calculate SHA-256 hash of file content

  2. CHECK DATABASE: Query if hash exists in ingested.sqlite3
     - If exists: Skip (already ingested), log duplicate
     - If new: Proceed to step 3

  3. COPY: Copy file to $INGESTION_DIR (flat structure, preserve filename)
     - Handle filename conflicts: Append _{counter} if collision
     - Log successful copy

  4. RECORD: Insert into database (hash, original_path, timestamp)

  5. AGE CHECK: Calculate file age from mtime
     - If age < 14 days: Leave in Downloads
     - If age >= 14 days: Move to ~/Downloads/Stale/
     - Create Stale directory if missing
```

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS ingested_files (
    file_hash TEXT PRIMARY KEY,
    original_path TEXT NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_filename TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingested_at ON ingested_files(ingested_at);
CREATE INDEX IF NOT EXISTS idx_original_path ON ingested_files(original_path);
```

### Configuration (TOML)

**File:** `~/.config/document_ingestion/config.toml`

```toml
[source]
# Directory to monitor for documents
directory = "~/Downloads"

# Directory for files older than age threshold
stale_directory = "~/Downloads/Stale"

[processing]
# File extensions to process (hardcoded, no tag routing)
extensions = [".md", ".pdf"]

# Age threshold in days before moving to stale
age_threshold_days = 14

[ingestion]
# Destination directory (uses environment variable)
# This is read from $INGESTION_DIR at runtime
# Default: /home/coldaine/Desktop/VaultRebuildObsidian/Ingestion/
```

---

## Environment Configuration

### Environment Variable
- **Variable:** `INGESTION_DIR`
- **Location:** `~/.secrets` (auto-loaded via `~/.bashrc`)
- **Current Value:** `/home/coldaine/Desktop/VaultRebuildObsidian/Ingestion/`
- **Purpose:** Makes ingestion directory easily configurable without editing script

### Accessing in Script
```python
import os

ingestion_dir = os.environ.get("INGESTION_DIR")
if not ingestion_dir:
    raise ConfigError("INGESTION_DIR environment variable not set")
```

---

## Code Organization

### Modules (Top to Bottom)
1. **Imports & Constants**
   - Standard library imports only
   - No external dependencies

2. **Custom Exceptions**
   ```python
   class ConfigError(Exception): pass
   class LockError(Exception): pass
   class IngestError(Exception): pass
   ```

3. **Dataclasses**
   ```python
   @dataclass
   class Config:
       source_dir: Path
       stale_dir: Path
       ingestion_dir: Path
       extensions: list[str]
       age_threshold_days: int

       def validate(self) -> None:
           """Validate all paths and settings"""

   @dataclass
   class Stats:
       files_scanned: int = 0
       files_copied: int = 0
       duplicates_skipped: int = 0
       files_moved_to_stale: int = 0
   ```

4. **File Operations**
   - `calculate_hash(file_path: Path) -> str`
   - `get_file_age_days(file_path: Path) -> int`
   - `copy_file(src: Path, dest_dir: Path) -> Path`
   - `move_to_stale(file_path: Path, stale_dir: Path) -> None`

5. **Database Operations**
   ```python
   class Database:
       def __init__(self, db_path: Path)
       def _initialize(self) -> None
       def is_ingested(self, file_hash: str) -> bool
       def record_ingestion(self, file_hash: str, original_path: str, filename: str) -> None
       def get_stats(self) -> dict
   ```

6. **Config Operations**
   - `load_config() -> Config`
   - `create_default_config(config_path: Path) -> None`

7. **Lock Management**
   - `acquire_lock(lock_file: Path) -> None`
   - `release_lock(lock_file: Path) -> None`

8. **Main Processing**
   ```python
   def process_file(file_path: Path, config: Config, db: Database) -> tuple[bool, str]:
       """Process single file. Returns (success, action_taken)"""

   def process(config: Config, dry_run: bool = False) -> Stats:
       """Main processing loop"""

   def main():
       """CLI entry point with argparse"""
   ```

---

## CLI Interface

### Command-Line Arguments
```bash
ingest_documents.py [OPTIONS]

Options:
  --init-config    Create default configuration file
  --dry-run        Preview actions without making changes
  --quiet          Minimal output (errors/warnings only)
  --help           Show help message
```

### Usage Examples

**Initial Setup:**
```bash
./ingest_documents.py --init-config
# Edit ~/.config/document_ingestion/config.toml if needed
```

**Test Run:**
```bash
./ingest_documents.py --dry-run
# Output shows what would happen without modifying files
```

**Manual Execution:**
```bash
./ingest_documents.py
# Process all files, show detailed output
```

**Cron Execution:**
```bash
./ingest_documents.py --quiet
# Minimal output suitable for automated runs
```

---

## Testing Strategy

### Test Script: `test_ingest.py`

**Comprehensive smoke tests covering:**

1. **Configuration Tests**
   - Default config generation
   - Config validation (paths, thresholds)
   - Environment variable reading

2. **File Operations Tests**
   - Hash calculation consistency
   - Copy operations (preserve content)
   - Filename collision handling
   - Stale file movement

3. **Database Tests**
   - Schema initialization
   - Duplicate detection by hash
   - Record insertion
   - Query correctness

4. **Workflow Tests**
   - New file ingestion
   - Duplicate skipping (same hash, different name)
   - Age-based stale movement
   - Mixed file types (.md vs .pdf)

5. **Edge Cases**
   - Empty files
   - Large files (test performance)
   - Unicode filenames
   - Missing directories (auto-creation)

### Test Execution
```bash
./test_ingest.py
# Auto-cleanup: Temporary files removed after run
# Exit code 0 = all tests passed
```

---

## Deployment

### Cron Configuration

**Schedule:** Every 15 minutes

```bash
# Edit crontab
crontab -e

# Add this line:
*/15 * * * * /home/coldaine/scripts/ingest_documents.py --quiet

# Verify cron job
crontab -l
```

### First-Time Setup Checklist

1. ✅ Environment variable configured in `~/.secrets`
2. ✅ Ingestion directory exists and writable
3. ✅ Script has execute permissions: `chmod +x ingest_documents.py`
4. ✅ Config initialized: `./ingest_documents.py --init-config`
5. ✅ Dry run successful: `./ingest_documents.py --dry-run`
6. ✅ Test suite passes: `./test_ingest.py`
7. ✅ Cron job added and verified

### Monitoring

**Check lockfile status:**
```bash
ls -l /tmp/ingest_documents.lock
# Should not persist between runs
```

**View recent ingestions:**
```bash
sqlite3 ~/.local/share/document_ingestion/ingested.sqlite3 \
  "SELECT original_filename, ingested_at FROM ingested_files ORDER BY ingested_at DESC LIMIT 10;"
```

**Check stale files:**
```bash
ls -lah ~/Downloads/Stale/
```

---

## Operational Notes

### Performance Characteristics
- **Scan Time:** ~10ms per 100 files in Downloads
- **Copy Time:** Depends on file size (typically <100ms per file)
- **Database Query:** <5ms per file lookup
- **Expected Duration:** <2 seconds for typical workload (10-20 documents)

### Failure Modes & Recovery

**Lockfile Stuck:**
```bash
# If process crashes, lockfile may persist
rm /tmp/ingest_documents.lock
```

**Database Corruption:**
```bash
# Rebuild from scratch (safe - RAG system has copies)
rm ~/.local/share/document_ingestion/ingested.sqlite3
./ingest_documents.py  # Rebuilds schema, treats all files as new
```

**Missing Environment Variable:**
```bash
# Reload secrets
source ~/.secrets
echo $INGESTION_DIR  # Verify
```

### Maintenance

**Periodic Tasks:**
- Monthly: Review `~/Downloads/Stale/` and archive/delete old files
- Quarterly: Vacuum database: `sqlite3 ingested.sqlite3 "VACUUM;"`
- As needed: Adjust `age_threshold_days` if Downloads accumulates too fast

**Log Rotation:**
- Cron logs to syslog by default
- Check: `grep ingest_documents /var/log/syslog | tail -n 20`

---

## Future Enhancements (Not in MVP)

**Potential additions:**
- Configurable file extensions (TOML array)
- Metadata extraction (author, created date) stored in DB
- Subdirectory organization in ingestion dir (by date/type)
- Web dashboard for ingestion stats
- Integration with RAG system API (webhook on new file)
- Support for additional document formats (.docx, .txt, .epub)

**Not planned:**
- Tag-based routing (single destination is intentional)
- Cloud sync (out of scope)
- File content modification (copy-only by design)

---

## Comparison Matrix

| Feature | dedupe_downloads.py | ingest_documents.py |
|---------|---------------------|---------------------|
| **Primary Purpose** | Organize photos/videos | Feed RAG system |
| **File Types** | Images, videos | Documents (.md, .pdf) |
| **Operation** | Move with tag routing | Copy to single destination |
| **Duplicate Handling** | Delete immediately | Skip, leave in Downloads |
| **Tag System** | Multi-tag with priority | No tags (single destination) |
| **Original Files** | Removed after move | Kept 14 days, then → Stale |
| **Execution Frequency** | Hourly | Every 15 minutes |
| **Database Purpose** | Dedup tracking | Ingestion tracking |
| **Config Complexity** | High (tag rules) | Low (simple paths) |
| **Cron Safety** | Lockfile | Lockfile |
| **Dry Run Mode** | Yes | Yes |

---

## Implementation Checklist

- [ ] Write `ingest_documents.py` with all sections
- [ ] Implement dataclasses (Config, Stats)
- [ ] Implement Database class with schema
- [ ] Implement file operations (hash, copy, age check)
- [ ] Implement config loading with TOML
- [ ] Implement lockfile mechanism
- [ ] Implement main processing loop
- [ ] Add CLI argument parsing
- [ ] Write `test_ingest.py` with comprehensive tests
- [ ] Test dry-run mode
- [ ] Test quiet mode
- [ ] Verify environment variable reading
- [ ] Add cron job
- [ ] Monitor first 24 hours of automated execution
- [ ] Update ~/dependencylog.md with deployment date

---

## References

- **Related Script:** `/home/coldaine/scripts/dedupe_downloads.py`
- **Test Reference:** `/home/coldaine/scripts/test_dedupe.py`
- **Config Location:** `~/.config/document_ingestion/config.toml`
- **Database Location:** `~/.local/share/document_ingestion/ingested.sqlite3`
- **Environment Config:** `~/.secrets` (line 172)
- **RAG Ingestion Target:** `$INGESTION_DIR` → `/home/coldaine/Desktop/VaultRebuildObsidian/Ingestion/`

---

**Document Version:** 1.0
**Last Updated:** 2025-10-12
**Author:** Automated specification for Claude Code implementation
