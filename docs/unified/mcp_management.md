# MCP Server Management Strategy

**Last Updated:** 2025-11-11

This document outlines The Watchman's role as the central orchestrator and manager for all MCP (Model Context Protocol) servers in the user's environment.

## Overview

The Watchman will serve as the **single source of truth** for MCP server lifecycle management, providing:

1. **Centralized Registry** - Catalog of all available MCP servers
2. **Docker-based Deployment** - Spin up/down servers via Docker Compose
3. **Health Monitoring** - Track server status and availability
4. **Tool Discovery** - Index MCP tools and capabilities
5. **Local Tool Management** - Strategy for tools requiring local installation

## Architecture

### MCP Registry Domain

Location: `domains/mcp_registry/`

**Responsibilities:**
- YAML-based server registry
- Docker Compose orchestration
- Health check monitoring
- Graph integration (`:MCPServer`, `:Tool` nodes)
- API endpoints for control

### Core Components

```
domains/mcp_registry/
├── registry.py         # YAML parser, registry loader
├── orchestrator.py     # Docker Compose control
├── health.py           # Health check polling
├── discovery.py        # Tool discovery & indexing
├── local_tools.py      # Local installation manager
└── graph_writer.py     # Neo4j integration
```

## Registry Format

`config/mcp_registry.yaml`:

```yaml
version: "1.0"

servers:
  # Docker-based MCP servers
  - name: neo4j-mcp
    deployment: docker
    compose_file: /opt/mcp/neo4j-mcp/docker-compose.yml
    service: neo4j-mcp
    image: docker.io/user/neo4j-mcp:latest
    health_check: http://localhost:3200/health
    auto_start: true
    tools:
      - name: cypher_query
        description: Execute Cypher queries against Neo4j
      - name: graph_schema
        description: Retrieve Neo4j graph schema

  - name: bookmarks-mcp
    deployment: docker
    compose_file: /opt/mcp/bookmarks/docker-compose.yml
    service: bookmarks
    image: docker.io/modelcontextprotocol/bookmarks:latest
    health_check: http://localhost:3100/health
    auto_start: false

  # Local binary MCP servers
  - name: filesystem-mcp
    deployment: local
    binary: /usr/local/bin/mcp-filesystem
    install_method: pip
    package: mcp-filesystem
    health_check: unix:///tmp/mcp-filesystem.sock
    auto_start: true
    tools:
      - name: read_file
      - name: write_file
      - name: list_directory

  # Docker Hub registry
  - name: github-mcp
    deployment: docker_hub
    image: modelcontextprotocol/github:latest
    port: 3300
    health_check: http://localhost:3300/health
    auto_start: false
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

## Docker-Based Management

### Deployment Workflow

1. **Registry Scan**: Parse `mcp_registry.yaml` on startup
2. **Image Pull**: Pull Docker images from Docker Hub if not present
3. **Compose Generation**: Generate/validate `docker-compose.yml` for each server
4. **Lifecycle Control**: Start/stop/restart via Docker Compose CLI
5. **Health Monitoring**: Poll health endpoints every 5 minutes

### Docker Compose Generation

For servers defined in registry without explicit `compose_file`, auto-generate:

```yaml
# Generated: /var/lib/watchman/mcp/github-mcp/docker-compose.yml
version: '3.8'
services:
  github-mcp:
    image: modelcontextprotocol/github:latest
    container_name: watchman-mcp-github
    ports:
      - "3300:3300"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    restart: unless-stopped
    networks:
      - watchman-mcp-net
    labels:
      - "watchman.mcp.server=github"
      - "watchman.managed=true"

networks:
  watchman-mcp-net:
    external: true
```

### Docker Hub Integration

**Research Needed:**
- [ ] How to query Docker Hub API for MCP server images
- [ ] Standard MCP image naming convention (modelcontextprotocol/*)
- [ ] Image metadata for tool discovery (labels, annotations)
- [ ] Version pinning strategy (latest vs. semver tags)

**Proposed Approach:**
```python
import requests

def search_mcp_servers_on_docker_hub(query: str = "mcp"):
    """Search Docker Hub for MCP server images."""
    url = "https://hub.docker.com/v2/search/repositories/"
    params = {
        "query": f"{query} modelcontextprotocol",
        "page_size": 100
    }
    response = requests.get(url, params=params)
    return response.json()["results"]
```

**Auto-discovery flow:**
1. User: "Find available MCP servers"
2. Watchman queries Docker Hub API
3. Parse results, extract MCP-compatible images
4. Add to registry with default config
5. User reviews and enables desired servers

## Local Tool Management

### Challenge

Some MCP tools require local installation:
- `mcp-filesystem` - Needs direct filesystem access
- `mcp-git` - Requires git CLI
- `mcp-docker` - Needs Docker socket access

### Strategies

#### Option 1: Host Installation (Recommended for Phase 1)

**Pros:**
- Simple, no container complexity
- Full system access
- User manages dependencies

**Cons:**
- Requires user to install tools manually
- Dependency conflicts possible
- Less isolated

**Implementation:**
```yaml
- name: filesystem-mcp
  deployment: local
  binary: /usr/local/bin/mcp-filesystem
  install_method: pip
  package: mcp-filesystem
  install_command: "pip install mcp-filesystem"
```

Watchman provides:
- Installation instructions in `/admin/mcp/install-guide/{name}`
- Binary existence check before marking as available
- Fallback to Docker if local binary missing

#### Option 2: Privileged Docker Container

**Pros:**
- Isolated but with system access
- Consistent environment
- Auto-installation

**Cons:**
- Security risk (privileged mode)
- Complex volume mounting
- Potential permission issues

**Implementation:**
```yaml
services:
  filesystem-mcp:
    image: watchman/mcp-filesystem:latest
    privileged: true
    volumes:
      - /:/host:ro  # Read-only host filesystem
    environment:
      - HOST_ROOT=/host
```

#### Option 3: Hybrid Approach (Recommended for Phase 2)

- Docker for network-based tools (APIs, databases)
- Local for filesystem/system tools
- Watchman detects which approach is needed per tool

**Decision Matrix:**

| Tool Type | Deployment | Reason |
|-----------|------------|--------|
| API/Network services | Docker | Isolated, portable |
| Filesystem access | Local | Direct access required |
| Git operations | Local | Uses host git config |
| Database clients | Docker | No local deps needed |
| System commands | Local | Needs sudo/system access |

### Research Tasks

- [ ] Survey existing MCP servers and categorize by deployment needs
- [ ] Test Docker socket mounting for `mcp-docker` tool
- [ ] Evaluate security implications of privileged containers
- [ ] Design fallback chain: local → privileged Docker → regular Docker → disabled
- [ ] Document installation requirements per MCP server

## Graph Schema

```cypher
# MCP Server nodes
CREATE CONSTRAINT mcp_server_name IF NOT EXISTS
FOR (m:MCPServer) REQUIRE m.name IS UNIQUE;

(:MCPServer {
  name: "neo4j-mcp",
  deployment_type: "docker",  # docker, local, docker_hub
  status: "running",  # running, stopped, failed, installing
  image: "docker.io/user/neo4j-mcp:latest",
  health_url: "http://localhost:3200/health",
  last_health_check: datetime(),
  auto_start: true,
  created_at: datetime(),
  updated_at: datetime()
})

# Tool nodes
CREATE CONSTRAINT tool_id IF NOT EXISTS
FOR (t:Tool) REQUIRE t.id IS UNIQUE;

(:Tool {
  id: "neo4j-mcp::cypher_query",
  name: "cypher_query",
  description: "Execute Cypher queries",
  input_schema: {...},
  output_schema: {...}
})

# Relationships
(:MCPServer)-[:PROVIDES_TOOL]->(:Tool)
(:MCPServer)-[:RUNS_IN]->(:Container)  # For Docker deployments
(:MCPServer)-[:USES_BINARY]->(:File)   # For local deployments
(:MCPServer)-[:DEPENDS_ON]->(:Software)
```

## API Endpoints

### Lifecycle Management

```bash
# List all MCP servers
GET /mcp/list
Response: [
  {
    "name": "neo4j-mcp",
    "status": "running",
    "deployment": "docker",
    "health": "healthy",
    "tools": ["cypher_query", "graph_schema"]
  }
]

# Start MCP server
POST /mcp/start/{name}
Response: {"status": "starting", "container_id": "abc123"}

# Stop MCP server
POST /mcp/stop/{name}
Response: {"status": "stopped"}

# Restart MCP server
POST /mcp/restart/{name}
Response: {"status": "restarting"}

# Get server logs
GET /mcp/logs/{name}?lines=100
Response: {"logs": "..."}
```

### Discovery & Registry

```bash
# Search Docker Hub for MCP servers
GET /mcp/discover?query=github
Response: [
  {
    "image": "modelcontextprotocol/github:latest",
    "description": "GitHub MCP server",
    "stars": 150,
    "pulls": 5000
  }
]

# Add server to registry
POST /mcp/add
Body: {
  "name": "github-mcp",
  "image": "modelcontextprotocol/github:latest",
  "port": 3300,
  "env": {"GITHUB_TOKEN": "..."}
}
Response: {"status": "added", "name": "github-mcp"}

# Remove server from registry
DELETE /mcp/remove/{name}
Response: {"status": "removed"}
```

### Tool Discovery

```bash
# List tools from server
GET /mcp/{name}/tools
Response: [
  {
    "name": "cypher_query",
    "description": "Execute Cypher queries",
    "input_schema": {...}
  }
]

# Invoke tool
POST /mcp/{server}/tool/{tool_name}
Body: {"params": {...}}
Response: {"result": {...}}
```

## Health Monitoring

### Health Check Worker

Location: `domains/mcp_registry/health.py`

```python
class MCPHealthMonitor:
    def __init__(self):
        self.check_interval = 300  # 5 minutes

    async def run(self):
        while True:
            servers = self.get_registered_servers()
            for server in servers:
                health = await self.check_health(server)
                self.update_status(server, health)
            await asyncio.sleep(self.check_interval)

    async def check_health(self, server: dict) -> dict:
        """Check server health via HTTP, socket, or Docker PS."""
        if server["deployment"] == "docker":
            return self.check_docker_health(server)
        elif server["deployment"] == "local":
            return self.check_local_health(server)
```

### Status Updates

- Update `:MCPServer.status` in Neo4j
- Create `:HealthCheckEvent` for tracking
- Alert if server down for >15 minutes
- Auto-restart if `auto_start=true` and status=failed

## Implementation Plan

### Phase 1: Docker Management (Week 1-2)

- [ ] YAML registry parser
- [ ] Docker Compose orchestration (start/stop/restart)
- [ ] Basic health checks (HTTP endpoints)
- [ ] `/mcp/list`, `/mcp/start`, `/mcp/stop` endpoints
- [ ] Graph integration (`:MCPServer` nodes)

### Phase 2: Docker Hub Integration (Week 3)

- [ ] Research Docker Hub API
- [ ] Implement server discovery
- [ ] Auto-generate Compose files
- [ ] `/mcp/discover` and `/mcp/add` endpoints
- [ ] Image pull and version management

### Phase 3: Local Tool Support (Week 4)

- [ ] Research local tool requirements
- [ ] Decide on deployment strategy (see Options above)
- [ ] Implement binary detection
- [ ] Installation guide generation
- [ ] Fallback logic (local → Docker)

### Phase 4: Tool Discovery & Invocation (Week 5)

- [ ] Parse MCP tool schemas
- [ ] Create `:Tool` nodes in Neo4j
- [ ] `/mcp/{server}/tools` endpoint
- [ ] Tool invocation proxy
- [ ] Agent interface integration

## Security Considerations

- **API Keys**: Store in `.env`, never in registry YAML
- **Docker Socket**: Limit access, consider Docker-in-Docker
- **Privileged Containers**: Document risks, user consent required
- **Network Isolation**: Separate `watchman-mcp-net` network
- **Health Endpoints**: Authentication if exposing sensitive data

## Testing Strategy

- Unit tests: Registry parsing, Compose generation
- Integration tests: Docker lifecycle (start/stop/restart)
- Health check tests: Mock HTTP responses
- Security tests: Ensure secrets not logged
- Performance tests: 10+ concurrent servers

## Dependencies

Add to `requirements.txt`:
```
docker>=7.0.0  # Docker SDK for Python
pyyaml>=6.0   # YAML parsing
requests>=2.31.0  # Docker Hub API
```

## Future Enhancements

- **MCP Server Marketplace**: Web UI for browsing/installing
- **Version Management**: Pin/upgrade MCP server versions
- **Resource Limits**: CPU/memory constraints per server
- **Load Balancing**: Multiple instances of popular servers
- **Telemetry**: Usage stats per MCP tool
- **Auto-updates**: Nightly image pulls for latest versions
