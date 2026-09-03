# Hybrid GraphRAG Retrieval Engine

Orchestration layer around your existing `FunctionTools` (see
`function_tools.py`). It does not redesign any retrieval tool — it plans,
parallelizes, fuses, reranks, and packages evidence for the synthesis LLM.

```
graphrag_retrieval/
  models.py     # QueryIntentResult, RetrievalPlan, Candidate, RetrievalResult, ...
  config.py     # index-name mappings, intent profiles, rerank weights (tune here)
  tools.py      # ToolRegistry + output normalization for FunctionTools' mixed return shapes
  lexical.py    # calls full_text_keyword_tool (precise literal matching)
  vector.py     # calls vector_search_tool (semantic discovery; embeds internally)
  graph.py      # calls the 5 structural tools: relations, traversal, node
                # detail, bulk content, aggregation
  fusion.py     # normalize -> dedupe/fuse -> RRF-based rerank
  coverage.py   # evidence coverage check + bounded top-K selection
  engine.py     # build_retrieval_plan() + retrieve() orchestrator
function_tools.py  # reference copy of your FunctionTools class
example_usage.py   # wiring it all together
test_smoke.py       # offline tests with faked tool outputs — no live infra needed
```

## Pipeline

```
user_query + QueryIntentResult
        |
build_retrieval_plan()                  # engine.py
        |
   ┌─────────────┬─────────────┬─────────────┐
   │  lexical.py │  vector.py  │   graph.py  │   <- asyncio.gather, concurrent
   └─────────────┴─────────────┴─────────────┘
        |
normalize_candidates()  -> fuse_candidates()  -> rerank_candidates()   # fusion.py
        |
check_evidence_coverage()  --(missing)-->  one bounded follow-up round
        |
select_evidence()                        # coverage.py
        |
RetrievalResult
```

## Design decisions worth knowing about

**Every branch calls a FunctionTools method — there's no separate Neo4j
driver or embedder in the engine.** `vector_search_tool` and
`full_text_keyword_tool` already do exactly what a hand-rolled "vector
branch" and "lexical branch" would do (they embed/query the same indexes
and return the same `{element_id, labels, properties, score}` shape), so
`lexical.py`/`vector.py` just call them instead of duplicating that access.
The remaining five tools (`get_ticket_relations_tool`,
`traverse_ticket_network_tool`, `get_node_details_tool`,
`get_all_connected_nodes_content_tool`, `count_tickets_by_metadata_tool`)
are the graph branch.

**Two distinct anchor types, because the tools anchor differently.**
`RetrievalPlan.ticket_anchor` (a Jira issue key, e.g. `"NV-1023"`) drives
the three ticket-scoped tools. `RetrievalPlan.metadata_anchor_value` +
`metadata_relation_type` (e.g. `("Yoshihara Taro", "REPORTS")`) drives
`count_tickets_by_metadata_tool`. A resolved `ticket` entity or a
Jira-key regex match becomes the former; a resolved `person`/`track`/
`label`/`system`/`environment` entity becomes the latter
(`config.LABEL_TO_METADATA_RELATION`). Neither is guessed at when absent —
those tools simply don't run, and lexical/vector keep working regardless.

**Tool output is normalized once, centrally.** `tools.parse_tool_output`
handles all four shapes your tools actually return — a JSON string, a raw
dict, a raw list, or plain human-readable text — so every parser downstream
only has to check for `{"_text": ...}` as the "unstructured" case rather
than guessing at string formats itself. `count_tickets_by_metadata_tool` in
particular never returns structured data (see `function_tools.py`'s
docstring note at the top), so its total is recovered via a regex over the
summary text — `graph.py::_parse_aggregation_output`.

**METADATA intent chases relation edges into full node detail.**
`get_ticket_relations_tool` only returns labels + element IDs, not
properties — so when the answer is something like "which track is this
ticket on," a second, bounded round of `get_node_details_tool` calls (capped
at 8) fetches the actual property values for a handful of discovered
targets. This mirrors the tools' own documented usage pattern
("use `get_node_details_tool` when you need to inspect one specific
connected node in depth"). Controlled by `INTENT_PROFILES[...]["expand_node_details"]`.

**Fusion uses Reciprocal Rank Fusion (RRF), not min-max score
normalization.** Lexical (Lucene) and vector (cosine) scores live on
incomparable scales, and most graph candidates have no score at all. Rather
than normalize raw scores, each candidate's *rank position* within each
modality converts to `RRF_K / (RRF_K + rank)`, weighted per modality and
summed, then combined with bonuses for intent-label match,
required-evidence match, entity match, and multi-source agreement — see
`config.RERANK_WEIGHTS` / `config.RRF_K`. This is what lets an
`investigationReport` outrank a `ticket` with a marginally higher raw
vector score when the query is asking for investigation findings
(`test_smoke.py::test_fuse_and_rerank_prioritizes_multi_source_and_required_label`).

**Partial failure is a first-class outcome, not an exception.** Each branch
returns a `ModalityOutcome(ok, candidate_count, error)`; `asyncio.gather`
is used at every fan-out point with `call_safe` (never raises) underneath,
so one bad query or one down tool degrades that branch's results without
aborting the others. `RetrievalResult.status` is `"success"` / `"partial"`
/ `"failed"` accordingly.

**Evidence-coverage follow-up is bounded to one extra round**
(`config.MAX_ADDITIONAL_RETRIEVAL_ROUNDS`), scoped to lexical/vector only,
against indexes narrowed to the specific missing labels.

**Aggregation bypasses the synthesis-evidence path.** Its result lands in
`RetrievalResult.aggregation_result` (`{"total": int | None, "raw_text": str}`)
rather than being expanded into individual ticket candidates.

## Heads up: a few things in the reference `function_tools.py`

These are flagged in detail at the top of that file — summarizing here:

- `vector_search_tool` will raise `UnboundLocalError` on a zero-hit query
  (the JSON output is only assigned inside the results loop), and iterates
  the async result with a plain `for` instead of `async for`.
- `get_ticket_relations_tool`, `get_all_connected_nodes_content_tool`, and
  the first loop in `count_tickets_by_metadata_tool` have the same
  `for row in result:` issue.
- `get_all_connected_nodes_content_tool`'s Cypher has a trailing comma
  before `LIMIT 200` (invalid syntax) and references an unbound `n` in its
  `WHERE` clause.
- `count_tickets_by_metadata_tool` calls `session.run(...)` and
  `.single()` on the union query without `await`.

None of these block wiring the retrieval engine — `graph.py` tolerates
whatever comes back — but they'll raise against a real async Neo4j session
until patched. Happy to fix these if useful; didn't touch them here since
that's a separate change from the orchestration layer.

## Usage

```python
from function_tools import FunctionTools
from graphrag_retrieval import QueryIntentResult, ToolRegistry, retrieve

function_tools = FunctionTools(driver, embedding_model)
registry = ToolRegistry({
    "vector_search_tool": function_tools.vector_search_tool,
    "full_text_keyword_tool": function_tools.full_text_keyword_tool,
    "get_ticket_relations_tool": function_tools.get_ticket_relations_tool,
    "traverse_ticket_network_tool": function_tools.traverse_ticket_network_tool,
    "get_node_details_tool": function_tools.get_node_details_tool,
    "get_all_connected_nodes_content_tool": function_tools.get_all_connected_nodes_content_tool,
    "count_tickets_by_metadata_tool": function_tools.count_tickets_by_metadata_tool,
})

result = await retrieve(
    user_query,
    intent_result,              # your existing QueryIntentResult
    tool_registry=registry,
    resolved_entities=resolved_entities,  # optional
    top_k=12,
)
```

These are the exact same bound methods you'd pass to
`FunctionTool.from_defaults(fn=...)` for your `FunctionAgent`/`ReActAgent` —
registering them there doesn't change anything about wiring them in here.

`result.model_dump()` matches the output shape from the design doc:
`status`, `query`, `intent`, `retrieval_summary`, `resolved_entities`,
`evidence`, `modality_outcomes`, `coverage`, `aggregation_result`.

See `example_usage.py` for the full wiring, and `test_smoke.py` for
runnable, infra-free tests (`python3 test_smoke.py`).

## Tuning

Everything you're likely to retune lives in `config.py`:
- `INTENT_PROFILES` — which labels/graph ops/content-relations each intent
  prioritizes, and whether it expands relation targets into node details
- `LABEL_TO_METADATA_RELATION` — which relation type backs aggregation for
  each resolved-entity label
- `RERANK_WEIGHTS`, `RRF_K` — fusion/rerank weighting
- `DEFAULT_TOP_K`, `PER_LABEL_MIN_SLOTS` — evidence bundle size and per-label
  reservation
- `MAX_ADDITIONAL_RETRIEVAL_ROUNDS` — follow-up round budget
