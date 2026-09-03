"""
Thin adapter around the existing `FunctionTools` methods so the rest of the
engine can call them uniformly and asynchronously without caring about their
internals. This file contains NO retrieval logic of its own — the tools
already exist elsewhere in the system (see function_tools.py at the project
root for the reference implementation) and are only referenced here by name.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_tool_output(raw: Any) -> Any:
    """
    Normalize whatever a FunctionTools method handed back into plain Python
    data. In practice these tools return four different shapes depending on
    which one you call and whether it found anything:

      - a JSON string (vector_search_tool, full_text_keyword_tool,
        get_ticket_relations_tool)
      - a raw dict (get_node_details_tool, get_all_connected_nodes_content_tool
        on success)
      - a raw list (traverse_ticket_network_tool on success)
      - a plain human-readable string (count_tickets_by_metadata_tool always;
        every tool's "not found" / error message)

    dicts and lists pass through unchanged. A string is parsed as JSON when
    possible; a string that isn't valid JSON is wrapped as {"_text": raw} so
    callers never have to special-case a bare string themselves.
    """
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"_text": raw}
    return raw


def candidates_from_index_search_output(parsed: Any, matched_query: str) -> list[dict]:
    """
    Shared parser for vector_search_tool / full_text_keyword_tool output,
    both of which share the shape:
        {"status": "success", "results": [{"element_id", "labels",
         "properties", "score"}, ...], ...}
    Returns plain dicts (element_id/labels/properties/score/matched_query)
    rather than Candidate objects, so lexical.py and vector.py can each
    attach the result to the right score field.
    """
    if not isinstance(parsed, dict):
        return []
    results = parsed.get("results")
    if not isinstance(results, list):
        return []

    hits = []
    for item in results:
        if not isinstance(item, dict):
            continue
        element_id = item.get("element_id")
        if not element_id:
            continue
        hits.append({
            "element_id": str(element_id),
            "labels": item.get("labels") or [],
            "properties": item.get("properties") or {},
            "score": item.get("score"),
            "matched_query": matched_query,
        })
    return hits


class ToolRegistry:
    """
    Wraps a ``{tool_name: bound_method_or_tool}`` dict and exposes one
    uniform async entry point. Works whether the underlying tool is a plain
    (sync or async) callable — which is what `FunctionTools`'s methods are —
    or a LlamaIndex-wrapped `FunctionTool` exposing ``.acall``/``.call``.
    """

    def __init__(self, tools: dict[str, Any]):
        self._tools = tools

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools.keys())

    async def call(self, name: str, **kwargs) -> Any:
        """
        Invoke a registered tool by name and return its output normalized
        via `parse_tool_output`. Raises on a missing tool or a tool-side
        exception — use `call_safe` when robustness matters more than
        fail-fast behavior (the default everywhere in this engine).
        """
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        tool = self._tools[name]

        if hasattr(tool, "acall"):
            result = await tool.acall(**kwargs)
        elif hasattr(tool, "call"):
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: tool.call(**kwargs))
        elif callable(tool):
            result = tool(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
        else:
            raise TypeError(f"Tool '{name}' is not callable")

        # LlamaIndex FunctionTool responses are commonly wrapped in a
        # ToolOutput with a `.raw_output` or `.content` attribute.
        if hasattr(result, "raw_output"):
            result = result.raw_output
        elif hasattr(result, "content"):
            result = result.content

        return parse_tool_output(result)

    async def call_safe(self, name: str, **kwargs) -> tuple[bool, Any]:
        """Same as `call`, but never raises — returns (ok, result_or_error_str)."""
        try:
            result = await self.call(name, **kwargs)
            return True, result
        except Exception as exc:  # noqa: BLE001 - deliberate: this is a robustness boundary
            logger.warning("Graph tool '%s' failed: %s", name, exc)
            return False, str(exc)
