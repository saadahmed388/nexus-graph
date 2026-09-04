# Nexus Graph — Design Document

## 1. Executive Summary

Nexus Graph is an agentic retrieval system built for JIRA incident intelligence. Its architecture treats enterprise retrieval as an evidence-acquisition problem rather than a simple nearest-neighbor search.

The system combines:
- semantic retrieval for conceptual similarity,
- lexical retrieval for exact terms,
- graph retrieval for relationships and multi-hop context,
- dynamic Cypher for open-ended graph questions,
- evidence coverage checks for retrieval reliability.

## 2. Core Design Principle

The central principle is:

> Use the simplest retrieval capability that can satisfy the evidence requirement, and escalate to graph reasoning or dynamic Cypher when deeper structure is required.

This prevents the system from overusing expensive or unnecessarily complex graph queries.

## 3. Logical Components

```text
User
 ↓
Intent / Requirement
 ↓
Agent / Retrieval Planner
 ├───────────────┬─────────────────┐
 ↓               ↓                 ↓
Hybrid        Graph Tools      Dynamic Cypher
 ↓               ↓                 ↓
Vector +      Relationships      Neo4j
Lexical       + Traversal
 └───────────────┬─────────────────┘
                 ↓
          Candidate Processing
       Normalize → Fuse → Rerank
                 ↓
          Evidence Coverage
                 ↓
          Evidence Selection
                 ↓
          Grounded Context
```

## 4. Retrieval Modalities

### Vector
Captures semantic similarity and handles paraphrased incident descriptions.

### Lexical
Captures exact tokens such as issue keys, error signatures and names.

### Graph
Captures relationships and network structure.

### Dynamic Cypher
Acts as a general-purpose read-only graph retrieval escape hatch.

## 5. Retrieval Pipeline

```text
Query + Intent
      ↓
Build Retrieval Plan
      ↓
Run Vector / Lexical / Graph retrieval concurrently
      ↓
Normalize candidates
      ↓
Fuse and deduplicate
      ↓
Rerank
      ↓
Check Evidence Coverage
      ↓
(Optional) one bounded follow-up round
      ↓
Select top evidence
```

This pipeline is present in the repository's retrieval engine.

## 6. Hybrid Retrieval Design

The vector and lexical paths are represented as independent retrievers. Multiple relevant indexes can participate in a single retrieval operation.

```text
                  Query
                    │
        ┌───────────┴───────────┐
        │                       │
   Vector retrievers       Lexical retrievers
        │                       │
        └───────────┬───────────┘
                    ↓
           Reciprocal Rank Fusion
                    ↓
              Candidate Set
                    ↓
                 Rerank
```

This is preferable to a single blended index because the application can target more specific entity types and fields.

## 7. Agent Tool Architecture

The agent receives specialized tools rather than a single opaque retrieval function.

```text
FunctionAgent
 ├── Hybrid Retrieval
 ├── Relationship Discovery
 ├── Network Traversal
 ├── Node Details
 ├── Connected Content
 └── Dynamic Cypher
```

This creates a clear division of responsibility and makes tool selection part of the agent's reasoning.

## 8. Dynamic Cypher

Dynamic Cypher solves the limitation of fixed retrieval APIs.

```text
Requirement
    ↓
Identify needed entities / relationships / conditions
    ↓
Generate read-only Cypher
    ↓
Execute
    ↓
Return evidence
```

A structured query representation makes the boundary explicit:

```text
CypherModel
├── cypher
└── parameters
```

The intended security boundary is read-only execution.

## 9. Why Graph + RAG?

Pure RAG asks:

> Which documents are similar?

GraphRAG can additionally ask:

> Which entities are related, how are they connected, and what evidence is reachable through those relationships?

This matters for incident questions involving systems, environments, investigations, comments, code changes, and linked tickets.

## 10. Evidence Coverage

The design deliberately separates **relevance** from **sufficiency**.

A result can be highly relevant but still fail to answer the question.

Therefore:

```text
Ranking
  ≠
Evidence Sufficiency
```

The coverage stage checks whether the retrieved evidence satisfies the information requested. If not, a bounded follow-up retrieval pass can target missing evidence.

## 11. Concurrency

Independent retrieval modalities should not block one another.

```python
await asyncio.gather(
    vector_retrieval(),
    lexical_retrieval(),
    graph_retrieval()
)
```

This design reduces latency from serial execution and aligns naturally with independent Neo4j retrieval operations.

## 12. Data Representation

Each graph entity can support both:

```text
Graph representation
    +
Vector representation
```

For example, a ticket can participate in graph relationships while also being indexed semantically.

This dual representation is the foundation of the system.

## 13. Safety Model

Recommended production architecture:

```text
Agent
  ↓
Tool Registry
  ↓
Read-only validation layer
  ↓
Read-only Neo4j credentials
  ↓
Bounded query execution
```

The agent should never be given database write privileges.

## 14. Key Trade-offs

### Complexity vs. retrieval power
Hybrid + graph retrieval is more complex than simple vector RAG, but it handles substantially richer incident questions.

### Dynamic query flexibility vs. safety
Dynamic Cypher is powerful, but it must be constrained and observed.

### Multiple indexes vs. maintenance
Separate vector/full-text indexes improve targeted retrieval at the cost of additional index lifecycle management.

### Follow-up retrieval vs. latency
A bounded follow-up improves completeness while avoiding open-ended retrieval loops.

## 15. Evaluation Strategy

A serious production evaluation should measure:

```text
Recall@K
Precision@K
MRR / NDCG
Evidence Coverage
Tool Selection Accuracy
Dynamic Cypher Success Rate
Retrieval Latency
Follow-up Retrieval Rate
Grounded Answer Rate
```

Evaluation should be conducted on a representative benchmark of incident questions with known supporting evidence.

## 16. Recommended Production Evolution

```text
Current prototype
      ↓
Benchmark dataset
      ↓
Automated retrieval evaluation
      ↓
Tracing / telemetry
      ↓
Cypher validation + sandbox
      ↓
Permission-aware graph access
      ↓
Load / latency testing
      ↓
Production deployment
```

## 17. Design Summary

Nexus Graph is best viewed as:

```text
LLM reasoning
    +
specialized tools
    +
hybrid retrieval
    +
knowledge graph
    +
dynamic Cypher
    +
evidence coverage
    =
agentic GraphRAG
```

The important engineering distinction is that the LLM is not expected to “know” the answer. It is responsible for deciding **what evidence must be acquired and which retrieval capability can acquire it**, while Neo4j and the retrieval layer provide the actual evidence.
