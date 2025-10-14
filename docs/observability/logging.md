# Logging Standards

**Last Updated:** 2025-10-14

## Overview

Logging is centralized around Loguru for Python services. The goals are consistent structured output, actionable debugging information, and production-ready observability.

## Configuration

- Global setup provided by `app/logging/setup.py` (to be implemented) initializes Loguru.
- Default sinks:
  - JSON to stdout for containerized deployments (`enqueue=True` for async safety).
  - Optional rotating file sink for local development.
  - Optional syslog or Loki exporter via configuration.
- Environment-driven configuration keys:
  - `LOG_LEVEL`: default `INFO`.
  - `LOG_FORMAT`: `json` or `console`.
  - `LOG_DESTINATION`: comma-separated sinks (`stdout,file,loki`).
  - `LOG_DEBUG_SAMPLE_RATE`: sample factor for high-volume DEBUG logs.

## Message Structure

Every log entry should include:

- `timestamp`
- `level`
- `message`
- `collector` or `component`
- `trace_id` / `request_id`
- `event_source` (AT-SPI, screenshot, ingestion, API, automation)
- Optional contextual fields (e.g., `app`, `path`, `object_id`, `hash`)

### Correlation IDs

- API layer injects `request_id` for HTTP requests.
- Collectors generate `trace_id` per batch and propagate to Neo4j writes.
- Automation runner reuses IDs from triggering events.

## Log Level Guidance

| Level   | Usage Example                                                   |
|---------|-----------------------------------------------------------------|
| DEBUG   | Detailed reasoning for collectors, queue depth metrics          |
| INFO    | Startup/shutdown, successful batch summaries, configuration load |
| WARNING | Retriable errors, degraded external dependencies                 |
| ERROR   | Failed operations impacting end users or data integrity          |
| CRITICAL| System-wide failures requiring immediate attention               |

## Sensitive Data Handling

- Never log raw GUI text or OCR content. Use hashes or redacted snippets.
- Strip secrets via shared redaction utilities before logging.
- Mark logs containing potentially sensitive metadata with `"sensitive": true`.

## Collector Patterns

- Each collector logs lifecycle events: starting, configuration summary, graceful shutdown.
- Batch operations log counts and durations (`items_processed`, `elapsed_ms`).
- Rate-limited error logging prevents floods (Loguru `filter`/`patch` or custom throttling).
- Neo4j interactions logged with query type and latency (avoid full query text in production).

## Development Experience

- Console sink enabled when `LOG_FORMAT=console`; colored output aids debugging.
- `--verbose` CLI flag toggles DEBUG level.
- Local `.env.development` template documents recommended logging settings.

## Monitoring & Metrics

- Convert key metrics to logs (`events_per_sec`, `queue_length`, `retry_count`).
- Future enhancement: expose Prometheus metrics sidecar and correlate IDs.
- Alerting derives from log queries (e.g., `ERROR` rate over time, missing heartbeat logs).

## Quality Controls

- Pre-commit hook checks for `print()` usage and bare `logging` calls.
- Unit tests validate correlation ID propagation and redaction helpers.
- Integration tests assert logs emit expected JSON structure.

This document supersedes standalone logging plans and should be kept in sync with implementation changes.
