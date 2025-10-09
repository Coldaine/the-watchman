// =====================================================
// The Watchman - Neo4j Schema Contracts
// =====================================================
// This file defines all node constraints, indexes, and
// relationship types for the Watchman system.
//
// Run this after Neo4j initialization to set up the schema.
// =====================================================

// =====================================================
// CONSTRAINTS (Uniqueness + Existence)
// =====================================================

// --- Visual Timeline ---
CREATE CONSTRAINT snapshot_id IF NOT EXISTS
FOR (s:Snapshot) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT chunk_hash IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.content_hash IS UNIQUE;

// --- System Graph ---
CREATE CONSTRAINT file_path IF NOT EXISTS
FOR (f:File) REQUIRE f.path IS UNIQUE;

CREATE CONSTRAINT dir_path IF NOT EXISTS
FOR (d:Directory) REQUIRE d.path IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT software_key IF NOT EXISTS
FOR (sw:Software) REQUIRE sw.key IS UNIQUE;

CREATE CONSTRAINT container_id IF NOT EXISTS
FOR (c:Container) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT service_name IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT network_endpoint_key IF NOT EXISTS
FOR (n:NetworkEndpoint) REQUIRE n.key IS UNIQUE;

CREATE CONSTRAINT config_file_path IF NOT EXISTS
FOR (cf:ConfigFile) REQUIRE cf.path IS UNIQUE;

// --- MCP Registry ---
CREATE CONSTRAINT mcp_name IF NOT EXISTS
FOR (m:MCPServer) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT tool_key IF NOT EXISTS
FOR (t:Tool) REQUIRE t.key IS UNIQUE;

// --- Events & Change ---
CREATE CONSTRAINT event_id IF NOT EXISTS
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT user_name IF NOT EXISTS
FOR (u:User) REQUIRE u.name IS UNIQUE;

// =====================================================
// INDEXES (Performance)
// =====================================================

// --- Timestamp indexes for temporal queries ---
CREATE INDEX event_timestamp IF NOT EXISTS
FOR (e:Event) ON (e.ts);

CREATE INDEX snapshot_timestamp IF NOT EXISTS
FOR (s:Snapshot) ON (e.ts);

CREATE INDEX file_modified IF NOT EXISTS
FOR (f:File) ON (f.last_modified);

// --- Path indexes for location queries ---
CREATE INDEX file_name IF NOT EXISTS
FOR (f:File) ON (f.name);

CREATE INDEX dir_name IF NOT EXISTS
FOR (d:Directory) ON (d.name);

CREATE INDEX project_name IF NOT EXISTS
FOR (p:Project) ON (p.name);

// --- Type indexes for filtering ---
CREATE INDEX event_type IF NOT EXISTS
FOR (e:Event) ON (e.type);

CREATE INDEX project_type IF NOT EXISTS
FOR (p:Project) ON (p.type);

CREATE INDEX container_state IF NOT EXISTS
FOR (c:Container) ON (c.state);

CREATE INDEX mcp_status IF NOT EXISTS
FOR (m:MCPServer) ON (m.status);

// =====================================================
// VECTOR INDEXES
// =====================================================

// Chunk embeddings for semantic search
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }
};

// Optional: Document embeddings (for full-doc search)
CREATE VECTOR INDEX document_embedding IF NOT EXISTS
FOR (f:File) ON (f.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }
};

// =====================================================
// RELATIONSHIP TYPES (Documentation Only)
// =====================================================
// Neo4j doesn't enforce relationship types, but here's
// the canonical list for consistency:
//
// --- Containment & Hierarchy ---
// :CONTAINS         - Directory->File, Project->File, Container->Volume
// :LOCATED_IN       - Project->Directory, File->Directory
// :PARENT_OF        - Directory->Directory (tree structure)
//
// --- Dependencies & Links ---
// :DEPENDS_ON       - Project->Software, Service->Service
// :USES_CONFIG      - Service->ConfigFile, Container->ConfigFile
// :RUNS_ON          - Container->Host, Service->Container
// :BACKED_BY        - Service->Dataset (e.g., app->Neo4j)
//
// --- Network & Ports ---
// :EXPOSES          - Container->NetworkEndpoint, Service->NetworkEndpoint
// :LISTENS_ON       - Service->NetworkEndpoint
//
// --- MCP & Tools ---
// :PROVIDES_TOOL    - MCPServer->Tool
// :USES_TOOL        - Service->Tool (if service consumes MCP tools)
//
// --- Visual Timeline ---
// :HAS_OCR          - Snapshot->Chunk
// :IN_DIR           - Snapshot->Directory (location when captured)
// :SEEN_APP         - Snapshot->Software (active app during snapshot)
//
// --- Events & Change ---
// :ACTED_ON         - Event->File, Event->Container, Event->Service
// :PERFORMED_BY     - Event->User
// :TRIGGERED        - Event->Event (causality chain)
//
// =====================================================
// SAMPLE QUERIES (Validation)
// =====================================================

// Verify constraints are active
// CALL db.constraints();

// Verify indexes are active
// CALL db.indexes();

// Verify vector index dimensionality
// CALL db.index.vector.queryNodes('chunk_embedding', 5, [0.1, 0.2, ...]) YIELD node, score RETURN node LIMIT 1;

// =====================================================
// MAINTENANCE QUERIES
// =====================================================

// Drop all constraints (DANGER - only for reset)
// CALL apoc.schema.assert({}, {});

// Drop specific constraint
// DROP CONSTRAINT snapshot_id IF EXISTS;

// Drop vector index
// DROP INDEX chunk_embedding IF EXISTS;

// =====================================================
// SCHEMA VERSION
// =====================================================
CREATE (sv:SchemaVersion {
  version: '1.0.0',
  created_at: datetime(),
  description: 'Initial Watchman schema with all core node types and vector indexes'
})
RETURN sv;
