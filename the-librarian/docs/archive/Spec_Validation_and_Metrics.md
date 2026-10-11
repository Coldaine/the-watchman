# Spec_Validation_and_Metrics.md

## Metrics and Success Criteria

### Key Performance Indicators

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Spec Compliance Rate** | >95% | Approved vs. total changes |
| **Drift Detection Time** | <5 minutes | Time from commit to detection |
| **False Positive Rate** | <10% | Invalid rejections / total |
| **Resolution Time** | <1 hour | Detection to resolution |
| **Agent Productivity** | No decrease | Tasks/day with vs. without |

## Core Validation Queries

### Find Uncovered Requirements
```cypher
MATCH (a:Architecture {id:$archId})-[:DEFINES]->(req:Requirement)
WHERE NOT (req)<-[:SATISFIES]-(:Design)
  AND req.status <> 'deferred'
RETURN req.rid, req.text, req.priority
ORDER BY req.priority DESC
```

### Detect Design Drift
```cypher
MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
OPTIONAL MATCH (dec:Decision)-[:SUPERSEDES]->(d)
WITH d, a, max(dec.date) AS last_decision
WHERE d.version > a.version 
  AND (last_decision IS NULL OR last_decision < d.last_reviewed)
RETURN d.id AS drifting_design, 
       a.id AS against_arch,
       d.version AS design_version,
       a.version AS arch_version
```

### Find Undocumented Changes
```cypher
MATCH (c:CodeArtifact)
WHERE NOT (c)-[:IMPLEMENTS]->(:Design|:Requirement)
  AND c.created_date > date() - duration('P7D')
RETURN c.path, c.lang, c.created_date
ORDER BY c.created_date DESC
```

### Check API Contract Violations
```cypher
MATCH (api:ApiContract)-[:CONTRACT_FOR]->(d:Design)
WHERE api.version CONTAINS "-dev" OR api.version CONTAINS "-wip"
  AND NOT EXISTS { 
    MATCH (:Decision {kind: 'approve'})-[:SUPERSEDES]->(api) 
  }
RETURN api.id, api.version, d.id, d.owners
```

## Drift Tolerance Policy

```yaml
drift_tolerance:
  critical_path:
    tolerance: none
    examples: 
      - "Core algorithm changes"
      - "Security boundaries"
      - "Data format modifications"
    
  optimization:
    tolerance: moderate
    examples:
      - "Performance improvements"
      - "Memory optimization"
      - "Caching strategies"
    
  implementation_detail:
    tolerance: high
    examples:
      - "Internal helper functions"
      - "Logging verbosity"
      - "Variable naming"
```

## Versioning Strategy

### Versioning Options

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **Strict Semver** | Public APIs, stable systems | `2.1.3` → Breaking/Feature/Fix |
| **Date-based** | Rapid iteration, continuous deployment | `2025.09.05` |
| **Git SHA** | Tight code-spec coupling | `spec-a3f2b9c` |
| **Hybrid** | Different strategies per doc type | Architecture: Semver, Tasks: Date |

## Librarian Toolbelt Class

```python
class LibrarianToolbelt:
    def __init__(self, graph_db, vector_db):
        self.graph = graph_db
        self.vector = vector_db
    
    def retrieve_semantic(self, query: str, filters: dict = None) -> List[Chunk]:
        """Vector search across all document types with optional filtering"""
        embeddings = self.vector.embed(query)
        results = self.vector.search(
            embeddings, 
            limit=10,
            metadata_filter=filters
        )
        return self._enrich_with_graph_context(results)
    
    def graph_requirements_coverage(self, subsystem: str) -> CoverageReport:
        """Analyze requirement satisfaction for a subsystem"""
        query = """
        MATCH (s:Subsystem {slug: $subsystem})<-[:OF_SUBSYSTEM]-(a:Architecture)
        MATCH (a)-[:DEFINES]->(req:Requirement)
        OPTIONAL MATCH (req)<-[:SATISFIES]-(d:Design)
        RETURN req, collect(d) as designs
        """
        results = self.graph.run(query, subsystem=subsystem)
        return self._build_coverage_report(results)
    
    def validate_pr(self, pr_number: int) -> ValidationResult:
        """Run all invariants against PR changes"""
        touched_files = self._get_pr_files(pr_number)
        validations = []
        
        # Check each invariant
        validations.append(self._check_architecture_primacy(touched_files))
        validations.append(self._check_requirements_coverage(touched_files))
        validations.append(self._check_version_discipline(touched_files))
        validations.append(self._check_decision_linkage(touched_files))
        
        return ValidationResult(validations)
    
    def record_decision(self, decision: Decision) -> None:
        """Record a decision with proper linkage and version updates"""
        # Create decision node
        self.graph.create(decision)
        
        # Update superseded documents
        for doc_id in decision.supersedes:
            self._bump_document_version(doc_id)
        
        # Link to research if provided
        if decision.research_refs:
            for ref in decision.research_refs:
                self.graph.create_relationship(
                    decision, "CREATED_FROM", ref
                )
```