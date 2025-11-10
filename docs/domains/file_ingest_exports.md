# Knowledge Export Processor

## Overview

Automated script that monitors `~/Downloads` for zip files containing "exported" in the filename, extracts and organizes the contents (code, documents, images, CSVs) into appropriate destinations for ingestion and archival.

**Script:** `process_exports.py`
**Purpose:** Extract AI conversation artifacts and organize them with associated documents
**Execution:** Every 15 minutes via cron (same schedule as document ingestion)

---

## Export Structure Analysis

Based on analysis of existing exports, these zips contain:
- **Python scripts** (.py) - Generated code and utilities
- **Markdown documents** (.md) - Technical specs, guides, summaries
- **Images** (.png) - Architecture diagrams, charts, visualizations
- **Data files** (.csv) - Structured data outputs

---

## Core Requirements

### Functional Requirements
1. **Discovery:** Scan `~/Downloads` for files matching `*exported*.zip`
2. **Staging:** Copy zip files to `~/Downloads/Processed-Exports/` (for later cleanup)
3. **Extraction:** Unzip contents to temporary directory
4. **Categorization:** Route files by type:
   - `.md`, `.pdf` → Document ingestion pipeline
   - `.py` → Code archive (`~/Code-Exports/` or project-specific location)
   - `.png`, `.jpg`, `.webp` → Asset archive (`~/Export-Assets/`)
   - `.csv`, `.json`, `.toml` → Data archive (`~/Export-Data/`)
5. **Cleanup:** Move original zip to staging area (not delete - manual review later)
6. **Deduplication:** Skip files already processed (by zip filename + mtime)

### Non-Functional Requirements
- **Idempotency:** Safe to run multiple times on same files
- **Concurrency Safety:** Lockfile prevents overlapping executions
- **Integration:** Works alongside `ingest_documents.py` without conflicts
- **Minimal Overhead:** Fast processing suitable for 15-minute cron intervals
- **Logging:** Structured logging for debugging

---

## Architecture

### Design Principles
Follows established patterns from `dedupe_downloads.py`:
- Single-file executable
- SQLite for persistent state (track processed zips)
- TOML configuration
- Dataclass-based design
- Stdlib logging

### Key Differences from Other Scripts

| Aspect | dedupe_downloads.py | ingest_documents.py | process_exports.py |
|--------|---------------------|---------------------|---------------------|
| **Source Files** | Images/videos | Documents | Zip archives |
| **Operation** | Move with tags | Copy then age-move | Extract, categorize, move |
| **Destinations** | Multiple (tags) | Single (RAG dir) | Multiple (by file type) |
| **Complexity** | Moderate | Low | High (extraction + routing) |
| **Purpose** | Media organization | RAG feeding | Knowledge export processing |

---

## Workflow Logic

### Processing Flow
```
For each file in ~/Downloads matching *exported*.zip:

  1. HASH: Calculate SHA-256 hash of zip file

  2. CHECK DATABASE: Query if zip already processed
     - If exists: Skip, log duplicate
     - If new: Proceed to step 3

  3. COPY: Copy zip to ~/Downloads/Processed-Exports/
     - Preserve filename
     - Handle collisions with _{counter}

  4. EXTRACT: Unzip to temporary directory
     - Temp location: /tmp/export_processing_{timestamp}/

  5. CATEGORIZE & ROUTE: For each extracted file:
     - .md, .pdf → Copy to $INGESTION_DIR (for RAG)
     - .py → Copy to ~/Code-Exports/{export_name}/
     - .png, .jpg, .webp, .gif → Copy to ~/Export-Assets/{export_name}/
     - .csv, .json, .toml, .yaml → Copy to ~/Export-Data/{export_name}/
     - Other → Copy to ~/Export-Other/{export_name}/

  6. RECORD: Insert into database:
     - zip_hash, original_filename, processed_at, file_count, categories

  7. CLEANUP:
     - Delete temporary extraction directory
     - Original zip already in Processed-Exports/

  8. STALE MANAGEMENT:
     - After 30 days, move zips from Processed-Exports/ to ~/Downloads/Stale/
```

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS processed_exports (
    zip_hash TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    original_path TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_count INTEGER,
    categories TEXT,  -- JSON array: ["code", "docs", "images"]
    extraction_success BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_exports(processed_at);
CREATE INDEX IF NOT EXISTS idx_filename ON processed_exports(original_filename);
```

### Configuration (TOML)

**File:** `~/.config/export_processor/config.toml`

```toml
[source]
# Directory to monitor for export zips
directory = "~/Downloads"

# Pattern to match export files
pattern = "*exported*.zip"

# Where to move processed zips
staging_directory = "~/Downloads/Processed-Exports"

# Where to move old processed zips
stale_directory = "~/Downloads/Stale"

[destinations]
# Where to copy markdown/PDF documents for RAG ingestion
# Uses environment variable $INGESTION_DIR
documents = "${INGESTION_DIR}"

# Where to organize extracted code files
code = "~/Code-Exports"

# Where to organize extracted images/assets
assets = "~/Export-Assets"

# Where to organize extracted data files
data = "~/Export-Data"

# Catch-all for unrecognized file types
other = "~/Export-Other"

[processing]
# Age threshold before moving processed zips to stale
stale_days = 30

# Create subdirectories per export (uses zip filename without extension)
organize_by_export = true

# File extensions by category
extensions_documents = [".md", ".pdf", ".txt"]
extensions_code = [".py", ".js", ".ts", ".sh", ".bash", ".zsh"]
extensions_assets = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]
extensions_data = [".csv", ".json", ".toml", ".yaml", ".yml", ".xml"]
```

---

## Code Organization

### Modules (Top to Bottom)

1. **Imports & Constants**
   - Standard library: pathlib, sqlite3, hashlib, zipfile, shutil, tempfile, json, tomllib
   - No external dependencies

2. **Custom Exceptions**
   ```python
   class ConfigError(Exception): pass
   class LockError(Exception): pass
   class ExportProcessingError(Exception): pass
   class ExtractionError(Exception): pass
   ```

3. **Dataclasses**
   ```python
   @dataclass
   class Config:
       source_dir: Path
       staging_dir: Path
       stale_dir: Path
       dest_documents: Path
       dest_code: Path
       dest_assets: Path
       dest_data: Path
       dest_other: Path
       stale_days: int
       organize_by_export: bool
       extensions_documents: list[str]
       extensions_code: list[str]
       extensions_assets: list[str]
       extensions_data: list[str]

       def validate(self) -> None:
           """Validate all paths and settings"""

   @dataclass
   class Stats:
       exports_found: int = 0
       exports_processed: int = 0
       exports_skipped: int = 0
       files_extracted: int = 0
       files_to_documents: int = 0
       files_to_code: int = 0
       files_to_assets: int = 0
       files_to_data: int = 0
       files_to_other: int = 0
       errors: int = 0

   @dataclass
   class ExtractedFile:
       path: Path
       category: str  # "documents", "code", "assets", "data", "other"
       relative_path: str  # Path within zip
   ```

4. **File Operations**
   - `calculate_hash(file_path: Path) -> str`
   - `extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]`
   - `categorize_file(file_path: Path, config: Config) -> str`
   - `copy_to_destination(file: ExtractedFile, export_name: str, config: Config) -> Path`
   - `get_export_name(zip_path: Path) -> str`  # Strip .zip and numbering

5. **Database Operations**
   ```python
   class Database:
       def __init__(self, db_path: Path)
       def _initialize(self) -> None
       def is_processed(self, zip_hash: str) -> bool
       def record_export(self, zip_hash: str, filename: str, path: str,
                        file_count: int, categories: list[str]) -> None
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
   def process_export(zip_path: Path, config: Config, db: Database,
                     dry_run: bool = False) -> tuple[bool, Stats]:
       """Process single export zip. Returns (success, stats)"""

   def process(config: Config, dry_run: bool = False) -> Stats:
       """Main processing loop"""

   def main():
       """CLI entry point with argparse"""
   ```

---

## CLI Interface

### Command-Line Arguments
```bash
process_exports.py [OPTIONS]

Options:
  --init-config    Create default configuration file
  --dry-run        Preview actions without making changes
  --quiet          Minimal output (errors/warnings only)
  --help           Show help message
```

### Usage Examples

**Initial Setup:**
```bash
./process_exports.py --init-config
# Edit ~/.config/export_processor/config.toml if needed
```

**Test Run:**
```bash
./process_exports.py --dry-run
# Shows what would happen without modifying files
```

**Manual Execution:**
```bash
./process_exports.py
# Process all export zips, show detailed output
```

**Cron Execution:**
```bash
./process_exports.py --quiet
# Minimal output suitable for automated runs
```

---

## Testing Strategy

### Test Script: `test_exports.py`

**Comprehensive smoke tests covering:**

1. **Configuration Tests**
   - Default config generation
   - Config validation
   - Environment variable substitution

2. **Extraction Tests**
   - Zip file creation and extraction
   - Handling nested directories in zips
   - Invalid/corrupted zip handling

3. **Categorization Tests**
   - File type detection
   - Extension matching
   - Unknown file type handling

4. **Routing Tests**
   - Correct destination by category
   - Subdirectory creation (organize_by_export)
   - Filename collision handling

5. **Database Tests**
   - Schema initialization
   - Duplicate detection by hash
   - Record insertion with categories

6. **Workflow Tests**
   - End-to-end processing
   - Multiple exports in one run
   - Mixed file types in single export

7. **Edge Cases**
   - Empty zips
   - Zips with duplicate filenames
   - Zips with special characters
   - Large exports (performance)

### Test Execution
```bash
./test_exports.py
# Auto-cleanup: Temporary files removed after run
# Exit code 0 = all tests passed
```

---

## Deployment

### Cron Configuration

**Schedule:** Every 15 minutes (same as document ingestion)

```bash
# Edit crontab
crontab -e

# Add this line:
*/15 * * * * /home/coldaine/scripts/process_exports.py --quiet

# Verify cron job
crontab -l
```

### First-Time Setup Checklist

1. ✅ Script has execute permissions: `chmod +x process_exports.py`
2. ✅ Config initialized: `./process_exports.py --init-config`
3. ✅ Destination directories exist or will be auto-created
4. ✅ Dry run successful: `./process_exports.py --dry-run`
5. ✅ Test suite passes: `./test_exports.py`
6. ✅ Cron job added and verified
7. ✅ $INGESTION_DIR environment variable available

---

## Integration with Existing Scripts

### Coordination with ingest_documents.py

**Problem:** Both scripts may process documents at the same time

**Solution:**
- `process_exports.py` runs first (extracts to `$INGESTION_DIR`)
- `ingest_documents.py` runs after and picks up the documents
- No conflict: They work on different file types (zips vs docs)
- Both use separate databases for tracking

**Execution order in cron:**
```bash
# Run exports processor first
*/15 * * * * /home/coldaine/scripts/process_exports.py --quiet

# Run document ingestion 2 minutes later
2-59/15 * * * * /home/coldaine/scripts/ingest_documents.py --quiet
```

---

## Operational Notes

### Performance Characteristics
- **Scan Time:** ~5ms per zip file check
- **Extraction Time:** ~100-500ms per zip (depends on size)
- **Categorization:** ~1ms per file
- **Copy Time:** Depends on file sizes
- **Expected Duration:** <10 seconds for typical workload (1-3 exports)

### Failure Modes & Recovery

**Lockfile Stuck:**
```bash
rm /tmp/process_exports.lock
```

**Database Corruption:**
```bash
# Rebuild from scratch (safe - files already organized)
rm ~/.local/share/export_processor/exports.sqlite3
./process_exports.py  # Rebuilds schema, treats all zips as new
```

**Partial Extraction:**
- If script crashes during extraction, temp directory in /tmp will be cleaned on reboot
- Next run will reprocess the zip (idempotent)

**Duplicate Files:**
- Script handles filename collisions by appending _{counter}
- Original names preserved where possible

### Maintenance

**Periodic Tasks:**
- Monthly: Review `~/Downloads/Processed-Exports/` and manually delete if satisfied
- Monthly: Check category destinations for proper organization
- Quarterly: Vacuum database: `sqlite3 exports.sqlite3 "VACUUM;"`
- As needed: Adjust `stale_days` threshold

**Manual Organization:**
```bash
# View recent exports
ls -lth ~/Code-Exports/

# Check what was extracted from specific export
ls -R ~/Code-Exports/exported-assets-4/

# Find all Python files across exports
find ~/Code-Exports/ -name "*.py"
```

---

## Example Processing Scenario

Given: `/home/coldaine/Downloads/exported-assets (4).zip` containing:
- `chart_script.py`
- `comparison_table.png`
- `chart_script_1.py`
- `coldvox_migration_architecture.png`

**Processing steps:**

1. Hash zip file → `abc123...`
2. Check database → Not found, proceed
3. Copy zip → `~/Downloads/Processed-Exports/exported-assets (4).zip`
4. Extract to `/tmp/export_processing_1729012345/`
5. Categorize files:
   - `chart_script.py` → code
   - `comparison_table.png` → assets
   - `chart_script_1.py` → code
   - `coldvox_migration_architecture.png` → assets
6. Copy to destinations:
   - `~/Code-Exports/exported-assets-4/chart_script.py`
   - `~/Code-Exports/exported-assets-4/chart_script_1.py`
   - `~/Export-Assets/exported-assets-4/comparison_table.png`
   - `~/Export-Assets/exported-assets-4/coldvox_migration_architecture.png`
7. Record in database: hash, filename, 4 files, ["code", "assets"]
8. Cleanup temp directory
9. Log summary: "Processed exported-assets (4).zip: 2 code, 2 assets"

---

## Future Enhancements (Not in MVP)

**Potential additions:**
- Smart filename parsing (extract conversation title from export)
- Markdown index generation (catalog of all exports)
- Content analysis (detect code language, image types)
- Integration with git (auto-commit extracted code to repos)
- Web UI for browsing processed exports
- Duplicate detection across exports (same file in multiple zips)

**Not planned:**
- Modification of extracted files (copy-only by design)
- Cloud sync (out of scope)
- Automatic execution of extracted code (security risk)

---

## Implementation Checklist

- [ ] Write `process_exports.py` with all sections
- [ ] Implement dataclasses (Config, Stats, ExtractedFile)
- [ ] Implement Database class with schema
- [ ] Implement zip extraction with tempfile
- [ ] Implement file categorization logic
- [ ] Implement routing to multiple destinations
- [ ] Implement config loading with TOML and env var substitution
- [ ] Implement lockfile mechanism
- [ ] Implement main processing loop
- [ ] Add CLI argument parsing
- [ ] Write `test_exports.py` with comprehensive tests
- [ ] Test dry-run mode
- [ ] Test quiet mode
- [ ] Create destination directories
- [ ] Test with existing export zips in Downloads
- [ ] Add cron job with staggered timing
- [ ] Monitor first 24 hours of automated execution
- [ ] Update ~/dependencylog.md with deployment date

---

## References

- **Related Scripts:**
  - `/home/coldaine/scripts/dedupe_downloads.py` (architecture pattern)
  - `/home/coldaine/scripts/ingest_documents.py` (document ingestion integration)
- **Test Reference:** `/home/coldaine/scripts/test_dedupe.py`
- **Config Location:** `~/.config/export_processor/config.toml`
- **Database Location:** `~/.local/share/export_processor/exports.sqlite3`
- **Lockfile Location:** `/tmp/process_exports.lock`
- **Example Exports:** `/home/coldaine/Downloads/exported-assets*.zip`

---

**Document Version:** 1.0
**Last Updated:** 2025-10-12
**Author:** Automated specification for Claude Code implementation
