#!/usr/bin/env python3
"""
Unit tests for Parameter Extractor.
"""

import pytest
from datetime import datetime, timedelta
from domains.agent_interface.parameter_extractor import ParameterExtractor


class TestParameterExtractor:
    """Test suite for ParameterExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ParameterExtractor()

    def test_locate_params_simple(self, extractor):
        """Test extracting locate parameters - simple case."""
        params = extractor.extract("Where is my docker-compose.yml?", "locate")

        assert 'search_term' in params
        assert 'docker-compose.yml' in params['search_term']

    def test_locate_params_with_path(self, extractor):
        """Test extracting locate parameters with path."""
        params = extractor.extract("Find the path to nginx.conf", "locate")

        assert 'search_term' in params
        assert 'nginx.conf' in params['search_term']

    def test_locate_params_which_file(self, extractor):
        """Test extracting locate parameters with 'which file'."""
        params = extractor.extract("Which directory has README?", "locate")

        assert 'search_term' in params
        assert 'README' in params['search_term']

    def test_changed_params_with_path(self, extractor):
        """Test extracting changed parameters with path."""
        params = extractor.extract("What changed in /etc today?", "changed")

        assert 'path' in params
        assert params['path'] == '/etc'
        assert 'since' in params
        assert isinstance(params['since'], datetime)

    def test_changed_params_with_time(self, extractor):
        """Test extracting changed parameters with specific time."""
        params = extractor.extract("What changed since 10:00?", "changed")

        assert 'since' in params
        assert isinstance(params['since'], datetime)
        assert params['since'].hour == 10
        assert params['since'].minute == 0

    def test_changed_params_relative_time(self, extractor):
        """Test extracting changed parameters with relative time."""
        params = extractor.extract("What changed this morning?", "changed")

        assert 'since' in params
        assert isinstance(params['since'], datetime)
        assert params['since'].hour == 6

    def test_find_text_params_simple(self, extractor):
        """Test extracting find_text parameters."""
        params = extractor.extract("Find OCR text about TLS certificates", "find_text")

        assert 'search_text' in params
        assert 'TLS certificates' in params['search_text']

    def test_find_text_params_with_time(self, extractor):
        """Test extracting find_text parameters with time."""
        params = extractor.extract("Find screenshot with error from this morning", "find_text")

        assert 'search_text' in params
        assert 'since' in params
        assert isinstance(params['since'], datetime)

    def test_status_params_containers(self, extractor):
        """Test extracting status parameters for containers."""
        params = extractor.extract("Which containers are running?", "status")

        assert 'resource_type' in params
        assert params['resource_type'] == 'containers'

    def test_status_params_mcps(self, extractor):
        """Test extracting status parameters for MCPs."""
        params = extractor.extract("Status of MCP servers", "status")

        assert 'resource_type' in params
        assert params['resource_type'] == 'mcps'

    def test_status_params_services(self, extractor):
        """Test extracting status parameters for services."""
        params = extractor.extract("List all services", "status")

        assert 'resource_type' in params
        assert params['resource_type'] == 'services'

    def test_time_reference_yesterday(self, extractor):
        """Test time reference extraction for yesterday."""
        time_ref = extractor._extract_time_reference("What changed yesterday?")

        assert time_ref is not None
        now = datetime.now()
        expected = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert time_ref.date() == expected.date()

    def test_time_reference_last_hour(self, extractor):
        """Test time reference extraction for last hour."""
        time_ref = extractor._extract_time_reference("Changes in the last hour")

        assert time_ref is not None
        now = datetime.now()
        diff = now - time_ref
        # Should be approximately 1 hour ago (within 1 minute tolerance)
        assert 59 <= diff.total_seconds() / 60 <= 61

    def test_time_reference_specific_period(self, extractor):
        """Test time reference extraction for specific period."""
        time_ref = extractor._extract_time_reference("Changes in the last 3 hours")

        assert time_ref is not None
        now = datetime.now()
        diff = now - time_ref
        # Should be approximately 3 hours ago
        assert 179 <= diff.total_seconds() / 60 <= 181

    def test_no_time_reference(self, extractor):
        """Test when no time reference is present."""
        time_ref = extractor._extract_time_reference("Where is my file?")

        assert time_ref is None
