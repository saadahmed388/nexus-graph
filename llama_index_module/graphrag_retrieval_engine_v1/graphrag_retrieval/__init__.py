"""
Hybrid GraphRAG retrieval engine for a LlamaIndex + Neo4j incident graph.

Public entry point: `retrieve()`. Everything else is exported for testing,
custom orchestration, or reuse of individual pipeline stages.
"""

from .models import (
    Candidate,
    EvidenceCoverage,
    ModalityOutcome,
    QueryIntentResult,
    ResolvedEntity,
    RetrievalPlan,
    RetrievalResult,
    RetrievalSource,
)
from .tools import ToolRegistry
from .engine import build_retrieval_plan, retrieve
from .lexical import run_lexical_retrieval, select_fulltext_indexes
from .vector import run_vector_retrieval, select_vector_indexes
from .graph import run_graph_retrieval
from .fusion import (
    fuse_candidates,
    mark_entity_matches,
    normalize_candidates,
    rerank_candidates,
)
from .coverage import check_evidence_coverage, select_evidence

__all__ = [
    "Candidate",
    "EvidenceCoverage",
    "ModalityOutcome",
    "QueryIntentResult",
    "ResolvedEntity",
    "RetrievalPlan",
    "RetrievalResult",
    "RetrievalSource",
    "ToolRegistry",
    "build_retrieval_plan",
    "retrieve",
    "run_lexical_retrieval",
    "select_fulltext_indexes",
    "run_vector_retrieval",
    "select_vector_indexes",
    "run_graph_retrieval",
    "normalize_candidates",
    "fuse_candidates",
    "mark_entity_matches",
    "rerank_candidates",
    "check_evidence_coverage",
    "select_evidence",
]
