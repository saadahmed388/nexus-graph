"""
Graph retrieval branch: exclusively uses the existing FunctionTools methods
(get_ticket_relations_tool, traverse_ticket_network_tool, get_node_details_tool,
get_all_connected_nodes_content_tool, count_tickets_by_metadata_tool).
Structural / contextual retrieval — relationships, traversal, node detail,
and direct aggregation. vector_search_tool / full_text_keyword_tool are
handled by vector.py / lexical.py instead, since they're really the vector
and lexical branches wearing FunctionTool clothing.

This module is written against the ACTUAL signatures of those tools, which
matters because they don't all anchor the same way:

  - get_ticket_relations_tool, traverse_ticket_network_tool, and
    get_all_connected_nodes_content_tool all key off a ticket's Jira issue
    key (`ticket_id`), NOT a Neo4j elementId.
  - get_node_details_tool is the one tool that takes a Neo4j elementId
    (`node_identifier`) — typically one discovered via a relations call.
  - count_tickets_by_metadata_tool keys off a metadata value (a person,
    track, label, or system name) plus an optional relation_type.
  - get_all_connected_nodes_content_tool REQUIRES a specific relation_type
    (it's interpolated directly into the tool's Cypher) — it can't be
    called with "any relation", unlike get_ticket_relations_tool.

A note on the reference implementation: several of these tools return
plain human-readable strings rather than structured data on the "not
found" path (and count_tickets_by_metadata_tool returns plain text even on
success). `tools.parse_tool_output` wraps any non-JSON string as
`{"_text": "..."}` so every parser below has one place to check for that
rather than guessing at string formats.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from .models import Candidate, ModalityOutcome, RetrievalPlan, RetrievalSource
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

_MAX_DETAIL_EXPANSIONS = 8  # bound on how many discovered targets get a get_node_details_tool follow-up
_AGGREGATE_COUNT_RE = re.compile(r"Total Unique Tickets:\s*(\d+)", re.IGNORECASE)


def _is_text_only(parsed) -> bool:
    return isinstance(parsed, dict) and set(parsed.keys()) == {"_text"}


# --------------------------------------------------------------------------
# Per-tool output parsers
# --------------------------------------------------------------------------

def _candidates_from_relations(parsed) -> tuple[list[Candidate], list[dict]]:
    """
    get_ticket_relations_tool returns relationship EDGES, not node content:
    {"relationships": [{"relationship", "direction",
     "target": {"labels": [...], "element_id": ...}}, ...]}
    There's no score and no properties here — just structural discovery —
    so candidates from this parser carry graph_score=None and rely on
    intent/evidence bonuses during reranking. The target list is also
    returned separately so the caller can optionally expand a bounded
    number of them into full node detail via get_node_details_tool.
    """
    if _is_text_only(parsed) or not isinstance(parsed, dict):
        return [], []
    relationships = parsed.get("relationships")
    if not isinstance(relationships, list):
        return [], []

    candidates, targets = [], []
    for rel in relationships:
        target = rel.get("target") or {}
        element_id = target.get("element_id")
        if not element_id:
            continue
        labels = target.get("labels") or []
        candidates.append(
            Candidate(
                element_id=str(element_id),
                labels=labels,
                sources=[RetrievalSource.GRAPH],
                relationship=rel.get("relationship"),
            )
        )
        targets.append({"element_id": str(element_id), "labels": labels})
    return candidates, targets


def _candidates_from_traverse(parsed) -> list[Candidate]:
    """
    traverse_ticket_network_tool returns a list of paths, each a list of hop
    dicts: {"source_element_id", "target_element_id", "source_key",
    "target_key", "relationship"}. Only ticket keys/ids are available here
    (no full properties), so candidates carry a minimal `issue_key` property
    — enough to satisfy "related tickets" evidence coverage even without
    full content.
    """
    if not isinstance(parsed, list):
        return []

    seen: dict[str, Candidate] = {}
    for path in parsed:
        if not isinstance(path, list):
            continue
        for hop in path:
            if not isinstance(hop, dict):
                continue
            for side in ("source", "target"):
                element_id = hop.get(f"{side}_element_id")
                key = hop.get(f"{side}_key")
                if not element_id or element_id in seen:
                    continue
                seen[element_id] = Candidate(
                    element_id=str(element_id),
                    labels=["ticket"],
                    properties={"issue_key": key} if key else {},
                    sources=[RetrievalSource.GRAPH],
                    relationship=hop.get("relationship"),
                )
    return list(seen.values())


def _candidates_from_bulk_content(parsed, relationship: str) -> list[Candidate]:
    """
    get_all_connected_nodes_content_tool returns, on success:
    {"data": {label: [{"node_id", "relation", "direction", "properties"}, ...]}}
    and a plain "No items found..." string otherwise (already normalized to
    {"_text": ...} by this point).
    """
    if _is_text_only(parsed) or not isinstance(parsed, dict):
        return []
    data = parsed.get("data")
    if not isinstance(data, dict):
        return []

    candidates = []
    for label, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            node_id = item.get("node_id")
            if not node_id:
                continue
            candidates.append(
                Candidate(
                    element_id=str(node_id),
                    labels=[label],
                    properties=item.get("properties") or {},
                    sources=[RetrievalSource.GRAPH],
                    relationship=item.get("relation") or relationship,
                )
            )
    return candidates


def _candidate_from_node_details(parsed, element_id: str, labels: list[str]) -> Optional[Candidate]:
    """get_node_details_tool returns {"header", "data": {...props...}} or an error string."""
    if _is_text_only(parsed) or not isinstance(parsed, dict):
        return None
    properties = parsed.get("data")
    if not isinstance(properties, dict):
        return None
    return Candidate(
        element_id=element_id,
        labels=labels,
        properties=properties,
        sources=[RetrievalSource.GRAPH],
        relationship="get_node_details_tool",
    )


def _parse_aggregation_output(parsed) -> Optional[dict]:
    """
    count_tickets_by_metadata_tool returns a plain formatted summary string
    on both the found and not-found paths — never structured JSON. Extract
    the total via regex and keep the human-readable text alongside it so
    nothing is silently lost even where the regex doesn't match.
    """
    text = parsed.get("_text") if _is_text_only(parsed) else None
    if text is None:
        # Tool was fixed upstream to return structured data — use as-is.
        return parsed if isinstance(parsed, dict) else None

    if text.strip().lower().startswith("no tickets found"):
        return {"total": 0, "raw_text": text}

    match = _AGGREGATE_COUNT_RE.search(text)
    return {"total": int(match.group(1)) if match else None, "raw_text": text}


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

async def run_graph_retrieval(
    registry: ToolRegistry, plan: RetrievalPlan
) -> tuple[list[Candidate], ModalityOutcome, Optional[dict]]:
    """
    Execute every planned, anchor-eligible graph operation concurrently.
    Ticket-anchored ops (relations, traversal, bulk content) only run when
    the plan resolved a specific ticket_id; the metadata aggregation op
    only runs when the plan resolved a metadata anchor value. Neither is
    guessed at when absent — the lexical/vector branches keep working with
    or without a graph anchor.
    """
    tasks: list = []
    kinds: list[str] = []

    if plan.ticket_anchor:
        if "get_ticket_relations_tool" in plan.graph_operations:
            tasks.append(registry.call_safe(
                "get_ticket_relations_tool", ticket_id=plan.ticket_anchor, relation_type=None
            ))
            kinds.append("relations")

        if "traverse_ticket_network_tool" in plan.graph_operations:
            tasks.append(registry.call_safe(
                "traverse_ticket_network_tool", ticket_id=plan.ticket_anchor,
                relation_types=None, max_hops=3,
            ))
            kinds.append("traverse")

        if "get_all_connected_nodes_content_tool" in plan.graph_operations:
            for relation in plan.content_relations:
                tasks.append(registry.call_safe(
                    "get_all_connected_nodes_content_tool",
                    ticket_id=plan.ticket_anchor, relation_type=relation,
                ))
                kinds.append(f"content:{relation}")

    aggregation_planned = (
        "count_tickets_by_metadata_tool" in plan.graph_operations and plan.metadata_anchor_value
    )
    if aggregation_planned:
        tasks.append(registry.call_safe(
            "count_tickets_by_metadata_tool",
            metadata_value=plan.metadata_anchor_value,
            relation_type=plan.metadata_relation_type,
        ))
        kinds.append("aggregation")

    if not tasks:
        return [], ModalityOutcome(source=RetrievalSource.GRAPH, ok=True, candidate_count=0), None

    results = await asyncio.gather(*tasks)  # call_safe never raises

    candidates: list[Candidate] = []
    errors: list[str] = []
    aggregation_result: Optional[dict] = None
    relation_targets: list[dict] = []

    for kind, (ok, parsed) in zip(kinds, results):
        if not ok:
            errors.append(f"{kind}: {parsed}")
            continue
        if kind == "relations":
            rel_candidates, targets = _candidates_from_relations(parsed)
            candidates.extend(rel_candidates)
            relation_targets.extend(targets)
        elif kind == "traverse":
            candidates.extend(_candidates_from_traverse(parsed))
        elif kind.startswith("content:"):
            candidates.extend(_candidates_from_bulk_content(parsed, relationship=kind.split(":", 1)[1]))
        elif kind == "aggregation":
            aggregation_result = _parse_aggregation_output(parsed)

    # Bounded follow-up: expand a handful of relation-discovered targets
    # (e.g. the track/system/label a ticket belongs to) into full node
    # detail, per the tools' own documented usage pattern. Only for intents
    # that actually need those property values (see config.INTENT_PROFILES
    # "expand_node_details").
    detail_count = 0
    if plan.expand_node_details and relation_targets:
        targets_to_expand = relation_targets[:_MAX_DETAIL_EXPANSIONS]
        detail_count = len(targets_to_expand)
        detail_results = await asyncio.gather(*[
            registry.call_safe("get_node_details_tool", node_identifier=t["element_id"])
            for t in targets_to_expand
        ])
        for target, (ok, parsed) in zip(targets_to_expand, detail_results):
            if not ok:
                errors.append(f"get_node_details_tool({target['element_id']}): {parsed}")
                continue
            detail_candidate = _candidate_from_node_details(parsed, target["element_id"], target["labels"])
            if detail_candidate is not None:
                candidates.append(detail_candidate)

    total_attempts = len(tasks) + detail_count
    ok = (len(errors) < total_attempts) if total_attempts else True
    outcome = ModalityOutcome(
        source=RetrievalSource.GRAPH,
        ok=ok,
        candidate_count=len(candidates),
        error="; ".join(errors) if errors else None,
    )
    return candidates, outcome, aggregation_result
