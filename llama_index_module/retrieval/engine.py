"""
Retrieval planning and the main orchestrator.

Pipeline:

    user query + intent
            |
    build_retrieval_plan
            |
      lexical | vector | graph   (asyncio.gather — concurrent)
            |
    normalize_candidates
            |
    fuse_candidates (dedup by elementId)
            |
    rerank_candidates
            |
    check_evidence_coverage --(missing)--> one bounded follow-up round
            |
    select_evidence (top-K)
            |
    RetrievalResult
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from .config import (
    DEFAULT_TOP_K,
    MAX_ADDITIONAL_RETRIEVAL_ROUNDS,
    labels_from_required_evidence,
)
from .coverage import check_evidence_coverage, select_evidence
from .fusion import fuse_candidates, mark_entity_matches, normalize_candidates, rerank_candidates
from .graph import run_graph_retrieval
from .lexical import run_lexical_retrieval, select_fulltext_indexes
from .models import (
    Candidate,
    ModalityOutcome,
    QueryIntentResult,
    ResolvedEntity,
    RetrievalPlan,
    RetrievalResult,
    RetrievalSource,
)
from .tools import ToolRegistry
from .vector import EmbedFn, run_vector_retrieval, select_vector_indexes

try:
    from .config import INTENT_PROFILES
except ImportError:  # pragma: no cover - defensive, config always defines this
    INTENT_PROFILES = {}

logger = logging.getLogger(__name__)

_JIRA_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b")


# --------------------------------------------------------------------------
# Query decomposition helpers
# --------------------------------------------------------------------------

def _merge_unique(*label_lists: list[str]) -> list[str]:
    merged: list[str] = []
    for labels in label_lists:
        for label in labels:
            if label not in merged:
                merged.append(label)
    return merged


def _build_lexical_terms(user_query: str, resolved_entities: list[ResolvedEntity]) -> list[str]:
    """
    Extract literal search terms: resolved entity names, Jira-key-like
    tokens, quoted phrases, and capitalized proper-noun runs. Falls back to
    the raw query so lexical search always has something to work with.
    """
    terms: list[str] = []

    for entity in resolved_entities:
        terms.append(entity.canonical_name or entity.mention)

    terms.extend(_JIRA_KEY_RE.findall(user_query))

    for match in _QUOTED_RE.finditer(user_query):
        phrase = match.group(1) or match.group(2)
        if phrase:
            terms.append(phrase)

    for match in _PROPER_NOUN_RE.finditer(user_query):
        phrase = match.group(1)
        if len(phrase) > 2:
            terms.append(phrase)

    if not terms:
        terms.append(user_query)

    seen = set()
    unique_terms = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique_terms.append(term)
    return unique_terms


def _build_vector_query_texts(user_query: str, intent_result: QueryIntentResult) -> list[str]:
    """
    Preserve the original query as the primary semantic probe, and add a
    sub-intent-qualified variant when the sub_intent adds context the raw
    query doesn't already contain (helps disambiguate vague queries).
    """
    texts = [user_query]
    if intent_result.sub_intent and intent_result.sub_intent.lower() not in user_query.lower():
        texts.append(f"{user_query} ({intent_result.sub_intent})")
    return texts


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------

def build_retrieval_plan(
    user_query: str,
    intent_result: QueryIntentResult,
    resolved_entities: Optional[list[ResolvedEntity]] = None,
) -> RetrievalPlan:
    """
    Turn a user query + QueryIntentResult (+ optional entity resolution)
    into concrete, modality-specific retrieval instructions. The intent
    profile *prioritizes* labels/operations — it never excludes vector or
    lexical discovery outright, per the "don't over-constrain semantic
    discovery" requirement.
    """
    resolved_entities = resolved_entities or []
    profile = INTENT_PROFILES.get(intent_result.intent, INTENT_PROFILES["GENERAL"])

    evidence_labels = labels_from_required_evidence(intent_result.required_evidence)
    lexical_labels = _merge_unique(profile["lexical_labels"], evidence_labels)
    vector_labels = _merge_unique(profile["vector_labels"], evidence_labels)

    lexical_terms = _build_lexical_terms(user_query, resolved_entities)
    lexical_indexes = select_fulltext_indexes(lexical_labels) if lexical_terms else []

    vector_query_texts = _build_vector_query_texts(user_query, intent_result)
    vector_indexes = select_vector_indexes(vector_labels)

    graph_operations = list(profile["graph_ops"])
    aggregation_requested = (
        intent_result.intent == "AGGREGATION"
        or "count_tickets_by_metadata_tool" in graph_operations
    )

    return RetrievalPlan(
        original_query=user_query,
        intent=intent_result.intent,
        sub_intent=intent_result.sub_intent,
        required_evidence=intent_result.required_evidence,
        lexical_indexes=lexical_indexes,
        lexical_terms=lexical_terms,
        vector_indexes=vector_indexes,
        vector_query_texts=vector_query_texts,
        graph_anchors=resolved_entities,
        graph_operations=graph_operations,
        aggregation_requested=aggregation_requested,
        modality_priority=[RetrievalSource(p) for p in profile["priority"]],
    )


# --------------------------------------------------------------------------
# Bounded follow-up round
# --------------------------------------------------------------------------

async def _run_followup_round(
    missing_evidence: list[str],
    plan: RetrievalPlan,
    neo4j_driver,
    embed_fn: EmbedFn,
) -> list[Candidate]:
    """
    One bounded, targeted retrieval round for evidence categories the first
    pass didn't cover. Only re-runs lexical + vector against indexes scoped
    to the missing labels — graph anchors don't change based on missing
    evidence alone, so the graph branch isn't re-run here.
    """
    labels = labels_from_required_evidence(missing_evidence)
    if not labels:
        return []

    followup_plan = plan.model_copy(update={
        "lexical_indexes": select_fulltext_indexes(labels),
        "vector_indexes": select_vector_indexes(labels),
    })

    lexical_candidates, _ = await run_lexical_retrieval(neo4j_driver, followup_plan)
    vector_candidates, _ = await run_vector_retrieval(neo4j_driver, embed_fn, followup_plan)
    return lexical_candidates + vector_candidates


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

async def retrieve(
    user_query: str,
    intent_result: QueryIntentResult,
    *,
    neo4j_driver,
    tool_registry: ToolRegistry,
    embed_fn: EmbedFn,
    resolved_entities: Optional[list[ResolvedEntity]] = None,
    top_k: int = DEFAULT_TOP_K,
) -> RetrievalResult:
    """
    Run the full hybrid retrieval pipeline and return a structured result
    ready for the synthesis LLM.

    Args:
        user_query: the original user question.
        intent_result: upstream QueryIntentResult.
        neo4j_driver: an `neo4j.AsyncDriver` (or duck-typed equivalent)
            used directly for the lexical and vector branches.
        tool_registry: a ToolRegistry wrapping the existing LlamaIndex
            FunctionTools, used for the graph branch.
        embed_fn: async callable mapping query text -> embedding vector,
            used for vector index queries.
        resolved_entities: optional entity-resolution hits to anchor graph
            retrieval and boost matching candidates during reranking.
        top_k: bound on the number of evidence items returned.
    """
    resolved_entities = resolved_entities or []
    plan = build_retrieval_plan(user_query, intent_result, resolved_entities)

    lexical_candidates, vector_candidates, graph_result = await asyncio.gather(
        run_lexical_retrieval(neo4j_driver, plan),
        run_vector_retrieval(neo4j_driver, embed_fn, plan),
        run_graph_retrieval(tool_registry, plan),
    )
    lexical_candidates, lexical_outcome = lexical_candidates
    vector_candidates, vector_outcome = vector_candidates
    graph_candidates, graph_outcome, aggregation_result = graph_result

    modality_outcomes: list[ModalityOutcome] = [lexical_outcome, vector_outcome, graph_outcome]

    all_candidates = normalize_candidates(lexical_candidates + vector_candidates + graph_candidates)
    fused = fuse_candidates(all_candidates)
    mark_entity_matches(fused, resolved_entities)
    ranked = rerank_candidates(fused, plan)
    coverage = check_evidence_coverage(ranked, plan.required_evidence, aggregation_result)

    rounds_used = 0
    while not coverage.complete and rounds_used < MAX_ADDITIONAL_RETRIEVAL_ROUNDS:
        followup_candidates = await _run_followup_round(coverage.missing, plan, neo4j_driver, embed_fn)
        rounds_used += 1
        if not followup_candidates:
            break
        all_candidates = normalize_candidates(all_candidates + followup_candidates)
        fused = fuse_candidates(all_candidates)
        mark_entity_matches(fused, resolved_entities)
        ranked = rerank_candidates(fused, plan)
        coverage = check_evidence_coverage(ranked, plan.required_evidence, aggregation_result)

    evidence = select_evidence(ranked, plan.required_evidence, top_k=top_k)

    failed_modalities = [o for o in modality_outcomes if not o.ok]
    if failed_modalities and not evidence:
        status = "failed"
    elif failed_modalities or not coverage.complete:
        status = "partial"
    else:
        status = "success"

    return RetrievalResult(
        status=status,
        query=user_query,
        intent=intent_result.model_dump(),
        retrieval_summary={
            "lexical_candidates": len(lexical_candidates),
            "vector_candidates": len(vector_candidates),
            "graph_candidates": len(graph_candidates),
            "fused_candidates": len(fused),
            "followup_rounds_used": rounds_used,
            "modality_priority": [str(s) for s in plan.modality_priority],
        },
        resolved_entities=resolved_entities,
        evidence=evidence,
        modality_outcomes=modality_outcomes,
        coverage=coverage,
        aggregation_result=aggregation_result,
    )
