"""
Normalization, deduplication/fusion, and reranking of candidates gathered
from the lexical, vector, and graph branches.
"""
from __future__ import annotations

from .config import RERANK_WEIGHTS, RRF_K, intent_priority_labels, labels_from_required_evidence
from .models import Candidate, ResolvedEntity, RetrievalPlan

_MAX_PROPERTY_TEXT_LEN = 4000  # guard against unexpectedly huge text fields


def normalize_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """
    Final cleanup pass applied to the combined candidate pool before fusion:
    caps long text values. Each branch already builds a common Candidate
    shape on the way out, so this step is intentionally light — it exists as
    one explicit choke point rather than scattered defensive checks.
    """
    for c in candidates:
        for key, value in list(c.properties.items()):
            if isinstance(value, str) and len(value) > _MAX_PROPERTY_TEXT_LEN:
                c.properties[key] = value[:_MAX_PROPERTY_TEXT_LEN] + "...[truncated]"
    return candidates


def fuse_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """
    Deduplicate by Neo4j elementId, merging per-modality scores and sources
    for any node that multiple branches independently surfaced. Multi-source
    agreement is preserved (not discarded) as a signal for reranking.
    """
    merged: dict[str, Candidate] = {}
    for c in candidates:
        existing = merged.get(c.element_id)
        if existing is None:
            merged[c.element_id] = c
            continue

        for s in c.sources:
            if s not in existing.sources:
                existing.sources.append(s)

        if c.lexical_score is not None:
            existing.lexical_score = max(existing.lexical_score or 0.0, c.lexical_score)
        if c.vector_score is not None:
            existing.vector_score = max(existing.vector_score or 0.0, c.vector_score)
        if c.graph_score is not None:
            existing.graph_score = max(existing.graph_score or 0.0, c.graph_score)

        # Prefer whichever copy carried richer property data.
        if len(c.properties) > len(existing.properties):
            existing.properties = c.properties
        for label in c.labels:
            if label not in existing.labels:
                existing.labels.append(label)

        if c.relationship and not existing.relationship:
            existing.relationship = c.relationship

    return list(merged.values())


def mark_entity_matches(candidates: list[Candidate], resolved_entities: list[ResolvedEntity]) -> None:
    """Flag candidates that correspond to an already-resolved entity anchor."""
    anchor_ids = {e.element_id for e in resolved_entities if e.element_id}
    if not anchor_ids:
        return
    for c in candidates:
        if c.element_id in anchor_ids:
            c.entity_match = True


def _rrf_scores(candidates: list[Candidate], score_attr: str) -> dict[str, float]:
    """
    Rank candidates by one modality's raw score and convert rank position
    into a fusion-friendly value via (scaled) Reciprocal Rank Fusion:
    k / (k + rank). This sidesteps comparing raw lexical/vector/graph scores
    directly (they live on different scales) while still rewarding a
    candidate for ranking well within any single modality.
    """
    scored = [(c.element_id, getattr(c, score_attr)) for c in candidates if getattr(c, score_attr) is not None]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return {element_id: RRF_K / (RRF_K + rank) for rank, (element_id, _) in enumerate(scored, start=1)}


def rerank_candidates(candidates: list[Candidate], plan: RetrievalPlan) -> list[Candidate]:
    """
    Combine per-modality RRF scores with intent/evidence/entity alignment
    signals into a single final_score. Weights live in config.RERANK_WEIGHTS
    so the ranking can be retuned without touching this logic. Raw vector or
    lexical score alone never determines the outcome — both are only ever
    consulted through their rank position, then blended with the other
    relevance signals below.
    """
    if not candidates:
        return []

    lexical_rrf = _rrf_scores(candidates, "lexical_score")
    vector_rrf = _rrf_scores(candidates, "vector_score")
    graph_rrf = _rrf_scores(candidates, "graph_score")

    priority_labels = intent_priority_labels(plan.intent)
    required_labels = set(labels_from_required_evidence(plan.required_evidence))

    w = RERANK_WEIGHTS
    for c in candidates:
        score = 0.0
        score += w["lexical"] * lexical_rrf.get(c.element_id, 0.0)
        score += w["vector"] * vector_rrf.get(c.element_id, 0.0)
        score += w["graph"] * graph_rrf.get(c.element_id, 0.0)

        if any(label in priority_labels for label in c.labels):
            score += w["intent_label_match"]
        if required_labels and any(label in required_labels for label in c.labels):
            score += w["required_evidence_match"]
        if c.entity_match:
            score += w["entity_match"]

        extra_sources = max(0, len(set(c.sources)) - 1)
        score += w["multi_source_bonus"] * extra_sources

        c.final_score = round(score, 6)

    candidates.sort(key=lambda c: c.final_score or 0.0, reverse=True)
    return candidates
