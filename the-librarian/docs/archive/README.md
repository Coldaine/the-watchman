# Archive: Research & Early Planning Documents

This directory contains **historical research and planning documents** that were used during the exploration and decision-making phase of the Librarian Agent project.

## Status: **Archived for Reference Only**

These documents are **no longer authoritative** and contain conflicting information, unresolved decisions, and exploratory research. They are preserved for historical context and to understand the evolution of the project's thinking.

## ⚠️ Important Notice

**DO NOT use these documents for implementation.**

The official, conflict-resolved architecture is located at:
- **[`docs/architecture.md`](../architecture.md)** - Single source of truth for implementation

All decisions, rationale, and conflict resolutions are documented in:
- **[`docs/ADR/`](../ADR/)** - Architecture Decision Records

## Contents Overview

### Planning Documents
- `Project_Brief_-_Librarian_Agent.md` - Original project vision
- `Project_Context.md` - Project scope and constraints
- `Project_Milestones.md` - Early milestone planning
- `Project - Library Agent.md` - Phase descriptions

### Technical Specifications (Superseded)
- `Spec_System_Architecture.md` - Early architecture thinking
- `Spec_Data_Model.md` - Initial graph schema ideas
- `Spec_Agent_Orchestration.md` - Agent interaction concepts
- `Spec_Validation_and_Metrics.md` - Validation query explorations

### Implementation Plans (Superseded)
- `Librarian_Pattern_Implementation_Plan.md` - Comprehensive but conflicting plan
- `Research_Decisions.md` - List of pending technical decisions

### Research Documents
- `neo4j_vs_falkordb_comparison.md` - Database technology comparison
- `RAG PLANS 090 06 25.md` - Alternative RAG implementation approaches
- `Temporal Knowledge Graphs and Agentic Invalidation.md` - Advanced concepts research

## Known Issues in These Documents

These documents contain several **unresolved conflicts**:

1. **Language Choice**: Some docs assume Python, others recommend Node.js
2. **Database Choice**: Neo4j vs FalkorDB recommendations conflict
3. **Project Scope**: Three different visions (Agent Governance, Document RAG, System Admin KG)
4. **Timeline**: Conflicting estimates from "hours" to "weeks"
5. **Technology Stack**: Multiple incompatible technology recommendations

All of these conflicts have been **resolved** in the official architecture document and ADR.

## Historical Value

These documents are valuable for:
- Understanding the research process
- Seeing what alternatives were considered
- Learning why certain decisions were made
- Tracking the evolution of project thinking

## Migration Notes

**From Research → Official Architecture:**
- ✅ Conflicts identified and resolved
- ✅ Technology stack finalized
- ✅ Clear implementation path defined
- ✅ Decision rationale documented in ADR
- ✅ Timeline made realistic for personal project

## Questions?

If you need to understand **why** certain decisions were made, consult:
1. **[ADR Index](../ADR/)** - For decision rationale
2. **[Architecture Doc](../architecture.md)** - For current implementation spec

---

**Last Updated**: 2024-11-10
**Status**: Archived
**Superseded By**: docs/architecture.md v2.0.0
