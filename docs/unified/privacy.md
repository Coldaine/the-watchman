# Privacy & Data Handling

**Last Updated:** 2025-10-14

## Core Principles

- Operate entirely on the local machine; no external transmission of captured data.
- Provide clear controls for what is captured, how long it is retained, and who can access it.
- Default to the minimum necessary retention and redact sensitive content by design.

## Capture Controls

### GUI Events

- `ENABLE_GUI_COLLECTOR` defaults to `false`. When enabled, `capture_text` controls whether raw widget text is stored.
- Text content is hashed before persistence; storing raw text is optional and governed by `GUI_COLLECTOR_CAPTURE_TEXT`.
- Allow- and deny-lists exist for applications, roles, and window titles.

### Screenshots & OCR

- Screenshot cadence, capture hotkeys, and pause rules (e.g., full-screen apps) are configurable.
- OCR text inherits the same redaction pipeline used by GUI events.
- Raw images and OCR text can have independent retention windows.

### File Ingestion

- Downloads ingestion respects `MIN_FILE_AGE_SEC` to avoid capturing partially written files.
- SHA-256 hashes identify duplicates without needing content inspection.
- `EXCLUDE_PATHS` and `EXCLUDE_EXTENSIONS` prevent processing of sensitive directories or file types.

## Redaction & Masking

1. **Regex-based redaction**: Email addresses, tokens, secrets, and other sensitive patterns are stripped or replaced with hashes prior to logging or persistence.
2. **Application-level exclusions**: GUI collector skips applications on the deny-list; screenshot collector can blur or skip configured windows.
3. **Selective storage**: For high-risk domains (password managers, messaging apps), collectors may store only metadata such as timestamps and hashes.

## Retention Policies

| Data Type             | Default | Configuration Key                     |
|-----------------------|---------|---------------------------------------|
| Raw screenshots       | 14 days | `SCREENSHOT_RETENTION_DAYS`           |
| OCR text chunks       | 90 days | `OCR_RETENTION_DAYS`                  |
| GUI raw text          | 0 days (disabled) | `GUI_RAW_TEXT_RETENTION_DAYS` |
| Ingested documents    | Until routed/manual | `INGEST_RETENTION_DAYS`    |
| Event nodes in Neo4j  | Infinite (prune via Cypher job) | `EVENT_TTL_DAYS` |

A scheduled cleanup task removes expired nodes and files. Cleanup scripts live under `scripts/maintenance/`.

## Access & Permissions

- Running containers drop privileges where possible and use dedicated service accounts.
- Data directories (`/var/lib/watchman/...`) are restricted to the service user.
- Optional encryption-at-rest is supported via filesystem-level tooling (LUKS, dm-crypt) or database-level encryption.

## Logging & Auditing

- Logs never include raw captured content. Hashes or redacted placeholders are used instead.
- Access to admin endpoints and configuration changes is logged with user identity and timestamp.
- Audit scripts can export summaries of captured data without exposing full contents.

## Incident Response

1. Disable collectors via environment toggles.
2. Run cleanup scripts to purge sensitive datasets.
3. Rotate any derived keys or tokens stored in configuration.
4. Review logs for unauthorized access or configuration changes.

This policy supersedes the standalone `coldwatch/PRIVACY.md` guidance and applies to all Watchman collectors.
