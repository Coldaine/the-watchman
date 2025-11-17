#!/usr/bin/env python3
"""
Demo script showing the Agent Interface query pipeline.

Demonstrates the full flow:
1. User asks a natural language question
2. Intent is classified
3. Parameters are extracted
4. Cypher query is built
5. (In production: query executes, LLM generates answer)
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.agent_interface.intent_classifier import IntentClassifier
from domains.agent_interface.parameter_extractor import ParameterExtractor
from domains.agent_interface.query_builder import QueryBuilder


def demo_query(query_text: str):
    """Process a single query through the pipeline."""
    print(f"\n{'='*70}")
    print(f"Query: {query_text}")
    print(f"{'='*70}\n")

    # Initialize components
    classifier = IntentClassifier()
    extractor = ParameterExtractor()
    builder = QueryBuilder()

    # Step 1: Classify intent
    intent, confidence = classifier.classify(query_text)
    print(f"📋 Intent: {intent} (confidence: {confidence:.2f})")

    # Step 2: Extract parameters
    params = extractor.extract(query_text, intent)
    print(f"🔍 Parameters:")
    for key, value in params.items():
        print(f"   - {key}: {value}")

    # Step 3: Build Cypher query
    cypher, cypher_params = builder.build(intent, params)
    print(f"\n💾 Cypher Query:")
    print(f"{cypher[:300]}..." if len(cypher) > 300 else cypher)
    print(f"\n🎯 Query Parameters:")
    for key, value in cypher_params.items():
        print(f"   - {key}: {value}")

    print(f"\n✅ Ready to execute against Neo4j!\n")


def main():
    """Run demo queries."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          TheWatchman Agent Interface - Query Pipeline Demo       ║
║                                                                  ║
║  Demonstrating: Intent Classification → Parameter Extraction    ║
║                 → Cypher Query Building                          ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # Example queries
    queries = [
        "Where is my docker-compose.yml?",
        "What changed in /etc since 10:00?",
        "Find OCR text about TLS certificates from this morning",
        "Which MCP servers are running?",
        "List containers",
        "What changed in /var/log in the last 3 hours?",
    ]

    for query in queries:
        demo_query(query)

    print("""
╔══════════════════════════════════════════════════════════════════╗
║  Next Steps:                                                     ║
║  1. LLM Integration - Generate natural language answers          ║
║  2. Response Formatter - Structure results with sources          ║
║  3. Main /ask endpoint - Complete API integration                ║
╚══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
