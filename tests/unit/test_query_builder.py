#!/usr/bin/env python3
"""
Unit tests for Query Builder.
"""

import pytest
from datetime import datetime
from domains.agent_interface.query_builder import QueryBuilder


class TestQueryBuilder:
    """Test suite for QueryBuilder."""

    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return QueryBuilder()

    def test_build_locate_query(self, builder):
        """Test building locate query."""
        params = {'search_term': 'docker-compose.yml'}
        query, query_params = builder.build('locate', params)

        assert 'MATCH (f:File)' in query
        assert 'MATCH (p:Project)' in query
        assert 'MATCH (d:Directory)' in query
        assert 'search_term' in query_params
        assert query_params['search_term'] == 'docker-compose.yml'

    def test_build_changed_query_with_path(self, builder):
        """Test building changed query with path."""
        params = {
            'path': '/etc',
            'since': datetime(2025, 11, 14, 10, 0, 0)
        }
        query, query_params = builder.build('changed', params)

        assert 'MATCH (e:Event)' in query
        assert 'e.ts >=' in query
        assert 'e.path STARTS WITH' in query
        assert 'path' in query_params
        assert 'since' in query_params
        assert query_params['path'] == '/etc'

    def test_build_changed_query_without_path(self, builder):
        """Test building changed query without path filter."""
        params = {
            'since': datetime(2025, 11, 14, 10, 0, 0)
        }
        query, query_params = builder.build('changed', params)

        assert 'MATCH (e:Event)' in query
        assert 'e.ts >=' in query
        assert 'since' in query_params
        assert 'path' not in query_params

    def test_build_changed_query_no_filters(self, builder):
        """Test building changed query with no filters."""
        params = {}
        query, query_params = builder.build('changed', params)

        assert 'MATCH (e:Event)' in query
        # Should still work, just no filters
        assert 'ORDER BY e.ts DESC' in query

    def test_build_find_text_query(self, builder):
        """Test building find_text query."""
        params = {'search_text': 'TLS certificate'}
        query, query_params = builder.build('find_text', params)

        assert 'MATCH (chunk:Chunk)' in query
        assert '[:HAS_OCR]' in query
        assert 'Snapshot' in query
        assert 'search_text' in query_params
        assert query_params['search_text'] == 'TLS certificate'

    def test_build_find_text_query_with_time(self, builder):
        """Test building find_text query with time filter."""
        params = {
            'search_text': 'error message',
            'since': datetime(2025, 11, 14, 6, 0, 0)
        }
        query, query_params = builder.build('find_text', params)

        assert 's.ts >=' in query
        assert 'since' in query_params

    def test_build_status_query_containers(self, builder):
        """Test building status query for containers."""
        params = {'resource_type': 'containers'}
        query, query_params = builder.build('status', params)

        assert 'MATCH (c:Container)' in query
        assert 'NetworkEndpoint' in query
        assert 'c.state' in query

    def test_build_status_query_mcps(self, builder):
        """Test building status query for MCPs."""
        params = {'resource_type': 'mcps'}
        query, query_params = builder.build('status', params)

        assert 'MATCH (m:MCPServer)' in query
        assert 'PROVIDES_TOOL' in query
        assert 'm.status' in query

    def test_build_status_query_services(self, builder):
        """Test building status query for services."""
        params = {'resource_type': 'services'}
        query, query_params = builder.build('status', params)

        assert 'MATCH (s:Service)' in query
        assert 's.state' in query

    def test_build_invalid_intent(self, builder):
        """Test building query with invalid intent."""
        params = {}

        with pytest.raises(ValueError, match="Unknown intent"):
            builder.build('invalid_intent', params)

    def test_locate_query_structure(self, builder):
        """Test locate query returns proper structure."""
        params = {'search_term': 'test'}
        query, query_params = builder.build('locate', params)

        # Should have UNION to combine results
        assert query.count('UNION') >= 2
        # Should return consistent columns
        assert 'RETURN type, path, name, details' in query
        # Should have limit
        assert 'LIMIT' in query

    def test_changed_query_ordering(self, builder):
        """Test changed query orders by timestamp descending."""
        params = {}
        query, query_params = builder.build('changed', params)

        assert 'ORDER BY e.ts DESC' in query

    def test_find_text_query_limit(self, builder):
        """Test find_text query has reasonable limit."""
        params = {'search_text': 'test'}
        query, query_params = builder.build('find_text', params)

        assert 'LIMIT 20' in query
