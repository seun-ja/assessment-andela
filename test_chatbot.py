import pytest
from unittest.mock import AsyncMock, patch
from chatbot import MeridianSupportAgent

@pytest.mark.asyncio
async def test_chat_loop_gradio_basic():
    agent = MeridianSupportAgent()
    # Patch the OpenAI client to return a fake response
    with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices = [type('obj', (object,), {'message': type('msg', (object,), {'content': 'Hello!', 'tool_calls': None})()})]
        result = await agent.chat_loop_gradio("Hi", tools=None)
        assert hasattr(result, 'content')
        assert result.content == 'Hello!'

@pytest.mark.asyncio
async def test_chat_loop_gradio_with_tool():
    agent = MeridianSupportAgent()
    # Simulate a tool call in the LLM response
    fake_tool_call = type('obj', (object,), {
        'id': '1',
        'function': type('func', (object,), {'name': 'get_order_status', 'arguments': '{"order_id": "123"}'})()
    })
    fake_message = type('msg', (object,), {'content': 'Checking order...', 'tool_calls': [fake_tool_call]})()
    with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices = [type('obj', (object,), {'message': fake_message})]
        result = await agent.chat_loop_gradio("Check order 123", tools=[{"name": "get_order_status"}])
        assert hasattr(result, 'tool_calls')
        assert result.tool_calls[0].function.name == 'get_order_status'

# Add more tests as needed for error handling, tool errors, etc.
