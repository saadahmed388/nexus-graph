"""
Pydantic models and typed data structures shared across the retrieval engine.

Nothing in here talks to Neo4j or LlamaIndex directly — this module only
defines shapes, so the rest of the engine has a single, stable contract to
program against.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

IntentLiteral = Literal[
    "METADATA", "ANALYSIS", "ROOT_CAUSE", "RESOLUTION", "COMMENTS",
    "CODE_CHANGES", "RELATED_TICKETS", "SEMANTIC_SEARCH",
    "EXACT_SEARCH", "AGGREGATION", "GENERAL",
]


class QueryIntentResult(BaseModel):
    """Upstream intent classification result. Treated as read-only input."""

    intent: IntentLiteral
    sub_intent: str
    required_evidence: list[str] = Field(default_factory=list)
    retrieval_strategy: list[str] = Field(default_factory=list)


class ResolvedEntity(BaseModel):
    """An entity-resolution hit that can anchor graph retrieval."""

    mention: str
    canonical_name: Optional[str] = None
    label: Optional[str] = None        # Neo4j node label, e.g. "person"
    element_id: Optional[str] = None   # Neo4j elementId, used as a graph anchor
    confidence: Optional[float] = None


class RetrievalSource(str, Enum):
    LEXICAL = "lexical"
    VECTOR = "vector"
    GRAPH = "graph"


class RetrievalPlan(BaseModel):
    """
    Concrete, modality-specific retrieval instructions derived from the
    intent result and the user query. This is a plan only — nothing is
    executed while it's being built.
    """

    original_query: str
    intent: IntentLiteral
    sub_intent: str
    required_evidence: list[str] = Field(default_factory=list)

    lexical_indexes: list[str] = Field(default_factory=list)
    lexical_terms: list[str] = Field(default_factory=list)

    vector_indexes: list[str] = Field(default_factory=list)
    vector_query_texts: list[str] = Field(default_factory=list)

    graph_anchors: list[ResolvedEntity] = Field(default_factory=list)
    graph_operations: list[str] = Field(default_factory=list)
    aggregation_requested: bool = False

    modality_priority: list[RetrievalSource] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    """
    Common normalized representation of a retrieval hit, regardless of which
    modality produced it. Embeddings and other heavy payloads are
    intentionally excluded so this stays cheap to pass around and rerank.
    """

    model_config = ConfigDict(use_enum_values=True)

    element_id: str
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

    sources: list[RetrievalSource] = Field(default_factory=list)
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    graph_score: Optional[float] = None

    matched_query: Optional[str] = None   # query text that produced this hit
    relationship: Optional[str] = None    # graph relationship/tool that produced this hit
    entity_match: bool = False            # corresponds to a resolved entity anchor

    final_score: Optional[float] = None   # populated by rerank_candidates


class ModalityOutcome(BaseModel):
    """Per-modality execution status, used for partial-failure reporting."""

    model_config = ConfigDict(use_enum_values=True)

    source: RetrievalSource
    ok: bool
    candidate_count: int = 0
    error: Optional[str] = None


class EvidenceCoverage(BaseModel):
    complete: bool
    satisfied: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Final structured output handed to the synthesis LLM."""

    status: Literal["success", "partial", "failed"]
    query: str
    intent: dict[str, Any]
    retrieval_summary: dict[str, Any]
    resolved_entities: list[ResolvedEntity] = Field(default_factory=list)
    evidence: list[Candidate] = Field(default_factory=list)
    modality_outcomes: list[ModalityOutcome] = Field(default_factory=list)
    coverage: EvidenceCoverage
    aggregation_result: Optional[dict[str, Any]] = None
