"""
Graph retrieval branch: exclusively uses the existing LlamaIndex FunctionTools
(vector_search_tool, full_text_keyword_tool, get_ticket_relations_tool,
traverse_ticket_network_tool, get_node_details_tool,
get_all_connected_nodes_content_tool, count_tickets_by_metadata_tool).
Structural / contextual retrieval — relationships, traversal, node detail,
and direct aggregation. No raw Cypher lives here by design; the tools
already encapsulate that.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .models import Candidate, ModalityOutcome, ResolvedEntity, RetrievalPlan, RetrievalSource
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

_STRIP_PROPERTY_KEYS = {"embedding", "vector", "raw_text_blob"}

# count_tickets_by_metadata_tool returns a scalar/aggregate, not a node list,
# so it's handled as a single separate call rather than folded into the
# generic node-producing dispatch below.
_AGGREGATION_OP = "count_tickets_by_metadata_tool"
_ANCHOR_REQUIRED_OPS = {
    "get_ticket_relations_tool",
    "traverse_ticket_network_tool",
    "get_all_connected_nodes_content_tool",
    "get_node_details_tool",
}
_QUERY_ONLY_OPS = {"vector_search_tool", "full_text_keyword_tool"}


def _clean_properties(props: dict) -> dict:
    return {k: v for k, v in (props or {}).items() if k not in _STRIP_PROPERTY_KEYS}


def _candidates_from_tool_output(
    raw: object, relationship: Optional[str], source_query: str
) -> list[Candidate]:
    """
    Normalize whatever shape a FunctionTool happens to return (a list of
    dicts, a single dict, or a dict nesting a 'nodes'/'results' list) into
    Candidates. Tools are treated as black boxes with best-effort parsing —
    per the instruction not to redesign them, this makes no assumption
    beyond "some dict-shaped node data is present somewhere in here."
    """
    items: list[dict] = []
    if isinstance(raw, dict):
        for key in ("nodes", "results", "records", "tickets", "data"):
            nested = raw.get(key)
            if isinstance(nested, list):
                items = nested
                break
        else:
            if "element_id" in raw or "elementId" in raw:
                items = [raw]
    elif isinstance(raw, list):
        items = [i for i in raw if isinstance(i, dict)]

    candidates = []
    for item in items:
        element_id = item.get("element_id") or item.get("elementId")
        if not element_id:
            continue
        labels = item.get("labels") or ([item["label"]] if item.get("label") else [])
        properties = item.get("properties") or {
            k: v for k, v in item.items()
            if k not in {"element_id", "elementId", "labels", "label", "score"}
        }
        candidates.append(
            Candidate(
                element_id=str(element_id),
                labels=labels,
                properties=_clean_properties(properties),
                sources=[RetrievalSource.GRAPH],
                graph_score=float(item["score"]) if item.get("score") is not None else None,
                matched_query=source_query,
                relationship=relationship,
            )
        )
    return candidates


async def _run_candidate_op(
    registry: ToolRegistry, op: str, anchor: Optional[ResolvedEntity], plan: RetrievalPlan
) -> list[Candidate]:
    """Dispatch one graph operation for one anchor (or query-only, if no anchor)."""
    if op in _ANCHOR_REQUIRED_OPS:
        if not (anchor and anchor.element_id):
            return []  # these tools need a graph anchor; skip rather than guess one
        ok, raw = await registry.call_safe(op, element_id=anchor.element_id)
    elif op in _QUERY_ONLY_OPS:
        ok, raw = await registry.call_safe(op, query=plan.original_query)
    else:
        logger.warning("Unrecognized/unsupported graph operation in plan: %s", op)
        return []

    if not ok:
        return []
    return _candidates_from_tool_output(raw, relationship=op, source_query=plan.original_query)


async def run_graph_retrieval(
    registry: ToolRegistry, plan: RetrievalPlan
) -> tuple[list[Candidate], ModalityOutcome, Optional[dict]]:
    """
    Execute every planned graph operation across every graph anchor
    (resolved entity), concurrently. A missing anchor causes an
    anchor-dependent op to be skipped for that anchor rather than guessed at.
    Aggregation is handled as one separate call since it returns a scalar
    rather than a node list.
    """
    candidate_ops = [op for op in plan.graph_operations if op != _AGGREGATION_OP]
    anchors: list[Optional[ResolvedEntity]] = plan.graph_anchors or [None]

    tasks = [
        _run_candidate_op(registry, op, anchor, plan)
        for op in candidate_ops
        for anchor in anchors
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []

    candidates: list[Candidate] = []
    errors: list[str] = []
    for res in results:
        if isinstance(res, Exception):
            errors.append(str(res))
            logger.warning("Graph op failed: %s", res)
            continue
        candidates.extend(res)

    aggregation_result = None
    aggregation_attempted = _AGGREGATION_OP in plan.graph_operations
    if aggregation_attempted:
        anchor = plan.graph_anchors[0] if plan.graph_anchors else None
        kwargs = {"query": plan.original_query}
        if anchor and anchor.element_id:
            kwargs["element_id"] = anchor.element_id
        ok, raw = await registry.call_safe(_AGGREGATION_OP, **kwargs)
        if ok:
            aggregation_result = raw if isinstance(raw, dict) else {"result": raw}
        else:
            errors.append(f"{_AGGREGATION_OP}: {raw}")

    total_attempts = len(results) + (1 if aggregation_attempted else 0)
    ok = (len(errors) < total_attempts) if total_attempts else True
    outcome = ModalityOutcome(
        source=RetrievalSource.GRAPH,
        ok=ok,
        candidate_count=len(candidates),
        error="; ".join(errors) if errors else None,
    )
    return candidates, outcome, aggregation_result
