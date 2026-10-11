"""
Predefined Cypher queries for drift detection, validation, and governance.

Contains all the critical queries from the architecture specification for
detecting drift, validating compliance, and maintaining graph integrity.
"""

from typing import List, Dict, Optional, Any
import logging

from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


# Query constants from architecture specification (lines 469-501)

FIND_UNCOVERED_REQUIREMENTS = """
MATCH (a:Architecture)-[:DEFINES]->(req:Requirement)
WHERE NOT exists((req)<-[:SATISFIES]-(:Design))
  AND req.status = 'active'
RETURN req.rid, req.text, req.priority, a.id as source
ORDER BY req.priority DESC
"""

DETECT_DESIGN_DRIFT = """
MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
WHERE d.version > a.version
  AND NOT exists((:Decision)-[:SUPERSEDES]->(d))
RETURN d.id, d.version, a.id, a.version,
       d.last_reviewed as last_design_update
"""

FIND_UNDOCUMENTED_CODE = """
MATCH (c:CodeArtifact)
WHERE NOT exists((c)-[:IMPLEMENTS]->(:Design|:Requirement))
  AND c.last_modified > datetime() - duration('P7D')
RETURN c.path, c.lang, c.last_modified
ORDER BY c.last_modified DESC
"""

CHECK_AGENT_COMPLIANCE_RATE = """
MATCH (r:AgentRequest)
WHERE r.timestamp > datetime() - duration('P30D')
WITH r.agent_id as agent,
     count(CASE WHEN r.status = 'approved' THEN 1 END) as approved,
     count(*) as total
RETURN agent,
       toFloat(approved) / total * 100 as compliance_rate
ORDER BY compliance_rate DESC
"""

# Additional governance queries

FIND_ORPHANED_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE NOT exists((:Architecture)-[:DEFINES]->(r))
RETURN r.rid, r.text, r.status
"""

FIND_CIRCULAR_DEPENDENCIES = """
MATCH p=(n)-[:SUPERSEDES*]->(n)
RETURN n.id as node_id, length(p) as cycle_length
"""

FIND_MISSING_EMBEDDINGS = """
MATCH (n:Architecture|Design)
WHERE n.embedding IS NULL
RETURN labels(n)[0] as node_type, n.id as node_id, n.title
"""

GET_DOCUMENT_HIERARCHY = """
MATCH (d:Design {id: $design_id})
OPTIONAL MATCH (d)-[:IMPLEMENTS]->(a:Architecture)
OPTIONAL MATCH (d)-[:SATISFIES]->(r:Requirement)
OPTIONAL MATCH (c:CodeArtifact)-[:IMPLEMENTS]->(d)
RETURN d, a, collect(DISTINCT r) as requirements,
       collect(DISTINCT c) as code_artifacts
"""

FIND_SUPERSEDED_DOCUMENTS = """
MATCH (new:Architecture)-[:SUPERSEDES]->(old:Architecture)
WHERE old.id = $doc_id
RETURN new
"""

DETECT_DRIFT_BY_TIMESTAMP = """
MATCH (d:Design)-[:IMPLEMENTS]->(a:Architecture)
WHERE d.modified_at > a.modified_at
  AND NOT exists((decision:Decision)-[:APPROVES]->
                (req:AgentRequest)-[:TARGETS]->(d))
RETURN d.id as design, a.id as architecture,
       d.modified_at as design_modified,
       a.modified_at as arch_modified
"""

FIND_RECENT_AGENT_REQUESTS = """
MATCH (ar:AgentRequest)
WHERE ar.timestamp > datetime() - duration('P7D')
OPTIONAL MATCH (ar)-[:TARGETS]->(target)
OPTIONAL MATCH (ar)-[:RESULTED_IN]->(decision:Decision)
RETURN ar, labels(target)[0] as target_type,
       target.id as target_id, decision
ORDER BY ar.timestamp DESC
LIMIT $limit
"""

GET_COMPLIANCE_BY_SUBSYSTEM = """
MATCH (a:Architecture)
WHERE a.subsystem = $subsystem
OPTIONAL MATCH (a)-[:DEFINES]->(req:Requirement)
OPTIONAL MATCH (req)<-[:SATISFIES]-(d:Design)
WITH a, count(req) as total_requirements,
     count(d) as satisfied_requirements
RETURN a.subsystem,
       total_requirements,
       satisfied_requirements,
       toFloat(satisfied_requirements) / total_requirements * 100 as compliance_rate
"""

FIND_HIGH_IMPACT_NODES = """
MATCH (n)
WHERE (n:Architecture OR n:Design)
WITH n, size((n)<-[:IMPLEMENTS|SATISFIES]-()) as impact_score
WHERE impact_score > $threshold
RETURN labels(n)[0] as node_type, n.id, n.title, impact_score
ORDER BY impact_score DESC
LIMIT $limit
"""

GET_AGENT_ACTIVITY_SUMMARY = """
MATCH (ar:AgentRequest)
WHERE ar.timestamp > datetime() - duration($period)
WITH ar.agent_id as agent,
     count(*) as total_requests,
     count(CASE WHEN ar.status = 'approved' THEN 1 END) as approved,
     count(CASE WHEN ar.status = 'rejected' THEN 1 END) as rejected,
     count(CASE WHEN ar.status = 'escalated' THEN 1 END) as escalated,
     avg(ar.processing_ms) as avg_processing_ms
RETURN agent, total_requests, approved, rejected, escalated,
       toFloat(approved) / total_requests * 100 as approval_rate,
       avg_processing_ms
ORDER BY total_requests DESC
"""


class QueryExecutor:
    """Executes predefined governance and validation queries."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize query executor.

        Args:
            connection: Neo4j connection instance
        """
        self.conn = connection

    async def find_uncovered_requirements(self) -> List[Dict[str, Any]]:
        """
        Find requirements that are not covered by any design.

        Returns:
            List of uncovered requirements with priority
        """
        try:
            results = await self.conn.execute_read(FIND_UNCOVERED_REQUIREMENTS)
            logger.info(f"Found {len(results)} uncovered requirements")
            return results
        except Exception as e:
            logger.error(f"Failed to find uncovered requirements: {e}")
            raise

    async def detect_design_drift(self) -> List[Dict[str, Any]]:
        """
        Detect designs that have drifted ahead of architecture versions.

        Returns:
            List of drifted designs
        """
        try:
            results = await self.conn.execute_read(DETECT_DESIGN_DRIFT)
            logger.info(f"Found {len(results)} drifted designs")
            return results
        except Exception as e:
            logger.error(f"Failed to detect design drift: {e}")
            raise

    async def find_undocumented_code(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Find code artifacts modified recently without design/requirement links.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of undocumented code artifacts
        """
        try:
            # Modify query to use custom days parameter
            query = f"""
            MATCH (c:CodeArtifact)
            WHERE NOT exists((c)-[:IMPLEMENTS]->(:Design|:Requirement))
              AND c.last_modified > datetime() - duration('P{days}D')
            RETURN c.path, c.lang, c.last_modified
            ORDER BY c.last_modified DESC
            """
            results = await self.conn.execute_read(query)
            logger.info(f"Found {len(results)} undocumented code artifacts")
            return results
        except Exception as e:
            logger.error(f"Failed to find undocumented code: {e}")
            raise

    async def check_agent_compliance_rate(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Calculate compliance rate for each agent.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            List of agents with compliance rates
        """
        try:
            query = f"""
            MATCH (r:AgentRequest)
            WHERE r.timestamp > datetime() - duration('P{days}D')
            WITH r.agent_id as agent,
                 count(CASE WHEN r.status = 'approved' THEN 1 END) as approved,
                 count(*) as total
            RETURN agent,
                   toFloat(approved) / total * 100 as compliance_rate
            ORDER BY compliance_rate DESC
            """
            results = await self.conn.execute_read(query)
            logger.info(f"Calculated compliance for {len(results)} agents")
            return results
        except Exception as e:
            logger.error(f"Failed to check agent compliance: {e}")
            raise

    async def find_orphaned_requirements(self) -> List[Dict[str, Any]]:
        """
        Find requirements not linked to any architecture.

        Returns:
            List of orphaned requirements
        """
        try:
            results = await self.conn.execute_read(FIND_ORPHANED_REQUIREMENTS)
            logger.info(f"Found {len(results)} orphaned requirements")
            return results
        except Exception as e:
            logger.error(f"Failed to find orphaned requirements: {e}")
            raise

    async def find_circular_dependencies(self) -> List[Dict[str, Any]]:
        """
        Find circular SUPERSEDES relationships.

        Returns:
            List of nodes involved in circular dependencies
        """
        try:
            results = await self.conn.execute_read(FIND_CIRCULAR_DEPENDENCIES)
            logger.info(f"Found {len(results)} circular dependencies")
            return results
        except Exception as e:
            logger.error(f"Failed to find circular dependencies: {e}")
            raise

    async def find_missing_embeddings(self) -> List[Dict[str, Any]]:
        """
        Find Architecture/Design nodes without embeddings.

        Returns:
            List of nodes missing embeddings
        """
        try:
            results = await self.conn.execute_read(FIND_MISSING_EMBEDDINGS)
            logger.info(f"Found {len(results)} nodes without embeddings")
            return results
        except Exception as e:
            logger.error(f"Failed to find missing embeddings: {e}")
            raise

    async def get_document_hierarchy(self, design_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete hierarchy for a design document.

        Args:
            design_id: Design document ID

        Returns:
            Dictionary with design, architecture, requirements, and code artifacts
        """
        try:
            results = await self.conn.execute_read(
                GET_DOCUMENT_HIERARCHY,
                {"design_id": design_id}
            )
            if results:
                logger.info(f"Retrieved hierarchy for design: {design_id}")
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get document hierarchy: {e}")
            raise

    async def detect_drift_by_timestamp(self) -> List[Dict[str, Any]]:
        """
        Detect drift based on modification timestamps.

        Returns:
            List of designs modified after their architecture
        """
        try:
            results = await self.conn.execute_read(DETECT_DRIFT_BY_TIMESTAMP)
            logger.info(f"Found {len(results)} timestamp-based drifts")
            return results
        except Exception as e:
            logger.error(f"Failed to detect drift by timestamp: {e}")
            raise

    async def find_recent_agent_requests(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find recent agent requests.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of recent agent requests
        """
        try:
            query = f"""
            MATCH (ar:AgentRequest)
            WHERE ar.timestamp > datetime() - duration('P{days}D')
            OPTIONAL MATCH (ar)-[:TARGETS]->(target)
            OPTIONAL MATCH (ar)-[:RESULTED_IN]->(decision:Decision)
            RETURN ar, labels(target)[0] as target_type,
                   target.id as target_id, decision
            ORDER BY ar.timestamp DESC
            LIMIT $limit
            """
            results = await self.conn.execute_read(query, {"limit": limit})
            logger.info(f"Found {len(results)} recent agent requests")
            return results
        except Exception as e:
            logger.error(f"Failed to find recent agent requests: {e}")
            raise

    async def get_compliance_by_subsystem(self, subsystem: str) -> Optional[Dict[str, Any]]:
        """
        Calculate requirement compliance for a subsystem.

        Args:
            subsystem: Subsystem name

        Returns:
            Compliance statistics
        """
        try:
            results = await self.conn.execute_read(
                GET_COMPLIANCE_BY_SUBSYSTEM,
                {"subsystem": subsystem}
            )
            if results:
                logger.info(f"Calculated compliance for subsystem: {subsystem}")
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get compliance by subsystem: {e}")
            raise

    async def find_high_impact_nodes(self, threshold: int = 5, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find nodes with high dependency counts (impact analysis).

        Args:
            threshold: Minimum number of dependencies
            limit: Maximum number of results

        Returns:
            List of high-impact nodes
        """
        try:
            results = await self.conn.execute_read(
                FIND_HIGH_IMPACT_NODES,
                {"threshold": threshold, "limit": limit}
            )
            logger.info(f"Found {len(results)} high-impact nodes")
            return results
        except Exception as e:
            logger.error(f"Failed to find high-impact nodes: {e}")
            raise

    async def get_agent_activity_summary(self, period: str = "P30D") -> List[Dict[str, Any]]:
        """
        Get activity summary for all agents.

        Args:
            period: ISO 8601 duration (e.g., 'P30D' for 30 days)

        Returns:
            Summary of agent activity
        """
        try:
            results = await self.conn.execute_read(
                GET_AGENT_ACTIVITY_SUMMARY,
                {"period": period}
            )
            logger.info(f"Generated activity summary for {len(results)} agents")
            return results
        except Exception as e:
            logger.error(f"Failed to get agent activity summary: {e}")
            raise

    async def run_health_checks(self) -> Dict[str, Any]:
        """
        Run all health check queries and return combined results.

        Returns:
            Dictionary with all health check results
        """
        logger.info("Running comprehensive health checks...")

        health = {
            "uncovered_requirements": [],
            "design_drift": [],
            "undocumented_code": [],
            "orphaned_requirements": [],
            "circular_dependencies": [],
            "missing_embeddings": [],
            "errors": []
        }

        try:
            health["uncovered_requirements"] = await self.find_uncovered_requirements()
            health["design_drift"] = await self.detect_design_drift()
            health["undocumented_code"] = await self.find_undocumented_code()
            health["orphaned_requirements"] = await self.find_orphaned_requirements()
            health["circular_dependencies"] = await self.find_circular_dependencies()
            health["missing_embeddings"] = await self.find_missing_embeddings()

            total_issues = sum([
                len(health["uncovered_requirements"]),
                len(health["design_drift"]),
                len(health["undocumented_code"]),
                len(health["orphaned_requirements"]),
                len(health["circular_dependencies"]),
                len(health["missing_embeddings"])
            ])

            health["summary"] = {
                "total_issues": total_issues,
                "health_status": "healthy" if total_issues == 0 else "degraded"
            }

            logger.info(f"Health check completed: {total_issues} total issues found")

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["errors"].append(str(e))
            health["summary"] = {"health_status": "error"}

        return health
