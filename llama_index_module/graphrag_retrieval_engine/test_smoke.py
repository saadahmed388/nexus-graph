"""
Offline smoke tests. No live Neo4j or LlamaIndex required — every
FunctionTools method is faked with realistic return shapes (JSON strings,
raw dicts, raw lists, and plain text — matching what the real
`FunctionTools` implementation actually returns) so the full `retrieve()`
pipeline can be exercised end to end in CI.

Run with:  python3 test_smoke.py
"""
from __future__ import annotations

import asyncio
import json

from graphrag_retrieval import (
    Candidate,
    QueryIntentResult,
    ResolvedEntity,
    ToolRegistry,
    build_retrieval_plan,
    check_evidence_coverage,
    fuse_candidates,
    normalize_candidates,
    rerank_candidates,
    retrieve,
    select_evidence,
)

# ---------------------------------------------------------------------------
# Fake FunctionTools methods — return shapes mirror the real implementation:
# vector_search_tool / full_text_keyword_tool / get_ticket_relations_tool
# return JSON strings; get_all_connected_nodes_content_tool and
# get_node_details_tool return raw dicts (or a plain string when nothing is
# found); traverse_ticket_network_tool returns a raw list (or plain string);
# count_tickets_by_metadata_tool always returns plain text.
# ---------------------------------------------------------------------------

FAKE_VECTOR_HITS = {
    "investigation_report_embedding_index": [
        {"element_id": "inv-1", "labels": ["investigationReport"],
         "properties": {"summary": "Null pointer in EAI transform"}, "score": 0.87},
    ],
}
FAKE_LEXICAL_HITS = {
    "ticket_full_text_index": [
        {"element_id": "ticket-1", "labels": ["ticket"],
         "properties": {"issue_key": "NV-1023", "title": "EAI transform failure"}, "score": 3.2},
    ],
}


async def fake_vector_search_tool(query_text: str, index_name: str) -> str:
    hits = FAKE_VECTOR_HITS.get(index_name, [])
    return json.dumps({
        "status": "success", "search_type": "vector", "query": query_text,
        "index": index_name, "count": len(hits), "results": hits,
    })


async def fake_full_text_keyword_tool(keyword: str, index_name: str) -> str:
    hits = FAKE_LEXICAL_HITS.get(index_name, [])
    return json.dumps({
        "status": "success", "search_type": "lexical", "keyword": keyword,
        "index": index_name, "count": len(hits), "results": hits,
    })


async def fake_get_ticket_relations_tool(ticket_id: str, relation_type=None) -> str:
    return json.dumps({
        "status": "success", "source_ticket": ticket_id, "relationship_type": relation_type,
        "relationship_count": 1,
        "relationships": [
            {"source_ticket": ticket_id, "relationship": "HAS_INVESTIGATION", "direction": "outgoing",
             "target": {"labels": ["investigationReport"], "element_id": "inv-1"}},
        ],
    })


async def fake_get_all_connected_nodes_content_tool(ticket_id: str, relation_type: str):
    if relation_type == "HAS_INVESTIGATION":
        return {
            "header": "--- Complete list of data for the requested relation types---",
            "data": {
                "investigationReport": [
                    {"node_id": "inv-1", "relation": "HAS_INVESTIGATION", "direction": "OUTGOING",
                     "properties": {"summary": "Null pointer in EAI transform"}},
                ]
            },
        }
    return f"No items found for relationship '{relation_type}' on ticket '{ticket_id}'."


async def fake_count_tickets_by_metadata_tool(metadata_value: str, relation_type=None) -> str:
    return (
        f"=== Metadata Count Summary for '{metadata_value}' ===\n"
        f"Total Unique Tickets: 7\n\n"
        f"Breakdown by Relationship Type:\n- Connected via 'REPORTS': 7 tickets"
    )


async def fake_traverse_ticket_network_tool(ticket_id, relation_types=None, max_hops=3):
    return [
        [{"source_element_id": "ticket-src", "target_element_id": "ticket-dup",
          "source_key": ticket_id, "target_key": "NV-2000", "relationship": "DUPLICATES"}]
    ]


async def fake_get_node_details_tool(node_identifier: str):
    return {
        "header": f"=== Details for Node: {node_identifier} ===",
        "data": {"name": "SV Track", "id": node_identifier},
    }


def make_fake_tool_registry() -> ToolRegistry:
    return ToolRegistry({
        "vector_search_tool": fake_vector_search_tool,
        "full_text_keyword_tool": fake_full_text_keyword_tool,
        "get_ticket_relations_tool": fake_get_ticket_relations_tool,
        "get_all_connected_nodes_content_tool": fake_get_all_connected_nodes_content_tool,
        "count_tickets_by_metadata_tool": fake_count_tickets_by_metadata_tool,
        "traverse_ticket_network_tool": fake_traverse_ticket_network_tool,
        "get_node_details_tool": fake_get_node_details_tool,
    })


# ---------------------------------------------------------------------------
# Pure-logic tests (no I/O)
# ---------------------------------------------------------------------------

def test_build_retrieval_plan_root_cause():
    intent = QueryIntentResult(
        intent="ROOT_CAUSE",
        sub_intent="find root cause of EAI transform failure",
        required_evidence=["investigationReport", "ticket"],
        retrieval_strategy=["vector", "graph"],
    )
    plan = build_retrieval_plan("Why did the EAI transform fail on ticket NV-1023?", intent)

    assert "NV-1023" in plan.lexical_terms
    assert plan.ticket_anchor == "NV-1023"
    assert "investigation_report_full_text_index" in plan.lexical_indexes
    assert "investigation_report_embedding_index" in plan.vector_indexes
    assert plan.graph_operations == ["get_all_connected_nodes_content_tool"]
    assert plan.content_relations == ["HAS_INVESTIGATION"]
    print("OK: build_retrieval_plan (ROOT_CAUSE)")


def test_build_retrieval_plan_falls_back_to_semantic_index():
    intent = QueryIntentResult(
        intent="GENERAL", sub_intent="vague question", required_evidence=[], retrieval_strategy=[]
    )
    plan = build_retrieval_plan("what's been going on with the dealership system lately", intent)
    assert plan.vector_indexes == ["semantic_search_index"]
    assert plan.ticket_anchor is None
    print("OK: build_retrieval_plan (GENERAL semantic fallback)")


def test_fuse_and_rerank_prioritizes_multi_source_and_required_label():
    plan = build_retrieval_plan(
        "investigation findings for ticket NV-1023",
        QueryIntentResult(
            intent="ROOT_CAUSE", sub_intent="root cause", required_evidence=["investigationReport"],
            retrieval_strategy=[],
        ),
    )

    ticket_only_high_score = Candidate(
        element_id="ticket-1", labels=["ticket"], sources=["vector"], vector_score=0.99,
    )
    investigation_multi_source = Candidate(
        element_id="inv-1", labels=["investigationReport"], sources=["vector", "graph"],
        vector_score=0.4, graph_score=0.5,
    )

    fused = fuse_candidates(normalize_candidates([ticket_only_high_score, investigation_multi_source]))
    ranked = rerank_candidates(fused, plan)

    assert ranked[0].element_id == "inv-1", "investigationReport should outrank a raw-score-only ticket"
    print("OK: rerank prioritizes required-evidence label + multi-source agreement over raw score")


def test_evidence_coverage_and_selection():
    candidates = [
        Candidate(element_id="t1", labels=["ticket"], final_score=0.9),
        Candidate(element_id="p1", labels=["person"], final_score=0.7),
    ]
    coverage = check_evidence_coverage(candidates, ["ticket", "person", "investigationReport"])
    assert coverage.satisfied == ["ticket", "person"]
    assert coverage.missing == ["investigationReport"]

    selected = select_evidence(candidates, ["ticket", "person"], top_k=5)
    assert {c.element_id for c in selected} == {"t1", "p1"}
    print("OK: evidence coverage + selection")


def test_resolved_entity_drives_metadata_anchor_not_ticket_anchor():
    """
    A resolved *person* entity should anchor aggregation (metadata_anchor_value
    + relation_type) — it must NOT be mistaken for a ticket anchor, since
    count_tickets_by_metadata_tool and get_ticket_relations_tool key off
    completely different identifiers in the real tool signatures.
    """
    entity = ResolvedEntity(mention="Yoshihara", canonical_name="Yoshihara Taro",
                             label="person", element_id="person-42")
    intent = QueryIntentResult(
        intent="AGGREGATION", sub_intent="count tickets by reporter",
        required_evidence=["person", "aggregated ticket count"], retrieval_strategy=["graph"],
    )
    plan = build_retrieval_plan(
        "How many issues raised by Yoshihara related to BIP reports?", intent, [entity]
    )
    assert plan.ticket_anchor is None
    assert plan.metadata_anchor_value == "Yoshihara Taro"
    assert plan.metadata_relation_type == "REPORTS"
    assert "Yoshihara Taro" in plan.lexical_terms
    assert plan.aggregation_requested is True
    print("OK: resolved person entity becomes a metadata anchor, not a ticket anchor")


# ---------------------------------------------------------------------------
# Full pipeline tests (fake FunctionTools)
# ---------------------------------------------------------------------------

async def test_full_retrieve_pipeline():
    registry = make_fake_tool_registry()
    intent = QueryIntentResult(
        intent="ROOT_CAUSE",
        sub_intent="root cause of EAI transform failure",
        required_evidence=["investigationReport", "ticket"],
        retrieval_strategy=["vector", "graph"],
    )

    result = await retrieve(
        "Why did the EAI transform fail on ticket NV-1023?",
        intent,
        tool_registry=registry,
    )

    assert result.status in ("success", "partial")
    assert any("investigationReport" in c.labels for c in result.evidence)
    assert any("ticket" in c.labels for c in result.evidence)
    print("OK: full retrieve() pipeline (status=%s, evidence=%d)" % (result.status, len(result.evidence)))


async def test_aggregation_result_parses_plain_text_output():
    registry = make_fake_tool_registry()
    intent = QueryIntentResult(
        intent="AGGREGATION", sub_intent="count tickets reported by person",
        required_evidence=["person", "aggregated ticket count"], retrieval_strategy=["graph"],
    )
    entity = ResolvedEntity(mention="Yoshihara", canonical_name="Yoshihara Taro",
                             label="person", element_id="person-42")

    result = await retrieve(
        "How many tickets did Yoshihara raise?",
        intent,
        tool_registry=registry,
        resolved_entities=[entity],
    )
    # count_tickets_by_metadata_tool returns plain text, not JSON — confirm
    # the regex-based parser still recovers the total.
    assert result.aggregation_result is not None
    assert result.aggregation_result["total"] == 7
    assert "Total Unique Tickets: 7" in result.aggregation_result["raw_text"]
    print("OK: aggregation_result recovered from plain-text tool output")


async def test_metadata_intent_expands_relation_targets_into_node_details():
    registry = make_fake_tool_registry()
    intent = QueryIntentResult(
        intent="METADATA", sub_intent="which track is this ticket on",
        required_evidence=["ticket"], retrieval_strategy=["graph"],
    )
    result = await retrieve("What track is ticket NV-1023 on?", intent, tool_registry=registry)
    # get_ticket_relations_tool -> discovers inv-1 -> expand_node_details
    # chases it into get_node_details_tool, which should surface its properties.
    detail_hits = [c for c in result.evidence if c.properties.get("name") == "SV Track"]
    assert detail_hits, "expected a get_node_details_tool-expanded candidate in evidence"
    print("OK: METADATA intent expands relation targets via get_node_details_tool")


def main():
    test_build_retrieval_plan_root_cause()
    test_build_retrieval_plan_falls_back_to_semantic_index()
    test_fuse_and_rerank_prioritizes_multi_source_and_required_label()
    test_evidence_coverage_and_selection()
    test_resolved_entity_drives_metadata_anchor_not_ticket_anchor()
    asyncio.run(test_full_retrieve_pipeline())
    asyncio.run(test_aggregation_result_parses_plain_text_output())
    asyncio.run(test_metadata_intent_expands_relation_targets_into_node_details())
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
