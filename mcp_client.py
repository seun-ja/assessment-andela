from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)

class MCPClient:
    """Thin sync-friendly wrapper around an MCP Streamable-HTTP session."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._session_ready = False
        self._tools_cache: list[dict[str, Any]] | None = None

    async def get_mcp_session(self) -> None:
        logger.info(f"🔌 Step 1: Opening SSE Connection to MCP server at {self.server_url} ...")

        self._exit_stack = AsyncExitStack()

        read, write, _ = await self._exit_stack.enter_async_context(
            streamable_http_client(self.server_url)
        )

        logger.info("🔌 Step 2: SSE Stream Connected. Starting Session...")

        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        self._session_ready = False
        try:
            await asyncio.wait_for(self._session.initialize(), timeout=10)
            self._session_ready = True
            logger.info("✅ Step 3: MCP Session Initialized!")
        except Exception:
            logger.warning("⚠️ MCP initialize failed — degraded mode")

        if not self._session_ready:
            return None

    async def aclose(self) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions in OpenAI-compatible schema, cached."""
        if self._tools_cache is not None:
            return self._tools_cache
        if self._session is None:
            raise RuntimeError("MCPClient not connected. Call connect() first.")

        response = await self._session.list_tools()
        tools: list[dict[str, Any]] = []
        for t in response.tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema or {"type": "object", "properties": {}},
                    },
                }
            )
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool, return a string result safe to feed back to the LLM."""
        if self._session is None:
            raise RuntimeError("MCPClient not connected. Call connect() first.")

        result = await self._session.call_tool(name, arguments=arguments)

        # MCP returns a list of content blocks. For this server we expect text.
        # Concatenate text blocks; on error, surface a structured message rather
        # than raising -- the LLM can then apologise to the customer gracefully.
        if result.isError:
            return json.dumps({"error": True, "message": _flatten_content(result.content)})
        return _flatten_content(result.content)


def _flatten_content(blocks: list[Any]) -> str:
    """Pull text out of MCP content blocks. Falls back to repr for safety."""
    out: list[str] = []
    for b in blocks:
        text = getattr(b, "text", None)
        if text is not None:
            out.append(text)
        else:
            out.append(repr(b))
    return "\n".join(out) if out else ""
