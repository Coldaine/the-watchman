# Retrieval and Context Assembly

## Overview
The Retrieval and Context subdomain implements the RAG (Retrieval-Augmented Generation) pattern, combining semantic vector search with graph traversal to provide agents with relevant, accurate context. It assembles information from multiple sources to answer queries and support decision-making.

## Core Concepts

### Retrieval Methods
- **Vector Search**: Semantic similarity using embeddings
- **Graph Traversal**: Following relationships in Neo4j
- **Hybrid Search**: Combining vector and keyword matching
- **Faceted Search**: Filtering by metadata attributes

### Context Types
- **Direct Context**: Exact matches to queries
- **Related Context**: Connected via graph relationships
- **Historical Context**: Previous versions and decisions
- **Supplementary Context**: Supporting documentation

### Ranking Strategies
- **Relevance Scoring**: Cosine similarity for vectors
- **Graph Distance**: Hop count from query node
- **Recency Weighting**: Prefer newer content
- **Authority Scoring**: Based on approval status

## Implementation Details

### Retrieval Engine

```python
from typing import List, Dict, Optional, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class RetrievalQuery:
    """Query specification for retrieval"""
    text: str                           # Query text
    query_type: str                     # semantic|exact|hybrid
    filters: Dict[str, Any]             # Metadata filters
    limit: int = 10                     # Max results
    min_score: float = 0.7              # Minimum similarity

    # Context preferences
    include_history: bool = False       # Include superseded docs
    include_code: bool = True           # Include code artifacts
    max_graph_distance: int = 2        # Max hops in graph

@dataclass
class RetrievalResult:
    """Single retrieval result"""
    node_id: str
    content: str
    score: float
    node_type: str                      # Architecture|Design|Code|etc

    # Metadata
    title: Optional[str]
    path: Optional[str]
    version: Optional[str]
    status: Optional[str]

    # Relationships
    distance: int                       # Graph distance from query
    relationship_type: Optional[str]   # How related to query

class RetrievalEngine:
    """Main retrieval orchestrator"""

    def __init__(self, graph: GraphOperations,
                 embedder: EmbeddingGenerator):
        self.graph = graph
        self.embedder = embedder
        self.vector_index = "chunk_embedding"

    async def retrieve(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Execute retrieval based on query type"""

        if query.query_type == "semantic":
            results = await self._semantic_search(query)

        elif query.query_type == "exact":
            results = await self._exact_search(query)

        elif query.query_type == "hybrid":
            # Combine semantic and exact
            semantic_results = await self._semantic_search(query)
            exact_results = await self._exact_search(query)
            results = self._merge_results(semantic_results, exact_results)

        else:
            raise ValueError(f"Unknown query type: {query.query_type}")

        # Apply filters
        if query.filters:
            results = self._apply_filters(results, query.filters)

        # Expand with graph context
        if query.max_graph_distance > 0:
            results = await self._expand_graph_context(results, query)

        # Rank and limit
        results = self._rank_results(results)[:query.limit]

        return results
```

### Semantic Search Implementation

```python
class SemanticSearch:
    """Vector-based semantic search"""

    async def search(self, query_text: str,
                     index_name: str,
                     limit: int = 10,
                     min_score: float = 0.7) -> List[Dict]:
        """Perform vector similarity search"""

        # Generate query embedding
        query_embedding = await self.embedder.generate_embedding(query_text)

        # Search via Neo4j vector index
        cypher = """
            CALL db.index.vector.queryNodes(
                $index_name,
                $limit * 2,  // Get extra for filtering
                $query_embedding
            ) YIELD node, score
            WHERE score >= $min_score
            WITH node, score
            MATCH (node)-[:BELONGS_TO]->(doc)
            RETURN node {
                .id, .content,
                score: score,
                doc_id: doc.id,
                doc_type: doc.doc_type,
                doc_title: doc.title,
                doc_path: doc.path,
                doc_version: doc.version,
                doc_status: doc.status
            } as result
            ORDER BY score DESC
            LIMIT $limit
        """

        results = await self.graph.query(cypher, {
            'index_name': index_name,
            'limit': limit,
            'query_embedding': query_embedding.tolist(),
            'min_score': min_score
        })

        return [r['result'] for r in results]

    async def multi_vector_search(self, query_text: str,
                                 indices: List[str]) -> List[Dict]:
        """Search across multiple vector indices"""

        results = []

        for index_name in indices:
            index_results = await self.search(
                query_text=query_text,
                index_name=index_name
            )
            results.extend(index_results)

        # Deduplicate and sort by score
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x['score'], reverse=True):
            if r['id'] not in seen:
                seen.add(r['id'])
                unique_results.append(r)

        return unique_results
```

### Graph Context Expansion

```python
class GraphContextExpander:
    """Expand results with graph relationships"""

    async def expand_context(self, initial_results: List[RetrievalResult],
                            max_distance: int = 2) -> List[RetrievalResult]:
        """Add related nodes via graph traversal"""

        expanded = list(initial_results)
        node_ids = [r.node_id for r in initial_results]

        for distance in range(1, max_distance + 1):
            # Find connected nodes at this distance
            cypher = """
                UNWIND $node_ids as node_id
                MATCH (start {id: node_id})
                MATCH path = (start)-[*..{distance}]-(related)
                WHERE NOT related.id IN $already_found
                AND (
                    related:Architecture OR
                    related:Design OR
                    related:Requirement OR
                    related:Decision
                )
                RETURN DISTINCT related {
                    .id, .content, .title, .path, .version, .status,
                    node_type: labels(related)[0],
                    distance: {distance},
                    relationship: type(last(relationships(path)))
                } as result
                LIMIT 20
            """.format(distance=distance)

            results = await self.graph.query(cypher, {
                'node_ids': node_ids,
                'already_found': [r.node_id for r in expanded],
                'distance': distance
            })

            for r in results:
                expanded.append(RetrievalResult(
                    node_id=r['result']['id'],
                    content=r['result'].get('content', ''),
                    score=self._calculate_graph_score(distance),
                    node_type=r['result']['node_type'],
                    title=r['result'].get('title'),
                    path=r['result'].get('path'),
                    version=r['result'].get('version'),
                    status=r['result'].get('status'),
                    distance=distance,
                    relationship_type=r['result']['relationship']
                ))

        return expanded

    def _calculate_graph_score(self, distance: int) -> float:
        """Score based on graph distance"""
        # Decay score with distance
        return 1.0 / (1.0 + distance)
```

### Hybrid Search

```python
class HybridSearch:
    """Combine vector and keyword search"""

    def __init__(self, semantic_search: SemanticSearch,
                 keyword_weight: float = 0.3):
        self.semantic_search = semantic_search
        self.keyword_weight = keyword_weight
        self.vector_weight = 1.0 - keyword_weight

    async def search(self, query: str) -> List[RetrievalResult]:
        """Perform hybrid search"""

        # Semantic search
        vector_results = await self.semantic_search.search(query)

        # Keyword search using full-text index
        keyword_results = await self._keyword_search(query)

        # Combine results
        combined = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results
        )

        return combined

    async def _keyword_search(self, query: str) -> List[Dict]:
        """Full-text keyword search"""

        cypher = """
            CALL db.index.fulltext.queryNodes(
                'doc_content_search',
                $query
            ) YIELD node, score
            RETURN node {
                .id, .content, .title, .path,
                score: score
            } as result
            ORDER BY score DESC
            LIMIT 20
        """

        results = await self.graph.query(cypher, {'query': query})
        return [r['result'] for r in results]

    def _reciprocal_rank_fusion(self, vector_results: List,
                               keyword_results: List) -> List:
        """Combine results using RRF"""

        scores = {}

        # Score vector results
        for rank, result in enumerate(vector_results):
            doc_id = result['id']
            scores[doc_id] = scores.get(doc_id, 0) + \
                           self.vector_weight * (1.0 / (rank + 1))

        # Score keyword results
        for rank, result in enumerate(keyword_results):
            doc_id = result['id']
            scores[doc_id] = scores.get(doc_id, 0) + \
                           self.keyword_weight * (1.0 / (rank + 1))

        # Sort by combined score
        sorted_ids = sorted(scores.keys(),
                          key=lambda x: scores[x],
                          reverse=True)

        # Build final results
        id_to_result = {}
        for r in vector_results + keyword_results:
            id_to_result[r['id']] = r

        return [id_to_result[doc_id] for doc_id in sorted_ids]
```

### Context Assembly

```python
class ContextAssembler:
    """Assemble context for agent consumption"""

    def __init__(self, max_context_length: int = 8000):
        self.max_context_length = max_context_length

    def assemble_context(self, results: List[RetrievalResult],
                        query: str) -> AssembledContext:
        """Create structured context from results"""

        # Group by type
        grouped = self._group_by_type(results)

        # Prioritize content
        prioritized = self._prioritize_content(grouped, query)

        # Build context sections
        sections = []

        # Primary context (highest relevance)
        if prioritized['primary']:
            sections.append(ContextSection(
                title="Primary Context",
                content=self._format_results(prioritized['primary']),
                relevance="high"
            ))

        # Supporting context
        if prioritized['supporting']:
            sections.append(ContextSection(
                title="Supporting Documentation",
                content=self._format_results(prioritized['supporting']),
                relevance="medium"
            ))

        # Historical context
        if prioritized['historical']:
            sections.append(ContextSection(
                title="Historical Context",
                content=self._format_results(prioritized['historical']),
                relevance="low"
            ))

        # Truncate if needed
        context = self._truncate_context(sections)

        return AssembledContext(
            query=query,
            sections=context,
            total_results=len(results),
            truncated=self._was_truncated
        )

    def _prioritize_content(self, grouped: Dict,
                          query: str) -> Dict[str, List]:
        """Prioritize content for context"""

        prioritized = {
            'primary': [],
            'supporting': [],
            'historical': []
        }

        # Architecture and approved designs are primary
        for result in grouped.get('Architecture', []):
            if result.status == 'approved':
                prioritized['primary'].append(result)
            else:
                prioritized['supporting'].append(result)

        for result in grouped.get('Design', []):
            if result.status == 'approved' and result.score > 0.8:
                prioritized['primary'].append(result)
            else:
                prioritized['supporting'].append(result)

        # Requirements are supporting
        prioritized['supporting'].extend(grouped.get('Requirement', []))

        # Superseded docs are historical
        for result in grouped.get('Architecture', []):
            if result.status == 'superseded':
                prioritized['historical'].append(result)

        return prioritized

    def _format_results(self, results: List[RetrievalResult]) -> str:
        """Format results for context"""

        formatted = []

        for result in results:
            # Format based on type
            if result.node_type == 'Architecture':
                formatted.append(
                    f"## {result.title} (v{result.version})\n"
                    f"Status: {result.status}\n"
                    f"Relevance: {result.score:.2f}\n\n"
                    f"{result.content}\n"
                )

            elif result.node_type == 'Design':
                formatted.append(
                    f"### {result.title}\n"
                    f"Component: {result.path}\n"
                    f"Relevance: {result.score:.2f}\n\n"
                    f"{result.content}\n"
                )

            else:
                formatted.append(f"{result.content}\n")

        return "\n---\n".join(formatted)
```

### Query Understanding

```python
class QueryUnderstanding:
    """Analyze and enhance queries"""

    def __init__(self):
        self.query_patterns = {
            'architecture': r'(architecture|design|pattern|structure)',
            'implementation': r'(implement|code|develop|build)',
            'requirement': r'(requirement|must|should|need)',
            'decision': r'(decision|choice|why|rationale)'
        }

    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query intent and type"""

        # Detect query type
        query_type = self._detect_query_type(query)

        # Extract entities
        entities = self._extract_entities(query)

        # Identify filters
        filters = self._extract_filters(query)

        # Suggest expansions
        expansions = self._suggest_expansions(query)

        return QueryAnalysis(
            original_query=query,
            query_type=query_type,
            entities=entities,
            filters=filters,
            suggested_expansions=expansions
        )

    def _detect_query_type(self, query: str) -> str:
        """Identify type of query"""

        query_lower = query.lower()

        for pattern_type, pattern in self.query_patterns.items():
            if re.search(pattern, query_lower):
                return pattern_type

        return 'general'

    def expand_query(self, query: str) -> List[str]:
        """Generate query variations"""

        variations = [query]

        # Add synonyms
        synonyms = {
            'implement': ['build', 'develop', 'create'],
            'design': ['architecture', 'structure', 'pattern'],
            'requirement': ['constraint', 'specification', 'must have']
        }

        for word, syns in synonyms.items():
            if word in query.lower():
                for syn in syns:
                    variations.append(query.replace(word, syn))

        return variations
```

## Interfaces

### Retrieval API

```python
class RetrievalService:
    """Main retrieval service interface"""

    def __init__(self):
        self.retrieval_engine = RetrievalEngine()
        self.context_assembler = ContextAssembler()
        self.query_analyzer = QueryUnderstanding()

    async def retrieve_context(self, query_text: str,
                              options: RetrievalOptions = None) -> AssembledContext:
        """Main retrieval endpoint"""

        # Analyze query
        analysis = self.query_analyzer.analyze_query(query_text)

        # Build retrieval query
        retrieval_query = RetrievalQuery(
            text=query_text,
            query_type=options.search_type if options else 'hybrid',
            filters=analysis.filters,
            limit=options.max_results if options else 10,
            include_history=options.include_history if options else False
        )

        # Retrieve results
        results = await self.retrieval_engine.retrieve(retrieval_query)

        # Assemble context
        context = self.context_assembler.assemble_context(results, query_text)

        # Log retrieval
        await self._log_retrieval(query_text, results, context)

        return context
```

### REST API Endpoints

```yaml
/retrieval/search:
  method: POST
  description: Semantic search
  body:
    query: string
    limit: integer
    filters: object
  response: List[RetrievalResult]

/retrieval/context:
  method: POST
  description: Get assembled context
  body:
    query: string
    options: RetrievalOptions
  response: AssembledContext

/retrieval/similar:
  method: POST
  description: Find similar documents
  body:
    document_id: string
    limit: integer
  response: List[RetrievalResult]

/retrieval/graph:
  method: POST
  description: Graph-based retrieval
  body:
    start_node: string
    max_distance: integer
    relationship_types: List[string]
  response: GraphContext
```

## Configuration

### Retrieval Configuration
```yaml
# config/retrieval.yaml
retrieval:
  # Search settings
  search:
    default_type: hybrid
    default_limit: 10
    min_score_threshold: 0.7

    vector_search:
      indices:
        - chunk_embedding
        - doc_embedding
      similarity_function: cosine

    keyword_search:
      index_name: doc_content_search
      analyzer: standard

    hybrid:
      vector_weight: 0.7
      keyword_weight: 0.3

  # Context assembly
  context:
    max_length: 8000
    include_metadata: true
    format: markdown

    prioritization:
      approved_boost: 1.5
      recent_boost: 1.2
      architecture_weight: 2.0
      design_weight: 1.5
      code_weight: 1.0

  # Graph expansion
  graph:
    max_distance: 2
    max_expanded_nodes: 20
    relationship_weights:
      IMPLEMENTS: 1.0
      SATISFIES: 0.9
      REFERENCES: 0.7
      SUPERSEDES: 0.5

  # Caching
  cache:
    enabled: true
    ttl: 300  # seconds
    max_size: 1000
```

## Common Operations

### 1. Agent Context Retrieval
```python
async def get_agent_context(agent_request: AgentRequest):
    """Get context for agent request"""

    service = RetrievalService()

    # Build query from request
    query = f"{agent_request.action} {agent_request.target_type}"
    if agent_request.content:
        query += f" {agent_request.content[:100]}"

    # Get context
    context = await service.retrieve_context(
        query_text=query,
        options=RetrievalOptions(
            search_type='hybrid',
            max_results=15,
            include_history=False,
            filters={
                'status': 'approved',
                'subsystem': agent_request.subsystem
            }
        )
    )

    return context
```

### 2. Similar Document Search
```python
async def find_similar_documents(doc_id: str):
    """Find documents similar to given document"""

    # Get document embedding
    cypher = """
        MATCH (d {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
        RETURN avg(c.embedding) as avg_embedding
    """

    result = await graph.query(cypher, {'doc_id': doc_id})
    doc_embedding = result[0]['avg_embedding']

    # Search for similar
    similar_results = await semantic_search.search_with_embedding(
        embedding=doc_embedding,
        limit=10,
        min_score=0.8
    )

    return similar_results
```

### 3. Impact Analysis Context
```python
async def get_impact_context(node_id: str):
    """Get context showing impact of changes"""

    # Find all dependent nodes
    cypher = """
        MATCH (n {id: $node_id})
        MATCH (n)<-[:IMPLEMENTS|:SATISFIES|:REFERENCES*1..3]-(dependent)
        RETURN dependent {
            .id, .title, .type,
            path: [x in nodes(path) | x.id]
        } as result
    """

    dependents = await graph.query(cypher, {'node_id': node_id})

    # Assemble impact context
    context = {
        'direct_impact': [],
        'indirect_impact': [],
        'total_affected': len(dependents)
    }

    for dep in dependents:
        if len(dep['result']['path']) == 2:
            context['direct_impact'].append(dep['result'])
        else:
            context['indirect_impact'].append(dep['result'])

    return context
```

## Troubleshooting

### Common Issues

#### "No results found"
- **Cause**: Query too specific or embeddings misaligned
- **Solution**: Expand query, lower min_score threshold
```python
# Use query expansion
expanded = query_analyzer.expand_query(original_query)
for q in expanded:
    results = await retrieve(q)
    if results:
        break
```

#### "Context too large"
- **Cause**: Too many results or verbose content
- **Solution**: Adjust prioritization and truncation
```python
context_assembler = ContextAssembler(
    max_context_length=6000  # Reduce size
)
```

#### "Slow retrieval"
- **Cause**: No caching or inefficient queries
- **Solution**: Enable caching, optimize Cypher
```python
# Enable result caching
@cache(ttl=300)
async def retrieve_cached(query):
    return await retrieval_engine.retrieve(query)
```

#### "Irrelevant results"
- **Cause**: Poor query understanding or ranking
- **Solution**: Improve query analysis and scoring
```python
# Add query-specific filters
filters = {
    'doc_type': detected_type,
    'status': 'approved'
}
```

### Performance Monitoring
```python
# Retrieval metrics
metrics = retrieval_service.get_metrics()
print(f"Avg retrieval time: {metrics.avg_retrieval_time}ms")
print(f"Cache hit rate: {metrics.cache_hit_rate}%")
print(f"Avg results per query: {metrics.avg_results}")
print(f"Vector search time: {metrics.vector_search_time}ms")
print(f"Graph expansion time: {metrics.graph_time}ms")
```

## References

- **Architecture Document**: [`docs/architecture.md`](../architecture.md)
- **Graph Operations**: [`docs/subdomains/graph-operations.md`](./graph-operations.md)
- **Document Processing**: [`docs/subdomains/document-processing.md`](./document-processing.md)
- **LangChain RAG**: https://python.langchain.com/docs/use_cases/question_answering/
- **Neo4j Vector Search**: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/