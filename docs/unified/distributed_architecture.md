# Distributed Architecture: Multi-Machine Watchman

**Last Updated:** 2025-11-11

This document describes The Watchman's **distributed architecture** for managing multiple computers with a master/satellite topology, always-on queue services, and automated machine provisioning.

## Overview

The Watchman operates in three modes:

1. **Master Mode** - Full installation with Neo4j, all collectors, and the complete knowledge graph
2. **Satellite Mode** - Lightweight collector that forwards data to a master
3. **Queue Mode** - Always-on buffer service (e.g., Raspberry Pi) that queues data when master is offline

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Master Watchman                          │
│                   (Primary Dev Machine)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Neo4j     │  │  All Domains │  │  /ask API       │   │
│  │  Database   │  │  Collectors  │  │  Query Engine   │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────▲────────────────────────────────────┘
                         │
                         │ Data Forwarding (HTTPS/gRPC)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│  Satellite   │  │  Satellite   │  │  Always-On Queue     │
│  (Laptop)    │  │  (Work PC)   │  │  (Raspberry Pi)      │
│              │  │              │  │                      │
│ - Collectors │  │ - Collectors │  │ - Redis Queue        │
│ - No Neo4j   │  │ - No Neo4j   │  │ - Batch Forwarder    │
│ - Forwards   │  │ - Forwards   │  │ - Health Monitor     │
└──────────────┘  └──────────────┘  └──────────────────────┘
      │                 │                      │
      │                 │                      │
      └─────────────────┴──────────────────────┘
                        │
                        ▼ When master offline
                  Queued for later delivery
```

## Master Mode (Full Installation)

**Location:** Primary development machine, always-on server, or cloud instance

### Characteristics

- **Full Neo4j database** - Complete knowledge graph
- **All collectors enabled** - Visual timeline, system graph, events, MCP, file ingest, GUI
- **API server** - `/ask` endpoint, admin endpoints, MCP orchestration
- **Data ingestion** - Receives data from satellites
- **Query interface** - Primary interface for user queries
- **MCP orchestration** - Manages all MCP servers

### Configuration

```toml
[mode]
type = "master"
instance_id = "master-dev-machine"
listen_address = "0.0.0.0:8000"
enable_ingestion = true  # Accept data from satellites

[master]
# TLS for secure satellite connections
tls_enabled = true
tls_cert = "/etc/watchman/certs/master.crt"
tls_key = "/etc/watchman/certs/master.key"

# Authentication for satellites
satellite_auth_enabled = true
satellite_tokens_file = "/etc/watchman/satellite_tokens.yaml"

# Always-on queue service
queue_service_enabled = true
queue_service_url = "https://queue.home.lan:8001"
queue_poll_interval = 60  # seconds
```

### API Endpoints (Master-Only)

```bash
# Accept data from satellites
POST /ingest/batch
Headers: Authorization: Bearer <satellite_token>
Body: {
  "satellite_id": "laptop-work",
  "timestamp": "2025-11-11T14:30:00Z",
  "events": [
    {
      "type": "snapshot",
      "data": {...},
      "timestamp": "2025-11-11T14:29:45Z"
    },
    {
      "type": "package_install",
      "data": {...},
      "timestamp": "2025-11-11T14:30:00Z"
    }
  ]
}

# Query satellite status
GET /satellites/status
Response: [
  {
    "id": "laptop-work",
    "status": "online",
    "last_seen": "2025-11-11T14:30:00Z",
    "events_queued": 0,
    "version": "1.0.0"
  },
  {
    "id": "work-desktop",
    "status": "offline",
    "last_seen": "2025-11-10T18:00:00Z",
    "events_queued": 145
  }
]

# Register new satellite
POST /satellites/register
Body: {
  "name": "new-laptop",
  "hostname": "laptop-2",
  "mac_address": "aa:bb:cc:dd:ee:ff"
}
Response: {
  "satellite_id": "new-laptop-abc123",
  "auth_token": "sat_xyz789...",
  "config": {...}
}
```

---

## Satellite Mode (Lightweight Collector)

**Location:** Secondary machines (laptops, work desktops, etc.)

### Characteristics

- **No Neo4j** - No local database
- **Collectors only** - Visual timeline, system graph, events (configurable subset)
- **Forward to master** - All data sent to master via HTTPS/gRPC
- **Offline buffering** - Queue data locally when master unreachable
- **Minimal footprint** - ~200MB memory, low CPU usage
- **Auto-registration** - Discover and register with master on first boot

### Configuration

```toml
[mode]
type = "satellite"
instance_id = "laptop-work"
master_url = "https://watchman.home.lan:8000"
auth_token = "sat_xyz789..."  # From master registration

[satellite]
# Retry policy
retry_enabled = true
retry_max_attempts = 5
retry_backoff = "exponential"  # 2s, 4s, 8s, 16s, 32s

# Offline buffering
buffer_enabled = true
buffer_dir = "/var/lib/watchman/buffer"
buffer_max_size_mb = 1000  # Discard oldest if exceeded
buffer_flush_interval = 60  # seconds

# Data forwarding
forward_batch_size = 100  # Events per batch
forward_compression = true  # gzip

# Collectors (subset)
[features]
visual_timeline = true
system_graph = true
event_tracking = true
gui_collector = false  # Disable on low-power devices
file_ingest = false
mcp_registry = false  # Only master manages MCPs
```

### Data Forwarding

**Push Model** (Default)
```python
class SatelliteForwarder:
    """Forward collected data to master."""

    async def forward_batch(self, events: List[Event]):
        """Send batch to master."""
        payload = {
            "satellite_id": self.instance_id,
            "timestamp": now_iso(),
            "events": [e.to_dict() for e in events]
        }

        try:
            response = await self.http_client.post(
                f"{self.master_url}/ingest/batch",
                json=payload,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=30
            )
            response.raise_for_status()
            self.mark_events_sent(events)
        except Exception as e:
            logger.warning(f"Forward failed: {e}, buffering locally")
            self.buffer_events(events)
```

**Offline Buffering**
```python
class EventBuffer:
    """Local buffer for when master is unreachable."""

    def buffer_events(self, events: List[Event]):
        """Write events to disk buffer."""
        buffer_file = self.buffer_dir / f"batch_{uuid4()}.json.gz"
        with gzip.open(buffer_file, "wt") as f:
            json.dump([e.to_dict() for e in events], f)

    async def flush_buffer(self):
        """Send buffered events when master comes back online."""
        buffer_files = sorted(self.buffer_dir.glob("batch_*.json.gz"))

        for buffer_file in buffer_files:
            with gzip.open(buffer_file, "rt") as f:
                events = json.load(f)

            try:
                await self.forwarder.forward_batch(events)
                buffer_file.unlink()  # Delete after successful send
            except Exception:
                break  # Master still down, try again later
```

### Satellite Health Monitoring

Satellites send periodic heartbeats to master:

```python
async def send_heartbeat(self):
    """Send health status to master."""
    status = {
        "satellite_id": self.instance_id,
        "timestamp": now_iso(),
        "status": "healthy",
        "collectors": {
            "visual_timeline": {"status": "running", "events_captured": 145},
            "system_graph": {"status": "running", "last_scan": "2025-11-11T14:00:00Z"},
            "event_tracking": {"status": "running", "events_tracked": 892}
        },
        "buffer": {
            "events_queued": 0,
            "size_mb": 0,
            "oldest_event": None
        },
        "system": {
            "cpu_percent": 5.2,
            "memory_mb": 180,
            "disk_free_gb": 450
        }
    }

    await self.http_client.post(
        f"{self.master_url}/satellites/heartbeat",
        json=status,
        headers={"Authorization": f"Bearer {self.auth_token}"}
    )
```

---

## Queue Mode (Always-On Buffer Service)

**Location:** Raspberry Pi, NAS, or always-on home server

### Purpose

When the master is offline (e.g., primary dev machine shut down), the queue service:
1. Accepts data from satellites
2. Buffers to Redis or disk
3. Forwards to master when it comes back online
4. Ensures no data loss

### Characteristics

- **No collectors** - Pure queue/buffer service
- **Redis queue** - Fast in-memory buffering with disk persistence
- **Master detection** - Poll master for availability
- **Automatic forwarding** - Flush queue when master online
- **Low power** - Runs on Raspberry Pi 4 (2GB RAM)

### Configuration

```toml
[mode]
type = "queue"
instance_id = "queue-raspi"
listen_address = "0.0.0.0:8001"

[queue]
# Redis for buffering
redis_url = "redis://localhost:6379"
redis_queue_key = "watchman:queue"
redis_max_memory_mb = 500

# Disk overflow (if Redis full)
disk_overflow_enabled = true
disk_overflow_dir = "/mnt/storage/watchman/queue"
disk_overflow_max_gb = 10

# Master forwarding
master_url = "https://watchman.home.lan:8000"
master_auth_token = "queue_token_abc123"
master_poll_interval = 60  # Check if master is online
flush_batch_size = 500
flush_interval = 30  # seconds (when master online)

# Health monitoring
health_check_enabled = true
alert_on_queue_size_mb = 800  # Alert if queue growing too large
```

### Queue Service Implementation

```python
class QueueService:
    """Always-on queue service for buffering satellite data."""

    def __init__(self):
        self.redis = redis.Redis.from_url(settings.queue_redis_url)
        self.master_online = False

    async def accept_data(self, satellite_id: str, events: List[dict]):
        """Accept data from satellite and queue."""
        for event in events:
            event["_satellite_id"] = satellite_id
            event["_queued_at"] = now_iso()

            # Push to Redis queue
            self.redis.rpush(
                settings.queue_redis_queue_key,
                json.dumps(event)
            )

        logger.info(f"Queued {len(events)} events from {satellite_id}")

    async def check_master(self):
        """Poll master for availability."""
        try:
            response = await self.http_client.get(
                f"{settings.queue_master_url}/health",
                timeout=5
            )
            self.master_online = response.status_code == 200
        except Exception:
            self.master_online = False

    async def flush_to_master(self):
        """Forward queued events to master."""
        if not self.master_online:
            return

        batch = []
        for _ in range(settings.queue_flush_batch_size):
            event_json = self.redis.lpop(settings.queue_redis_queue_key)
            if not event_json:
                break
            batch.append(json.loads(event_json))

        if not batch:
            return

        try:
            response = await self.http_client.post(
                f"{settings.queue_master_url}/ingest/batch",
                json={
                    "satellite_id": "queue-service",
                    "timestamp": now_iso(),
                    "events": batch
                },
                headers={"Authorization": f"Bearer {settings.queue_master_auth_token}"}
            )
            response.raise_for_status()
            logger.success(f"Flushed {len(batch)} events to master")
        except Exception as e:
            # Put events back in queue
            for event in reversed(batch):
                self.redis.lpush(settings.queue_redis_queue_key, json.dumps(event))
            logger.warning(f"Flush failed: {e}, events re-queued")

    async def run(self):
        """Main queue service loop."""
        while True:
            await self.check_master()
            if self.master_online:
                await self.flush_to_master()
            await asyncio.sleep(settings.queue_flush_interval)
```

### Queue Service API

```bash
# Accept data from satellites
POST /queue/ingest
Headers: Authorization: Bearer <satellite_token>
Body: {
  "satellite_id": "laptop-work",
  "events": [...]
}

# Queue status
GET /queue/status
Response: {
  "queue_size": 1450,
  "queue_size_mb": 12.5,
  "oldest_event": "2025-11-11T08:00:00Z",
  "master_online": false,
  "last_flush": "2025-11-11T12:00:00Z"
}
```

---

## Machine Provisioning & Configuration

The Watchman can **provision new machines** by:
1. Generating configuration for a new satellite/queue instance
2. Installing required software
3. Configuring collectors
4. Registering with master

### Provisioning Workflow

```bash
# On master: Generate config for new machine
POST /admin/provision/create
Body: {
  "name": "new-laptop",
  "mode": "satellite",
  "hostname": "laptop-personal",
  "collectors": ["visual_timeline", "system_graph", "event_tracking"],
  "master_url": "https://watchman.home.lan:8000"
}

Response: {
  "provision_id": "prov_abc123",
  "config_url": "https://watchman.home.lan:8000/provision/prov_abc123/config.toml",
  "install_script": "https://watchman.home.lan:8000/provision/prov_abc123/install.sh",
  "auth_token": "sat_newlaptop_xyz789"
}

# On new machine: Run install script
curl -fsSL https://watchman.home.lan:8000/provision/prov_abc123/install.sh | bash

# Install script does:
# 1. Install Docker & Docker Compose
# 2. Download config.toml
# 3. Pull watchman-satellite Docker image
# 4. Start satellite service
# 5. Auto-register with master
```

### Provisioning Configuration Generator

```python
class ProvisioningService:
    """Generate configurations for new machines."""

    async def create_provision(
        self,
        name: str,
        mode: str,
        collectors: List[str]
    ) -> dict:
        """Generate config and auth for new machine."""

        # Generate auth token
        auth_token = f"sat_{name}_{secrets.token_urlsafe(32)}"

        # Create config.toml
        config = self.generate_config(
            name=name,
            mode=mode,
            collectors=collectors,
            auth_token=auth_token
        )

        # Store provision record
        provision_id = f"prov_{uuid4().hex[:12]}"
        self.store_provision(provision_id, config, auth_token)

        # Register satellite in Neo4j
        self.register_satellite(name, auth_token)

        return {
            "provision_id": provision_id,
            "config_url": f"{self.base_url}/provision/{provision_id}/config.toml",
            "install_script": f"{self.base_url}/provision/{provision_id}/install.sh",
            "auth_token": auth_token
        }

    def generate_config(self, name: str, mode: str, collectors: List[str], auth_token: str) -> str:
        """Generate config.toml for new instance."""
        config = f"""
[mode]
type = "{mode}"
instance_id = "{name}"
master_url = "{self.master_url}"
auth_token = "{auth_token}"

[satellite]
retry_enabled = true
buffer_enabled = true
buffer_dir = "/var/lib/watchman/buffer"

[features]
"""
        for collector in collectors:
            config += f"{collector} = true\n"

        # Disable features not in collectors list
        all_features = ["visual_timeline", "system_graph", "event_tracking", "gui_collector", "file_ingest"]
        for feature in all_features:
            if feature not in collectors:
                config += f"{feature} = false\n"

        return config
```

### Install Script Template

```bash
#!/bin/bash
# The Watchman - Satellite Installation Script
# Generated: 2025-11-11T14:30:00Z
# Provision ID: prov_abc123

set -e

echo "Installing The Watchman (Satellite Mode)..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || {
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
}

# Download configuration
mkdir -p /etc/watchman
curl -fsSL "https://watchman.home.lan:8000/provision/prov_abc123/config.toml" \
    -o /etc/watchman/config.toml

# Pull Docker image
docker pull watchman/satellite:latest

# Create docker-compose.yml
cat > /etc/watchman/docker-compose.yml <<'EOF'
version: '3.8'
services:
  watchman-satellite:
    image: watchman/satellite:latest
    container_name: watchman-satellite
    restart: unless-stopped
    volumes:
      - /etc/watchman/config.toml:/app/config.toml:ro
      - /var/lib/watchman:/var/lib/watchman
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - DISPLAY=${DISPLAY}
    network_mode: host
EOF

# Start service
cd /etc/watchman
docker-compose up -d

echo "Installation complete!"
echo "Satellite is now running and will auto-register with master."
```

---

## Graph Schema for Distributed Architecture

```cypher
# Satellite node
CREATE CONSTRAINT satellite_id IF NOT EXISTS
FOR (s:Satellite) REQUIRE s.id IS UNIQUE;

(:Satellite {
  id: "laptop-work",
  name: "Work Laptop",
  hostname: "laptop-thinkpad",
  mac_address: "aa:bb:cc:dd:ee:ff",
  mode: "satellite",
  status: "online",
  registered_at: datetime(),
  last_seen: datetime(),
  version: "1.0.0",
  master_url: "https://watchman.home.lan:8000"
})

# Queue service node
(:QueueService {
  id: "queue-raspi",
  hostname: "raspberrypi",
  status: "running",
  queue_size: 1450,
  queue_size_mb: 12.5,
  master_online: false
})

# Relationships
(:Master)-[:MANAGES]->(:Satellite)
(:Satellite)-[:FORWARDS_TO]->(:Master)
(:Satellite)-[:BUFFERS_VIA]->(:QueueService)
(:QueueService)-[:FORWARDS_TO]->(:Master)

# Events track source satellite
(:Event {
  source_satellite: "laptop-work",
  collected_at: datetime(),  # When satellite collected
  ingested_at: datetime()    # When master received
})-[:COLLECTED_BY]->(:Satellite)
```

## Configuration Examples

### Master (Primary Dev Machine)

```toml
[mode]
type = "master"
instance_id = "master-dev"

[neo4j]
uri = "bolt://localhost:7687"

[features]
# All features enabled
visual_timeline = true
system_graph = true
event_tracking = true
gui_collector = true
file_ingest = true
mcp_registry = true

[master]
enable_ingestion = true
satellite_auth_enabled = true
```

### Satellite (Laptop)

```toml
[mode]
type = "satellite"
instance_id = "laptop-work"
master_url = "https://watchman.home.lan:8000"

[features]
# Lightweight collectors only
visual_timeline = true
system_graph = true
event_tracking = true
gui_collector = false
file_ingest = false
mcp_registry = false
```

### Queue (Raspberry Pi)

```toml
[mode]
type = "queue"
instance_id = "queue-raspi"

[queue]
redis_url = "redis://localhost:6379"
master_url = "https://watchman.home.lan:8000"
master_poll_interval = 60

[features]
# No collectors, pure queue
visual_timeline = false
system_graph = false
event_tracking = false
```

## Implementation Roadmap

### Phase 1: Core Distributed Features
- [ ] Mode detection (master/satellite/queue)
- [ ] Satellite data forwarding
- [ ] Master ingestion endpoint
- [ ] Offline buffering
- [ ] Satellite heartbeats

### Phase 2: Queue Service
- [ ] Always-on queue service
- [ ] Redis integration
- [ ] Master availability polling
- [ ] Automatic flush to master

### Phase 3: Provisioning
- [ ] Config generation API
- [ ] Install script templates
- [ ] Auto-registration
- [ ] Satellite discovery

### Phase 4: Management
- [ ] Satellite dashboard
- [ ] Remote satellite control
- [ ] Health monitoring
- [ ] Unified queries across satellites

## Security Considerations

- **TLS Required**: All satellite-to-master communication over HTTPS
- **Token-based Auth**: Each satellite has unique token
- **Token Rotation**: Periodic token refresh
- **Network Isolation**: Satellites can't access each other
- **Rate Limiting**: Prevent satellite DoS of master
- **Data Encryption**: Optional encryption of buffered data at rest

## Resource Requirements

| Mode | CPU | Memory | Disk | Network |
|------|-----|--------|------|---------|
| Master | 4 cores | 8GB | 500GB SSD | 100Mbps |
| Satellite | 2 cores | 2GB | 50GB | 10Mbps |
| Queue | 1 core | 1GB | 20GB + buffer | 10Mbps |
