# System Management & Infrastructure Domain

**Last Updated:** 2025-11-11

This document enumerates **all system management responsibilities** that fall under The Watchman's domain. The Watchman serves as the **central orchestrator** for monitoring, configuring, and managing the entire computing environment.

## Core Principle

**The Watchman is the single source of truth for:**
- What's installed on the system
- What's running and its health status
- What changed and when
- System configuration state
- Network topology and connectivity
- Backup and disaster recovery status
- MCP server lifecycle

## Domain Coverage

### 1. Software Installation Monitoring ✅ **DOCUMENTED**

**Location:** `domains/memory_change/watchers/packages.py`

**Responsibilities:**
- Monitor package manager logs (`/var/log/dnf.log`, `/var/log/apt/history.log`, `/var/log/brew.log`)
- Track installations, updates, and removals
- Create `:Event` nodes for every package change
- Link to `:Software` nodes

**Graph Schema:**
```cypher
(:Event {
  id: "evt_123",
  ts: datetime(),
  type: "package_install",
  package_name: "docker-ce",
  version: "24.0.7",
  source: "dnf"
})-[:ACTED_ON]->(:Software {key: "docker-ce"})
```

**Queries:**
- "What was installed this week?"
- "When was docker last updated?"
- "Show me all Python packages installed in the last month"

**Status:** Implementation planned in Phase 1 (Stream C)

---

### 2. Network Monitoring & Configuration 🟡 **PARTIAL**

**Current Coverage:**
- Container port mappings (`:NetworkEndpoint` nodes)
- Exposed services discovery

**Missing Coverage:**
- System-level network interfaces
- Firewall rules (iptables, ufw, firewalld)
- DNS configuration
- VPN status and routing
- Network performance metrics
- Bandwidth usage tracking

**Proposed Implementation:**

#### 2.1 Network Topology Scanner

**Location:** `domains/system_graph/scanners/network.py`

```python
class NetworkScanner:
    """Discover and map network configuration."""

    def scan_interfaces(self):
        """Scan network interfaces via ip/ifconfig."""
        # ip addr show
        # Create :NetworkInterface nodes
        pass

    def scan_routes(self):
        """Scan routing table."""
        # ip route show
        # Create :Route nodes
        pass

    def scan_firewall(self):
        """Scan firewall rules."""
        # iptables -L, ufw status, firewall-cmd --list-all
        # Create :FirewallRule nodes
        pass

    def scan_dns(self):
        """Scan DNS configuration."""
        # /etc/resolv.conf, systemd-resolved
        # Create :DNSServer nodes
        pass

    def scan_vpn(self):
        """Detect active VPN connections."""
        # Check wireguard, openvpn, tailscale status
        # Create :VPNConnection nodes
        pass
```

**Graph Schema:**
```cypher
# Network interface
(:NetworkInterface {
  name: "eth0",
  mac_address: "00:1a:2b:3c:4d:5e",
  ip_addresses: ["192.168.1.100", "fe80::1"],
  state: "UP",
  mtu: 1500
})

# Firewall rule
(:FirewallRule {
  chain: "INPUT",
  rule_num: 1,
  target: "ACCEPT",
  protocol: "tcp",
  port: 22,
  source: "0.0.0.0/0"
})

# DNS server
(:DNSServer {
  ip: "8.8.8.8",
  port: 53,
  provider: "Google"
})-[:USED_BY]->(:NetworkInterface)

# VPN connection
(:VPNConnection {
  type: "wireguard",
  interface: "wg0",
  peer_endpoint: "vpn.example.com:51820",
  status: "active",
  connected_at: datetime()
})
```

**Queries:**
- "What's my external IP?"
- "Show firewall rules for port 443"
- "Is my VPN active?"
- "What DNS servers am I using?"

**Status:** 🔴 **NOT IMPLEMENTED** - Needs full specification

#### 2.2 Network Change Tracking

**Location:** `domains/memory_change/watchers/network.py`

- Monitor interface up/down events
- Track firewall rule changes
- Detect VPN connect/disconnect
- Alert on DNS changes

---

### 3. Backup Management 🔴 **NOT DOCUMENTED**

**Proposed Domain:** `domains/backup_manager/`

The Watchman should be responsible for:
1. **Backup orchestration** - Triggering backup jobs
2. **Backup verification** - Ensuring backups completed successfully
3. **Backup inventory** - Tracking what's backed up and where
4. **Recovery testing** - Periodic restore dry-runs
5. **Retention management** - Purging old backups per policy

#### 3.1 Backup Strategy

**Local Backups:**
- Neo4j database dumps
- Configuration files (`/etc`, `~/.config`)
- Project directories
- Docker volumes
- MCP server state

**Remote Backups:**
- S3-compatible storage (MinIO, AWS S3, Backblaze B2)
- Rsync to remote server
- Git repositories (auto-commit configs)

#### 3.2 Backup Orchestrator

**Location:** `domains/backup_manager/orchestrator.py`

```python
class BackupOrchestrator:
    """Manage backup jobs across the system."""

    async def backup_neo4j(self):
        """Dump Neo4j database."""
        # docker exec neo4j neo4j-admin dump
        # Upload to S3
        # Create :Backup node
        pass

    async def backup_configs(self):
        """Backup configuration files."""
        # tar /etc, ~/.config, ~/.ssh
        # Encrypt with age
        # Upload to S3
        pass

    async def backup_docker_volumes(self):
        """Backup Docker volumes."""
        # docker run --rm -v vol:/volume -v /backup:/backup alpine tar czf ...
        pass

    async def backup_projects(self, selective=True):
        """Backup project directories."""
        if selective:
            # Only backup projects modified in last 7 days
            pass
        pass

    async def verify_backup(self, backup_id: str):
        """Verify backup integrity."""
        # Download from S3
        # Verify checksum
        # Test restore (dry-run)
        pass
```

**Graph Schema:**
```cypher
# Backup job
(:BackupJob {
  id: "backup_123",
  type: "neo4j_dump",
  started_at: datetime(),
  completed_at: datetime(),
  status: "success",
  size_bytes: 1024000,
  checksum: "sha256:abc123...",
  storage_location: "s3://backups/neo4j-2025-11-11.dump",
  retention_days: 90
})

# Backup relationship
(:BackupJob)-[:BACKED_UP]->(:Database {name: "neo4j"})
(:BackupJob)-[:STORED_IN]->(:StorageLocation {provider: "s3", bucket: "watchman-backups"})

# Recovery point
(:RecoveryPoint {
  timestamp: datetime(),
  includes: ["neo4j", "configs", "docker_volumes"],
  tested: true,
  test_date: datetime()
})
```

**Configuration:**
```toml
[backup]
enabled = true
schedule = "0 2 * * *"  # Daily at 2 AM
storage_provider = "s3"
encryption_enabled = true

[backup.neo4j]
enabled = true
retention_days = 90
compression = "gzip"

[backup.configs]
enabled = true
paths = ["/etc", "~/.config", "~/.ssh"]
retention_days = 365

[backup.docker_volumes]
enabled = true
exclude = ["cache_vol", "tmp_vol"]
retention_days = 30

[backup.s3]
endpoint = "https://s3.amazonaws.com"
bucket = "watchman-backups"
region = "us-east-1"
access_key_id = ""  # From env: AWS_ACCESS_KEY_ID
secret_access_key = ""  # From env: AWS_SECRET_ACCESS_KEY
```

**API Endpoints:**
```bash
# Trigger backup
POST /admin/backup/trigger
Body: {"type": "full", "priority": "high"}

# List backups
GET /admin/backup/list?type=neo4j&days=30

# Verify backup
POST /admin/backup/verify/{backup_id}

# Restore from backup (requires confirmation)
POST /admin/backup/restore/{backup_id}
Body: {"target": "neo4j", "confirm": "I understand this will overwrite current data"}

# Test recovery
POST /admin/backup/test-recovery/{backup_id}
```

**Queries:**
- "When was the last Neo4j backup?"
- "Show backups from last week"
- "Which backups failed in the last month?"
- "What's the total size of backups?"

**Status:** 🔴 **NOT IMPLEMENTED** - New domain needed

---

### 4. MCP Server Management ✅ **DOCUMENTED**

**Location:** `docs/unified/mcp_management.md`

Fully documented in separate document. Includes:
- Docker-based lifecycle management
- Health monitoring
- Tool discovery
- Local vs. containerized deployment strategies

**Status:** 📝 Documented, implementation in progress

---

### 5. Service Monitoring 🟡 **PARTIAL**

**Current Coverage:**
- systemd service state tracking
- Docker container health
- MCP server health checks

**Missing Coverage:**
- Custom service health checks
- Performance metrics (CPU, memory, disk I/O)
- Log aggregation and analysis
- Alerting on service failures
- Auto-restart policies

#### 5.1 Enhanced Service Monitor

**Location:** `domains/memory_change/watchers/services.py` (extend)

```python
class ServiceMonitor:
    """Enhanced service monitoring with metrics."""

    async def monitor_systemd_services(self):
        """Monitor systemd services."""
        # systemctl list-units --type=service
        # Track state changes, restarts, failures
        pass

    async def collect_metrics(self, service: str):
        """Collect performance metrics for service."""
        # CPU: via /proc/<pid>/stat
        # Memory: via /proc/<pid>/status
        # Disk I/O: via /proc/<pid>/io
        pass

    async def analyze_logs(self, service: str, since: datetime):
        """Analyze service logs for errors."""
        # journalctl -u service --since
        # Detect ERROR, WARN patterns
        # Create :LogEvent nodes
        pass

    async def check_health(self, service: str):
        """Custom health check."""
        # HTTP endpoint, TCP socket, process existence
        # Return health status
        pass
```

**Graph Schema:**
```cypher
(:Service {
  name: "nginx",
  type: "systemd",
  state: "running",
  pid: 1234,
  started_at: datetime(),
  restarts: 0,
  health_status: "healthy"
})

# Performance metrics
(:ServiceMetrics {
  service_name: "nginx",
  timestamp: datetime(),
  cpu_percent: 2.5,
  memory_mb: 128,
  disk_read_mb: 10,
  disk_write_mb: 5,
  network_rx_mb: 100,
  network_tx_mb: 50
})-[:METRICS_FOR]->(:Service)

# Log events
(:LogEvent {
  timestamp: datetime(),
  level: "ERROR",
  message: "Connection timeout to upstream",
  service: "nginx"
})-[:LOGGED_BY]->(:Service)
```

**Queries:**
- "Which services are using >90% CPU?"
- "Show nginx error logs from today"
- "What services restarted in the last hour?"
- "Graph memory usage for postgres over last 24h"

**Status:** 🟡 Basic monitoring exists, metrics/logs/health checks needed

---

### 6. Configuration Management 🟡 **PARTIAL**

**Current Coverage:**
- Config file discovery (`:ConfigFile` nodes)
- File change tracking

**Missing Coverage:**
- Configuration validation
- Rollback capability
- Configuration templating
- Secret management
- Configuration drift detection

#### 6.1 Configuration Manager

**Location:** `domains/config_manager/`

```python
class ConfigManager:
    """Manage system and application configurations."""

    async def track_config_changes(self, path: Path):
        """Track configuration file changes."""
        # Git-style versioning of configs
        # Store diffs in Neo4j
        pass

    async def validate_config(self, path: Path):
        """Validate configuration syntax."""
        # nginx -t, sshd -t, etc.
        # Return validation result
        pass

    async def rollback_config(self, path: Path, version: str):
        """Rollback config to previous version."""
        # Restore from backup/git history
        pass

    async def detect_drift(self):
        """Detect configuration drift from desired state."""
        # Compare current vs. expected
        # Report differences
        pass
```

**Status:** 🟡 Tracking exists, management features needed

---

### 7. Resource Monitoring 🔴 **NOT IMPLEMENTED**

Track system-wide resource usage:
- CPU utilization (per core, per process)
- Memory usage (used/free/cached/swap)
- Disk space (per filesystem)
- Disk I/O (read/write rates)
- Network bandwidth (per interface)
- GPU usage (if available)

**Location:** `domains/resource_monitor/`

**Graph Schema:**
```cypher
(:SystemMetrics {
  timestamp: datetime(),
  cpu_percent: 45.2,
  memory_used_gb: 12.5,
  memory_total_gb: 32.0,
  disk_used_gb: 450,
  disk_total_gb: 1000,
  load_average_1m: 2.3,
  load_average_5m: 1.8,
  load_average_15m: 1.5
})

(:DiskMetrics {
  filesystem: "/dev/sda1",
  mount_point: "/",
  used_gb: 450,
  available_gb: 550,
  use_percent: 45.0,
  timestamp: datetime()
})
```

**Status:** 🔴 **NOT IMPLEMENTED**

---

### 8. Git Runner Management 🔴 **NOT IMPLEMENTED**

**Purpose**

Manage self-hosted CI/CD runners (GitHub Actions, GitLab CI, etc.) including:
- Runner lifecycle (installation, registration, updates)
- Job monitoring and logging
- Resource allocation
- Runner health checks
- Auto-scaling based on workload

**Location:** `domains/runner_manager/`

#### 8.1 Runner Orchestrator

```python
class RunnerManager:
    """Manage self-hosted CI/CD runners."""

    async def register_runner(self, provider: str, repo: str):
        """Register new runner with CI provider."""
        # GitHub: gh api repos/{repo}/actions/runners/registration-token
        # GitLab: gitlab-runner register
        pass

    async def monitor_jobs(self):
        """Track running jobs and resource usage."""
        # Query runner API for active jobs
        # Monitor CPU, memory per job
        pass

    async def scale_runners(self):
        """Auto-scale runners based on queue depth."""
        # If jobs queued > threshold, spin up more runners
        pass

    async def update_runners(self):
        """Update runner software versions."""
        pass
```

**Graph Schema:**
```cypher
(:GitRunner {
  id: "runner-01",
  provider: "github",  # github, gitlab, gitea
  repo: "Coldaine/the-watchman",
  status: "idle",  # idle, running, offline
  version: "2.311.0",
  registered_at: datetime(),
  last_job: datetime(),
  jobs_completed: 145
})

(:CIJob {
  id: "job_123",
  repo: "Coldaine/the-watchman",
  workflow: "ci.yml",
  status: "running",
  started_at: datetime(),
  duration_seconds: 120
})-[:RAN_ON]->(:GitRunner)
```

**Configuration:**
```toml
[git_runners]
enabled = true
auto_register = true  # Auto-register on startup

[[git_runners.providers]]
provider = "github"
repos = ["Coldaine/the-watchman", "Coldaine/dotfiles"]
runner_count = 2
auto_scale = true
max_runners = 5

[[git_runners.providers]]
provider = "gitlab"
url = "https://gitlab.com"
groups = ["mygroup"]
runner_count = 1
```

**API Endpoints:**
```bash
# List runners
GET /admin/runners
Response: [
  {
    "id": "runner-01",
    "provider": "github",
    "status": "idle",
    "jobs_completed": 145
  }
]

# Register new runner
POST /admin/runners/register
Body: {
  "provider": "github",
  "repo": "Coldaine/the-watchman"
}

# View job history
GET /admin/runners/jobs?days=7
```

**Queries:**
- "Which runners are currently running jobs?"
- "Show me failed CI jobs from last week"
- "How many jobs did runner-01 complete today?"
- "What's the average CI job duration?"

**Status:** 🔴 **NOT IMPLEMENTED**

---

### 9. Obsidian Vault Sync Management 🔴 **NOT IMPLEMENTED**

**Purpose**

Orchestrate self-hosted Obsidian vault synchronization:
- Git-based sync (auto-commit, auto-pull)
- Rsync fallback for large media files
- Conflict detection and resolution
- Backup integration (vault included in backup jobs)
- Sync status monitoring

**Location:** `domains/obsidian_sync/`

#### 9.1 Obsidian Sync Orchestrator

```python
class ObsidianSyncManager:
    """Manage Obsidian vault synchronization."""

    async def auto_sync(self, vault_path: Path):
        """Automatically sync vault to git."""
        # Check for changes
        # Auto-commit with timestamp
        # Pull from remote (handle conflicts)
        # Push to remote
        pass

    async def detect_conflicts(self, vault_path: Path):
        """Detect merge conflicts."""
        # Check for conflict markers
        # Alert user
        pass

    async def backup_vault(self, vault_path: Path):
        """Trigger vault backup."""
        # Integrate with backup manager
        pass

    async def sync_media(self, vault_path: Path):
        """Rsync large media files."""
        # Images, PDFs, videos separate from git
        pass
```

**Graph Schema:**
```cypher
(:ObsidianVault {
  id: "vault-main",
  name: "Main Vault",
  path: "/home/user/Documents/Obsidian/MainVault",
  git_remote: "https://github.com/Coldaine/obsidian-vault.git",
  last_sync: datetime(),
  sync_status: "synced",  # synced, syncing, conflict, error
  file_count: 892,
  note_count: 456,
  total_size_mb: 250
})

(:ObsidianSyncEvent {
  vault_id: "vault-main",
  timestamp: datetime(),
  type: "auto_commit",  # auto_commit, pull, push, conflict
  files_changed: 3,
  commit_hash: "abc123"
})-[:SYNCED]->(:ObsidianVault)
```

**Configuration:**
```toml
[obsidian]
enabled = true

[[obsidian.vaults]]
name = "Main Vault"
path = "/home/user/Documents/Obsidian/MainVault"
git_remote = "https://github.com/Coldaine/obsidian-vault.git"
auto_sync = true
sync_interval = 300  # 5 minutes
auto_commit = true
commit_message_template = "Auto-sync: {timestamp}"

# Media sync (separate from git for performance)
media_sync_enabled = true
media_extensions = [".png", ".jpg", ".pdf", ".mp4"]
media_rsync_target = "user@nas.home.lan:/backups/obsidian-media/"

# Conflict handling
conflict_strategy = "alert"  # alert, latest, manual
```

**API Endpoints:**
```bash
# Trigger manual sync
POST /admin/obsidian/sync/{vault_id}

# View sync status
GET /admin/obsidian/status
Response: [
  {
    "vault_id": "vault-main",
    "sync_status": "synced",
    "last_sync": "2025-11-11T14:30:00Z",
    "conflicts": 0
  }
]

# View sync history
GET /admin/obsidian/history?vault_id=vault-main&days=7
```

**Queries:**
- "When was my Obsidian vault last synced?"
- "Are there any sync conflicts?"
- "Show me sync events from today"
- "How many notes did I add this week?"

**Status:** 🔴 **NOT IMPLEMENTED**

---

### 10. Data Retention Policies 🔴 **PARTIALLY DOCUMENTED**

**Purpose**

Comprehensive data retention management across all domains:
- Configurable retention periods per data type
- Automatic purging of expired data
- Retention enforcement with audit trail
- GDPR/compliance-friendly retention rules
- Selective retention (keep important, purge routine)

**Graph Schema:**
```cypher
(:RetentionPolicy {
  id: "policy-screenshots",
  data_type: "Screenshot",
  retention_days: 14,
  enforcement: "automatic",  # automatic, manual, disabled
  purge_strategy: "soft_delete",  # soft_delete, hard_delete, archive
  created_at: datetime()
})

(:RetentionEvent {
  policy_id: "policy-screenshots",
  timestamp: datetime(),
  action: "purged",  # purged, archived, exempted
  records_affected: 145,
  size_freed_mb: 1250
})-[:APPLIED]->(:RetentionPolicy)
```

**Configuration:**
```toml
[retention]
# Global defaults
default_retention_days = 90
enforcement_schedule = "0 3 * * *"  # Daily at 3 AM
dry_run = false  # Test mode, no actual deletion

# Per-domain retention
[retention.screenshots]
retention_days = 14
purge_strategy = "hard_delete"  # Delete image files
keep_metadata = true  # Keep :Snapshot nodes
exempt_tagged = ["important", "reference"]  # Never delete these

[retention.ocr_text]
retention_days = 90
purge_strategy = "soft_delete"  # Mark deleted, keep in DB

[retention.events]
retention_days = 365
purge_strategy = "archive"  # Move to cold storage
archive_location = "s3://watchman-archive/events/"

[retention.backups]
retention_days = 90
purge_strategy = "hard_delete"
keep_monthly = true  # Keep one backup per month indefinitely

[retention.logs]
retention_days = 30
purge_strategy = "hard_delete"

[retention.gui_events]
retention_days = 60
purge_strategy = "hard_delete"

[retention.file_ingest_metadata]
retention_days = 180
purge_strategy = "soft_delete"

# Exemptions (never delete)
[retention.exemptions]
# Keep all data from specific date ranges
date_ranges = [
  { start = "2025-10-01", end = "2025-10-31", reason = "Critical project month" }
]
# Keep data with specific tags
tags = ["important", "reference", "legal"]
```

**API Endpoints:**
```bash
# View retention policies
GET /admin/retention/policies

# Preview what would be purged
GET /admin/retention/preview?policy=screenshots&dry_run=true
Response: {
  "records_to_purge": 145,
  "size_freed_mb": 1250,
  "oldest_record": "2025-09-15T10:00:00Z",
  "newest_record": "2025-10-28T18:00:00Z"
}

# Trigger manual purge
POST /admin/retention/purge
Body: {
  "policy": "screenshots",
  "confirm": true
}

# Exempt specific records from purging
POST /admin/retention/exempt
Body: {
  "record_ids": ["snapshot_123", "snapshot_456"],
  "reason": "Important reference"
}
```

**Queries:**
- "How much disk space will retention purge free up?"
- "When was the last retention purge?"
- "Show me exempted records"
- "What's the oldest data in the system?"

**Status:** 🟡 **PARTIALLY DOCUMENTED** - Basic retention exists, needs full policy engine

---

### 11. FIDO2 Encryption 🔴 **NOT IMPLEMENTED**

**Purpose**

Encrypt sensitive data using FIDO2 hardware keys (YubiKey, etc.):
- Backup encryption with hardware key
- Sensitive configuration encryption
- Secret management (API keys, tokens)
- Database field-level encryption
- Multi-factor decryption (require physical key)

**Location:** `domains/security_manager/fido2.py`

#### 11.1 FIDO2 Encryption Manager

```python
class FIDO2EncryptionManager:
    """Manage FIDO2-encrypted sensitive data."""

    async def encrypt_with_fido2(self, data: bytes, label: str) -> dict:
        """Encrypt data using FIDO2 key."""
        # Challenge user to touch FIDO2 key
        # Derive encryption key from FIDO2 credential
        # Encrypt data with AES-256-GCM
        # Store encrypted blob + metadata
        pass

    async def decrypt_with_fido2(self, encrypted_blob: bytes) -> bytes:
        """Decrypt data (requires FIDO2 key)."""
        # Challenge user to touch FIDO2 key
        # Derive decryption key from FIDO2 credential
        # Decrypt and return
        pass

    async def encrypt_backup(self, backup_path: Path):
        """Encrypt backup with FIDO2."""
        # Read backup file
        # Encrypt with FIDO2
        # Replace with encrypted version
        pass
```

**Configuration:**
```toml
[security]
fido2_enabled = true
fido2_required_for = ["backups", "secrets", "api_keys"]

# FIDO2 key configuration
[security.fido2]
device_path = "/dev/hidraw0"  # Auto-detect if empty
timeout_seconds = 30  # Time to touch key
credential_id = ""  # Generated on first use

# What to encrypt
[security.encryption]
encrypt_backups = true
encrypt_neo4j_dumps = true
encrypt_config_backups = true
encrypt_api_tokens = true
encrypt_satellite_tokens = true

# Encryption algorithm
encryption_algorithm = "AES-256-GCM"
key_derivation = "HKDF-SHA256"
```

**Graph Schema:**
```cypher
(:EncryptedData {
  id: "encrypted_backup_123",
  type: "neo4j_backup",
  encrypted_at: datetime(),
  encryption_method: "FIDO2-AES256",
  fido2_credential_id: "abc123",
  blob_location: "s3://backups/encrypted_neo4j_2025-11-11.enc",
  size_bytes: 1024000,
  checksum: "sha256:xyz789"
})

(:FIDO2Key {
  credential_id: "abc123",
  label: "YubiKey 5C",
  registered_at: datetime(),
  last_used: datetime(),
  usage_count: 45
})
```

**API Endpoints:**
```bash
# Encrypt file with FIDO2
POST /admin/security/encrypt
Body: {
  "file_path": "/path/to/sensitive.dat",
  "label": "Important backup"
}
Response: {
  "encrypted_path": "/path/to/sensitive.dat.enc",
  "credential_id": "abc123"
}

# Decrypt file (requires FIDO2 touch)
POST /admin/security/decrypt
Body: {
  "encrypted_path": "/path/to/sensitive.dat.enc"
}
Response: {
  "decrypted_path": "/tmp/decrypted_sensitive.dat",
  "touch_required": true
}

# List FIDO2-encrypted data
GET /admin/security/encrypted
```

**Queries:**
- "Which backups are FIDO2-encrypted?"
- "When was my FIDO2 key last used?"
- "Show me all encrypted secrets"

**Status:** 🔴 **NOT IMPLEMENTED** - Requires libfido2 integration

---

### 12. Security & Compliance 🔴 **NOT DOCUMENTED**

**Responsibilities:**
- Track security updates
- Monitor failed login attempts
- Audit sudo usage
- Track file permission changes
- Monitor exposed services
- CVE tracking for installed packages

**Location:** `domains/security_monitor/`

**Status:** 🔴 **NOT IMPLEMENTED** - Future consideration

---

## Summary of System Management Domains

| Domain | Status | Location | Priority |
|--------|--------|----------|----------|
| Software Install Monitoring | ✅ Documented | `domains/memory_change/watchers/packages.py` | High |
| MCP Server Management | ✅ Documented | `domains/mcp_registry/` | High |
| Basic Service Monitoring | 🟡 Partial | `domains/memory_change/watchers/services.py` | High |
| Container Monitoring | ✅ Implemented | `domains/memory_change/watchers/docker.py` | High |
| Config File Tracking | 🟡 Partial | `domains/system_graph/scanners/configs.py` | Medium |
| Network Topology | 🟡 Partial | `domains/system_graph/scanners/network.py` (planned) | Medium |
| Backup Management | ✅ Documented | `domains/backup_manager/` (planned) | High |
| Git Runner Management | ✅ Documented | `domains/runner_manager/` (planned) | Medium |
| Obsidian Vault Sync | ✅ Documented | `domains/obsidian_sync/` (planned) | Medium |
| Data Retention Policies | 🟡 Partial | Extend all domains | High |
| FIDO2 Encryption | ✅ Documented | `domains/security_manager/fido2.py` (planned) | Medium |
| Enhanced Service Metrics | 🔴 Not Implemented | Extend service monitor | Medium |
| Configuration Management | 🔴 Not Implemented | `domains/config_manager/` (planned) | Medium |
| Resource Monitoring | 🔴 Not Implemented | `domains/resource_monitor/` (planned) | Medium |
| Network Config Management | 🔴 Not Implemented | Extend network scanner | Low |
| Security & Compliance | 🔴 Not Implemented | `domains/security_monitor/` (future) | Low |

## Implementation Roadmap

### Phase 1: Core Monitoring (Current)
- [x] Software installation tracking
- [x] Container events
- [x] Basic service monitoring
- [x] Config file discovery

### Phase 2: Network & Backups
- [ ] Network topology scanner
- [ ] Backup orchestrator
- [ ] Backup verification
- [ ] S3 integration

### Phase 3: Enhanced Monitoring
- [ ] Service performance metrics
- [ ] Log aggregation
- [ ] Resource monitoring
- [ ] Health checks

### Phase 4: Configuration Management
- [ ] Config versioning
- [ ] Validation
- [ ] Rollback capability
- [ ] Drift detection

### Phase 5: Security & Compliance
- [ ] Security audit trail
- [ ] CVE tracking
- [ ] Access monitoring
- [ ] Compliance reporting

## Configuration

All system management features can be toggled via `config.toml`:

```toml
[features]
system_monitoring = true
network_scanning = true
backup_management = true
config_management = true
resource_monitoring = true
security_monitoring = false  # Future

[monitoring]
metrics_interval = 60  # seconds
log_analysis_enabled = true
alert_on_service_failure = true

[backup]
enabled = true
schedule = "0 2 * * *"
storage_provider = "s3"

[network]
scan_interval = 300  # seconds
monitor_interfaces = ["eth0", "wlan0"]
track_vpn = true
```

## API Endpoints Summary

All system management features exposed via REST API:

- `/admin/scan` - Trigger system scan
- `/admin/packages` - Query package history
- `/admin/services` - Service status/control
- `/admin/network` - Network topology
- `/admin/backup/*` - Backup management
- `/admin/config/*` - Configuration management
- `/admin/metrics` - Resource metrics

See individual domain docs for detailed API specifications.
