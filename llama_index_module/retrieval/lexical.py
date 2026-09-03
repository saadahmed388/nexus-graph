"""
Lexical retrieval branch: queries Neo4j full-text indexes directly.
Precise literal matching — names, keys, identifiers, exact phrases.
"""
from __future__ import annotations

import asyncio
import logging

from .config import FULLTEXT_INDEX_BY_LABEL
from .models import Candidate, ModalityOutcome, RetrievalPlan, RetrievalSource

logger = logging.getLogger(__name__)

# Fields stripped from returned node properties before they travel further
# down the pipeline — heavy or irrelevant payloads.
_STRIP_PROPERTY_KEYS = {"embedding", "vector", "raw_text_blob"}

_LEXICAL_QUERY = (
    "CALL db.index.fulltext.queryNodes($index_name, $query_text) "
    "YIELD node, score "
    "RETURN elementId(node) AS element_id, labels(node) AS labels, "
    "       properties(node) AS properties, score AS score "
    "ORDER BY score DESC "
    "LIMIT $limit"
)


def _clean_properties(props: dict) -> dict:
    return {k: v for k, v in (props or {}).items() if k not in _STRIP_PROPERTY_KEYS}


async def _query_one_index(driver, index_name: str, query_text: str, limit: int) -> list[Candidate]:
    """Run a single Lucene full-text query against one index."""
    candidates: list[Candidate] = []
    async with driver.session() as session:
        result = await session.run(
            _LEXICAL_QUERY, index_name=index_name, query_text=query_text, limit=limit
        )
        async for record in result:
            candidates.append(
                Candidate(
                    element_id=record["element_id"],
                    labels=record["labels"] or [],
                    properties=_clean_properties(record["properties"]),
                    sources=[RetrievalSource.LEXICAL],
                    lexical_score=float(record["score"]),
                    matched_query=query_text,
                )
            )
    return candidates


async def run_lexical_retrieval(
    driver,
    plan: RetrievalPlan,
    per_index_limit: int = 15,
) -> tuple[list[Candidate], ModalityOutcome]:
    """
    Execute the plan's lexical branch across every selected full-text index
    and every generated lexical term, concurrently. A failure on one
    index/term query does not abort the others.
    """
    if not plan.lexical_indexes or not plan.lexical_terms:
        return [], ModalityOutcome(source=RetrievalSource.LEXICAL, ok=True, candidate_count=0)

    tasks = [
        _query_one_index(driver, index_name, term, per_index_limit)
        for index_name in plan.lexical_indexes
        for term in plan.lexical_terms
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    candidates: list[Candidate] = []
    errors: list[str] = []
    for res in results:
        if isinstance(res, Exception):
            errors.append(str(res))
            logger.warning("Lexical sub-query failed: %s", res)
            continue
        candidates.extend(res)

    ok = (len(errors) < len(results)) if results else True
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
