"""
Lexical retrieval branch: calls the existing `full_text_keyword_tool`
(which itself queries Neo4j full-text indexes) — precise literal matching
for names, keys, identifiers, and exact phrases. No direct Neo4j access
lives here; the tool already encapsulates that.
"""
from __future__ import annotations

import asyncio
import logging

from .config import FULLTEXT_INDEX_BY_LABEL
from .models import Candidate, ModalityOutcome, RetrievalPlan, RetrievalSource
from .tools import ToolRegistry, candidates_from_index_search_output

logger = logging.getLogger(__name__)


async def run_lexical_retrieval(
    registry: ToolRegistry,
    plan: RetrievalPlan,
) -> tuple[list[Candidate], ModalityOutcome]:
    """
    Call `full_text_keyword_tool(keyword, index_name)` for every selected
    index x term combination, concurrently. A failure on one combination
    does not abort the others.
    """
    if not plan.lexical_indexes or not plan.lexical_terms:
        return [], ModalityOutcome(source=RetrievalSource.LEXICAL, ok=True, candidate_count=0)

    combos = [
        (index_name, term)
        for index_name in plan.lexical_indexes
        for term in plan.lexical_terms
    ]
    results = await asyncio.gather(*[
        registry.call_safe("full_text_keyword_tool", keyword=term, index_name=index_name)
        for index_name, term in combos
    ])

    candidates: list[Candidate] = []
    errors: list[str] = []
    for (index_name, term), (ok, parsed) in zip(combos, results):
        if not ok:
            errors.append(f"{index_name}/{term}: {parsed}")
            logger.warning("full_text_keyword_tool failed for %s/%r: %s", index_name, term, parsed)
            continue
        for hit in candidates_from_index_search_output(parsed, matched_query=term):
            candidates.append(
                Candidate(
                    element_id=hit["element_id"],
                    labels=hit["labels"],
                    properties=hit["properties"],
                    sources=[RetrievalSource.LEXICAL],
                    lexical_score=float(hit["score"]) if hit["score"] is not None else None,
                    matched_query=hit["matched_query"],
                )
            )

    ok = len(errors) < len(results) if results else True
    outcome = ModalityOutcome(
        source=RetrievalSource.LEXICAL,
        ok=ok,
        candidate_count=len(candidates),
        error="; ".join(errors) if errors else None,
    )
    return candidates, outcome


def select_fulltext_indexes(labels: list[str]) -> list[str]:
    """Map a set of target node labels onto their full-text index names."""
    indexes = []
    for label in labels:
        idx = FULLTEXT_INDEX_BY_LABEL.get(label)
        if idx and idx not in indexes:
            indexes.append(idx)
    return indexes
