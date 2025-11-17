#!/usr/bin/env python3
"""
Query Builder for Agent Interface.

Builds Cypher queries from intent + parameters to execute against Neo4j.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class QueryBuilder:
    """Build Cypher queries from intent and parameters."""

    def build(self, intent: str, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Build Cypher query from intent and parameters.

        Args:
            intent: Query intent (locate, changed, find_text, status)
            params: Extracted parameters

        Returns:
            Tuple of (cypher_query, query_parameters)
        """
        if intent == 'locate':
            return self.build_locate_query(params)
        elif intent == 'changed':
            return self.build_changed_query(params)
        elif intent == 'find_text':
            return self.build_find_text_query(params)
        elif intent == 'status':
            return self.build_status_query(params)
        else:
            raise ValueError(f"Unknown intent: {intent}")

    def build_locate_query(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Build query to locate files/projects/directories.

        Returns results from Files, Projects, and Directories that match the search term.
        """
        search_term = params.get('search_term', '')

        query = """
        // Search files
        CALL {
            MATCH (f:File)
            WHERE f.path CONTAINS $search_term
            RETURN 'File' as type, f.path as path, null as name, null as details, f.path as sort_key
            LIMIT 10
        }

        UNION

        // Search projects
        CALL {
            MATCH (p:Project)
            WHERE p.name CONTAINS $search_term OR p.path CONTAINS $search_term
            RETURN 'Project' as type, p.path as path, p.name as name, p.type as details, p.path as sort_key
            LIMIT 10
        }

        UNION

        // Search directories
        CALL {
            MATCH (d:Directory)
            WHERE d.path CONTAINS $search_term
            RETURN 'Directory' as type, d.path as path, d.name as name, null as details, d.path as sort_key
            LIMIT 10
        }

        RETURN type, path, name, details
        ORDER BY sort_key
        LIMIT 20
        """

        query_params = {'search_term': search_term}

        logger.debug(f"Built locate query with params: {query_params}")
        return query, query_params

    def build_changed_query(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Build query for change timeline.

        Returns events filtered by path and time range.
        """
        path = params.get('path')
        since = params.get('since')

        query = """
        MATCH (e:Event)
        WHERE 1=1
        """

        query_params = {}

        # Add time filter if provided
        if since:
            query += " AND e.ts >= datetime($since)"
            query_params['since'] = since.isoformat()

        # Add path filter if provided
        if path:
            query += " AND e.path STARTS WITH $path"
            query_params['path'] = path

        # Add result selection and ordering
        query += """
        OPTIONAL MATCH (e)-[:ACTED_ON]->(entity)

        RETURN e.id as event_id,
               e.ts as timestamp,
               e.type as event_type,
               e.path as path,
               e.dest_path as dest_path,
               labels(entity) as entity_types
        ORDER BY e.ts DESC
        LIMIT 50
        """

        logger.debug(f"Built changed query with params: {query_params}")
        return query, query_params

    def build_find_text_query(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Build vector/full-text search query for OCR chunks.

        Searches OCR text and returns matching snapshots with context.
        """
        search_text = params.get('search_text', '')
        since = params.get('since')

        # Note: This uses full-text search. In production, you'd also want vector search
        # For now, using simple CONTAINS matching as full-text index may not exist yet
        query = """
        MATCH (chunk:Chunk)<-[:HAS_OCR]-(s:Snapshot)
        WHERE chunk.text CONTAINS $search_text
        """

        query_params = {'search_text': search_text}

        # Add time filter if provided
        if since:
            query += " AND s.ts >= datetime($since)"
            query_params['since'] = since.isoformat()

        query += """
        RETURN s.id as snapshot_id,
               s.ts as timestamp,
               s.app as app,
               s.window as window,
               s.path as screenshot_path,
               chunk.text as ocr_text,
               chunk.id as chunk_id
        ORDER BY s.ts DESC
        LIMIT 20
        """

        logger.debug(f"Built find_text query with params: {query_params}")
        return query, query_params

    def build_status_query(self, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Build query for status checks.

        Returns status of containers, MCPs, or services.
        """
        resource_type = params.get('resource_type', 'containers')

        queries = {
            'containers': """
                MATCH (c:Container)
                OPTIONAL MATCH (c)-[:EXPOSES]->(port:NetworkEndpoint)

                RETURN c.id as id,
                       c.name as name,
                       c.state as state,
                       c.image as image,
                       collect(DISTINCT port.host + ':' + toString(port.port)) as ports
                ORDER BY c.name
                LIMIT 50
            """,

            'mcps': """
                MATCH (m:MCPServer)
                OPTIONAL MATCH (m)-[:PROVIDES_TOOL]->(t:Tool)

                RETURN m.name as name,
                       m.status as status,
                       m.url as url,
                       count(DISTINCT t) as tool_count
                ORDER BY m.name
                LIMIT 50
            """,

            'services': """
                MATCH (s:Service)

                RETURN s.name as name,
                       s.state as state,
                       s.type as type,
                       s.description as description
                ORDER BY s.name
                LIMIT 50
            """
        }

        query = queries.get(resource_type, queries['containers'])
        query_params = {}

        logger.debug(f"Built status query for resource_type: {resource_type}")
        return query, query_params


# Convenience function
def build_query(intent: str, params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """Build Cypher query from intent and parameters."""
    builder = QueryBuilder()
    return builder.build(intent, params)
