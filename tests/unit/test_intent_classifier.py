#!/usr/bin/env python3
"""
Unit tests for Intent Classifier.
"""

import pytest
from domains.agent_interface.intent_classifier import IntentClassifier


class TestIntentClassifier:
    """Test suite for IntentClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return IntentClassifier()

    def test_locate_intent(self, classifier):
        """Test locate intent classification."""
        queries = [
            "Where is my docker-compose.yml?",
            "Find the path to nginx.conf",
            "Locate the config file for postgres",
            "Which directory has the README?",
            "Show me the path to /etc/nginx",
        ]

        for query in queries:
            intent, confidence = classifier.classify(query)
            assert intent == "locate", f"Failed for: {query}"
            assert confidence > 0.0

    def test_changed_intent(self, classifier):
        """Test changed intent classification."""
        queries = [
            "What changed in /etc today?",
            "Recent changes to docker-compose.yml",
            "Modified files since 10:00",
            "Updates in /var/log",
            "What's changed in the last hour?",
        ]

        for query in queries:
            intent, confidence = classifier.classify(query)
            assert intent == "changed", f"Failed for: {query}"
            assert confidence > 0.0

    def test_find_text_intent(self, classifier):
        """Test find_text intent classification."""
        queries = [
            "Find OCR text about TLS certificates",
            "What did I saw on screen about docker?",
            "Search for screenshot with error message",
            "Screen showed something about nginx",
            "Find text I was looking at this morning",
        ]

        for query in queries:
            intent, confidence = classifier.classify(query)
            assert intent == "find_text", f"Failed for: {query}"
            assert confidence > 0.0

    def test_status_intent(self, classifier):
        """Test status intent classification."""
        queries = [
            "Which containers are running?",
            "Status of MCP servers",
            "List all services",
            "What MCPs are up?",
            "Show me running containers",
            "Are any services down?",
        ]

        for query in queries:
            intent, confidence = classifier.classify(query)
            assert intent == "status", f"Failed for: {query}"
            assert confidence > 0.0

    def test_unknown_intent(self, classifier):
        """Test unknown intent for nonsense queries."""
        queries = [
            "Hello world",
            "The quick brown fox",
            "Random gibberish query",
        ]

        for query in queries:
            intent, confidence = classifier.classify(query)
            assert intent == "unknown", f"Should be unknown: {query}"
            assert confidence == 0.0

    def test_confidence_scoring(self, classifier):
        """Test confidence scoring is reasonable."""
        # Strong match (multiple patterns)
        intent, confidence = classifier.classify("Where is the path to my file?")
        assert intent == "locate"
        assert confidence > 0.2  # Should have reasonable confidence

        # Weak match (single pattern)
        intent, confidence = classifier.classify("locate something")
        assert intent == "locate"
        assert confidence > 0.0

    def test_case_insensitive(self, classifier):
        """Test classifier is case insensitive."""
        queries = [
            ("WHERE IS MY FILE?", "locate"),
            ("WHAT CHANGED IN /ETC?", "changed"),
            ("Find OCR Text", "find_text"),
            ("Status of Containers", "status"),
        ]

        for query, expected_intent in queries:
            intent, _ = classifier.classify(query)
            assert intent == expected_intent, f"Failed for: {query}"

    def test_get_patterns(self, classifier):
        """Test pattern retrieval."""
        patterns = classifier.get_intent_patterns()

        assert 'locate' in patterns
        assert 'changed' in patterns
        assert 'find_text' in patterns
        assert 'status' in patterns

        assert isinstance(patterns['locate'], list)
        assert len(patterns['locate']) > 0
