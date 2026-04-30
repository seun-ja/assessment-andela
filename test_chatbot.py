import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch
from chatbot import MeridianSupportAgent

@pytest.mark.asyncio
async def test_chat_loop_gradio_no_tool_calls(monkeypatch):
    agent = MeridianSupportAgent()
    agent.client = AsyncMock()
    agent.model = "gpt-4o"
    agent.messages = [
        {"role": "system", "content": "Test system message."}
    ]

    # Mock MCP session
    class DummySession:
        async def list_tools(self):
            class Tools:
                tools = []
            return Tools()
        async def call_tool(self, name, args):
            return AsyncMock(content="tool result")

    # Mock OpenAI response
    class DummyResponse:
        class Choice:
            def __init__(self):
                self.message = type("Msg", (), {"tool_calls": [], "content": "Hello!"})()
        choices = [Choice()]
    agent.client.chat = AsyncMock()
    agent.client.chat.completions = AsyncMock()
    agent.client.chat.completions.create = AsyncMock(return_value=DummyResponse())

    result = await agent.chat_loop_gradio("hi", DummySession())
    assert result == "Hello!"

@pytest.mark.asyncio
async def test_chat_loop_gradio_with_tool_calls(monkeypatch):
    agent = MeridianSupportAgent()
    agent.client = AsyncMock()
    agent.model = "gpt-4o"
    agent.messages = [
        {"role": "system", "content": "Test system message."}
    ]

    # Mock MCP session
    class DummySession:
        async def list_tools(self):
            class Tool:
                name = "test_tool"
                description = "desc"
                inputSchema = {}
            class Tools:
                tools = [Tool()]
            return Tools()
        async def call_tool(self, name, args):
            class Result:
                content = "tool result"
            return Result()

    # Mock OpenAI response with tool call
    class DummyResponse:
        class ToolCall:
            function = type("Func", (), {"name": "test_tool", "arguments": "{}"})()
            id = "1"
        class Choice:
            def __init__(self):
                self.message = type("Msg", (), {"tool_calls": [DummyResponse.ToolCall()], "content": None})()
        choices = [Choice()]
    class DummyFinalResponse:
        class Choice:
            def __init__(self):
                self.message = type("Msg", (), {"content": "Final answer"})()
        choices = [Choice()]
    agent.client.chat = AsyncMock()
    agent.client.chat.completions = AsyncMock()
    agent.client.chat.completions.create = AsyncMock(side_effect=[DummyResponse(), DummyFinalResponse()])

    result = await agent.chat_loop_gradio("hi", DummySession())
    assert "Final answer" in result
    assert "System Action" in result

def test_agent_init():
    agent = MeridianSupportAgent()
    assert agent.mcp_url
    assert agent.client
    assert agent.model
    assert isinstance(agent.messages, list)
