# Repository Portfolio Management

## Overview
The Repository Portfolio Management capability extends the Librarian's graph database to **store and track portfolio-wide repository data**. The Librarian provides the **data storage and query layer**, while external agent systems (Colossus, Watchmen) perform the actual analysis and coordination work.

## Core Concept

**The Librarian's Role**: Data Manager
- Store repository metadata in the Neo4j graph
- Store analysis results from external systems
- Provide query capabilities for portfolio intelligence
- Track historical trends and health scores

**Not the Librarian's Role**: Analysis Orchestration
- ❌ Does NOT run repository analysis agents
- ❌ Does NOT invoke Perplexity or other LLMs for analysis
- ❌ Does NOT schedule or trigger analysis runs
- ❌ Does NOT coordinate sprint planning workflows

**Who Does What**:
- **Colossus / Watchmen**: Run repository analysis, invoke Perplexity, coordinate work
- **The Librarian**: Store the results, provide query API, maintain graph relationships

## Librarian's Responsibilities

### 1. Repository Data Storage
**What the Librarian Provides**:
- Graph schema for `Repository` nodes
- Storage for repository metadata (name, URL, language, etc.)
- Relationships between repositories (dependencies, forks)

**What External Systems Do**:
- Discovery and cataloging of repositories
- Fetching metadata from GitHub API
- Cloning and updating repository contents

### 2. Analysis Results Storage
**What the Librarian Provides**:
- Graph schema for `AnalysisRun` and `AnalysisResult` nodes
- Time-series storage for health scores
- Query API to retrieve analysis history

**What External Systems Do**:
- Running the actual analysis (via Perplexity, static analysis tools, etc.)
- Generating health scores and findings
- Submitting results to the Librarian's API

### 3. Portfolio Query Capabilities
**What the Librarian Provides**:
- Cypher query endpoints for portfolio intelligence
- Pre-built queries for common questions:
  - "Which repos have declining health?"
  - "Which repos haven't been analyzed recently?"
  - "Show me all repos with critical security issues"
- Vector search across repository documentation

**What External Systems Do**:
- Interpreting natural language queries
- Orchestrating complex analysis workflows
- Presenting results to users

### 4. Sprint and Triage Support
**What the Librarian Provides**:
- Graph schema for `Sprint` nodes
- Relationships linking repositories to sprints
- Queries for "which repos are in this sprint?"

**What External Systems Do**:
- Sprint planning and coordination
- Prioritization decisions
- Work assignment and tracking

## Graph Schema Extension

The Librarian extends its existing graph schema to support portfolio data:

**Existing Nodes**: `Architecture`, `Design`, `Requirement`, `AgentRequest`, `Decision`

**New Nodes for Portfolio**:
- `Repository` - Metadata about GitHub repositories
- `AnalysisRun` - Record of an analysis execution
- `AnalysisResult` - Specific findings from analysis
- `ProjectHealth` - Time-series health scores
- `Sprint` - Work coordination nodes

**Key Relationships**:
- `(Repository)-[:ANALYZED_BY]->(AnalysisRun)`
- `(AnalysisRun)-[:PRODUCED]->(AnalysisResult)`
- `(Repository)-[:HAS_HEALTH]->(ProjectHealth)`
- `(Repository)-[:CONTAINS]->(Architecture|Design)`
- `(Sprint)-[:INCLUDES]->(Repository)`

This creates a **unified graph** where:
- Document-level governance (core Librarian functionality)
- Repository-level health tracking (new capability)
- Portfolio-level coordination (new capability)

...all coexist in the same Neo4j database.

## Example Queries the Librarian Enables

Once Colossus/Watchmen populate the graph with data, the Librarian can answer:

**Portfolio Health**:
- "Show me all repos with declining health in the last 3 months"
- "Which repos have critical security issues?"
- "Which repos haven't been analyzed in 30+ days?"

**Cross-Repository Intelligence**:
- "Which repos depend on deprecated libraries?"
- "Which repos have similar architectural patterns?"
- "Show me all Python repos with < 50% test coverage"

**Historical Trends**:
- "How has repository X's health changed over 6 months?"
- "What issues were found in the last 5 analysis runs?"

## API Endpoints the Librarian Provides

**Repository Management**:
- `POST /repositories` - Create/update repository metadata
- `GET /repositories` - List all repositories
- `GET /repositories/{id}` - Get repository details

**Analysis Results**:
- `POST /repositories/{id}/analysis` - Submit analysis results
- `GET /repositories/{id}/analysis` - Get analysis history
- `GET /repositories/{id}/health` - Get health score trends

**Portfolio Queries**:
- `POST /query/portfolio` - Run custom Cypher queries
- `GET /portfolio/health` - Get portfolio-wide health summary
- `GET /sprints` - List sprints and assigned repositories

## External Systems Integration

### Colossus / Watchmen Agent Systems
These external systems handle:
- Repository discovery and cloning
- Scheduling periodic analysis runs
- Invoking Perplexity for repository analysis (via MCP stealth-browser)
- Parsing analysis results
- **Submitting results to the Librarian's API**
- Coordinating sprint planning
- Generating reports and notifications

### The Librarian's Role
The Librarian is a **passive data store with query capabilities**:
- Receives data submissions from external systems
- Stores everything in the Neo4j graph
- Provides query API for retrieving data
- Maintains data integrity and relationships

## Future Considerations

**Data Retention**:
- How long to keep old analysis results (e.g., 1 year)
- Archival strategy for historical data

**Query Performance**:
- Indexing strategy for large portfolio (100+ repositories)
- Caching frequently accessed queries

**Access Control**:
- Which external systems can write to the graph
- API authentication and authorization

## References

- **Main Architecture**: [`docs/architecture.md`](../architecture.md)
- **Graph Operations**: [`docs/subdomains/graph-operations.md`](./graph-operations.md)
- **Audit Governance**: [`docs/subdomains/audit-governance.md`](./audit-governance.md)
- **External Agent Systems**: Colossus and Watchmen (separate projects)
