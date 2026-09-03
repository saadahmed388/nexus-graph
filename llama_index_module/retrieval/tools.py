"""
Thin adapter around the existing LlamaIndex FunctionTools so the rest of the
engine can call them uniformly and asynchronously without caring about their
internals. This file contains NO tool logic — the tools already exist
elsewhere in the system and are only referenced here by name.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Wraps a ``{tool_name: FunctionTool}`` dict and exposes one uniform async
    entry point. Works whether the underlying tool exposes ``.acall(**kwargs)``,
    ``.call(**kwargs)``, or is a bare (sync or async) callable.
    """

    def __init__(self, tools: dict[str, Any]):
        self._tools = tools

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools.keys())

    async def call(self, name: str, **kwargs) -> Any:
        """
        Invoke a registered tool by name. Raises on a missing tool or a
        tool-side exception. Use `call_safe` when robustness to failure
        matters more than fail-fast behavior (which is the default
        everywhere in this engine's retrieval branches).
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
        # ToolOutput with a `.raw_output` or `.content` attribute — unwrap
        # transparently so callers just get the underlying data.
        if hasattr(result, "raw_output"):
            return result.raw_output
        if hasattr(result, "content"):
            return result.content
        return result

    async def call_safe(self, name: str, **kwargs) -> tuple[bool, Any]:
        """Same as `call`, but never raises — returns (ok, result_or_error_str)."""
        try:
            result = await self.call(name, **kwargs)
            return True, result
        except Exception as exc:  # noqa: BLE001 - deliberate: this is a robustness boundary
            logger.warning("Graph tool '%s' failed: %s", name, exc)
            return False, str(exc)
