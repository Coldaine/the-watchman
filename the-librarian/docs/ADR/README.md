# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) that document significant architectural and technical decisions made for the Librarian Agent project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences. ADRs help us:

- **Remember why** we made certain decisions
- **Understand context** that influenced those decisions
- **Track evolution** of the architecture over time
- **Onboard new contributors** by explaining design rationale
- **Avoid revisiting** already-decided questions

## ADR Format

Each ADR follows this structure:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: What is the issue we're addressing?
- **Decision**: What is the change we're making?
- **Consequences**: What becomes easier or harder as a result?
- **Alternatives Considered**: What other options were evaluated?

## Index of ADRs

### Active ADRs

| Number | Title | Status | Date | Summary |
|--------|-------|--------|------|---------|
| [001](./001-technology-stack-and-architecture-decisions.md) | Technology Stack and Architecture Decisions | Accepted | 2024-11-10 | Establishes Python + Neo4j + FastAPI stack and resolves all specification conflicts |

### Superseded ADRs

*None yet*

### Deprecated ADRs

*None yet*

## When to Create an ADR

Create a new ADR when:
- Making a significant technology choice (language, database, framework)
- Changing a major architectural pattern
- Resolving conflicts between competing approaches
- Making a decision with long-term consequences
- Choosing between multiple viable alternatives

**Do NOT** create ADRs for:
- Minor implementation details
- Obvious or trivial choices
- Temporary workarounds
- Decisions that can be easily reversed

## How to Create an ADR

1. Copy the template: `cp template.md 00X-your-decision-title.md`
2. Fill in all sections with clear, concise information
3. Number sequentially (next available number)
4. Update this README index with the new ADR
5. Get review from stakeholders if applicable
6. Commit once status is "Accepted"

## ADR Lifecycle

```
┌──────────┐
│ Proposed │ ← Draft ADR, under discussion
└────┬─────┘
     │
     ↓
┌──────────┐
│ Accepted │ ← Decision made, currently active
└────┬─────┘
     │
     ↓
┌────────────┐        ┌────────────┐
│ Superseded │   OR   │ Deprecated │
└────────────┘        └────────────┘
     ↑                      ↑
     └── New ADR replaces  └── No longer valid
```

## Related Documentation

- **[Architecture Document](../architecture.md)**: Official implementation specification
- **[Archive](../archive/)**: Historical research documents (superseded)

## Questions?

If you have questions about a decision:
1. Check if an ADR exists for that decision
2. Read the "Context" and "Consequences" sections
3. Look at "Alternatives Considered" to understand tradeoffs
4. If still unclear, ask the project owner or create an issue

---

**Last Updated**: 2024-11-10
**Total ADRs**: 1 Active, 0 Superseded, 0 Deprecated
