# Troubleshooting Guide

**Last Updated:** 2025-10-14

This guide aggregates remediation steps from the legacy projects with Watchman-specific diagnostics.

## AT-SPI & GUI Collector

- **Symptoms:** No GUI events captured; logs show `pyatspi` connection errors.
  - Ensure the collector runs under a regular desktop user (not root).
  - Verify `GTK_MODULES=atk-bridge` is not forced globally; prefer per-app enabling.
  - Confirm `XDG_RUNTIME_DIR` points to a writable directory.
  - Restart the accessibility bus: `killall at-spi-bus-launcher` then log out/in.
- **Symptoms:** High CPU usage when collector enabled.
  - Reduce `GUI_COLLECTOR_MAX_EVENTS_PER_SEC`.
  - Switch `capture_text` off to avoid hashing large payloads.
  - Check deny-lists for noisy applications (e.g., rapidly updating terminals).

## Screenshot & OCR Pipeline

- **Symptoms:** No screenshots captured.
  - Ensure the container has access to the X11 socket (`/tmp/.X11-unix`).
  - Confirm `DISPLAY` is set and `xhost +local:docker` was run (or use Wayland portal integration).
- **Symptoms:** OCR produces empty text.
  - Verify Tesseract language packs are installed.
  - Check that privacy filters are not redacting everything (review regex configuration).
  - Inspect raw images in `data/snapshots/` for resolution/contrast issues.

## Neo4j & Graph Ingestion

- **Symptoms:** Collectors logging `Neo4jException: connection refused`.
  - Ensure Neo4j container is healthy (`docker compose ps`).
  - Check credentials in `.env`; rotate password if changed.
- **Symptoms:** Writes succeed but queries return nothing.
  - Run migration scripts under `scripts/migrations/` to ensure constraints exist.
  - Execute `MATCH (n) RETURN labels(n), count(*) LIMIT 20` to confirm data presence.

## File Ingestion Collector

- **Symptoms:** Files not routed.
  - Confirm `MIN_FILE_AGE_SEC` is lower than actual file age.
  - Ensure destination directories exist and are writable.
  - Inspect logs for `lockfile` warnings indicating another process holds the lock.
- **Symptoms:** Duplicates still appear.
  - Verify hash calculation is enabled (no `--skip-hash` flag).
  - Clean the Neo4j `:IngestedDocument` nodes for stale entries to avoid collisions.

## Automation & MCP

- **Symptoms:** MCP server fails to start from API.
  - Check Docker Compose logs for the service (`docker compose logs <service>`).
  - Ensure the registry YAML entry matches the compose service name.
- **Symptoms:** Automation runner keeps retrying an action.
  - Review automation rules for contradictory conditions.
  - Increase debounce timers or add idempotency checks.

## General Tips

- Use `uvx pre-commit run --all-files` before pushing changes.
- Enable DEBUG logging temporarily via `LOG_LEVEL=DEBUG` to capture additional context.
- For persistent issues, snapshot logs and relevant database exports in `support/` for later analysis.

This guide replaces ColdWatch’s `TROUBLESHOOTING.md` and `docs/GTK_ACCESSIBILITY_WARNING.md` while broadening coverage to Watchman’s collectors.
