# Deployment and Operations

## Overview
This document covers deployment strategies, operational procedures, monitoring, and maintenance for the Librarian Agent system. It provides runbooks for common operations and incident response procedures.

## Deployment Architecture

### Container Architecture
```yaml
# docker-compose.yml
version: '3.8'

services:
  neo4j:
    image: neo4j:5-community
    container_name: librarian-neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    volumes:
      - ./neo4j/data:/data
      - ./neo4j/logs:/logs
      - ./neo4j/conf:/conf
      - ./neo4j/plugins:/plugins
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2g
      - NEO4J_dbms_memory_pagecache_size=512m
    healthcheck:
      test: ["CMD", "wget", "-O", "-", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 3

  librarian-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: librarian-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    depends_on:
      neo4j:
        condition: service_healthy
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./docs:/app/docs:ro
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: librarian-ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ./ollama:/root/.ollama
    environment:
      - OLLAMA_MODELS=/root/.ollama/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]  # Optional: for GPU support
```

### Dockerfile
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Non-root user
RUN useradd -m -u 1000 librarian && \
    chown -R librarian:librarian /app
USER librarian

# Health check script
COPY scripts/health_check.py .

# Start application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
```

## Deployment Process

### Initial Deployment

```bash
#!/bin/bash
# deploy.sh - Initial deployment script

set -e

echo "Starting Librarian Agent deployment..."

# 1. Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "Error: Docker Compose not installed"
        exit 1
    fi

    # Check environment file
    if [ ! -f .env ]; then
        echo "Error: .env file not found"
        echo "Creating from template..."
        cp .env.template .env
        echo "Please update .env with your settings"
        exit 1
    fi
}

# 2. Prepare directories
prepare_directories() {
    echo "Creating directories..."
    mkdir -p neo4j/{data,logs,conf,plugins}
    mkdir -p logs
    mkdir -p config
    mkdir -p ollama
}

# 3. Pull embedding model
pull_embedding_model() {
    echo "Pulling embedding model..."
    docker run --rm -v ./ollama:/root/.ollama ollama/ollama \
        pull nomic-embed-text
}

# 4. Start services
start_services() {
    echo "Starting services..."
    docker-compose up -d

    # Wait for Neo4j
    echo "Waiting for Neo4j to be ready..."
    until docker exec librarian-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1" > /dev/null 2>&1; do
        sleep 5
    done
}

# 5. Initialize database
initialize_database() {
    echo "Initializing database schema..."
    docker exec librarian-api python -m src.init_db
}

# 6. Run health checks
run_health_checks() {
    echo "Running health checks..."
    curl -f http://localhost:8000/health || exit 1
    echo "Deployment successful!"
}

# Main execution
check_prerequisites
prepare_directories
pull_embedding_model
start_services
initialize_database
run_health_checks
```

### Update Deployment

```bash
#!/bin/bash
# update.sh - Update deployment script

set -e

echo "Updating Librarian Agent..."

# 1. Backup current state
backup() {
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR

    echo "Creating backup in $BACKUP_DIR..."

    # Backup Neo4j
    docker exec librarian-neo4j neo4j-admin database dump neo4j \
        --to-path=/backups/neo4j.dump

    # Copy configs
    cp -r config $BACKUP_DIR/

    echo "Backup completed"
}

# 2. Pull latest changes
update_code() {
    echo "Pulling latest code..."
    git pull origin main
}

# 3. Rebuild containers
rebuild() {
    echo "Rebuilding containers..."
    docker-compose build --no-cache librarian-api
}

# 4. Apply migrations
migrate() {
    echo "Applying database migrations..."
    docker exec librarian-api python -m src.migrations.apply
}

# 5. Restart services
restart() {
    echo "Restarting services..."
    docker-compose down
    docker-compose up -d
}

# 6. Verify
verify() {
    echo "Verifying deployment..."
    sleep 10
    curl -f http://localhost:8000/health || exit 1
}

# Main execution
backup
update_code
rebuild
migrate
restart
verify

echo "Update completed successfully!"
```

## Operational Procedures

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart librarian-api

# View logs
docker-compose logs -f librarian-api
docker-compose logs --tail=100 neo4j

# Execute commands in container
docker exec -it librarian-api bash
docker exec -it librarian-neo4j cypher-shell
```

### Database Operations

```bash
#!/bin/bash
# db-operations.sh

# Backup Neo4j
backup_neo4j() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    docker exec librarian-neo4j neo4j-admin database dump neo4j \
        --to-path=/backups/neo4j_$TIMESTAMP.dump
    echo "Backup created: neo4j_$TIMESTAMP.dump"
}

# Restore Neo4j
restore_neo4j() {
    BACKUP_FILE=$1
    docker exec librarian-neo4j neo4j-admin database load neo4j \
        --from-path=/backups/$BACKUP_FILE \
        --overwrite-destination=true
    echo "Restored from: $BACKUP_FILE"
}

# Clear test data
clear_test_data() {
    docker exec librarian-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
        "MATCH (n:TestNode) DETACH DELETE n"
}

# Optimize indexes
optimize_indexes() {
    docker exec librarian-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
        "CALL db.indexes() YIELD name CALL db.index.fulltext.drop(name)"
}
```

### Document Ingestion

```python
#!/usr/bin/env python
# ingest_documents.py - Manual document ingestion

import asyncio
import argparse
from pathlib import Path

async def ingest_directory(directory: str, pattern: str = "**/*.md"):
    """Manually ingest documents"""
    from src.document_processing import DocumentIngestionService

    service = DocumentIngestionService()

    print(f"Ingesting documents from {directory}")
    print(f"Pattern: {pattern}")

    report = await service.ingest_directory(
        directory=directory,
        pattern=pattern,
        recursive=True
    )

    print(f"\nIngestion Report:")
    print(f"Total files: {report.total_files}")
    print(f"Processed: {report.processed}")
    print(f"Failed: {report.failed}")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  - {error}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory to ingest")
    parser.add_argument("--pattern", default="**/*.md")
    args = parser.parse_args()

    asyncio.run(ingest_directory(args.directory, args.pattern))
```

## Monitoring

### Health Checks

```python
# health_check.py
from fastapi import FastAPI
from typing import Dict
import asyncio

app = FastAPI()

@app.get("/health")
async def health_check() -> Dict:
    """Comprehensive health check"""
    health = {
        "status": "healthy",
        "checks": {}
    }

    # Check Neo4j
    try:
        from src.graph import graph
        await graph.query("RETURN 1")
        health["checks"]["neo4j"] = "healthy"
    except Exception as e:
        health["checks"]["neo4j"] = f"unhealthy: {e}"
        health["status"] = "degraded"

    # Check Ollama
    try:
        from src.embeddings import embedder
        await embedder.health_check()
        health["checks"]["ollama"] = "healthy"
    except Exception as e:
        health["checks"]["ollama"] = f"unhealthy: {e}"
        health["status"] = "degraded"

    # Check disk space
    import shutil
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024**3)
    if free_gb < 1:
        health["checks"]["disk"] = f"low: {free_gb:.2f}GB free"
        health["status"] = "degraded"
    else:
        health["checks"]["disk"] = f"healthy: {free_gb:.2f}GB free"

    return health

@app.get("/metrics")
async def metrics() -> Dict:
    """System metrics"""
    from src.metrics import MetricsCollector

    collector = MetricsCollector()
    return {
        "requests": {
            "total": collector.total_requests,
            "success": collector.successful_requests,
            "failed": collector.failed_requests,
            "avg_response_time": collector.avg_response_time
        },
        "database": {
            "node_count": await collector.get_node_count(),
            "relationship_count": await collector.get_relationship_count(),
            "index_count": await collector.get_index_count()
        },
        "cache": {
            "hit_rate": collector.cache_hit_rate,
            "size": collector.cache_size
        }
    }
```

### Logging Configuration

```python
# logging_config.py
import logging
import logging.config
from pythonjsonlogger import jsonlogger

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": jsonlogger.JsonFormatter,
            "format": "%(timestamp)s %(level)s %(name)s %(message)s"
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "/app/logs/librarian.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "/app/logs/error.log",
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "loggers": {
        "src": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file", "error_file"]
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Monitoring Stack (Optional)

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    container_name: librarian-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana
    container_name: librarian-grafana
    ports:
      - "3000:3000"
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}

volumes:
  prometheus_data:
  grafana_data:
```

## Maintenance

### Scheduled Tasks

```python
# scheduled_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
async def nightly_backup():
    """Nightly backup task"""
    logger.info("Starting nightly backup...")
    from src.operations import backup_system
    await backup_system()
    logger.info("Nightly backup completed")

@scheduler.scheduled_job('interval', hours=1)
async def drift_detection():
    """Hourly drift detection"""
    logger.info("Running drift detection...")
    from src.validation import DriftDetector
    detector = DriftDetector()
    violations = await detector.detect_all_drift()
    if violations:
        logger.warning(f"Found {len(violations)} drift violations")

@scheduler.scheduled_job('cron', day_of_week='mon', hour=0, minute=0)
async def weekly_compliance_report():
    """Weekly compliance report"""
    logger.info("Generating weekly compliance report...")
    from src.audit import generate_compliance_report
    await generate_compliance_report()

@scheduler.scheduled_job('interval', minutes=30)
async def cleanup_old_sessions():
    """Clean up old sessions"""
    logger.info("Cleaning up old sessions...")
    from src.sessions import cleanup_expired
    count = await cleanup_expired()
    logger.info(f"Cleaned up {count} expired sessions")

def start_scheduler():
    """Start scheduled tasks"""
    scheduler.start()
    logger.info("Scheduler started")
```

### Performance Optimization

```python
#!/usr/bin/env python
# optimize_performance.py

async def optimize_neo4j():
    """Optimize Neo4j performance"""
    from src.graph import graph

    print("Optimizing Neo4j...")

    # Update statistics
    await graph.query("CALL db.stats.clear()")
    await graph.query("CALL db.stats.collect()")

    # Optimize indexes
    indexes = await graph.query("CALL db.indexes()")
    for index in indexes:
        if index['state'] != 'ONLINE':
            print(f"Rebuilding index: {index['name']}")
            await graph.query(f"DROP INDEX {index['name']}")
            # Recreate index...

    print("Optimization complete")

async def clear_cache():
    """Clear application caches"""
    from src.cache import cache_manager

    print("Clearing caches...")
    cache_manager.clear_all()
    print("Caches cleared")

async def vacuum_database():
    """Clean up database"""
    from src.graph import graph

    print("Vacuuming database...")

    # Remove orphaned nodes
    await graph.query("""
        MATCH (n)
        WHERE NOT (n)--()
        AND NOT n:Architecture
        AND NOT n:Design
        DELETE n
    """)

    # Remove old audit events
    await graph.query("""
        MATCH (e:AuditEvent)
        WHERE e.timestamp < datetime() - duration('P90D')
        AND e.severity = 'INFO'
        DELETE e
    """)

    print("Database vacuumed")
```

## Incident Response

### Runbooks

#### Service Down
```markdown
# Runbook: Service Down

## Symptoms
- API not responding
- Health check failing
- Connection errors

## Resolution Steps

1. **Check container status**
   ```bash
   docker-compose ps
   ```

2. **Check logs**
   ```bash
   docker-compose logs --tail=100 librarian-api
   ```

3. **Restart service**
   ```bash
   docker-compose restart librarian-api
   ```

4. **If persistent, check resources**
   ```bash
   docker stats
   df -h
   ```

5. **Check database connection**
   ```bash
   docker exec librarian-api python -c "from src.graph import graph; graph.health_check()"
   ```

## Escalation
If issue persists after restart, check:
- Database health
- Disk space
- Memory usage
- Network connectivity
```

#### High Memory Usage
```markdown
# Runbook: High Memory Usage

## Symptoms
- Container using >2GB RAM
- Slow response times
- OOM errors

## Resolution Steps

1. **Check memory usage**
   ```bash
   docker stats librarian-api
   ```

2. **Identify memory leak**
   ```bash
   docker exec librarian-api python -m src.debug.memory_profile
   ```

3. **Clear caches**
   ```bash
   docker exec librarian-api python -c "from src.cache import clear_all; clear_all()"
   ```

4. **Restart with increased memory**
   ```bash
   docker-compose down
   export MEMORY_LIMIT=4g
   docker-compose up -d
   ```

5. **Monitor**
   ```bash
   watch docker stats librarian-api
   ```
```

#### Database Performance Issues
```markdown
# Runbook: Database Performance Issues

## Symptoms
- Slow queries
- Timeouts
- High CPU on Neo4j

## Resolution Steps

1. **Check slow queries**
   ```cypher
   CALL dbms.listQueries()
   YIELD query, elapsedTimeMillis
   WHERE elapsedTimeMillis > 1000
   RETURN query, elapsedTimeMillis
   ```

2. **Kill long-running queries**
   ```cypher
   CALL dbms.listQueries()
   YIELD queryId, elapsedTimeMillis
   WHERE elapsedTimeMillis > 10000
   CALL dbms.killQuery(queryId)
   ```

3. **Update statistics**
   ```cypher
   CALL db.stats.clear();
   CALL db.stats.collect();
   ```

4. **Check indexes**
   ```cypher
   CALL db.indexes()
   YIELD name, state
   WHERE state <> 'ONLINE'
   RETURN name, state
   ```

5. **Restart Neo4j if needed**
   ```bash
   docker-compose restart neo4j
   ```
```

## Backup and Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Comprehensive backup script

BACKUP_ROOT="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p $BACKUP_DIR

# Backup Neo4j
echo "Backing up Neo4j..."
docker exec librarian-neo4j neo4j-admin database dump neo4j \
    --to-path=/backups/neo4j_$TIMESTAMP.dump

# Backup configurations
echo "Backing up configurations..."
tar -czf $BACKUP_DIR/config.tar.gz config/

# Backup Ollama models
echo "Backing up Ollama models..."
tar -czf $BACKUP_DIR/ollama.tar.gz ollama/

# Create manifest
cat > $BACKUP_DIR/manifest.json << EOF
{
    "timestamp": "$TIMESTAMP",
    "version": "$(git describe --tags --always)",
    "components": {
        "neo4j": "neo4j_$TIMESTAMP.dump",
        "config": "config.tar.gz",
        "ollama": "ollama.tar.gz"
    }
}
EOF

# Compress backup
tar -czf $BACKUP_ROOT/backup_$TIMESTAMP.tar.gz -C $BACKUP_ROOT $TIMESTAMP

# Clean up old backups (keep last 7 days)
find $BACKUP_ROOT -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: backup_$TIMESTAMP.tar.gz"
```

### Recovery Procedure

```bash
#!/bin/bash
# recover.sh - Recovery from backup

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./recover.sh backup_TIMESTAMP.tar.gz"
    exit 1
fi

echo "Recovering from $BACKUP_FILE..."

# Extract backup
tar -xzf $BACKUP_FILE

# Stop services
docker-compose down

# Restore Neo4j
docker run --rm \
    -v $(pwd)/neo4j/data:/data \
    -v $(pwd)/backups:/backups \
    neo4j:5-community \
    neo4j-admin database load neo4j \
    --from-path=/backups/neo4j.dump \
    --overwrite-destination=true

# Restore configurations
tar -xzf config.tar.gz -C /

# Restore Ollama models
tar -xzf ollama.tar.gz -C /

# Start services
docker-compose up -d

echo "Recovery completed"
```

## Security Operations

### Security Checklist

```yaml
# security-checklist.yml
security:
  network:
    - [ ] Firewall configured
    - [ ] Only necessary ports exposed
    - [ ] HTTPS enabled for API
    - [ ] Network isolation between containers

  authentication:
    - [ ] Strong Neo4j password
    - [ ] API key authentication enabled
    - [ ] Rate limiting configured
    - [ ] Session timeout set

  data:
    - [ ] Backups encrypted
    - [ ] Sensitive data masked in logs
    - [ ] PII handling compliant

  monitoring:
    - [ ] Security events logged
    - [ ] Audit trail enabled
    - [ ] Alerts configured for anomalies
```

### Security Updates

```bash
#!/bin/bash
# security_update.sh

# Update base images
docker pull neo4j:5-community
docker pull python:3.11-slim
docker pull ollama/ollama:latest

# Rebuild with latest security patches
docker-compose build --no-cache

# Update Python dependencies
docker exec librarian-api pip list --outdated
docker exec librarian-api pip install --upgrade -r requirements.txt

# Restart services
docker-compose down
docker-compose up -d
```

## References

- **Docker Documentation**: https://docs.docker.com/
- **Neo4j Operations Manual**: https://neo4j.com/docs/operations-manual/current/
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **12-Factor App**: https://12factor.net/
- **SRE Practices**: https://sre.google/sre-book/