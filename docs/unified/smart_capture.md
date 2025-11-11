# Smart Screenshot Capture Features

**Last Updated:** 2025-11-11

This document describes the intelligent screenshot capture features that optimize storage, reduce processing overhead, and improve the signal-to-noise ratio of captured screen data.

## Overview

The Visual Timeline domain includes several advanced features beyond basic time-based screenshot capture:

1. **Screenshot Diffing** - Only capture when screen content changes
2. **Smart Capture Triggers** - Capture on meaningful events (app switches, idle return)
3. **Similarity Clustering** - Detect and deduplicate near-identical screenshots
4. **Lazy OCR Processing** - Process screenshots on-demand rather than immediately

## 1. Screenshot Diffing

### Purpose

Prevents capturing redundant screenshots when the screen hasn't changed, dramatically reducing:
- Storage usage (50-90% reduction typical)
- OCR processing workload
- Database growth
- Energy consumption

### Configuration

```toml
[screenshot]
enable_diffing = true
diff_threshold = 0.10  # Capture if >10% of pixels changed
diff_algorithm = "phash"  # Options: phash, dhash, pixel
```

### Algorithms

**Perceptual Hash (phash)** - Default, recommended
- Robust to minor UI changes (scrolling, blinking cursors)
- Fast comparison (microseconds)
- Works across resolution changes
- Best for general desktop usage

**Difference Hash (dhash)** - Alternative
- Simpler algorithm, faster computation
- More sensitive to minor changes
- Good for detecting subtle shifts
- Best for monitoring active work sessions

**Pixel Diff** - Exact comparison
- Compares actual pixel values
- Most accurate but slowest
- Captures even tiny changes (cursor, clock updates)
- Best for security/audit scenarios

### Implementation Details

Location: `domains/visual_timeline/diffing.py` (planned)

```python
from imagehash import phash, dhash
from PIL import Image

def should_capture_screenshot(
    current_frame: Image,
    last_captured: Image,
    threshold: float,
    algorithm: str
) -> bool:
    """
    Compare current frame to last captured screenshot.

    Returns:
        True if difference exceeds threshold
    """
    if algorithm == "phash":
        hash_diff = phash(current_frame) - phash(last_captured)
    elif algorithm == "dhash":
        hash_diff = dhash(current_frame) - dhash(last_captured)
    else:  # pixel
        # Compute pixel-wise difference
        ...

    normalized_diff = hash_diff / 64.0  # Normalize to 0-1
    return normalized_diff > threshold
```

### Storage

- Last captured screenshot hash stored in memory
- On restart, compares against most recent `:Snapshot` from Neo4j
- Hash stored as `last_capture_hash` property on `:Snapshot` nodes

## 2. Smart Capture Triggers

### Purpose

Capture screenshots when meaningful events occur, regardless of timer interval. This ensures important moments are never missed while reducing noise during idle periods.

### Configuration

```toml
[screenshot]
enable_smart_capture = true
capture_on_app_switch = true
capture_on_idle_return = true
idle_threshold = 300  # seconds
```

### Triggers

**App Switch Detection**
- Monitors active window via `xdotool` (Linux) or platform APIs
- Captures when `WM_CLASS` changes
- Useful for: "What was I looking at before the meeting?"
- Graph: Creates `(:AppSwitchEvent)-[:TRIGGERED_CAPTURE]->(:Snapshot)`

**Idle Return Detection**
- Monitors keyboard/mouse activity via X11 idle time
- Captures first activity after idle period exceeds threshold
- Useful for: "What did I start working on after lunch?"
- Graph: Creates `(:IdleReturnEvent)-[:TRIGGERED_CAPTURE]->(:Snapshot)`

### Implementation

Location: `domains/visual_timeline/triggers.py` (planned)

```python
class SmartCaptureMonitor:
    def __init__(self):
        self.last_active_window = None
        self.last_activity_time = time.time()
        self.was_idle = False

    def should_trigger_capture(self) -> tuple[bool, str]:
        """
        Check if smart trigger conditions met.

        Returns:
            (should_capture, trigger_reason)
        """
        current_window = get_active_window()
        idle_time = get_x11_idle_time()

        # App switch
        if current_window != self.last_active_window:
            return (True, "app_switch")

        # Idle return
        if idle_time < 5 and self.was_idle:
            self.was_idle = False
            return (True, "idle_return")

        if idle_time > self.settings.idle_threshold:
            self.was_idle = True

        return (False, None)
```

## 3. Similarity Clustering

### Purpose

Detect and group near-duplicate screenshots to:
- Reduce storage of redundant data
- Improve query relevance (avoid showing 10 identical screenshots)
- Enable "show unique screens" queries
- Optional: Delete duplicates automatically

### Configuration

```toml
[screenshot]
enable_similarity_clustering = true
similarity_threshold = 0.95  # 95% similar = duplicate
cluster_window = 3600  # only compare within 1 hour window

[retention]
auto_delete_duplicates = false  # keep all by default
```

### Clustering Strategy

1. **Capture Phase**: Screenshot always saved initially
2. **Async Clustering**: Background worker compares against recent captures
3. **Graph Relationships**: Create `(:Snapshot)-[:SIMILAR_TO {similarity: 0.97}]->(:Snapshot)`
4. **Optional Deletion**: If `auto_delete_duplicates=true`, delete image file but keep metadata

### Graph Schema

```cypher
# Similarity relationship
(:Snapshot)-[:SIMILAR_TO {
    similarity: 0.97,
    algorithm: "phash",
    detected_at: datetime()
}]->(:Snapshot)

# Cluster representative (keep one, link rest)
(:Snapshot {cluster_id: "abc123", is_representative: true})
(:Snapshot {cluster_id: "abc123", is_representative: false})-[:DUPLICATE_OF]->(:Snapshot {is_representative: true})
```

### Query Examples

```cypher
# Find unique screens from today
MATCH (s:Snapshot)
WHERE s.ts > datetime() - duration({hours: 24})
  AND NOT (s)-[:DUPLICATE_OF]->()
RETURN s
ORDER BY s.ts DESC

# Find all duplicates of a screenshot
MATCH (s:Snapshot {id: $snapshot_id})-[r:SIMILAR_TO]-(other:Snapshot)
WHERE r.similarity > 0.90
RETURN other, r.similarity
ORDER BY r.similarity DESC
```

## 4. Lazy OCR Processing

### Purpose

Defer OCR processing until needed, reducing:
- Continuous CPU load from OCR workers
- Energy consumption on battery devices
- Unnecessary processing of screens you'll never query

Process OCR:
- On-demand when queried
- Automatically for recent screenshots (last 1 hour)
- Batch processing during idle periods

### Configuration

```toml
[ocr]
enable_lazy_processing = true  # Don't process immediately
auto_process_recent = true     # Process last hour automatically
recent_threshold = 3600        # seconds
```

### Workflow

**Immediate Mode** (`enable_lazy_processing = false`)
- Current behavior
- OCR worker processes all pending snapshots every 30 seconds
- Suitable for: Always-on desktop workstations

**Lazy Mode** (`enable_lazy_processing = true`)
- OCR triggered by:
  - User query requiring text search
  - Manual `/review` API call
  - Scheduled batch (e.g., nightly OCR catch-up)
- Recent threshold: Auto-process last N seconds
- Suitable for: Laptops, resource-constrained systems

### API Endpoints

**Trigger OCR for time range**
```bash
POST /admin/ocr/process
{
  "start_time": "2025-11-11T14:00:00Z",
  "end_time": "2025-11-11T16:00:00Z",
  "priority": "high"
}
```

**Review session (OCR + summarize)**
```bash
POST /review
{
  "start_time": "2025-11-11T14:00:00Z",
  "end_time": "2025-11-11T16:00:00Z",
  "summarize": true,
  "model": "llama3.2"
}
```

Response:
```json
{
  "screenshots_processed": 23,
  "ocr_chunks_created": 156,
  "summary": "During this period, you worked on The Watchman documentation, switched between VS Code and a web browser viewing Neo4j docs, and responded to several Slack messages.",
  "key_applications": ["VS Code", "Firefox", "Slack"],
  "snapshots": [...]
}
```

## 5. Performance Tuning

### Configuration

```toml
[performance]
screenshot_compression_quality = 85  # 1-100, JPEG quality
screenshot_max_dimension = 1920      # Scale down 4K displays
enable_incremental_hashing = true    # Hash only changed regions
hash_grid_size = 16                  # Grid size for incremental hashing
```

### Incremental Hashing

Instead of hashing entire screen every time:

1. Divide screen into NxN grid (default 16x16 = 256 cells)
2. Hash each cell independently
3. On next capture, only re-hash cells that changed
4. Compare only changed cell hashes

**Benefit**: 10-50x faster diffing for typical desktop usage (only small regions change)

### Compression

- Raw PNG: ~5-10 MB per screenshot
- JPEG quality 85: ~200-500 KB per screenshot (10-50x reduction)
- JPEG quality 60: ~100-200 KB (acceptable for OCR)

Recommendation: Quality 85 for general use, 60 if storage-constrained

## Implementation Status

| Feature | Status | Location | Priority |
|---------|--------|----------|----------|
| Screenshot Diffing | Planned | `domains/visual_timeline/diffing.py` | High |
| Smart Triggers | Planned | `domains/visual_timeline/triggers.py` | Medium |
| Similarity Clustering | Planned | `domains/visual_timeline/clustering.py` | Medium |
| Lazy OCR | Planned | `domains/visual_timeline/ocr.py` (extend) | High |
| Review API | Planned | `app/api/review.py` | High |
| Incremental Hashing | Planned | `domains/visual_timeline/hashing.py` | Low |

## Migration Path

Existing deployments continue to work with time-based capture. To enable smart features:

1. Update `config.toml` with desired feature flags
2. Restart visual timeline workers
3. Existing screenshots remain queryable
4. New captures use smart features immediately

No schema migration required - new relationships added only when features enabled.

## Testing Strategy

- Unit tests: Hash algorithms, trigger detection, similarity computation
- Integration tests: End-to-end capture with diffing enabled
- Performance tests: Diffing overhead, clustering throughput
- Storage tests: Verify disk space reduction
- Query tests: Ensure deduplicated screenshots don't break search

See `tests/unit/test_smart_capture.py` and `tests/integration/test_visual_timeline_smart.py`.
