"""
Vector retrieval branch: queries Neo4j vector indexes directly using query
embeddings. Semantic discovery — conceptual, similarity-based matches that
lexical search would miss.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from .config import SEMANTIC_FALLBACK_INDEX, VECTOR_INDEX_BY_LABEL
from .models import Candidate, ModalityOutcome, RetrievalPlan, RetrievalSource

logger = logging.getLogger(__name__)

EmbedFn = Callable[[str], Awaitable[list[float]]]

_STRIP_PROPERTY_KEYS = {"embedding", "vector", "raw_text_blob"}

_VECTOR_QUERY = (
    "CALL db.index.vector.queryNodes($index_name, $top_k, $embedding) "
    "YIELD node, score "
    "RETURN elementId(node) AS element_id, labels(node) AS labels, "
    "       properties(node) AS properties, score AS score"
)


def _clean_properties(props: dict) -> dict:
    return {k: v for k, v in (props or {}).items() if k not in _STRIP_PROPERTY_KEYS}


async def _query_one_index(
    driver, index_name: str, embedding: list[float], query_text: str, top_k: int
) -> list[Candidate]:
    candidates: list[Candidate] = []
    async with driver.session() as session:
        result = await session.run(
            _VECTOR_QUERY, index_name=index_name, top_k=top_k, embedding=embedding
        )
        async for record in result:
            candidates.append(
                Candidate(
                    element_id=record["element_id"],
                    labels=record["labels"] or [],
                    properties=_clean_properties(record["properties"]),
                    sources=[RetrievalSource.VECTOR],
                    vector_score=float(record["score"]),
                    matched_query=query_text,
                )
            )
    return candidates


async def run_vector_retrieval(
    driver,
    embed_fn: EmbedFn,
    plan: RetrievalPlan,
    top_k: int = 15,
) -> tuple[list[Candidate], ModalityOutcome]:
    """
    Embed each planned query text once, then fan the search out concurrently
    across every selected vector index (specific indexes, plus the semantic
    fallback when nothing more specific was determined). An embedding
    failure for one query text doesn't block the others.
    """
    if not plan.vector_query_texts:
        return [], ModalityOutcome(source=RetrievalSource.VECTOR, ok=True, candidate_count=0)

    indexes = plan.vector_indexes or [SEMANTIC_FALLBACK_INDEX]

    embed_tasks = [embed_fn(text) for text in plan.vector_query_texts]
    embeddings = await asyncio.gather(*embed_tasks, return_exceptions=True)

    query_tasks = []
    task_meta = []
    for query_text, embedding in zip(plan.vector_query_texts, embeddings):
        if isinstance(embedding, Exception):
            logger.warning("Embedding failed for %r: %s", query_text, embedding)
            continue
        for index_name in indexes:
            query_tasks.append(_query_one_index(driver, index_name, embedding, query_text, top_k))
            task_meta.append(index_name)

    if not query_tasks:
        return [], ModalityOutcome(
            source=RetrievalSource.VECTOR, ok=False, candidate_count=0,
            error="all query embeddings failed",
        )

    results = await asyncio.gather(*query_tasks, return_exceptions=True)

    candidates: list[Candidate] = []
    errors: list[str] = []
    for res, index_name in zip(results, task_meta):
        if isinstance(res, Exception):
            errors.append(f"{index_name}: {res}")
            logger.warning("Vector sub-query on %s failed: %s", index_name, res)
            continue
        candidates.extend(res)

    ok = len(errors) < len(results)
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
    determined. This fallback is what keeps vector search able to discover
    candidates the intent layer didn't explicitly anticipate.
    """
    indexes = []
    for label in labels:
        idx = VECTOR_INDEX_BY_LABEL.get(label)
        if idx and idx not in indexes:
            indexes.append(idx)
    if not indexes:
        indexes.append(SEMANTIC_FALLBACK_INDEX)
    return indexes
