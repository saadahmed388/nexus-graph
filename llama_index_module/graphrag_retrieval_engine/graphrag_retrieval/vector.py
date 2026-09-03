"""
Vector retrieval branch: calls the existing `vector_search_tool` (which
embeds the query itself via `embedding_model.get_query_embedding` and
queries Neo4j vector indexes) — semantic discovery for conceptual,
similarity-based matches lexical search would miss. No separate embedder
or Neo4j driver is needed here; the tool owns both.
"""
from __future__ import annotations

import asyncio
import logging

from .config import SEMANTIC_FALLBACK_INDEX, VECTOR_INDEX_BY_LABEL
from .models import Candidate, ModalityOutcome, RetrievalPlan, RetrievalSource
from .tools import ToolRegistry, candidates_from_index_search_output

logger = logging.getLogger(__name__)


async def run_vector_retrieval(
    registry: ToolRegistry,
    plan: RetrievalPlan,
) -> tuple[list[Candidate], ModalityOutcome]:
    """
    Call `vector_search_tool(query_text, index_name)` for every selected
    index x query-text combination, concurrently. Indexes default to the
    semantic fallback when nothing more specific was determined, which is
    what keeps vector search able to discover candidates the intent layer
    didn't explicitly anticipate.
    """
    if not plan.vector_query_texts:
        return [], ModalityOutcome(source=RetrievalSource.VECTOR, ok=True, candidate_count=0)

    indexes = plan.vector_indexes or [SEMANTIC_FALLBACK_INDEX]
    combos = [
        (index_name, text)
        for text in plan.vector_query_texts
        for index_name in indexes
    ]
    results = await asyncio.gather(*[
        registry.call_safe("vector_search_tool", query_text=text, index_name=index_name)
        for index_name, text in combos
    ])

    candidates: list[Candidate] = []
    errors: list[str] = []
    for (index_name, text), (ok, parsed) in zip(combos, results):
        if not ok:
            errors.append(f"{index_name}: {parsed}")
            logger.warning("vector_search_tool failed for %s (%r): %s", index_name, text, parsed)
            continue
        for hit in candidates_from_index_search_output(parsed, matched_query=text):
            candidates.append(
                Candidate(
                    element_id=hit["element_id"],
                    labels=hit["labels"],
                    properties=hit["properties"],
                    sources=[RetrievalSource.VECTOR],
                    vector_score=float(hit["score"]) if hit["score"] is not None else None,
                    matched_query=hit["matched_query"],
                )
            )

    ok = len(errors) < len(results) if results else True
    outcome = ModalityOutcome(
        source=RetrievalSource.VECTOR,
        ok=ok,
        candidate_count=len(candidates),
        error="; ".join(errors) if errors else None,
    )
    return candidates, outcome


def select_vector_indexes(labels: list[str]) -> list[str]:
    """
    Map target node labels onto their specific vector indexes, falling back
    to the broad semantic_search_index when no specific label was
    determined.
    """
    indexes = []
    for label in labels:
        idx = VECTOR_INDEX_BY_LABEL.get(label)
        if idx and idx not in indexes:
            indexes.append(idx)
    if not indexes:
        indexes.append(SEMANTIC_FALLBACK_INDEX)
    return indexes
