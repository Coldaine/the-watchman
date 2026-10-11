# Project Brief: Librarian Agent

## Part 1: Requirements & Vision

### Executive Summary

The Librarian Pattern introduces a **centralized governance system for AI agents** working on your codebase. It acts as the sole authority for all documentation and code changes, preventing agents from making chaotic, uncoordinated modifications.

Without the Librarian, AI agents:
- Write documentation in arbitrary locations
- Make uncontrolled changes to code
- Lack consistent project context
- Create organizational chaos

With the Librarian:
- All agent interactions are mediated and controlled
- Documentation follows consistent standards
- Changes are tracked with immutable records
- Agents receive authoritative project context

### Core Concept

The Librarian is a **meta-agent governance system** that ensures AI implementation stays aligned with specifications and design documents through conversational validation. Unlike traditional approaches that rely on rigid tooling, the Librarian maintains project coherence through intelligent mediation.

The pattern's strength lies in its simplicity: one central authority whose job is to ensure all agents "ask permission" before making changes and "report back" afterward.

By combining:
- **Graph databases** for relationship tracking across all project artifacts
- **Vector search** for semantic understanding of code and documentation
- **Conversational validation** over rigid enforcement
- **Immutable record keeping** for all changes

The Librarian Pattern creates a controlled environment where AI agents can be productive while maintaining project coherence.

### Project Goals

This personal project aims to:
1. Build a centralized system that all AI agents must interact with for documentation
2. Create immutable records of all code and documentation changes
3. Provide consistent context to AI agents working on the codebase
4. Prevent agents from making unauthorized or chaotic modifications
5. Explore the boundaries of AI agent governance and coordination

## Part 2: Specification Documents

The detailed implementation of the Librarian Agent is specified in the following documents:

* [[LLM/KnowledgeAgents/Project_Library_Agent/Spec_System_Architecture]]
* [[LLM/KnowledgeAgents/Project_Library_Agent/Spec_Data_Model]]
* [[LLM/KnowledgeAgents/Project_Library_Agent/Spec_Agent_Orchestration]]
* [[LLM/KnowledgeAgents/Project_Library_Agent/Spec_Validation_and_Metrics]]
* [[LLM/KnowledgeAgents/Project_Library_Agent/Project_Context]]
* [[LLM/KnowledgeAgents/Project_Library_Agent/Research_Decisions]]
* [[research/neo4j_vs_falkordb_comparison]]

## Part 3: Implementation To-Dos

### MVP Phase (Personal Project Approach)
* [ ] Deploy Neo4j with vector index via Docker
* [ ] Choose and test local embedding model (see [[LLM/KnowledgeAgents/Project_Library_Agent/Research_Decisions]])
* [ ] Implement basic FastAPI service with `/ingest` and `/ask` endpoints
* [ ] Create minimal graph schema for `Doc`/`Chunk` nodes
* [ ] Build working end-to-end pipeline (ingest → query → answer)
* [ ] Test with personal codebase to validate usefulness

### Iterative Enhancement (As Time/Interest Allows)
* [ ] Improve chunking strategy based on real-world performance
* [ ] Add hybrid retrieval (vector + keyword) for better results
* [ ] Implement graph relationships between code entities
* [ ] Add simple web UI for easier interaction
* [ ] Enhance context assembly for more accurate answers

### Experimental Exploration (Learning Focus)
* [ ] Try different embedding models and compare results
* [ ] Experiment with graph-based retrieval enhancements
* [ ] Explore multi-document reasoning capabilities
* [ ] Test with different types of technical documentation