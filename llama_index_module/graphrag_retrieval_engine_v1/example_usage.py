"""
Example: wiring the engine into your real LlamaIndex + Neo4j system.

Every branch — lexical, vector, and graph — now routes through your
existing `FunctionTools` instance (see function_tools.py). There's no
direct Neo4j driver or embedder dependency left in the engine itself:
vector_search_tool already owns the embedding step, and full_text_keyword_tool
already owns the lexical lookup.
"""
from __future__ import annotations

import asyncio

from function_tools import FunctionTools
from graphrag_retrieval import QueryIntentResult, ResolvedEntity, ToolRegistry, retrieve

# --- 1. Neo4j driver + embedding model, exactly as FunctionTools expects ----
# from neo4j import AsyncGraphDatabase
# from llama_index.core import Settings
#
# driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
# function_tools = FunctionTools(driver=driver, embedding_model=Settings.embed_model)

# --- 2. Wrap its bound methods in a ToolRegistry -----------------------------
# registry = ToolRegistry({
#     "vector_search_tool": function_tools.vector_search_tool,
#     "full_text_keyword_tool": function_tools.full_text_keyword_tool,
#     "get_ticket_relations_tool": function_tools.get_ticket_relations_tool,
#     "traverse_ticket_network_tool": function_tools.traverse_ticket_network_tool,
#     "get_node_details_tool": function_tools.get_node_details_tool,
#     "get_all_connected_nodes_content_tool": function_tools.get_all_connected_nodes_content_tool,
#     "count_tickets_by_metadata_tool": function_tools.count_tickets_by_metadata_tool,
# })
#
# These same bound methods are also what you'd pass to
# FunctionTool.from_defaults(fn=...) when registering them with your
# FunctionAgent/ReActAgent — nothing about that registration changes.


async def main():
    # Wherever your upstream intent classifier already produces this:
    intent_result = QueryIntentResult(
        intent="ROOT_CAUSE",
        sub_intent="root cause of EAI transform failure",
        required_evidence=["investigationReport", "ticket"],
        retrieval_strategy=["vector", "graph"],
    )

    # Wherever your entity-resolution step already produces this (optional).
    # A "ticket" entity anchors the ticket-scoped graph tools
    # (get_ticket_relations_tool, traverse_ticket_network_tool,
    # get_all_connected_nodes_content_tool). A person/track/label/system/
    # environment entity anchors count_tickets_by_metadata_tool instead.
    resolved_entities: list[ResolvedEntity] = [
        # ResolvedEntity(mention="NV-1023", canonical_name="NV-1023", label="ticket"),
    ]

    result = await retrieve(
        "Why did the EAI transform fail on ticket NV-1023?",
        intent_result,
        tool_registry=registry,  # noqa: F821 - see steps 1-2 above
        resolved_entities=resolved_entities,
        top_k=12,
    )

    print("status:", result.status)
    print("coverage:", result.coverage)
    for c in result.evidence:
        print(f"- [{'/'.join(c.labels)}] {c.element_id} score={c.final_score} sources={c.sources}")

    # `result.model_dump()` gives you the plain dict shown in the design doc
    # (status/query/intent/retrieval_summary/evidence/coverage/...), ready
    # to hand to the synthesis LLM.


if __name__ == "__main__":
    asyncio.run(main())
