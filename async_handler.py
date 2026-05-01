import asyncio
import logging

import os
import json

import gradio as gr
from dotenv import load_dotenv

from async_handler import run_async
from chatbot import MeridianSupportAgent
from mcp_client import MCPClient

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("main")

# Initialize Agent and Async Stop Event
agent = MeridianSupportAgent()
stop_event = asyncio.Event()

# Global variable to hold the persistent MCP session
mcp_session = None
client_context = None
session_ready = False

url = os.getenv("MCP_SERVER_URL")

mcp = MCPClient(url)

run_async(mcp.get_mcp_session())
TOOLS = run_async(mcp.list_tools())

logger.info("Loaded %d tools from MCP server", len(TOOLS))


async def _chat_async(user_message, history):
    """
    Asynchronous handler for Gradio ChatInterface.
    Organizes context, agent call, tool handling, and fallback.
    """
    logger.info("MESSAGE RECEIVED")

    # 1. Build conversation context for the LLM
    agent.messages = [
        {
            "role": "system",
            "content": "You are a helpful support agent for Meridian Electronics. Use tools to check inventory and orders."
        }
    ]
    for turn in history:
        if isinstance(turn, dict) and "role" in turn and "content" in turn:
            # Gradio message dict format
            text = ""
            if isinstance(turn["content"], list) and turn["content"]:
                text = turn["content"][0].get("text", "")
            agent.messages.append({"role": turn["role"], "content": text})
        elif isinstance(turn, (list, tuple)) and len(turn) == 2:
            human, assistant = turn
            agent.messages.append({"role": "user", "content": human})
            agent.messages.append({"role": "assistant", "content": assistant})
        else:
            logger.warning(f"Unexpected history turn format: {turn}")

    # 2. Get LLM response (may include tool calls)
    result = await agent.chat_loop_gradio(user_message, TOOLS)

    # 3. Prepare assistant message entry
    assistant_entry = {"role": "assistant", "content": getattr(result, "content", "")}
    tool_calls = getattr(result, "tool_calls", None)
    if tool_calls:
        assistant_entry["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    agent.messages.append(assistant_entry)

    # 4. If no tool calls, return LLM's answer
    if not tool_calls:
        return getattr(result, "content", "(no response)")

    # 5. Execute each tool call and append results
    for tc in tool_calls:
        tool_name = tc.function.name
        try:
            tool_args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            tool_args = {}
            logger.warning("Bad JSON args from model for %s", tool_name)

        logger.info("Tool call: %s(%s)", tool_name, tool_args)
        try:
            tool_result = run_async(mcp.call_tool(tool_name, tool_args))
            logger.info("Tool ok: %s returned %d chars", tool_name, len(tool_result or ""))
        except Exception as e:
            logger.exception("Tool %s raised", tool_name)
            tool_result = json.dumps({"error": True, "message": str(e)})

        agent.messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": tool_result,
        })

    # 6. Return the last tool result (or a default message)
    # If tool_result is a JSON error object, return only the 'message' field
    try:
        parsed = json.loads(tool_result)
        if isinstance(parsed, dict) and parsed.get("error") and "message" in parsed:
            return parsed["message"]
    except Exception:
        pass
    return tool_result if tool_calls else "Can you send a message? I didn't get that."

# Build the Gradio UI
with gr.Blocks(title="Meridian Electronics Support") as demo:
    gr.Markdown("# 🤖 Meridian Electronics AI Support")

    stop_btn = gr.Button("⏹️ Stop Generation", variant="stop")

    chat_interface = gr.ChatInterface(
        fn=_chat_async,
        chatbot=gr.Chatbot(height=500),
        textbox=gr.Textbox(
            placeholder="Ask about orders, inventory, or account status...",
            container=False
        ),
    )

    async def stop_chat():
        logger.info("🛑 Stop requested by user.")
        stop_event.set()
        return

    stop_btn.click(fn=stop_chat, inputs=None, outputs=None)

if __name__ == "__main__":
    # Launch with a queue to handle multiple requests if needed
    demo.queue().launch()