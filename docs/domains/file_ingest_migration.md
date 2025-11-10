# File Watchman Migration & Deprecation Guide

**Status:** file-watchman repository still **ACTIVE** and required
**Last Updated:** 2025-11-10

---

## ⚠️ DO NOT DELETE file-watchman YET

The standalone file-watchman repository is currently **running in production** and must remain until the migration to The Watchman is complete and verified.

---

## Current Production Status

### Active Components in file-watchman

**Production Script:**
- `dedupe_downloads.py` - **RUNNING** via cron (hourly at minute 0)
- Processed 518 files successfully
- Database: `~/.local/share/photo_dedupe/photos.sqlite3` (active)
- Cron job: `0 * * * * /home/coldaine/scripts/dedupe_downloads.py --quiet`

**Why You Still Need It:**
- ✅ The actual working implementation code
- ✅ Reference for porting to the-watchman collectors
- ✅ Active deduplication database with historical hashes
- ✅ Tested and proven tag-based routing logic
- ✅ Production configuration and patterns

---

## Migration Checklist

### Phase 1: Implementation (NOT STARTED)
- [ ] Implement `domains/file_ingest/processors/hasher.py`
- [ ] Implement `domains/file_ingest/processors/router.py`
- [ ] Implement `domains/file_ingest/processors/graph_writer.py`
- [ ] Implement `domains/file_ingest/collectors/dedupe_collector.py`
- [ ] Implement `domains/file_ingest/collectors/document_collector.py`
- [ ] Implement `domains/file_ingest/collectors/export_collector.py`
- [ ] Add to docker-compose.yml
- [ ] Configure environment variables and volumes
- [ ] Write integration tests

**Estimated Time:** 2-3 weeks

### Phase 2: Parallel Operation (1-2 WEEKS)
- [ ] Deploy the-watchman collectors alongside existing cron jobs
- [ ] Monitor both systems simultaneously
- [ ] Verify Neo4j nodes created correctly
- [ ] Compare results for consistency
- [ ] Watch for errors or missing files
- [ ] Validate duplicate detection matches

**Success Criteria:**
- Both systems process files identically
- No files missed by new collectors
- Neo4j graph accurately reflects file operations
- Performance acceptable (<5 second detection latency)

### Phase 3: Gradual Cutover (1 WEEK)
- [ ] **Day 1:** Disable dedupe cron job (most stable)
- [ ] **Days 2-3:** Monitor the-watchman dedupe collector
- [ ] **Day 4:** Disable document ingestion cron job
- [ ] **Days 5-6:** Monitor document collector
- [ ] **Day 7:** Disable export processing cron job
- [ ] **Days 8-9:** Monitor export collector
- [ ] **Day 10:** Final verification all collectors stable

**Rollback Plan:** Re-enable cron jobs if issues detected

### Phase 4: Archive file-watchman (AFTER 1+ WEEK STABLE)
- [ ] Verify no cron jobs reference file-watchman scripts
- [ ] Backup SQLite databases for historical record
- [ ] Optional: Migrate SQLite history to Neo4j
- [ ] Remove cron jobs from crontab
- [ ] Archive repository (don't delete yet)
- [ ] Update documentation with cutover date

---

## When It's Safe to Archive

**Minimum Requirements:**
1. ✅ All three collectors implemented and running in the-watchman
2. ✅ Parallel operation completed (1+ week)
3. ✅ All cron jobs disabled and removed
4. ✅ 1+ week of stable operation without cron jobs
5. ✅ Neo4j graph verified accurate
6. ✅ No files missed or improperly processed
7. ✅ Team/user comfortable with new system

**Timeline Estimate:**
- If starting today: **Earliest safe date is ~5-6 weeks from now**
  - 2-3 weeks: Implementation
  - 1-2 weeks: Parallel operation
  - 1 week: Gradual cutover
  - 1 week: Stability verification

---

## Archive Process (NOT DELETE)

### Step 1: Create Archive Branch
```bash
cd /path/to/file-watchman
git checkout -b archive/production-final
git commit --allow-empty -m "Archive: Final production state before migration to the-watchman"
git push origin archive/production-final
```

### Step 2: Backup Databases
```bash
mkdir -p ~/backups/file-watchman-$(date +%Y%m%d)
cp ~/.local/share/photo_dedupe/photos.sqlite3 ~/backups/file-watchman-$(date +%Y%m%d)/
cp ~/.local/share/document_ingestion/ingested.sqlite3 ~/backups/file-watchman-$(date +%Y%m%d)/ 2>/dev/null || true
cp ~/.local/share/export_processor/exports.sqlite3 ~/backups/file-watchman-$(date +%Y%m%d)/ 2>/dev/null || true
```

### Step 3: Remove Cron Jobs
```bash
crontab -e
# Comment out or delete all file-watchman lines:
# 0 * * * * /home/coldaine/scripts/dedupe_downloads.py --quiet
# */15 * * * * /home/coldaine/scripts/process_exports.py --quiet
# 2-59/15 * * * * /home/coldaine/scripts/ingest_documents.py --quiet

# Verify removal:
crontab -l | grep -i "scripts/"
```

### Step 4: Add Archive README
```bash
cd /path/to/file-watchman
cat > ARCHIVED.md << 'EOF'
# ARCHIVED - file-watchman

**Archive Date:** $(date +%Y-%m-%d)
**Reason:** Functionality migrated to the-watchman as `domains/file_ingest/`

This repository has been archived and is no longer actively maintained.

## Successor

All functionality has been integrated into:
- **Repository:** https://github.com/Coldaine/the-watchman
- **Domain:** `domains/file_ingest/`
- **Documentation:** `docs/domains/file_ingest_implementation.md`

## Historical Production Stats
- dedupe_downloads.py: 518 files processed successfully
- Active from: 2025-10-12 to $(date +%Y-%m-%d)
- Database records: [run query and note count here]

## Reference Implementation

This repository remains valuable as a reference for:
- Original standalone script patterns
- Tag-based routing logic
- SQLite schema design
- Testing approaches

Do not delete - keep for historical reference.
EOF

git add ARCHIVED.md
git commit -m "Mark repository as archived - migrated to the-watchman"
git push origin main
```

### Step 5: GitHub Archive
- Go to repository settings on GitHub
- Click "Archive this repository"
- Confirm archival

**Important:** Archiving makes the repo read-only but preserves all code and history.

---

## Data Migration (Optional)

### Migrate SQLite Hash History to Neo4j

If you want to preserve the deduplication history in the graph:

```python
# scripts/migrate_file_watchman_history.py
import sqlite3
from neo4j import GraphDatabase
from pathlib import Path

def migrate_dedupe_history():
    """Migrate photo_dedupe SQLite to Neo4j :MediaFile nodes."""

    # Connect to SQLite
    db_path = Path.home() / ".local/share/photo_dedupe/photos.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Connect to Neo4j
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "watchman123")
    )

    # Read all processed photos
    cursor.execute("SELECT hash, first_seen, original_path, final_path, tag FROM photos")
    photos = cursor.fetchall()

    # Write to Neo4j
    with driver.session() as session:
        for hash, first_seen, orig_path, final_path, tag in photos:
            session.run("""
                MERGE (m:MediaFile {file_hash: $hash})
                SET m.original_path = $orig_path,
                    m.dest_path = $final_path,
                    m.tag = $tag,
                    m.processed_at = datetime({epochSeconds: $first_seen}),
                    m.migrated_from_sqlite = true
            """, hash=hash, orig_path=orig_path, final_path=final_path,
                 tag=tag, first_seen=first_seen)

    print(f"Migrated {len(photos)} photo records to Neo4j")

    conn.close()
    driver.close()

if __name__ == "__main__":
    migrate_dedupe_history()
```

Run this **after** collectors are deployed but **before** archiving file-watchman.

---

## Rollback Plan

If you need to roll back to file-watchman after disabling cron:

```bash
# Re-enable cron jobs
crontab -e
# Uncomment the file-watchman lines

# Stop the-watchman collectors
cd /path/to/the-watchman
docker-compose stop file-ingest-dedupe
docker-compose stop file-ingest-documents
docker-compose stop file-ingest-exports

# Verify cron jobs running
crontab -l
watch -n 60 'ls -lt ~/Downloads | head'
```

---

## Current Status Summary

**As of 2025-11-10:**

| Component | Status | Location |
|-----------|--------|----------|
| file-watchman repo | ✅ **ACTIVE - DO NOT DELETE** | Standalone repo |
| dedupe_downloads.py | ✅ **RUNNING IN PRODUCTION** | Cron (hourly) |
| the-watchman integration | ✅ **DOCUMENTED** | `domains/file_ingest/` |
| the-watchman implementation | ❌ **NOT STARTED** | Directory structure only |
| Safe to archive file-watchman? | ❌ **NO - WAIT 5-6 WEEKS** | See timeline above |

---

## Questions to Ask Before Archiving

1. **Are all collectors running?**
   `docker-compose ps | grep file-ingest`

2. **Have any files been missed?**
   Check Downloads directory for unprocessed files older than 5 minutes

3. **Is Neo4j graph accurate?**
   Run test queries to verify nodes and relationships

4. **Are cron jobs completely removed?**
   `crontab -l | grep scripts`

5. **Has it been stable for 1+ week?**
   Check logs for errors or crashes

6. **Do you have database backups?**
   Verify SQLite files backed up safely

**If all answers are YES:** Safe to archive file-watchman
**If any answer is NO:** Wait and investigate

---

## Support

If issues arise during migration:
- Check `docs/unified/troubleshooting.md`
- Review collector logs: `docker-compose logs file-ingest-*`
- Compare behavior against file-watchman reference implementation
- Rollback if necessary (see Rollback Plan above)

---

**Remember:** Archive ≠ Delete. Keep the repository accessible for reference even after archival.
