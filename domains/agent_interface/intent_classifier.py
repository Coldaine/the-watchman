#!/usr/bin/env python3
"""
Intent Classifier for Agent Interface.

Classifies user query intent to route to appropriate query type:
- locate: Find files, projects, services
- changed: Recent changes and events
- find_text: Vector search over OCR/docs
- status: MCP/container/service status
"""

import re
from typing import Tuple
from loguru import logger


class IntentClassifier:
    """Classify user query intent using pattern matching."""

    # Intent patterns (keyword → regex patterns)
    INTENT_PATTERNS = {
        'locate': [
            r'where is',
            r'where\'s',
            r'find (the |my )?path',
            r'locate',
            r'which (file|directory|folder|dir)',
            r'show me (the )?path',
            r'path (to|for|of)',
        ],
        'changed': [
            r'what changed',
            r'what\'s changed',
            r'recent changes',
            r'modified .* (in|since|at)',
            r'updates? (in|to|since)',
            r'changed (in|since)',
            r'edits? (in|to|since)',
        ],
        'find_text': [
            r'find (ocr|text|screenshot)',
            r'saw (on|about)',
            r'screen (showed|had|displayed)',
            r'search (for|ocr)',
            r'looked at',
            r'was looking at',
        ],
        'status': [
            r'(which|what) .* (running|up|down)',
            r'status of',
            r'list .* (containers|mcps|mcp|services)',
            r'show .* (containers|services|mcps)',
            r'(are|is) .* (running|up|down|active)',
            r'list (containers|services|mcps?)',
        ]
    }

    def classify(self, query: str) -> Tuple[str, float]:
        """
        Classify query intent using pattern matching.

        Args:
            query: User query string

        Returns:
            Tuple of (intent, confidence)
                - intent: 'locate', 'changed', 'find_text', 'status', or 'unknown'
                - confidence: Float between 0.0 and 1.0
        """
        query_lower = query.lower()
        scores = {}

        # Score each intent based on pattern matches
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1

            if score > 0:
                scores[intent] = score

        if not scores:
            logger.warning(f"No intent match for query: {query}")
            return 'unknown', 0.0

        # Get best scoring intent
        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        # Calculate confidence (normalize by number of patterns for that intent)
        pattern_count = len(self.INTENT_PATTERNS[best_intent])
        confidence = min(max_score / pattern_count, 1.0)

        logger.info(f"Classified intent: {best_intent} (confidence: {confidence:.2f})")

        return best_intent, confidence

    def get_intent_patterns(self) -> dict:
        """Get all intent patterns (for testing/debugging)."""
        return self.INTENT_PATTERNS


# Convenience function for single imports
def classify_intent(query: str) -> Tuple[str, float]:
    """Classify query intent."""
    classifier = IntentClassifier()
    return classifier.classify(query)
