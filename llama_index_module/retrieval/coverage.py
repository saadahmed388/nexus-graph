"""
Evidence coverage checking and final top-K evidence selection.
"""
from __future__ import annotations

from .config import DEFAULT_TOP_K, PER_LABEL_MIN_SLOTS, labels_from_required_evidence
from .models import Candidate, EvidenceCoverage


def check_evidence_coverage(
    candidates: list[Candidate],
    required_evidence: list[str],
    aggregation_result: dict | None = None,
) -> EvidenceCoverage:
    """
    A required_evidence item is satisfied if:
      - it names an aggregation/count requirement and an aggregation_result
        is already available, or
      - it maps to a known node label and at least one candidate carries
        that label, or
      - it doesn't map to anything in the label table, in which case it
        can't be verified structurally and is treated as satisfied by
        default rather than blocking the whole result on an unmappable
        requirement.
    """
    present_labels = {label for c in candidates for label in c.labels}
    satisfied: list[str] = []
    missing: list[str] = []

    for item in required_evidence:
        key = item.strip().lower()
        if "aggregate" in key or "count" in key:
            (satisfied if aggregation_result is not None else missing).append(item)
            continue

        mapped = labels_from_required_evidence([item])
        if not mapped:
            satisfied.append(item)
        elif any(label in present_labels for label in mapped):
            satisfied.append(item)
        else:
            missing.append(item)

    return EvidenceCoverage(complete=not missing, satisfied=satisfied, missing=missing)


def select_evidence(
    candidates: list[Candidate],
    required_evidence: list[str],
    top_k: int = DEFAULT_TOP_K,
) -> list[Candidate]:
    """
    Take the reranked pool and build a bounded, coverage-aware evidence set:
    reserve a few top-ranked slots per required-evidence label first, so a
    strong requirement doesn't get crowded out purely by another label's
    higher-scoring candidates, then fill the remainder by rank.
    """
    if not candidates:
        return []

    required_labels = labels_from_required_evidence(required_evidence)
    selected: list[Candidate] = []
    selected_ids: set[str] = set()

    for label in required_labels:
        count = 0
        for c in candidates:
            if count >= PER_LABEL_MIN_SLOTS:
                break
            if label in c.labels and c.element_id not in selected_ids:
                selected.append(c)
                selected_ids.add(c.element_id)
                count += 1

    for c in candidates:
        if len(selected) >= top_k:
            break
        if c.element_id not in selected_ids:
            selected.append(c)
            selected_ids.add(c.element_id)

    # Re-sort by rank so reserved-slot insertion order doesn't scramble the
    # final ordering handed to the synthesis LLM.
    selected.sort(key=lambda c: c.final_score or 0.0, reverse=True)
    return selected[:top_k]
