#!/usr/bin/env python3
"""
Integration tests for Agent Interface components.

Tests the full pipeline: Intent Classifier → Parameter Extractor → Query Builder
"""

import pytest
from datetime import datetime
from domains.agent_interface.intent_classifier import IntentClassifier
from domains.agent_interface.parameter_extractor import ParameterExtractor
from domains.agent_interface.query_builder import QueryBuilder


class TestAgentInterfaceIntegration:
    """Test integration of all agent interface components."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return IntentClassifier()

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ParameterExtractor()

    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return QueryBuilder()

    def test_locate_pipeline(self, classifier, extractor, builder):
        """Test full pipeline for locate query."""
        query = "Where is my docker-compose.yml?"

        # Step 1: Classify intent
        intent, confidence = classifier.classify(query)
        assert intent == 'locate'
        assert confidence > 0.0

        # Step 2: Extract parameters
        params = extractor.extract(query, intent)
        assert 'search_term' in params
        assert 'docker-compose.yml' in params['search_term']

        # Step 3: Build Cypher query
        cypher, cypher_params = builder.build(intent, params)
        assert 'MATCH (f:File)' in cypher
        assert 'search_term' in cypher_params

    def test_changed_pipeline(self, classifier, extractor, builder):
        """Test full pipeline for changed query."""
        query = "What changed in /etc since 10:00?"

        # Step 1: Classify intent
        intent, confidence = classifier.classify(query)
        assert intent == 'changed'

        # Step 2: Extract parameters
        params = extractor.extract(query, intent)
        assert 'path' in params
        assert params['path'] == '/etc'
        assert 'since' in params
        assert isinstance(params['since'], datetime)

        # Step 3: Build Cypher query
        cypher, cypher_params = builder.build(intent, params)
        assert 'MATCH (e:Event)' in cypher
        assert 'path' in cypher_params
        assert 'since' in cypher_params

    def test_find_text_pipeline(self, classifier, extractor, builder):
        """Test full pipeline for find_text query."""
        query = "Find OCR text about TLS certificates from this morning"

        # Step 1: Classify intent
        intent, confidence = classifier.classify(query)
        assert intent == 'find_text'

        # Step 2: Extract parameters
        params = extractor.extract(query, intent)
        assert 'search_text' in params
        assert 'TLS certificates' in params['search_text']
        assert 'since' in params

        # Step 3: Build Cypher query
        cypher, cypher_params = builder.build(intent, params)
        assert 'MATCH (chunk:Chunk)' in cypher
        assert '[:HAS_OCR]' in cypher
        assert 'search_text' in cypher_params

    def test_status_pipeline(self, classifier, extractor, builder):
        """Test full pipeline for status query."""
        query = "Which MCP servers are running?"

        # Step 1: Classify intent
        intent, confidence = classifier.classify(query)
        assert intent == 'status'

        # Step 2: Extract parameters
        params = extractor.extract(query, intent)
        assert 'resource_type' in params
        assert params['resource_type'] == 'mcps'

        # Step 3: Build Cypher query
        cypher, cypher_params = builder.build(intent, params)
        assert 'MATCH (m:MCPServer)' in cypher

    def test_multiple_queries_in_sequence(self, classifier, extractor, builder):
        """Test processing multiple different queries in sequence."""
        queries = [
            ("Where is nginx.conf?", "locate"),
            ("What changed today?", "changed"),
            ("Find screenshot with error", "find_text"),
            ("List containers", "status"),
        ]

        for query_text, expected_intent in queries:
            # Classify
            intent, _ = classifier.classify(query_text)
            assert intent == expected_intent

            # Extract
            params = extractor.extract(query_text, intent)
            assert params is not None
            assert isinstance(params, dict)

            # Build
            cypher, cypher_params = builder.build(intent, params)
            assert isinstance(cypher, str)
            assert len(cypher) > 0
            assert isinstance(cypher_params, dict)

    def test_edge_case_empty_results(self, classifier, extractor, builder):
        """Test edge case: query that might return no results."""
        query = "Where is nonexistent_file_xyz123.txt?"

        intent, _ = classifier.classify(query)
        params = extractor.extract(query, intent)
        cypher, cypher_params = builder.build(intent, params)

        # Should still generate valid query
        assert 'MATCH' in cypher
        assert 'search_term' in cypher_params
        assert 'nonexistent_file_xyz123.txt' in cypher_params['search_term']

    def test_complex_time_query(self, classifier, extractor, builder):
        """Test complex query with time constraints."""
        query = "What changed in /var/log in the last 3 hours?"

        intent, _ = classifier.classify(query)
        params = extractor.extract(query, intent)

        assert params['path'] == '/var/log'
        assert 'since' in params
        assert isinstance(params['since'], datetime)

        cypher, cypher_params = builder.build(intent, params)
        assert 'e.path STARTS WITH' in cypher
        assert 'e.ts >=' in cypher
