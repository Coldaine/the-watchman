# Testing Strategy

**Last Updated:** 2025-10-14

This strategy consolidates the former ColdWatch test philosophy with The Watchman’s domain-driven coverage needs.

## Principles

- Tests validate observable behavior (CLI output, graph state, queue contents) rather than implementation details.
- Favor realistic end-to-end scenarios using behavioral fakes over heavy mocking.
- Keep the suite fast by separating quick unit tests from slower integration pipelines.

## Test Layers

1. **Unit**: Pure functions, configuration parsing, redaction utilities, and Neo4j query builders.
2. **Service / Collector**: Runs collectors against fakes (e.g., fake AT-SPI bus, temp filesystem) to verify ingestion pipelines.
3. **Contract**: Ensures API routes (`/ask`, `/admin/*`) honor schemas and error handling.
4. **Trace & Performance**: Measures end-to-end latency (e.g., AT-SPI event to Neo4j write) and ensures rate limits enforce backpressure.
5. **End-to-End**: Launches a minimal stack (Neo4j + API + selected collectors) and exercises real workflows.

## Tooling

- `pytest` with markers: `unit`, `service`, `integration`, `gui`, `visual`, `ingest`.
- `pytest-asyncio` for async collectors and API tests.
- `pytest-xdist` to parallelize pure unit suites.
- Behavioral fakes located under `tests/fakes/` (AT-SPI, filesystem, Docker events).

## Running Tests

```bash
# Quick feedback (unit + service)
uvx pytest -m "unit or service"

# Include GUI and ingestion collectors (requires Linux + AT-SPI)
uvx pytest -m "integration"

# Full E2E stack with docker-compose
uvx pytest -m "e2e" --compose

# Linting and formatting checks
uvx pre-commit run --all-files
```

## Continuous Integration

- GitHub Actions workflow executes unit and service suites across Python 3.10–3.12.
- Optional integration job (Linux only) provisions AT-SPI dependencies and uploads artifacts (SQLite exports, screenshots, logs).
- Nightly scheduled run performs extended soak tests to detect flaky DBus or OCR failures.
- Coverage reports generated from Python 3.12 build.

## Performance Guardrails

- AT-SPI collector: p95 ingestion latency < 100 ms per event.
- Screenshot pipeline: OCR queue latency < 2 minutes under nominal load.
- File ingestion: Dedup batch completes within 30 seconds for 500 files.
- Regression tests assert metrics via log snapshots.

## Future Enhancements

- Add synthetic workloads for Neo4j stress testing (1M nodes / 5M relationships).
- Integrate OpenTelemetry for distributed tracing across collectors.
- Automate ingestion of archived ColdWatch SQLite databases for migration validation.

This document replaces ColdWatch’s `testing_philosophy.md`, `testing_strategy.md`, and `testing_cheatsheet.md` while factoring in The Watchman’s additional domains.
