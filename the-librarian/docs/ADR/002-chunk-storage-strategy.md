# ADR-002: Chunk Storage Strategy

## Status
**Accepted** - 2024-11-10

## Context

The Librarian system needs to store document embeddings for semantic search. During implementation, a critical design decision emerged: **how to store document chunks with their embeddings in the Neo4j graph**.

Two primary approaches were considered:

1. **Chunks as Properties**: Store chunks as array properties directly on document nodes
2. **Chunks as Nodes**: Create separate `Chunk` nodes with `CONTAINS` relationships to parent documents

This decision impacts:
- **Search granularity**: Document-level vs chunk-level results
- **Query flexibility**: Ability to annotate, version, and traverse chunks
- **Performance**: Relationship overhead vs property array operations
- **Data modeling**: Simplicity vs expressiveness
- **Future capabilities**: Chunk versioning, annotations, and provenance tracking

## Decision

**We will store chunks as separate `Chunk` nodes**, not as properties on document nodes.

Each chunk will:
- Be a first-class Neo4j node with label `Chunk`
- Have its own embedding stored directly on the node
- Be linked to its parent document via a `CONTAINS` relationship
- Have its own unique ID, content, metadata, and position information

## Implementation

### Schema Addition

```cypher
// Chunk node constraint
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
  FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Vector index for chunk embeddings
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS {
    indexConfig: {
      'vector.dimensions': 768,
      'vector.similarity_function': 'cosine'
    }
  };
```

### Chunk Node Structure

```cypher
(chunk:Chunk {
  id: "chunk_abc123_0",              // Unique ID (doc_id + index hash)
  content: "Text content...",         // Chunk text (1000 chars default)
  embedding: [0.1, 0.2, ...],        // 768-dim nomic-embed-text vector

  // Position/Context
  chunk_index: 0,                    // Position within parent document
  start_index: 0,                    // Character start position
  end_index: 1000,                   // Character end position
  section_title: "Overview",         // Section heading
  section_level: 2,                  // Heading level (1-6)

  // Metadata
  doc_type: "architecture",          // Parent document type
  source_path: "/path/to/doc.md",    // Original file path
  created_at: "2024-11-10T12:00:00Z",

  // Embedding metadata
  embedding_model: "nomic-embed-text",
  embedding_date: "2024-11-10T12:00:00Z"
})
```

### Relationships

```cypher
// Parent document CONTAINS chunk
(doc:Architecture|Design)-[:CONTAINS {
  chunk_index: 0
}]->(chunk:Chunk)
```

### Search Query Pattern

```cypher
// Semantic search returns chunks with parent context
CALL db.index.vector.queryNodes('chunk_embedding', 10, $query_embedding)
YIELD node, score

// Get parent document for context
MATCH (doc)-[:CONTAINS]->(node)

RETURN
  node.id as chunk_id,
  node.content as chunk_content,
  node.section_title as section,
  doc.id as doc_id,
  doc.title as doc_title,
  doc.version as doc_version,
  score
ORDER BY score DESC
```

## Rationale

### Advantages of Chunks as Nodes

1. **Fine-grained Search Results** ✅
   - Return specific relevant chunks, not entire documents
   - Users see exactly which section matched their query
   - Better user experience for large documents (50+ pages)

2. **Chunk-level Annotations** ✅
   - Can add metadata to individual chunks (tags, confidence scores)
   - Can mark chunks as deprecated without affecting whole document
   - Can track which chunks are most frequently accessed

3. **Future Versioning Capability** ✅
   - Can version chunks independently of documents
   - Can track chunk history: `(chunk:Chunk {version: 2})-[:SUPERSEDES]->(old_chunk)`
   - Enables chunk-level diff and change tracking

4. **Clear Separation of Concerns** ✅
   - Documents represent high-level metadata and structure
   - Chunks represent searchable content units
   - Clean data model that's easier to reason about

5. **Flexible Relationships** ✅
   - Can create relationships FROM chunks (e.g., `(chunk)-[:IMPLEMENTS]->(req)`)
   - Can link related chunks across documents
   - Enables knowledge graph construction at chunk granularity

6. **Selective Embedding Storage** ✅
   - Can store embeddings on chunks only, not full documents
   - Reduces storage if document embeddings not needed
   - Matches how users actually search (by content sections, not full docs)

### Disadvantages (Mitigated)

1. **More Relationships to Manage** ⚠️
   - Each document with 20 chunks = 20 relationships
   - **Mitigation**: Neo4j handles this efficiently; negligible performance impact at our scale
   - **Mitigation**: Chunk relationships are simple (no complex properties)

2. **More Nodes to Query** ⚠️
   - Must traverse `(doc)-[:CONTAINS]->(chunk)` in queries
   - **Mitigation**: Cypher is optimized for traversals; this is the intended use case
   - **Mitigation**: Vector index on chunks is fast (HNSW algorithm)

3. **Slightly More Complex Queries** ⚠️
   - Need to join chunk results with parent documents
   - **Mitigation**: Pattern is consistent across all queries
   - **Mitigation**: Encapsulated in `VectorOperations.semantic_search()`

## Alternatives Considered

### Alternative 1: Chunks as Array Properties

**Approach**: Store chunks as JSON array on document nodes

```cypher
(doc:Architecture {
  chunks: [
    {content: "...", embedding: [...], index: 0},
    {content: "...", embedding: [...], index: 1}
  ]
})
```

**Rejected Because**:
- ❌ Cannot create vector indexes on array elements (Neo4j limitation)
- ❌ Search returns entire document, not specific chunks
- ❌ Cannot annotate or version individual chunks
- ❌ Difficult to query chunk-level relationships
- ❌ Large arrays slow down document queries (all chunks loaded)
- ❌ No way to reference a specific chunk from other nodes

### Alternative 2: Hybrid Approach

**Approach**: Store both chunk nodes AND chunk arrays on documents

**Rejected Because**:
- ❌ Dual maintenance burden (must update both)
- ❌ Risk of data inconsistency between node and property
- ❌ Doubles storage requirements for chunks
- ❌ Adds complexity without clear benefit

### Alternative 3: Chunk Nodes WITHOUT Embeddings

**Approach**: Store embeddings only on documents, use chunks for structure

**Rejected Because**:
- ❌ Cannot do chunk-level semantic search
- ❌ Loses fine-grained search capability
- ❌ Would need separate vector store for chunk embeddings
- ❌ Misses the primary use case (chunk-level semantic similarity)

## Consequences

### Positive Consequences

- ✅ **Fine-grained search**: Users get specific relevant sections, not full documents
- ✅ **Future-proof**: Enables chunk versioning, annotations, provenance tracking
- ✅ **Flexible data model**: Can add chunk-level relationships as needed
- ✅ **Better UX**: Search results show exact matching sections with context
- ✅ **Scalable**: Neo4j handles thousands of chunk nodes efficiently
- ✅ **Clean separation**: Documents = metadata, Chunks = searchable content

### Negative Consequences

- ⚠️ **More nodes**: ~20x increase in node count (1 doc = ~20 chunks)
  - **Impact**: Negligible at our scale (1000 docs = 20k chunks is small for Neo4j)
- ⚠️ **Relationship overhead**: More traversals in queries
  - **Impact**: Minimal; this is what Neo4j is optimized for
- ⚠️ **Slightly complex queries**: Must join chunks with documents
  - **Impact**: Encapsulated in `VectorOperations.semantic_search()`

### Migration Path

**For existing data**:
- Documents without chunks will continue to work (backward compatible)
- Documents can be re-ingested to generate chunks
- No breaking changes to existing API contracts

**For future enhancements**:
- Chunk versioning: `(new_chunk)-[:SUPERSEDES]->(old_chunk)`
- Chunk annotations: `(chunk)-[:TAGGED_AS]->(tag:Tag)`
- Cross-document chunk links: `(chunk1)-[:RELATED_TO]->(chunk2)`
- Chunk provenance: `(chunk)-[:DERIVED_FROM]->(source)`

## Validation

### Acceptance Criteria

- [x] `Chunk` node type added to schema (src/graph/schema.py)
- [x] `CONTAINS` relationship type added and whitelisted
- [x] Vector index created for chunk embeddings
- [x] `DocumentGraphAdapter.store_document()` creates chunks
- [x] `VectorOperations.semantic_search()` returns chunk-level results
- [x] Security tests validate `CONTAINS` relationship
- [x] Chunks stored with embeddings via `store_embedding()`

### Performance Characteristics

- **Chunk storage**: ~1ms per chunk (tested with nomic-embed-text)
- **Semantic search**: ~50ms for top-10 chunks (768-dim HNSW index)
- **Memory overhead**: ~1KB per chunk node (content + embedding + metadata)
- **Storage impact**: 20x nodes, negligible for target scale (< 100k chunks)

### Test Coverage

- Unit tests: Chunk creation, embedding storage, relationship creation
- Integration tests: End-to-end document ingestion with chunks
- Security tests: `CONTAINS` relationship validation

## References

- Sprint Plan: Week 2, Task 2.1 (Chunk Storage Strategy)
- Implementation: `src/integration/document_adapter.py`
- Search: `src/graph/vector_ops.py::semantic_search()`
- Schema: `src/graph/schema.py` (NodeLabels.CHUNK, RelationshipTypes.CONTAINS)

## Notes

- This decision aligns with RAG best practices (chunk-level retrieval)
- Neo4j 5.x native vector indexes make this approach performant
- Future work: Implement chunk-level versioning and annotations
- Consider: Chunk overlap strategy (currently 200 chars, may need tuning)

---

**Last Updated**: 2024-11-10
**Supersedes**: N/A (initial decision)
**Related ADRs**: ADR-001 (Technology Stack - Neo4j selection)
