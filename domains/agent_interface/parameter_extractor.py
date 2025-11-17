#!/usr/bin/env python3
"""
Parameter Extractor for Agent Interface.

Extracts relevant parameters from user queries based on intent type.
Handles time parsing, path extraction, search term identification, etc.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger


class ParameterExtractor:
    """Extract parameters from queries based on intent."""

    def extract(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Extract parameters from query based on intent.

        Args:
            query: User query string
            intent: Classified intent type

        Returns:
            Dictionary of extracted parameters
        """
        if intent == 'locate':
            return self._extract_locate_params(query)
        elif intent == 'changed':
            return self._extract_changed_params(query)
        elif intent == 'find_text':
            return self._extract_find_text_params(query)
        elif intent == 'status':
            return self._extract_status_params(query)
        else:
            return {}

    def _extract_locate_params(self, query: str) -> Dict[str, Any]:
        """Extract parameters for locate queries."""
        params = {}

        # Extract search term - everything after the trigger phrase
        patterns = [
            r'where is (?:my |the )?(.+?)(?:\?|$)',
            r'find (?:the |my )?path (?:to |for )?(.+?)(?:\?|$)',
            r'locate (?:the |my )?(.+?)(?:\?|$)',
            r'which (?:file|directory|folder|dir) (?:has|contains) (.+?)(?:\?|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params['search_term'] = match.group(1).strip()
                break

        # If no specific pattern matched, use the whole query
        if 'search_term' not in params:
            params['search_term'] = query.strip('?').strip()

        logger.debug(f"Locate params: {params}")
        return params

    def _extract_changed_params(self, query: str) -> Dict[str, Any]:
        """Extract parameters for changed queries."""
        params = {}

        # Extract path if specified
        path_match = re.search(r'in ([/~][^\s?]+)', query, re.IGNORECASE)
        if path_match:
            params['path'] = path_match.group(1)

        # Extract time reference
        params['since'] = self._extract_time_reference(query)

        logger.debug(f"Changed params: {params}")
        return params

    def _extract_find_text_params(self, query: str) -> Dict[str, Any]:
        """Extract parameters for find_text queries."""
        params = {}

        # Extract search text - what to look for
        patterns = [
            r'(?:about|for|containing|with) (.+?)(?:\?|$| from| since)',
            r'find (?:ocr|text|screenshot) (.+?)(?:\?|$| from| since)',
            r'(?:showed|had|displayed) (.+?)(?:\?|$| from| since)',
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params['search_text'] = match.group(1).strip()
                break

        # If no specific pattern, use cleaned query
        if 'search_text' not in params:
            # Remove common prefixes
            clean_query = re.sub(r'^(find|search|show|get)\s+', '', query, flags=re.IGNORECASE)
            params['search_text'] = clean_query.strip('?').strip()

        # Extract time reference
        since = self._extract_time_reference(query)
        if since:
            params['since'] = since

        logger.debug(f"Find text params: {params}")
        return params

    def _extract_status_params(self, query: str) -> Dict[str, Any]:
        """Extract parameters for status queries."""
        params = {}

        # Determine resource type
        query_lower = query.lower()
        if 'mcp' in query_lower or 'server' in query_lower:
            params['resource_type'] = 'mcps'
        elif 'service' in query_lower:
            params['resource_type'] = 'services'
        elif 'container' in query_lower:
            params['resource_type'] = 'containers'
        else:
            # Default to containers
            params['resource_type'] = 'containers'

        logger.debug(f"Status params: {params}")
        return params

    def _extract_time_reference(self, query: str) -> Optional[datetime]:
        """
        Extract time reference from query.

        Supports:
        - Specific times: "since 10:00", "since 14:30"
        - Relative times: "today", "this morning", "yesterday", "last hour"
        - Time periods: "in the last 2 hours", "in the past day"

        Returns:
            datetime object or None if no time found
        """
        query_lower = query.lower()
        now = datetime.now()

        # Specific time (HH:MM format)
        time_match = re.search(r'since (\d{1,2}):(\d{2})', query_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Relative time periods
        if 'this morning' in query_lower or 'from morning' in query_lower:
            return now.replace(hour=6, minute=0, second=0, microsecond=0)

        if 'this afternoon' in query_lower or 'from afternoon' in query_lower:
            return now.replace(hour=12, minute=0, second=0, microsecond=0)

        if 'today' in query_lower:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        if 'yesterday' in query_lower:
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        if 'this week' in query_lower:
            # Start of week (Monday)
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Time periods (last N hours/days)
        period_match = re.search(r'(?:last|past) (\d+) (hour|day|minute)', query_lower)
        if period_match:
            count = int(period_match.group(1))
            unit = period_match.group(2)

            if unit == 'minute':
                return now - timedelta(minutes=count)
            elif unit == 'hour':
                return now - timedelta(hours=count)
            elif unit == 'day':
                return now - timedelta(days=count)

        # "in the last hour" pattern
        if 'last hour' in query_lower or 'past hour' in query_lower:
            return now - timedelta(hours=1)

        if 'last day' in query_lower or 'past day' in query_lower:
            return now - timedelta(days=1)

        # Default: None (no time constraint)
        return None


# Convenience function
def extract_parameters(query: str, intent: str) -> Dict[str, Any]:
    """Extract parameters from query."""
    extractor = ParameterExtractor()
    return extractor.extract(query, intent)
